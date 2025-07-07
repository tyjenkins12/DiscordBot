FROM python:3.9-slim-buster

# Set working directory
WORKDIR /app

# Install system dependencies needed for audio & building packages
RUN apt-get update && \
    apt-get install -y ffmpeg gcc python3-dev libffi-dev libssl-dev build-essential && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip setuptools wheel
RUN pip install --no-cache-dir -r requirements.txt

# Copy app source code into container
COPY . .

# Unbuffered output (logs show up immediately)
ENV PYTHONUNBUFFERED=1

# Run the bot
CMD ["python3", "main.py"]
