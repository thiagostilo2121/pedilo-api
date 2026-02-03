import requests
from app.core.config import settings

MP_ACCESS_TOKEN = settings.MP_ACCESS_TOKEN

def crear_suscripcion_mp(payer_email: str, plan_id: str, external_reference: str):
    url = "https://api.mercadopago.com/preapproval"
    headers = {
        "Authorization": f"Bearer {MP_ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {
        "preapproval_plan_id": plan_id,
        "payer_email": payer_email,
        "reason": "Suscripción Pedilo",
        "external_reference": external_reference,
        "status": "authorized"
    }

    res = requests.post(url, json=payload, headers=headers)
    res.raise_for_status()
    return res.json()

def obtener_suscripcion_mp(mp_subscription_id: str):
    url = f"https://api.mercadopago.com/preapproval/{mp_subscription_id}"
    headers = {
        "Authorization": f"Bearer {MP_ACCESS_TOKEN}"
    }
    res = requests.get(url, headers=headers)
    res.raise_for_status()
    return res.json()

