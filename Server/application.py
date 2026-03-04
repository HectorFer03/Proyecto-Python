from flask import Flask, request, jsonify
from flask_pymongo import PyMongo
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from bson.objectid import ObjectId
from jsonschema import validate, ValidationError
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)

# --- CONFIGURACIÓN ---
app.config["MONGO_URI"] = "mongodb://localhost:27017/fothelcards"
app.config["JWT_SECRET_KEY"] = "super-secreto-coleccionable"

mongo = PyMongo(app)
jwt = JWTManager(app)

# ==========================================
# RUTAS DE AUTENTICACIÓN
# ==========================================

@app.route('/registro', methods=['POST'])
def registro():
    try:
        data = request.get_json()
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

        if mongo.db.usuarios.find_one({"nombre": data['nombre']}):
            return jsonify({"msg": "El usuario ya existe"}), 400
        
        hashed_contraseña = generate_password_hash(data['contraseña'])
        mongo.db.usuarios.insert_one({
            "nombre": data['nombre'],
            "contraseña": hashed_contraseña,
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
        user = mongo.db.usuarios.find_one({"nombre": data['nombre']})
        
        if user and check_password_hash(user['contraseña'], data['contraseña']):
            # SOLUCIÓN: Guardamos solo el nombre (que es un String)
            access_token = create_access_token(identity=user['nombre'])
            return jsonify({'access_token': access_token, 'rol': user['rol']}), 200
            
        return jsonify({"msg": "Credenciales incorrectas"}), 401
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
    nombre_usuario = get_jwt_identity()
    user_db = mongo.db.usuarios.find_one({"nombre": nombre_usuario})
    
    if not user_db or user_db['rol'] != 'admin':
        return jsonify({"msg": "Acceso denegado"}), 403

    try:
        data = request.get_json()
        
        # Validamos que el ID no exista para evitar duplicados y devolver error 400
        if mongo.db.productos.find_one({"_id": data.get("_id")}):
            return jsonify({"msg": "Ese ID ya existe. Usa uno diferente."}), 400
            
        mongo.db.productos.insert_one(data)
        return jsonify({"msg": "Producto añadido correctamente"}), 201
    except Exception as e:
        return jsonify({"msg": "Error al añadir producto"}), 400

@app.route('/productos/<id>', methods=['PUT'])
@jwt_required()
def actualizar_producto(id):
    nombre_usuario = get_jwt_identity()
    user_db = mongo.db.usuarios.find_one({"nombre": nombre_usuario})
    if not user_db or user_db['rol'] != 'admin':
        return jsonify({"msg": "Acceso denegado"}), 403

    try:
        data = request.get_json()
        # Buscamos directamente por 'id' (String), sin ObjectId
        result = mongo.db.productos.update_one({"_id": id}, {"$set": data})
        if result.matched_count == 1:
            return jsonify({"msg": "Producto actualizado"}), 200
        return jsonify({"msg": "Producto no encontrado"}), 404
    except Exception:
        return jsonify({"msg": "Error al actualizar"}), 400

@app.route('/productos/<id>', methods=['DELETE'])
@jwt_required()
def eliminar_producto(id):
    nombre_usuario = get_jwt_identity()
    user_db = mongo.db.usuarios.find_one({"nombre": nombre_usuario})
    if not user_db or user_db['rol'] != 'admin':
        return jsonify({"msg": "Acceso denegado"}), 403

    try:
        # Borramos directamente por 'id' (String)
        resultado = mongo.db.productos.delete_one({"_id": id})
        if resultado.deleted_count == 1:
            return jsonify({"msg": "Producto eliminado"}), 200
        return jsonify({"msg": "Producto no encontrado"}), 404
    except:
        return jsonify({"msg": "Error al eliminar"}), 400

# ==========================================
# RUTAS DE COMPRA
# ==========================================

@app.route('/comprar/<id>', methods=['POST'])
@jwt_required()
def comprar_productos(id):
    nombre_usuario = get_jwt_identity()
    if not ObjectId.is_valid(id):
        return jsonify({"msg": "ID inválido"}), 400

    producto = mongo.db.productos.find_one({"_id": ObjectId(id)})
    if not producto or producto['stock'] < 1:
        return jsonify({"msg": "Producto no disponible"}), 400
        
    mongo.db.productos.update_one({"_id": ObjectId(id)}, {"$inc": {"stock": -1}})
    mongo.db.pedidos.insert_one({
        "nombre": nombre_usuario,
        "nombre_producto": producto['nombre'],
        "precio": producto['precio'], 
        "status": "Completado"
    })
    return jsonify({"msg": f"¡Compra exitosa de {producto['nombre']}!"}), 200

@app.route('/mis-pedidos', methods=['GET'])
@jwt_required()
def pedidos():
    nombre_usuario = get_jwt_identity()
    orders = []
    for doc in mongo.db.pedidos.find({"nombre": nombre_usuario}):
        orders.append({
            "producto": doc['nombre_producto'],
            "precio": doc.get('precio', 0),
            "estado": doc.get('status', 'Completado')
        })
    return jsonify(orders), 200

@app.route('/perfil', methods=['GET'])
@jwt_required()
def perfil():
    nombre_usuario = get_jwt_identity()
    user = mongo.db.usuarios.find_one({"nombre": nombre_usuario})
    
    if not user:
        return jsonify({"msg": "Usuario no encontrado"}), 404
        
    return jsonify({
        "nombre": user['nombre'],
        "rol": user['rol']
    }), 200

if __name__ == '__main__':
    app.run(debug=True, port=5000)
