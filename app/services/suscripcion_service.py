"""
Service layer para manejo de suscripciones.
Incluye lógica de negocio y integración con Mercado Pago.
"""
import hmac
import hashlib
import logging
import requests
from datetime import datetime, timezone, timedelta
from typing import Optional
from urllib.parse import quote

from sqlmodel import Session, select

from app.models.models import Subscription, Usuario, SubscriptionStatus
from app.core.config import settings

logger = logging.getLogger(__name__)

TRIAL_DAYS = 14
MP_ACCESS_TOKEN = settings.MP_ACCESS_TOKEN
MP_WEBHOOK_SECRET = getattr(settings, 'MP_WEBHOOK_SECRET', None)


# === Funciones de integración con Mercado Pago ===

def validar_firma_webhook(x_signature: str, x_request_id: str, data_id: str) -> bool:
    """
    Valida la firma HMAC SHA256 del webhook de Mercado Pago.
    """
    if not MP_WEBHOOK_SECRET:
        logger.warning("MP_WEBHOOK_SECRET no configurado, omitiendo validación de firma")
        return True
    
    try:
        parts = dict(part.split("=", 1) for part in x_signature.split(","))
        ts = parts.get("ts")
        v1 = parts.get("v1")
        
        if not ts or not v1:
            logger.error("x-signature malformada: falta ts o v1")
            return False
        
        manifest = f"id:{data_id};request-id:{x_request_id};ts:{ts};"
        
        signature = hmac.new(
            MP_WEBHOOK_SECRET.encode(),
            manifest.encode(),
            hashlib.sha256
        ).hexdigest()
        
        if v1 and hmac.compare_digest(signature, v1):
            return True
        else:
            logger.warning(f"Firma inválida. Esperada: {signature[:16]}..., Recibida: {v1[:16] if v1 else 'None'}...")
            return False
            
    except Exception as e:
        logger.error(f"Error validando firma webhook: {e}")
        return False


def obtener_suscripcion_mp(mp_subscription_id: str) -> dict | None:
    """Obtiene los datos de una suscripción desde la API de Mercado Pago."""
    url = f"https://api.mercadopago.com/preapproval/{mp_subscription_id}"
    headers = {"Authorization": f"Bearer {MP_ACCESS_TOKEN}"}
    
    try:
        res = requests.get(url, headers=headers)
        res.raise_for_status()
        return res.json()
    except requests.RequestException as e:
        logger.error(f"Error obteniendo suscripción {mp_subscription_id}: {e}")
        return None


def buscar_suscripcion_por_email(email: str) -> dict | None:
    """Busca suscripciones activas de un usuario por email."""
    url = "https://api.mercadopago.com/preapproval/search"
    headers = {"Authorization": f"Bearer {MP_ACCESS_TOKEN}"}
    params = {"payer_email": email, "status": "authorized"}
    
    try:
        res = requests.get(url, headers=headers, params=params)
        res.raise_for_status()
        data = res.json()
        results = data.get("results", [])
        return results[0] if results else None
    except requests.RequestException as e:
        logger.error(f"Error buscando suscripción para {email}: {e}")
        return None


def obtener_checkout_url(external_reference: str, payer_email: str) -> str:
    """
    Genera una URL de checkout de Mercado Pago para suscripción.
    """
    plan_id = getattr(settings, 'MP_PLAN_ID', None)
    
    if not plan_id:
        logger.error("MP_PLAN_ID no configurado")
        return ""
    
    checkout_url = (
        f"https://www.mercadopago.com.ar/subscriptions/checkout"
        f"?preapproval_plan_id={plan_id}"
        f"&external_reference={quote(external_reference)}"
        f"&payer_email={quote(payer_email)}"
    )
    
    return checkout_url


# === Funciones de lógica de negocio ===


def obtener_suscripcion_usuario(session: Session, usuario_id: int) -> Optional[Subscription]:
    """Obtiene la suscripción de un usuario."""
    return session.exec(
        select(Subscription).where(Subscription.usuario_id == usuario_id)
    ).first()


def tiene_suscripcion_activa(session: Session, usuario_id: int) -> bool:
    """Verifica si el usuario tiene una suscripción activa."""
    suscripcion = session.exec(
        select(Subscription).where(
            Subscription.usuario_id == usuario_id,
            Subscription.status.in_([SubscriptionStatus.AUTHORIZED, SubscriptionStatus.ACTIVE])
        )
    ).first()
    return suscripcion is not None


def crear_suscripcion_testing(session: Session, usuario: Usuario) -> Subscription:
    """
    Crea una suscripción de prueba para desarrollo.
    Solo usar en ENVIRONMENT=development.
    """
    if settings.ENVIRONMENT != "development":
        raise ValueError("Suscripciones de testing solo permitidas en development")
    
    suscripcion = Subscription(
        usuario_id=usuario.id,
        mp_subscription_id=f"TEST_SUBSCRIPTION_{usuario.id}_{datetime.now().timestamp()}",
        mp_plan_id="TEST_PLAN",
        status=SubscriptionStatus.AUTHORIZED,
        start_date=datetime.now(timezone.utc),
        amount=0.0,
        currency="ARS",
        frequency=1,
        frequency_type="months"
    )
    
    session.add(suscripcion)
    
    usuario.es_premium = True
    session.add(usuario)
    
    session.commit()
    session.refresh(suscripcion)
    
    logger.info(f"Suscripción de testing creada para usuario {usuario.id}")
    return suscripcion


def crear_suscripcion_desde_mp(session: Session, mp_data: dict) -> Optional[Subscription]:
    """
    Crea una nueva suscripción en DB a partir de datos de Mercado Pago.
    
    Returns:
        Subscription si se creó correctamente, None si no se encontró el usuario
    """
    external_ref = mp_data.get("external_reference")
    payer_email = mp_data.get("payer_email")
    
    usuario = _buscar_usuario(session, external_ref, payer_email)
    if not usuario:
        logger.error(f"Usuario no encontrado: external_ref={external_ref}, email={payer_email}")
        return None
    
    suscripcion_existente = obtener_suscripcion_usuario(session, usuario.id)
    
    if suscripcion_existente:
        suscripcion_existente.mp_subscription_id = mp_data["id"]
        actualizar_suscripcion(suscripcion_existente, mp_data)
        logger.info(f"Suscripción existente actualizada para usuario {usuario.id}")
        return suscripcion_existente
    
    suscripcion = _construir_suscripcion(usuario.id, mp_data)
    session.add(suscripcion)
    
    logger.info(f"Nueva suscripción creada para usuario {usuario.id}")
    return suscripcion


def actualizar_suscripcion(suscripcion: Subscription, mp_data: dict) -> None:
    """Actualiza una suscripción existente con datos de Mercado Pago."""
    
    nuevo_status = mp_data.get("status")
    if nuevo_status:
        try:
            suscripcion.status = SubscriptionStatus(nuevo_status)
        except ValueError:
            logger.warning(f"Status desconocido de MP: {nuevo_status}")
    
    suscripcion.updated_at = datetime.now(timezone.utc)
    
    next_payment = mp_data.get("next_payment_date")
    if next_payment:
        suscripcion.next_payment_date = _parse_fecha_mp(next_payment)
    
    if suscripcion.status in [SubscriptionStatus.CANCELLED, SubscriptionStatus.EXPIRED]:
        suscripcion.end_date = datetime.now(timezone.utc)
    
    auto_recurring = mp_data.get("auto_recurring", {})
    if auto_recurring.get("transaction_amount"):
        suscripcion.amount = float(auto_recurring["transaction_amount"])
    
    if mp_data.get("preapproval_plan_id"):
        suscripcion.mp_plan_id = mp_data["preapproval_plan_id"]


def actualizar_estado_premium(session: Session, suscripcion: Subscription) -> None:
    """Actualiza el flag es_premium del usuario según el estado de la suscripción."""
    if not suscripcion.usuario:
        usuario = session.get(Usuario, suscripcion.usuario_id)
        if not usuario:
            return
    else:
        usuario = suscripcion.usuario
    
    es_activa = suscripcion.status in [SubscriptionStatus.AUTHORIZED, SubscriptionStatus.ACTIVE]
    
    if usuario.es_premium != es_activa:
        usuario.es_premium = es_activa
        session.add(usuario)
        logger.info(f"Usuario {usuario.id} premium={es_activa}")


def procesar_webhook_suscripcion(session: Session, mp_data: dict) -> Subscription:
    """
    Procesa un webhook de suscripción de Mercado Pago.
    Crea o actualiza la suscripción según corresponda.
    
    Returns:
        La suscripción procesada
    
    Raises:
        ValueError si no se puede encontrar/crear la suscripción
    """
    mp_id = mp_data.get("id")
    
    suscripcion = session.exec(
        select(Subscription).where(Subscription.mp_subscription_id == mp_id)
    ).first()
    
    if not suscripcion:
        suscripcion = crear_suscripcion_desde_mp(session, mp_data)
        if not suscripcion:
            raise ValueError(f"No se pudo crear suscripción para MP ID {mp_id}")
    else:
        actualizar_suscripcion(suscripcion, mp_data)
    
    actualizar_estado_premium(session, suscripcion)
    
    session.add(suscripcion)
    session.commit()
    session.refresh(suscripcion)
    
    return suscripcion


# === Funciones privadas ===

def _buscar_usuario(session: Session, external_ref: str | None, email: str | None) -> Optional[Usuario]:
    """Busca un usuario por external_reference (ID) o por email."""
    usuario = None
    
    if external_ref and external_ref.isdigit():
        usuario = session.get(Usuario, int(external_ref))
    
    if not usuario and email:
        usuario = session.exec(
            select(Usuario).where(Usuario.email == email)
        ).first()
    
    return usuario


def _construir_suscripcion(usuario_id: int, mp_data: dict) -> Subscription:
    """Construye un objeto Subscription a partir de datos de MP."""
    auto_recurring = mp_data.get("auto_recurring", {})
    
    start_date_str = mp_data.get("date_created") or auto_recurring.get("start_date")
    start_date = _parse_fecha_mp(start_date_str) or datetime.now(timezone.utc)
    
    amount = auto_recurring.get("transaction_amount", 0)
    if amount is None:
        amount = 0
    
    status_str = mp_data.get("status", "authorized")
    try:
        status = SubscriptionStatus(status_str)
    except ValueError:
        status = SubscriptionStatus.AUTHORIZED
    
    free_trial = auto_recurring.get("free_trial")
    is_trial = free_trial is not None or float(amount) == 0
    
    trial_end_date = None
    if is_trial:
        trial_days = TRIAL_DAYS
        if free_trial and isinstance(free_trial, dict):
            trial_days = free_trial.get("frequency", TRIAL_DAYS)
        trial_end_date = start_date + timedelta(days=trial_days)
        logger.info(f"Usuario {usuario_id} en período de prueba de {trial_days} días hasta {trial_end_date}")
    
    suscripcion = Subscription(
        usuario_id=usuario_id,
        mp_subscription_id=mp_data["id"],
        mp_plan_id=mp_data.get("preapproval_plan_id"),
        status=status,
        start_date=start_date,
        amount=float(amount),
        currency=auto_recurring.get("currency_id", "ARS"),
        frequency=auto_recurring.get("frequency", 1),
        frequency_type=auto_recurring.get("frequency_type", "months"),
    )
    
    if trial_end_date:
        suscripcion.next_payment_date = trial_end_date
    elif mp_data.get("next_payment_date"):
        suscripcion.next_payment_date = _parse_fecha_mp(mp_data["next_payment_date"])
    
    return suscripcion


def _parse_fecha_mp(fecha_str: str | None) -> Optional[datetime]:
    """Parsea una fecha ISO de Mercado Pago."""
    if not fecha_str:
        return None
    try:
        return datetime.fromisoformat(fecha_str.replace("Z", "+00:00"))
    except ValueError:
        return None
