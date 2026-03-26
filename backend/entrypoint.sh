#!/bin/sh
set -e

echo "DATABASE_URL=$DATABASE_URL"
echo "Running database migrations..."
alembic upgrade head

echo "Starting server..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
