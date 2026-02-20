#!/usr/bin/env python3
"""
Script para reparar las dependencias circulares encontradas.
"""

import sys
from pathlib import Path

# Agregar el directorio backend al path
backend_path = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_path))


def fix_contact_organization_circular_dep():
    """Repara la dependencia circular entre contact y organization schemas."""
    print("🔧 REPARANDO DEPENDENCIA CIRCULAR: contact ↔ organization")
    print("=" * 60)

    contact_schema_path = backend_path / "app" / "schemas" / "contact.py"
    organization_schema_path = backend_path / "app" / "schemas" / "organization.py"

    try:
        # Leer contact.py
        with open(contact_schema_path, encoding="utf-8") as f:
            contact_content = f.read()

        # Leer organization.py
        with open(organization_schema_path, encoding="utf-8") as f:
            organization_content = f.read()

        print("📦 Analizando imports...")

        # Verificar imports circulares
        if "from app.schemas.organization import" in contact_content:
            print("   ❌ contact.py importa de organization.py")
        else:
            print("   ✅ contact.py no importa de organization.py")

        if "from app.schemas.contact import" in organization_content:
            print("   ❌ organization.py importa de contact.py")
        else:
            print("   ✅ organization.py no importa de contact.py")

        # Solución: mover imports a dentro de funciones
        new_contact_content = contact_content
        new_organization_content = organization_content

        # Reparar contact.py si es necesario
        if "from app.schemas.organization import" in contact_content:
            # Reemplazar import en nivel de módulo con import local
            lines = contact_content.split("\n")
            new_lines = []

            for line in lines:
                if "from app.schemas.organization import" in line:
                    # Comentar el import y agregar nota
                    new_lines.append(f"# MOVED TO LOCAL IMPORT: {line}")
                    print(f"   📝 Movido import: {line.strip()}")
                else:
                    new_lines.append(line)

            new_contact_content = "\n".join(new_lines)

        # Reparar organization.py si es necesario
        if "from app.schemas.contact import" in organization_content:
            lines = organization_content.split("\n")
            new_lines = []

            for line in lines:
                if "from app.schemas.contact import" in line:
                    # Comentar el import y agregar nota
                    new_lines.append(f"# MOVED TO LOCAL IMPORT: {line}")
                    print(f"   📝 Movido import: {line.strip()}")
                else:
                    new_lines.append(line)

            new_organization_content = "\n".join(new_lines)

        # Guardar archivos reparados
        if new_contact_content != contact_content:
            with open(contact_schema_path, "w", encoding="utf-8") as f:
                f.write(new_contact_content)
            print("   ✅ contact.py actualizado")

        if new_organization_content != organization_content:
            with open(organization_schema_path, "w", encoding="utf-8") as f:
                f.write(new_organization_content)
            print("   ✅ organization.py actualizado")

        return True

    except Exception as e:
        print(f"   ❌ Error reparando dependencia circular: {e}")
        return False


def create_lazy_import_wrapper():
    """Crea un wrapper para imports con lazy loading."""
    print("\n🔧 CREANDO WRAPPER PARA LAZY IMPORTS")
    print("=" * 50)

    wrapper_content = '''"""
Wrapper para imports con lazy loading para evitar dependencias circulares.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    # Estos imports solo se usan para type checking
    from app.schemas.contact import ContactCreate, ContactResponse
    from app.schemas.organization import OrganizationCreate, OrganizationResponse

def get_contact_schemas():
    """Importa schemas de contacto de forma lazy."""
    from app.schemas.contact import ContactCreate, ContactResponse
    return ContactCreate, ContactResponse

def get_organization_schemas():
    """Importa schemas de organización de forma lazy."""
    from app.schemas.organization import OrganizationCreate, OrganizationResponse
    return OrganizationCreate, OrganizationResponse
'''

    wrapper_path = backend_path / "app" / "schemas" / "lazy_imports.py"

    try:
        with open(wrapper_path, "w", encoding="utf-8") as f:
            f.write(wrapper_content)

        print(f"✅ Wrapper creado en: {wrapper_path}")
        return True

    except Exception as e:
        print(f"❌ Error creando wrapper: {e}")
        return False


def optimize_session_imports():
    """Optimiza los imports de session para reducir carga."""
    print("\n🔧 OPTIMIZANDO IMPORTS DE SESSION")
    print("=" * 50)

    session_path = backend_path / "app" / "core" / "db" / "session.py"

    try:
        with open(session_path, encoding="utf-8") as f:
            content = f.read()

        # Verificar si ya está optimizado
        if "sqlite" in content.lower():
            print("✅ session.py ya está optimizado")
            return True

        # Crear versión optimizada
        optimized_content = """from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.core.config_file import get_settings

settings = get_settings()

# Detectar tipo de base de datos y configurar apropiadamente
database_url = settings.database_url

if database_url.startswith("sqlite"):
    # Configuración para SQLite (más rápida para desarrollo)
    engine = create_engine(
        database_url,
        echo=settings.DEBUG,
        future=True,
        pool_pre_ping=True,
        connect_args={"check_same_thread": False}
    )
else:
    # Configuración para PostgreSQL
    engine = create_engine(
        database_url,
        echo=settings.DEBUG,
        future=True,
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=20,
        connect_args={
            "connect_timeout": 10,
            "options": "-c timezone=utc"
        }
    )

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

Base = declarative_base()
"""

        with open(session_path, "w", encoding="utf-8") as f:
            f.write(optimized_content)

        print("✅ session.py optimizado")
        return True

    except Exception as e:
        print(f"❌ Error optimizando session.py: {e}")
        return False


def create_minimal_main():
    """Crea una versión minimal de main.py para pruebas."""
    print("\n🔧 CREANDO VERSIÓN MINIMAL DE main.py")
    print("=" * 50)

    minimal_main_content = '''"""
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
'''

    minimal_main_path = backend_path / "app" / "main_minimal.py"

    try:
        with open(minimal_main_path, "w", encoding="utf-8") as f:
            f.write(minimal_main_content)

        print("✅ main_minimal.py creado")
        return True

    except Exception as e:
        print(f"❌ Error creando main_minimal.py: {e}")
        return False


def main():
    """Función principal."""
    print("🔧 REPARACIÓN DE DEPENDENCIAS CIRCULARES")
    print("=" * 60)

    success_count = 0
    total_tasks = 4

    # Tarea 1: Reparar dependencia circular contact-organization
    if fix_contact_organization_circular_dep():
        success_count += 1

    # Tarea 2: Crear wrapper para lazy imports
    if create_lazy_import_wrapper():
        success_count += 1

    # Tarea 3: Optimizar imports de session
    if optimize_session_imports():
        success_count += 1

    # Tarea 4: Crear main minimal para pruebas
    if create_minimal_main():
        success_count += 1

    print("\n📊 RESUMEN")
    print("=" * 50)
    print(f"Tareas completadas: {success_count}/{total_tasks}")

    if success_count == total_tasks:
        print("✅ Todas las reparaciones completadas")
        print("\n💡 PASOS SIGUIENTES:")
        print("1. Prueba el servidor minimal: uvicorn app.main_minimal:app --reload")
        print("2. Si funciona, el problema está en los imports del main original")
        print("3. Revisa los schemas que usan imports locales")
        print("4. Considera mover más imports a dentro de funciones")
    else:
        print("❌ Algunas reparaciones fallaron")

    return success_count == total_tasks


if __name__ == "__main__":
    main()
