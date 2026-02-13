import openpyxl
from openpyxl import Workbook
import os

def generate_excel():
    wb = Workbook()
    ws = wb.active
    ws.title = "Productos"

    # Headers match Key requirements: nombre, precio, sku, codigo_barras
    # Added optional text fields like descripcion, categoria for completeness
    headers = ["nombre", "precio", "sku", "codigo_barras", "descripcion", "categoria", "stock", "destacado"]
    ws.append(headers)

    # Sample Data
    data = [
        ["Hamburguesa Royal", 4500, "HAM-ROY", "779123450001", "Doble carne, cheddar, bacon y huevo", "Hamburguesas", "si", "si"],
        ["Papas Cheddar", 3200, "PAP-CHE", "779123450002", "Papas fritas con salsa cheddar y verdeo", "Acompañamientos", "si", "no"],
        ["Lata Cola 354ml", 1500, "BEB-COL", "779123450003", "Gaseosa cola bien fría", "Bebidas", "si", "no"],
        ["Pizza Napolitana", 5800, "PIZ-NAP", "", "Salsa, muzzarella, tomate y ajo", "Pizzas", "si", "si"],
        ["Helado 1kg", 6000, "POS-HEL", "", "Sabores a elección", "Postres", "si", "no"]
    ]

    for row in data:
        ws.append(row)

    # Output path
    output_file = os.path.join(os.getcwd(), "productos_ejemplo.xlsx")
    wb.save(output_file)
    print(f"Excel generado exitosamente en: {output_file}")

if __name__ == "__main__":
    generate_excel()
