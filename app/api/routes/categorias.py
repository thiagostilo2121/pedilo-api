from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from app.api.deps import get_current_user, get_negocio_del_usuario, get_session, PaginationParams
from app.models.models import Categoria
from app.schemas.categoria import CategoriaCreate, CategoriaRead, CategoriaUpdate
from app.services import categoria_service

router = APIRouter(prefix="/api/categorias", tags=["Categorías"])


@router.post("/", response_model=CategoriaRead)
def crear_categoria(
    categoria: CategoriaCreate,
    session: Session = Depends(get_session),
    usuario=Depends(get_current_user),
):
    negocio = get_negocio_del_usuario(session, usuario)
    nueva = categoria_service.obtener_o_crear_categoria_por_nombre(
        session, negocio.id, categoria.nombre
    )
    return CategoriaRead.model_validate(nueva)


@router.get("/", response_model=list[CategoriaRead])
def listar_categorias(
    session: Session = Depends(get_session),
    usuario=Depends(get_current_user),
    pagination: PaginationParams = Depends(),
):
    negocio = get_negocio_del_usuario(session, usuario)

    categorias = session.exec(
        select(Categoria)
        .where(Categoria.negocio_id == negocio.id, Categoria.activo)
        .offset(pagination.skip)
        .limit(pagination.limit)
    ).all()
    return [CategoriaRead.model_validate(c) for c in categorias]


@router.put("/{categoria_id}", response_model=CategoriaRead)
def actualizar_categoria(
    categoria_id: int,
    datos: CategoriaUpdate,
    session: Session = Depends(get_session),
    usuario=Depends(get_current_user),
):
    negocio = get_negocio_del_usuario(session, usuario)
    categoria = categoria_service.obtener_categoria_por_id(session, categoria_id, negocio.id)

    data = datos.dict(exclude_unset=True)
    for campo, valor in data.items():
        setattr(categoria, campo, valor)

    session.add(categoria)
    session.commit()
    session.refresh(categoria)
    return CategoriaRead.model_validate(categoria)


@router.delete("/{categoria_id}")
def eliminar_categoria(
    categoria_id: int, session: Session = Depends(get_session), usuario=Depends(get_current_user)
):
    negocio = get_negocio_del_usuario(session, usuario)
    return categoria_service.desactivar_categoria(session, categoria_id, negocio.id)
