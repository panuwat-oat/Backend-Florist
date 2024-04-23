# Dockerfile for FastAPI
FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "main:app", "--root-path=/addresses", "--reload" , "--host", "0.0.0.0", "--port", "80"]
