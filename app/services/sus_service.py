import hmac
import hashlib
import logging
import requests
from app.core.config import settings

logger = logging.getLogger(__name__)

MP_ACCESS_TOKEN = settings.MP_ACCESS_TOKEN
MP_WEBHOOK_SECRET = settings.MP_WEBHOOK_SECRET


def validar_firma_webhook(x_signature: str, x_request_id: str, data_id: str) -> bool:
    """
    Valida la firma HMAC SHA256 del webhook de Mercado Pago.
    
    Args:
        x_signature: Header 'x-signature' del request (formato: ts=...,v1=...)
        x_request_id: Header 'x-request-id' del request
        data_id: El 'data.id' del payload del webhook
    
    Returns:
        True si la firma es válida, False en caso contrario
    """
    if not MP_WEBHOOK_SECRET:
        logger.warning("MP_WEBHOOK_SECRET no configurado, omitiendo validación de firma")
        return True  # En desarrollo sin secret, permitir
    
    try:
        # Parsear x-signature: "ts=123456789,v1=abc123..."
        parts = dict(part.split("=", 1) for part in x_signature.split(","))
        ts = parts.get("ts")
        v1 = parts.get("v1")
        
        if not ts or not v1:
            logger.error("x-signature malformada: falta ts o v1")
            return False
        
        # Construir el manifest según documentación de MP
        # Formato: id:{data_id};request-id:{x_request_id};ts:{ts};
        manifest = f"id:{data_id};request-id:{x_request_id};ts:{ts};"
        
        # Calcular HMAC SHA256
        signature = hmac.new(
            MP_WEBHOOK_SECRET.encode(),
            manifest.encode(),
            hashlib.sha256
        ).hexdigest()
        
        # Comparar de forma segura
        if v1 and hmac.compare_digest(signature, v1):
            return True
        else:
            logger.warning(f"Firma inválida. Esperada: {signature[:16]}..., Recibida: {v1[:16] if v1 else 'None'}...")
            return False
            
    except Exception as e:
        logger.error(f"Error validando firma webhook: {e}")
        return False


def obtener_suscripcion_mp(mp_subscription_id: str) -> dict | None:
    """
    Obtiene los datos de una suscripción desde la API de Mercado Pago.
    """
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
    """
    Busca suscripciones activas de un usuario por email.
    Útil para sincronizar suscripciones existentes.
    """
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
