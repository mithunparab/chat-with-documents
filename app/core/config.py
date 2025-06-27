from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    """
    Application configuration settings loaded from environment variables.

    Attributes:
        GOOGLE_API_KEY (str): Google API key.
        GROQ_API_KEY (str): Groq API key.
        CHUNK_SIZE (int): Size of text chunks for RAG.
        CHUNK_OVERLAP (int): Overlap size between chunks.
        LLM_MODEL_NAME (str): Name of the LLM model.
        EMBEDDING_MODEL_NAME (str): Name of the embedding model.
        DATABASE_URL (str): Database connection URL.
        MINIO_SERVER_URL (str): MinIO/S3 server URL.
        MINIO_ACCESS_KEY (str): MinIO/S3 access key.
        MINIO_SECRET_KEY (str): MinIO/S3 secret key.
        MINIO_BUCKET_NAME (str): MinIO/S3 bucket name.
        JWT_SECRET_KEY (str): JWT secret key.
        JWT_ALGORITHM (str): JWT algorithm.
        ACCESS_TOKEN_EXPIRE_MINUTES (int): JWT access token expiry in minutes.
        CHROMA_PATH (str): Path for ChromaDB data.
    """
    GOOGLE_API_KEY: str
    GROQ_API_KEY: str
    CHUNK_SIZE: int = 1000
    CHUNK_OVERLAP: int = 200
    LLM_MODEL_NAME: str = "llama3-8b-8192"
    EMBEDDING_MODEL_NAME: str = "models/embedding-001"
    DATABASE_URL: str
    MINIO_SERVER_URL: str
    MINIO_ACCESS_KEY: str
    MINIO_SECRET_KEY: str
    MINIO_BUCKET_NAME: str = "documents"
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24
    CHROMA_PATH: str = "/app/chroma_data"

    class Config:
        env_file = ".env"
        env_file_encoding = 'utf-8'

# TODO: Add validation for required fields and custom environment variable parsing if needed.
settings: Settings = Settings()