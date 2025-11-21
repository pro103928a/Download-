FROM python:3.9-slim

# Install system dependencies (FFmpeg is required for yt-dlp)
RUN apt-get update && \
    apt-get install -y ffmpeg && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Expose port 10000 (Default for Render)
EXPOSE 10000

# Run the application using Gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:10000", "--timeout", "120", "main:app"]
