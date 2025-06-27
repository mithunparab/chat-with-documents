import uuid
from pydantic import BaseModel, Field
from datetime import datetime
from typing import List, Optional

from .models import DocumentStatus

# --- Base Models ---
class UserBase(BaseModel):
    """
    Base model for a user.
    """
    username: str

class ProjectBase(BaseModel):
    """
    Base model for a project.
    """
    name: str = Field(..., min_length=1, max_length=100)

class DocumentBase(BaseModel):
    """
    Base model for a document.
    """
    file_name: str
    file_type: str

# --- Creation Models (for POST/PUT requests) ---
class UserCreate(UserBase):
    """
    Model for creating a user.
    """
    password: str

class ProjectCreate(ProjectBase):
    """
    Model for creating a project.
    """
    pass

class DocumentCreate(DocumentBase):
    """
    Model for creating a document.
    """
    storage_key: str
    project_id: uuid.UUID
    status: DocumentStatus = DocumentStatus.PENDING

class ChatMessageCreate(BaseModel):
    """
    Model for creating a chat message.
    """
    role: str
    content: str
    sources: Optional[str] = None

# --- Read Models (for GET responses) ---
class User(UserBase):
    """
    Model representing a user (read model).
    """
    id: uuid.UUID

    class Config:
        from_attributes = True

class Document(DocumentBase):
    """
    Model representing a document (read model).
    """
    id: uuid.UUID
    status: DocumentStatus
    created_at: datetime

    class Config:
        from_attributes = True

class Project(ProjectBase):
    """
    Model representing a project (read model).
    """
    id: uuid.UUID
    owner_id: uuid.UUID
    documents: List[Document] = []

    class Config:
        from_attributes = True

class ChatMessage(BaseModel):
    """
    Model representing a chat message (read model).
    """
    id: uuid.UUID
    role: str
    content: str
    sources: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

class ChatSession(BaseModel):
    """
    Model representing a chat session.
    """
    id: uuid.UUID
    title: str
    project_id: uuid.UUID
    created_at: datetime
    messages: List[ChatMessage] = []

    class Config:
        from_attributes = True