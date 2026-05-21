# ─────────────────────────────────────────────
# Quiz Format Converter — Telegram Bot
# ─────────────────────────────────────────────
FROM python:3.11-slim

# Tizim paketlari: antiword (.doc fayllari uchun)
RUN apt-get update \
    && apt-get install -y --no-install-recommends antiword \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Avval faqat requirements — Docker cache uchun (kod o'zgarsa qayta yuklanmaydi)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Loyiha kodi
COPY . .

# BOT_TOKEN muhit o'zgaruvchisi sifatida beriladi (docker run -e yoki Railway Variables)
ENV PYTHONUNBUFFERED=1

CMD ["python", "main.py"]
