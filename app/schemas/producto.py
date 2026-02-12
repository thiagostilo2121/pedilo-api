from pydantic import BaseModel, model_validator
from sqlmodel import Field, SQLModel

from app.models.models import Producto


class ProductoBase(SQLModel):
    nombre: str
    descripcion: str | None = None
    precio: int = Field(gt=0)
    unidad: str = "unidad"
    precio_mayorista: int | None = None
    cantidad_mayorista: int | None = None
    cantidad_minima: int = 1
    imagen_url: str | None = None
    categoria: str | None = None
    stock: bool | None = True
    destacado: bool | None = False

    model_config = {
        "json_schema_extra": {
            "example": {
                "nombre": "Hamburguesa Doble",
                "descripcion": "Hamburguesa con doble carne, queso y bacon",
                "precio": 8500,
                "categoria": "Comida rápida",
                "stock": True
            }
        }
    }

    @classmethod
    def from_orm(cls, producto: Producto):
        data = producto.dict()
        data["categoria"] = producto.categoria_nombre
        return cls(**data)


class ProductoUpdate(BaseModel):
    nombre: str | None = None
    descripcion: str | None = None
    precio: int | None = None
    unidad: str | None = None
    precio_mayorista: int | None = None
    cantidad_mayorista: int | None = None
    cantidad_minima: int | None = None
    imagen_url: str | None = None
    categoria: str | None = None
    stock: bool | None = None
    destacado: bool | None = None

    @classmethod
    def from_orm(cls, producto: Producto):
        data = producto.dict()
        data["categoria"] = producto.categoria_nombre
        return cls(**data)


class ProductoCreate(ProductoBase):
    pass


class ProductoRead(ProductoBase):
    id: int
    
    @model_validator(mode='wrap')
    @classmethod
    def extract_categoria(cls, values, handler):
        if isinstance(values, Producto):
            data = {
                "id": values.id,
                "nombre": values.nombre,
                "descripcion": values.descripcion,
                "precio": values.precio,
                "unidad": values.unidad,
                "precio_mayorista": values.precio_mayorista,
                "cantidad_mayorista": values.cantidad_mayorista,
                "cantidad_minima": values.cantidad_minima,
                "imagen_url": values.imagen_url,
                "categoria": values.categoria_nombre,
                "stock": values.stock,
                "destacado": values.destacado,
            }
            return handler(data)
        return handler(values)