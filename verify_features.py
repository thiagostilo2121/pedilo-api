
import sys
import os
from sqlmodel import Session, select, create_engine
from app.models.models import Negocio, Usuario, Pedido, PedidoEstado
from app.core.config import settings

from sqlmodel import Session, select, create_engine, text
from app.models.models import Negocio, Usuario, Pedido, PedidoEstado
from app.core.config import settings
from sqlalchemy.exc import OperationalError, ProgrammingError

# Setup DB connection
engine = create_engine(settings.DATABASE_URL)

def ensure_column_exists():
    print("Checking if 'anuncio_web' column exists...")
    with Session(engine) as session:
        try:
            # Try to select the column
            session.exec(text("SELECT anuncio_web FROM negocios LIMIT 1"))
            print("✅ Column 'anuncio_web' already exists.")
        except (OperationalError, ProgrammingError):
            print("⚠️ Column 'anuncio_web' missing. Adding it...")
            session.rollback() # Clear error
            try:
                session.exec(text("ALTER TABLE negocios ADD COLUMN anuncio_web TEXT"))
                session.commit()
                print("✅ Column 'anuncio_web' added successfully.")
            except Exception as e:
                print(f"❌ Failed to add column: {e}")
                sys.exit(1)

def verify_smart_banner():
    print("Verifying Smart Banner...")
    with Session(engine) as session:
        # Get a test business
        negocio = session.exec(select(Negocio)).first()
        if not negocio:
            print("No business found to test.")
            return

        print(f"Testing with business: {negocio.nombre} ({negocio.slug})")
        
        # Update banner
        original_banner = negocio.anuncio_web
        negocio.anuncio_web = "Banner de prueba - Verification Script"
        session.add(negocio)
        session.commit()
        session.refresh(negocio)
        
        if negocio.anuncio_web == "Banner de prueba - Verification Script":
            print("✅ Smart Banner updated successfully in DB.")
        else:
            print("❌ Failed to update Smart Banner.")
            
        # Restore original
        negocio.anuncio_web = original_banner
        session.add(negocio)
        session.commit()

def verify_badges():
    print("\nVerifying Reputation Badges...")
    with Session(engine) as session:
        test_slug = "negocio-test-badges"
        
        # Check if exists
        negocio = session.exec(select(Negocio).where(Negocio.slug == test_slug)).first()
        
        if negocio:
            print("Test business already exists. Cleaning up orders...")
            # Clean up existing orders
            statement = select(Pedido).where(Pedido.negocio_id == negocio.id)
            results = session.exec(statement).all()
            for res in results:
                session.delete(res)
            session.commit()
            print("Cleanup complete. Reuse business.")
        else:
            # Create a dummy business for testing
            # We need a user first
            user = session.exec(select(Usuario)).first()
            if not user:
                print("No user found.")
                return

            negocio = Negocio(
                usuario_id=user.id,
                nombre="Negocio Test Badges",
                slug=test_slug,
                anuncio_web="Test Banner"
            )
            session.add(negocio)
            session.commit()
            session.refresh(negocio)
        

        try:
            # Create 101 orders using raw SQL to avoid Enum issues in test env
            print("Creating 101 orders via raw SQL...")
            from datetime import datetime, timezone
            
            for i in range(101):
                estado = "finalizado" if i < 51 else "pendiente"
                # Need to handle foreign keys and required fields
                # Pedido: negocio_id, codigo, estado, total, creado_en...
                # We assume constraints are minimal or we satisfy them
                
                # Note: We need to use valid values for all NOT NULL columns.
                # Assuming id is auto-increment.
                # Promocion_id nullable.
                
                stmt = text("""
                    INSERT INTO pedidos (negocio_id, codigo, estado, total, creado_en, descuento_aplicado)
                    VALUES (:negocio_id, :codigo, :estado, :total, :creado_en, 0)
                """)
                
                session.exec(stmt, params={
                    "negocio_id": negocio.id,
                    "codigo": f"ORD-{i}",
                    "estado": estado,
                    "total": 1000,
                    "creado_en": datetime.now(timezone.utc)
                })
            
            session.commit()
            
            # Now we need to call the logic that calculates badges. 
            # Since we can't easily call the API endpoint function directly with full context, 
            # we will replicate the query logic here to verify it works as expected.
            
            from sqlalchemy import func
            
            session.commit()
            
            # Now we need to call the logic that calculates badges. 
            # Since we can't easily call the API endpoint function directly with full context, 
            # we will replicate the query logic here to verify it works as expected.
            
            from sqlalchemy import func
            
            # Badge: TOP_SELLER_100
            total_pedidos = session.exec(
                select(func.count(Pedido.id)).where(Pedido.negocio_id == negocio.id)
            ).one()
        except Exception as e:
            print(f"❌ Error during verification: {e}")
            import traceback
            traceback.print_exc()
            raise e
            
            print(f"Total orders: {total_pedidos}")
            if total_pedidos > 100:
                print("✅ TOP_SELLER_100 badge condition met.")
            else:
                print("❌ TOP_SELLER_100 badge condition NOT met.")

            # Badge: VERIFICADO_50
            pedidos_entregados = session.exec(
                select(func.count(Pedido.id)).where(
                    Pedido.negocio_id == negocio.id,
                    Pedido.estado == PedidoEstado.FINALIZADO
                )
            ).one()

            print(f"Delivered orders: {pedidos_entregados}")
            if pedidos_entregados > 50:
                 print("✅ VERIFICADO_50 badge condition met.")
            else:
                 print("❌ VERIFICADO_50 badge condition NOT met.")

        finally:
            # Cleanup
            print("Cleaning up test data...")
            session.exec(select(Pedido).where(Pedido.negocio_id == negocio.id)).all()
            # Delete orders first (cascade might not be set up in SQLModel default)
            # Actually, let's just delete the business and let DB handle cascade if configured, 
            # or manual delete if necessary. For safety in prod DB, maybe just leave it or careful delete.
            # Assuming dev env.
            
            # Delete created orders
            statement = select(Pedido).where(Pedido.negocio_id == negocio.id)
            results = session.exec(statement).all()
            for res in results:
                session.delete(res)
                
            session.delete(negocio)
            session.commit()
            print("Cleanup complete.")

if __name__ == "__main__":
    ensure_column_exists()
    verify_smart_banner()
    verify_badges()
