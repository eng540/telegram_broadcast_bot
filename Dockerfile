# نستخدم نسخة Bookworm لدعم Playwright والخطوط
FROM python:3.11-slim-bookworm

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH="${PYTHONPATH}:/app"

# 1. تحديث النظام وتثبيت المكتبات الأساسية
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    libfreetype6 \
    libfreetype6-dev \
    libfribidi-dev \
    fontconfig \
    && rm -rf /var/lib/apt/lists/*

# 2. تثبيت مكتبات بايثون
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 3. تثبيت المتصفح (Playwright)
RUN playwright install --with-deps chromium

# 4. نسخ الكود والأصول
COPY . .

# 5. إنشاء المجلدات الضرورية وصلاحياتها
RUN mkdir -p /app/data /app/assets /app/templates /app/src/resources
RUN chmod -R 777 /app/data /app/assets

CMD ["python", "-m", "src.main"]