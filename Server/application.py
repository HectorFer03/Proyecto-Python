from flask import Flask, request, jsonify
from flask_pymongo import PyMongo
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from bson.objectid import ObjectId
# Importamos lo necesario para validar
from marshmallow import Schema, fields, validate, ValidationError 

app = Flask(__name__)

# --- CONFIGURACIÓN ---
app.config["MONGO_URI"] = "mongodb://localhost:27017/collectorvault"
app.config["JWT_SECRET_KEY"] = "super-secreto-coleccionable"

mongo = PyMongo(app)
jwt = JWTManager(app)

# ==========================================
# 1. DEFINICIÓN DE ESQUEMAS (SCHEMAS)
# ==========================================

class RegisterSchema(Schema):
    username = fields.Str(required=True, validate=validate.Length(min=3, error="El usuario debe tener al menos 3 caracteres."))
    password = fields.Str(required=True, validate=validate.Length(min=4, error="La contraseña debe tener al menos 4 caracteres."))
    role = fields.Str(validate=validate.OneOf(["user", "admin"], error="El rol solo puede ser 'user' o 'admin'."), missing="user")

class LoginSchema(Schema):
    username = fields.Str(required=True, error_messages={"required": "Falta el usuario."})
    password = fields.Str(required=True, error_messages={"required": "Falta la contraseña."})

class ProductSchema(Schema):
    nombre = fields.Str(required=True, validate=validate.Length(min=1, error="El nombre no puede estar vacío."))
    # Validamos que sea uno de los tipos permitidos
    tipo = fields.Str(required=True, validate=validate.OneOf(["Carta", "Figura", "Funko"], error="Tipo inválido. Usa: Carta, Figura o Funko."))
    # Validamos precio positivo
    precio = fields.Float(required=True, validate=validate.Range(min=0.01, error="El precio debe ser mayor a 0."))
    # Validamos stock no negativo
    stock = fields.Int(required=True, validate=validate.Range(min=0, error="El stock no puede ser negativo."))

# ==========================================
# 2. RUTAS DE AUTENTICACIÓN
# ==========================================

@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    
    # Validar datos con el esquema
    schema = RegisterSchema()
    try:
        validated_data = schema.load(data)
    except ValidationError as err:
        return jsonify(err.messages), 400

    # Comprobar duplicados
    if mongo.db.users.find_one({"username": validated_data['username']}):
        return jsonify({"msg": "El usuario ya existe"}), 400
    
    # Guardar
    mongo.db.users.insert_one({
        "username": validated_data['username'],
        "password": validated_data['password'], 
        "role": validated_data['role']
    })
    
    return jsonify({"msg": "Usuario registrado correctamente"}), 201

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    
    # Validar datos
    schema = LoginSchema()
    try:
        validated_data = schema.load(data)
    except ValidationError as err:
        return jsonify(err.messages), 400

    # Buscar usuario
    user = mongo.db.users.find_one({"username": validated_data['username']})
    
    if user and user['password'] == validated_data['password']:
        access_token = create_access_token(identity={"username": user['username'], "role": user['role']})
        return jsonify(access_token=access_token, role=user['role']), 200
        
    return jsonify({"msg": "Credenciales incorrectas"}), 401

# ==========================================
# 3. RUTAS DE PRODUCTOS (CRUD)
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

    data = request.get_json()
    
    # Validar con ProductSchema
    schema = ProductSchema()
    try:
        validated_data = schema.load(data)
    except ValidationError as err:
        return jsonify(err.messages), 400

    mongo.db.products.insert_one(validated_data)
    return jsonify({"msg": "Producto añadido correctamente"}), 201

@app.route('/products/<id>', methods=['PUT'])
@jwt_required()
def update_product(id):
    current_user = get_jwt_identity()
    if current_user['role'] != 'admin':
        return jsonify({"msg": "Acceso denegado"}), 403

    data = request.get_json()
    
    # Validar parcial (partial=True) permite enviar solo precio, o solo stock...
    schema = ProductSchema()
    try:
        validated_data = schema.load(data, partial=True)
    except ValidationError as err:
        return jsonify(err.messages), 400

    if not validated_data:
        return jsonify({"msg": "No se enviaron datos para actualizar"}), 400

    try:
        mongo.db.products.update_one({"_id": ObjectId(id)}, {"$set": validated_data})
        return jsonify({"msg": "Producto actualizado"}), 200
    except:
        return jsonify({"msg": "Error al actualizar (posible ID inválido)"}), 400

@app.route('/products/<id>', methods=['DELETE'])
@jwt_required()
def delete_product(id):
    current_user = get_jwt_identity()
    if current_user['role'] != 'admin':
        return jsonify({"msg": "Acceso denegado"}), 403

    try:
        mongo.db.products.delete_one({"_id": ObjectId(id)})
        return jsonify({"msg": "Producto eliminado"}), 200
    except:
        return jsonify({"msg": "Error al eliminar"}), 400

# ==========================================
# 4. RUTAS DE COMPRA (LÓGICA DE NEGOCIO)
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
        
    # Restar stock y crear pedido
    mongo.db.products.update_one({"_id": ObjectId(id)}, {"$inc": {"stock": -1}})
    
    mongo.db.orders.insert_one({
        "username": current_user['username'],
        "product_name": product['nombre'],
        "price": product['precio'],
        "status": "Completado"
    })
    
    return jsonify({"msg": f"¡Compra exitosa de {product['nombre']}!"}), 200

@app.route('/my-orders', methods=['GET'])
@jwt_required()
def my_orders():
    current_user = get_jwt_identity()
    orders = []
    for doc in mongo.db.orders.find({"username": current_user['username']}):
        orders.append({
            "producto": doc['product_name'],
            "precio": doc['precio'],
            "estado": doc['status']
        })
    return jsonify(orders), 200

if __name__ == '__main__':
    app.run(debug=True, port=5000)