#!/bin/bash
# Code formatting script for the RAG chatbot codebase

echo "📐 Formatting code..."

# Change to project root
cd "$(dirname "$0")/.."

# Format with black
uv run black backend/ main.py

# Sort imports with isort
uv run isort backend/ main.py

echo "✅ Code formatting complete!"