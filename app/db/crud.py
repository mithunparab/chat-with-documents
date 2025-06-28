import uuid
from sqlalchemy.orm import Session
from . import models, schemas
from app.auth.jwt import get_password_hash

def get_user(db: Session, user_id: uuid.UUID) -> models.User | None:
    """
    Retrieve a user by their UUID.
    Args:
        db (Session): SQLAlchemy session.
        user_id (uuid.UUID): User's UUID.
    Returns:
        User instance or None if not found.
    """
    return db.query(models.User).filter(models.User.id == user_id).first()

def get_user_by_username(db: Session, username: str) -> models.User | None:
    """
    Retrieve a user by their username.
    Args:
        db (Session): SQLAlchemy session.
        username (str): Username.
    Returns:
        User instance or None if not found.
    """
    return db.query(models.User).filter(models.User.username == username).first()

def create_user(db: Session, user: schemas.UserCreate) -> models.User:
    """
    Create a new user with hashed password.
    Args:
        db (Session): SQLAlchemy session.
        user (UserCreate): User creation schema.
    Returns:
        Created User instance.
    """
    hashed_password = get_password_hash(user.password)
    db_user = models.User(username=user.username, hashed_password=hashed_password)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def get_project(db: Session, project_id: uuid.UUID, user_id: uuid.UUID) -> models.Project | None:
    """
    Retrieve a project by its UUID and owner.
    Args:
        db (Session): SQLAlchemy session.
        project_id (uuid.UUID): Project UUID.
        user_id (uuid.UUID): Owner's UUID.
    Returns:
        Project instance or None if not found.
    """
    return db.query(models.Project).filter(
        models.Project.id == project_id,
        models.Project.owner_id == user_id
    ).first()

def get_projects_for_user(db: Session, user_id: uuid.UUID) -> list[models.Project]:
    """
    Retrieve all projects for a given user.
    Args:
        db (Session): SQLAlchemy session.
        user_id (uuid.UUID): User's UUID.
    Returns:
        List of Project instances.
    """
    return db.query(models.Project).filter(models.Project.owner_id == user_id).all()

def create_project(db: Session, project: schemas.ProjectCreate, user_id: uuid.UUID) -> models.Project:
    """
    Create a new project for a user.
    Args:
        db (Session): SQLAlchemy session.
        project (ProjectCreate): Project creation schema.
        user_id (uuid.UUID): Owner's UUID.
    Returns:
        Created Project instance.
    """
    db_project = models.Project(**project.dict(), owner_id=user_id)
    db.add(db_project)
    db.commit()
    db.refresh(db_project)
    return db_project

def create_document(db: Session, doc: schemas.DocumentCreate) -> models.Document:
    """
    Create a new document.
    Args:
        db (Session): SQLAlchemy session.
        doc (DocumentCreate): Document creation schema.
    Returns:
        Created Document instance.
    """
    db_doc = models.Document(**doc.dict())
    db.add(db_doc)
    db.commit()
    db.refresh(db_doc)
    return db_doc

def get_documents_for_project(db: Session, project_id: uuid.UUID) -> list[models.Document]:
    """
    Retrieve all documents for a given project.
    Args:
        db (Session): SQLAlchemy session.
        project_id (uuid.UUID): Project UUID.
    Returns:
        List of Document instances.
    """
    return db.query(models.Document).filter(models.Document.project_id == project_id).all()

def update_document_status(db: Session, document_id: uuid.UUID, status: models.DocumentStatus) -> models.Document | None:
    """
    Update the status of a document.
    Args:
        db (Session): SQLAlchemy session.
        document_id (uuid.UUID): Document UUID.
        status (DocumentStatus): New status.
    Returns:
        Updated Document instance or None if not found.
    """
    db_doc = db.query(models.Document).filter(models.Document.id == document_id).first()
    if db_doc:
        db_doc.status = status
        db.commit()
        db.refresh(db_doc)
    return db_doc

def create_chat_session(db: Session, project_id: uuid.UUID, first_message: str) -> models.ChatSession:
    """
    Create a new chat session for a project.
    Args:
        db (Session): SQLAlchemy session.
        project_id (uuid.UUID): Project UUID.
        first_message (str): First message content.
    Returns:
        Created ChatSession instance.
    """
    title = f"Chat about: {first_message[:30]}..."
    db_session = models.ChatSession(project_id=project_id, title=title)
    db.add(db_session)
    db.commit()
    db.refresh(db_session)
    return db_session

def get_chat_sessions_for_project(db: Session, project_id: uuid.UUID) -> list[models.ChatSession]:
    """
    Retrieve all chat sessions for a project, ordered by creation date descending.
    Args:
        db (Session): SQLAlchemy session.
        project_id (uuid.UUID): Project UUID.
    Returns:
        List of ChatSession instances.
    """
    return db.query(models.ChatSession).filter(
        models.ChatSession.project_id == project_id
    ).order_by(models.ChatSession.created_at.desc()).all()

def get_chat_session(db: Session, session_id: uuid.UUID, project_id: uuid.UUID) -> models.ChatSession | None:
    """
    Retrieve a chat session by its UUID and project.
    Args:
        db (Session): SQLAlchemy session.
        session_id (uuid.UUID): ChatSession UUID.
        project_id (uuid.UUID): Project UUID.
    Returns:
        ChatSession instance or None if not found.
    """
    return db.query(models.ChatSession).filter(
        models.ChatSession.id == session_id,
        models.ChatSession.project_id == project_id
    ).first()

def add_chat_message(db: Session, session_id: uuid.UUID, message: schemas.ChatMessageCreate) -> models.ChatMessage:
    """
    Add a new message to a chat session.
    Args:
        db (Session): SQLAlchemy session.
        session_id (uuid.UUID): ChatSession UUID.
        message (ChatMessageCreate): Message creation schema.
    Returns:
        Created ChatMessage instance.
    """
    db_message = models.ChatMessage(session_id=session_id, **message.dict())
    db.add(db_message)
    db.commit()
    db.refresh(db_message)
    return db_message

def delete_document(db: Session, document_id: uuid.UUID) -> models.Document | None:
    """
    Delete a document by its UUID.
    Args:
        db (Session): SQLAlchemy session.
        document_id (uuid.UUID): Document UUID.
    Returns:
        Deleted Document instance or None if not found.
    """
    db_doc = db.query(models.Document).filter(models.Document.id == document_id).first()
    if db_doc:
        db.delete(db_doc)
        db.commit()
    return db_doc

def delete_chat_session(db: Session, session_id: uuid.UUID) -> models.ChatSession | None:
    """
    Delete a chat session by its UUID.
    Args:
        db (Session): SQLAlchemy session.
        session_id (uuid.UUID): ChatSession UUID.
    Returns:
        Deleted ChatSession instance or None if not found.
    """
    db_session = db.query(models.ChatSession).filter(models.ChatSession.id == session_id).first()
    if db_session:
        db.delete(db_session)
        db.commit()
    return db_session

def delete_user(db: Session, user_id: uuid.UUID) -> models.User | None:
    """
    Delete a user by their UUID.
    Args:
        db (Session): SQLAlchemy session.
        user_id (uuid.UUID): User's UUID.
    Returns:
        Deleted User instance or None if not found.
    """
    db_user = db.query(models.User).filter(models.User.id == user_id).first()
    if db_user:
        db.delete(db_user)
        db.commit()
    return db_user

# TODO: Add error handling and logging for CRUD operations.