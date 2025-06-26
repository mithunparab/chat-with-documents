from fastapi import APIRouter, BackgroundTasks, HTTPException, Depends
from services.rag_service import get_rag_service, RAGService

router = APIRouter()

@router.post("/process", status_code=202)
async def process_documents_endpoint(
    background_tasks: BackgroundTasks,
    rag_service: RAGService = Depends(get_rag_service) 
):
    """
    Triggers the background processing of documents in the data/books directory.
    """
    try:
        background_tasks.add_task(rag_service.process_documents)
        return {"message": "Document processing started in the background."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))