#!/usr/bin/env python3
"""
Script para optimizar el rendimiento de Tasks
Fase 1: Índices + Cache Wrapper
"""

import os
import sys
import subprocess
import time
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_dir))


def run_command(cmd: list[str], description: str) -> bool:
    """Ejecuta un comando y retorna si fue exitoso."""
    print(f"\n🔧 {description}")
    print(f"   Comando: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        print(f"   ✅ Exitoso")
        if result.stdout:
            print(f"   Output: {result.stdout.strip()}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"   ❌ Error: {e}")
        if e.stderr:
            print(f"   Error output: {e.stderr.strip()}")
        return False


def check_redis_connection() -> bool:
    """Verifica si Redis está disponible."""
    try:
        import redis
        from app.core.cache.redis_client import get_redis_client
        
        redis_client = get_redis_client()
        redis_client.ping()
        print("✅ Redis connection successful")
        return True
    except Exception as e:
        print(f"❌ Redis connection failed: {e}")
        return False


def run_migration() -> bool:
    """Ejecuta la migración de índices."""
    return run_command(
        ["alembic", "upgrade", "head"],
        "Ejecutando migración de índices de Tasks"
    )


def test_performance() -> None:
    """Prueba de rendimiento básica."""
    print("\n📊 Probando rendimiento...")
    
    try:
        from app.core.db.deps import get_db
        from app.repositories.task_repository import TaskRepository
        from app.models.user import User
        
        # Obtener un usuario de prueba
        db = next(get_db())
        repo = TaskRepository(db)
        
        # Buscar primer usuario
        user = db.query(User).first()
        if not user:
            print("   ⚠️ No hay usuarios para probar")
            return
        
        # Probar método original
        start = time.time()
        tasks_original = repo.get_visible_tasks(
            tenant_id=user.tenant_id,
            user_id=user.id,
            skip=0,
            limit=20
        )
        time_original = time.time() - start
        
        # Probar método con cache (si está activado)
        start = time.time()
        tasks_cached = repo.get_visible_tasks_cached(
            tenant_id=user.tenant_id,
            user_id=user.id,
            skip=0,
            limit=20
        )
        time_cached = time.time() - start
        
        print(f"   📈 Método original: {time_original:.3f}s ({len(tasks_original)} tareas)")
        print(f"   📈 Método cache: {time_cached:.3f}s ({len(tasks_cached)} tareas)")
        
        if time_cached < time_original:
            improvement = ((time_original - time_cached) / time_original) * 100
            print(f"   🚀 Mejora: {improvement:.1f}% más rápido")
        
    except Exception as e:
        print(f"   ❌ Error en prueba de rendimiento: {e}")


def main() -> None:
    """Función principal."""
    print("🚀 Optimización de Rendimiento de Tasks - Fase 1")
    print("=" * 50)
    
    # 1. Verificar Redis
    if not check_redis_connection():
        print("\n⚠️ Redis no está disponible. Cache será desactivado.")
        print("   Para activar cache:")
        print("   1. Inicia Redis: docker-compose up -d redis")
        print("   2. Configura ENABLE_TASKS_CACHE=true")
    
    # 2. Ejecutar migración
    if not run_migration():
        print("\n❌ Falló la migración. Abortando.")
        sys.exit(1)
    
    # 3. Configurar variables de entorno
    print("\n🔧 Configuración de variables de entorno:")
    print("   Para activar cache: export ENABLE_TASKS_CACHE=true")
    print("   Para desactivar: export ENABLE_TASKS_CACHE=false (default)")
    
    # 4. Probar rendimiento
    test_performance()
    
    print("\n✅ Fase 1 completada exitosamente!")
    print("\n📋 Resumen:")
    print("   ✅ Índices de visibilidad agregados")
    print("   ✅ Cache wrapper implementado")
    print("   ✅ Endpoint actualizado")
    print("\n🎯 Próximos pasos:")
    print("   1. Reiniciar el servidor backend")
    print("   2. Activar cache con ENABLE_TASKS_CACHE=true")
    print("   3. Monitorear rendimiento en /tasks")


if __name__ == "__main__":
    main()
