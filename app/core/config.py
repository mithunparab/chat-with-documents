from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    GOOGLE_API_KEY: str
    GROQ_API_KEY: str

    CHROMA_PATH: str = "chroma"
    DATA_PATH: str = "data/books"
    
    CHUNK_SIZE: int = 800
    CHUNK_OVERLAP: int = 100
    
    LLM_MODEL_NAME: str = "llama3-8b-8192"
    EMBEDDING_MODEL_NAME: str = "models/embedding-001"
    
    INTERNAL_API_URL: str = "http://chat-app:8000"

    class Config:
        env_file = ".env"
        env_file_encoding = 'utf-8'

settings = Settings()