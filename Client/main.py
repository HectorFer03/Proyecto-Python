import requests
import sys

BASE_URL = "http://127.0.0.1:5000"
TOKEN = None 
CURRENT_ROLE = None  # NUEVA VARIABLE: Guardará si es 'user' o 'admin'

def menu():
    role_str = f" (Rol: {CURRENT_ROLE})" if CURRENT_ROLE else " (Sin login)"
    print(f"\n--- COLLECTOR VAULT{role_str} ---")
    print("1. Registro")
    print("2. Login")
    print("3. Ver Catálogo (Público)")
    print("4. Comprar Producto (Usuario)")
    print("5. Ver Mis Pedidos (Usuario)")
    print("6. Añadir Producto (Solo Admin)")
    print("7. Editar Producto (Solo Admin)")
    print("8. Borrar Producto (Solo Admin)")
    print("9. Salir")

def register():
    print("\n--- REGISTRO ---")
    user = input("Usuario: ")
    pwd = input("Contraseña: ")
    role = input("Rol (user/admin): ") 
    try:
        res = requests.post(f"{BASE_URL}/register", json={"username": user, "password": pwd, "role": role})
        if res.status_code == 201:
            print(f">> ÉXITO: {res.json().get('msg')}")
        else:
            print(f">> ERROR: {res.json().get('msg')}")
    except Exception as e:
        print(f">> ERROR DE CONEXIÓN: {e}")

def login():
    global TOKEN, CURRENT_ROLE
    print("\n--- LOGIN ---")
    user = input("Usuario: ")
    pwd = input("Contraseña: ")
    
    try:
        res = requests.post(f"{BASE_URL}/login", json={"username": user, "password": pwd})
        
        if res.status_code == 200:
            data = res.json()
            TOKEN = data.get('access_token')
            CURRENT_ROLE = data.get('role')  # <--- ASÍ DEBE QUEDAR (sin corchetes ni cosas raras)
            print(f">> LOGIN EXITOSO. Bienvenido {user} ({CURRENT_ROLE}).")
        else:
            print(f">> ERROR: {res.json().get('msg')}")
    except Exception as e:
        print(f">> ERROR DE CONEXIÓN: {e}")

def ver_catalogo():
    try:
        res = requests.get(f"{BASE_URL}/products")
        if res.status_code == 200:
            productos = res.json()
            print("\n--- CATÁLOGO ---")
            for p in productos:
                print(f"ID: {p['_id']} | [{p['tipo']}] {p['nombre']} - {p['precio']}€ (Stock: {p['stock']})")
        else:
            print(">> Error al obtener productos")
    except Exception as e:
        print(f">> ERROR: {e}")

# --- FUNCIONES DE ADMIN PROTEGIDAS EN EL CLIENTE ---

def add_product():
    # 1. VALIDACIÓN INMEDIATA DEL ROL
    if CURRENT_ROLE != 'admin':
        print("\n ACCESO DENEGADO: Esta opción es exclusiva para Administradores.")
        return # Nos salimos de la función aquí mismo

    print("\n--- AÑADIR PRODUCTO ---")
    nombre = input("Nombre del coleccionable: ")
    tipo = input("Tipo (Carta/Figura): ")
    try:
        precio = float(input("Precio: "))
        stock = int(input("Stock: "))
    except ValueError:
        print(">> ERROR: Precio y Stock deben ser números.")
        return
    
    headers = {"Authorization": f"Bearer {TOKEN}"}
    try:
        res = requests.post(f"{BASE_URL}/products", 
                            json={"nombre": nombre, "tipo": tipo, "precio": precio, "stock": stock},
                            headers=headers)
        if res.status_code == 201:
            print(">> Producto creado correctamente.")
        else:
            print(f">> Error: {res.json().get('msg')}")
    except Exception as e:
        print(f">> ERROR: {e}")

def edit_product():
    # 1. VALIDACIÓN INMEDIATA DEL ROL
    if CURRENT_ROLE != 'admin':
        print("\n ACCESO DENEGADO: Esta opción es exclusiva para Administradores.")
        return 

    product_id = input("ID del producto a editar: ")
    print("Deja en blanco si no quieres cambiar el valor.")
    nombre = input("Nuevo nombre: ")
    tipo = input("Nuevo tipo: ")
    precio = input("Nuevo precio: ")
    stock = input("Nuevo stock: ")
    
    data = {}
    if nombre: data['nombre'] = nombre
    if tipo: data['tipo'] = tipo
    if precio: data['precio'] = float(precio)
    if stock: data['stock'] = int(stock)
    
    headers = {"Authorization": f"Bearer {TOKEN}"}
    try:
        res = requests.put(f"{BASE_URL}/products/{product_id}", json=data, headers=headers)
        if res.status_code == 200:
            print(">> Producto actualizado.")
        else:
            print(f">> Error: {res.json().get('msg')}")
    except Exception as e:
        print(f">> ERROR: {e}")

def delete_product():
    # 1. VALIDACIÓN INMEDIATA DEL ROL
    if CURRENT_ROLE != 'admin':
        print("\n ACCESO DENEGADO: Esta opción es exclusiva para Administradores.")
        return 

    product_id = input("ID del producto a eliminar: ")
    headers = {"Authorization": f"Bearer {TOKEN}"}
    try:
        res = requests.delete(f"{BASE_URL}/products/{product_id}", headers=headers)
        if res.status_code == 200:
            print(">> Producto eliminado.")
        else:
            print(f">> Error: {res.json().get('msg')}")
    except Exception as e:
        print(f">> ERROR: {e}")

# --- FUNCIONES DE USUARIO ---

def comprar_producto():
    if not TOKEN:
        print(">> ERROR: Inicia sesión primero.")
        return
    
    product_id = input("Introduce el ID del producto a comprar: ")
    headers = {"Authorization": f"Bearer {TOKEN}"}
    try:
        res = requests.post(f"{BASE_URL}/buy/{product_id}", headers=headers)
        print(f">> {res.json().get('msg')}")
    except Exception as e:
        print(f">> ERROR: {e}")

def ver_pedidos():
    if not TOKEN:
        print(">> ERROR: Inicia sesión primero.")
        return
    headers = {"Authorization": f"Bearer {TOKEN}"}
    try:
        res = requests.get(f"{BASE_URL}/my-orders", headers=headers)
        if res.status_code == 200:
            print("\n--- MIS PEDIDOS ---")
            for o in res.json():
                print(f"- {o['producto']} ({o['precio']}€) [{o['estado']}]")
        else:
            print(">> Error al recuperar pedidos.")
    except Exception as e:
        print(f">> ERROR: {e}")

if __name__ == "__main__":
    while True:
        menu()
        opc = input("Selecciona una opción: ")
        if opc == '1': register()
        elif opc == '2': login()
        elif opc == '3': ver_catalogo()
        elif opc == '4': comprar_producto()
        elif opc == '5': ver_pedidos()
        elif opc == '6': add_product()
        elif opc == '7': edit_product()
        elif opc == '8': delete_product()
        elif opc == '9': sys.exit()