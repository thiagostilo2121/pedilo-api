import openpyxl
from typing import BinaryIO, Any
from sqlmodel import Session, select
from app.models.models import Producto, Categoria
import requests
from app.utils.cloudinary import subir_imagen
from io import BytesIO

class ImportService:
    def _fetch_image_from_barcode(self, barcode: str) -> str | None:
        """
        Consulta Open Food Facts para obtener la imagen del producto.
        Si la encuentra, la sube a Cloudinary y devuelve la URL segura.
        """
        try:
            url = f"https://world.openfoodfacts.org/api/v0/product/{barcode}.json"
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == 1:
                    product = data.get("product", {})
                    image_url = product.get("image_front_url") or product.get("image_url")
                    
                    if image_url:
                        # Descargar la imagen
                        img_resp = requests.get(image_url, timeout=10)
                        if img_resp.status_code == 200:
                            # Subir a Cloudinary
                            # subir_imagen espera un archivo, podemos usar BytesIO
                            # PERO: subir_imagen espera un UploadFile o similar que tenga .file
                            # Vamos a revisar subir_imagen en utils/cloudinary.py
                            # Dice: result = cloudinary.uploader.upload(file)
                            # cloudinary.uploader.upload acepta file-like obj o path.
                            
                            img_file = BytesIO(img_resp.content)
                            img_file.name = f"{barcode}.jpg" # Cloudinary a veces usa el nombre
                            
                            secure_url = subir_imagen(img_file)
                            return secure_url
        except Exception as e:
            print(f"Error fetching image for barcode {barcode}: {e}")
        return None

    def _parse_stock(self, value: Any) -> bool:
        if value is None:
            return True # Default to True if not specified? Or False? Usually True for products.
        
        if isinstance(value, bool):
            return value
        
        if isinstance(value, (int, float)):
            return value >= 1
            
        if isinstance(value, str):
            v_lower = value.lower().strip()
            if v_lower in ["si", "sí", "true", "verdadero", "1", "s"]:
                return True
            return False
            
        return True

    def process_excel_file(self, file: BinaryIO, negocio_id: int, db: Session) -> dict[str, Any]:
        workbook = openpyxl.load_workbook(file)
        sheet = workbook.active
        
        # Pre-fetch categories
        cats = db.exec(select(Categoria).where(Categoria.negocio_id == negocio_id)).all()
        cat_map = {c.nombre.lower().strip(): c.id for c in cats}
        
        # Ensure 'Otros' category exists (or get it ready to use)
        otros_id = cat_map.get("otros")
        if not otros_id:
            otros_cat = Categoria(negocio_id=negocio_id, nombre="Otros", activo=True)
            db.add(otros_cat)
            db.commit()
            db.refresh(otros_cat)
            otros_id = otros_cat.id
            cat_map["otros"] = otros_id

        
        # Get headers from first row
        headers = []
        for cell in sheet[1]:
            headers.append(cell.value)
            
        header_map = {str(h).lower(): i for i, h in enumerate(headers) if h}
        
        stats: dict[str, Any] = {"created": 0, "updated": 0, "errors": []}
        
        # Helper to get value from row safely
        def get_val(row: tuple, col_name: str) -> Any:
            idx = header_map.get(col_name)
            if idx is not None and idx < len(row):
                return row[idx].value
            return None

        # Iterate rows starting from 2
        for row_idx, row in enumerate(sheet.iter_rows(min_row=2), start=2):
            try:
                sku = get_val(row, "sku")
                codigo_barras = get_val(row, "codigo_barras") or get_val(row, "barcode")
                nombre = get_val(row, "nombre") or get_val(row, "producto") or get_val(row, "name")
                precio = get_val(row, "precio") or get_val(row, "price")
                
                # New fields
                descripcion = get_val(row, "descripcion") or get_val(row, "description")
                stock_val = get_val(row, "stock")
                categoria_nombre = get_val(row, "categoria") or get_val(row, "category")
                
                # Resolve Category ID
                categoria_id = otros_id
                if categoria_nombre:
                    cat_key = str(categoria_nombre).lower().strip()
                    if cat_key in cat_map:
                        categoria_id = cat_map[cat_key]
                    else:
                        # Required to fall back to 'Otros' as per request
                        categoria_id = otros_id

                # Convert to string if they are numbers
                if sku: sku = str(sku)
                if codigo_barras: codigo_barras = str(codigo_barras)
                
                if not nombre:
                   # Skip empty rows
                   if not sku and not codigo_barras and not precio:
                       continue
                   stats["errors"].append(f"Row {row_idx}: Missing product name")
                   continue
                
                # Try to find existing product
                existing_product = None
                
                # Check 1: SKU
                if sku:
                    existing_product = db.exec(
                        select(Producto).where(Producto.negocio_id == negocio_id, Producto.sku == sku)
                    ).first()
                
                # Check 2: Barcode
                if not existing_product and codigo_barras:
                    existing_product = db.exec(
                        select(Producto).where(Producto.negocio_id == negocio_id, Producto.codigo_barras == codigo_barras)
                    ).first()
                
                # Check 3: Name (Exact match)
                if not existing_product:
                    existing_product = db.exec(
                        select(Producto).where(Producto.negocio_id == negocio_id, Producto.nombre == str(nombre))
                    ).first()

                if existing_product:
                    # Check if inactive -> Treat as creation (Reactivation)
                    is_reactivation = not existing_product.activo
                    
                    if precio is not None:
                        existing_product.precio = int(float(precio))
                    if sku:
                        existing_product.sku = sku
                    if codigo_barras:
                        existing_product.codigo_barras = codigo_barras
                    if nombre:
                        existing_product.nombre = str(nombre)
                    if descripcion:
                        existing_product.descripcion = str(descripcion)
                    if stock_val is not None:
                        existing_product.stock = self._parse_stock(stock_val)
                    
                    # Always update category if provided, or if we fallback? 
                    # Request says: "cat must exist, otherwise 'Otros'". 
                    # If column exists, we update. 
                    if categoria_id: 
                         existing_product.categoria_id = categoria_id

                    if is_reactivation:
                        existing_product.activo = True
                        stats["created"] += 1 # User requested to count as created
                    else:
                        stats["updated"] += 1
                    
                    db.add(existing_product)
                    target_product = existing_product
                else:
                    # Create
                    if precio is None:
                         stats["errors"].append(f"Row {row_idx}: Missing price for new product '{nombre}'")
                         continue

                    new_product = Producto(
                        negocio_id=negocio_id,
                        nombre=str(nombre),
                        precio=int(float(precio)),
                        sku=sku,
                        codigo_barras=codigo_barras,
                        activo=True,
                        stock=self._parse_stock(stock_val),
                        descripcion=str(descripcion) if descripcion else None,
                        categoria_id=categoria_id
                    )
                    db.add(new_product)
                    stats["created"] += 1
                    target_product = new_product
                
                # Image Enrichment
                if target_product and target_product.codigo_barras and not target_product.imagen_url:
                    image_url = self._fetch_image_from_barcode(target_product.codigo_barras)
                    if image_url:
                        target_product.imagen_url = image_url
                        db.add(target_product) # Ensure it's marked for update

            except Exception as e:
                stats["errors"].append(f"Row {row_idx}: {str(e)}")
        
        # Second pass or inline? We can do inline.
        # Check newly created or updated object for image.
        # However, we are inside the loop. Let's do it inside the loop.
        
        db.commit() # Commit to get IDs if needed, but we have objects attached to session.
        
        # Enrichment step (Iterate again or do it in the loop? In loop is better for simple logic, 
        # but existing_product might be detached? No, it's in session.)
        
        # Let's adjust the logic slightly to do it within the loop for `existing_product` or `new_product`
        # But `process_excel_file` already finished the loop in the previous code.
        # I need to insert the logic BEFORE db.commit() and INSIDE the loop.
        # The replacement request above replaces the WHOLE method? No, just insertion of helper.
        # I need another chunk to insert the logic inside the loop.

        
        db.commit()
        return stats
