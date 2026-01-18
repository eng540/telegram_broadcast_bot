FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH="${PYTHONPATH}:/app"

# 1. تثبيت مكتبات النظام الضرورية لمعالجة الصور والخطوط
RUN apt-get update && apt-get install -y \
    libfreetype6-dev \
    libfribidi-dev \
    libharfbuzz-dev \
    libjpeg-dev \
    zlib1g-dev \
    fontconfig \
    && rm -rf /var/lib/apt/lists/*

# 2. تثبيت مكتبات بايثون
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 3. نسخ الكود المصدري
COPY . .

# 4. (هام جداً) نسخ مجلد الأصول صراحةً
COPY assets /app/assets

# 5. إنشاء مجلد البيانات
RUN mkdir -p /app/data

CMD ["python", "-m", "src.main"]