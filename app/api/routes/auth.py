from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security import HTTPBearer
from sqlmodel import Session, select

from app.api.deps import get_session, get_current_user
from app.core.security import create_access_token, hash_password, verify_password
from app.models.models import Usuario, Negocio
from app.schemas.usuario import LoginRequest, Token, UsuarioCreate, UsuarioRead

security = HTTPBearer()

router = APIRouter(prefix="/api/auth", tags=["Auth"])


from app.core.rate_limit import limiter

@router.post("/register", response_model=UsuarioRead)
@limiter.limit("5/minute")
def registrar_usuario(request: Request, usuario: UsuarioCreate, session: Session = Depends(get_session)):
    existente = session.exec(select(Usuario).where(Usuario.email == usuario.email)).first()
    if existente:
        raise HTTPException(status_code=400, detail="Email ya registrado")

    nuevo = Usuario(
        nombre=usuario.nombre,
        email=usuario.email,
        password_hash=hash_password(usuario.password),
        es_premium=False,
    )

    session.add(nuevo)
    session.commit()
    session.refresh(nuevo)
    return nuevo


@router.post("/login", response_model=Token)
@limiter.limit("5/minute")
def login(request: Request, data: LoginRequest, session: Session = Depends(get_session)):
    usuario = session.exec(select(Usuario).where(Usuario.email == data.email)).first()
    if not usuario or not verify_password(data.password, usuario.password_hash):
        raise HTTPException(status_code=401, detail="Credenciales incorrectas")

    token = create_access_token(
        {
            "sub": usuario.email,
            "user_id": usuario.id,
        }
    )

    return {"access_token": token, "token_type": "bearer"}

@router.get("/usuario", response_model=UsuarioRead)
def get_usuario(
    session: Session = Depends(get_session),
    usuario = Depends(get_current_user)
):
    if not usuario:
        raise HTTPException(status_code=400, detail="Usuario no encontrado")

    negocio = session.exec(
        select(Negocio).where(Negocio.usuario_id == usuario.id)
    ).first()

    return UsuarioRead(
        id=usuario.id,
        email=usuario.email,
        nombre=usuario.nombre,
        activo=usuario.activo,
        es_premium=usuario.es_premium,
        tiene_negocio=bool(negocio),
    )