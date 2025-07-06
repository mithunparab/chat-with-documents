# Dockerfile

# ---- Stage 1: The Builder ----
# This stage builds the dependencies and will be discarded later.
FROM python:3.12-slim as builder

# --- THIS IS THE FIX ---
# Install build-essential which contains the g++ compiler needed for C++ extensions.
# We also install git, which is sometimes required by packages to fetch source code.
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential \
    git && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install poetry
RUN pip install poetry

# Copy only the files needed to install dependencies
COPY pyproject.toml poetry.lock* ./

# Disable virtualenv creation by poetry. This is a best practice for Docker.
RUN poetry config virtualenvs.create false

# Install dependencies using the lock file.
# This will now have the C++ compiler it needs to build chroma-hnswlib.
RUN poetry install --no-root


# ---- Stage 2: The Final Production Image ----
# This is the lean image that will be used in production.
# It does NOT contain build-essential, keeping it small.
FROM python:3.12-slim

WORKDIR /app

# Install only the RUNTIME system dependencies.
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    postgresql-client \
    libgl1-mesa-glx \
    libglib2.0-0 && \
    rm -rf /var/lib/apt/lists/*

# Copy the installed python packages from the builder stage
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages

# Copy any command-line executables that were installed by packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy your application code
COPY ./app ./app

# Expose the port and set the default command
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]