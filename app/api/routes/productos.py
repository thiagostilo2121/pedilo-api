from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from app.api.deps import get_current_user, get_negocio_del_usuario, get_session, PaginationParams
from app.models.models import Producto
from app.schemas.producto import ProductoCreate, ProductoRead, ProductoUpdate
from app.services import producto_service

router = APIRouter(prefix="/api/productos", tags=["Productos"])


@router.post("/", response_model=ProductoRead)
def crear_producto(
    producto: ProductoCreate,
    session: Session = Depends(get_session),
    usuario=Depends(get_current_user),
):
    negocio = get_negocio_del_usuario(session, usuario)
    nuevo = producto_service.crear_nuevo_producto(session, negocio.id, producto)
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
    return ProductoRead.model_validate(actualizado)


@router.delete("/{producto_id}")
def eliminar_producto(
    producto_id: int, session: Session = Depends(get_session), usuario=Depends(get_current_user)
):
    negocio = get_negocio_del_usuario(session, usuario)
    producto_service.desactivar_producto(session, producto_id, negocio.id)
    return {"status": "ok", "message": "Producto desactivado"}
