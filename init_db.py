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

# Borramos las colecciones unificadas
if "usuarios" in collection_names: db.usuarios.drop()
if "productos" in collection_names: db.productos.drop()
if "pedidos" in collection_names: db.pedidos.drop()

# Borramos también los nombres antiguos por si habías hecho pruebas
if "Usuarios" in collection_names: db.Usuarios.drop()
if "users" in collection_names: db.users.drop()
if "Productos" in collection_names: db.Productos.drop()
if "products" in collection_names: db.products.drop()
if "Pedidos" in collection_names: db.Pedidos.drop()
if "orders" in collection_names: db.orders.drop()


print("🧹 Base de datos limpiada")

# 4. Crear las colecciones vacías (Estructura en minúsculas)
db.create_collection("usuarios")
db.create_collection("productos")
db.create_collection("pedidos")

