import pytest
from app.models.models import Negocio, Usuario, Pedido, PedidoEstado
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



