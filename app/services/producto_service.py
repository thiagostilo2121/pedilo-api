from sqlmodel import Session, select, func
from app.models.models import Producto
from app.schemas.producto import ProductoCreate, ProductoUpdate
from app.services.categoria_service import obtener_o_crear_categoria_por_nombre
from app.utils.cloudinary import validar_imagen_url
from app.core.exceptions import EntityNotFoundError, BusinessLogicError

def crear_nuevo_producto(session: Session, negocio_id: int, data: ProductoCreate) -> Producto:
    cantidad_actual = session.exec(
        select(func.count()).select_from(Producto).where(Producto.negocio_id == negocio_id, Producto.activo == True)
    ).one()
    
    if cantidad_actual >= 100:
        raise BusinessLogicError("Has alcanzado el límite máximo de 100 productos activos.")

    nombre_categoria = data.categoria or "Otros"
    categoria = obtener_o_crear_categoria_por_nombre(session, negocio_id, nombre_categoria)

    imagen_url = validar_imagen_url(data.imagen_url) if data.imagen_url else None

    nuevo = Producto(
        nombre=data.nombre,
        descripcion=data.descripcion,
        precio=data.precio,
        imagen_url=imagen_url,
        negocio_id=negocio_id,
        categoria_id=categoria.id,
        stock=data.stock,
    )

    session.add(nuevo)
    session.commit()
    session.refresh(nuevo)
    return nuevo

def actualizar_producto_existente(session: Session, producto_id: int, negocio_id: int, data: ProductoUpdate) -> Producto:
    producto = session.get(Producto, producto_id)
    if not producto or producto.negocio_id != negocio_id:
        raise EntityNotFoundError("Producto no encontrado")

    update_data = data.dict(exclude_unset=True)

    if "categoria" in update_data:
        nombre_categoria = update_data.pop("categoria") or "Otros"
        categoria = obtener_o_crear_categoria_por_nombre(session, negocio_id, nombre_categoria)
        producto.categoria_id = categoria.id

    for campo, valor in update_data.items():
        setattr(producto, campo, valor)

    session.add(producto)
    session.commit()
    session.refresh(producto)
    return producto

def desactivar_producto(session: Session, producto_id: int, negocio_id: int):
    producto = session.get(Producto, producto_id)
    if not producto or producto.negocio_id != negocio_id:
        raise EntityNotFoundError("Producto no encontrado")

    producto.activo = False
    session.add(producto)
    session.commit()
    return {"message": "Producto desactivado"}
