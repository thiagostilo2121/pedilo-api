from pydantic import Field
from sqlmodel import SQLModel


class UsuarioCreate(SQLModel):
    nombre: str | None = Field(default=None, min_length=1)
    email: str = Field(pattern=r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")
    password: str = Field(min_length=8)


class UsuarioRead(SQLModel):
    id: int
    nombre: str | None
    email: str
    activo: bool
    es_premium: bool
    tiene_negocio: bool


class LoginRequest(SQLModel):
    email: str
    password: str


class Token(SQLModel):
    access_token: str
    token_type: str = "bearer"
