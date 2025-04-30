# Use official Python image
FROM python:3.11-slim

# Set work directory
WORKDIR /app

# Copy requirements and install
COPY ../requirements.txt /app/requirements.txt
RUN apt-get update && apt-get install -y gcc libpq-dev && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copy server code
COPY . /app

# Expose port (adjust if your server uses a different port)
EXPOSE 8000

# Default command (adjust if your entrypoint is different)
CMD ["flask", "run", "--host=0.0.0.0", "--port=8000"]