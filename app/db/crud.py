import uuid
from sqlalchemy.orm import Session
from . import models, schemas
from app.auth.jwt import get_password_hash

# --- User CRUD ---
def get_user(db: Session, user_id: uuid.UUID):
    return db.query(models.User).filter(models.User.id == user_id).first()

def get_user_by_username(db: Session, username: str):
    return db.query(models.User).filter(models.User.username == username).first()

def create_user(db: Session, user: schemas.UserCreate):
    hashed_password = get_password_hash(user.password)
    db_user = models.User(username=user.username, hashed_password=hashed_password)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

# --- Project CRUD ---
def get_project(db: Session, project_id: uuid.UUID, user_id: uuid.UUID):
    return db.query(models.Project).filter(models.Project.id == project_id, models.Project.owner_id == user_id).first()

def get_projects_for_user(db: Session, user_id: uuid.UUID):
    return db.query(models.Project).filter(models.Project.owner_id == user_id).all()

def create_project(db: Session, project: schemas.ProjectCreate, user_id: uuid.UUID):
    db_project = models.Project(**project.dict(), owner_id=user_id)
    db.add(db_project)
    db.commit()
    db.refresh(db_project)
    return db_project

# --- Document CRUD ---
def create_document(db: Session, doc: schemas.DocumentCreate):
    db_doc = models.Document(**doc.dict())
    db.add(db_doc)
    db.commit()
    db.refresh(db_doc)
    return db_doc

def get_documents_for_project(db: Session, project_id: uuid.UUID):
    return db.query(models.Document).filter(models.Document.project_id == project_id).all()

def update_document_status(db: Session, document_id: uuid.UUID, status: models.DocumentStatus): 
    db_doc = db.query(models.Document).filter(models.Document.id == document_id).first()
    if db_doc:
        db_doc.status = status
        db.commit()
        db.refresh(db_doc)
    return db_doc

# --- Chat CRUD ---
def create_chat_session(db: Session, project_id: uuid.UUID, first_message: str):
    title = f"Chat about: {first_message[:30]}..."
    db_session = models.ChatSession(project_id=project_id, title=title)
    db.add(db_session)
    db.commit()
    db.refresh(db_session)
    return db_session

def get_chat_sessions_for_project(db: Session, project_id: uuid.UUID):
    return db.query(models.ChatSession).filter(models.ChatSession.project_id == project_id).order_by(models.ChatSession.created_at.desc()).all()

def get_chat_session(db: Session, session_id: uuid.UUID, project_id: uuid.UUID):
    return db.query(models.ChatSession).filter(models.ChatSession.id == session_id, models.ChatSession.project_id == project_id).first()

def add_chat_message(db: Session, session_id: uuid.UUID, message: schemas.ChatMessageCreate):
    db_message = models.ChatMessage(session_id=session_id, **message.dict())
    db.add(db_message)
    db.commit()
    db.refresh(db_message)
    return db_message