from pydantic import BaseModel
from app.models.models import PedidoEstado


class PedidoItemCreate(BaseModel):
    producto_id: int
    cantidad: int
    nombre_producto: str | None = None


class PedidoCreate(BaseModel):
    metodo_pago: str | None = None
    tipo_entrega: str | None = None
    nombre_cliente: str | None = None
    telefono_cliente: str | None = None
    items: list[PedidoItemCreate]


class PedidoItemRead(PedidoItemCreate):
    id: int
    subtotal: int


class PedidoRead(BaseModel):
    id: int
    codigo: str
    estado: PedidoEstado
    total: int
    metodo_pago: str | None
    tipo_entrega: str | None
    nombre_cliente: str | None
    telefono_cliente: str | None
    items: list[PedidoItemRead]
