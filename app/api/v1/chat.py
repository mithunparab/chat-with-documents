"""
API endpoint for handling chat queries using a Retrieval-Augmented Generation (RAG) service.

This module defines the FastAPI router, request/response models, and the main endpoint for processing
user chat queries, retrieving relevant context, and generating answers.
"""

from fastapi import APIRouter, HTTPException, Body, Depends
from pydantic import BaseModel
from typing import List
from services.rag_service import get_rag_service, RAGService

router: APIRouter = APIRouter()

class ChatRequest(BaseModel):
    """
    Request model for chat queries.

    Attributes:
        query (str): The user's input question or prompt.
    """
    query: str

class ChatResponse(BaseModel):
    """
    Response model for chat answers.

    Attributes:
        answer (str): The generated answer to the user's query.
        sources (List[str]): List of document sources used to generate the answer.
    """
    answer: str
    sources: List[str]

@router.post("/", response_model=ChatResponse)
async def handle_chat_query(
    request: ChatRequest = Body(...),
    rag_service: RAGService = Depends(get_rag_service)
) -> ChatResponse:
    """
    Handles a chat query by retrieving relevant context and generating a response.

    Args:
        request (ChatRequest): The incoming chat request containing the user's query.
        rag_service (RAGService): Dependency-injected RAG service instance.

    Returns:
        ChatResponse: The generated answer and associated sources.

    Raises:
        HTTPException: 
            - 404 if no relevant information is found in the documents.
            - 500 for unexpected internal server errors.

    Notable Behavior:
        - Returns 404 if the answer indicates no relevant information was found.
        - Logs and returns 500 for unexpected exceptions.
    """
    try:
        answer: str
        sources: List[str]
        answer, sources = rag_service.query(request.query)

        if not sources and "couldn't find relevant information" in answer:
            raise HTTPException(
                status_code=404,
                detail="No relevant information found in the documents to answer the query."
            )
        return ChatResponse(answer=answer, sources=sources)

    except HTTPException:
        # Re-raise HTTPExceptions for FastAPI to handle appropriately.
        raise
    except Exception as e:
        print(f"An unexpected and unhandled error occurred in chat endpoint: {e}")
        raise HTTPException(
            status_code=500,
            detail="An internal server error occurred."
        )