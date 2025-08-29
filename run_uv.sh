#!/bin/bash
# MindAid - Development runner using uv (without venv watching)

# Add src directory to Python path
export PYTHONPATH="$PWD/src:$PYTHONPATH"

# Run the FastAPI application with uv (no reload to avoid venv restarts)
uv run uvicorn mindaid.main:app --host 0.0.0.0 --port 8000
