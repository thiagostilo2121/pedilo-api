from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import selectinload
from sqlmodel import Session, select, desc, col

from app.api.deps import get_current_user, get_negocio_del_usuario, get_session, PaginationParams
from app.models.models import Pedido, PedidoEstado
from app.schemas.pedido import PedidoRead

router = APIRouter(prefix="/api/pedidos", tags=["Pedidos"])


@router.get("/", response_model=list[PedidoRead])
def listar_pedidos(
    estado: PedidoEstado | None = None,
    buscar: str | None = Query(None, description="Buscar por código o nombre de cliente"),
    fecha_desde: datetime | None = Query(None, description="Filtrar desde fecha (ISO 8601)"),
    fecha_hasta: datetime | None = Query(None, description="Filtrar hasta fecha (ISO 8601)"),
    session: Session = Depends(get_session),
    usuario=Depends(get_current_user),
    pagination: PaginationParams = Depends(),
):
    negocio = get_negocio_del_usuario(session, usuario)
    query = (
        select(Pedido)
        .where(Pedido.negocio_id == negocio.id)
        .options(selectinload(Pedido.items))
    )

    if estado is not None:
        query = query.where(Pedido.estado == estado)

    if buscar:
        buscar_like = f"%{buscar}%"
        query = query.where(
            (col(Pedido.codigo).ilike(buscar_like))
            | (col(Pedido.nombre_cliente).ilike(buscar_like))
        )

    if fecha_desde is not None:
        query = query.where(Pedido.creado_en >= fecha_desde)

    if fecha_hasta is not None:
        query = query.where(Pedido.creado_en <= fecha_hasta)

    query = query.order_by(desc(Pedido.creado_en)).offset(pagination.skip).limit(pagination.limit)

    pedidos = session.exec(query).all()
    return pedidos




@router.patch("/{pedido_id}/aceptar")
def aceptar_pedido(
    pedido_id: int, session: Session = Depends(get_session), usuario=Depends(get_current_user)
):
    negocio = get_negocio_del_usuario(session, usuario)
    pedido = session.get(Pedido, pedido_id)

    if not pedido or pedido.negocio_id != negocio.id:
        raise HTTPException(status_code=404, detail="Pedido no encontrado")
    if pedido.estado != PedidoEstado.PENDIENTE:
        raise HTTPException(status_code=400, detail="Solo pedidos pendientes pueden aceptarse")

    pedido.estado = PedidoEstado.ACEPTADO
    session.add(pedido)
    session.commit()
    return {"status": "ok", "estado": pedido.estado}


@router.patch("/{pedido_id}/rechazar")
def rechazar_pedido(
    pedido_id: int, session: Session = Depends(get_session), usuario=Depends(get_current_user)
):
    negocio = get_negocio_del_usuario(session, usuario)
    pedido = session.get(Pedido, pedido_id)

    if not pedido or pedido.negocio_id != negocio.id:
        raise HTTPException(status_code=404, detail="Pedido no encontrado")
    if pedido.estado != PedidoEstado.PENDIENTE:
        raise HTTPException(status_code=400, detail="Solo pedidos pendientes pueden rechazarse")

    pedido.estado = PedidoEstado.RECHAZADO
    session.add(pedido)
    session.commit()
    return {"status": "ok", "estado": pedido.estado}


@router.patch("/{pedido_id}/progreso")
def marcar_en_progreso(
    pedido_id: int, session: Session = Depends(get_session), usuario=Depends(get_current_user)
):
    negocio = get_negocio_del_usuario(session, usuario)
    pedido = session.get(Pedido, pedido_id)

    if not pedido or pedido.negocio_id != negocio.id:
        raise HTTPException(status_code=404, detail="Pedido no encontrado")
    if pedido.estado != PedidoEstado.ACEPTADO:
        raise HTTPException(
            status_code=400, detail="Solo pedidos aceptados pueden pasar a progreso"
        )

    pedido.estado = PedidoEstado.EN_PROGRESO
    session.add(pedido)
    session.commit()
    return {"status": "ok", "estado": pedido.estado}


@router.patch("/{pedido_id}/finalizar")
def finalizar_pedido(
    pedido_id: int, session: Session = Depends(get_session), usuario=Depends(get_current_user)
):
    negocio = get_negocio_del_usuario(session, usuario)
    pedido = session.get(Pedido, pedido_id)

    if not pedido or pedido.negocio_id != negocio.id:
        raise HTTPException(status_code=404, detail="Pedido no encontrado")
    if pedido.estado != PedidoEstado.EN_PROGRESO:
        raise HTTPException(status_code=400, detail="Solo pedidos en progreso pueden finalizarse")

    pedido.estado = PedidoEstado.FINALIZADO
    session.add(pedido)
    session.commit()
    return {"status": "ok", "estado": pedido.estado}
