from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Cloudinary
    CLOUDINARY_CLOUD_NAME: str
    CLOUDINARY_API_KEY: str
    CLOUDINARY_API_SECRET: str

    # Database & Security
    DATABASE_URL: str = "sqlite:///./dev.db"
    SECRET_KEY: str
    ALGORITHM: str = "HS256"

    # Mercado Pago
    MP_ACCESS_TOKEN: str | None = None
    MP_PLAN_ID: str | None = None

    class Config:
        env_file = ".env"

settings = Settings()
