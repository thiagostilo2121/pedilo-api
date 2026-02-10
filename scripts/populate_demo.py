import asyncio
from sqlmodel import Session, create_engine, select
from app.models.models import Negocio, Categoria, Producto, GrupoTopping, Topping, ProductoGrupoTopping
from app.core.config import settings

# Usar el motor configurado en la app
engine = create_engine(settings.DATABASE_URL)

async def create_demo_data():
    with Session(engine) as session:
        # 1. Obtener el Negocio ID 1 (Pedilo Oficial)
        negocio = session.get(Negocio, 1)
        if not negocio:
            print("Negocio ID 1 no encontrado.")
            return

        print(f"Poblando datos para: {negocio.nombre}")

        # 2. Crear Categorías
        categorias_nombres = ["Pizzas", "Hamburguesas", "Bebidas", "Postres"]
        categorias = {}
        for nombre in categorias_nombres:
            cat = session.exec(select(Categoria).where(Categoria.negocio_id == 1, Categoria.nombre == nombre)).first()
            if not cat:
                cat = Categoria(negocio_id=1, nombre=nombre, activo=True)
                session.add(cat)
                session.flush()
            categorias[nombre] = cat

        # 3. Crear Grupo de Toppings (Extras)
        grupo_extras = session.exec(select(GrupoTopping).where(GrupoTopping.negocio_id == 1, GrupoTopping.nombre == "Extras Pizza")).first()
        if not grupo_extras:
            grupo_extras = GrupoTopping(negocio_id=1, nombre="Extras Pizza", activo=True)
            session.add(grupo_extras)
            session.flush()
        
        toppings_data = [
            ("Queso Extra", 500),
            ("Bacon", 400),
            ("Huevo Frito", 300)
        ]
        
        toppings_objs = []
        for nombre, precio in toppings_data:
            t = session.exec(select(Topping).where(Topping.grupo_id == grupo_extras.id, Topping.nombre == nombre)).first()
            if not t:
                t = Topping(grupo_id=grupo_extras.id, nombre=nombre, precio_extra=precio, activo=True, disponible=True)
                session.add(t)
                session.flush()
            toppings_objs.append(t)

        # 4. Crear Productos
        productos_data = [
            ("Pizza Muzza", "Salsa de tomate, muzzarella y olivas.", 8500, "Pizzas", True),
            ("Pizza Napolitana", "Salsa, muzza, rodajas de tomate y ajo.", 9500, "Pizzas", True),
            ("Hamburguesa Simple", "Carne, queso y pan artesanal.", 7000, "Hamburguesas", True),
            ("Hamburguesa Completa", "Carne, queso, bacon, huevo y lechuga.", 9000, "Hamburguesas", True),
            ("Coca-Cola 1.5L", "Gaseosa refrescante.", 2500, "Bebidas", False),
            ("Agua Mineral 500ml", "Agua sin gas.", 1200, "Bebidas", False),
            ("Flan con Dulce", "Postre casero.", 2000, "Postres", False),
            ("Helado 1/4kg", "Sabores a elección.", 3500, "Postres", False),
        ]

        for nombre, desc, precio, cat_nombre, con_toppings in productos_data:
            p = session.exec(select(Producto).where(Producto.negocio_id == 1, Producto.nombre == nombre)).first()
            if not p:
                p = Producto(
                    negocio_id=1,
                    categoria_id=categorias[cat_nombre].id,
                    nombre=nombre,
                    descripcion=desc,
                    precio=precio,
                    activo=True,
                    stock=True,
                    destacado=True if "Completa" in nombre or cat_nombre == "Pizzas" else False
                )
                session.add(p)
                session.flush()
            
            # Asociar toppings si corresponde
            if con_toppings:
                config = session.exec(select(ProductoGrupoTopping).where(
                    ProductoGrupoTopping.producto_id == p.id,
                    ProductoGrupoTopping.grupo_id == grupo_extras.id
                )).first()
                if not config:
                    config = ProductoGrupoTopping(
                        producto_id=p.id,
                        grupo_id=grupo_extras.id,
                        min_selecciones=0,
                        max_selecciones=3
                    )
                    session.add(config)

        session.commit()
        print("Datos de DEMO creados exitosamente.")

if __name__ == "__main__":
    asyncio.run(create_demo_data())
