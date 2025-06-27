import uuid
import json
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any

from app.db import crud, models, schemas
from app.db.database import get_db
from app.core.dependencies import get_current_user
from app.services.rag_service import RAGService

router = APIRouter()

class ChatRequest(BaseModel):
    query: str
    chat_id: Optional[uuid.UUID] = None

class ChatResponse(BaseModel):
    answer: str
    sources: List[Dict[str, Any]]
    chat_id: uuid.UUID

@router.post("/{project_id}", response_model=ChatResponse)
def handle_chat_query(
    project_id: uuid.UUID,
    request: ChatRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    project = crud.get_project(db, project_id=project_id, user_id=current_user.id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found or access denied")

    # Instantiate RAG service for the specific user and project
    rag_service = RAGService(user=current_user, project=project)
    
    answer, sources = rag_service.query(request.query)

    # Persist conversation
    chat_id = request.chat_id
    if not chat_id:
        chat_session = crud.create_chat_session(db, project_id=project_id, first_message=request.query)
        chat_id = chat_session.id
    
    # Add user message
    crud.add_chat_message(db, chat_id, schemas.ChatMessageCreate(role="user", content=request.query))
    # Add assistant message
    crud.add_chat_message(db, chat_id, schemas.ChatMessageCreate(
        role="assistant", 
        content=answer, 
        sources=json.dumps(sources)
    ))
    
    return ChatResponse(answer=answer, sources=sources, chat_id=chat_id)

@router.get("/sessions/{project_id}", response_model=List[schemas.ChatSession])
def get_chat_sessions(
    project_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
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
):
    session = crud.get_chat_session(db, session_id=session_id, project_id=project_id)
    if not session or session.project.owner_id != current_user.id:
         raise HTTPException(status_code=404, detail="Chat session not found")
    return session