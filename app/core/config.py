from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import validator
from typing import Optional

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding='utf-8',
        extra='ignore'
    )

    # --- API Keys ---
    GOOGLE_API_KEY: str
    GROQ_API_KEY: str

    # --- RAG/LLM Settings ---
    CHUNK_SIZE: int = 1000
    CHUNK_OVERLAP: int = 200
    LLM_MODEL_NAME: str = "llama3-8b-8192"
    EMBEDDING_MODEL_NAME: str = "models/embedding-001"

    # --- Database Settings ---
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_PORT: int = 5432
    DATABASE_URL: Optional[str] = None

    @validator("DATABASE_URL", pre=True, always=True)
    def assemble_db_connection(cls, v: Optional[str], values: dict) -> str:
        if isinstance(v, str):
            return v
        return (
            f"postgresql://{values.get('POSTGRES_USER')}:{values.get('POSTGRES_PASSWORD')}"
            f"@{values.get('POSTGRES_SERVER')}:{values.get('POSTGRES_PORT')}/{values.get('POSTGRES_DB')}"
        )

    # --- AWS S3 Settings ---
    S3_BUCKET_NAME: str
    AWS_REGION: str
    # These are optional because we will use an IAM role on EC2
    AWS_ACCESS_KEY_ID: Optional[str] = None
    AWS_SECRET_ACCESS_KEY: Optional[str] = None
    
    # --- JWT/Authentication Settings ---
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24

    # --- Vector Store Path ---
    CHROMA_PATH: str = "/app/chroma_data"
    
    # --- Celery ---
    CELERY_BROKER_URL: str = "redis://redis:6379/0"

settings: Settings = Settings()
