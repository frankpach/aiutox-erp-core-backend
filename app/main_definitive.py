"""
Versión definitiva de main.py con lazy loading para evitar dependencias circulares.
"""

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, Response
from fastapi.staticfiles import StaticFiles

# Configuración básica
logger = logging.getLogger(__name__)

# Variables globales para servicios
async_task_service = None
task_scheduler = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle events."""
    global async_task_service, task_scheduler

    # Startup - solo inicializar lo esencial
    logger.info("Iniciando aplicación...")
    
    # Inicializar servicios de forma lazy
    try:
        # Importar y configurar servicios básicos
        from app.core.config_file import get_settings
        settings = get_settings()
        logger.info(f"Configuración cargada: DEBUG={settings.DEBUG}")
        
        # Inicializar servicios de base de datos si es necesario
        from app.core.db.session import SessionLocal
        db = SessionLocal()
        db.close()
        logger.info("Conexión a base de datos verificada")
        
    except Exception as e:
        logger.error(f"Error en inicialización: {e}", exc_info=True)

    yield

    # Shutdown
    logger.info("Deteniendo aplicación...")

# Crear aplicación FastAPI
app = FastAPI(
    title="AiutoX ERP API",
    version="0.1.0",
    description="Backend API para AiutoX ERP",
    docs_url="/docs",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# Middleware básico
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    """Add basic security headers."""
    response = await call_next(request)
    
    # Headers básicos
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    
    return response

# Exception handlers básicos
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle validation errors."""
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Validation failed",
                "details": exc.errors(),
            },
            "data": None,
        },
    )

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handle all unhandled exceptions."""
    logger.exception(f"Unhandled exception: {exc}")
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "An internal server error occurred",
                "details": None,
            },
            "data": None,
        },
    )

# Health check
@app.get("/healthz", tags=["system"])
def healthz():
    """Health check endpoint."""
    return {
        "status": "ok",
        "message": "Servidor funcionando correctamente"
    }

# Función para cargar rutas de forma lazy
def load_api_routes():
    """Carga las rutas de API de forma lazy."""
    try:
        logger.info("Cargando rutas de API...")
        
        # Importar y configurar el router lazy
        from app.api.v1.lazy_router import get_api_router
        api_router = get_api_router()
        
        # Incluir el router en la aplicación
        app.include_router(api_router, prefix="/api/v1")
        
        logger.info("Rutas de API cargadas exitosamente")
        
    except Exception as e:
        logger.error(f"Error cargando rutas de API: {e}", exc_info=True)

# Montar archivos estáticos si existen
storage_path = os.getenv("STORAGE_BASE_PATH", "./storage")
if os.path.exists(storage_path):
    app.mount("/files", StaticFiles(directory=storage_path), name="files")
    logger.info(f"Archivos estáticos montados desde {storage_path}")

# Cargar rutas al final (después de que la aplicación está completamente configurada)
# Esto se ejecutará cuando FastAPI esté listo para recibir solicitudes
@app.on_event("startup")
async def startup_event():
    """Evento de startup para cargar rutas."""
    load_api_routes()

if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
