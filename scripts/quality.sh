#!/bin/bash
# Quality check script for the RAG chatbot codebase

echo "🔍 Running code quality checks..."
echo

# Change to project root
cd "$(dirname "$0")/.."

# Format code
echo "📐 Formatting code with black..."
uv run black backend/ main.py
echo

# Sort imports
echo "🔢 Sorting imports with isort..."
uv run isort backend/ main.py
echo

# Run linting
echo "🔍 Linting with flake8..."
uv run flake8 backend/ main.py --max-line-length=88 --extend-ignore=E203,W503
echo

echo "✅ Quality checks complete!"