"""
Router lazy minimal con solo endpoints esenciales.
"""

from typing import TYPE_CHECKING

from fastapi import APIRouter

if TYPE_CHECKING:
    pass

# Cache para el router
_api_router = None


def get_api_router() -> APIRouter:
    """Obtiene el API router con lazy loading."""
    global _api_router

    if _api_router is not None:
        return _api_router

    print("🔄 Creando API router minimal (lazy loading)...")

    # Importar solo los módulos esenciales que funcionan
    try:
        # Importar módulos básicos que no causan problemas
        from app.api.v1 import auth, config, users

        # Crear el router
        _api_router = APIRouter()

        # Incluir solo los routers esenciales
        _api_router.include_router(config.router, prefix="/config", tags=["config"])
        _api_router.include_router(users.router, prefix="/users", tags=["users"])
        _api_router.include_router(auth.router, prefix="/auth", tags=["auth"])

        print("✅ API router minimal creado exitosamente")
        return _api_router

    except Exception as e:
        print(f"❌ Error creando router minimal: {e}")

        # Crear un router vacío si hay errores
        _api_router = APIRouter()

        @_api_router.get("/status")
        def router_status():
            return {"status": "minimal_router", "message": "Router minimal funcionando"}

        return _api_router


# Para compatibilidad
api_router = get_api_router()
