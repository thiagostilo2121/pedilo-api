from uuid import uuid4
from sqlmodel import Session, select
from app.models.models import Negocio, Pedido, PedidoItem, Producto
from app.schemas.pedido import PedidoCreate
from app.core.exceptions import EntityNotFoundError, BusinessLogicError, PermissionDeniedError

def crear_nuevo_pedido(session: Session, slug: str, data: PedidoCreate) -> Pedido:

    negocio = session.exec(
        select(Negocio).where(Negocio.slug == slug, Negocio.activo == True)
    ).first()
    
    if not negocio:
        raise EntityNotFoundError("Negocio no encontrado")
    
    if not negocio.acepta_pedidos:
        raise PermissionDeniedError("Este negocio no está recibiendo pedidos en este momento")

    if data.metodo_pago not in negocio.metodos_pago:
        raise BusinessLogicError("El método de pago no está permitido por este negocio")

    if data.tipo_entrega not in negocio.tipos_entrega:
        raise BusinessLogicError("El tipo de entrega no está permitido por este negocio")

    total = 0
    items_procesados = []
    
    for item in data.items:
        if item.cantidad <= 0:
            raise BusinessLogicError("La cantidad de los productos debe ser mayor a 0")

        producto = session.get(Producto, item.producto_id)
        if not producto or producto.negocio_id != negocio.id:
            raise EntityNotFoundError(f"Producto {item.producto_id} no encontrado")

        if not producto.stock:
            raise BusinessLogicError(f"El producto '{producto.nombre}' no tiene stock disponible")

        subtotal = producto.precio * item.cantidad
        total += subtotal
        
        items_procesados.append({
            "producto_id": producto.id,
            "nombre_producto": producto.nombre,
            "precio_unitario": producto.precio,
            "cantidad": item.cantidad,
            "subtotal": subtotal
        })

    codigo = uuid4().hex[:6].upper()
    pedido = Pedido(
        negocio_id=negocio.id,
        codigo=codigo,
        estado="pendiente",
        total=total,
        metodo_pago=data.metodo_pago,
        tipo_entrega=data.tipo_entrega,
        nombre_cliente=data.nombre_cliente,
        telefono_cliente=data.telefono_cliente,
    )

    session.add(pedido)
    session.flush()

    for item_data in items_procesados:
        pedido_item = PedidoItem(
            pedido_id=pedido.id,
            **item_data
        )
        session.add(pedido_item)

    session.commit()
    session.refresh(pedido)
    return pedido
