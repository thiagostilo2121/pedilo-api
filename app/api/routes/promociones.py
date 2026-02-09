from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.api.deps import get_session, get_current_user_negocio
from app.models.models import Negocio, Promocion
from app.schemas.promocion import PromocionRead, PromocionCreate, PromocionUpdate

router = APIRouter(prefix="/api/promociones", tags=["Promociones"])

@router.get("", response_model=list[PromocionRead])
def get_promociones(
    session: Session = Depends(get_session),
    current_negocio: Negocio = Depends(get_current_user_negocio),
):
    """Listar todas las promociones del negocio actual"""
    promos = session.exec(
        select(Promocion).where(Promocion.negocio_id == current_negocio.id)
    ).all()
    return promos

@router.post("", response_model=PromocionRead)
def create_promocion(
    promocion: PromocionCreate,
    session: Session = Depends(get_session),
    current_negocio: Negocio = Depends(get_current_user_negocio),
):
    """Crear una nueva promoción"""
    # Validar código único en el negocio
    existing = session.exec(
        select(Promocion).where(
            Promocion.codigo == promocion.codigo,
            Promocion.negocio_id == current_negocio.id
        )
    ).first()
    
    if existing:
        raise HTTPException(status_code=400, detail="Ya existe una promoción con este código")

    promo_data = promocion.model_dump(exclude_unset=True)
    db_promo = Promocion(**promo_data)
    db_promo.negocio_id = current_negocio.id
    session.add(db_promo)
    session.commit()
    session.refresh(db_promo)
    return db_promo

@router.patch("/{promocion_id}", response_model=PromocionRead)
def update_promocion(
    promocion_id: int,
    promocion_in: PromocionUpdate,
    session: Session = Depends(get_session),
    current_negocio: Negocio = Depends(get_current_user_negocio),
):
    """Actualizar una promoción"""
    db_promo = session.get(Promocion, promocion_id)
    if not db_promo or db_promo.negocio_id != current_negocio.id:
        raise HTTPException(status_code=404, detail="Promoción no encontrada")

    promo_data = promocion_in.model_dump(exclude_unset=True)
    for key, value in promo_data.items():
        setattr(db_promo, key, value)

    session.add(db_promo)
    session.commit()
    session.refresh(db_promo)
    return db_promo

@router.delete("/{promocion_id}")
def delete_promocion(
    promocion_id: int,
    session: Session = Depends(get_session),
    current_negocio: Negocio = Depends(get_current_user_negocio),
):
    """Eliminar (soft delete o hard delete) una promoción"""
    db_promo = session.get(Promocion, promocion_id)
    if not db_promo or db_promo.negocio_id != current_negocio.id:
        raise HTTPException(status_code=404, detail="Promoción no encontrada")
    
    session.delete(db_promo)
    session.commit()
    return {"ok": True}
