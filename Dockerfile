FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN addgroup --system zerva \
    && adduser --system --ingroup zerva zerva

COPY pyproject.toml ./

# نکته: این Image عمداً Single-stage است (شامل ابزار Dev/Test هم می‌شود)؛
# طبق ZRV-BOOT-001 بخش ۲۰، جدا کردن Build/Runtime Multi-stage برای
# Production یک بهبود مستند و آگاهانه برای فاز بعد است، نه الان.
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -e . \
    && pip install --no-cache-dir pytest==9.1.1 pytest-django==4.14.0 ruff==0.16.3

COPY . .

RUN chown -R zerva:zerva /app

USER zerva

EXPOSE 8000

CMD ["daphne", "-b", "0.0.0.0", "-p", "8000", "config.asgi:application"]
