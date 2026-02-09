from datetime import datetime
from pydantic import BaseModel
from app.models.models import PromocionTipo

class PromocionBase(BaseModel):
    nombre: str
    codigo: str
    descripcion: str | None = None
    tipo: PromocionTipo
    valor: float
    reglas: dict = {}
    fecha_inicio: datetime | None = None
    fecha_fin: datetime | None = None
    activo: bool = True
    limite_usos_total: int | None = None
    limite_usos_por_usuario: int | None = 1

class PromocionCreate(PromocionBase):
    pass

class PromocionUpdate(PromocionBase):
    nombre: str | None = None
    codigo: str | None = None
    tipo: PromocionTipo | None = None
    valor: float | None = None
    fecha_inicio: datetime | None = None
    
class PromocionRead(PromocionBase):
    id: int
    negocio_id: int
    usos_actuales: int
    creado_en: datetime
