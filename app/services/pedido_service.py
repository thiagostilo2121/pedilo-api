from uuid import uuid4
from sqlmodel import Session, select
from app.models.models import Negocio, Pedido, PedidoItem, Producto
from app.schemas.pedido import PedidoCreate
from app.core.exceptions import EntityNotFoundError, BusinessLogicError, PermissionDeniedError
from app.services.topping_service import validar_toppings_seleccionados


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

    items_procesados = []
    
    # --- LOGICA DE PROCESAMIENTO DE ITEMS ---
    subtotal_productos = 0

    for item in data.items:
        if item.cantidad <= 0:
            raise BusinessLogicError("La cantidad de los productos debe ser mayor a 0")

        producto = session.get(Producto, item.producto_id)
        if not producto or producto.negocio_id != negocio.id:
            raise EntityNotFoundError(f"Producto {item.producto_id} no encontrado")

        if not producto.stock:
            raise BusinessLogicError(f"El producto '{producto.nombre}' no tiene stock disponible")

        # Validar y procesar toppings
        toppings_procesados = []
        precio_toppings = 0
        if item.toppings:
            toppings_dict = [t.model_dump() for t in item.toppings]
            toppings_procesados, precio_toppings = validar_toppings_seleccionados(
                session, producto.id, toppings_dict
            )

        # Calcular subtotal: (precio_producto + precio_toppings) * cantidad
        precio_unitario_total = producto.precio + precio_toppings
        subtotal = precio_unitario_total * item.cantidad
        subtotal_productos += subtotal

        # Guardamos datos crudos para luego crear Items
        items_procesados.append({
            "producto_id": producto.id,
            "nombre_producto": producto.nombre,
            "precio_unitario": precio_unitario_total,
            "cantidad": item.cantidad,
            "subtotal": subtotal,
            "toppings_seleccionados": toppings_procesados,
            "categoria_id": producto.categoria_id # Útil para validar reglas de cupón
        })

    # --- LÓGICA DE CUPONES ---
    descuento_aplicado = 0
    promocion_id = None
    
    if data.codigo_cupon:
        from app.services.promocion_service import PromocionService
        promo_service = PromocionService(session)
        # Validamos el cupón (Lanza excepción si es inválido)
        # Pasamos items procesados para reglas avanzadas si fuera necesario
        items_para_reglas = [{"categoria_id": i["categoria_id"], "producto_id": i["producto_id"]} for i in items_procesados]
        
        resultado = promo_service.validar_cupon(
            codigo=data.codigo_cupon, 
            negocio_id=negocio.id, 
            carrito_total=subtotal_productos,
            items=items_para_reglas
        )
        
        descuento_aplicado = int(resultado["descuento"])
        promocion_id = resultado["promocion"].id
        
        # Incrementar uso del cupón
        promo_service.aplicar_uso(promocion_id)

    total_final = max(0, subtotal_productos - descuento_aplicado)

    codigo = uuid4().hex[:6].upper()
    pedido = Pedido(
        negocio_id=negocio.id,
        codigo=codigo,
        estado="pendiente",
        total=total_final,
        descuento_aplicado=descuento_aplicado,
        promocion_id=promocion_id,
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

