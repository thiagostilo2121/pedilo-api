import cloudinary
import cloudinary.uploader
from app.core.config import settings
from urllib.parse import urlparse
from fastapi import HTTPException

cloudinary.config(
    cloud_name=settings.CLOUDINARY_CLOUD_NAME,
    api_key=settings.CLOUDINARY_API_KEY,
    api_secret=settings.CLOUDINARY_API_SECRET,
    secure=True,
)


def subir_imagen(file) -> str:
    """
    Sube una imagen a Cloudinary y devuelve la URL segura.
    `file` debe ser un UploadFile o archivo compatible.
    """
    try:
        result = cloudinary.uploader.upload(file)
        return result["secure_url"]
    except Exception as e:
        raise RuntimeError(f"Error al subir imagen: {str(e)}")
    
def validar_imagen_url(url: str | None) -> str | None:
    if not url:
        return None

    url = url.strip()
    if not url:
        return None

    parsed = urlparse(url)
    if not parsed.scheme or not parsed.netloc:
        raise HTTPException(status_code=400, detail="URL de imagen inválida")

    if not any(parsed.path.lower().endswith(ext) for ext in [".jpg", ".jpeg", ".png", ".webp"]):
        raise HTTPException(status_code=400, detail="La imagen debe ser JPG, PNG o WEBP")

    return url