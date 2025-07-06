import uuid
from sqlalchemy.orm import Session
from . import models, schemas
from app.auth.jwt import get_password_hash
from typing import Dict, Any

def get_user(db: Session, user_id: uuid.UUID) -> models.User | None:
    """Retrieve a user by their UUID."""
    return db.query(models.User).filter(models.User.id == user_id).first()

def get_user_by_username(db: Session, username: str) -> models.User | None:
    """Retrieve a user by their username."""
    return db.query(models.User).filter(models.User.username == username).first()

def get_user_by_email(db: Session, email: str) -> models.User | None:
    """Retrieve a user by their email address."""
    return db.query(models.User).filter(models.User.email == email).first()

def get_or_create_oauth_user(db: Session, user_info: Dict[str, Any]) -> models.User:
    """
    Find an existing user by email or create a new one for an OAuth login.
    If a user with the email exists but is from a different provider,
    it can be linked (this simple implementation just returns the user).
    """
    email = user_info.get("email")
    if not email:
        raise ValueError("Email not found in user info from OAuth provider.")

    # Find user by email, as it's the unique identifier for a person
    db_user = get_user_by_email(db, email=email)
    
    if db_user:
        # User exists. Update provider info if they are logging in with a new method.
        if not db_user.provider or db_user.provider == 'local':
            db_user.provider = user_info.get("provider")
            db_user.social_id = user_info.get("sub") # 'sub' is the standard OIDC claim for user ID
            db.commit()
            db.refresh(db_user)
        return db_user

    # User does not exist, create a new one.
    # Handle potential username collision if derived from email.
    username = user_info.get("name", email.split('@')[0]).replace(" ", "")
    original_username = username
    counter = 1
    while get_user_by_username(db, username):
        username = f"{original_username}{counter}"
        counter += 1
    
    new_user = models.User(
        email=email,
        username=username,
        provider=user_info.get("provider"),
        social_id=user_info.get("sub"),
        hashed_password=None # No password for OAuth users
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

def create_user(db: Session, user: schemas.UserCreate) -> models.User:
    """
    Create a new user with hashed password (for local auth).
    """
    hashed_password = get_password_hash(user.password)
    db_user = models.User(
        username=user.username,
        email=user.username, # Assume username is email for local auth consistency
        hashed_password=hashed_password,
        provider="local"
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

# NEW FUNCTION
def create_oauth_user(db: Session, email: str, full_name: str, provider: str) -> models.User:
    """
    Create a new user from OAuth provider data.
    """
    db_user = models.User(
        username=email, # Use email as the unique username
        email=email,
        full_name=full_name,
        provider=provider,
        hashed_password=None # No password for OAuth users
    )
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
    This will cascade and delete all related projects, documents, etc.
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