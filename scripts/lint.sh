#!/bin/bash
# Linting script for the RAG chatbot codebase

echo "🔍 Running linting checks..."

# Change to project root
cd "$(dirname "$0")/.."

# Run flake8
uv run flake8 backend/ main.py --max-line-length=88 --extend-ignore=E203,W503

echo "✅ Linting complete!"