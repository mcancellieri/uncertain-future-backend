FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    && rm -rf /var/lib/apt-get/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 5000

# Run Gunicorn with 1 worker to save RAM on Render's free tier
CMD ["gunicorn", "-w", "1", "-b", "0.0.0.0:5000", "app:app"]