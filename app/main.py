import logging
from contextlib import asynccontextmanager
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

# Global variable for async task service
async_task_service: AsyncTaskService | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle events."""
    global async_task_service

    # Startup
    try:
        db = SessionLocal()
        async_task_service = AsyncTaskService(db)
        await async_task_service.start_scheduler()
        logger.info("Async task scheduler started")
    except Exception as e:
        logger.error(f"Failed to start async task scheduler: {e}", exc_info=True)

    yield

    # Shutdown
    if async_task_service:
        try:
            await async_task_service.stop_scheduler()
            if hasattr(async_task_service, 'db'):
                async_task_service.db.close()
            logger.info("Async task scheduler stopped")
        except Exception as e:
            logger.error(f"Error stopping async task scheduler: {e}", exc_info=True)

app = FastAPI(
    title="AiutoX ERP API",
    version="0.1.0",
    description="Backend API para AiutoX ERP",
    docs_url="/docs",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)


def add_security_headers(response: Response) -> None:
    """Add security headers to a response."""
    # Ensure all header values are properly encoded as UTF-8 strings
    def set_header_safely(key: str, value: str) -> None:
        """Set header with proper UTF-8 encoding."""
        if isinstance(value, bytes):
            try:
                value = value.decode('utf-8')
            except UnicodeDecodeError:
                # If bytes can't be decoded, use a safe fallback
                value = str(value.encode('utf-8', errors='replace'), 'utf-8')
        elif not isinstance(value, str):
            value = str(value)

        # Ensure the value can be encoded as UTF-8
        try:
            value.encode('utf-8')
            response.headers[key] = value
        except UnicodeEncodeError:
            # Replace problematic characters
            safe_value = value.encode('utf-8', errors='replace').decode('utf-8')
            response.headers[key] = safe_value

    set_header_safely("X-Content-Type-Options", "nosniff")
    set_header_safely("X-Frame-Options", "DENY")
    set_header_safely("X-XSS-Protection", "1; mode=block")
    set_header_safely("Referrer-Policy", "strict-origin-when-cross-origin")
    set_header_safely("Permissions-Policy", "geolocation=(), microphone=(), camera=()")

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
    set_header_safely("Content-Security-Policy", csp)


class CORSEnforcementMiddleware(BaseHTTPMiddleware):
    """Middleware to ensure CORS headers are always added, even for errors."""

    def __init__(self, app, allowed_origins: list[str]):
        super().__init__(app)
        self.allowed_origins = allowed_origins

    async def dispatch(self, request: Request, call_next):
        def set_header_safely(response, key: str, value: str) -> None:
            """Set header with proper UTF-8 encoding."""
            if isinstance(value, bytes):
                try:
                    value = value.decode('utf-8')
                except UnicodeDecodeError:
                    value = str(value.encode('utf-8', errors='replace'), 'utf-8')
            elif not isinstance(value, str):
                value = str(value)

            try:
                value.encode('utf-8')
                response.headers[key] = value
            except UnicodeEncodeError:
                safe_value = value.encode('utf-8', errors='replace').decode('utf-8')
                response.headers[key] = safe_value

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
                set_header_safely(error_response, "Access-Control-Allow-Origin", origin)
                set_header_safely(error_response, "Access-Control-Allow-Credentials", "true")
            add_security_headers(error_response)
            return error_response

        # Ensure CORS headers are present even if middleware didn't add them
        origin = request.headers.get("origin")
        if origin and origin in self.allowed_origins:
            if "Access-Control-Allow-Origin" not in response.headers:
                set_header_safely(response, "Access-Control-Allow-Origin", origin)
                set_header_safely(response, "Access-Control-Allow-Credentials", "true")

        add_security_headers(response)
        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware to add security headers to all responses."""

    async def dispatch(self, request: Request, call_next):
        import logging
        logger = logging.getLogger(__name__)
        logger.debug(f"SecurityHeadersMiddleware called for {request.url.path}")

        try:
            response = await call_next(request)
            logger.debug(f"SecurityHeadersMiddleware: response received from {request.url.path}, status: {response.status_code}")
            add_security_headers(response)
            return response
        except Exception as e:
            logger.error(f"Error in SecurityHeadersMiddleware for {request.url.path}: {e}", exc_info=True)
            raise


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

# Middleware to normalize request body encoding (must be FIRST middleware in execution order)
# In FastAPI, middlewares are executed in reverse order of addition
class RequestBodyEncodingMiddleware(BaseHTTPMiddleware):
    """Middleware to normalize request body encoding before FastAPI processes it."""

    async def dispatch(self, request: Request, call_next):
        import logging
        logger = logging.getLogger(__name__)

        # Only process POST/PUT/PATCH requests with JSON content
        if request.method in ["POST", "PUT", "PATCH"]:
            content_type = request.headers.get("content-type", "")
            if "application/json" in content_type:
                try:
                    # Read the raw body as bytes
                    body_bytes = await request.body()

                    if body_bytes:
                        # Try to decode as UTF-8 first
                        try:
                            body_str = body_bytes.decode("utf-8")
                            logger.debug(f"Request body decoded as UTF-8 for {request.url.path}")
                        except UnicodeDecodeError:
                            # Fallback to Latin-1/Windows-1252 (common on Windows)
                            try:
                                body_str = body_bytes.decode("latin-1")
                                logger.warning(
                                    f"Request body had encoding issues, decoded as Latin-1 for {request.url.path}. "
                                    f"Client should send UTF-8 encoded JSON."
                                )
                                # Re-encode as UTF-8 to ensure FastAPI processes it correctly
                                body_bytes = body_str.encode("utf-8")
                            except UnicodeDecodeError:
                                # Last resort: decode with error replacement
                                body_str = body_bytes.decode("utf-8", errors="replace")
                                logger.error(
                                    f"Request body has severe encoding issues for {request.url.path}, "
                                    f"using error replacement"
                                )
                                body_bytes = body_str.encode("utf-8")

                        # Replace the request body with the normalized UTF-8 version
                        # We need to modify the request's receive function
                        async def receive():
                            return {
                                "type": "http.request",
                                "body": body_bytes,
                                "more_body": False,
                            }

                        request._receive = receive

                except Exception as e:
                    logger.error(f"Error in RequestBodyEncodingMiddleware for {request.url.path}: {e}", exc_info=True)
                    # Continue with original request if middleware fails

        response = await call_next(request)
        return response


# Add header encoding fix middleware (innermost to catch all headers)
class HeaderEncodingMiddleware(BaseHTTPMiddleware):
    """Middleware to ensure all headers are properly UTF-8 encoded."""

    async def dispatch(self, request: Request, call_next):
        import logging
        logger = logging.getLogger(__name__)
        logger.debug(f"HeaderEncodingMiddleware called for {request.url.path}")

        try:
            response = await call_next(request)
            logger.debug(f"Response received from {request.url.path}, status: {response.status_code}")
        except Exception as e:
            logger.error(f"Error in call_next for {request.url.path}: {e}", exc_info=True)
            raise

        # Clean up any problematic headers
        headers_to_remove = []
        headers_to_update = {}

        try:
            logger.debug(f"Response headers type: {type(response.headers)}, value: {response.headers}")
            for key, value in response.headers.items():
                logger.debug(f"Processing header: key={key}, value={value}, value_type={type(value)}")
                try:
                    # Try to encode as UTF-8 to check for issues
                    if isinstance(value, str):
                        value.encode('utf-8')
                    elif isinstance(value, bytes):
                        value.decode('utf-8')
                    else:
                        # Convert to string and check
                        str(value).encode('utf-8')
                except (UnicodeEncodeError, UnicodeDecodeError) as e:
                    logger.error(f"Encoding error for header {key}: {e}")
                    # This header has encoding issues, remove it or fix it
                    if key.lower() not in ['content-type', 'content-length']:  # Keep essential headers
                        headers_to_remove.append(key)
                    else:
                        # Try to fix essential headers
                        try:
                            if isinstance(value, bytes):
                                fixed_value = value.decode('utf-8', errors='replace')
                            else:
                                fixed_value = str(value).encode('utf-8', errors='replace').decode('utf-8')
                            headers_to_update[key] = fixed_value
                        except:
                            headers_to_remove.append(key)
        except Exception as e:
            logger.error(f"Error in HeaderEncodingMiddleware: {e}", exc_info=True)

        # Remove problematic headers
        for key in headers_to_remove:
            response.headers.pop(key, None)

        # Update fixed headers
        for key, value in headers_to_update.items():
            response.headers[key] = value

        return response


@app.exception_handler(APIException)
async def api_exception_handler(request: Request, exc: APIException) -> JSONResponse:
    """Handle APIException and return standard error format.

    This ensures all APIException instances return the standard error format
    defined in rules/api-contract.md.
    """
    def set_header_safely(response, key: str, value: str) -> None:
        """Set header with proper UTF-8 encoding."""
        if isinstance(value, bytes):
            try:
                value = value.decode('utf-8')
            except UnicodeDecodeError:
                value = str(value.encode('utf-8', errors='replace'), 'utf-8')
        elif not isinstance(value, str):
            value = str(value)

        try:
            value.encode('utf-8')
            response.headers[key] = value
        except UnicodeEncodeError:
            safe_value = value.encode('utf-8', errors='replace').decode('utf-8')
            response.headers[key] = safe_value

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
        set_header_safely(response, "Access-Control-Allow-Origin", origin)
        set_header_safely(response, "Access-Control-Allow-Credentials", "true")
    add_security_headers(response)
    return response


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Handle Pydantic validation errors and format them according to API contract.

    Converts FastAPI's default validation error format to the standard API contract format.
    """
    def set_header_safely(response, key: str, value: str) -> None:
        """Set header with proper UTF-8 encoding."""
        if isinstance(value, bytes):
            try:
                value = value.decode('utf-8')
            except UnicodeDecodeError:
                value = str(value.encode('utf-8', errors='replace'), 'utf-8')
        elif not isinstance(value, str):
            value = str(value)

        try:
            value.encode('utf-8')
            response.headers[key] = value
        except UnicodeEncodeError:
            safe_value = value.encode('utf-8', errors='replace').decode('utf-8')
            response.headers[key] = safe_value

    # Check if this is a color validation error
    for error in exc.errors():
        msg = error.get("msg", "")
        if "Invalid color format" in msg and "#RRGGBB" in msg:
            # Extract field name from message
            field_name = None
            if "for '" in msg:
                start = msg.find("for '") + 5
                end = msg.find("':", start)
                if end > start:
                    field_name = msg[start:end]

            response_content = {
                "error": {
                    "code": "INVALID_COLOR_FORMAT",
                    "message": msg,
                    "details": {
                        "key": field_name,
                        "value": error.get("input", ""),
                        "expected_format": "#RRGGBB",
                    },
                },
                "data": None,
            }
            response = JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content=response_content,
            )
            add_security_headers(response)
            return response

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
        set_header_safely(response, "Access-Control-Allow-Origin", origin)
        set_header_safely(response, "Access-Control-Allow-Credentials", "true")
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

# Add encoding middlewares LAST (so they execute FIRST in the middleware chain)
# In FastAPI, middlewares are executed in reverse order of addition
app.add_middleware(RequestBodyEncodingMiddleware)  # Executes first (normalizes request body)
app.add_middleware(HeaderEncodingMiddleware)      # Executes second (normalizes response headers)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
