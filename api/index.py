"""Vercel file-based Python function for the quote API.

The Vite build is the static UI. This module is only the ``/api`` function.
Do not select the FastAPI framework preset: that sends ``/queue`` to Python
and drops the static files. The shop box worker is not this function.
Cloudflare does not load this module. ``cloudflare/worker.py`` serves the
hosted routes only, and that file does not import this module.
"""

from app.main import app

__all__ = ["app"]
