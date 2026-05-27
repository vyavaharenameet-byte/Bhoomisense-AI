# BhoomiSense backend — production image
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install deps first so Docker layer-caching skips this on code-only changes
RUN apt-get update && apt-get install -y \
    build-essential \
    cmake
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# App code + trained models (app/models/*.joblib)
COPY app ./app

EXPOSE 8000
# Render / Railway inject $PORT; default to 8000 for local runs
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
