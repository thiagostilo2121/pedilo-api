from datetime import datetime, timezone
from sqlmodel import Session, select
from app.models.models import Promocion, PromocionTipo, Pedido, Negocio
from fastapi import HTTPException

class PromocionService:
    def __init__(self, session: Session):
        self.session = session

    def validar_cupon(self, codigo: str, negocio_id: int, carrito_total: float, items: list[dict]):
        """
        Valida si un cupón es aplicable a un carrito.
        Retorna el monto de descuento y el objeto Promocion si es válido.
        Lanza HTTPException si no es válido.
        """
        # 1. Buscar la promoción (Case Insensitive)
        # Traemos todas las activas del negocio y filtramos en python para evitar lios con collactions/db specifics
        promos = self.session.exec(
            select(Promocion).where(
                Promocion.negocio_id == negocio_id,
                Promocion.activo == True
            )
        ).all()
        
        promo = next((p for p in promos if p.codigo.lower() == codigo.lower()), None)

        if not promo:
            raise HTTPException(status_code=404, detail="Cupón no válido o inexistente")

        # 2. Validar fechas
        now = datetime.now(timezone.utc)
        
        # Asegurar que las fechas de la DB tengan timezone (asumimos UTC si son naive)
        p_inicio = promo.fecha_inicio
        if p_inicio.tzinfo is None:
            p_inicio = p_inicio.replace(tzinfo=timezone.utc)
            
        if p_inicio > now:
            raise HTTPException(status_code=400, detail="El cupón aún no está activo")
            
        if promo.fecha_fin:
            p_fin = promo.fecha_fin
            if p_fin.tzinfo is None:
                p_fin = p_fin.replace(tzinfo=timezone.utc)
            
            if p_fin < now:
                raise HTTPException(status_code=400, detail="El cupón ha expirado")

        # 3. Validar límites de uso
        if promo.limite_usos_total and promo.usos_actuales >= promo.limite_usos_total:
             raise HTTPException(status_code=400, detail="Este cupón ha alcanzado su límite de usos")

        # 4. Validar reglas específicas (JSON)
        reglas = promo.reglas or {}
        
        # Mínimo de compra
        min_compra = reglas.get("min_compra", 0)
        if carrito_total < min_compra:
             raise HTTPException(status_code=400, detail=f"El monto mínimo para este cupón es ${min_compra}")

        # 5. Calcular Descuento
        descuento = 0
        if promo.tipo == PromocionTipo.PORCENTAJE:
            descuento = carrito_total * (promo.valor / 100)
            # Tope máximo de descuento (opcional en reglas)
            tope = reglas.get("tope_maximo")
            if tope and descuento > tope:
                descuento = tope

        elif promo.tipo == PromocionTipo.MONTO_FIJO:
            descuento = promo.valor

        elif promo.tipo == PromocionTipo.ENVIO_GRATIS:
            # El frontend/controlador debe saber que el envío es 0
            # Aquí podríamos retornar un flag o el valor del envío si lo tuviéramos
            descuento = 0 # Se maneja en el total final restando el costo de envío
            
        elif promo.tipo == PromocionTipo.DOS_POR_UNO:
             # Lógica 2x1: Por cada 2 unidades del mismo producto, 1 es gratis (se descuenta su precio)
             # Iteramos los items para calcular cuantos pares hay
             descuento_total_2x1 = 0
             for item in items:
                 # item es un dict con {producto_id, cantidad, precio_unitario, ...}
                 cantidad = item.get("cantidad", 0)
                 precio = item.get("precio_unitario", 0)
                 
                 # Si la promo tiene reglas de productos especificos, filtrar aqui
                 # Por simplicidad asumimos que si es 2x1 global, aplica a todo. 
                 # Si hay 'productos_ids' en reglas, validamos.
                 productos_validos = reglas.get("productos_ids")
                 if productos_validos and item.get("producto_id") not in productos_validos:
                     continue
                     
                 # Pares gratis = cantidad // 2
                 pares_gratis = cantidad // 2
                 descuento_total_2x1 += pares_gratis * precio
             
             descuento = descuento_total_2x1

        # Validar que el descuento no supere el total (excepto envío gratis que es otro concepto)
        if promo.tipo != PromocionTipo.ENVIO_GRATIS and descuento > carrito_total:
            descuento = carrito_total

        return {
            "valido": True,
            "descuento": descuento,
            "promocion": promo,
            "mensaje": f"Cupón {codigo} aplicado con éxito"
        }

    def aplicar_uso(self, promocion_id: int):
        """Incrementa el contador de uso de una promoción"""
        promo = self.session.get(Promocion, promocion_id)
        if promo:
            promo.usos_actuales += 1
            self.session.add(promo)
            self.session.commit()
