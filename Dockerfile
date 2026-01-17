FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# نسخ ملف requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# نسخ كل الملفات إلى الحاوية
COPY . .

# ضبط PYTHONPATH ليعرف مجلد src
ENV PYTHONPATH="${PYTHONPATH}:/app"

# أمر التشغيل
CMD ["python", "-m", "src.main"]