from sqlmodel import Session, select
from sqlalchemy.orm import joinedload

from app.models.models import (
    GrupoTopping,
    Topping,
    ProductoGrupoTopping,
    Producto,
)
from app.schemas.topping import (
    GrupoToppingCreate,
    GrupoToppingUpdate,
    ToppingCreate,
    ToppingUpdate,
    ProductoGrupoToppingConfig,
)
from app.core.exceptions import EntityNotFoundError, BusinessLogicError


# ============ Grupos de Toppings ============

def crear_grupo_topping(
    session: Session, negocio_id: int, data: GrupoToppingCreate
) -> GrupoTopping:
    """Crea un grupo de toppings con toppings iniciales opcionales"""
    grupo = GrupoTopping(
        negocio_id=negocio_id,
        nombre=data.nombre,
    )
    session.add(grupo)
    session.flush()

    for topping_data in data.toppings:
        topping = Topping(
            grupo_id=grupo.id,
            nombre=topping_data.nombre,
            precio_extra=topping_data.precio_extra,
            disponible=topping_data.disponible,
        )
        session.add(topping)

    session.commit()
    session.refresh(grupo)
    return grupo


def listar_grupos_topping(session: Session, negocio_id: int) -> list[GrupoTopping]:
    """Lista todos los grupos de toppings activos de un negocio"""
    statement = (
        select(GrupoTopping)
        .where(GrupoTopping.negocio_id == negocio_id, GrupoTopping.activo == True)
        .options(joinedload(GrupoTopping.toppings))
    )
    return list(session.exec(statement).unique().all())


def obtener_grupo_topping(
    session: Session, grupo_id: int, negocio_id: int
) -> GrupoTopping:
    """Obtiene un grupo de toppings verificando pertenencia al negocio"""
    grupo = session.get(GrupoTopping, grupo_id)
    if not grupo or not grupo.activo or grupo.negocio_id != negocio_id:
        raise EntityNotFoundError("Grupo de toppings no encontrado")
    return grupo


def actualizar_grupo_topping(
    session: Session, grupo_id: int, negocio_id: int, data: GrupoToppingUpdate
) -> GrupoTopping:
    """Actualiza el nombre de un grupo de toppings"""
    grupo = obtener_grupo_topping(session, grupo_id, negocio_id)

    if data.nombre is not None:
        grupo.nombre = data.nombre

    if data.toppings is not None:
        for topping in grupo.toppings:
            if topping.activo:
                topping.activo = False
                session.add(topping)
        
        for topping_data in data.toppings:
            nuevo_topping = Topping(
                grupo_id=grupo.id,
                nombre=topping_data.nombre,
                precio_extra=topping_data.precio_extra,
                disponible=topping_data.disponible,
                activo=True
            )
            session.add(nuevo_topping)

    session.add(grupo)
    session.commit()
    session.refresh(grupo)
    return grupo


def eliminar_grupo_topping(session: Session, grupo_id: int, negocio_id: int) -> None:
    """Soft delete de un grupo de toppings"""
    grupo = obtener_grupo_topping(session, grupo_id, negocio_id)
    grupo.activo = False
    session.add(grupo)
    session.commit()


# ============ Toppings Individuales ============

def agregar_topping_a_grupo(
    session: Session, grupo_id: int, negocio_id: int, data: ToppingCreate
) -> Topping:
    """Agrega un topping a un grupo existente"""
    grupo = obtener_grupo_topping(session, grupo_id, negocio_id)

    topping = Topping(
        grupo_id=grupo.id,
        nombre=data.nombre,
        precio_extra=data.precio_extra,
        disponible=data.disponible,
    )
    session.add(topping)
    session.commit()
    session.refresh(topping)
    return topping


def actualizar_topping(
    session: Session, topping_id: int, negocio_id: int, data: ToppingUpdate
) -> Topping:
    """Actualiza un topping individual"""
    topping = session.get(Topping, topping_id)
    if not topping or not topping.activo:
        raise EntityNotFoundError("Topping no encontrado")

    grupo = session.get(GrupoTopping, topping.grupo_id)
    if not grupo or grupo.negocio_id != negocio_id:
        raise EntityNotFoundError("Topping no encontrado")

    if data.nombre is not None:
        topping.nombre = data.nombre
    if data.precio_extra is not None:
        topping.precio_extra = data.precio_extra
    if data.disponible is not None:
        topping.disponible = data.disponible

    session.add(topping)
    session.commit()
    session.refresh(topping)
    return topping


def eliminar_topping(session: Session, topping_id: int, negocio_id: int) -> None:
    """Soft delete de un topping"""
    topping = session.get(Topping, topping_id)
    if not topping or not topping.activo:
        raise EntityNotFoundError("Topping no encontrado")

    grupo = session.get(GrupoTopping, topping.grupo_id)
    if not grupo or grupo.negocio_id != negocio_id:
        raise EntityNotFoundError("Topping no encontrado")

    topping.activo = False
    session.add(topping)
    session.commit()


# ============ Producto-Topping Configuración ============

def configurar_toppings_producto(
    session: Session,
    producto_id: int,
    negocio_id: int,
    configs: list[ProductoGrupoToppingConfig],
) -> Producto:
    """Configura qué grupos de toppings aplican a un producto"""
    producto = session.get(Producto, producto_id)
    if not producto or not producto.activo or producto.negocio_id != negocio_id:
        raise EntityNotFoundError("Producto no encontrado")

    statement = select(ProductoGrupoTopping).where(
        ProductoGrupoTopping.producto_id == producto_id
    )
    existentes = session.exec(statement).all()
    for existente in existentes:
        session.delete(existente)

    for config in configs:
        grupo = session.get(GrupoTopping, config.grupo_id)
        if not grupo or not grupo.activo or grupo.negocio_id != negocio_id:
            raise EntityNotFoundError(f"Grupo de toppings {config.grupo_id} no encontrado")

        if config.min_selecciones > config.max_selecciones:
            raise BusinessLogicError(
                f"El mínimo de selecciones no puede ser mayor que el máximo "
                f"para el grupo '{grupo.nombre}'"
            )

        producto_grupo = ProductoGrupoTopping(
            producto_id=producto_id,
            grupo_id=config.grupo_id,
            min_selecciones=config.min_selecciones,
            max_selecciones=config.max_selecciones,
        )
        session.add(producto_grupo)

    session.commit()
    session.refresh(producto)
    return producto


def obtener_toppings_producto(
    session: Session, producto_id: int
) -> list[dict]:
    """Obtiene los grupos de toppings configurados para un producto"""
    statement = (
        select(ProductoGrupoTopping)
        .where(ProductoGrupoTopping.producto_id == producto_id)
        .options(joinedload(ProductoGrupoTopping.grupo).joinedload(GrupoTopping.toppings))
    )
    configs = session.exec(statement).unique().all()

    result = []
    for config in configs:
        if config.grupo.activo:
            toppings_activos = [t for t in config.grupo.toppings if t.activo]
            result.append({
                "grupo_id": config.grupo.id,
                "grupo_nombre": config.grupo.nombre,
                "min_selecciones": config.min_selecciones,
                "max_selecciones": config.max_selecciones,
                "toppings": [
                    {"id": t.id, "nombre": t.nombre, "precio_extra": t.precio_extra, "disponible": t.disponible}
                    for t in toppings_activos
                ],
            })
    return result


# ============ Validación de Toppings en Pedidos ============

def validar_toppings_seleccionados(
    session: Session,
    producto_id: int,
    toppings_seleccionados: list[dict],
) -> tuple[list[dict], int]:
    """
    Valida los toppings seleccionados contra la configuración del producto.
    Retorna la lista de toppings procesados y el precio total de toppings.
    """
    configs = obtener_toppings_producto(session, producto_id)

    if not configs and toppings_seleccionados:
        raise BusinessLogicError("Este producto no acepta toppings")

    topping_map = {}
    for config in configs:
        for topping in config["toppings"]:
            topping_map[topping["id"]] = {
                "nombre": topping["nombre"],
                "precio": topping["precio_extra"],
                "disponible": topping["disponible"],
                "grupo_id": config["grupo_id"],
                "grupo_nombre": config["grupo_nombre"],
                "min_selecciones": config["min_selecciones"],
                "max_selecciones": config["max_selecciones"],
            }

    selecciones_por_grupo: dict[int, list[int]] = {}
    for sel in toppings_seleccionados:
        topping_id = sel.get("topping_id") or sel.get("id")
        if topping_id not in topping_map:
            raise BusinessLogicError(f"Topping {topping_id} no disponible para este producto")
        
        if not topping_map[topping_id]["disponible"]:
            raise BusinessLogicError(f"El topping '{topping_map[topping_id]['nombre']}' no está disponible")

        grupo_id = topping_map[topping_id]["grupo_id"]
        if grupo_id not in selecciones_por_grupo:
            selecciones_por_grupo[grupo_id] = []
        selecciones_por_grupo[grupo_id].append(topping_id)

    for config in configs:
        grupo_id = config["grupo_id"]
        seleccionados = selecciones_por_grupo.get(grupo_id, [])
        cantidad = len(seleccionados)

        if cantidad < config["min_selecciones"]:
            raise BusinessLogicError(
                f"Debes seleccionar al menos {config['min_selecciones']} "
                f"opción(es) de '{config['grupo_nombre']}'"
            )
        if cantidad > config["max_selecciones"]:
            raise BusinessLogicError(
                f"Solo puedes seleccionar hasta {config['max_selecciones']} "
                f"opción(es) de '{config['grupo_nombre']}'"
            )

    toppings_procesados = []
    precio_total = 0
    for sel in toppings_seleccionados:
        topping_id = sel.get("topping_id") or sel.get("id")
        info = topping_map[topping_id]
        toppings_procesados.append({
            "nombre": info["nombre"],
            "precio": info["precio"],
        })
        precio_total += info["precio"]


def obtener_toppings_para_varios_productos(
    session: Session, producto_ids: list[int]
) -> dict[int, list[dict]]:
    """Obtiene los grupos de toppings configurados para múltiples productos, retornando un mapa {producto_id: configs}"""
    statement = (
        select(ProductoGrupoTopping)
        .where(ProductoGrupoTopping.producto_id.in_(producto_ids))
        .options(joinedload(ProductoGrupoTopping.grupo).joinedload(GrupoTopping.toppings))
    )
    configs = session.exec(statement).unique().all()
    
    result = {}
    # First, group by product_id
    temp_map = {}
    for config in configs:
        if config.grupo.activo:
            if config.producto_id not in temp_map:
                temp_map[config.producto_id] = []
            
            toppings_activos = [t for t in config.grupo.toppings if t.activo]
            temp_map[config.producto_id].append({
                "grupo_id": config.grupo.id,
                "grupo_nombre": config.grupo.nombre,
                "min_selecciones": config.min_selecciones,
                "max_selecciones": config.max_selecciones,
                "toppings": [
                    {"id": t.id, "nombre": t.nombre, "precio_extra": t.precio_extra, "disponible": t.disponible}
                    for t in toppings_activos
                ],
            })
            
    return temp_map


def validar_toppings_con_config(
    configs: list[dict],
    toppings_seleccionados: list[dict],
) -> tuple[list[dict], int]:
    """
    Valida los toppings seleccionados contra una configuración ya cargada en memoria.
    Retorna (toppings_procesados, precio_total).
    """
    if not configs and toppings_seleccionados:
        raise BusinessLogicError("Este producto no acepta toppings")

    topping_detail_map = {}
    for config in configs:
        for topping in config["toppings"]:
            topping_detail_map[topping["id"]] = {
                "nombre": topping["nombre"],
                "precio": topping["precio_extra"],
                "disponible": topping["disponible"],
                "grupo_id": config["grupo_id"],
                "grupo_nombre": config["grupo_nombre"],
                "min_selecciones": config["min_selecciones"],
                "max_selecciones": config["max_selecciones"],
            }

    selecciones_por_grupo: dict[int, list[int]] = {}
    
    toppings_procesados = []
    precio_total = 0

    for sel in toppings_seleccionados:
        topping_id = sel.get("topping_id") or sel.get("id")
        
        if topping_id not in topping_detail_map:
            raise BusinessLogicError(f"Topping {topping_id} no disponible para este producto")
        
        info = topping_detail_map[topping_id]
        if not info["disponible"]:
            raise BusinessLogicError(f"El topping '{info['nombre']}' no está disponible")

        grupo_id = info["grupo_id"]
        if grupo_id not in selecciones_por_grupo:
            selecciones_por_grupo[grupo_id] = []
        selecciones_por_grupo[grupo_id].append(topping_id)
        
        toppings_procesados.append({
            "nombre": info["nombre"],
            "precio": info["precio"],
        })
        precio_total += info["precio"]

    # Validar restricciones de cantidad
    for config in configs:
        grupo_id = config["grupo_id"]
        seleccionados = selecciones_por_grupo.get(grupo_id, [])
        cantidad = len(seleccionados)

        if cantidad < config["min_selecciones"]:
            raise BusinessLogicError(
                f"Debes seleccionar al menos {config['min_selecciones']} "
                f"opción(es) de '{config['grupo_nombre']}'"
            )
        if cantidad > config["max_selecciones"]:
            raise BusinessLogicError(
                f"Solo puedes seleccionar hasta {config['max_selecciones']} "
                f"opción(es) de '{config['grupo_nombre']}'"
            )

    return toppings_procesados, precio_total