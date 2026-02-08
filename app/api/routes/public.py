from sqlalchemy.orm import joinedload
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.api.deps import get_session, PaginationParams
from app.models.models import Negocio, Pedido, Producto, Categoria
from app.schemas.pedido import PedidoCreate, PedidoRead, PedidoItemCreate
from app.schemas.producto import ProductoRead
from app.schemas.negocio import NegocioRead
from app.schemas.categoria import CategoriaRead
from app.schemas.promocion import PromocionRead
from app.services.pedido_service import crear_nuevo_pedido
from app.services import topping_service

router = APIRouter(prefix="/public", tags=["Públicos"])


@router.get("/{slug}", response_model=NegocioRead)
def get_negocio(slug: str, session: Session = Depends(get_session)):
    negocio = session.exec(select(Negocio).where(Negocio.slug == slug)).first()

    if not negocio:
        raise HTTPException(status_code=404, detail="Negocio no encontrado")

    return negocio

@router.get("/{slug}/productos", response_model=list[ProductoRead])
def listar_productos_por_slug(
    slug: str,
    session: Session = Depends(get_session),
    pagination: PaginationParams = Depends(),
):
    negocio = session.exec(
        select(Negocio).where(Negocio.slug == slug, Negocio.activo)
    ).first()
    if not negocio:
        raise HTTPException(status_code=404, detail="Negocio no encontrado")
    
    productos = session.exec(
        select(Producto)
        .where(Producto.negocio_id == negocio.id, Producto.activo)
        .options(joinedload(Producto.categorias))
        .offset(pagination.skip)
        .limit(pagination.limit)
    ).all()

    result = []
    for p in productos:
        p_read = ProductoRead.model_validate(p)
        p_read.categoria = p.categoria_nombre
        result.append(p_read)
        
    return result

@router.get("/{slug}/categorias", response_model=list[CategoriaRead])
def listar_categorias_por_slug(
    slug: str,
    session: Session = Depends(get_session),
    pagination: PaginationParams = Depends(),
):
    negocio = session.exec(
        select(Negocio).where(Negocio.slug == slug, Negocio.activo)
    ).first()
    if not negocio:
        raise HTTPException(status_code=404, detail="Negocio no encontrado")

    categorias = session.exec(
        select(Categoria)
        .where(Categoria.negocio_id == negocio.id, Categoria.activo)
        .offset(pagination.skip)
        .limit(pagination.limit)
    ).all()
    return [CategoriaRead.model_validate(c) for c in categorias]


@router.post("/{slug}/pedidos", response_model=PedidoRead)
def crear_pedido(slug: str, data: PedidoCreate, session: Session = Depends(get_session)):
    return crear_nuevo_pedido(session, slug, data)


@router.get("/{slug}/pedidos/{codigo}", response_model=PedidoRead)
def ver_pedido(slug: str, codigo: str, session: Session = Depends(get_session)):
    negocio = session.exec(
        select(Negocio).where(Negocio.slug == slug, Negocio.activo)
    ).first()
    if not negocio:
        raise HTTPException(status_code=404, detail="Negocio no encontrado")

    pedido = session.exec(
        select(Pedido).where(Pedido.negocio_id == negocio.id, Pedido.codigo == codigo)
    ).first()

    if not pedido:
        raise HTTPException(status_code=404, detail="Pedido no encontrado")

    return pedido

@router.get("/{slug}/productos/{producto_id}/toppings")
def obtener_toppings_producto_publico(
    slug: str,
    producto_id: int,
    session: Session = Depends(get_session),
):
    """Obtiene los grupos de toppings disponibles para un producto (API pública)"""
    negocio = session.exec(
        select(Negocio).where(Negocio.slug == slug, Negocio.activo)
    ).first()
    if not negocio:
        raise HTTPException(status_code=404, detail="Negocio no encontrado")

    producto = session.get(Producto, producto_id)
    if not producto or producto.negocio_id != negocio.id or not producto.activo:
        raise HTTPException(status_code=404, detail="Producto no encontrado")

    return topping_service.obtener_toppings_producto(session, producto_id)

from pydantic import BaseModel
class CouponValidationRequest(BaseModel):
    codigo: str
    items: list[PedidoItemCreate]

@router.post("/{slug}/validate-coupon")
def validar_cupon_endpoint(
    slug: str,
    data: CouponValidationRequest,
    session: Session = Depends(get_session)
):
    negocio = session.exec(select(Negocio).where(Negocio.slug == slug)).first()
    if not negocio:
        raise HTTPException(status_code=404, detail="Negocio no encontrado")

    # Recalcular total y preparar items para validación
    total_carrito = 0
    items_para_reglas = []
    
    for item in data.items:
        producto = session.get(Producto, item.producto_id)
        if producto and producto.negocio_id == negocio.id:
            subtotal = producto.precio * item.cantidad
            # Sumar toppings si fuera necesario (simplificado: ignoramos precio toppings para descuento base, o lo incluimos?)
            # Para proteccion, lo ideal es calcularlo bien.
            # Por ahora, usamos el precio base del producto como base para descuentos % 
            
            # Si el cupon aplica al total, deberiamos sumar toppings tambien.
            # Vamos a sumar toppings basicos si estan en el modelo, pero item.toppings viene del request.
            # Asumamos que el descuento es sobre el precio base de productos por simplicidad inicial o iterar.
            # Mejor: Calcular bien.
            precio_toppings = 0
            if item.toppings:
                # Logica simplificada de costo toppings (sin validacion estricta aqui para velocidad de UI)
                for t in item.toppings:
                    # t es ToppingSeleccionado
                    # Necesitamos buscar precio real
                    from app.models.models import Topping
                    top_db = session.get(Topping, t.topping_id)
                    if top_db:
                        precio_toppings += top_db.precio_extra
            
            total_carrito += (producto.precio + precio_toppings) * item.cantidad
            
            items_para_reglas.append({
                "producto_id": producto.id,
                "categoria_id": producto.categoria_id,
                "cantidad": item.cantidad,
                "precio_unitario": producto.precio
            })

    from app.services.promocion_service import PromocionService
    service = PromocionService(session)
    
    try:
        resultado = service.validar_cupon(
            codigo=data.codigo,
            negocio_id=negocio.id,
            carrito_total=total_carrito,
            items=items_para_reglas
        )
        
        # Serializar objeto Promocion para evitar errores de referencia circular/lazy loading
        # Serializar objeto Promocion para evitar errores de referencia circular/lazy loading
        if resultado.get("promocion"):
            # Convertimos manualmente para evitar líos con el ORM y lazy loading
            p_orm = resultado["promocion"]
            resultado["promocion"] = PromocionRead(
                id=p_orm.id,
                negocio_id=p_orm.negocio_id,
                nombre=p_orm.nombre,
                codigo=p_orm.codigo,
                descripcion=p_orm.descripcion,
                tipo=p_orm.tipo,
                valor=p_orm.valor,
                reglas=p_orm.reglas,
                fecha_inicio=p_orm.fecha_inicio,
                fecha_fin=p_orm.fecha_fin,
                activo=p_orm.activo,
                limite_usos_total=p_orm.limite_usos_total,
                limite_usos_por_usuario=p_orm.limite_usos_por_usuario,
                usos_actuales=p_orm.usos_actuales,
                creado_en=p_orm.creado_en
            )
            
        return resultado
    except HTTPException as e:
        raise e
    except Exception as e:
        import traceback
        traceback.print_exc()
        # DEV: Expose error to user to debug the 400
        raise HTTPException(status_code=400, detail=f"Error validando cupón: {str(e)}")