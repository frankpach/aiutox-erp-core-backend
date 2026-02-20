"""
Versión minimal de main.py para identificar el problema.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

# Configuración básica
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle minimal."""
    logger.info("Aplicación iniciada (minimal)")
    yield
    logger.info("Aplicación detenida (minimal)")


app = FastAPI(
    title="AiutoX ERP API (Minimal)",
    version="0.1.0-minimal",
    description="Backend API minimal para pruebas",
    lifespan=lifespan,
)


@app.get("/healthz")
def healthz():
    """Health check."""
    return {"status": "ok", "mode": "minimal"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
