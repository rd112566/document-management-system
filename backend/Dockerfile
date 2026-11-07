FROM python:3.10-slim

WORKDIR /app

# Install minimal build tools & curl
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend application source
COPY . .

# Set default port
ENV PORT=8000
EXPOSE 8000

# Start FastAPI application
CMD sh -c "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"
