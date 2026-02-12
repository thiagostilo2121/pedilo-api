from sqlalchemy.orm import joinedload
from sqlalchemy import func
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlmodel import Session, select
from app.core.rate_limit import limiter

from app.api.deps import get_session, PaginationParams
from app.models.models import Negocio, Pedido, Producto, Categoria, TipoNegocio
from app.schemas.pedido import PedidoCreate, PedidoRead, PedidoItemCreate
from app.schemas.producto import ProductoRead
from app.schemas.negocio import NegocioRead, NegocioPublicDetail
from app.schemas.categoria import CategoriaRead
from app.schemas.promocion import PromocionRead
from app.services.pedido_service import crear_nuevo_pedido
from app.services import topping_service
from app.models.models import PedidoEstado

router = APIRouter(prefix="/public", tags=["Públicos"])


@router.get("/{slug}", response_model=NegocioPublicDetail)
@limiter.limit("60/minute")
def get_negocio(request: Request, slug: str, session: Session = Depends(get_session)):
    negocio = session.exec(select(Negocio).where(Negocio.slug == slug)).first()

    if not negocio:
        raise HTTPException(status_code=404, detail="Negocio no encontrado")

    # Calculo de insignias (On-the-fly)
    insignias = []
    
    # Badge: TOP_SELLER_100
    total_pedidos = session.exec(
        select(func.count(Pedido.id)).where(Pedido.negocio_id == negocio.id)
    ).one()
    
    if total_pedidos > 100:
        insignias.append("TOP_SELLER_100")

    # Badge: VERIFICADO_50
    pedidos_entregados = session.exec(
        select(func.count(Pedido.id)).where(
            Pedido.negocio_id == negocio.id,
            Pedido.estado == PedidoEstado.FINALIZADO
        )
    ).one()

    if pedidos_entregados > 50:
        insignias.append("VERIFICADO_50")

    # Badge: ENTREGA_FLASH (Opcional - placeholder logic)
    # Aquí podríamos calcular el promedio de tiempo si tuviéramos esa data
    # Por ahora, dejámoslo pendiente o con una lógica simple si aplica
    
    negocio_dict = negocio.model_dump()
    negocio_dict["insignias"] = insignias
    
    return NegocioPublicDetail(**negocio_dict)

@router.get("/{slug}/productos", response_model=list[ProductoRead])
@limiter.limit("60/minute")
def listar_productos_por_slug(
    request: Request,
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
@limiter.limit("60/minute")
def listar_categorias_por_slug(
    request: Request,
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
@limiter.limit("10/minute")
def crear_pedido(request: Request, slug: str, data: PedidoCreate, session: Session = Depends(get_session)):
    return crear_nuevo_pedido(session, slug, data)


@router.get("/{slug}/pedidos/{codigo}", response_model=PedidoRead)
@limiter.limit("60/minute")
def ver_pedido(request: Request, slug: str, codigo: str, session: Session = Depends(get_session)):
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
@limiter.limit("60/minute")
def obtener_toppings_producto_publico(
    request: Request,
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
@limiter.limit("20/minute")
def validar_cupon_endpoint(
    request: Request,
    slug: str,
    data: CouponValidationRequest,
    session: Session = Depends(get_session)
):
    negocio = session.exec(select(Negocio).where(Negocio.slug == slug)).first()
    if not negocio:
        raise HTTPException(status_code=404, detail="Negocio no encontrado")

    # Optimization: Prefetch all products and toppings to avoid N+1 queries
    product_ids = {item.producto_id for item in data.items}
    
    topping_ids = set()
    for item in data.items:
        if item.toppings:
            for t in item.toppings:
                topping_ids.add(t.topping_id)
    
    # Fetch products
    productos = session.exec(select(Producto).where(Producto.id.in_(product_ids))).all()
    productos_map = {p.id: p for p in productos}
    
    # Fetch toppings
    from app.models.models import Topping
    toppings_map = {}
    if topping_ids:
        toppings = session.exec(select(Topping).where(Topping.id.in_(topping_ids))).all()
        toppings_map = {t.id: t for t in toppings}

    # Recalcular total y preparar items para validación
    total_carrito = 0
    items_para_reglas = []
    
    for item in data.items:
        producto = productos_map.get(item.producto_id)
        
        if producto and producto.negocio_id == negocio.id:
            # Calcular precio toppings
            precio_toppings = 0
            if item.toppings:
                for t in item.toppings:
                    top_db = toppings_map.get(t.topping_id)
                    if top_db:
                        precio_toppings += top_db.precio_extra

            # Calcular precio base: considerar mayorista si aplica
            precio_base = producto.precio
            if (
                negocio.tipo_negocio == TipoNegocio.DISTRIBUIDORA
                and producto.precio_mayorista is not None
                and producto.cantidad_mayorista is not None
                and item.cantidad >= producto.cantidad_mayorista
            ):
                precio_base = producto.precio_mayorista

            total_carrito += (precio_base + precio_toppings) * item.cantidad
            
            items_para_reglas.append({
                "producto_id": producto.id,
                "categoria_id": producto.categoria_id,
                "cantidad": item.cantidad,
                "precio_unitario": precio_base + precio_toppings
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