#!/bin/bash

# Startup script for mock-rgs server
cd "$(dirname "$0")"

echo "🚀 Starting Mock RGS Server..."

# Use math-sdk virtual environment
VENV_PATH="../math-sdk/env/bin"

if [ ! -d "$VENV_PATH" ]; then
    echo "❌ math-sdk virtual environment not found!"
    echo "Please run: cd ../math-sdk && make setup"
    exit 1
fi

# Install Flask if not already installed
echo "📦 Installing Flask dependencies..."
$VENV_PATH/pip install Flask flask-cors -q

# Start server
echo "✅ Starting server on port 3008..."
MATH_SDK_GAME_ID=lexlooter $VENV_PATH/python server.py
