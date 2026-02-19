FROM python:3.11-slim

WORKDIR /app

# System dependencies for opencv-python, pdf2image, and other tools
RUN apt-get update && apt-get install -y \
    poppler-utils \
    libgl1 \
    libglib2.0-0 \
    libglib2.0-dev \
    libsm6 \
    libxext6 \
    libxrender-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

COPY . .

COPY app/nhomaid@is.com.sa-2025-07-17T19_17_53.024Z.pem /app/oci_key.pem

EXPOSE 80

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "80"]

