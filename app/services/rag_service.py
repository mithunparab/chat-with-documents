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
from langchain_community.llms import Ollama # If using older langchain
from langchain_community.chat_models import ChatOllama # More common now
from langchain_community.embeddings import OllamaEmbeddings
from langchain_chroma import Chroma
from langchain_groq import ChatGroq
from groq import Groq as GroqClient
from langchain.prompts import ChatPromptTemplate
from langchain.retrievers.multi_query import MultiQueryRetriever
from chromadb.config import Settings as ChromaSettings

from app.core.config import settings
from app.services import storage_service
from app.db.models import Project, User
import logging

logger = logging.getLogger(__name__)

class RAGService:
    def __init__(self, user: User, project: Project) -> None:
        self.user: User = user
        self.project: Project = project
        self.collection_name: str = f"proj_{str(project.id).replace('-', '')}"
        if settings.OLLAMA_HOST:
            # Use Ollama for both LLM and Embeddings
            logger.info(f"Using Ollama provider at {settings.OLLAMA_HOST} with model {settings.OLLAMA_MODEL}")
            self.llm = ChatOllama(base_url=settings.OLLAMA_HOST, model=settings.OLLAMA_MODEL)
            # Note: You can use a different model for embeddings if you want
            self.embedding_function = OllamaEmbeddings(base_url=settings.OLLAMA_HOST, model=settings.OLLAMA_MODEL)
        else:
            # Fallback to Google and Groq if Ollama is not configured
            logger.info("Using Google and Groq providers.")
            self.embedding_function = GoogleGenerativeAIEmbeddings(model=settings.EMBEDDING_MODEL_NAME)
            http_client = httpx.Client(proxies=None)
            root_groq_client = GroqClient(api_key=settings.GROQ_API_KEY, http_client=http_client)
            self.llm = ChatGroq(model=settings.LLM_MODEL_NAME, client=root_groq_client.chat.completions)

        try:
            self.redis_client: Optional[redis.Redis] = redis.from_url(settings.CELERY_BROKER_URL)
            self.redis_client.ping()
            logger.info("Successfully connected to Redis for caching.")
        except Exception as e:
            logger.error(f"Could not connect to Redis: {e}. Caching will be disabled.", exc_info=True)
            self.redis_client = None

        chroma_client = chromadb.PersistentClient(path=settings.CHROMA_PATH, settings=ChromaSettings(anonymized_telemetry=False))
        self.vectorstore: Chroma = Chroma(
            client=chroma_client, 
            collection_name=self.collection_name,
            embedding_function=self.embedding_function,
        )

    def _get_loader(self, file_path: Optional[str], file_type: str, url: Optional[str] = None) -> Any:
        # ... (This method remains unchanged)
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
        else: # Fallback for other document types unstructured can handle
            return UnstructuredWordDocumentLoader(file_path)


    def process_document(self, storage_key: str, file_type: str, file_name: str, document_id: str, url: Optional[str] = None) -> None:
        # ... (This method remains unchanged)
        logger.info(f"Processing document_id: {document_id} for project {self.project.name}")
        if url:
            loader = self._get_loader(None, file_type, url=url)
            docs: List[Document] = loader.load()
        else:
            with tempfile.NamedTemporaryFile(delete=True, suffix=f"_{file_name}") as tmp_file:
                storage_service.download_file(storage_key, tmp_file.name)
                loader = self._get_loader(tmp_file.name, file_type)
                docs: List[Document] = loader.load()
        
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
            chunk.metadata.setdefault('source', url or file_name)

        self.vectorstore.add_documents(documents=chunks)
        logger.info(f"Added {len(chunks)} chunks for document {document_id} to '{self.collection_name}'.")
        self.clear_cache_for_project()

    def delete_document_chunks(self, document_id: str) -> None:
        # ... (This method remains unchanged)
        logger.info(f"Deleting chunks for document_id: {document_id} from '{self.collection_name}'")
        try:
            collection = self.vectorstore._collection
            existing_chunks = collection.get(where={"document_id": document_id}, include=[])
            if not existing_chunks or not existing_chunks.get('ids'):
                 logger.info(f"No chunks found for document_id: {document_id}. Nothing to delete.")
                 return
            collection.delete(where={"document_id": document_id})
            logger.info(f"Deleted {len(existing_chunks['ids'])} chunks for document_id: {document_id}.")
            self.clear_cache_for_project()
        except Exception as e:
            logger.error(f"Error deleting chunks for document {document_id}: {e}", exc_info=True)

    def clear_cache_for_project(self) -> None:
        # ... (This method remains unchanged)
        if not self.redis_client:
            return
        try:
            keys_to_delete: List[str] = [k.decode('utf-8') for k in self.redis_client.scan_iter(f"rag_cache:{self.project.id}:*")]
            if keys_to_delete:
                self.redis_client.delete(*keys_to_delete)
                logger.info(f"Invalidated {len(keys_to_delete)} cache entries for project {self.project.id}.")
        except Exception as e:
            logger.error(f"Failed to clear Redis cache for project {self.project.id}: {e}", exc_info=True)

    def query(self, message: str) -> Tuple[str, List[Dict[str, Any]]]:
        # --- CACHING LOGIC (Unchanged) ---
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

        # --- RETRIEVAL LOGIC (REWRITTEN FOR PERFORMANCE) ---
        # The old method of loading all docs into memory for BM25 is removed.
        # We now use a MultiQueryRetriever for better performance and recall.
        vector_retriever = self.vectorstore.as_retriever(search_kwargs={"k": 7})
        
        # Check if there are any documents in the vector store for this project
        # A simple way is to try a dummy search. If it fails or returns nothing, we can exit.
        try:
            # Note: A more robust check would be `self.vectorstore._collection.count() > 0`
            if not self.vectorstore._collection or self.vectorstore._collection.count() == 0:
                 return "This project has no documents processed yet. Please upload a document and wait for it to complete.", []
        except Exception:
            return "This project has no documents processed yet. Please upload a document and wait for it to complete.", []


        multi_query_retriever = MultiQueryRetriever.from_llm(
            retriever=vector_retriever, llm=self.llm
        )

        final_docs: List[Document] = multi_query_retriever.invoke(message)
        
        if not final_docs:
            return "I couldn't find relevant information in your documents to answer the query.", []

        # --- CONTEXT & PROMPT (Unchanged - Preserving your core RAG logic) ---
        context_text: str = "\n\n---\n\n".join([doc.page_content for doc in final_docs])
        
        rag_prompt = ChatPromptTemplate.from_template("""
            You are a helpful and diligent AI assistant. Your task is to answer the user's question based on the provided context.

            **Instructions:**
            1.  **Analyze the Context:** Carefully read the following context, which is composed of text chunks from one or more documents.
            2.  **Synthesize an Answer:** Formulate a comprehensive, well-structured answer to the user's question. Do not just copy-paste from the context. You must synthesize the information.
            3.  **Strictly Ground Your Answer:** Your entire response must be based *only* on the information available in the provided context. Do not use any outside knowledge.
            4.  **Handle Missing Information:** If the context does not contain the necessary information to answer the question, do not invent an answer. Instead, clearly state that the provided documents do not contain the answer. However, if the context contains information that is *related* to the question, you should present that information and explain how it relates, while still noting that a direct answer is unavailable.
            5.  **Be Conversational:** Present the answer in a clear and helpful manner.

            **Context:**
            {context}

            **Question:**
            {question}

            **Answer:**
        """)

        rag_chain = rag_prompt | self.llm
        answer: str = rag_chain.invoke({"context": context_text, "question": message}).content
        
        unique_sources: Dict[str, Dict[str, Any]] = {}
        for doc in final_docs:
            source_info: Dict[str, Any] = {"content": doc.page_content, "source": doc.metadata.get("source", "Unknown")}
            unique_sources[doc.page_content] = source_info
        
        sources: List[Dict[str, Any]] = list(unique_sources.values())
        
        # --- CACHE WRITING (Unchanged) ---
        if self.redis_client:
            try:
                result_to_cache: Dict[str, Any] = {"answer": answer, "sources": sources}
                self.redis_client.set(cache_key, json.dumps(result_to_cache), ex=3600)
                logger.info(f"Cached RAG result for project {self.project.id}")
            except Exception as e:
                logger.warning(f"Redis cache set failed: {e}", exc_info=True)

        return answer, sources