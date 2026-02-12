import pymongo

# 1. Conexión a MongoDB local
try:
    client = pymongo.MongoClient("mongodb://localhost:27017/")
    print("✅ Conexión exitosa a MongoDB")
except Exception as e:
    print(f"❌ Error al conectar: {e}")
    exit()

# 2. Definir la base de datos
db = client["collectorvault"]

# 3. Limpiar la base de datos (borra todo lo anterior)
db.users.drop()
db.products.drop()
db.orders.drop()
print("🧹 Base de datos limpiada: No hay usuarios ni productos.")

print("\n🚀 ¡TODO LISTO! La base de datos está vacía.")
