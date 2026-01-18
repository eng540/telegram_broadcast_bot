FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH="${PYTHONPATH}:/app"

# تثبيت مكتبات النظام (تمت إضافة libraqm-dev لدعم العربية المتقدم)
RUN apt-get update && apt-get install -y \
    libfreetype6-dev \
    libfribidi-dev \
    libharfbuzz-dev \
    libjpeg-dev \
    libraqm-dev \
    zlib1g-dev \
    fontconfig \
    wget \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
COPY assets /app/assets
RUN mkdir -p /app/data

CMD ["python", "-m", "src.main"]