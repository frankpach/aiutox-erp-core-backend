"""Health check endpoints para monitoreo del sistema."""

from datetime import datetime  # noqa: I001
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.db.session import get_db
from app.schemas.common import StandardResponse

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/live")
async def liveness():
    """
    Health check básico - el servicio está vivo.

    Returns:
        Status del servicio
    """
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "aiutox-backend"
    }


@router.get("/ready")
async def readiness(db: Session = Depends(get_db)):
    """
    Health check completo - el servicio está listo para recibir tráfico.

    Verifica:
    - Conexión a base de datos
    - Conexión a Redis
    - Estado del TaskScheduler

    Returns:
        Status detallado de todos los componentes
    """
    checks = {
        "database": "unknown",
        "redis": "unknown",
        "scheduler": "unknown"
    }

    # Check database
    try:
        db.execute("SELECT 1")
        checks["database"] = "healthy"
    except Exception as e:
        checks["database"] = f"unhealthy: {str(e)}"

    # Check Redis
    try:
        from app.core.redis import get_redis_client
        redis_client = get_redis_client()
        await redis_client.ping()
        checks["redis"] = "healthy"
    except Exception as e:
        checks["redis"] = f"unhealthy: {str(e)}"

    # Check TaskScheduler
    try:
        from app.core.tasks.scheduler import get_task_scheduler
        scheduler = await get_task_scheduler()
        checks["scheduler"] = "healthy" if scheduler.scheduler.running else "stopped"
    except Exception as e:
        checks["scheduler"] = f"unhealthy: {str(e)}"

    # Determinar status general
    all_healthy = all(
        status_value == "healthy"
        for status_value in checks.values()
    )


    return StandardResponse(
        data={
            "status": "healthy" if all_healthy else "unhealthy",
            "checks": checks,
            "timestamp": datetime.utcnow().isoformat()
        }
    )


@router.get("/metrics")
async def metrics_summary():
    """
    Resumen de métricas del sistema.

    Returns:
        Métricas básicas del sistema
    """
    try:
        from app.monitoring.task_metrics import get_task_metrics
        metrics = get_task_metrics()

        return {
            "status": "healthy",
            "prometheus_available": metrics.prometheus_available,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }
