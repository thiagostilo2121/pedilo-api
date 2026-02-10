import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine, StaticPool

from app.main import app
from app.api.deps import get_session

# Base de datos en memoria para los tests
DATABASE_URL = "sqlite://"

@pytest.fixture(name="session")
def session_fixture():
    # El StaticPool es necesario para usar SQLite en memoria con múltiples hilos/conexiones
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    SQLModel.metadata.drop_all(engine)

@pytest.fixture(name="db_session")
def db_session_fixture(session):
    return session

@pytest.fixture(name="client")
def client_fixture(session: Session):
    # Sobrescribimos la dependencia get_session para que use la DB de prueba
    def get_session_override():
        return session

    app.dependency_overrides[get_session] = get_session_override
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()
