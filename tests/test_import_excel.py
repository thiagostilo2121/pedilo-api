import os
# Set env vars BEFORE importing app to satisfy Pydantic settings validation
os.environ["CLOUDINARY_CLOUD_NAME"] = "test"
os.environ["CLOUDINARY_API_KEY"] = "test"
os.environ["CLOUDINARY_API_SECRET"] = "test"
os.environ["SECRET_KEY"] = "test-secret"
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

import pytest
from unittest.mock import MagicMock
import sys
# Removed sys.modules hacking as env vars should suffice

from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool
from app.main import app
from app.api.deps import get_session
from app.models.models import Producto, Negocio, Usuario

# Setup in-memory DB for testing
@pytest.fixture(name="session")
def session_fixture():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session

@pytest.fixture(name="client")
def client_fixture(session: Session):
    def get_session_override():
        return session
    app.dependency_overrides[get_session] = get_session_override
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()

# Mocking for enrichment
class MockResponse:
    def __init__(self, json_data, status_code=200):
        self.json_data = json_data
        self.status_code = status_code
        self.content = b"fake_image_content"
    def json(self):
        return self.json_data

def test_import_products(client: TestClient, session: Session, monkeypatch):
    # Create user and business
    user = Usuario(email="test@test.com", password_hash="hash", nombre="Test")
    session.add(user)
    session.commit()
    
    negocio = Negocio(usuario_id=user.id, nombre="Negocio Test", slug="negocio-test")
    session.add(negocio)
    session.commit()
    
    # Authenticate (mock)
    # Now import app modules
    import requests
    from app.utils import cloudinary
    from app.services.import_service import ImportService
    from io import BytesIO
    import openpyxl

    # Mock requests.get
    def mock_get(url, timeout=None):
        print(f"Mock GET: {url}")
        if "openfoodfacts" in url:
            if "BAR001" in url:
                return MockResponse({"status": 1, "product": {"image_url": "http://fake.com/image.jpg"}})
            print("Mock GET: OpenFoodFacts BAR001 not found in URL")
            return MockResponse({"status": 0})
        if "fake.com" in url:
            return MockResponse({}, 200)
        return MockResponse({}, 404)
        
    monkeypatch.setattr(requests, "get", mock_get)

    # Mock cloudinary upload
    def mock_upload(file):
        print(f"Mock Upload: {file}")
        return {"secure_url": "http://cloudinary.com/uploaded.jpg"}
        
    monkeypatch.setattr(cloudinary.uploader, "upload", mock_upload)
    
    # Create a mock Excel file
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["nombre", "precio", "sku", "codigo_barras", "stock", "descripcion", "categoria"])
    
    # row 1: valid stock "si", valid category (we will create "Bebidas")
    ws.append(["Producto 1", 100, "SKU001", "BAR001", "si", "Desc 1", "Bebidas"]) 
    
    # row 2: invalid category -> "Otros", stock 0 -> False
    ws.append(["Producto 2", 200, "SKU002", "BAR002", 0, "Desc 2", "Inexistente"]) 
    
    # Row 3: Reactivation with stock check (number > 1)
    # Create an INACTIVE product to test reactivation
    # Create "Bebidas" category first
    bebidas = Categoria(negocio_id=negocio.id, nombre="Bebidas", activo=True)
    session.add(bebidas)
    session.add(
        Producto(
           negocio_id=negocio.id,
           nombre="Old Product",
           precio=50,
           sku="SKU_OLD",
           activo=False,
           stock=False
        )
    )
    session.commit()
    
    ws.append(["New Name Old Product", 75, "SKU_OLD", "", 50, "Updated Desc", "Bebidas"]) # >1 -> True stock
    
    file = BytesIO()
    wb.save(file)
    file.seek(0)
    
    importer = ImportService()
    
    print("Starting process_excel_file...")
    stats = importer.process_excel_file(file, negocio.id, session)
    print(f"Stats: {stats}")
    
    # Created = 2 new + 1 reactivated = 3
    assert stats["created"] == 3
    assert stats["updated"] == 0
    
    # Verify DB
    # Reselect category to get ID
    bebidas_db = session.query(Categoria).filter(Categoria.nombre == "Bebidas").first()
    otros_db = session.query(Categoria).filter(Categoria.nombre == "Otros").first()
    assert otros_db is not None # Should be auto-created
    
    p1 = session.query(Producto).filter(Producto.sku == "SKU001").first()
    assert p1.stock is True
    assert p1.descripcion == "Desc 1"
    assert p1.categoria_id == bebidas_db.id
    
    p2 = session.query(Producto).filter(Producto.codigo_barras == "BAR002").first()
    assert p2.stock is False
    assert p2.descripcion == "Desc 2"
    assert p2.categoria_id == otros_db.id # Fallback
    
    # Verify Reactivation
    p3 = session.query(Producto).filter(Producto.sku == "SKU_OLD").first()
    assert p3.activo is True
    assert p3.stock is True
    assert p3.descripcion == "Updated Desc"
    assert p3.categoria_id == bebidas_db.id


