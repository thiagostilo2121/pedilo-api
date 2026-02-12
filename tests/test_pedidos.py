import pytest
from app.models.models import Negocio, Usuario, Pedido, PedidoEstado, TipoNegocio
from sqlmodel import select
from app.core.security import hash_password

def test_pedidos_pagination_ordering(client, session):
    # 1. Setup: Create User and Business
    usuario = Usuario(
        email="owner@example.com",
        password_hash=hash_password("password"),
        nombre="Owner",
        es_premium=True,
        activo=True
    )
    session.add(usuario)
    session.commit()
    session.refresh(usuario)

    negocio = Negocio(
        usuario_id=usuario.id,
        nombre="Test Business",
        slug="test-business",
        acepta_pedidos=True,
        activo=True
    )
    session.add(negocio)
    session.commit()
    session.refresh(negocio)

    # 2. Login
    login_response = client.post(
        "/api/auth/login",
        json={"email": "owner@example.com", "password": "password"}
    )
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 3. Create Orders to test pagination and ordering
    # We want to see if the default order pushes new pending orders off the first page
    # Default limit is 100.
    
    # Create 100 "old" finalized orders
    for i in range(100):
        o = Pedido(
            negocio_id=negocio.id,
            codigo=f"OLD-{i}",
            estado=PedidoEstado.FINALIZADO,
            total=1000,
            nombre_cliente=f"Cliente Old {i}"
        )
        session.add(o)
    
    session.commit() # Commit to ensure they have IDs and likely stored in order
    
    # Create 5 "new" pending orders
    pending_codes = []
    for i in range(5):
        code = f"NEW-{i}"
        pending_codes.append(code)
        o = Pedido(
            negocio_id=negocio.id,
            codigo=code,
            estado=PedidoEstado.PENDIENTE,
            total=2000,
            nombre_cliente=f"Cliente New {i}"
        )
        session.add(o)
    
    session.commit()

    # 4. Fetch Page 1 (limit 100)
    response = client.get("/api/pedidos/", headers=headers)
    assert response.status_code == 200
    orders = response.json()

    print(f"\nOrders returned on page 1: {len(orders)}")
    
    # If the API returns insertion order (oldest first), we get the 100 OLD orders
    # and NO NEW orders.
    returned_codes = {o["codigo"] for o in orders}
    
    # We expect this to FAIL if the bug exists (missing pending orders on dashboard)
    # The dashboard likely expects Newest First.
    
    found_new = False
    for code in pending_codes:
        if code in returned_codes:
            found_new = True
            break
            
    if not found_new:
        pytest.fail("No pending (new) orders found on page 1! API is likely returning oldest first.")
        
    # Also verify the first order is actually one of the new ones
    first_order_code = orders[0]["codigo"]
    assert first_order_code in pending_codes, f"Expected newest order first, but got {first_order_code}"


def _setup_user_negocio_token(client, session, **negocio_kwargs):
    """Helper to create user, negocio, and return (negocio, headers) with direct JWT."""
    from app.core.security import create_access_token

    usuario = Usuario(
        email="distri@example.com",
        password_hash=hash_password("password"),
        nombre="Distri Owner",
        es_premium=True,
        activo=True,
    )
    session.add(usuario)
    session.commit()
    session.refresh(usuario)

    defaults = {
        "usuario_id": usuario.id,
        "nombre": "Distribuidora Test",
        "slug": "distri-test",
        "acepta_pedidos": True,
        "activo": True,
        "metodos_pago": ["efectivo", "transferencia"],
        "tipos_entrega": ["delivery"],
    }
    defaults.update(negocio_kwargs)
    negocio = Negocio(**defaults)
    session.add(negocio)
    session.commit()
    session.refresh(negocio)

    token = create_access_token({"user_id": usuario.id})
    headers = {"Authorization": f"Bearer {token}"}
    return negocio, headers


def _create_producto(session, negocio_id, **kwargs):
    """Helper to create a Producto directly in DB."""
    from app.models.models import Producto
    defaults = {
        "negocio_id": negocio_id,
        "nombre": "Producto Test",
        "precio": 1000,
        "activo": True,
        "stock": True,
    }
    defaults.update(kwargs)
    p = Producto(**defaults)
    session.add(p)
    session.commit()
    session.refresh(p)
    return p


def test_pedido_minimo_rechazado(client, session):
    """Un pedido menor al mínimo del negocio debe ser rechazado."""
    negocio, _ = _setup_user_negocio_token(client, session, pedido_minimo=5000, tipo_negocio=TipoNegocio.DISTRIBUIDORA)
    producto = _create_producto(session, negocio.id, precio=1000)

    response = client.post(
        f"/public/{negocio.slug}/pedidos",
        json={
            "metodo_pago": "efectivo",
            "tipo_entrega": "delivery",
            "nombre_cliente": "Cliente Test",
            "items": [{"producto_id": producto.id, "cantidad": 3}],
        },
    )
    assert response.status_code == 400
    assert "pedido mínimo" in response.json()["detail"].lower()


def test_pedido_minimo_aceptado(client, session):
    """Un pedido que cumple el mínimo debe pasar."""
    negocio, _ = _setup_user_negocio_token(client, session, pedido_minimo=5000, tipo_negocio=TipoNegocio.DISTRIBUIDORA)
    producto = _create_producto(session, negocio.id, precio=1000)

    response = client.post(
        f"/public/{negocio.slug}/pedidos",
        json={
            "metodo_pago": "efectivo",
            "tipo_entrega": "delivery",
            "nombre_cliente": "Cliente Test",
            "items": [{"producto_id": producto.id, "cantidad": 6}],
        },
    )
    assert response.status_code == 200
    assert response.json()["total"] == 6000


def test_cantidad_minima_producto(client, session):
    """Pedir menos de la cantidad mínima de un producto debe fallar."""
    negocio, _ = _setup_user_negocio_token(client, session, tipo_negocio=TipoNegocio.DISTRIBUIDORA)
    producto = _create_producto(session, negocio.id, precio=1000, cantidad_minima=5)

    response = client.post(
        f"/public/{negocio.slug}/pedidos",
        json={
            "metodo_pago": "efectivo",
            "tipo_entrega": "delivery",
            "nombre_cliente": "Cliente Test",
            "items": [{"producto_id": producto.id, "cantidad": 3}],
        },
    )
    assert response.status_code == 400
    assert "cantidad mínima" in response.json()["detail"].lower()


def test_precio_mayorista(client, session):
    """Cuando la cantidad supera el umbral mayorista, se debe aplicar el precio mayorista."""
    negocio, _ = _setup_user_negocio_token(client, session, tipo_negocio=TipoNegocio.DISTRIBUIDORA)
    producto = _create_producto(
        session,
        negocio.id,
        precio=1000,
        precio_mayorista=800,
        cantidad_mayorista=10,
    )

    response = client.post(
        f"/public/{negocio.slug}/pedidos",
        json={
            "metodo_pago": "efectivo",
            "tipo_entrega": "delivery",
            "nombre_cliente": "Cliente Test",
            "items": [{"producto_id": producto.id, "cantidad": 10}],
        },
    )
    assert response.status_code == 200
    data = response.json()
    # 10 unidades * $800 = $8000
    assert data["total"] == 8000
    assert data["items"][0]["precio_unitario"] == 800


def test_filtro_pedidos_por_estado(client, session):
    """Filtrar pedidos por estado devuelve solo los del estado pedido."""
    negocio, headers = _setup_user_negocio_token(client, session)

    # Crear pedidos en distintos estados
    for i, estado in enumerate([PedidoEstado.PENDIENTE, PedidoEstado.ACEPTADO, PedidoEstado.FINALIZADO]):
        p = Pedido(
            negocio_id=negocio.id,
            codigo=f"FIL-{i}",
            estado=estado,
            total=1000,
            nombre_cliente=f"Cliente {i}",
        )
        session.add(p)
    session.commit()

    # Filtrar solo pendientes
    response = client.get("/api/pedidos/?estado=pendiente", headers=headers)
    assert response.status_code == 200
    orders = response.json()
    assert len(orders) == 1
    assert orders[0]["estado"] == "pendiente"


def test_busqueda_pedidos(client, session):
    """Buscar pedidos por código o nombre de cliente."""
    negocio, headers = _setup_user_negocio_token(client, session)

    p1 = Pedido(negocio_id=negocio.id, codigo="ABC123", estado=PedidoEstado.PENDIENTE, total=1000, nombre_cliente="Juan Perez")
    p2 = Pedido(negocio_id=negocio.id, codigo="XYZ789", estado=PedidoEstado.PENDIENTE, total=2000, nombre_cliente="Maria Lopez")
    session.add_all([p1, p2])
    session.commit()

    # Buscar por código
    response = client.get("/api/pedidos/?buscar=ABC", headers=headers)
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["codigo"] == "ABC123"

    # Buscar por nombre de cliente
    response = client.get("/api/pedidos/?buscar=Maria", headers=headers)
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["nombre_cliente"] == "Maria Lopez"


def test_direccion_entrega_y_notas(client, session):
    """Los campos de dirección y notas se guardan y devuelven correctamente."""
    negocio, _ = _setup_user_negocio_token(client, session)
    producto = _create_producto(session, negocio.id, precio=1000)

    response = client.post(
        f"/public/{negocio.slug}/pedidos",
        json={
            "metodo_pago": "efectivo",
            "tipo_entrega": "delivery",
            "nombre_cliente": "Cliente Test",
            "direccion_entrega": "Av. Siempre Viva 742",
            "notas": "Dejar en portería",
            "items": [{"producto_id": producto.id, "cantidad": 2}],
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["direccion_entrega"] == "Av. Siempre Viva 742"
    assert data["notas"] == "Dejar en portería"

