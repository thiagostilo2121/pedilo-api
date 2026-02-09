from pydantic import BaseModel


class ToppingSeleccionado(BaseModel):
    topping_id: int | None = None
    nombre: str
    precio: int = 0


class ToppingCreate(BaseModel):
    nombre: str
    precio_extra: int = 0
    disponible: bool = True


class ToppingRead(BaseModel):
    id: int
    nombre: str
    precio_extra: int


class ToppingUpdate(BaseModel):
    nombre: str | None = None
    precio_extra: int | None = None
    disponible: bool | None = None


class GrupoToppingCreate(BaseModel):
    nombre: str
    toppings: list[ToppingCreate] = []


class GrupoToppingRead(BaseModel):
    id: int
    nombre: str
    toppings: list[ToppingRead] = []


class GrupoToppingUpdate(BaseModel):
    nombre: str | None = None
    toppings: list[ToppingCreate] | None = None


class ProductoGrupoToppingConfig(BaseModel):
    grupo_id: int
    min_selecciones: int = 0
    max_selecciones: int = 1
