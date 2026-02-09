from sqlmodel import Session, select, func
from app.models.models import Categoria, Producto
from app.core.exceptions import EntityNotFoundError, BusinessLogicError

def obtener_categoria_por_id(session: Session, categoria_id: int, negocio_id: int) -> Categoria:
    categoria = session.get(Categoria, categoria_id)
    if not categoria or categoria.negocio_id != negocio_id:
        raise EntityNotFoundError("Categoría no encontrada")
    return categoria

def obtener_o_crear_categoria_por_nombre(session: Session, negocio_id: int, nombre: str) -> Categoria:
    categoria = session.exec(
        select(Categoria).where(
            Categoria.negocio_id == negocio_id,
            Categoria.nombre == nombre,
            Categoria.activo == True,
        )
    ).first()

    if categoria:
        return categoria

    cantidad_actual = session.exec(
        select(func.count()).select_from(Categoria).where(Categoria.negocio_id == negocio_id, Categoria.activo == True)
    ).one()

    if cantidad_actual >= 20:
        raise BusinessLogicError("Has alcanzado el límite máximo de 20 categorías activas.")

    nueva = Categoria(negocio_id=negocio_id, nombre=nombre, activo=True)
    session.add(nueva)
    session.commit()
    session.refresh(nueva)
    return nueva

def desactivar_categoria(session: Session, categoria_id: int, negocio_id: int):
    categoria = obtener_categoria_por_id(session, categoria_id, negocio_id)
    
    if categoria.nombre.lower() == "otros":
        raise BusinessLogicError("La categoría 'Otros' no puede ser desactivada")

    categoria_otros = obtener_o_crear_categoria_por_nombre(session, negocio_id, "Otros")

    productos = session.exec(
        select(Producto).where(
            Producto.categoria_id == categoria.id,
            Producto.negocio_id == negocio_id,
            Producto.activo == True,
        )
    ).all()

    for producto in productos:
        producto.categoria_id = categoria_otros.id
        session.add(producto)

    categoria.activo = False
    session.add(categoria)
    session.commit()
    return {"message": "Categoría desactivada y productos movidos a 'Otros'"}
