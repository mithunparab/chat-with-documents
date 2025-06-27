# Dockerfile
FROM python:3.12-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y build-essential curl postgresql-client libgl1-mesa-glx libglib2.0-0 && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml .

RUN pip install poetry
RUN poetry config virtualenvs.create false && poetry install --no-root

COPY ./app ./app

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]