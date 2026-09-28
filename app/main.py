import uuid

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.core.config import settings
from app.core.database import Base, engine
from app.core.limiter import limiter
from app.core.logging import setup_logging, request_id_var, get_logger
from app.routers import auth, centres, bookings, payments

# ---- Bootstrap ----
setup_logging()
logger = get_logger(__name__)

# For this assignment we create tables directly on startup instead of
# wiring up Alembic migrations, to keep the project easy to run in one
# command. See README "Assumptions" for the tradeoff.
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Diagnostic test booking and simulated payment service for EVE Healthcare.",
    version="1.0.0",
)

# ---- Rate-limiting ----
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


# ---- Middleware ----
@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    """Attach a unique request-ID to every request for structured-log tracing."""
    rid = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    request_id_var.set(rid)
    logger.info("%s %s", request.method, request.url.path)
    response = await call_next(request)
    response.headers["X-Request-ID"] = rid
    return response


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


# ---- Routers ----
app.include_router(auth.router)
app.include_router(centres.router)
app.include_router(bookings.router)
app.include_router(payments.router)


@app.get("/health", tags=["health"])
def health():
    return {"status": "ok"}
