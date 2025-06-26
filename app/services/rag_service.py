"""
This module provides the RAGService class for Retrieval-Augmented Generation (RAG) operations,
including document ingestion, chunking, embedding, vector database management, and LLM-based
question answering. It also manages singleton lifecycle for application-wide access.

Dependencies:
    - langchain_community
    - langchain_text_splitters
    - langchain_google_genai
    - langchain_chroma
    - langchain_groq
    - core.config.settings

TODO:
    - [ ] Implement user-specific storage for documents and embeddings.
    - [ ] Refactor synchronous I/O to async for compatibility with async web frameworks.
    - [ ] Add support for additional document formats beyond PDF.
    - [ ] Enhance error handling and logging for production robustness.
"""

import os
import glob
import shutil
from typing import List, Tuple, Optional, Dict

from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain.schema import Document
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_chroma import Chroma
from langchain_groq import ChatGroq
from langchain.prompts import ChatPromptTemplate
from core.config import settings

class RAGService:
    """
    Service for Retrieval-Augmented Generation (RAG) operations.

    Handles document ingestion, chunking, embedding, vector database management,
    and LLM-based question answering.

    Attributes:
        chroma_path (str): Filesystem path for Chroma vector database persistence.
        data_path (str): Filesystem path for document storage.
        embedding_function (GoogleGenerativeAIEmbeddings): Embedding model instance.
        llm (ChatGroq): Large Language Model instance for response generation.
        db (Chroma): Chroma vector database instance.
        prompt_template (ChatPromptTemplate): Prompt template for LLM queries.
    """

    def __init__(self) -> None:
        """
        Initialize the RAGService, setting up storage directories, embedding model,
        LLM, and vector database. Raises on critical initialization failure.
        """
        print("--- Initializing RAGService ---")
        self.chroma_path: str = settings.CHROMA_PATH
        self.data_path: str = settings.DATA_PATH
        os.makedirs(self.data_path, exist_ok=True)
        os.makedirs(self.chroma_path, exist_ok=True)
        self.prompt_template: ChatPromptTemplate = ChatPromptTemplate.from_template("""
            You are an expert assistant. Your task is to answer the user's question with a comprehensive and detailed response, based *only* on the provided context.

            Follow these rules:
            1.  Synthesize information from all relevant parts of the context to form a complete answer.
            2.  If the context contains examples, tables, or lists, use them to support your explanation.
            3.  Structure your answer clearly, using paragraphs and bullet points if helpful.
            4.  Do not introduce any external information. If the answer cannot be found in the context, state that clearly.

            Provided Context:
            ---
            {context}
            ---

            User's Question: {question}

            Your Detailed Answer:
        """)

        try:
            print("➡️  Step 1/3: Initializing GoogleGenerativeAIEmbeddings...")
            self.embedding_function: GoogleGenerativeAIEmbeddings = GoogleGenerativeAIEmbeddings(
                model=settings.EMBEDDING_MODEL_NAME
            )
            print("✅ Step 1/3: Google Embeddings initialized.")

            print("➡️  Step 2/3: Initializing ChatGroq LLM...")
            self.llm: ChatGroq = ChatGroq(model=settings.LLM_MODEL_NAME)
            print("✅ Step 2/3: ChatGroq LLM initialized.")

            print("➡️  Step 3/3: Initializing Chroma DB...")
            self.db: Chroma = Chroma(
                persist_directory=self.chroma_path,
                embedding_function=self.embedding_function
            )
            print("✅ Step 3/3: Chroma DB initialized.")
            print("--- RAGService fully initialized successfully. ---")

        except Exception as e:
            print("\n" + "="*50)
            print("❌ FATAL ERROR DURING RAG SERVICE INITIALIZATION")
            print(f"   Error Type: {type(e).__name__}")
            print(f"   Error Details: {e}")
            print("="*50 + "\n")
            raise e

    def process_documents(self):
        print("Starting document processing...")
        documents = self._load_documents()
        if not documents:
            print("No new documents to process.")
            return
            
        chunks = self._split_documents(documents)
        self._add_to_chroma(chunks)
        print("Document processing complete.")

    def _load_documents(self) -> List[Document]:
        """
        Loads all PDF documents from the data directory.

        Returns:
            List[Document]: List of loaded document pages.
        """
        pdf_files: List[str] = glob.glob(os.path.join(self.data_path, "*.pdf"))
        documents: List[Document] = []
        for pdf_file in pdf_files:
            try:
                loader = PyPDFLoader(pdf_file)
                documents.extend(loader.load())
            except Exception as e:
                print(f"Error loading {pdf_file}: {e}")
        print(f"Loaded {len(documents)} document pages.")
        return documents

    def _split_documents(self, documents: List[Document]) -> List[Document]:
        """
        Splits documents into smaller chunks for embedding and retrieval.

        Args:
            documents (List[Document]): List of loaded documents.

        Returns:
            List[Document]: List of document chunks.
        """
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=settings.CHUNK_SIZE,
            chunk_overlap=settings.CHUNK_OVERLAP,
            length_function=len,
            add_start_index=True,
        )
        chunks: List[Document] = text_splitter.split_documents(documents)
        print(f"Split documents into {len(chunks)} chunks.")
        return chunks

    def _add_to_chroma(self, chunks: List[Document]) -> None:
        """
        Adds document chunks to the Chroma vector database.

        Args:
            chunks (List[Document]): List of document chunks to add.
        """
        self.db.add_documents(chunks)
        print(f"Added {len(chunks)} chunks to Chroma (auto-persisted).")

    def query(self, message: str) -> Tuple[str, List[str]]:
        """
        Answers a user query using the RAG pipeline.

        Args:
            message (str): The user's question.

        Returns:
            Tuple[str, List[str]]: (LLM-generated answer, list of unique source filenames).
            If no relevant information is found, returns a default message and empty list.

        Raises:
            Exception: Propagates exceptions encountered during similarity search or LLM invocation.
        """
        print(f"--- Starting Query for: '{message}' ---")

        if self.db is None:
            print("❌ FATAL: self.db object is None. Database was not initialized correctly.")
            return "Error: The document database is not available.", []

        try:
            print("➡️  Attempting similarity search in ChromaDB...")
            results: List[Tuple[Document, float]] = self.db.similarity_search_with_relevance_scores(message, k=7)
            print("✅ Similarity search successful.")

        except Exception as e:
            print(f"❌ FATAL: An exception occurred during similarity_search_with_relevance_scores.")
            print(f"   Error Type: {type(e).__name__}")
            print(f"   Error Details: {e}")
            return "Error: A failure occurred while searching the document database.", []

        if not results:
            print("ℹ️  Query complete: No results returned from the database.")
            return "I couldn't find relevant information in your documents.", []

        print(f"ℹ️  Query complete: Found {len(results)} results. Top score: {results[0][1]:.4f}")

        RELEVANCE_THRESHOLD: float = 0.4  # Lowered threshold for relevance
        if results[0][1] < RELEVANCE_THRESHOLD:
            print(f"ℹ️  Top score {results[0][1]:.4f} is below threshold {RELEVANCE_THRESHOLD}.")
            return "I couldn't find relevant information in your documents.", []

        print("➡️  Passing context to the LLM for response generation...")
        try:
            context_text: str = "\n\n---\n\n".join([doc.page_content for doc, _score in results])
            prompt: str = self.prompt_template.format(context=context_text, question=message)
            response = self.llm.invoke(prompt)
            print("✅ LLM response generated successfully.")

            sources: List[str] = [os.path.basename(doc.metadata.get("source", "")) for doc, _score in results]
            unique_sources: List[str] = sorted(list(set(sources)))

            return response.content, unique_sources

        except Exception as e:
            print(f"❌ FATAL: An exception occurred during LLM response generation.")
            print(f"   Error Type: {type(e).__name__}")
            print(f"   Error Details: {e}")
            return "Error: A failure occurred while generating the AI response.", []

    def clear_database(self) -> None:
        """
        Clears all documents and vector database contents.

        Removes and recreates storage directories, and reinitializes the Chroma database instance.
        Note: This operation is destructive and cannot be undone.
        """
        if os.path.exists(self.chroma_path):
            shutil.rmtree(self.chroma_path)
        if os.path.exists(self.data_path):
            shutil.rmtree(self.data_path)
        os.makedirs(self.data_path, exist_ok=True)
        os.makedirs(self.chroma_path, exist_ok=True)
        self.db = Chroma(
            persist_directory=self.chroma_path,
            embedding_function=self.embedding_function
        )
        print("Cleared all documents and database.")

rag_service_singleton: Dict[str, Optional[RAGService]] = {"instance": None}

def initialize_rag_service() -> None:
    """
    Initializes the singleton RAGService instance.

    Should be called once on application startup. Subsequent calls are no-ops.
    """
    if rag_service_singleton["instance"] is None:
        print("Creating new RAG Service instance...")
        rag_service_singleton["instance"] = RAGService()
    else:
        print("RAG Service instance already exists.")

def get_rag_service() -> RAGService:
    """
    Retrieves the initialized singleton RAGService instance.

    Returns:
        RAGService: The singleton RAGService instance.

    Raises:
        RuntimeError: If the service has not been initialized.
    """
    if rag_service_singleton["instance"] is None:
        # Technical Debt: This safeguard is necessary due to synchronous singleton management.
        # Refactoring for async compatibility if used in async web frameworks.
        raise RuntimeError("RAG Service has not been initialized. Ensure the lifespan event is configured correctly.")
    return rag_service_singleton["instance"]