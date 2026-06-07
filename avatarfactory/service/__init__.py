"""
AvatarFactory Service Layer.

FastAPI-based REST API for AvatarFactory.

Requires optional dependencies: pip install avatarfactory[service]
"""

try:
    from avatarfactory.service.app import app, create_app

    __all__ = ["app", "create_app"]
except ImportError:
    app = None
    create_app = None
    __all__ = []
