#!/bin/bash

# Exit immediately if a command exits with a non-zero status
set -e

# Run migrations
echo "==> Applying database migrations..."
python manage.py makemigrations --noinput
python manage.py migrate --noinput

# Collect static files
echo "==> Collecting static files..."
python manage.py collectstatic --noinput

# Start Daphne server for HTTP and WebSockets
echo "==> Starting Daphne server on port 8000..."
daphne -b 0.0.0.0 -p 8000 config.asgi:application
