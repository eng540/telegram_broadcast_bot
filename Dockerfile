# نستخدم نسخة Bookworm لأنها مستقرة وحديثة لدعم المتصفحات
FROM python:3.11-slim-bookworm

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH="${PYTHONPATH}:/app"

# 1. تحديث النظام وتثبيت أدوات أساسية
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    && rm -rf /var/lib/apt/lists/*

# 2. تثبيت مكتبات بايثون أولاً
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 3. (الخطوة الحاسمة) تثبيت المتصفح ومكتبات النظام الخاصة به
# هذا الأمر يقوم بتحميل Chromium وتثبيت كل المكتبات الناقصة في Linux
RUN playwright install --with-deps chromium

# 4. نسخ بقية الكود
COPY . .

# 5. إنشاء المجلدات الضرورية
RUN mkdir -p /app/data /app/assets /app/templates

CMD ["python", "-m", "src.main"]