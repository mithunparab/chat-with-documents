# 📚 Chat with Documents

A powerful AI-powered document chatbot that lets you query and interact with your PDF documents using advanced language models and vector search.

## ✨ Features

- 🔍 Intelligent Document Search: Fast, accurate retrieval using ChromaDB vector search
- 🤖 Multiple AI Models: Supports Groq's language models for high-quality responses
- 📄 PDF Processing: Automatically processes and indexes PDF documents
- ⚡ Real-time Responses: Typewriter animation for engaging user experience
- 🎯 Context-Aware: Answers with relevant context and source citations
- 🖥️ Modern UI: Clean, responsive web interface for chatting with your documents
- 🔧 Easy Configuration: Simple setup with environment variables

## 🚀 Quick Start

### Prerequisites

- Docker & Docker Compose installed
- Google AI API Key
- Groq API Key

### Running the Project

1. **Stop and clean up any previous containers and data**
   ```bash
   docker-compose down --remove-orphans
   rm -rf ./data/books/* ./chroma/*/Volumes/FLASH_128GB/Mit_drive/Code/chat-with-documents/.env
   docker-compose up --build
   ```

2. **Add your PDF documents**
   - Place your PDF files in the `data/books/` directory.

3. **Start the application**
   ```bash
   docker-compose up --build
   ```

4. **Access the frontend**
   - Open [http://0.0.0.0:8501/](http://0.0.0.0:8501/) in your browser.

### Environment Variables

Create a `.env` file in the root directory with your API keys:
```env
GOOGLE_API_KEY=your_google_api_key_here
GROQ_API_KEY=your_groq_api_key_here
```

## 🖥️ User Interface

The UI is built with Streamlit for a fast, interactive chat experience:
- Upload and manage PDFs
- Ask questions and get instant answers
- View source citations for every response

- Start the stack with Docker Compose
- Interact via the web UI at [http://0.0.0.0:8501/](http://0.0.0.0:8501/)


## 📁 Project Structure

```
.
├── app
│   ├── __init__.py
│   ├── api
│   │   ├── __init__.py
│   │   └── v1
│   │       ├── __init__.py
│   │       ├── chat.py
│   │       └── documents.py
│   ├── core
│   │   ├── __init__.py
│   │   └── config.py
│   ├── main.py
│   └── services
│       ├── __init__.py
│       └── rag_service.py
├── chroma
├── cli.py
├── data
│   └── books
├── docker-compose.yml
├── Dockerfile
├── frontend
│   ├── app.py
│   ├── Dockerfile
│   └── requirements.txt
├── pyproject.toml
├── README.md
└── requirements.txt
```

## 🔧 Troubleshooting

- Ensure your `.env` file contains valid API keys and is in the root directory.
- Use `docker-compose logs` to view logs for debugging.
- For UI issues, check the Streamlit logs in the frontend container.

---