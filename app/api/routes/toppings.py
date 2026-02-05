from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.api.deps import get_current_user, get_negocio_del_usuario, get_session
from app.schemas.topping import (
    GrupoToppingCreate,
    GrupoToppingRead,
    GrupoToppingUpdate,
    ToppingCreate,
    ToppingRead,
    ToppingUpdate,
)
from app.services import topping_service

router = APIRouter(prefix="/api/grupos-topping", tags=["Toppings"])


# ============ Grupos de Toppings ============

@router.post("/", response_model=GrupoToppingRead)
def crear_grupo(
    data: GrupoToppingCreate,
    session: Session = Depends(get_session),
    usuario=Depends(get_current_user),
):
    """Crear un grupo de toppings con toppings iniciales opcionales"""
    negocio = get_negocio_del_usuario(session, usuario)
    grupo = topping_service.crear_grupo_topping(session, negocio.id, data)
    return GrupoToppingRead(
        id=grupo.id,
        nombre=grupo.nombre,
        toppings=[
            ToppingRead(id=t.id, nombre=t.nombre, precio_extra=t.precio_extra)
            for t in grupo.toppings if t.activo
        ],
    )


@router.get("/", response_model=list[GrupoToppingRead])
def listar_grupos(
    session: Session = Depends(get_session),
    usuario=Depends(get_current_user),
):
    """Listar todos los grupos de toppings del negocio"""
    negocio = get_negocio_del_usuario(session, usuario)
    grupos = topping_service.listar_grupos_topping(session, negocio.id)
    return [
        GrupoToppingRead(
            id=g.id,
            nombre=g.nombre,
            toppings=[
                ToppingRead(id=t.id, nombre=t.nombre, precio_extra=t.precio_extra)
                for t in g.toppings if t.activo
            ],
        )
        for g in grupos
    ]


@router.put("/{grupo_id}", response_model=GrupoToppingRead)
def actualizar_grupo(
    grupo_id: int,
    data: GrupoToppingUpdate,
    session: Session = Depends(get_session),
    usuario=Depends(get_current_user),
):
    """Actualizar el nombre de un grupo de toppings"""
    negocio = get_negocio_del_usuario(session, usuario)
    grupo = topping_service.actualizar_grupo_topping(session, grupo_id, negocio.id, data)
    return GrupoToppingRead(
        id=grupo.id,
        nombre=grupo.nombre,
        toppings=[
            ToppingRead(id=t.id, nombre=t.nombre, precio_extra=t.precio_extra)
            for t in grupo.toppings if t.activo
        ],
    )


@router.delete("/{grupo_id}")
def eliminar_grupo(
    grupo_id: int,
    session: Session = Depends(get_session),
    usuario=Depends(get_current_user),
):
    """Desactivar un grupo de toppings (soft delete)"""
    negocio = get_negocio_del_usuario(session, usuario)
    topping_service.eliminar_grupo_topping(session, grupo_id, negocio.id)
    return {"status": "ok", "message": "Grupo de toppings desactivado"}


# ============ Toppings Individuales ============

@router.post("/{grupo_id}/toppings/", response_model=ToppingRead)
def agregar_topping(
    grupo_id: int,
    data: ToppingCreate,
    session: Session = Depends(get_session),
    usuario=Depends(get_current_user),
):
    """Agregar un topping a un grupo existente"""
    negocio = get_negocio_del_usuario(session, usuario)
    topping = topping_service.agregar_topping_a_grupo(session, grupo_id, negocio.id, data)
    return ToppingRead(id=topping.id, nombre=topping.nombre, precio_extra=topping.precio_extra)


@router.put("/toppings/{topping_id}", response_model=ToppingRead)
def actualizar_topping(
    topping_id: int,
    data: ToppingUpdate,
    session: Session = Depends(get_session),
    usuario=Depends(get_current_user),
):
    """Actualizar un topping individual"""
    negocio = get_negocio_del_usuario(session, usuario)
    topping = topping_service.actualizar_topping(session, topping_id, negocio.id, data)
    return ToppingRead(id=topping.id, nombre=topping.nombre, precio_extra=topping.precio_extra)


@router.delete("/toppings/{topping_id}")
def eliminar_topping(
    topping_id: int,
    session: Session = Depends(get_session),
    usuario=Depends(get_current_user),
):
    """Desactivar un topping (soft delete)"""
    negocio = get_negocio_del_usuario(session, usuario)
    topping_service.eliminar_topping(session, topping_id, negocio.id)
    return {"status": "ok", "message": "Topping desactivado"}
