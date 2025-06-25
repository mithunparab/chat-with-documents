from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain.schema import Document
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_chroma import Chroma
import shutil
import os
import glob
from dotenv import load_dotenv
load_dotenv()

os.environ["GOOGLE_API_KEY"] = os.getenv("GOOGLE_API_KEY")
os.environ["GROQ_API_KEY"] = os.getenv("GROQ_API_KEY")

CHROMA_PATH = "chroma"
DATA_PATH = "data/books"

def main():
    generate_data_store()

def load_documents():
    documents = []
    pdf_files = glob.glob(os.path.join(DATA_PATH, "**/*.pdf"), recursive=True)
    
    for pdf_file in pdf_files:
        try:
            loader = PyPDFLoader(pdf_file)
            docs = loader.load()
            documents.extend(docs)
            print(f"Loaded {len(docs)} pages from {pdf_file}")
        except Exception as e:
            print(f"Error loading {pdf_file}: {e}")
    
    print(f"Total documents loaded: {len(documents)}")
    return documents

def split_text(documents: list[Document]):
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=300, 
        chunk_overlap=100,
        length_function=len,
        add_start_index=True,)
    chunks = text_splitter.split_documents(documents)
    print(f"Split {len(documents)} documents into {len(chunks)} chunks.")
    return chunks


def save_to_chroma(chunks: list[Document]):
    if os.path.exists(CHROMA_PATH):
        shutil.rmtree(CHROMA_PATH)
    db = Chroma.from_documents(
        chunks, GoogleGenerativeAIEmbeddings(model="models/embedding-001"), persist_directory=CHROMA_PATH
    )
    print(f"Saved {len(chunks)} chunks to Chroma database at {CHROMA_PATH}.")

def generate_data_store():
    documents = load_documents()
    chunks = split_text(documents)
    save_to_chroma(chunks)

if __name__ == "__main__":
    main()
    print("Data store generation complete.")