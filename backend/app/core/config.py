from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    POSTGRES_HOST: str = "postgres"
    POSTGRES_PORT: int = 5432

    REDIS_URL: str = "redis://redis:6379/0"

    SECRET_KEY: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480

    BACKEND_CORS_ORIGINS: str = "http://localhost:3000"
    UPLOAD_DIR: str = "/app/uploads"
    MAX_UPLOAD_SIZE_MB: int = 100

    CELERY_TASK_ALWAYS_EAGER: bool = False

    # Parâmetros de estimativa energética (fórmula: área × irradiação × eficiência × (1-perdas) × 30)
    IRRADIACAO_LOCAL: float = 5.5   # kWh/m²/dia — São Luís-MA (média anual)
    EFICIENCIA_MEDIA: float = 0.18  # eficiência típica de painel fotovoltaico (18%)
    PERDAS_SISTEMA: float = 0.14    # perdas por cabeamento, inversor, sujeira etc.

    # Geolocalização — desativado por padrão para não impactar ambientes de teste
    # ENABLE_GEOCODING=true  → ativa geocodificação reversa (lat/lon → endereço)
    # GEOCODING_PER_PANEL=true → 1 consulta Nominatim por painel (lento, evite em produção)
    # GEOCODING_PER_PANEL=false (padrão) → 1 consulta por imagem, reutilizada para todos os painéis
    ENABLE_GEOCODING: bool = False
    GEOCODING_PER_PANEL: bool = False

    @property
    def DATABASE_URL(self) -> str:
        return (
            f"postgresql+psycopg2://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @property
    def CORS_ORIGINS(self) -> list[str]:
        return [o.strip() for o in self.BACKEND_CORS_ORIGINS.split(",")]

    class Config:
        env_file = ".env"


settings = Settings()
