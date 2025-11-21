FROM python:3.9-slim

# 1. এই লাইনটি লগ জ্যাম হওয়া আটকাবে (খুব জরুরি)
ENV PYTHONUNBUFFERED=1

# 2. ভিডিও প্রসেসিংয়ের জন্য FFmpeg ইনস্টল
RUN apt-get update && \
    apt-get install -y ffmpeg && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# 3. Render এর অটোমেটিক পোর্টে রান হবে
CMD gunicorn --bind 0.0.0.0:$PORT main:app
