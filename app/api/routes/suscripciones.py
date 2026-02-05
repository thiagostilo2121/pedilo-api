"""
Rutas HTTP para manejo de suscripciones.
La lógica de negocio está en suscripcion_service.py.
"""
import logging

from fastapi import APIRouter, Depends, Request, HTTPException
from sqlmodel import Session

from app.api.deps import get_current_user, get_session
from app.schemas.suscripcion import SubscriptionRead
from app.services.suscripcion_service import (
    obtener_suscripcion_usuario,
    tiene_suscripcion_activa,
    crear_suscripcion_testing,
    procesar_webhook_suscripcion,
    obtener_suscripcion_mp,
    obtener_checkout_url,
    validar_firma_webhook,
)
from app.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["Suscripciones"])


@router.post("/suscripciones", deprecated=True)
def crear_suscripcion(usuario=Depends(get_current_user)):
    """
    DEPRECADO: Las suscripciones se crean desde el checkout de Mercado Pago.
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
    return obtener_suscripcion_usuario(session, usuario.id)


@router.get("/suscripcion/checkout-url")
def get_checkout_url_endpoint(
    usuario=Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """
    Genera la URL de checkout de Mercado Pago con el external_reference del usuario.
    """
    if tiene_suscripcion_activa(session, usuario.id):
        return {
            "url": None,
            "has_subscription": True,
            "message": "Ya tenés una suscripción activa"
        }
    
    if settings.ENVIRONMENT == "development" and getattr(settings, 'TESTING_USER_ID', None) == usuario.id:
        crear_suscripcion_testing(session, usuario)
        logger.info(f"Testing: Premium habilitado para usuario {usuario.id}")
        return {
            "url": None,
            "has_subscription": True,
            "message": "Testing: Premium habilitado automáticamente"
        }
    
    checkout_url = obtener_checkout_url(
        external_reference=str(usuario.id),
        payer_email=usuario.email
    )
    
    return {
        "url": checkout_url,
        "has_subscription": False
    }


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
    """
    x_signature = request.headers.get("x-signature", "")
    x_request_id = request.headers.get("x-request-id", "")
    
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
    
    if not validar_firma_webhook(x_signature, x_request_id, str(mp_id)):
        logger.warning(f"Firma inválida para webhook {mp_id}")
        raise HTTPException(401, "Invalid signature")
    
    if topic not in ["subscription_preapproval", "subscription_authorized_payment"]:
        return {"status": "ignored", "reason": "topic_not_handled"}
    
    if str(mp_id) in ["123456", "12345", "1234567890"]:
        logger.info(f"Notificación de prueba detectada (id={mp_id})")
        return {"status": "ok", "test": True, "message": "Test notification received"}
    
    suscripcion_mp = obtener_suscripcion_mp(mp_id)
    if not suscripcion_mp:
        logger.warning(f"No se pudo obtener suscripción {mp_id} de MP")
        return {"status": "ignored", "reason": "subscription_not_found_in_mp"}
    
    try:
        suscripcion = procesar_webhook_suscripcion(session, suscripcion_mp)
        logger.info(f"Suscripción {mp_id} procesada: status={suscripcion.status}")
        return {"status": "ok"}
    except ValueError as e:
        logger.error(f"Error procesando webhook: {e}")
        return {"status": "error", "reason": str(e)}