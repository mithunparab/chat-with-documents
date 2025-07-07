import tempfile
import json
import hashlib
import redis
from typing import List, Tuple, Dict, Any, Optional
import httpx
import chromadb
from langchain_community.document_loaders import (
    PyPDFLoader, UnstructuredURLLoader, UnstructuredWordDocumentLoader,
    UnstructuredMarkdownLoader, TextLoader
)
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain.schema import Document
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_community.chat_models import ChatOllama
from langchain_chroma import Chroma
from langchain_groq import ChatGroq
from langchain.prompts import ChatPromptTemplate
from langchain.retrievers import EnsembleRetriever
from langchain_community.retrievers import BM25Retriever
from chromadb.config import Settings as ChromaSettings

from app.core.config import settings
from app.services import storage_service
from app.db.models import Project, User
import logging

logger = logging.getLogger(__name__)

def _ensure_ollama_model_is_available(model_name: str) -> None:
    if not settings.OLLAMA_HOST:
        return
    try:
        client = httpx.Client(base_url=settings.OLLAMA_HOST, timeout=60.0)
        response = client.get("/api/tags")
        response.raise_for_status()
        models = response.json().get("models", [])
        model_base_name = model_name.split(':')[0]
        model_exists = any(m['name'].split(':')[0] == model_base_name for m in models)
        if model_exists:
            return
        logger.info(f"Ollama model '{model_name}' not found. Pulling it now in the background...")
        pull_response = client.post("/api/pull", json={"name": model_name, "stream": False}, timeout=None)
        pull_response.raise_for_status()
        logger.info(f"Successfully pulled Ollama model '{model_name}'.")
    except Exception as e:
        logger.error(f"Failed to ensure Ollama model '{model_name}' is available: {e}", exc_info=True)
        raise

class RAGService:
    def __init__(self, user: User, project: Project) -> None:
        self.user: User = user
        self.project: Project = project
        self.collection_name: str = f"proj_{str(project.id).replace('-', '')}"
        
        self.embedding_function = GoogleGenerativeAIEmbeddings(model=settings.EMBEDDING_MODEL_NAME)

        if self.project.llm_provider == "ollama" and settings.OLLAMA_HOST:
            model_name = self.project.llm_model_name or settings.OLLAMA_MODEL
            self.llm = ChatOllama(base_url=settings.OLLAMA_HOST, model=model_name)
        else:
            model_name = self.project.llm_model_name or settings.LLM_MODEL_NAME
            self.llm = ChatGroq(groq_api_key=settings.GROQ_API_KEY, model_name=model_name)
            
        try:
            self.redis_client: Optional[redis.Redis] = redis.from_url(settings.CELERY_BROKER_URL)
            self.redis_client.ping()
        except Exception as e:
            logger.error(f"Could not connect to Redis: {e}. Caching is disabled.", exc_info=True)
            self.redis_client = None

        chroma_client = chromadb.PersistentClient(path=settings.CHROMA_PATH, settings=ChromaSettings(anonymized_telemetry=False))
        self.vectorstore: Chroma = Chroma(
            client=chroma_client, 
            collection_name=self.collection_name,
            embedding_function=self.embedding_function,
        )

    def _get_loader(self, file_path: Optional[str], file_type: str, url: Optional[str] = None) -> Any:
        # Reverting to your original, more robust loader logic
        if url:
            headers = {"User-Agent": "Mozilla/5.0"}
            return UnstructuredURLLoader(urls=[url], headers=headers)
        if file_type == "application/pdf":
            return PyPDFLoader(file_path)
        elif file_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
            return UnstructuredWordDocumentLoader(file_path)
        elif file_type == "text/markdown":
            return UnstructuredMarkdownLoader(file_path)
        elif file_type.startswith("text/"):
            return TextLoader(file_path)
        else:
            logger.warning(f"Defaulting to UnstructuredWordDocumentLoader for unknown type: {file_type}")
            return UnstructuredWordDocumentLoader(file_path)

    def process_document(
        self, storage_key: str, file_type: str, file_name: str, document_id: str, url: Optional[str] = None
    ) -> None:
        if self.project.llm_provider == "ollama":
            _ensure_ollama_model_is_available(self.project.llm_model_name or settings.OLLAMA_MODEL)
            
        logger.info(f"Processing document_id: {document_id} for project {self.project.name}")

        # Reverting to your original temp file logic which correctly preserves filenames
        docs: List[Document]
        if url:
            loader = self._get_loader(None, file_type, url=url)
            docs = loader.load()
        else:
            with tempfile.NamedTemporaryFile(delete=True, suffix=f"_{file_name}") as tmp_file:
                storage_service.download_file(storage_key, tmp_file.name)
                loader = self._get_loader(tmp_file.name, file_type)
                docs = loader.load()
        
        if not docs:
            logger.warning(f"No documents could be loaded from {file_name}. Skipping.")
            return

        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=settings.CHUNK_SIZE, chunk_overlap=settings.CHUNK_OVERLAP
        )
        chunks: List[Document] = text_splitter.split_documents(docs)
        if not chunks:
            logger.warning(f"No text could be extracted from {file_name}. Skipping.")
            return

        for chunk in chunks:
            chunk.metadata['document_id'] = document_id
            # This correctly sets the source to the original filename or URL
            chunk.metadata.setdefault('source', url or file_name)

        self.vectorstore.add_documents(documents=chunks)
        logger.info(f"Added {len(chunks)} chunks for document {document_id} to '{self.collection_name}'.")
        self.clear_cache_for_project()

    def delete_document_chunks(self, document_id: str) -> None:
        logger.info(f"Deleting chunks for document_id: {document_id} from '{self.collection_name}'")
        try:
            self.vectorstore.delete(ids=None, where={"document_id": document_id})
            logger.info(f"Successfully submitted deletion for chunks of document_id: {document_id}.")
            self.clear_cache_for_project()
        except Exception as e:
            logger.error(f"Error deleting chunks for document {document_id}: {e}", exc_info=True)

    def clear_cache_for_project(self) -> None:
        if not self.redis_client: return
        try:
            keys_to_delete: List[str] = [k.decode('utf-8') for k in self.redis_client.scan_iter(f"rag_cache:{self.project.id}:*")]
            if keys_to_delete:
                self.redis_client.delete(*keys_to_delete)
                logger.info(f"Invalidated {len(keys_to_delete)} cache entries for project {self.project.id}.")
        except Exception as e:
            logger.error(f"Failed to clear Redis cache for project {self.project.id}: {e}", exc_info=True)
    
    def _load_all_project_docs(self) -> List[Document]:
        # Your original method to load all docs for BM25
        try:
            results = self.vectorstore.get(include=["metadatas", "documents"])
            all_docs: List[Document] = []
            for i, text in enumerate(results['documents'] or []):
                doc = Document(page_content=text, metadata=results['metadatas'][i] or {})
                all_docs.append(doc)
            logger.info(f"Loaded {len(all_docs)} total document chunks for project {self.project.id}.")
            return all_docs
        except Exception as e:
            logger.error(f"Failed to load all project documents from Chroma: {e}", exc_info=True)
            return []

    def _get_ensemble_retriever(self, all_project_docs: List[Document]) -> EnsembleRetriever:
        # Your original ensemble retriever
        bm25_retriever = BM25Retriever.from_documents(all_project_docs, k=5)
        vector_retriever = self.vectorstore.as_retriever(search_kwargs={"k": 5})
        ensemble_retriever = EnsembleRetriever(
            retrievers=[bm25_retriever, vector_retriever], weights=[0.5, 0.5]
        )
        return ensemble_retriever

    def query(self, message: str) -> Tuple[str, List[Dict[str, Any]]]:
        # Your original, advanced query logic with HyDE
        if self.redis_client:
            message_hash: str = hashlib.sha256(message.encode()).hexdigest()
            cache_key: str = f"rag_cache:{self.project.id}:{message_hash}"
            try:
                cached_result = self.redis_client.get(cache_key)
                if cached_result:
                    logger.info(f"Returning cached RAG result for project {self.project.id}")
                    result = json.loads(cached_result)
                    return result['answer'], result['sources']
            except Exception as e:
                logger.warning(f"Redis cache check failed: {e}", exc_info=True)
        
        logger.info(f"Querying project '{self.project.name}' with: '{message}'")

        all_project_docs: List[Document] = self._load_all_project_docs()
        if not all_project_docs:
            return "This project has no documents. Please upload a document to begin.", []

        ensemble_retriever: EnsembleRetriever = self._get_ensemble_retriever(all_project_docs)

        hyde_prompt = ChatPromptTemplate.from_template(
            "Please write a short, hypothetical document that could answer the user's question. "
            "Question: {question}"
        )
        hyde_chain = hyde_prompt | self.llm
        hypothetical_doc: str = hyde_chain.invoke({"question": message}).content
        logger.info("HyDE document generated for query expansion.")

        final_docs: List[Document] = ensemble_retriever.invoke(hypothetical_doc)
        if not final_docs:
            return "I couldn't find relevant information in your documents to answer the query.", []

        context_text: str = "\n\n---\n\n".join([doc.page_content for doc in final_docs])
        
        rag_prompt = ChatPromptTemplate.from_template("""
            You are a helpful and diligent AI assistant. Your task is to answer the user's question based on the provided context.
            (Instructions from your original prompt...)
            Context:
            {context}
            Question:
            {question}
            Answer:
        """)

        rag_chain = rag_prompt | self.llm
        answer: str = rag_chain.invoke({"context": context_text, "question": message}).content
        
        unique_sources: Dict[str, Dict[str, Any]] = {}
        for doc in final_docs:
            source_info: Dict[str, Any] = {"content": doc.page_content, "source": doc.metadata.get("source", "Unknown")}
            unique_sources[doc.page_content] = source_info
        
        sources: List[Dict[str, Any]] = list(unique_sources.values())
        
        if self.redis_client:
            try:
                result_to_cache: Dict[str, Any] = {"answer": answer, "sources": sources}
                self.redis_client.set(cache_key, json.dumps(result_to_cache), ex=3600)
                logger.info(f"Cached RAG result for project {self.project.id}")
            except Exception as e:
                logger.warning(f"Redis cache set failed: {e}", exc_info=True)

        return answer, sources