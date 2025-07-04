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
* AWS Account with Administrator Access

### Provisioning EC2 instance

Launch an instance with:
- Operating System: Ubuntu (Linux/Unix)
- Instance Type: c6a.large (2 vCPU, 4GB RAM)
- Allow traffic from ports 22 (SSH), 80 (HTTP), 443 (HTTPS)
- EBS volume: 30GB GP3
- Attach IAM instance profile with S3 access permissions

### Setting up EC2 instance

After SSH connection, execute:

```bash
sudo apt update && sudo apt upgrade -y
```

### Docker Installation for Ubuntu 24.04

Run this installation script:

```bash
#!/bin/bash

# Update and install dependencies
sudo apt-get update
sudo apt-get install -y ca-certificates curl gnupg lsb-release

# Set up Docker GPG key
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc

# Add Docker repository
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "${UBUNTU_CODENAME:-$VERSION_CODENAME}") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Install Docker components
sudo apt-get update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin btop

# Add current user to docker group
sudo usermod -aG docker "$USER"

echo
echo "✅ Docker installed. User added to 'docker' group."
echo "🔄 Reboot or log out/in for group changes to apply"
```

### Clone the repository:

  ```bash
    git clone https://github.com/mithunparab/chat-with-documents.git
    cd chat-with-documents
   ```

### Configuration and Execution

Create .env configuration in the root folder and add this to .env (replace placeholder values with actual credentials):

```bash
# API Keys (replace with actual values)
GOOGLE_API_KEY=your_google_api_key_here
GROQ_API_KEY=your_groq_api_key_here

# Model Configuration
LLM_MODEL_NAME="llama3-8b-8192"
EMBEDDING_MODEL_NAME="models/embedding-001"

# Document Processing
CHUNK_SIZE=1000
CHUNK_OVERLAP=200

# Security Settings (change JWT secret in production)
JWT_SECRET_KEY="a_very_secret_key_for_jwt_token_generation"
JWT_ALGORITHM="HS256"
ACCESS_TOKEN_EXPIRE_MINUTES=1440 

# AWS Configuration
S3_BUCKET_NAME=your_s3_bucket_name_here
AWS_REGION=your_region_on_which_your_s3_bucket_is_present

# Database Settings (change credentials in production)
POSTGRES_USER=chatuser
POSTGRES_PASSWORD=chatpassword
POSTGRES_DB=chatdb
POSTGRES_SERVER=postgres
POSTGRES_PORT=5432
DATABASE_URL=postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@${POSTGRES_SERVER}:${POSTGRES_PORT}/${POSTGRES_DB}

# Hydra Settings
HYDRA_DB_USER=hydrauser
HYDRA_DB_PASSWORD=hydrapassword
HYDRA_DB_DB=hydradb

# MinIO Settings (change defaults in production)
MINIO_ROOT_USER=minioadmin
MINIO_ROOT_PASSWORD=minioadmin
MINIO_SERVER_URL=http://minio:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_BUCKET_NAME=documents

# ChromaDB
CHROMA_PATH=/app/chroma_data
```

### Build and launch with Docker:

```bash
docker-compose up --build
```

### Access the application on: http://localhost:80

```bash
Project Structure
text
.
├── Dockerfile
├── README.md
├── app
│   ├── __init__.py
│   ├── api
│   │   ├── __init__.py
│   │   └── v1
│   │       ├── __init__.py
│   │       ├── auth.py
│   │       ├── chat.py
│   │       ├── documents.py
│   │       └── projects.py
│   ├── auth
│   │   ├── jwt.py
│   │   └── schemas.py
│   ├── core
│   │   ├── __init__.py
│   │   ├── celery_app.py
│   │   ├── config.py
│   │   ├── dependencies.py
│   │   └── logging_config.py
│   ├── db
│   │   ├── crud.py
│   │   ├── database.py
│   │   ├── models.py
│   │   └── schemas.py
│   ├── main.py
│   ├── services
│   │   ├── __init__.py
│   │   ├── rag_service.py
│   │   └── storage_service.py
│   └── tasks.py
├── cli.py
├── docker-compose.yml
├── frontend
│   ├── Dockerfile
│   ├── app.py
│   └── requirements.txt
├── poetry.lock
├── pyproject.toml
└── requirements.txt
```

### Troubleshooting

* **Connection Refused:** Ensure `docker-compose up` is running. If connecting locally via `localhost:8501`, make sure your API is running on `localhost:8000`. If running in Docker and connecting via `http://api:8000`, ensure the `api` service is healthy. Check environment variables in `.env` and `docker-compose.yml`.
* **Database Errors:** Ensure your `POSTGRES_SERVER` setting correctly points to `localhost` for local commands and `postgres` for Docker containers. Verify the `postgres` container is healthy and running. If tables are missing, try removing the `postgres_data` Docker volume (`docker volume rm <your_volume_name>`) and restarting `docker-compose up --build`.
* **API Errors (500):** Check the `chat_with_docs_api` container logs for detailed Python tracebacks.

---