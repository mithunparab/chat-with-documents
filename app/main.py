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

from api.v1 import documents, chat
from services.rag_service import initialize_rag_service

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Manages application startup and shutdown events.

    Args:
        app (FastAPI): The FastAPI application instance.

    Yields:
        None: Control is yielded back to FastAPI after startup is complete.

    Notable:
        - Initializes the RAG service synchronously. This may block the event loop.
          See TODO for technical debt.
    """
    print("Application startup: Initializing RAG service...")
    initialize_rag_service()  # TODO: Refactor to async if RAG service supports it.
    print("Application startup: RAG service ready.")
    yield
    print("Application shutdown.")

app: FastAPI = FastAPI(
    title="Chat with Documents API",
    lifespan=lifespan,
    description="A headless API for the Retrieval-Augmented Generation (RAG) application."
)

# --- API Router Mounting ---
print("Mounting API endpoints...")
app.include_router(documents.router, prefix="/api/v1/documents", tags=["Documents"])
app.include_router(chat.router, prefix="/api/v1/chat", tags=["Chat"])
print("API endpoints mounted.")

@app.get("/", include_in_schema=False)
def root() -> RedirectResponse:
    """
    Redirects the root path to the API documentation.

    Returns:
        RedirectResponse: Redirects client to the /docs endpoint.
    """
    return RedirectResponse(url="/docs")

@app.get("/health", tags=["Health"])
def health_check() -> dict[str, str]:
    """
    Health check endpoint to verify server status.

    Returns:
        dict[str, str]: A dictionary indicating the server status.
            Example: {"status": "ok"}
    """
    return {"status": "ok"}