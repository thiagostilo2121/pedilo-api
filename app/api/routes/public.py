from sqlalchemy.orm import joinedload
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.api.deps import get_session, PaginationParams
from app.models.models import Negocio, Pedido, Producto, Categoria
from app.schemas.pedido import PedidoCreate, PedidoRead
from app.schemas.producto import ProductoRead
from app.schemas.negocio import NegocioRead
from app.schemas.categoria import CategoriaRead
from app.services.pedido_service import crear_nuevo_pedido

router = APIRouter(prefix="/public", tags=["Públicos"])


@router.get("/{slug}", response_model=NegocioRead)
def get_negocio(slug: str, session: Session = Depends(get_session)):
    negocio = session.exec(select(Negocio).where(Negocio.slug == slug)).first()

    if not negocio:
        raise HTTPException(status_code=404, detail="Negocio no encontrado")

    return negocio

@router.get("/{slug}/productos", response_model=list[ProductoRead])
def listar_productos_por_slug(
    slug: str,
    session: Session = Depends(get_session),
    pagination: PaginationParams = Depends(),
):
    negocio = session.exec(
        select(Negocio).where(Negocio.slug == slug, Negocio.activo)
    ).first()
    if not negocio:
        raise HTTPException(status_code=404, detail="Negocio no encontrado")
    
    productos = session.exec(
        select(Producto)
        .where(Producto.negocio_id == negocio.id, Producto.activo)
        .options(joinedload(Producto.categorias))
        .offset(pagination.skip)
        .limit(pagination.limit)
    ).all()

    result = []
    for p in productos:
        # Validamos usando el modelo base
        p_read = ProductoRead.model_validate(p)
        # Asignamos manualmente el nombre de la categoría usando la property del modelo
        p_read.categoria = p.categoria_nombre
        result.append(p_read)
        
    return result

@router.get("/{slug}/categorias", response_model=list[CategoriaRead])
def listar_categorias_por_slug(
    slug: str,
    session: Session = Depends(get_session),
    pagination: PaginationParams = Depends(),
):
    negocio = session.exec(
        select(Negocio).where(Negocio.slug == slug, Negocio.activo)
    ).first()
    if not negocio:
        raise HTTPException(status_code=404, detail="Negocio no encontrado")

    categorias = session.exec(
        select(Categoria)
        .where(Categoria.negocio_id == negocio.id, Categoria.activo)
        .offset(pagination.skip)
        .limit(pagination.limit)
    ).all()
    return [CategoriaRead.model_validate(c) for c in categorias]


@router.post("/{slug}/pedidos", response_model=PedidoRead)
def crear_pedido(slug: str, data: PedidoCreate, session: Session = Depends(get_session)):
    return crear_nuevo_pedido(session, slug, data)


@router.get("/{slug}/pedidos/{codigo}", response_model=PedidoRead)
def ver_pedido(slug: str, codigo: str, session: Session = Depends(get_session)):
    negocio = session.exec(
        select(Negocio).where(Negocio.slug == slug, Negocio.activo)
    ).first()
    if not negocio:
        raise HTTPException(status_code=404, detail="Negocio no encontrado")

    pedido = session.exec(
        select(Pedido).where(Pedido.negocio_id == negocio.id, Pedido.codigo == codigo)
    ).first()

    if not pedido:
        raise HTTPException(status_code=404, detail="Pedido no encontrado")

    return pedido
