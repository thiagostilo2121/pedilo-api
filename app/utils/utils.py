import re
import unicodedata


def generar_slug(texto: str) -> str:
    # Normaliza acentos (á → a, ñ → n, etc.)
    texto = unicodedata.normalize("NFKD", texto)
    texto = texto.encode("ascii", "ignore").decode("ascii")

    # Pasa a minúsculas
    texto = texto.lower()

    # Reemplaza cualquier cosa que no sea letra o número por "-"
    texto = re.sub(r"[^a-z0-9]+", "-", texto)

    # Quita guiones al inicio y final
    texto = texto.strip("-")

    return texto
