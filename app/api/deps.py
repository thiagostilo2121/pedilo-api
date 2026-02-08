from fastapi import Depends, HTTPException, Query
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlmodel import Session, select

from app.core.config import settings
from app.core.database import engine
from app.models.models import Negocio, Usuario

class PaginationParams:
    def __init__(
        self,
        skip: int = Query(0, ge=0, description="Número de registros a saltar"),
        limit: int = Query(100, ge=1, le=100, description="Cantidad máxima de registros a retornar"),
    ):
        self.skip = skip
        self.limit = limit

security = HTTPBearer()


def get_session():
    with Session(engine) as session:
        yield session


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    session: Session = Depends(get_session),
):
    token = credentials.credentials
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id = payload.get("user_id")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Token inválido")
    except JWTError:
        raise HTTPException(status_code=401, detail="Token inválido")

    usuario = session.get(Usuario, user_id)
    if not usuario:
        raise HTTPException(status_code=401, detail="Usuario no encontrado")

    return usuario


def get_negocio_del_usuario(session: Session, usuario: Usuario):
    negocio = session.exec(
        select(Negocio).where(Negocio.usuario_id == usuario.id, Negocio.activo)
    ).first()
    if not negocio:
        raise HTTPException(status_code=403, detail="El usuario no tiene un negocio activo")
    return negocio


def get_current_user_negocio(
    session: Session = Depends(get_session),
    usuario: Usuario = Depends(get_current_user),
):
    return get_negocio_del_usuario(session, usuario)
