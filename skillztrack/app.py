"""Entry point for WSGI servers: `gunicorn wsgi:application` or `python run.py`."""
from . import admin_views, assessment_views, views, web  # noqa: F401  (importing these modules registers the routes)

web.bootstrap()
application = web.application
