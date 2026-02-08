from pydantic import BaseModel
from app.models.models import PedidoEstado
from app.schemas.topping import ToppingSeleccionado


class PedidoItemCreate(BaseModel):
    producto_id: int
    cantidad: int
    nombre_producto: str | None = None
    toppings: list[ToppingSeleccionado] = []


class PedidoCreate(BaseModel):
    metodo_pago: str | None = None
    tipo_entrega: str | None = None
    nombre_cliente: str | None = None
    telefono_cliente: str | None = None
    codigo_cupon: str | None = None
    items: list[PedidoItemCreate]


class PedidoItemRead(BaseModel):
    id: int
    producto_id: int | None
    nombre_producto: str
    precio_unitario: int
    cantidad: int
    subtotal: int
    toppings_seleccionados: list[dict] = []


class PedidoRead(BaseModel):
    id: int
    codigo: str
    estado: PedidoEstado
    total: int
    metodo_pago: str | None
    tipo_entrega: str | None
    nombre_cliente: str | None
    telefono_cliente: str | None
    descuento_aplicado: int = 0
    items: list[PedidoItemRead]
