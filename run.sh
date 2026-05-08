#!/usr/bin/env bash
set -e

# Run migrations at startup (before gunicorn starts)
echo "Running migrations..."
python manage.py migrate

echo "Creating demo users..."
python manage.py create_demo_users

echo "Starting gunicorn..."
exec gunicorn webapp.wsgi:application --bind 0.0.0.0:$PORT
