from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # API Keys
    GOOGLE_API_KEY: str
    GROQ_API_KEY: str
    
    # RAG Settings
    CHUNK_SIZE: int = 1000
    CHUNK_OVERLAP: int = 200
    LLM_MODEL_NAME: str = "llama3-8b-8192"
    EMBEDDING_MODEL_NAME: str = "models/embedding-001"
    
    # Database
    DATABASE_URL: str
    
    # Object Storage (MinIO/S3)
    MINIO_SERVER_URL: str
    MINIO_ACCESS_KEY: str
    MINIO_SECRET_KEY: str
    MINIO_BUCKET_NAME: str = "documents"

    # Authentication
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 # 1 day

    # ChromaDB
    CHROMA_PATH: str = "/app/chroma_data"

    class Config:
        env_file = ".env"
        env_file_encoding = 'utf-8'

settings = Settings()