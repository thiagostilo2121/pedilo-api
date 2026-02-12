from pydantic import BaseModel, Field, field_validator
from sqlmodel import SQLModel
from app.models.models import TipoNegocio


class NegocioBase(SQLModel):
    nombre: str = Field(min_length=1, max_length=50)
    descripcion: str | None = Field(default=None, max_length=240)
    slug: str = Field(min_length=1)
    logo_url: str | None = None
    banner_url: str | None = None
    color_primario: str | None = None
    color_secundario: str | None = None
    metodos_pago: list[str] = []
    tipos_entrega: list[str] = []
    codigo_pais: str | None = None
    telefono: str | None = None
    direccion: str | None = None
    horario: str | None = None
    acepta_pedidos: bool = True
    pedido_minimo: int = 0
    tipo_negocio: TipoNegocio = TipoNegocio.MINORISTA

    model_config = {
        "json_schema_extra": {
            "example": {
                "nombre": "Mi Tienda",
                "descripcion": "La mejor tienda de ropa",
                "slug": "mi-tienda",
                "metodos_pago": ["efectivo", "transferencia"],
                "tipos_entrega": ["delivery", "takeaway"],
                "telefono": "12345678"
            }
        }
    }

    @field_validator("nombre", "descripcion", mode="before")
    @classmethod
    def strip_strings(cls, v):
        if isinstance(v, str):
            stripped = v.strip()
            return stripped or None if stripped == "" else stripped
        return v


class NegocioUpdate(BaseModel):
    nombre: str | None = None
    descripcion: str | None = None
    slug: str | None = None
    logo_url: str | None = None
    color_primario: str | None = None
    color_secundario: str | None = None
    metodos_pago: list[str] | None = None
    tipos_entrega: list[str] | None = None
    codigo_pais: str | None = None
    telefono: str | None = None
    direccion: str | None = None
    horario: str | None = None
    acepta_pedidos: bool | None = None
    pedido_minimo: int | None = None
    tipo_negocio: TipoNegocio | None = None
    banner_url: str | None = None


class NegocioCreate(NegocioBase):
    pass


class NegocioRead(NegocioBase):
    id: int
    activo: bool
