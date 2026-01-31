#!/usr/bin/env bash
set -o errexit

echo "🔧 Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

echo "🗄️ Running database migrations..."
python manage.py migrate

echo "👤 Ensuring admin superuser exists..."
python manage.py create_superuser_if_not_exists

echo "🎨 Collecting static files..."
python manage.py collectstatic --noinput

echo "✅ Build completed successfully."
