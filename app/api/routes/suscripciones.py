from fastapi import APIRouter, Depends, Request, HTTPException
from sqlmodel import Session, select
from app.api.deps import get_current_user , get_session
from app.services.sus_service import crear_suscripcion_mp, obtener_suscripcion_mp

from datetime import datetime, timezone
from app.models.models import Subscription
from app.schemas.suscripcion import SubscriptionRead
from app.core.config import settings

router = APIRouter(prefix="/api", tags=["Suscripciones"])

@router.post("/suscripciones")
def crear_suscripcion(usuario=Depends(get_current_user), session: Session = Depends(get_session)):
    mp_data = crear_suscripcion_mp(
        payer_email=usuario.email,
        plan_id=settings.MP_PLAN_ID,
        external_reference=str(usuario.id)
    )

    suscripcion = Subscription(
        usuario_id=usuario.id,
        mp_subscription_id=mp_data["id"],
        mp_plan_id=mp_data.get("preapproval_plan_id"),
        status=mp_data["status"],
        start_date=datetime.fromisoformat(mp_data["auto_recurring"]["start_date"].replace("Z", "")),
        amount=mp_data["auto_recurring"]["transaction_amount"],
        currency=mp_data["auto_recurring"]["currency_id"],
        frequency=mp_data["auto_recurring"]["frequency"],
        frequency_type=mp_data["auto_recurring"]["frequency_type"]
    )

    session.add(suscripcion)
    session.commit()
    session.refresh(suscripcion)
    return suscripcion

@router.get("/suscripcion", response_model=SubscriptionRead | None)
def get_mi_suscripcion(
    session: Session = Depends(get_session),
    usuario=Depends(get_current_user),
):
    stmt = select(Subscription).where(Subscription.usuario_id == usuario.id)
    suscripcion = session.exec(stmt).first()
    return suscripcion

@router.post("/suscripciones/cancelar", deprecated=True)
def cancelar_suscripcion(usuario=Depends(get_current_user), session: Session = Depends(get_session)):

    raise HTTPException(410, "Deprecado")

    # Eliminado código en desuso


@router.post("/webhooks/mercadopago")
async def webhook_mp(request: Request, session: Session = Depends(get_session)):
    data = await request.json()

    topic = data.get("type") or data.get("topic")
    mp_id = data.get("data", {}).get("id")

    if not mp_id:
        return {"status": "ignored"}

    # Solo nos importa suscripciones
    if topic not in ["subscription_preapproval", "subscription_authorized_payment"]:
        return {"status": "ignored"}

    # Obtener info real desde MP
    suscripcion_mp = obtener_suscripcion_mp(mp_id)

    # Buscar en DB
    suscripcion = session.exec(
        select(Subscription).where(Subscription.mp_subscription_id == mp_id)
    ).first()

    if not suscripcion:
        return {"status": "not_found"}

    # Actualizar campos
    suscripcion.status = suscripcion_mp["status"]
    suscripcion.updated_at = datetime.now(timezone.utc)

    if "next_payment_date" in suscripcion_mp:
        suscripcion.next_payment_date = datetime.fromisoformat(
            suscripcion_mp["next_payment_date"].replace("Z", "")
        )

    if suscripcion.status in ["cancelled", "expired"]:
        suscripcion.end_date = datetime.now(timezone.utc)
        suscripcion.usuario.es_premium = False

    if suscripcion.status == "active":
        suscripcion.usuario.es_premium = True

    session.add(suscripcion)
    session.commit()

    return {"status": "ok"}