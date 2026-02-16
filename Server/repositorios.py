from extensiones import db
# Importamos las clases con sus nombres en español
from modelos import Usuario, Producto, Pedido, Rol

class RepositorioUsuario:
    def buscar_por_nombre(self, nombre):
        # 'nombre' es la columna en la BD (antes username)
        return Usuario.query.filter_by(nombre=nombre).first()

    def crear(self, nombre, contrasena_hash, nombre_rol):
        # Buscamos el rol en la BD
        rol_obj = Rol.query.filter_by(nombre=nombre_rol).first()
        
        # Si no existe (seguridad), asignamos 'user' por defecto
        if not rol_obj:
            rol_obj = Rol.query.filter_by(nombre='user').first()
            
        nuevo_usuario = Usuario(nombre=nombre, contrasena_hash=contrasena_hash, rol=rol_obj)
        db.session.add(nuevo_usuario)
        db.session.commit()
        return nuevo_usuario

class RepositorioProducto:
    def obtener_todos(self):
        return Producto.query.all()

    def obtener_por_id(self, id_producto):
        return Producto.query.get(id_producto)

    def crear(self, datos):
        nuevo_producto = Producto(
            nombre=datos['nombre'],
            tipo=datos['tipo'],
            precio=datos['precio'],
            stock=datos['stock']
        )
        db.session.add(nuevo_producto)
        db.session.commit()
        return nuevo_producto

    def actualizar(self, id_producto, datos):
        producto = self.obtener_por_id(id_producto)
        if not producto: return None
        
        if 'nombre' in datos: producto.nombre = datos['nombre']
        if 'tipo' in datos: producto.tipo = datos['tipo']
        if 'precio' in datos: producto.precio = float(datos['precio'])
        if 'stock' in datos: producto.stock = int(datos['stock'])
        
        db.session.commit()
        return producto

    def eliminar(self, id_producto):
        producto = self.obtener_por_id(id_producto)
        if producto:
            db.session.delete(producto)
            db.session.commit()
            return True
        return False

class RepositorioPedido:
    def crear_pedido(self, objeto_usuario, objeto_producto):
        # 1. Crear el registro del pedido
        nuevo_pedido = Pedido(
            usuario_id=objeto_usuario.id,
            nombre_producto=objeto_producto.nombre,
            precio=objeto_producto.precio,
            estado="Completado"
        )
        # 2. Restar stock (Lógica de negocio)
        objeto_producto.stock -= 1
        
        db.session.add(nuevo_pedido)
        db.session.commit()
        return nuevo_pedido
    
    def obtener_por_usuario(self, usuario_id):
        return Pedido.query.filter_by(usuario_id=usuario_id).all()