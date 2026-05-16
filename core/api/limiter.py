"""Shared Flask-Limiter instance — import and call init_app(app) in create_app()."""
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(key_func=get_remote_address, default_limits=["500/day", "100/hour"])
