import pytest
from app.core.security import verify_password
from app.models.models import Usuario
from sqlmodel import select

def test_registrar_usuario(client, session):
    response = client.post(
        "/api/auth/register",
        json={
            "nombre": "Test User",
            "email": "test@example.com",
            "password": "testpassword123"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "test@example.com"
    assert "id" in data
    
    # Verificar en la DB
    usuario = session.exec(select(Usuario).where(Usuario.email == "test@example.com")).first()
    assert usuario is not None
    assert usuario.nombre == "Test User"
    assert verify_password("testpassword123", usuario.password_hash)

def test_login_usuario(client, session):
    # Primero registramos
    client.post(
        "/api/auth/register",
        json={
            "nombre": "Login User",
            "email": "login@example.com",
            "password": "password123"
        }
    )
    
    # Intentamos login
    response = client.post(
        "/api/auth/login",
        json={
            "email": "login@example.com",
            "password": "password123"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"

def test_login_fallido(client):
    response = client.post(
        "/api/auth/login",
        json={
            "email": "nonexistent@example.com",
            "password": "wrongpassword"
        }
    )
    assert response.status_code == 401
