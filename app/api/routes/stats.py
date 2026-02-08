from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select, func, desc, col
from sqlalchemy import cast, Date, text

from app.api.deps import get_session, get_current_user_negocio
from app.models.models import Negocio, Pedido, PedidoItem, Producto, Usuario

router = APIRouter(prefix="/api/stats", tags=["Estadísticas"])

@router.get("/overview")
def get_stats_overview(
    session: Session = Depends(get_session),
    current_user_negocio: Negocio = Depends(get_current_user_negocio)
):
    """
    Retorna métricas clave del negocio para el dashboard.
    - Ventas Totales (Hoy)
    - Pedidos (Hoy)
    - Ticket Promedio (Histórico)
    - Tasa de Conversión (Simulada por ahora)
    """
    negocio = current_user_negocio
    
    # Fechas
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    
    # Ventas Hoy & Pedidos Hoy
    query_today = select(func.sum(Pedido.total), func.count(Pedido.id))\
        .where(Pedido.negocio_id == negocio.id)\
        .where(Pedido.creado_en >= today_start)\
        .where(Pedido.estado != "rechazado") # Excluir rechazados? O incluir solo finalizados? Generalmente "Ventas" son confirmadas.
        # Vamos a incluir todos menos rechazados y pendientes para "Ventas" reales?
        # Para "Pedidos" (cantidad) quizas todos sirven para ver demanda.
        # Ajuste: Ventas = Aceptado, En Progreso, Finalizado
    
    sales_today_query = select(func.sum(Pedido.total), func.count(Pedido.id))\
        .where(Pedido.negocio_id == negocio.id)\
        .where(Pedido.creado_en >= today_start)\
        .where(col(Pedido.estado).in_(["aceptado", "en_progreso", "finalizado"]))

    sales_today, orders_today = session.exec(sales_today_query).one() or (0, 0)
    
    # Ticket Promedio Histórico
    avg_ticket_query = select(func.avg(Pedido.total))\
        .where(Pedido.negocio_id == negocio.id)\
        .where(col(Pedido.estado).in_(["aceptado", "en_progreso", "finalizado"]))
        
    avg_ticket = session.exec(avg_ticket_query).one() or 0
    
    # Pedidos Pendientes (Acción requerida)
    pending_orders = session.exec(
        select(func.count(Pedido.id))
        .where(Pedido.negocio_id == negocio.id, Pedido.estado == "pendiente")
    ).one()

    return {
        "ventas_hoy": sales_today or 0,
        "pedidos_hoy": orders_today or 0,
        "ticket_promedio": round(avg_ticket or 0, 2),
        "pedidos_pendientes": pending_orders or 0
    }

@router.get("/sales-chart")
def get_sales_chart(
    days: int = Query(7, ge=1, le=90),
    session: Session = Depends(get_session),
    current_user_negocio: Negocio = Depends(get_current_user_negocio)
):
    """
    Retorna datos de ventas agrupados por día para gráficos.
    """
    negocio = current_user_negocio
    end_date = datetime.now(timezone.utc)
    start_date = end_date - timedelta(days=days)
    
    # Query agrupada por fecha (cast a Date)
    # SQLite/Postgres compatibility note: func.date() works in standard SQL usually.
    # SQLModel/SQLAlchemy abstraction:
    
    # Postgres: cast(Pedido.creado_en, Date)
    
    results = session.exec(
        select(
            cast(Pedido.creado_en, Date).label("fecha"),
            func.sum(Pedido.total).label("total"),
            func.count(Pedido.id).label("cantidad")
        )
        .where(Pedido.negocio_id == negocio.id)
        .where(Pedido.creado_en >= start_date)
        .where(col(Pedido.estado).in_(["aceptado", "en_progreso", "finalizado"]))
        .group_by(cast(Pedido.creado_en, Date))
        .order_by(text("fecha") if "sqlite" in str(session.bind.url) else cast(Pedido.creado_en, Date)) 
    ).all()
    
    # Formatear
    data = []
    # Rellenar días vacíos? El front puede hacerlo, pero mejor aquí si es fácil.
    # Por rapidez, retornamos lo que hay.
    
    for row in results:
        data.append({
            "fecha": row.fecha.isoformat() if hasattr(row.fecha, 'isoformat') else str(row.fecha),
            "ventas": row.total,
            "pedidos": row.cantidad
        })
        
    return data

@router.get("/top-products")
def get_top_products(
    limit: int = 5,
    session: Session = Depends(get_session),
    current_user_negocio: Negocio = Depends(get_current_user_negocio)
):
    """
    Productos más vendidos (por cantidad).
    """
    negocio = current_user_negocio
    
    results = session.exec(
        select(
            PedidoItem.nombre_producto,
            func.sum(PedidoItem.cantidad).label("total_vendido"),
            func.sum(PedidoItem.subtotal).label("ingresos_generados")
        )
        .join(Pedido)
        .where(Pedido.negocio_id == negocio.id)
        .where(col(Pedido.estado).in_(["aceptado", "en_progreso", "finalizado"]))
        .group_by(PedidoItem.nombre_producto)
        .order_by(desc("total_vendido"))
        .limit(limit)
    ).all()
    
    return [
        {
            "nombre": row.nombre_producto,
            "cantidad": row.total_vendido,
            "ingresos": row.ingresos_generados
        }
        for row in results
    ]
