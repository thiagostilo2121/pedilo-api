import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Request, HTTPException
from sqlmodel import Session, select

from app.api.deps import get_current_user, get_session
from app.models.models import Subscription, Usuario
from app.schemas.suscripcion import SubscriptionRead
from app.services.sus_service import (
    obtener_suscripcion_mp,
    validar_firma_webhook,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["Suscripciones"])


@router.post("/suscripciones", deprecated=True)
def crear_suscripcion(usuario=Depends(get_current_user)):
    """
    DEPRECADO: Las suscripciones se crean desde el checkout de Mercado Pago.
    El usuario debe usar el link de suscripción del panel de MP.
    """
    raise HTTPException(
        status_code=410,
        detail="Este endpoint está deprecado. Usa el link de suscripción de Mercado Pago."
    )


@router.get("/suscripcion", response_model=SubscriptionRead | None)
def get_mi_suscripcion(
    session: Session = Depends(get_session),
    usuario=Depends(get_current_user),
):
    """Obtiene la suscripción del usuario autenticado."""
    stmt = select(Subscription).where(Subscription.usuario_id == usuario.id)
    suscripcion = session.exec(stmt).first()
    return suscripcion


@router.post("/suscripciones/cancelar", deprecated=True)
def cancelar_suscripcion():
    """
    DEPRECADO: El usuario gestiona su suscripción directamente desde Mercado Pago.
    """
    raise HTTPException(
        status_code=410,
        detail="Gestiona tu suscripción desde Mercado Pago."
    )


@router.post("/webhooks/mercadopago")
async def webhook_mp(request: Request, session: Session = Depends(get_session)):
    """
    Webhook para recibir notificaciones de Mercado Pago sobre suscripciones.
    
    Maneja eventos:
    - subscription_preapproval: Cambios en estado de suscripción
    - subscription_authorized_payment: Pagos autorizados
    """
    # Obtener headers para validación
    x_signature = request.headers.get("x-signature", "")
    x_request_id = request.headers.get("x-request-id", "")
    
    # Parsear payload
    try:
        data = await request.json()
    except Exception:
        logger.error("Error parseando JSON del webhook")
        raise HTTPException(400, "Invalid JSON")
    
    topic = data.get("type") or data.get("topic")
    mp_id = data.get("data", {}).get("id")
    
    logger.info(f"Webhook recibido: topic={topic}, id={mp_id}")
    
    if not mp_id:
        return {"status": "ignored", "reason": "no_id"}
    
    # Validar firma HMAC
    if not validar_firma_webhook(x_signature, x_request_id, str(mp_id)):
        logger.warning(f"Firma inválida para webhook {mp_id}")
        raise HTTPException(401, "Invalid signature")
    
    # Solo procesar eventos de suscripción
    if topic not in ["subscription_preapproval", "subscription_authorized_payment"]:
        return {"status": "ignored", "reason": "topic_not_handled"}
    
    # Obtener datos completos de la suscripción desde MP
    suscripcion_mp = obtener_suscripcion_mp(mp_id)
    if not suscripcion_mp:
        logger.error(f"No se pudo obtener suscripción {mp_id} de MP")
        return {"status": "error", "reason": "mp_fetch_failed"}
    
    # Buscar suscripción existente en nuestra DB
    suscripcion = session.exec(
        select(Subscription).where(Subscription.mp_subscription_id == mp_id)
    ).first()
    
    if not suscripcion:
        # Nueva suscripción: crear registro
        suscripcion = _crear_suscripcion_desde_mp(session, suscripcion_mp)
        if not suscripcion:
            return {"status": "error", "reason": "user_not_found"}
        logger.info(f"Nueva suscripción creada para usuario {suscripcion.usuario_id}")
    else:
        # Actualizar suscripción existente
        _actualizar_suscripcion(suscripcion, suscripcion_mp)
        logger.info(f"Suscripción {mp_id} actualizada: status={suscripcion.status}")
    
    # Actualizar estado premium del usuario
    _actualizar_estado_premium(suscripcion)
    
    session.add(suscripcion)
    session.commit()
    
    return {"status": "ok"}


def _crear_suscripcion_desde_mp(session: Session, mp_data: dict) -> Subscription | None:
    """Crea una nueva suscripción en DB a partir de datos de MP."""
    
    # Buscar usuario por external_reference (user_id) o por email
    external_ref = mp_data.get("external_reference")
    payer_email = mp_data.get("payer_email")
    
    usuario = None
    
    if external_ref and external_ref.isdigit():
        usuario = session.get(Usuario, int(external_ref))
    
    if not usuario and payer_email:
        usuario = session.exec(
            select(Usuario).where(Usuario.email == payer_email)
        ).first()
    
    if not usuario:
        logger.error(f"Usuario no encontrado: external_ref={external_ref}, email={payer_email}")
        return None
    
    # Verificar que no tenga ya una suscripción
    suscripcion_existente = session.exec(
        select(Subscription).where(Subscription.usuario_id == usuario.id)
    ).first()
    
    if suscripcion_existente:
        # Actualizar la existente con el nuevo mp_subscription_id
        suscripcion_existente.mp_subscription_id = mp_data["id"]
        _actualizar_suscripcion(suscripcion_existente, mp_data)
        return suscripcion_existente
    
    # Crear nueva suscripción
    auto_recurring = mp_data.get("auto_recurring", {})
    
    start_date_str = mp_data.get("date_created") or auto_recurring.get("start_date")
    start_date = datetime.now(timezone.utc)
    if start_date_str:
        try:
            start_date = datetime.fromisoformat(start_date_str.replace("Z", "+00:00"))
        except ValueError:
            pass
    
    suscripcion = Subscription(
        usuario_id=usuario.id,
        mp_subscription_id=mp_data["id"],
        mp_plan_id=mp_data.get("preapproval_plan_id"),
        status=mp_data.get("status", "authorized"),
        start_date=start_date,
        amount=auto_recurring.get("transaction_amount", 0),
        currency=auto_recurring.get("currency_id", "ARS"),
        frequency=auto_recurring.get("frequency", 1),
        frequency_type=auto_recurring.get("frequency_type", "months"),
    )
    
    if "next_payment_date" in mp_data:
        try:
            suscripcion.next_payment_date = datetime.fromisoformat(
                mp_data["next_payment_date"].replace("Z", "+00:00")
            )
        except ValueError:
            pass
    
    session.add(suscripcion)
    return suscripcion


def _actualizar_suscripcion(suscripcion: Subscription, mp_data: dict) -> None:
    """Actualiza una suscripción existente con datos de MP."""
    suscripcion.status = mp_data.get("status", suscripcion.status)
    suscripcion.updated_at = datetime.now(timezone.utc)
    
    if "next_payment_date" in mp_data and mp_data["next_payment_date"]:
        try:
            suscripcion.next_payment_date = datetime.fromisoformat(
                mp_data["next_payment_date"].replace("Z", "+00:00")
            )
        except ValueError:
            pass
    
    if suscripcion.status in ["cancelled", "expired"]:
        suscripcion.end_date = datetime.now(timezone.utc)


def _actualizar_estado_premium(suscripcion: Subscription) -> None:
    """Actualiza el flag es_premium del usuario según el estado de la suscripción."""
    if suscripcion.usuario:
        # Activo solo si la suscripción está autorizada o activa
        suscripcion.usuario.es_premium = suscripcion.status in ["authorized", "active"]