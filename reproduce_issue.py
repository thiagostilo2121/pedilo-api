import sys
import os
from datetime import datetime, timezone

# Add the parent directory to sys.path to import app modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sqlmodel import Session, create_engine, select
from app.models.models import Negocio, Promocion, PromocionTipo, Usuario
from app.api.routes.public import validar_cupon_endpoint, CouponValidationRequest
from app.schemas.pedido import PedidoItemCreate

# Setup in-memory DB for testing
from app.db.database import engine # Ensure this imports your actual engine or create a test one
# For reproduction, we might need a real connection if models depend on specific DB features, 
# but let's try to mock the session or use a test DB. 
# Assuming sqlite is okay or we can use the existing dev DB if credentials allow.
# For safety, let's look at how to get a session.

# Create a dummy session mock or use a real one if possible. 
# Better: Just inspect the code logic via mental model or use a small script that tries to serialize the response.

def test_serialization():
    from fastapi.encoders import jsonable_encoder
    
    # Create a dummy Promocion object (simulating DB object)
    promo = Promocion(
        id=1,
        negocio_id=1,
        nombre="Test Promo",
        codigo="TEST",
        tipo=PromocionTipo.PORCENTAJE,
        valor=10.0,
        reglas={},
        fecha_inicio=datetime.now(timezone.utc),
        activo=True
    )
    
    # Mock response dictionary
    response = {
        "valido": True,
        "descuento": 100.0,
        "promocion": promo, # This is the SQLModel object
        "mensaje": "Cupón TEST aplicado"
    }
    
    print("Attempting serialization...")
    try:
        json_output = jsonable_encoder(response)
        print("Serialization SUCCESS")
        print(json_output)
    except Exception as e:
        print(f"Serialization FAILED: {e}")

if __name__ == "__main__":
    test_serialization()
