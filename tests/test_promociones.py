import pytest
from app.services.promocion_service import PromocionService
from app.models.models import Promocion, PromocionTipo

def test_validar_cupon_porcentaje(db_session):
    # 1. PREPARAR (Set up): Creamos una promo en la DB de prueba
    service = PromocionService(db_session)
    promo = Promocion(
        negocio_id=1,
        nombre="Descuento 10%",
        codigo="DIEZ",
        tipo=PromocionTipo.PORCENTAJE,
        valor=10.0,
        activo=True
    )
    db_session.add(promo)
    db_session.commit()

    # 2. ACTUAR (Act): Llamamos a la función que queremos probar
    resultado = service.validar_cupon(
        codigo="DIEZ",
        negocio_id=1,
        carrito_total=1000,
        items=[]
    )

    # 3. AFIRMAR (Assert): Verificamos que el resultado sea el esperado
    assert resultado["descuento"] == 100.0  # El 10% de 1000
    assert resultado["promocion"].codigo == "DIEZ"