
from pydantic import BaseModel
from sqlmodel import Field, SQLModel

from app.models.models import Producto


class ProductoBase(SQLModel):
    nombre: str
    descripcion: str | None = None
    precio: int = Field(gt=0)
    imagen_url: str | None = None
    categoria: str | None = None
    stock: bool | None = True

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
    imagen_url: str | None = None
    categoria: str | None = None
    stock: bool | None = None

    @classmethod
    def from_orm(cls, producto: Producto):
        data = producto.dict()
        data["categoria"] = producto.categoria_nombre
        return cls(**data)


class ProductoCreate(ProductoBase):
    pass


class ProductoRead(ProductoBase):
    id: int
