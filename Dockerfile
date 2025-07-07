# Use a stable Python base image
FROM python:3.9-slim-buster

# Set working directory
WORKDIR /app

# Install system dependencies early (so layer can be cached)
RUN apt-get update && \
    apt-get install -y ffmpeg && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of your application
COPY . .

# Optional: set environment variables
ENV PYTHONUNBUFFERED=1

# Run your bot
CMD ["python3", "main.py"]
