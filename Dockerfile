# نستخدم النسخة الكاملة بدلاً من slim لتجنب مشاكل الخطوط
FROM python:3.11

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH="${PYTHONPATH}:/app"

# تحديث النظام وتثبيت مكتبات معالجة الخطوط الضرورية جداً
RUN apt-get update && apt-get install -y \
    libfreetype6 \
    libfreetype6-dev \
    libfribidi-dev \
    libharfbuzz-dev \
    libjpeg-dev \
    libopenjp2-7-dev \
    libraqm-dev \
    zlib1g-dev \
    fontconfig \
    && rm -rf /var/lib/apt/lists/*

# إعادة تثبيت Pillow لضمان ربطه بالمكتبات الجديدة
COPY requirements.txt .
RUN pip install --no-cache-dir --force-reinstall -r requirements.txt

COPY . .
# التأكد من صلاحيات المجلدات
RUN mkdir -p /app/data /app/assets && chmod -R 777 /app/data /app/assets

CMD ["python", "-m", "src.main"]