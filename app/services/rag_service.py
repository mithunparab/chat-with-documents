import tempfile
from typing import List, Tuple, Dict, Any
import httpx

from langchain_community.document_loaders import (
    PyPDFLoader, UnstructuredURLLoader, UnstructuredWordDocumentLoader,
    UnstructuredMarkdownLoader, TextLoader
)
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain.schema import Document
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_chroma import Chroma
from langchain_groq import ChatGroq
from groq import Groq as GroqClient
from langchain.prompts import ChatPromptTemplate
from langchain.retrievers import BM25Retriever, EnsembleRetriever

from chromadb.config import Settings as ChromaSettings

from app.core.config import settings
from app.services import storage_service
from app.db.models import Project, User

class RAGService:
    def __init__(self, user: User, project: Project):
        self.user = user
        self.project = project
        self.collection_name = f"proj_{str(project.id).replace('-', '')}"
        
        self.embedding_function = GoogleGenerativeAIEmbeddings(model=settings.EMBEDDING_MODEL_NAME)
        
        http_client = httpx.Client(proxies=None)
        root_groq_client = GroqClient(
            api_key=settings.GROQ_API_KEY,
            http_client=http_client
        )
        self.llm = ChatGroq(
            model=settings.LLM_MODEL_NAME, 
            client=root_groq_client.chat.completions
        )
        
        chroma_client_settings = ChromaSettings(anonymized_telemetry=False)
        
        self.vectorstore = Chroma(
            collection_name=self.collection_name,
            persist_directory=settings.CHROMA_PATH,
            embedding_function=self.embedding_function,
            client_settings=chroma_client_settings  
        )


    def _get_loader(self, file_path: str, file_type: str, url: str = None) -> Any:
        if url:
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"}
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
            return UnstructuredWordDocumentLoader(file_path)

    def process_document(self, storage_key: str, file_type: str, file_name: str, url: str=None):
        print(f"Processing document: {storage_key} for project {self.project.name}")
        
        if url:
             loader = self._get_loader(None, file_type, url=url)
             docs = loader.load()
             for doc in docs:
                doc.metadata['source'] = url
        else:
            with tempfile.NamedTemporaryFile(delete=True, suffix=f"_{file_name}") as tmp_file:
                storage_service.download_file(storage_key, tmp_file.name)
                loader = self._get_loader(tmp_file.name, file_type)
                docs = loader.load()

        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=settings.CHUNK_SIZE,
            chunk_overlap=settings.CHUNK_OVERLAP
        )
        chunks = text_splitter.split_documents(docs)
        print(f"Split into {len(chunks)} chunks.")
        
        if not chunks:
            print(f"Warning: No text could be extracted from {file_name}. Skipping.")
            return

        self.vectorstore.add_documents(documents=chunks)
        print(f"Added {len(chunks)} chunks to collection '{self.collection_name}'.")

    def _get_ensemble_retriever(self, chunks: List[Document]):
        bm25_retriever = BM25Retriever.from_documents(chunks)
        bm25_retriever.k = 5
        vector_retriever = self.vectorstore.as_retriever(search_kwargs={"k": 5})
        ensemble_retriever = EnsembleRetriever(
            retrievers=[bm25_retriever, vector_retriever], weights=[0.5, 0.5]
        )
        return ensemble_retriever

    def query(self, message: str) -> Tuple[str, List[Dict[str, Any]]]:
        print(f"Querying project '{self.project.name}' with: '{message}'")
        
        hyde_prompt = ChatPromptTemplate.from_template(
            "Please write a short, hypothetical document that could answer the user's question. "
            "Question: {question}"
        )
        hyde_chain = hyde_prompt | self.llm
        hypothetical_doc = hyde_chain.invoke({"question": message}).content
        
        print(f"HyDE document generated.")

        retrieved_docs = self.vectorstore.similarity_search(hypothetical_doc, k=10)
        
        if not retrieved_docs:
             return "I couldn't find any documents in this project. Please upload some first.", []
        
        ensemble_retriever = self._get_ensemble_retriever(retrieved_docs)
        final_docs = ensemble_retriever.invoke(hypothetical_doc)
        
        if not final_docs:
            return "I couldn't find relevant information in your documents to answer the query.", []

        context_text = "\n\n---\n\n".join([doc.page_content for doc in final_docs])
        rag_prompt = ChatPromptTemplate.from_template("""
            You are an expert assistant. Answer the user's question based ONLY on the provided context.
            Pinpoint the source of your information.

            Context:
            {context}

            Question: {question}

            Answer:
        """)
        
        rag_chain = rag_prompt | self.llm
        answer = rag_chain.invoke({"context": context_text, "question": message}).content

        sources = []
        for doc in final_docs:
            source_info = {
                "content": doc.page_content,
                "source": doc.metadata.get("source", "Unknown")
            }
            if source_info not in sources:
                 sources.append(source_info)

        return answer, sources