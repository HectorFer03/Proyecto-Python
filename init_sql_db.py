import sys
import os
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'Server'))

from application import app
from extensiones import db
from Modelos import Rol, Usuario

def inicializar_bd():
    # Usamos el contexto de la aplicación web de Flask
    with app.app_context():
        # Crea todas las tablas en el archivo SQLite según nuestros Modelos
        db.create_all()
        print("Tablas SQL creadas con éxito.")
        
        # Opcional: Crear los roles básicos por defecto si no existen
        if not Rol.query.first():
            rol_admin = Rol(nombre='admin')
            rol_user = Rol(nombre='user')
            db.session.add(rol_admin)
            db.session.add(rol_user)
            db.session.commit()
            print("Roles iniciales insertados.")

if __name__ == '__main__':
    inicializar_bd()
    print("Base de datos SQL inicializada y lista para usar.")
