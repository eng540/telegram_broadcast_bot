FROM python:3.11-slim-bookworm

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH="${PYTHONPATH}:/app"

# 1. تثبيت المتصفح ومتطلباته (العملية الأثقل ولكن الأهم)
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    && rm -rf /var/lib/apt/lists/*

# تثبيت Playwright ومتصفح Chromium
RUN pip install playwright
RUN playwright install --with-deps chromium

# 2. تثبيت بقية المكتبات
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 3. نسخ الكود والأصول
COPY . .
# إنشاء المجلدات
RUN mkdir -p /app/data /app/assets /app/templates

CMD ["python", "-m", "src.main"]