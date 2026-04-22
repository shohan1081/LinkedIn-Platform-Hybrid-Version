# Use an official Python runtime as a parent image (slim version for smaller size)
FROM python:3.12-slim

# Set environment variables for better Python performance in Docker
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set the working directory in the container
WORKDIR /app

# Install system dependencies (build-essential for Pillow/PUI, netcat for entrypoint checks)
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    netcat-traditional \
    gettext \
    && rm -rf /var/lib/apt/lists/*

# Install project dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir daphne channels-redis

# Copy the project code into the container
COPY . .

# Copy and prepare the entrypoint script
COPY ./scripts/entrypoint.sh /app/scripts/entrypoint.sh
RUN chmod +x /app/scripts/entrypoint.sh

# The application runs on 8000
EXPOSE 8000

# Entrypoint script handles migrations and starting the server
ENTRYPOINT ["/app/scripts/entrypoint.sh"]
