from flask import Flask, request, jsonify
from flask_pymongo import PyMongo
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from bson.objectid import ObjectId
from jsonschema import validate, ValidationError
# [NUEVO] Importamos las funciones de seguridad de Werkzeug
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)

# --- CONFIGURACIÓN ---
app.config["MONGO_URI"] = "mongodb://localhost:27017/fothelcards"
app.config["JWT_SECRET_KEY"] = "super-secreto-coleccionable"

mongo = PyMongo(app)
jwt = JWTManager(app)

# ... (Tus esquemas/schemas se quedan igual) ...

# ==========================================
# RUTAS DE AUTENTICACIÓN MODIFICADAS
# ==========================================

@app.route('/registro', methods=['POST'])
def registro():
    try:
        data = request.get_json()
        
        # Schema (igual que antes)
        schema = {
            "type": "object",
            "properties": {
                "nombre": { "type": "string", "minLength": 3 },
                "contraseña": { "type": "string", "minLength": 4 },
                "rol": { "enum": ["user", "admin"] }
            },
            "required": ["nombre", "contraseña", "rol"],
            "additionalProperties": False
        }
        validate(instance=data, schema=schema)

        if mongo.db.users.find_one({"nombre": data['nombre']}):
            return jsonify({"msg": "El usuario ya existe"}), 400
        
        # [CAMBIO] Hasheamos la contraseña antes de guardar
        hashed_contraseña = generate_password_hash(data['contraseña'])

        mongo.db.users.insert_one({
            "nombre": data['nombre'],
            "contraseña": hashed_contraseña,  # Guardamos el hash, NO el texto plano
            "rol": data['rol']
        })
        
        return jsonify({"msg": "Usuario registrado correctamente"}), 201

    except ValidationError as e:
        return jsonify({"msg": e.message}), 400
    except Exception:
        return jsonify({"msg": "Error en el servidor"}), 500

@app.route('/sesion', methods=['POST'])
def sesion():
    try:
        data = request.get_json()
        
        # Schema (igual que antes)
        schema = {
            "type": "object",
            "properties": {
                "nombre": { "type": "string" },
                "contraseña": { "type": "string" }
            },
            "required": ["nombre", "contraseña"],
            "additionalProperties": False
        }
        validate(instance=data, schema=schema)

        user = mongo.db.users.find_one({"nombre": data['nombre']})
        
        # [CAMBIO] Usamos check_contraseña_hash para comparar
        # Primero verificamos si 'user' existe, luego la contraseña
        if user and check_password_hash(user['contraseña'], data['contraseña']):
            access_token = create_access_token(identity={"nombre": user['nombre'], "rol": user['rol']})
            return jsonify({'access_token': access_token, 'rol': user['rol']}), 200
            
        return jsonify({"msg": "Credenciales incorrectas"}), 401

    except ValidationError as e:
        return jsonify({"msg": e.message}), 400
    except Exception:
        return jsonify({"msg": "Error interno"}), 500
# ==========================================
# RUTAS DE PRODUCTOS (CRUD)
# ==========================================

@app.route('/productos', methods=['GET'])
def ver_productos():
    productos = []
    for doc in mongo.db.productos.find():
        productos.append({
            "_id": str(doc['_id']),
            "nombre": doc['nombre'],
            "tipo": doc['tipo'],
            "precio": doc['precio'],
            "stock": doc['stock']
        })
    return jsonify(productos), 200

@app.route('/productos', methods=['POST'])
@jwt_required()
def añadir_producto():
    current_user = get_jwt_identity()
    if current_user['rol'] != 'admin':
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

@app.route('/productos/<id>', methods=['PUT'])
@jwt_required()
def actualizar_producto(id):
    current_user = get_jwt_identity()
    if current_user['rol'] != 'admin':
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

@app.route('/productos/<id>', methods=['DELETE'])
@jwt_required()
def eliminar_producto(id):
    usuario_act = get_jwt_identity()
    if usuario_act['rol'] != 'admin':
        return jsonify({"msg": "Acceso denegado"}), 403

    try:
        resultado = mongo.db.productos.delete_one({"_id": ObjectId(id)})
        if resultado.deleted_count == 1:
            return jsonify({"msg": "Producto eliminado"}), 200
        return jsonify({"msg": "Producto no encontrado"}), 404
    except:
        return jsonify({"msg": "Error al eliminar"}), 400

# ==========================================
# RUTAS DE COMPRA (Sin cambios en lógica, solo limpieza)
# ==========================================

@app.route('/buy/<id>', methods=['POST'])
@jwt_required()
def comprar_productos(id):
    usuario_act = get_jwt_identity()
    
    if not ObjectId.is_valid(id):
        return jsonify({"msg": "ID inválido"}), 400

    producto = mongo.db.products.find_one({"_id": ObjectId(id)})
    
    if not producto:
        return jsonify({"msg": "Producto no encontrado"}), 404
    
    if producto['stock'] < 1:
        return jsonify({"msg": "Sin stock"}), 400
        
    mongo.db.products.update_one({"_id": ObjectId(id)}, {"$inc": {"stock": -1}})
    
    mongo.db.orders.insert_one({
        "nombre":usuario_act['nombre'],
        "nombre_producto": producto['nombre'],
        "precio": producto['precio'], # Ojo: en tu código original usabas 'price' aquí y 'precio' en productos. Lo he unificado a 'precio' para consistencia con tu Client.
        "status": "Completado"
    })
    
    return jsonify({"msg": f"¡Compra exitosa de {producto['nombre']}!"}), 200

@app.route('/my-orders', methods=['GET'])
@jwt_required()
def pedidos():
    usuario_act = get_jwt_identity()
    orders = []
    # Nota: Asegúrate que al insertar la orden usas 'precio' o 'price' consistentemente. 
    # Aquí busco campos que coincidan con la inserción de arriba.
    for doc in mongo.db.orders.find({"nombre": usuario_act['nombre']}):
        orders.append({
            "producto": doc['nombre_producto'],
            "precio": doc.get('precio', doc.get('precio')), # Fallback por si tienes datos viejos
            "estado": doc.get('status', 'Completado')
        })
    return jsonify(orders), 200

@app.route('/profile', methods=['GET'])
@jwt_required()
def perfil():
    # 1. Obtenemos la identidad guardada en el token (nombre y rol)
    current_identity = get_jwt_identity()
    
    # 2. Buscamos en la base de datos por si quieres datos extra 
    # o asegurarte de que el usuario sigue existiendo.
    user = mongo.db.users.find_one({"nombre": current_identity['nombre']})
    
    if not user:
        return jsonify({"msg": "Usuario no encontrado"}), 404
        
    # 3. Devolvemos la info (¡OJO! Nunca devuelvas la contraseña)
    return jsonify({
        "id": str(user['_id']),
        "nombre": user['nombre'],
        "rol": user['rol']
    }), 200

if __name__ == '__main__':
    app.run(debug=True, port=5000)