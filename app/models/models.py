from typing import Any, Optional
from datetime import datetime, timezone
from enum import Enum
from sqlmodel import JSON, Column, Field, Relationship, SQLModel

class PedidoEstado(str, Enum):
    PENDIENTE = "pendiente"
    ACEPTADO = "aceptado"
    RECHAZADO = "rechazado"
    EN_PROGRESO = "en_progreso"
    FINALIZADO = "finalizado"

class SubscriptionStatus(str, Enum):
    AUTHORIZED = "authorized"
    ACTIVE = "active"
    PAUSED = "paused"
    CANCELLED = "cancelled"
    EXPIRED = "expired"
    REJECTED = "rejected"


class Usuario(SQLModel, table=True):
    __tablename__ = "usuarios"

    id: int | None = Field(default=None, primary_key=True)
    nombre: str | None
    email: str = Field(index=True, unique=True)
    password_hash: str
    es_premium: bool = False
    activo: bool = True
    creado_en: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    negocios: list["Negocio"] = Relationship(back_populates="usuario")
    suscripcion: Optional["Subscription"] = Relationship(back_populates="usuario")

    @property
    def tiene_negocio(self) -> bool:
        return len(self.negocios) > 0


class Negocio(SQLModel, table=True):
    __tablename__ = "negocios"

    id: int | None = Field(default=None, primary_key=True)
    usuario_id: int = Field(foreign_key="usuarios.id")
    nombre: str
    descripcion: str | None = None
    slug: str = Field(index=True, unique=True)
    logo_url: str | None = None
    banner_url: str | None = None
    color_primario: str | None = None
    color_secundario: str | None = None
    metodos_pago: list[str] = Field(sa_column=Column[Any](JSON), default=[])
    tipos_entrega: list[str] = Field(sa_column=Column[Any](JSON), default=[])
    codigo_pais: str | None = None
    telefono: str | None = None
    direccion: str | None = None
    horario: str | None = None
    acepta_pedidos: bool | None = True
    activo: bool = True
    creado_en: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    usuario: Usuario | None = Relationship(back_populates="negocios")
    productos: list["Producto"] = Relationship(back_populates="negocio")
    pedidos: list["Pedido"] = Relationship(back_populates="negocio")
    categorias: list["Categoria"] = Relationship(back_populates="negocio")
    grupos_topping: list["GrupoTopping"] = Relationship(back_populates="negocio")


class Categoria(SQLModel, table=True):
    __tablename__ = "categorias"

    id: int | None = Field(default=None, primary_key=True)
    negocio_id: int = Field(foreign_key="negocios.id")
    nombre: str
    imagen_url: str | None = None
    activo: bool = True
    creado_en: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    negocio: Negocio | None = Relationship(back_populates="categorias")
    productos: list["Producto"] = Relationship(back_populates="categorias")


class Producto(SQLModel, table=True):
    __tablename__ = "productos"

    id: int | None = Field(default=None, primary_key=True)
    negocio_id: int = Field(foreign_key="negocios.id")
    nombre: str
    descripcion: str | None = None
    precio: int
    imagen_url: str | None = None
    categoria_id: int | None = Field(default=None, foreign_key="categorias.id")
    stock: bool | None = True
    destacado: bool = Field(default=False)
    activo: bool = True
    creado_en: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    negocio: Negocio | None = Relationship(back_populates="productos")
    categorias: Categoria | None = Relationship(back_populates="productos")
    grupos_topping: list["ProductoGrupoTopping"] = Relationship(back_populates="producto")

    @property
    def categoria_nombre(self) -> str | None:
        return self.categorias.nombre if self.categorias else None


class Pedido(SQLModel, table=True):
    __tablename__ = "pedidos"

    id: int | None = Field(default=None, primary_key=True)
    negocio_id: int = Field(foreign_key="negocios.id")
    codigo: str
    estado: PedidoEstado = Field(default=PedidoEstado.PENDIENTE)
    total: int
    metodo_pago: str | None = None
    tipo_entrega: str | None = None
    nombre_cliente: str | None = None
    telefono_cliente: str | None = None
    creado_en: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    negocio: Negocio | None = Relationship(back_populates="pedidos")
    items: list["PedidoItem"] = Relationship(back_populates="pedido")


class PedidoItem(SQLModel, table=True):
    __tablename__ = "pedido_items"

    id: int | None = Field(default=None, primary_key=True)
    pedido_id: int = Field(foreign_key="pedidos.id")
    producto_id: int | None = Field(default=None)
    nombre_producto: str
    precio_unitario: int
    cantidad: int
    subtotal: int
    toppings_seleccionados: list[dict] = Field(sa_column=Column[Any](JSON), default=[])
    # Formato: [{"nombre": "Chocolate", "precio": 0}, {"nombre": "Queso extra", "precio": 200}]

    pedido: Pedido | None = Relationship(back_populates="items")


class Subscription(SQLModel, table=True):
    __tablename__ = "subscriptions"

    id: Optional[int] = Field(default=None, primary_key=True)

    usuario_id: int = Field(foreign_key="usuarios.id", index=True)
    usuario: Optional["Usuario"] = Relationship(back_populates="suscripcion")

    mp_subscription_id: str = Field(index=True, unique=True)
    mp_plan_id: Optional[str] = Field(default=None, index=True)

    status: SubscriptionStatus = Field(index=True)
    # possible: authorized, active, paused, cancelled, expired, rejected

    start_date: datetime
    next_payment_date: Optional[datetime] = None
    end_date: Optional[datetime] = None

    amount: float
    currency: str = "ARS"
    frequency: int = 1
    frequency_type: str = "months"

    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class GrupoTopping(SQLModel, table=True):
    """Grupo de toppings (ej: 'Sabores', 'Extras', 'Salsas')"""
    __tablename__ = "grupos_topping"

    id: int | None = Field(default=None, primary_key=True)
    negocio_id: int = Field(foreign_key="negocios.id")
    nombre: str
    activo: bool = True
    creado_en: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    negocio: "Negocio" = Relationship(back_populates="grupos_topping")
    toppings: list["Topping"] = Relationship(back_populates="grupo")
    productos_config: list["ProductoGrupoTopping"] = Relationship(back_populates="grupo")


class Topping(SQLModel, table=True):
    """Topping individual dentro de un grupo"""
    __tablename__ = "toppings"

    id: int | None = Field(default=None, primary_key=True)
    grupo_id: int = Field(foreign_key="grupos_topping.id")
    nombre: str
    precio_extra: int = 0
    disponible: bool = Field(default=True)
    activo: bool = True
    creado_en: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    grupo: GrupoTopping = Relationship(back_populates="toppings")


class ProductoGrupoTopping(SQLModel, table=True):
    """Relación M:N entre Producto y GrupoTopping con configuración de selecciones"""
    __tablename__ = "producto_grupo_topping"

    id: int | None = Field(default=None, primary_key=True)
    producto_id: int = Field(foreign_key="productos.id")
    grupo_id: int = Field(foreign_key="grupos_topping.id")
    min_selecciones: int = 0
    max_selecciones: int = 1

    producto: "Producto" = Relationship(back_populates="grupos_topping")
    grupo: GrupoTopping = Relationship(back_populates="productos_config")