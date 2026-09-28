"""
Application-wide rate limiter powered by SlowAPI.

Import ``limiter`` in any router to annotate endpoints, e.g.::

    from app.core.limiter import limiter

    @router.post("/login")
    @limiter.limit("10/minute")
    def login(request: Request, ...): ...

The limiter is wired into the FastAPI app in ``main.py``.
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
