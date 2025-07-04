from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import validator, Field
from typing import Optional

class Settings(BaseSettings):
    """
    Application configuration settings loaded from environment variables.
    """
    # --- Pydantic Model Config ---
    # This replaces the old `class Config:` and is the modern Pydantic v2 way.
    # It also tells Pydantic that it's okay to have extra variables in the .env file
    # that are not defined as fields in this class (like POSTGRES_USER).
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding='utf-8',
        extra='ignore'  # <-- This is the key change! It tells Pydantic to ignore extra fields.
    )

    # --- API Keys ---
    GOOGLE_API_KEY: str
    GROQ_API_KEY: str

    # --- RAG/LLM Settings ---
    CHUNK_SIZE: int = 1000
    CHUNK_OVERLAP: int = 200
    LLM_MODEL_NAME: str = "llama3-8b-8192"
    EMBEDDING_MODEL_NAME: str = "models/embedding-001"
    OLLAMA_BASE_URL: str = "http://localhost:11434"

    # --- Database Settings ---
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_PORT: int = 5432
    DATABASE_URL: Optional[str] = None

    @validator("DATABASE_URL", pre=True, always=True) # Use always=True for Pydantic v2
    def assemble_db_connection(cls, v: Optional[str], values: dict) -> str:
        if isinstance(v, str):
            return v
        return (
            f"postgresql://{values.get('POSTGRES_USER')}:{values.get('POSTGRES_PASSWORD')}"
            f"@{values.get('POSTGRES_SERVER')}:{values.get('POSTGRES_PORT')}/{values.get('POSTGRES_DB')}"
        )


    # --- MinIO/S3 Settings ---
    MINIO_SERVER_URL: str
    MINIO_ACCESS_KEY: str # Corresponds to MINIO_ROOT_USER
    MINIO_SECRET_KEY: str # Corresponds to MINIO_ROOT_PASSWORD
    MINIO_BUCKET_NAME: str = "documents"

    # --- JWT/Authentication Settings ---
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24

    # --- Vector Store Path ---
    CHROMA_PATH: str = "/app/chroma_data"
    
    # --- Celery ---
    CELERY_BROKER_URL: str


# Create the single settings instance to be used throughout the app
settings: Settings = Settings()