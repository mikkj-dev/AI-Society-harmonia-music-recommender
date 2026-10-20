# Build from the repository root:  docker build -t harmonia-api -f backend/Dockerfile .
FROM python:3.12-slim
WORKDIR /app
COPY backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt
COPY backend backend
COPY scripts scripts
COPY data data
RUN python scripts/prepare_data.py
ENV HARMONIA_CORS_ORIGINS=http://localhost:3000
EXPOSE 8000
CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
