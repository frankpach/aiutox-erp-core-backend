from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1 import api_router
from app.core.config_file import get_settings
from app.core.exceptions import APIException

settings = get_settings()

app = FastAPI(
    title="AiutoX ERP API",
    version="0.1.0",
    description="Backend API para AiutoX ERP",
    docs_url="/docs",
    openapi_url="/openapi.json",
)

# CORS configuration
if settings.CORS_ORIGINS:
    origins = [origin.strip() for origin in settings.CORS_ORIGINS.split(",")]
else:
    origins = ["http://localhost:5173", "http://localhost:3000"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(APIException)
async def api_exception_handler(request: Request, exc: APIException) -> JSONResponse:
    """Handle APIException and return standard error format.

    This ensures all APIException instances return the standard error format
    defined in rules/api-contract.md.
    """
    # exc.detail already contains {"error": {...}}, add data: null for API contract compliance
    response_content = exc.detail.copy()
    response_content["data"] = None
    return JSONResponse(
        status_code=exc.status_code,
        content=response_content,
    )


@app.get("/healthz", tags=["system"])
def healthz():
    """Health check endpoint."""
    return {
        "status": "ok",
        "env": settings.ENV,
        "debug": settings.DEBUG,
    }


# Include API routers
app.include_router(api_router, prefix="/api/v1")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
