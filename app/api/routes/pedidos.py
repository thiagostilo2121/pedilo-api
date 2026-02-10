from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import selectinload
from sqlmodel import Session, select, desc

from app.api.deps import get_current_user, get_negocio_del_usuario, get_session, PaginationParams
from app.models.models import Pedido, PedidoEstado
from app.schemas.pedido import PedidoRead

router = APIRouter(prefix="/api/pedidos", tags=["Pedidos"])


@router.get("/", response_model=list[PedidoRead])
def listar_pedidos(
    session: Session = Depends(get_session),
    usuario=Depends(get_current_user),
    pagination: PaginationParams = Depends(),
):
    negocio = get_negocio_del_usuario(session, usuario)
    pedidos = session.exec(
        select(Pedido)
        .where(Pedido.negocio_id == negocio.id)
        .options(selectinload(Pedido.items))
        .order_by(desc(Pedido.creado_en))
        .offset(pagination.skip)
        .limit(pagination.limit)
    ).all()
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
