#!/usr/bin/env bash
set -o errexit

echo "🔧 Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

echo "🗄️ Running database migrations..."
python manage.py migrate

echo "🎨 Collecting static files..."
python manage.py collectstatic --noinput

echo "✅ Build completed successfully."
