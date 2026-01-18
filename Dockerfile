FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH="${PYTHONPATH}:/app"

# تثبيت المتطلبات
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# نسخ الكود
COPY . .

# إنشاء مجلد البيانات للتأكد من وجوده
RUN mkdir -p /app/data

CMD ["python", "-m", "src.main"]