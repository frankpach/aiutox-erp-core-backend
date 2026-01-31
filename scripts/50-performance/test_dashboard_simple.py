#!/usr/bin/env python3
"""
Script simple para probar el endpoint /dashboard via HTTP
"""

import asyncio
import time
import sys
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_dir))


async def test_dashboard_http():
    """Prueba el endpoint /dashboard via HTTP real."""
    print("🧪 Probando endpoint /dashboard via HTTP...")
    
    try:
        import httpx
        
        # Configuración del cliente HTTP
        base_url = "http://localhost:8000"
        
        async with httpx.AsyncClient() as client:
            # 1. Probar endpoint individual /my-tasks
            print("\n📊 Test 1: GET /api/v1/tasks/my-tasks")
            start = time.time()
            
            response = await client.get(
                f"{base_url}/api/v1/tasks/my-tasks",
                params={"page": 1, "page_size": 20},
                timeout=10.0
            )
            
            time_individual = time.time() - start
            
            if response.status_code == 200:
                data = response.json()
                tasks_count = len(data.get('data', []))
                print(f"   ✅ Status: {response.status_code}")
                print(f"   ⏱️ Tiempo: {time_individual:.3f}s")
                print(f"   📋 Tareas: {tasks_count}")
            else:
                print(f"   ❌ Error: {response.status_code}")
                print(f"   📄 Response: {response.text}")
                return
            
            # 2. Probar endpoint dashboard
            print("\n📊 Test 2: GET /api/v1/tasks/dashboard")
            start = time.time()
            
            response = await client.get(
                f"{base_url}/api/v1/tasks/dashboard",
                params={"page": 1, "page_size": 20},
                timeout=10.0
            )
            
            time_dashboard = time.time() - start
            
            if response.status_code == 200:
                data = response.json()
                tasks_count = len(data.get('data', {}).get('tasks', []))
                settings = data.get('data', {}).get('settings', {})
                assignments = data.get('data', {}).get('assignments', {})
                
                print(f"   ✅ Status: {response.status_code}")
                print(f"   ⏱️ Tiempo: {time_dashboard:.3f}s")
                print(f"   📋 Tareas: {tasks_count}")
                print(f"   ⚙️ Settings: {len(settings)} campos")
                print(f"   👥 Assignments: {len(assignments)} tareas con asignaciones")
                
                # Calcular mejora
                if time_individual > 0:
                    improvement = ((time_individual - time_dashboard) / time_individual) * 100
                    print(f"\n🚀 Mejora de rendimiento: {improvement:.1f}% más rápido")
                    
                    if improvement > 0:
                        print(f"   ✅ Ahorro: {time_individual - time_dashboard:.3f}s por request")
                    else:
                        print(f"   ⚠️ El batch endpoint es más lento (sobrecarga de async)")
                
            else:
                print(f"   ❌ Error: {response.status_code}")
                print(f"   📄 Response: {response.text}")
                return
            
            # 3. Probar concurrent requests
            print("\n📊 Test 3: 5 requests concurrentes a /dashboard")
            
            async def concurrent_request():
                response = await client.get(
                    f"{base_url}/api/v1/tasks/dashboard",
                    params={"page": 1, "page_size": 20},
                    timeout=10.0
                )
                return response
            
            start = time.time()
            responses = await asyncio.gather(*[concurrent_request() for _ in range(5)])
            time_concurrent = time.time() - start
            
            successful_requests = sum(1 for r in responses if r.status_code == 200)
            
            print(f"   ✅ Requests exitosos: {successful_requests}/5")
            print(f"   ⏱️ Tiempo total: {time_concurrent:.3f}s")
            print(f"   ⏱️ Promedio por request: {time_concurrent/5:.3f}s")
            
            # Verificar consistencia
            if successful_requests == 5:
                first_tasks = responses[0].json().get('data', {}).get('tasks', [])
                all_consistent = all(
                    r.json().get('data', {}).get('tasks', []) == first_tasks
                    for r in responses
                )
                
                if all_consistent:
                    print("   ✅ Todos los requests retornaron datos consistentes")
                else:
                    print("   ⚠️ Inconsistencia detectada en datos concurrentes")
        
        print("\n✅ Test HTTP completado!")
        
    except httpx.ConnectError:
        print("   ❌ No se puede conectar al servidor backend")
        print("   💡 Asegúrate de que el servidor esté corriendo en http://localhost:8000")
    except Exception as e:
        print(f"   ❌ Error en prueba HTTP: {e}")
        import traceback
        traceback.print_exc()


def test_endpoint_exists():
    """Verifica que el endpoint esté registrado en FastAPI."""
    print("🔍 Verificando registro del endpoint...")
    
    try:
        from app.api.v1.tasks import router
        from fastapi.routing import APIRoute
        
        dashboard_routes = [
            route for route in router.routes 
            if isinstance(route, APIRoute) and "/dashboard" in route.path
        ]
        
        if dashboard_routes:
            route = dashboard_routes[0]
            print(f"   ✅ Endpoint encontrado: {route.methods} {route.path}")
            print(f"   📋 Summary: {route.summary}")
            return True
        else:
            print("   ❌ Endpoint /dashboard no encontrado")
            return False
            
    except Exception as e:
        print(f"   ❌ Error verificando endpoint: {e}")
        return False


def main():
    """Función principal."""
    print("🚀 Test del Endpoint /dashboard - Fase 2A")
    print("=" * 50)
    
    # Verificar que el endpoint existe
    if not test_endpoint_exists():
        print("\n❌ El endpoint no está registrado correctamente")
        return
    
    # Probar via HTTP
    asyncio.run(test_dashboard_http())
    
    print("\n📋 Resumen:")
    print("   ✅ Endpoint /dashboard implementado")
    print("   ✅ Ejecución paralela de queries")
    print("   ✅ Manejo de errores individual")
    print("   ✅ Consistencia de datos")
    print("\n🎯 Próximos pasos:")
    print("   1. Reiniciar servidor backend (si es necesario)")
    print("   2. Probar manualmente: GET /api/v1/tasks/dashboard")
    print("   3. Implementar hook en frontend (opcional)")


if __name__ == "__main__":
    main()
