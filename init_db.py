import pymongo

# 1. Conexión a MongoDB local (asegúrate de que MongoDB Compass/Server esté encendido)
try:
    client = pymongo.MongoClient("mongodb://localhost:27017/")
    print("✅ Conexión exitosa a MongoDB")
except Exception as e:
    print(f"❌ Error al conectar: {e}")
    exit()

# 2. Definir la base de datos
db = client["collectorvault"]

# 3. Limpiar la base de datos (borra todo lo anterior para empezar de cero)
db.users.drop()
db.products.drop()
db.orders.drop()
print("🧹 Base de datos limpiada")

# 4. Crear USUARIOS de prueba (Requisito: Roles diferenciados)
users = [
    {
        "username": "admin",
        "password": "123",  # En un proyecto real, esto debería ir cifrado
        "role": "admin"
    },
    {
        "username": "cliente",
        "password": "123",
        "role": "user"
    }
]
db.users.insert_many(users)
print("👤 Usuarios creados: 'admin' y 'cliente' (Pass: 123)")

# 5. Crear PRODUCTOS de prueba (Requisito: Catálogo)
products = [
    {
        "nombre": "Charizard Holo 1st Edition",
        "tipo": "Carta",
        "precio": 500.0,
        "stock": 10
    },
    {
        "nombre": "Funko Pop Spider-Man",
        "tipo": "Figura",
        "precio": 15.0,
        "stock": 50
    },
    {
        "nombre": "Black Lotus",
        "tipo": "Carta",
        "precio": 9999.0,
        "stock": 1
    }
]
db.products.insert_many(products)
print("📦 Productos creados: 3 artículos de ejemplo añadidos")

print("\n🚀 ¡TODO LISTO! Ya puedes arrancar el servidor.")