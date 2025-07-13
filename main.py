"""Backward compatibility entrypoint.

This module simply re-exports the FastAPI `app` instance from `api.py` so that
commands like `uvicorn main:app` continue to work."""

from api import app
