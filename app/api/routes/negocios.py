from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.api.deps import get_current_user, get_session
from app.models.models import Negocio
from app.schemas.negocio import NegocioCreate, NegocioRead, NegocioUpdate
from app.utils.utils import generar_slug

router = APIRouter(prefix="/api/negocios", tags=["Negocios"])


@router.get("/me", response_model=NegocioRead)
def get_negocio(session: Session = Depends(get_session), usuario=Depends(get_current_user)):
    negocio = session.exec(select(Negocio).where(Negocio.usuario_id == usuario.id)).first()

    if not negocio:
        raise HTTPException(status_code=404, detail="El usuario no tiene un negocio")

    return negocio


@router.post("/", response_model=NegocioRead)
def crear_negocio(
    datos: NegocioCreate, session: Session = Depends(get_session), usuario=Depends(get_current_user)
):
    if not usuario.es_premium:
        raise HTTPException(status_code=403, detail="Necesitas ser premium para crear un negocio")

    existente = session.exec(select(Negocio).where(Negocio.usuario_id == usuario.id)).first()
    if existente:
        raise HTTPException(status_code=400, detail="Ya tenés un negocio creado")

    slug = generar_slug(datos.slug)

    nuevo = Negocio(
        usuario_id=usuario.id,
        nombre=datos.nombre,
        descripcion=datos.descripcion,
        slug=slug,
        logo_url=datos.logo_url,
        color_primario=datos.color_primario,
        color_secundario=datos.color_secundario,
        telefono=datos.telefono,
        direccion=datos.direccion,
        horario=datos.horario,
    )

    session.add(nuevo)
    session.commit()
    session.refresh(nuevo)
    return nuevo


@router.get("/", response_model=list[NegocioRead])
def listar_negocios(session: Session = Depends(get_session)):
    negocios = session.exec(select(Negocio)).all()
    return negocios


@router.put("/me", response_model=NegocioRead)
def actualizar_negocio(
    datos: NegocioUpdate, 
    session: Session = Depends(get_session), 
    usuario = Depends(get_current_user)
):
    negocio = session.exec(select(Negocio).where(Negocio.usuario_id == usuario.id)).first()
    if not negocio:
        raise HTTPException(status_code=404, detail="Negocio no encontrado")


    campos_a_actualizar = {
        k: v for k, v in datos.dict(exclude_unset=True).items() if k != "slug"
    }

    for campo, valor in campos_a_actualizar.items():
        setattr(negocio, campo, valor)

    session.add(negocio)
    session.commit()
    session.refresh(negocio)
    return negocio
