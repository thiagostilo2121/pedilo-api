from fastapi import APIRouter, Depends
from sqlmodel import Session, select
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user, get_negocio_del_usuario, get_session, PaginationParams
from app.models.models import Producto
from app.schemas.producto import ProductoCreate, ProductoRead, ProductoUpdate
from app.schemas.topping import ProductoGrupoToppingConfig
from app.services import producto_service, topping_service

router = APIRouter(prefix="/api/productos", tags=["Productos"])


@router.post("/", response_model=ProductoRead)
def crear_producto(
    producto: ProductoCreate,
    session: Session = Depends(get_session),
    usuario=Depends(get_current_user),
):
    negocio = get_negocio_del_usuario(session, usuario)
    nuevo = producto_service.crear_nuevo_producto(session, negocio.id, producto)
    # Cargar la relación de categoría
    session.refresh(nuevo, ["categorias"])
    return ProductoRead.model_validate(nuevo)


@router.get("/", response_model=list[ProductoRead])
def listar_productos(
    session: Session = Depends(get_session),
    usuario=Depends(get_current_user),
    pagination: PaginationParams = Depends(),
):
    negocio = get_negocio_del_usuario(session, usuario)

    productos = session.exec(
        select(Producto)
        .where(Producto.negocio_id == negocio.id, Producto.activo)
        .options(selectinload(Producto.categorias))
        .offset(pagination.skip)
        .limit(pagination.limit)
    ).all()
    return [ProductoRead.model_validate(p) for p in productos]


@router.put("/{producto_id}", response_model=ProductoRead)
def actualizar_producto(
    producto_id: int,
    datos: ProductoUpdate,
    session: Session = Depends(get_session),
    usuario=Depends(get_current_user),
):
    negocio = get_negocio_del_usuario(session, usuario)
    actualizado = producto_service.actualizar_producto_existente(
        session, producto_id, negocio.id, datos
    )
    # Cargar la relación de categoría
    session.refresh(actualizado, ["categorias"])
    return ProductoRead.model_validate(actualizado)


@router.delete("/{producto_id}")
def eliminar_producto(
    producto_id: int, session: Session = Depends(get_session), usuario=Depends(get_current_user)
):
    negocio = get_negocio_del_usuario(session, usuario)
    producto_service.desactivar_producto(session, producto_id, negocio.id)
    return {"status": "ok", "message": "Producto desactivado"}


@router.put("/{producto_id}/toppings/")
def configurar_toppings_producto(
    producto_id: int,
    configs: list[ProductoGrupoToppingConfig],
    session: Session = Depends(get_session),
    usuario=Depends(get_current_user),
):
    """Configura qué grupos de toppings aplican a este producto"""
    negocio = get_negocio_del_usuario(session, usuario)
    topping_service.configurar_toppings_producto(session, producto_id, negocio.id, configs)
    return {"status": "ok", "message": "Toppings configurados"}


@router.get("/{producto_id}/toppings/")
def obtener_toppings_producto(
    producto_id: int,
    session: Session = Depends(get_session),
    usuario=Depends(get_current_user),
):
    """Obtiene los grupos de toppings configurados para este producto"""
    negocio = get_negocio_del_usuario(session, usuario)
    # Verificar que el producto pertenece al negocio
    producto = session.get(Producto, producto_id)
    if not producto or producto.negocio_id != negocio.id:
        from app.core.exceptions import EntityNotFoundError
        raise EntityNotFoundError("Producto no encontrado")
    return topping_service.obtener_toppings_producto(session, producto_id)
