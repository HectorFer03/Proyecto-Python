import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from flask import Flask, request, jsonify
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from bson.objectid import ObjectId
from jsonschema import validate, ValidationError
from werkzeug.security import generate_password_hash, check_password_hash

from config import Configuracion
from extensiones import db, jwt, mongo
from repositorios import FabricaRepositorios

# Inicialización de la aplicación web con Flask
app = Flask(__name__)
app.config.from_object(Configuracion)

# Inicializamos las extensiones con la app
db.init_app(app)
jwt.init_app(app)
if Configuracion.MOTOR_BD == 'MONGO':
    mongo.init_app(app)

# Fábrica de repositorios
fabrica = FabricaRepositorios(Configuracion.MOTOR_BD)
repo_usuarios = fabrica.obtener_repo_usuario()
repo_productos = fabrica.obtener_repo_producto()
repo_pedidos = fabrica.obtener_repo_pedido()

# ==========================================
# RUTAS DE AUTENTICACIÓN
# ==========================================

@app.route('/registro', methods=['POST'])
def registro():
    """Ruta para dar de alta a un usuario nuevo en el sistema."""
    try:
        # Extraemos el contenido JSON que nos ha enviado el cliente
        data = request.get_json()
        
        # Validamos que los datos que envía el cliente cumplan esta estructura (jsonschema)
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

        # Verificamos que no haya otro usuario con ese nombre en la base de datos
        if repo_usuarios.buscar_por_nombre(data['nombre']):
            return jsonify({"msg": "El usuario ya existe"}), 400
        
        # Encriptamos la contraseña para no guardarla en texto plano, aportando seguridad
        hashed_contraseña = generate_password_hash(data['contraseña'])
        
        # Guardamos el nuevo documento de usuario usando el repositorio
        repo_usuarios.crear(data['nombre'], hashed_contraseña, data['rol'])
        
        return jsonify({"msg": "Usuario registrado correctamente"}), 201
    except ValidationError as e:
        return jsonify({"msg": e.message}), 400
    except Exception as e:
        return jsonify({"msg": f"Error en el servidor: {e}"}), 500

@app.route('/sesion', methods=['POST'])
def sesion():
    """Ruta para que un usuario inicie sesión y reciba su token JWT."""
    try:
        data = request.get_json()
        # Buscamos al usuario en base de datos mediante su nombre
        user = repo_usuarios.buscar_por_nombre(data['nombre'])
        
        # Comprobamos que el usuario existe y que la contraseña enviada coincide con el hash almacenado
        if user and check_password_hash(user['contrasena_hash'], data['contraseña']):
            # Creamos un token en el que la 'identidad' (identity) es el nombre de usuario
            access_token = create_access_token(identity=user['nombre'])
            # Enviamos el token y el rol al cliente
            return jsonify({'access_token': access_token, 'rol': user['rol']}), 200
            
        return jsonify({"msg": "Credenciales incorrectas"}), 401
    except Exception as e:
        return jsonify({"msg": f"Error interno: {e}"}), 500

# ==========================================
# RUTAS DE PRODUCTOS (CRUD)
# ==========================================

@app.route('/productos', methods=['GET'])
def ver_productos():
    """Ruta pública que devuelve la lista de todos los productos del catálogo."""
    productos = repo_productos.obtener_todos()
    return jsonify(productos), 200

@app.route('/productos', methods=['POST'])
@jwt_required()  # <--- OBLIGA a que la petición incluya un token JWT válido
def añadir_producto():
    """Crea un nuevo producto. Ruta exclusiva para administradores."""
    
    # Obtenemos quién es el usuario logueado extrayendo la info del token
    nombre_usuario = get_jwt_identity()
    user_db = repo_usuarios.buscar_por_nombre(nombre_usuario)
    
    # Validación de seguridad: el usuario debe existir y tener el rol 'admin'
    if not user_db or user_db['rol'] != 'admin':
        return jsonify({"msg": "Acceso denegado"}), 403

    try:
        data = request.get_json()
        repo_productos.crear(data)
        return jsonify({"msg": "Producto añadido correctamente"}), 201
    except Exception as e:
        return jsonify({"msg": f"Error al añadir producto: {e}"}), 400

@app.route('/productos/<id>', methods=['PUT'])
@jwt_required()
def actualizar_producto(id):
    nombre_usuario = get_jwt_identity()
    user_db = repo_usuarios.buscar_por_nombre(nombre_usuario)
    if not user_db or user_db['rol'] != 'admin':
        return jsonify({"msg": "Acceso denegado"}), 403

    try:
        data = request.get_json()
        if repo_productos.actualizar(id, data):
            return jsonify({"msg": "Producto actualizado"}), 200
        return jsonify({"msg": "Producto no encontrado"}), 404
    except Exception as e:
        return jsonify({"msg": f"Error al actualizar: {e}"}), 400

@app.route('/productos/<id>', methods=['DELETE'])
@jwt_required()
def eliminar_producto(id):
    nombre_usuario = get_jwt_identity()
    user_db = repo_usuarios.buscar_por_nombre(nombre_usuario)
    if not user_db or user_db['rol'] != 'admin':
        return jsonify({"msg": "Acceso denegado"}), 403

    try:
        if repo_productos.eliminar(id):
            return jsonify({"msg": "Producto eliminado"}), 200
        return jsonify({"msg": "Producto no encontrado"}), 404
    except Exception as e:
        return jsonify({"msg": f"Error al eliminar: {e}"}), 400

# ==========================================
# RUTAS DE COMPRA
# ==========================================

@app.route('/comprar/<id>', methods=['POST'])
@jwt_required()
def comprar_productos(id):
    """Permite al usuario logueado comprar un producto, restando stock y guardando un ticket (pedido)."""
    # Identificamos quién compra usando la info del token
    nombre_usuario = get_jwt_identity()
    user_db = repo_usuarios.buscar_por_nombre(nombre_usuario)
    
    if not user_db:
        return jsonify({"msg": "Usuario no válido"}), 400

    producto = repo_productos.obtener_por_id(id)

    # Verificamos si existe el producto y si hay al menos 1 unidad de stock
    if not producto or producto.get('stock', 0) < 1:
        return jsonify({"msg": "Producto no disponible o ID no existe"}), 400
        
    try:
        repo_pedidos.crear_pedido(user_db['id'], id, producto['nombre'], producto['precio'])
        return jsonify({"msg": f"¡Compra exitosa de {producto['nombre']}!"}), 200
    except Exception as e:
        return jsonify({"msg": f"Error al realizar pedido: {e}"}), 400

@app.route('/mis-pedidos', methods=['GET'])
@jwt_required()
def pedidos():
    nombre_usuario = get_jwt_identity()
    user_db = repo_usuarios.buscar_por_nombre(nombre_usuario)
    if not user_db:
        return jsonify({"msg": "Usuario no encontrado"}), 404
        
    orders = repo_pedidos.obtener_por_usuario(user_db['id'])
    return jsonify(orders), 200

@app.route('/perfil', methods=['GET'])
@jwt_required()
def perfil():
    nombre_usuario = get_jwt_identity()
    user = repo_usuarios.buscar_por_nombre(nombre_usuario)
    
    if not user:
        return jsonify({"msg": "Usuario no encontrado"}), 404
        
    return jsonify({
        "nombre": user['nombre'],
        "rol": user['rol']
    }), 200

if __name__ == '__main__':
    app.run(debug=True, port=5000)
