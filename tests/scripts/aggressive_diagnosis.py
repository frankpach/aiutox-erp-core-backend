#!/usr/bin/env python3
"""
Diagnóstico agresivo para encontrar el verdadero problema raíz.
"""

import sys
import threading
import time
from pathlib import Path

# Agregar el directorio backend al path
backend_path = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_path))

def test_individual_modules():
    """Prueba cada módulo individualmente para encontrar el culpable exacto."""
    print("🔍 DIAGNÓSTICO AGRESIVO - MÓDULOS INDIVIDUALES")
    print("=" * 60)
    
    # Lista de todos los módulos que podrían causar problemas
    all_modules = [
        # Core modules
        "app.core.config_file",
        "app.core.db.session", 
        "app.core.exceptions",
        "app.core.auth.rate_limit",
        
        # API v1 modules
        "app.api.v1.config",
        "app.api.v1.auth", 
        "app.api.v1.users",
        
        # Module APIs
        "app.modules.calendar.api",
        "app.modules.crm.api",
        "app.modules.inventory.api", 
        "app.modules.products.api",
        "app.modules.tasks.api",
        
        # Feature modules
        "app.features.tasks.statuses",
    ]
    
    problem_modules = []
    
    for module in all_modules:
        print(f"\n📦 Probando: {module}")
        print("-" * 40)
        
        def import_module():
            try:
                if module == "app.core.config_file":
                    from app.core.config_file import get_settings
                elif module == "app.core.db.session":
                    from app.core.db.session import SessionLocal
                elif module == "app.core.exceptions":
                    from app.core.exceptions import APIException
                elif module == "app.core.auth.rate_limit":
                    from app.core.auth.rate_limit import limiter
                elif module == "app.api.v1.config":
                    import app.api.v1.config
                elif module == "app.api.v1.auth":
                    import app.api.v1.auth
                elif module == "app.api.v1.users":
                    import app.api.v1.users
                elif module == "app.modules.calendar.api":
                    from app.modules.calendar.api import router
                elif module == "app.modules.crm.api":
                    from app.modules.crm.api import router
                elif module == "app.modules.inventory.api":
                    from app.modules.inventory.api import router
                elif module == "app.modules.products.api":
                    from app.modules.products.api import router
                elif module == "app.modules.tasks.api":
                    from app.modules.tasks.api import router
                elif module == "app.features.tasks.statuses":
                    from app.features.tasks.statuses import router
                
                return True, None
            except Exception as e:
                return False, str(e)
        
        result = [None]
        exception = [None]
        
        def import_thread():
            try:
                success, exc = import_module()
                result[0] = success
                exception[0] = exc
            except Exception as e:
                result[0] = False
                exception[0] = str(e)
        
        thread = threading.Thread(target=import_thread)
        thread.daemon = True
        thread.start()
        thread.join(timeout=2)
        
        if thread.is_alive():
            print("   ⏰ TIMEOUT - MÓDULO PROBLEMÁTICO")
            problem_modules.append(module)
        elif result[0]:
            print("   ✅ OK")
        else:
            print(f"   ❌ ERROR: {exception[0]}")
            problem_modules.append(module)
    
    return problem_modules

def analyze_problem_modules(problem_modules):
    """Analiza los módulos problemáticos en detalle."""
    print(f"\n🔍 ANÁLISIS DETALLADO DE MÓDULOS PROBLEMÁTICOS")
    print("=" * 60)
    print(f"Módulos con problemas: {len(problem_modules)}")
    
    for module in problem_modules:
        print(f"\n📦 Analizando: {module}")
        print("-" * 40)
        
        # Convertir module name a file path
        if module.startswith("app.core"):
            parts = module.split(".")
            file_path = backend_path / "app" / parts[1] / parts[2] / f"{parts[3]}.py"
        elif module.startswith("app.api.v1"):
            parts = module.split(".")
            file_path = backend_path / "app" / "api" / "v1" / f"{parts[3]}.py"
        elif module.startswith("app.modules"):
            parts = module.split(".")
            file_path = backend_path / "app" / "modules" / parts[2] / "api.py"
        elif module.startswith("app.features"):
            parts = module.split(".")
            file_path = backend_path / "app" / "features" / parts[1] / parts[2] / f"{parts[3]}.py"
        else:
            print(f"   ❌ No se pudo determinar la ruta para {module}")
            continue
        
        print(f"   📄 Ruta: {file_path}")
        
        if file_path.exists():
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Analizar imports
                lines = content.split('\n')
                imports = []
                for line in lines:
                    if line.strip().startswith('from ') or line.strip().startswith('import '):
                        imports.append(line.strip())
                
                print(f"   📦 Imports encontrados: {len(imports)}")
                for imp in imports[:5]:  # Primeros 5 imports
                    print(f"      {imp}")
                if len(imports) > 5:
                    print(f"      ... y {len(imports) - 5} más")
                
                # Buscar imports de app que puedan causar ciclos
                app_imports = [imp for imp in imports if 'app.' in imp]
                if app_imports:
                    print(f"   ⚠️ Imports de app (posibles ciclos): {len(app_imports)}")
                    for imp in app_imports[:3]:
                        print(f"      → {imp}")
                
            except Exception as e:
                print(f"   ❌ Error leyendo archivo: {e}")
        else:
            print(f"   ❌ Archivo no existe")

def create_emergency_server():
    """Crea un servidor de emergencia que no importa nada problemático."""
    print(f"\n🚨 CREANDO SERVIDOR DE EMERGENCIA")
    print("=" * 60)
    
    emergency_server_content = '''"""
Servidor de emergencia - mínimo y funcional.
"""

from fastapi import FastAPI

# Crear aplicación FastAPI mínima
app = FastAPI(
    title="AiutoX ERP - Emergency Server",
    version="0.1.0-emergency",
    description="Servidor de emergencia sin imports problemáticos"
)

@app.get("/")
def root():
    return {"message": "Emergency server running"}

@app.get("/healthz")
def healthz():
    return {"status": "ok", "mode": "emergency"}

@app.get("/test")
def test():
    return {"message": "Test endpoint working"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
'''
    
    emergency_path = backend_path / "app" / "emergency_server.py"
    
    try:
        with open(emergency_path, 'w', encoding='utf-8') as f:
            f.write(emergency_server_content)
        
        print(f"✅ Servidor de emergencia creado en: {emergency_path}")
        return True
        
    except Exception as e:
        print(f"❌ Error creando servidor de emergencia: {e}")
        return False

def main():
    """Función principal."""
    print("🔍 DIAGNÓSTICO AGRESIVO - ENCONTRANDO EL VERDADERO PROBLEMA")
    print("=" * 70)
    
    # Paso 1: Probar módulos individuales
    problem_modules = test_individual_modules()
    
    # Paso 2: Analizar módulos problemáticos
    if problem_modules:
        analyze_problem_modules(problem_modules)
    
    # Paso 3: Crear servidor de emergencia
    create_emergency_server()
    
    print(f"\n📊 DIAGNÓSTICO FINAL")
    print("=" * 60)
    
    if problem_modules:
        print(f"❌ Se encontraron {len(problem_modules)} módulos problemáticos:")
        for module in problem_modules:
            print(f"   - {module}")
        
        print(f"\n💡 SOLUCIÓN INMEDIATA:")
        print(f"1. Usa el servidor de emergencia:")
        print(f"   uvicorn app.emergency_server:app --reload")
        print(f"2. Esto te dará un servidor funcional mientras reparas los módulos")
        print(f"3. Repara los módulos problemáticos uno por uno")
    else:
        print("✅ No se encontraron módulos problemáticos")
        print("💡 El problema puede estar en otro lugar - revisa el startup de FastAPI")

if __name__ == "__main__":
    main()
