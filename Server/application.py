from flask import Flask, request, jsonify
from flask_pymongo import PyMongo
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from bson.objectid import ObjectId
from jsonschema import validate, ValidationError
# [NUEVO] Importamos las funciones de seguridad de Werkzeug
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)

# --- CONFIGURACIÓN ---
app.config["MONGO_URI"] = "mongodb://localhost:27017/collectorvault"
app.config["JWT_SECRET_KEY"] = "super-secreto-coleccionable"

mongo = PyMongo(app)
jwt = JWTManager(app)

# ... (Tus esquemas/schemas se quedan igual) ...

# ==========================================
# RUTAS DE AUTENTICACIÓN MODIFICADAS
# ==========================================

@app.route('/register', methods=['POST'])
def register():
    try:
        data = request.get_json()
        
        # Schema (igual que antes)
        schema = {
            "type": "object",
            "properties": {
                "username": { "type": "string", "minLength": 3 },
                "password": { "type": "string", "minLength": 4 },
                "role": { "enum": ["user", "admin"] }
            },
            "required": ["username", "password", "role"],
            "additionalProperties": False
        }
        validate(instance=data, schema=schema)

        if mongo.db.users.find_one({"username": data['username']}):
            return jsonify({"msg": "El usuario ya existe"}), 400
        
        # [CAMBIO] Hasheamos la contraseña antes de guardar
        hashed_password = generate_password_hash(data['password'])

        mongo.db.users.insert_one({
            "username": data['username'],
            "password": hashed_password,  # Guardamos el hash, NO el texto plano
            "role": data['role']
        })
        
        return jsonify({"msg": "Usuario registrado correctamente"}), 201

    except ValidationError as e:
        return jsonify({"msg": e.message}), 400
    except Exception:
        return jsonify({"msg": "Error en el servidor"}), 500

@app.route('/login', methods=['POST'])
def login():
    try:
        data = request.get_json()
        
        # Schema (igual que antes)
        schema = {
            "type": "object",
            "properties": {
                "username": { "type": "string" },
                "password": { "type": "string" }
            },
            "required": ["username", "password"],
            "additionalProperties": False
        }
        validate(instance=data, schema=schema)

        user = mongo.db.users.find_one({"username": data['username']})
        
        # [CAMBIO] Usamos check_password_hash para comparar
        # Primero verificamos si 'user' existe, luego la contraseña
        if user and check_password_hash(user['password'], data['password']):
            access_token = create_access_token(identity={"username": user['username'], "role": user['role']})
            return jsonify({'access_token': access_token, 'role': user['role']}), 200
            
        return jsonify({"msg": "Credenciales incorrectas"}), 401

    except ValidationError as e:
        return jsonify({"msg": e.message}), 400
    except Exception:
        return jsonify({"msg": "Error interno"}), 500
# ==========================================
# RUTAS DE PRODUCTOS (CRUD)
# ==========================================

@app.route('/products', methods=['GET'])
def get_products():
    products = []
    for doc in mongo.db.products.find():
        products.append({
            "_id": str(doc['_id']),
            "nombre": doc['nombre'],
            "tipo": doc['tipo'],
            "precio": doc['precio'],
            "stock": doc['stock']
        })
    return jsonify(products), 200

@app.route('/products', methods=['POST'])
@jwt_required()
def add_product():
    current_user = get_jwt_identity()
    if current_user['role'] != 'admin':
        return jsonify({"msg": "Acceso denegado"}), 403

    try:
        data = request.get_json()

        # Schema para Producto
        schema = {
            "type": "object",
            "properties": {
                "nombre": { "type": "string", "minLength": 1 },
                "tipo": { "enum": ["Carta", "Figura", "Funko"] },
                "precio": { "type": "number", "exclusiveMinimum": 0 },
                "stock": { "type": "integer", "minimum": 0 }
            },
            "required": ["nombre", "tipo", "precio", "stock"],
            "additionalProperties": False
        }

        validate(instance=data, schema=schema)

        mongo.db.products.insert_one(data)
        return jsonify({"msg": "Producto añadido correctamente"}), 201

    except ValidationError as e:
        return jsonify({"msg": e.message}), 400
    except Exception as e:
        return jsonify({"msg": str(e)}), 400

@app.route('/products/<id>', methods=['PUT'])
@jwt_required()
def update_product(id):
    current_user = get_jwt_identity()
    if current_user['role'] != 'admin':
        return jsonify({"msg": "Acceso denegado"}), 403

    try:
        data = request.get_json()
        
        # Schema para Edición (No ponemos 'required' para permitir edición parcial)
        schema = {
            "type": "object",
            "properties": {
                "nombre": { "type": "string", "minLength": 1 },
                "tipo": { "enum": ["Carta", "Figura", "Funko"] },
                "precio": { "type": "number", "exclusiveMinimum": 0 },
                "stock": { "type": "integer", "minimum": 0 }
            },
            "additionalProperties": False
        }
        
        validate(instance=data, schema=schema)

        if not data:
            return jsonify({"msg": "No se enviaron datos para actualizar"}), 400

        result = mongo.db.products.update_one({"_id": ObjectId(id)}, {"$set": data})
        
        if result.matched_count == 1:
            return jsonify({"msg": "Producto actualizado"}), 200
        return jsonify({"msg": "Producto no encontrado"}), 404

    except ValidationError as e:
        return jsonify({"msg": e.message}), 400
    except Exception:
        return jsonify({"msg": "Error al actualizar"}), 400

@app.route('/products/<id>', methods=['DELETE'])
@jwt_required()
def delete_product(id):
    current_user = get_jwt_identity()
    if current_user['role'] != 'admin':
        return jsonify({"msg": "Acceso denegado"}), 403

    try:
        result = mongo.db.products.delete_one({"_id": ObjectId(id)})
        if result.deleted_count == 1:
            return jsonify({"msg": "Producto eliminado"}), 200
        return jsonify({"msg": "Producto no encontrado"}), 404
    except:
        return jsonify({"msg": "Error al eliminar"}), 400

# ==========================================
# RUTAS DE COMPRA (Sin cambios en lógica, solo limpieza)
# ==========================================

@app.route('/buy/<id>', methods=['POST'])
@jwt_required()
def buy_product(id):
    current_user = get_jwt_identity()
    
    if not ObjectId.is_valid(id):
        return jsonify({"msg": "ID inválido"}), 400

    product = mongo.db.products.find_one({"_id": ObjectId(id)})
    
    if not product:
        return jsonify({"msg": "Producto no encontrado"}), 404
    
    if product['stock'] < 1:
        return jsonify({"msg": "Sin stock"}), 400
        
    mongo.db.products.update_one({"_id": ObjectId(id)}, {"$inc": {"stock": -1}})
    
    mongo.db.orders.insert_one({
        "username": current_user['username'],
        "product_name": product['nombre'],
        "precio": product['precio'], # Ojo: en tu código original usabas 'price' aquí y 'precio' en productos. Lo he unificado a 'precio' para consistencia con tu Client.
        "status": "Completado"
    })
    
    return jsonify({"msg": f"¡Compra exitosa de {product['nombre']}!"}), 200

@app.route('/my-orders', methods=['GET'])
@jwt_required()
def my_orders():
    current_user = get_jwt_identity()
    orders = []
    # Nota: Asegúrate que al insertar la orden usas 'precio' o 'price' consistentemente. 
    # Aquí busco campos que coincidan con la inserción de arriba.
    for doc in mongo.db.orders.find({"username": current_user['username']}):
        orders.append({
            "producto": doc['product_name'],
            "precio": doc.get('precio', doc.get('price')), # Fallback por si tienes datos viejos
            "estado": doc.get('status', 'Completado')
        })
    return jsonify(orders), 200

@app.route('/profile', methods=['GET'])
@jwt_required()
def get_profile():
    # 1. Obtenemos la identidad guardada en el token (username y role)
    current_identity = get_jwt_identity()
    
    # 2. Buscamos en la base de datos por si quieres datos extra 
    # o asegurarte de que el usuario sigue existiendo.
    user = mongo.db.users.find_one({"username": current_identity['username']})
    
    if not user:
        return jsonify({"msg": "Usuario no encontrado"}), 404
        
    # 3. Devolvemos la info (¡OJO! Nunca devuelvas la contraseña)
    return jsonify({
        "id": str(user['_id']),
        "username": user['username'],
        "role": user['role']
    }), 200

if __name__ == '__main__':
    app.run(debug=True, port=5000)