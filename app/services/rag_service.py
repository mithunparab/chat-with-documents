import tempfile
import json
import hashlib
import redis
from typing import List, Tuple, Dict, Any, Optional
import httpx
import chromadb
import pickle
import io
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

# --- Helper functions for the new architecture ---

def get_bm25_cache_key(project_id: str) -> str:
    """Generates a consistent Redis key for a project's BM25 retriever."""
    return f"bm25_retriever:{project_id}"

def get_docs_cache_key(project_id: str) -> str:
    """Generates a consistent Redis key for a project's document chunks."""
    return f"project_docs:{project_id}"

def _ensure_ollama_model_is_available(model_name: str):
    if not settings.OLLAMA_HOST: return
    try:
        client = httpx.Client(base_url=settings.OLLAMA_HOST, timeout=60.0)
        response = client.get("/api/tags")
        response.raise_for_status()
        models = response.json().get("models", [])
        model_base_name = model_name.split(':')[0]
        model_exists = any(m['name'].split(':')[0] == model_base_name for m in models)
        if model_exists: return
        logger.info(f"Ollama model '{model_name}' not found. Pulling it now...")
        pull_response = client.post("/api/pull", json={"name": model_name, "stream": False}, timeout=None)
        pull_response.raise_for_status()
        logger.info(f"Successfully pulled Ollama model '{model_name}'.")
    except Exception as e:
        logger.error(f"Failed to ensure Ollama model '{model_name}' is available: {e}", exc_info=True)
        raise

class RAGService:
    def __init__(self, user: User, project: Project):
        self.user = user
        self.project = project
        self.collection_name = f"proj_{str(project.id).replace('-', '')}"
        
        self.embedding_function = GoogleGenerativeAIEmbeddings(model=settings.EMBEDDING_MODEL_NAME)

        llm_model_name = self.project.llm_model_name
        if self.project.llm_provider == "ollama" and settings.OLLAMA_HOST:
            self.llm = ChatOllama(base_url=settings.OLLAMA_HOST, model=llm_model_name, temperature=0.2)
        else:
            self.llm = ChatGroq(groq_api_key=settings.GROQ_API_KEY, model_name=llm_model_name, temperature=0.2)
            
        try:
            self.redis_client: redis.Redis = redis.from_url(settings.CELERY_BROKER_URL)
            self.redis_client.ping()
        except Exception:
            self.redis_client = None

        chroma_client = chromadb.PersistentClient(path=settings.CHROMA_PATH, settings=ChromaSettings(anonymized_telemetry=False))
        self.vectorstore = Chroma(client=chroma_client, collection_name=self.collection_name, embedding_function=self.embedding_function)

    def _get_loader(self, file_path, file_type, url=None):
        if url: return UnstructuredURLLoader(urls=[url], headers={"User-Agent": "Mozilla/5.0"})
        if file_type == "application/pdf": return PyPDFLoader(file_path)
        if file_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document": return UnstructuredWordDocumentLoader(file_path)
        if file_type == "text/markdown": return UnstructuredMarkdownLoader(file_path)
        if file_type.startswith("text/"): return TextLoader(file_path)
        return UnstructuredWordDocumentLoader(file_path)

    def _invalidate_project_cache(self):
        """Invalidates all caches related to a project."""
        if not self.redis_client: return
        try:
            rag_query_keys = [k.decode('utf-8') for k in self.redis_client.scan_iter(f"rag_cache:{self.project.id}:*")]
            if rag_query_keys: self.redis_client.delete(*rag_query_keys)
            
            self.redis_client.delete(get_bm25_cache_key(str(self.project.id)))
            self.redis_client.delete(get_docs_cache_key(str(self.project.id)))
            
            logger.info(f"Invalidated all caches for project {self.project.id}.")
        except Exception as e:
            logger.error(f"Failed to clear Redis cache for project {self.project.id}: {e}", exc_info=True)

    def process_document(self, storage_key, file_type, file_name, document_id, url=None):
        if self.project.llm_provider == "ollama":
            _ensure_ollama_model_is_available(self.project.llm_model_name)
            
        logger.info(f"Processing document: {file_name}")
        if url:
            docs = self._get_loader(None, file_type, url=url).load()
        else:
            with tempfile.NamedTemporaryFile(delete=True, suffix=f"_{file_name}") as tmp:
                storage_service.download_file(storage_key, tmp.name)
                docs = self._get_loader(tmp.name, file_type).load()
        
        if not docs: return
        
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=settings.CHUNK_SIZE, chunk_overlap=settings.CHUNK_OVERLAP)
        chunks = text_splitter.split_documents(docs)
        if not chunks: return

        for chunk in chunks:
            chunk.metadata['document_id'] = document_id
            chunk.metadata.setdefault('source', url or file_name)

        self.vectorstore.add_documents(documents=chunks)
        self._invalidate_project_cache()
        logger.info(f"Added {len(chunks)} chunks for document {document_id}. Caches invalidated.")
    
    # **FIX: Correct implementation for deleting chunks via LangChain wrapper**
    def delete_document_chunks(self, document_id: str):
        """
        Deletes all vector chunks associated with a specific document ID.
        This now correctly fetches the chunk IDs first, then deletes them.
        """
        logger.info(f"Preparing to delete chunks for document_id: {document_id}")
        try:
            # Step 1: Get the ChromaDB collection object.
            collection = self.vectorstore._collection
            
            # Step 2: Find all chunks with the matching document_id metadata.
            # We only need the 'ids' field, so we can pass an empty include list.
            chunks_to_delete = collection.get(where={"document_id": document_id}, include=[])
            
            # Step 3: Extract the list of unique IDs.
            ids_to_delete = chunks_to_delete['ids']

            if not ids_to_delete:
                logger.info(f"No chunks found for document_id: {document_id}. Nothing to delete.")
                return

            # Step 4: Call the delete method with the specific list of IDs.
            logger.info(f"Found {len(ids_to_delete)} chunks to delete. Deleting now...")
            self.vectorstore.delete(ids=ids_to_delete)
            
            # Step 5: Invalidate the project's caches.
            self._invalidate_project_cache()
            logger.info(f"Successfully deleted chunks for doc {document_id} and invalidated caches.")
        except Exception as e:
            logger.error(f"Error during chunk deletion for document {document_id}: {e}", exc_info=True)


    def _get_all_project_docs_from_chroma(self) -> List[Document]:
        """Loads all documents from ChromaDB. This is the 'slow' path."""
        try:
            logger.info(f"Loading all project documents from ChromaDB for project {self.project.id}...")
            results = self.vectorstore.get(include=["metadatas", "documents"])
            all_docs = [Document(page_content=text, metadata=meta or {}) for text, meta in zip(results['documents'] or [], results['metadatas'] or [])]
            logger.info(f"Loaded {len(all_docs)} documents from ChromaDB.")
            
            if self.redis_client and all_docs:
                docs_cache_key = get_docs_cache_key(str(self.project.id))
                self.redis_client.set(docs_cache_key, pickle.dumps(all_docs), ex=3600)
            
            return all_docs
        except Exception as e:
            logger.error(f"Failed to load all project documents from Chroma: {e}", exc_info=True)
            return []

    def _get_or_create_bm25_retriever(self) -> BM25Retriever:
        """
        Stateful BM25 Retriever.
        Tries to load from Redis cache first. If not found, builds it from Chroma and caches it.
        """
        bm25_cache_key = get_bm25_cache_key(str(self.project.id))
        docs_cache_key = get_docs_cache_key(str(self.project.id))

        if self.redis_client and (cached_retriever := self.redis_client.get(bm25_cache_key)):
            logger.info("BM25 Retriever loaded from Redis cache.")
            return pickle.loads(cached_retriever)
        
        all_docs = []
        if self.redis_client and (cached_docs := self.redis_client.get(docs_cache_key)):
            logger.info("Document chunks for BM25 loaded from Redis cache.")
            all_docs = pickle.loads(cached_docs)
        
        if not all_docs:
            all_docs = self._get_all_project_docs_from_chroma()

        if not all_docs:
            return None

        logger.info("Building new BM25 Retriever and caching it to Redis...")
        bm25_retriever = BM25Retriever.from_documents(all_docs, k=5)
        if self.redis_client:
            self.redis_client.set(bm25_cache_key, pickle.dumps(bm25_retriever), ex=3600)
            
        return bm25_retriever

    def query(self, message: str) -> Tuple[str, List[Dict[str, Any]]]:
        if self.redis_client and (cached_result := self.redis_client.get(f"rag_cache:{self.project.id}:{hashlib.sha256(message.encode()).hexdigest()}")):
            return json.loads(cached_result)['answer'], json.loads(cached_result)['sources']

        bm25_retriever = self._get_or_create_bm25_retriever()
        if not bm25_retriever:
            return "This project has no documents. Please upload a document to begin.", []
            
        vector_retriever = self.vectorstore.as_retriever(search_kwargs={"k": 5})
        ensemble_retriever = EnsembleRetriever(retrievers=[bm25_retriever, vector_retriever], weights=[0.5, 0.5])

        hyde_prompt = ChatPromptTemplate.from_template("Write a short hypothetical doc for this question: {question}")
        hypothetical_doc = (hyde_prompt | self.llm).invoke({"question": message}).content
        final_docs = ensemble_retriever.invoke(hypothetical_doc)
        
        if not final_docs:
            return "I couldn't find relevant information in your documents to answer the query.", []

        context_text = "\n\n---\n\n".join([doc.page_content for doc in final_docs])
        rag_prompt = ChatPromptTemplate.from_template("""
            You are a specialized assistant for answering questions based ONLY on the provided context.
            CRITICAL INSTRUCTIONS:
            1. ONLY use information from the `<context>` tags.
            2. DO NOT use outside knowledge.
            3. If the answer is not in the context, you MUST state "The provided documents do not contain an answer to this question."
            <context>
            {context}
            </context>
            Based *only* on the context above, answer this question:
            <question>
            {question}
            </question>
            Answer:
        """)
        answer = (rag_prompt | self.llm).invoke({"context": context_text, "question": message}).content
        
        unique_sources = {}
        for doc in final_docs:
            source_name = doc.metadata.get("source", "Unknown")
            if source_name not in unique_sources:
                unique_sources[source_name] = doc

        sources_info = [{"content": doc.page_content, "source": doc.metadata.get("source", "Unknown")} for doc in unique_sources.values()]

        if self.redis_client:
            result_to_cache = {"answer": answer, "sources": sources_info}
            self.redis_client.set(f"rag_cache:{self.project.id}:{hashlib.sha256(message.encode()).hexdigest()}", json.dumps(result_to_cache), ex=3600)

        return answer, sources_info