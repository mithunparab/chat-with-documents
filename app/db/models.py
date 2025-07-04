import uuid
from sqlalchemy import Column, String, ForeignKey, DateTime, Text, Enum as SAEnum
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import enum

from .database import Base

class User(Base):
    """
    Represents a user in the system.

    Attributes:
        id (UUID): Primary key, unique user identifier.
        username (str): Unique username for the user.
        hashed_password (str): Hashed password for authentication.
        projects (List[Project]): List of projects owned by the user.
    """
    __tablename__ = "users"
    id: uuid.UUID = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username: str = Column(String, unique=True, index=True, nullable=False)
    hashed_password: str = Column(String, nullable=False)
    projects = relationship("Project", back_populates="owner", cascade="all, delete-orphan")

class Project(Base):
    """
    Represents a project owned by a user.

    Attributes:
        id (UUID): Primary key, unique project identifier.
        name (str): Name of the project.
        owner_id (UUID): Foreign key to the user who owns the project.
        owner (User): The user who owns the project.
        documents (List[Document]): Documents associated with the project.
        chat_sessions (List[ChatSession]): Chat sessions related to the project.
    """
    __tablename__ = "projects"
    id: uuid.UUID = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: str = Column(String, index=True, nullable=False)
    llm_provider: str = Column(String, nullable=False, default="groq") 
    llm_model_name: str = Column(String, nullable=True) 
    owner_id: uuid.UUID = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    owner = relationship("User", back_populates="projects")
    documents = relationship("Document", back_populates="project", cascade="all, delete-orphan")
    chat_sessions = relationship("ChatSession", back_populates="project", cascade="all, delete-orphan")

class DocumentStatus(enum.Enum):
    """
    Enum for document processing status.
    """
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

class Document(Base):
    """
    Represents a document uploaded to a project.

    Attributes:
        id (UUID): Primary key, unique document identifier.
        file_name (str): Name of the file.
        file_type (str): Type of the file (e.g., 'pdf').
        storage_key (str): Unique storage key for the file.
        status (DocumentStatus): Processing status of the document.
        project_id (UUID): Foreign key to the associated project.
        project (Project): The project this document belongs to.
        created_at (datetime): Timestamp when the document was created.
    """
    __tablename__ = "documents"
    id: uuid.UUID = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    file_name: str = Column(String, nullable=False)
    file_type: str = Column(String, nullable=False)
    storage_key: str = Column(String, unique=True, nullable=False) # e.g., user_id/project_id/file_uuid.pdf
    status: DocumentStatus = Column(SAEnum(DocumentStatus), default=DocumentStatus.PENDING, nullable=False)
    project_id: uuid.UUID = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False)
    project = relationship("Project", back_populates="documents")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class ChatSession(Base):
    """
    Represents a chat session within a project.

    Attributes:
        id (UUID): Primary key, unique chat session identifier.
        title (str): Title of the chat session.
        project_id (UUID): Foreign key to the associated project.
        project (Project): The project this chat session belongs to.
        messages (List[ChatMessage]): Messages in the chat session.
        created_at (datetime): Timestamp when the chat session was created.
    """
    __tablename__ = "chat_sessions"
    id: uuid.UUID = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title: str = Column(String, nullable=False, default="New Chat")
    project_id: uuid.UUID = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False)
    project = relationship("Project", back_populates="chat_sessions")
    messages = relationship("ChatMessage", back_populates="session", cascade="all, delete-orphan")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class ChatMessage(Base):
    """
    Represents a message in a chat session.

    Attributes:
        id (UUID): Primary key, unique message identifier.
        session_id (UUID): Foreign key to the associated chat session.
        session (ChatSession): The chat session this message belongs to.
        role (str): Role of the sender ('user' or 'assistant').
        content (str): Content of the message.
        sources (str): JSON string of source chunks (optional).
        created_at (datetime): Timestamp when the message was created.
    """
    __tablename__ = "chat_messages"
    id: uuid.UUID = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id: uuid.UUID = Column(UUID(as_uuid=True), ForeignKey("chat_sessions.id"), nullable=False)
    session = relationship("ChatSession", back_populates="messages")
    role: str = Column(String, nullable=False)  # 'user' or 'assistant'
    content: str = Column(Text, nullable=False)
    sources: str = Column(Text, nullable=True) # JSON string of source chunks
    created_at = Column(DateTime(timezone=True), server_default=func.now())

# TODO:
# - Add validation for file_type and role fields.
# - Implement indexing for frequently queried fields if needed.
# - Consider adding updated_at timestamps for tracking modifications.
# - Add __repr__ methods for better debugging.
# - Add constraints or triggers for data integrity if required.