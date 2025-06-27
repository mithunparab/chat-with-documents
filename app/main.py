"""
Entry point for the Chat with Documents API application.

This module initializes the FastAPI app, sets up API routers, and defines
root and health check endpoints. It also manages application startup and
shutdown events, including initialization of the RAG service.
"""
from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from app.api.v1 import auth, projects, documents, chat
from app.db.database import init_db
from app.services.storage_service import create_minio_bucket_if_not_exists

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Context manager for FastAPI application lifespan events.

    Handles application startup and shutdown logic, such as initializing
    the database and ensuring the MinIO bucket exists.

    Args:
        app (FastAPI): The FastAPI application instance.

    Yields:
        None: Control is yielded back to FastAPI after startup logic.
    """
    print("Application startup: Initializing...")
    # For development, create DB tables on startup. For production, use Alembic migrations.
    init_db()
    create_minio_bucket_if_not_exists()
    print("Application startup complete.")
    yield
    print("Application shutdown.")

app: FastAPI = FastAPI(
    title="Chat with Documents API",
    lifespan=lifespan,
    description="A multi-tenant API for Retrieval-Augmented Generation (RAG)."
)

app.include_router(auth.router, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(projects.router, prefix="/api/v1/projects", tags=["Projects"])
app.include_router(documents.router, prefix="/api/v1/documents", tags=["Documents"])
app.include_router(chat.router, prefix="/api/v1/chat", tags=["Chat"])

@app.get("/", include_in_schema=False)
def root() -> RedirectResponse:
    """
    Redirects the root endpoint to the API documentation.

    Returns:
        RedirectResponse: A redirect response to the /docs endpoint.
    """
    return RedirectResponse(url="/docs")

@app.get("/health", tags=["Health"])
def health_check() -> dict[str, str]:
    """
    Health check endpoint.

    Returns:
        dict[str, str]: A dictionary indicating the service status.
    """
    return {"status": "ok"}