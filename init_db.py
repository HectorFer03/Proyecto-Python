import pymongo

# 1. Conexión a MongoDB local
try:
    cliente = pymongo.MongoClient("mongodb://localhost:27017/")
    print("Conexión exitosa a MongoDB")
except Exception as e:
    print(f"Error al conectar: {e}")
    exit()

# 2. Definir la base de datos
db = cliente["fothelcards"]

# 3. Limpiar la base de datos (Borra todo para evitar duplicados o errores)
collection_names = db.list_collection_names()
if "Usuarios" in collection_names: db.usuarios.drop()
if "Productos" in collection_names: db.productos.drop()
if "Pedidos" in collection_names: db.pedidos.drop()
if "Opiniones" in collection_names: db.opiniones.drop()

print("🧹 Base de datos limpiada")

# 4. Crear las colecciones vacías (Estructura)
# En MongoDB no es obligatorio crearlas explícitamente, pero esto hace 
# que aparezcan inmediatamente en Compass aunque no tengan datos.

db.create_collection("Usuarios")
db.create_collection("Productos")
db.create_collection("Pedidos")
db.create_collection("Opiniones")

