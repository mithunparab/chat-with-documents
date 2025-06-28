import uuid
import json
from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any

from app.db import crud, models, schemas
from app.db.database import get_db
from app.core.dependencies import get_current_user
from app.services.rag_service import RAGService
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

class ChatRequest(BaseModel):
    """Request model for chat queries."""
    query: str
    chat_id: Optional[uuid.UUID] = None

class ChatResponse(BaseModel):
    """Response model for chat queries."""
    answer: str
    sources: List[Dict[str, Any]]
    chat_id: uuid.UUID

@router.post("/{project_id}", response_model=ChatResponse)
def handle_chat_query(
    project_id: uuid.UUID,
    request: ChatRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
) -> ChatResponse:
    """
    Handle a chat query for a given project.

    Args:
        project_id (uuid.UUID): The project identifier.
        request (ChatRequest): The chat request payload.
        db (Session): Database session dependency.
        current_user (models.User): Authenticated user dependency.

    Returns:
        ChatResponse: The response containing the answer, sources, and chat session ID.

    Raises:
        HTTPException: If the project is not found or access is denied.
    """
    project = crud.get_project(db, project_id=project_id, user_id=current_user.id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found or access denied")

    rag_service = RAGService(user=current_user, project=project)
    answer, sources = rag_service.query(request.query)

    chat_id: Optional[uuid.UUID] = request.chat_id
    if not chat_id:
        chat_session = crud.create_chat_session(db, project_id=project_id, first_message=request.query)
        chat_id = chat_session.id

    crud.add_chat_message(db, chat_id, schemas.ChatMessageCreate(role="user", content=request.query))
    crud.add_chat_message(db, chat_id, schemas.ChatMessageCreate(
        role="assistant", 
        content=answer, 
        sources=json.dumps(sources)
    ))

    # TODO: Add support for streaming responses and message history context

    return ChatResponse(answer=answer, sources=sources, chat_id=chat_id)

@router.get("/sessions/{project_id}", response_model=List[schemas.ChatSession])
def get_chat_sessions(
    project_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
) -> List[schemas.ChatSession]:
    """
    Retrieve all chat sessions for a given project.

    Args:
        project_id (uuid.UUID): The project identifier.
        db (Session): Database session dependency.
        current_user (models.User): Authenticated user dependency.

    Returns:
        List[schemas.ChatSession]: List of chat sessions for the project.

    Raises:
        HTTPException: If the project is not found.
    """
    project = crud.get_project(db, project_id=project_id, user_id=current_user.id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return crud.get_chat_sessions_for_project(db, project_id=project_id)

@router.get("/sessions/{project_id}/{session_id}", response_model=schemas.ChatSession)
def get_chat_session_messages(
    project_id: uuid.UUID,
    session_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
) -> schemas.ChatSession:
    """
    Retrieve messages for a specific chat session.

    Args:
        project_id (uuid.UUID): The project identifier.
        session_id (uuid.UUID): The chat session identifier.
        db (Session): Database session dependency.
        current_user (models.User): Authenticated user dependency.

    Returns:
        schemas.ChatSession: The chat session with its messages.

    Raises:
        HTTPException: If the chat session is not found or access is denied.
    """
    session = crud.get_chat_session(db, session_id=session_id, project_id=project_id)
    if not session or session.project.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Chat session not found")
    return session

@router.delete(
    "/sessions/{project_id}/{session_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a chat session"
)
def delete_chat_session_endpoint(
    project_id: uuid.UUID,
    session_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
) -> Response:
    """
    Delete a specific chat session and all its associated messages for a given project.

    Args:
        project_id (uuid.UUID): The project identifier.
        session_id (uuid.UUID): The chat session identifier.
        db (Session): Database session dependency.
        current_user (models.User): Authenticated user dependency.

    Returns:
        Response: HTTP 204 No Content on successful deletion.

    Raises:
        HTTPException: If the chat session is not found or access is denied.
    """
    logger.info(f"User '{current_user.username}' attempting to delete chat session '{session_id}' from project '{project_id}'")

    session_to_delete = crud.get_chat_session(db, session_id=session_id, project_id=project_id)

    if not session_to_delete:
        logger.warning(f"Chat session '{session_id}' not found for project '{project_id}'.")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat session not found.")

    if session_to_delete.project.owner_id != current_user.id:
        logger.warning(f"Access denied: User '{current_user.username}' does not own project for chat session '{session_id}'.")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not have permission to delete this chat session.")

    try:
        crud.delete_chat_session(db, session_id=session_id)
        logger.info(f"Successfully deleted chat session '{session_id}'.")
    except Exception as e:
        logger.error(f"Database error while deleting chat session '{session_id}': {e}", exc_info=True)
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Could not delete chat session.")

    return Response(status_code=status.HTTP_204_NO_CONTENT)