from uuid import uuid4
from sqlmodel import Session, select
from app.models.models import Negocio, Pedido, PedidoItem, Producto, TipoNegocio
from app.schemas.pedido import PedidoCreate
from app.core.exceptions import EntityNotFoundError, BusinessLogicError, PermissionDeniedError
from app.services.topping_service import (
    obtener_toppings_para_varios_productos,
    validar_toppings_con_config
)


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
    
    # --- LOGICA DE PROCESAMIENTO DE ITEMS (OPTIMIZADA) ---
    subtotal_productos = 0

    # 1. Identificar todos los productos y toppings requeridos
    producto_ids = {item.producto_id for item in data.items}
    
    # 2. Cargar todos los productos en una sola consulta
    productos = session.exec(select(Producto).where(Producto.id.in_(producto_ids))).all()
    productos_map = {p.id: p for p in productos}
    
    # 3. Validar existencia de todos los productos y pertenencia al negocio
    for item in data.items:
        if item.producto_id not in productos_map:
            raise EntityNotFoundError(f"Producto {item.producto_id} no encontrado")
        
        producto = productos_map[item.producto_id]
        if producto.negocio_id != negocio.id:
            raise EntityNotFoundError(f"Producto {item.producto_id} no pertenece al negocio")
            
        if not producto.stock:
            raise BusinessLogicError(f"El producto '{producto.nombre}' no tiene stock disponible")

    # 4. Cargar configuraciones de toppings para todos los productos involucrados
    configs_map = obtener_toppings_para_varios_productos(session, list(producto_ids))

    # 5. Procesar items usando datos en memoria
    es_distribuidora = negocio.tipo_negocio == TipoNegocio.DISTRIBUIDORA
    for item in data.items:
        if item.cantidad <= 0:
            raise BusinessLogicError("La cantidad de los productos debe ser mayor a 0")

        producto = productos_map[item.producto_id]

        # Validar cantidad mínima por producto (solo distribuidoras)
        if es_distribuidora and item.cantidad < producto.cantidad_minima:
            raise BusinessLogicError(
                f"La cantidad mínima para '{producto.nombre}' es {producto.cantidad_minima} {producto.unidad}(s)"
            )
        
        # Validar y procesar toppings
        toppings_procesados = []
        precio_toppings = 0
        if item.toppings:
            toppings_dict = [t.model_dump() for t in item.toppings]
            # Obtener config para este producto (o lista vacía si no tiene)
            item_configs = configs_map.get(producto.id, [])
            
            toppings_procesados, precio_toppings = validar_toppings_con_config(
                item_configs, toppings_dict
            )

        # Calcular precio: usar precio mayorista si aplica (solo distribuidoras)
        precio_base = producto.precio
        if (
            es_distribuidora
            and producto.precio_mayorista is not None
            and producto.cantidad_mayorista is not None
            and item.cantidad >= producto.cantidad_mayorista
        ):
            precio_base = producto.precio_mayorista

        # Calcular subtotal: (precio_base + precio_toppings) * cantidad
        precio_unitario_total = precio_base + precio_toppings
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
            "categoria_id": producto.categoria_id 
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

    # Validar pedido mínimo (solo distribuidoras)
    if (
        negocio.tipo_negocio == TipoNegocio.DISTRIBUIDORA
        and negocio.pedido_minimo > 0
        and total_final < negocio.pedido_minimo
    ):
        raise BusinessLogicError(
            f"El pedido mínimo para este negocio es ${negocio.pedido_minimo}"
        )

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
        direccion_entrega=data.direccion_entrega,
        notas=data.notas,
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

