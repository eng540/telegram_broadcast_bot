FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH="${PYTHONPATH}:/app"

# تثبيت مكتبات النظام الضرورية لمعالجة الصور (مهم لـ Pillow)
RUN apt-get update && apt-get install -y \
    libfreetype6-dev \
    libfribidi-dev \
    libharfbuzz-dev \
    libjpeg-dev \
    zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# نسخ الكود
COPY . .

# نسخ مجلد الأصول (الخطوط والصور)
COPY assets /app/assets

# التأكد من وجود مجلد البيانات
RUN mkdir -p /app/data

CMD ["python", "-m", "src.main"]