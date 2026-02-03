
from sqlmodel import SQLModel


class CategoriaBase(SQLModel):
    nombre: str
    imagen_url: str | None = None
    activo: bool = True

    model_config = {
        "json_schema_extra": {
            "example": {
                "nombre": "Bebidas",
                "imagen_url": "https://res.cloudinary.com/demo/image/upload/sample.jpg",
                "activo": True
            }
        }
    }


class CategoriaUpdate(CategoriaBase):
    nombre: str | None = None
    imagen_url: str | None = None
    activo: bool | None = None


class CategoriaCreate(CategoriaBase):
    pass


class CategoriaRead(CategoriaBase):
    id: int
