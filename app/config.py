from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # App
    APP_NAME: str = "EMAI-APP"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    # Base de datos
    DATABASE_URL: str = "mysql+pymysql://root:password@localhost:3306/emai_db"

    # JWT
    SECRET_KEY: str = "cambia_esta_clave_en_produccion"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 10080  # 7 días

    # CORS
    ALLOWED_ORIGINS: str = "http://localhost:8081,http://localhost:19006"

    # OCR
    TESSERACT_CMD: str = "/usr/bin/tesseract"
    OCR_LANG: str = "spa"

    @property
    def origins_list(self) -> list[str]:
        return [o.strip() for o in self.ALLOWED_ORIGINS.split(",")]

    class Config:
        env_file = ".env"
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
