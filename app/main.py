import logging
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.api.v1 import api_router
from app.core.config_file import get_settings
from app.core.exceptions import APIException
# Import logging module to initialize loggers
from app.core import logging as app_logging  # noqa: F401
# Import async tasks to register them
from app.core.files import tasks as files_tasks  # noqa: F401
from app.core.async_tasks import AsyncTaskService
from app.core.db.session import SessionLocal

settings = get_settings()
logger = logging.getLogger(__name__)

app = FastAPI(
    title="AiutoX ERP API",
    version="0.1.0",
    description="Backend API para AiutoX ERP",
    docs_url="/docs",
    openapi_url="/openapi.json",
)


def add_security_headers(response: Response) -> None:
    """Add security headers to a response."""
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"

    # Content Security Policy
    # Note: frame-ancestors must be in CSP header, not meta tag
    csp = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "font-src 'self' https://fonts.gstatic.com; "
        "img-src 'self' data: https:; "
        "connect-src 'self' http://localhost:8000 https:; "
        "frame-ancestors 'none'; "
        "base-uri 'self'; "
        "form-action 'self'; "
        "worker-src 'self' blob:;"
    )
    response.headers["Content-Security-Policy"] = csp


class CORSEnforcementMiddleware(BaseHTTPMiddleware):
    """Middleware to ensure CORS headers are always added, even for errors."""

    def __init__(self, app, allowed_origins: list[str]):
        super().__init__(app)
        self.allowed_origins = allowed_origins

    async def dispatch(self, request: Request, call_next):
        try:
            response = await call_next(request)
        except Exception as e:
            # Create error response with CORS headers
            from fastapi.responses import JSONResponse
            error_response = JSONResponse(
                status_code=500,
                content={
                    "error": {
                        "code": "INTERNAL_SERVER_ERROR",
                        "message": "An internal server error occurred",
                        "details": {"error": str(e)} if settings.DEBUG else None,
                    },
                    "data": None,
                },
            )
            origin = request.headers.get("origin")
            if origin and origin in self.allowed_origins:
                error_response.headers["Access-Control-Allow-Origin"] = origin
                error_response.headers["Access-Control-Allow-Credentials"] = "true"
            add_security_headers(error_response)
            return error_response

        # Ensure CORS headers are present even if middleware didn't add them
        origin = request.headers.get("origin")
        if origin and origin in self.allowed_origins:
            if "Access-Control-Allow-Origin" not in response.headers:
                response.headers["Access-Control-Allow-Origin"] = origin
                response.headers["Access-Control-Allow-Credentials"] = "true"

        add_security_headers(response)
        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware to add security headers to all responses."""

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        add_security_headers(response)
        return response


# CORS configuration (must be added BEFORE SecurityHeadersMiddleware so CORS headers are added first)
if settings.CORS_ORIGINS:
    origins = [origin.strip() for origin in settings.CORS_ORIGINS.split(",")]
    # Always include common localhost variants for development
    if "http://127.0.0.1:3000" not in origins:
        origins.append("http://127.0.0.1:3000")
    if "http://localhost:3000" not in origins:
        origins.append("http://localhost:3000")
    if "http://localhost:5173" not in origins:
        origins.append("http://localhost:5173")
else:
    origins = ["http://localhost:5173", "http://localhost:3000", "http://127.0.0.1:3000"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add CORS enforcement middleware (after CORS middleware to ensure headers are always present)
app.add_middleware(CORSEnforcementMiddleware, allowed_origins=origins)

# Add security headers middleware (after CORS)
app.add_middleware(SecurityHeadersMiddleware)


@app.exception_handler(APIException)
async def api_exception_handler(request: Request, exc: APIException) -> JSONResponse:
    """Handle APIException and return standard error format.

    This ensures all APIException instances return the standard error format
    defined in rules/api-contract.md.
    """
    # exc.detail already contains {"error": {...}}, add data: null for API contract compliance
    response_content = exc.detail.copy()
    response_content["data"] = None
    response = JSONResponse(
        status_code=exc.status_code,
        content=response_content,
    )
    # Ensure CORS headers are added even for errors
    origin = request.headers.get("origin")
    if origin and origin in origins:
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Credentials"] = "true"
    add_security_headers(response)
    return response


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Handle Pydantic validation errors and format them according to API contract.

    Converts FastAPI's default validation error format to the standard API contract format.
    """
    # Convert FastAPI validation errors to standard format
    details = {}
    for error in exc.errors():
        # Extract field path (e.g., ["body", "name"] -> "name")
        field_path = error["loc"]
        # Ignore "body", "query", "path" and get the actual field name
        field_name = field_path[-1] if len(field_path) > 1 else field_path[0]

        # Add message to field
        if field_name not in details:
            details[field_name] = []
        details[field_name].append(error["msg"])

    response_content = {
        "error": {
            "code": "VALIDATION_ERROR",
            "message": "Validation failed",
            "details": details,
        },
        "data": None,
    }

    response = JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=response_content,
    )
    # Ensure CORS headers are added even for errors
    origin = request.headers.get("origin")
    if origin and origin in origins:
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Credentials"] = "true"
    add_security_headers(response)
    return response


@app.get("/healthz", tags=["system"])
def healthz():
    """Health check endpoint."""
    return {
        "status": "ok",
        "env": settings.ENV,
        "debug": settings.DEBUG,
    }


# Global exception handler for unhandled exceptions
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle all unhandled exceptions and ensure CORS headers are added."""
    # #region agent log
    import json
    try:
        with open(r"d:\Documents\Mis_proyectos\Proyectos_Actuales\aiutox_erp_core\.cursor\debug.log", "a", encoding="utf-8") as f:
            f.write(json.dumps({"location": "main.py:160", "message": "Global exception handler called", "data": {"exception_type": type(exc).__name__, "exception_msg": str(exc), "path": str(request.url.path), "origin": request.headers.get("origin")}, "timestamp": int(__import__("time").time() * 1000), "sessionId": "debug-session", "runId": "run1", "hypothesisId": "A"}) + "\n")
    except: pass
    # #endregion agent log

    logger.exception(f"Unhandled exception: {exc}")

    response_content = {
        "error": {
            "code": "INTERNAL_SERVER_ERROR",
            "message": "An internal server error occurred",
            "details": {"error": str(exc)} if settings.DEBUG else None,
        },
        "data": None,
    }

    response = JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=response_content,
    )

    # #region agent log
    try:
        with open(r"d:\Documents\Mis_proyectos\Proyectos_Actuales\aiutox_erp_core\.cursor\debug.log", "a", encoding="utf-8") as f:
            f.write(json.dumps({"location": "main.py:178", "message": "Before adding CORS headers", "data": {"origins_defined": "origins" in globals(), "origins_value": globals().get("origins", "NOT_FOUND"), "origin_header": request.headers.get("origin")}, "timestamp": int(__import__("time").time() * 1000), "sessionId": "debug-session", "runId": "run1", "hypothesisId": "B"}) + "\n")
    except: pass
    # #endregion agent log

    # Ensure CORS headers are added even for errors
    origin = request.headers.get("origin")
    if origin and origin in origins:
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Credentials"] = "true"

    # #region agent log
    try:
        with open(r"d:\Documents\Mis_proyectos\Proyectos_Actuales\aiutox_erp_core\.cursor\debug.log", "a", encoding="utf-8") as f:
            f.write(json.dumps({"location": "main.py:183", "message": "After adding CORS headers", "data": {"cors_origin": response.headers.get("Access-Control-Allow-Origin"), "cors_credentials": response.headers.get("Access-Control-Allow-Credentials"), "all_headers": dict(response.headers)}, "timestamp": int(__import__("time").time() * 1000), "sessionId": "debug-session", "runId": "run1", "hypothesisId": "C"}) + "\n")
    except: pass
    # #endregion agent log

    add_security_headers(response)
    return response


# Include API routers
app.include_router(api_router, prefix="/api/v1")

# Initialize async task scheduler
async_task_service: AsyncTaskService | None = None


@app.on_event("startup")
async def startup_event():
    """Initialize async task scheduler on startup."""
    global async_task_service
    try:
        db = SessionLocal()
        async_task_service = AsyncTaskService(db)
        await async_task_service.start_scheduler()
        logger.info("Async task scheduler started")
    except Exception as e:
        logger.error(f"Failed to start async task scheduler: {e}", exc_info=True)


@app.on_event("shutdown")
async def shutdown_event():
    """Stop async task scheduler on shutdown."""
    global async_task_service
    if async_task_service:
        try:
            await async_task_service.stop_scheduler()
            if hasattr(async_task_service, 'db'):
                async_task_service.db.close()
            logger.info("Async task scheduler stopped")
        except Exception as e:
            logger.error(f"Error stopping async task scheduler: {e}", exc_info=True)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
