FROM python:3.11-slim
WORKDIR /app
RUN apt-get update && apt-get install -y gcc libpq-dev tesseract-ocr tesseract-ocr-eng tesseract-ocr-hin tesseract-ocr-mar libgl1 libglib2.0-0 && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
# fonts-noto-core: Devanagari-capable font used by test_paddleocr_provider.py
# to render real Marathi text for OCR testing. ghostscript: T41's PDF/A-2b
# ingest-time conversion (storage_service.convert_to_pdfa). Kept as its own
# late layer so it doesn't invalidate the (slow) pip install layer above on rebuild.
RUN apt-get update && apt-get install -y fonts-noto-core ghostscript && rm -rf /var/lib/apt/lists/*
COPY . .
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
