from pydantic import BaseModel, Field


# ============ Topping Schemas ============

class ToppingBase(BaseModel):
    nombre: str
    precio_extra: int = Field(default=0, ge=0)
    disponible: bool = True


class ToppingCreate(ToppingBase):
    pass


class ToppingUpdate(BaseModel):
    nombre: str | None = None
    precio_extra: int | None = Field(default=None, ge=0)
    disponible: bool | None = None


class ToppingRead(ToppingBase):
    id: int


# ============ GrupoTopping Schemas ============

class GrupoToppingBase(BaseModel):
    nombre: str


class GrupoToppingCreate(GrupoToppingBase):
    """Crear grupo con toppings iniciales opcionales"""
    toppings: list[ToppingCreate] = []


class GrupoToppingUpdate(BaseModel):
    nombre: str | None = None
    toppings: list[ToppingCreate] | None = None


class GrupoToppingRead(GrupoToppingBase):
    id: int
    toppings: list[ToppingRead] = []


# ============ Producto-Topping Config Schemas ============

class ProductoGrupoToppingConfig(BaseModel):
    """Configuración de un grupo de toppings para un producto"""
    grupo_id: int
    min_selecciones: int = Field(default=0, ge=0)
    max_selecciones: int = Field(default=1, ge=1)


class ProductoToppingRead(BaseModel):
    """Vista de un grupo de toppings configurado para un producto (API pública)"""
    grupo_id: int
    grupo_nombre: str
    min_selecciones: int
    max_selecciones: int
    toppings: list[ToppingRead]


# ============ Topping en Pedido Schemas ============

class ToppingSeleccionado(BaseModel):
    """Topping seleccionado por el cliente al hacer un pedido"""
    topping_id: int
    nombre: str | None = None
    precio: int | None = None
