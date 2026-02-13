from sqlalchemy import text
from app.core.database import engine

def migrate():
    with engine.connect() as conn:
        print("Migrating products table...")
        try:
            conn.execute(text("ALTER TABLE productos ADD COLUMN sku VARCHAR(255);"))
            print("Added sku column.")
        except Exception as e:
            print(f"Skipping sku (might exist): {e}")

        try:
            conn.execute(text("CREATE INDEX ix_productos_sku ON productos (sku);"))
            print("Created sku index.")
        except Exception as e:
             print(f"Skipping sku index: {e}")

        try:
            conn.execute(text("ALTER TABLE productos ADD COLUMN codigo_barras VARCHAR(255);"))
            print("Added codigo_barras column.")
        except Exception as e:
            print(f"Skipping codigo_barras (might exist): {e}")

        try:
            conn.execute(text("CREATE INDEX ix_productos_codigo_barras ON productos (codigo_barras);"))
            print("Created codigo_barras index.")
        except Exception as e:
             print(f"Skipping codigo_barras index: {e}")
             
        conn.commit()
        print("Migration complete.")

if __name__ == "__main__":
    migrate()
