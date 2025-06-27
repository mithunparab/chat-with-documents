import uuid
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List

from app.db import crud, models, schemas
from app.db.database import get_db, SessionLocal # <-- FIX: Import SessionLocal
from app.core.dependencies import get_current_user
from app.services import storage_service
from app.services.rag_service import RAGService
from pydantic import BaseModel

router = APIRouter()

def process_document_in_background(user_id: uuid.UUID, project_id: uuid.UUID, document_id: uuid.UUID, storage_key: str, file_type: str, file_name: str, url: str=None):
    """Function to be run in the background for processing a single document."""
    print(f"Background task started for doc {document_id}")
    db = SessionLocal() # Create a new session for this background task
    try:
        crud.update_document_status(db, document_id, schemas.DocumentStatus.PROCESSING)
        
        user = crud.get_user(db, user_id)
        project = crud.get_project(db, project_id, user_id)
        
        rag_service = RAGService(user=user, project=project)
        rag_service.process_document(storage_key, file_type, file_name, url)

        crud.update_document_status(db, document_id, schemas.DocumentStatus.COMPLETED)
        print(f"Background task finished for doc {document_id}")
    except Exception as e:
        print(f"Background task FAILED for doc {document_id}: {e}")
        import traceback
        traceback.print_exc() # Print the full traceback for debugging
        crud.update_document_status(db, document_id, schemas.DocumentStatus.FAILED)
    finally:
        db.close() # Ensure the session is closed

@router.post("/upload/{project_id}", response_model=schemas.Document)
def upload_document(
    project_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    project = crud.get_project(db, project_id=project_id, user_id=current_user.id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    storage_key = f"{current_user.id}/{project_id}/{uuid.uuid4()}_{file.filename}"
    
    if not storage_service.upload_file_obj(file.file, storage_key):
        raise HTTPException(status_code=500, detail="Could not upload file to storage.")

    doc_create = schemas.DocumentCreate(
        file_name=file.filename,
        file_type=file.content_type,
        storage_key=storage_key,
        project_id=project_id
    )
    db_doc = crud.create_document(db, doc_create)

    # FIX: Pass IDs and primitive types to the background task, not the DB session
    background_tasks.add_task(
        process_document_in_background,
        current_user.id,
        project_id,
        db_doc.id,
        storage_key,
        file.content_type,
        file.filename
    )
    
    return db_doc

class URLPayload(BaseModel):
    url: str

@router.post("/upload_url/{project_id}", response_model=schemas.Document)
def upload_url(
    project_id: uuid.UUID,
    payload: URLPayload,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    project = crud.get_project(db, project_id=project_id, user_id=current_user.id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    file_name = payload.url
    storage_key = f"{current_user.id}/{project_id}/{uuid.uuid4()}_url"

    doc_create = schemas.DocumentCreate(
        file_name=file_name,
        file_type="text/html",
        storage_key=storage_key,
        project_id=project_id
    )
    db_doc = crud.create_document(db, doc_create)

    # FIX: Pass IDs and primitive types to the background task
    background_tasks.add_task(
        process_document_in_background,
        current_user.id,
        project_id,
        db_doc.id,
        storage_key,
        "text/html",
        file_name,
        url=payload.url
    )

    return db_doc

@router.get("/{project_id}", response_model=List[schemas.Document])
def get_documents_for_project(
    project_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    project = crud.get_project(db, project_id=project_id, user_id=current_user.id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return crud.get_documents_for_project(db, project_id=project_id)