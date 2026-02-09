import pytest
from app.models.models import Negocio, Usuario, Producto, Categoria, Promocion, PromocionTipo

@pytest.fixture
def setup_negocio(session):
    # Crear usuario
    usuario = Usuario(nombre="Owner", email="owner@test.com", password_hash="hash")
    session.add(usuario)
    session.flush()
    
    # Crear negocio
    negocio = Negocio(
        usuario_id=usuario.id,
        nombre="Test Shop",
        slug="test-shop",
        activo=True,
        metodos_pago=["efectivo"],
        tipos_entrega=["delivery"]
    )
    session.add(negocio)
    session.flush()
    
    # Crear categoria
    categoria = Categoria(negocio_id=negocio.id, nombre="Pizza", activo=True)
    session.add(categoria)
    session.flush()
    
    # Crear producto
    producto = Producto(
        negocio_id=negocio.id,
        categoria_id=categoria.id,
        nombre="Pizza Muzza",
        precio=1000,
        activo=True,
        stock=True
    )
    session.add(producto)
    session.commit()
    return negocio, producto

def test_get_negocio_publico(client, setup_negocio):
    negocio, _ = setup_negocio
    response = client.get(f"/public/{negocio.slug}")
    assert response.status_code == 200
    assert response.json()["nombre"] == "Test Shop"

def test_listar_productos_publico(client, setup_negocio):
    negocio, producto = setup_negocio
    response = client.get(f"/public/{negocio.slug}/productos")
    assert response.status_code == 200
    data = response.json()
    assert len(data) > 0
    assert data[0]["nombre"] == "Pizza Muzza"

def test_validar_cupon_publico(client, session, setup_negocio):
    negocio, producto = setup_negocio
    
    # Crear cupón
    promo = Promocion(
        negocio_id=negocio.id,
        nombre="Promo 10%",
        codigo="PROMO10",
        tipo=PromocionTipo.PORCENTAJE,
        valor=10.0,
        activo=True
    )
    session.add(promo)
    session.commit()
    
    response = client.post(
        f"/public/{negocio.slug}/validate-coupon",
        json={
            "codigo": "PROMO10",
            "items": [
                {"producto_id": producto.id, "cantidad": 2}
            ]
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["descuento"] == 200.0 # 10% de 2000
    assert data["promocion"]["codigo"] == "PROMO10"
