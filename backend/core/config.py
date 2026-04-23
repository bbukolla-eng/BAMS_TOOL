from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Application
    app_env: str = "development"
    secret_key: str = "change-me"
    debug: bool = False
    allowed_origins: list[str] = ["http://localhost:3000", "http://localhost:5173"]
    api_prefix: str = "/api/v1"

    # Database
    database_url: str = "postgresql+asyncpg://bams:bams_dev_password@localhost:5432/bams"
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "bams"
    postgres_user: str = "bams"
    postgres_password: str = "bams_dev_password"

    # Redis
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"

    # Object Storage
    storage_backend: str = "minio"  # "local" or "minio"
    local_storage_path: str = "./storage"
    storage_endpoint: str = "localhost:9000"
    storage_access_key: str = "minioadmin"
    storage_secret_key: str = "minioadmin"
    storage_bucket: str = "bams"
    storage_use_ssl: bool = False
    use_s3: bool = False

    # Anthropic
    anthropic_api_key: str = ""
    claude_model: str = "claude-sonnet-4-6"
    claude_max_tokens: int = 4096

    # ML Models
    ml_models_path: str = "./ml_models"
    yolo_confidence_threshold: float = 0.45
    yolo_iou_threshold: float = 0.45
    embedding_model: str = "sentence-transformers/all-mpnet-base-v2"

    # ODA File Converter
    oda_converter_path: str = "/usr/local/bin/OdaFileConverter"

    # Email
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    from_email: str = "noreply@bams.ai"

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def sync_database_url(self) -> str:
        return self.database_url.replace("postgresql+asyncpg", "postgresql+psycopg2")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
