# Gunakan image Python yang ringan
FROM python:3.12-slim

# Set environment variable untuk non-interaktif
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Buat direktori kerja di dalam container
WORKDIR /app

# Salin file requirements (jika ada) dan semua source code ke dalam image
COPY . /app

# Install dependencies
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# Expose port untuk FastAPI
EXPOSE 8000

# Jalankan server dengan Uvicorn
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
