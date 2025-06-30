## Chat with Documents

This application allows you to upload documents and interact with them using an AI assistant. You can ask questions about your documents and receive answers with source citations.

### Features

* Upload documents (PDF, DOCX, TXT, MD)
* Add content from URLs
* Chat with your documents using a Large Language Model
* View source citations for answers
* Manage projects to organize your documents
* User authentication and multi-tenancy

### Prerequisites

* Docker and Docker Compose installed
* Google AI API Key (for embeddings and LLM)
* Groq API Key (for LLM)

### Setup and Running

1. **Clone the repository:**

    ```bash
    git clone https://github.com/mithunparab/chat-with-documents.git
    cd chat-with-documents
    ```

2. **Create a `.env` file:**
    In the root directory of the project, create a file named `.env` and add your API keys:

    ```env
    GOOGLE_API_KEY=your_google_api_key_here
    GROQ_API_KEY=your_groq_api_key_here
    # --- Database Credentials ---
    # If running locally or need to override Docker defaults:
    # POSTGRES_USER=your_postgres_user
    # POSTGRES_PASSWORD=your_postgres_password
    # POSTGRES_DB=your_postgres_db
    # POSTGRES_SERVER=localhost
    # POSTGRES_PORT=5432
    # --- MinIO Credentials ---
    # If running locally or need to override Docker defaults:
    # MINIO_ROOT_USER=your_minio_access_key
    # MINIO_ROOT_PASSWORD=your_minio_secret_key
    # --- JWT Secret ---
    JWT_SECRET_KEY=your_jwt_secret_key_here
    JWT_ALGORITHM=HS256
    ```

    *Note: The `POSTGRES_SERVER` should be `postgres` when running within Docker Compose, and `localhost` for local development commands.*

3. **Build and Run with Docker Compose:**

    ```bash
    docker-compose up --build
    ```

    This command will build the Docker images, set up the containers (PostgreSQL, MinIO, API, Frontend), and start them.

4. **Access the Application:**
    Open your web browser and go to:
    [http://localhost:8501](http://localhost:8501)

### Project Structure

```
.
├── README.md
├── cli.py                  # Command-line interface (less used now)
├── docker-compose.yml      # Orchestrates all services
├── Dockerfile              # For the main API service
├── pyproject.toml          # Project dependencies and metadata
├── .env                    # Environment variables (API keys, DB creds)
├── .python-version         # Specifies Python version
├── alembic/                # Alembic migration scripts (if used)
├── alembic.ini             # Alembic configuration (if used)
├── app/                    # Backend API code
│   ├── __init__.py
│   ├── main.py             # FastAPI application entry point
│   ├── api/                # API endpoints
│   │   ├── __init__.py
│   │   └── v1/             # API version 1
│   │       ├── __init__.py
│   │       ├── auth.py     # User signup and login
│   │       ├── chat.py     # Chat functionalities
│   │       ├── documents.py# Document upload and management
│   │       └── projects.py # Project management
│   ├── auth/               # Authentication logic
│   │   ├── jwt.py          # JWT token handling
│   │   └── schemas.py      # Pydantic schemas for auth
│   ├── core/               # Core application logic
│   │   ├── __init__.py
│   │   ├── config.py       # Application settings
│   │   ├── dependencies.py # FastAPI dependencies (e.g., get_current_user)
│   │   ├── logging_config.py # Logging setup
│   │   └── celery_app.py   # Celery application instance
│   ├── db/                 # Database interactions
│   │   ├── crud.py         # Database CRUD operations
│   │   ├── database.py     # Database connection and session management
│   │   ├── models.py       # SQLAlchemy ORM models
│   │   └── schemas.py      # Pydantic schemas for database operations
│   ├── services/           # Business logic services
│   │   ├── __init__.py
│   │   ├── rag_service.py  # AI/RAG logic for chatting with documents
│   │   └── storage_service.py # MinIO/S3 file storage interaction
│   └── tasks.py            # Celery tasks (e.g., document processing)
└── frontend/               # Streamlit frontend code
    ├── app.py              # Main Streamlit application
    ├── Dockerfile          # Dockerfile for the frontend service
    └── requirements.txt    # Frontend dependencies
```

### Troubleshooting

* **Connection Refused:** Ensure `docker-compose up` is running. If connecting locally via `localhost:8501`, make sure your API is running on `localhost:8000`. If running in Docker and connecting via `http://api:8000`, ensure the `api` service is healthy. Check environment variables in `.env` and `docker-compose.yml`.
* **Database Errors:** Ensure your `POSTGRES_SERVER` setting correctly points to `localhost` for local commands and `postgres` for Docker containers. Verify the `postgres` container is healthy and running. If tables are missing, try removing the `postgres_data` Docker volume (`docker volume rm <your_volume_name>`) and restarting `docker-compose up --build`.
* **API Errors (500):** Check the `chat_with_docs_api` container logs for detailed Python tracebacks.

---
