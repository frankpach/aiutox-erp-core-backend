"""Script para crear archivo de seguimiento de tests."""

import sys
from datetime import datetime
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).parent.parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))


def create_test_tracking_file() -> Path:
    """
    Crear archivo de seguimiento de tests con timestamp.

    Returns:
        Path al archivo creado
    """
    # Crear directorio si no existe
    analysis_dir = backend_dir / "tests" / "analysis"
    analysis_dir.mkdir(parents=True, exist_ok=True)

    # Generar nombre de archivo con timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"last_test_{timestamp}.md"
    filepath = analysis_dir / filename

    # Leer plantilla del plan si existe
    plan_file = analysis_dir / "PLAN_MEJORADO_TESTS.md"
    if plan_file.exists():
        with open(plan_file, "r", encoding="utf-8") as f:
            plan_content = f.read()
    else:
        plan_content = "# Plan de Tests\n\n[Plan no encontrado - ver PLAN_MEJORADO_TESTS.md]"

    # Crear contenido del archivo de seguimiento
    content = f"""# Seguimiento de Tests - {timestamp}

**Fecha de Inicio:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
**Última Actualización:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
**Estado:** 🔄 Iniciado

---

## 📋 Plan de Ejecución

{plan_content}

---

## 📈 Seguimiento de Progreso por Módulo

### Resumen General

**Estado Inicial:**
- Tests totales: [Se actualizará después de ejecución]
- Tests pasando: [Se actualizará después de ejecución]
- Tests fallando: [Se actualizará después de ejecución]
- Tests saltados: [Se actualizará después de ejecución]

---

## 🐛 Lista de Errores y Correcciones

### Errores Pendientes

[Se actualizará después de cada ejecución]

### Errores Corregidos

[Se actualizará cuando se corrijan]

---

## 📝 Historial de Actualizaciones

### {datetime.now().strftime("%Y-%m-%d %H:%M:%S")} - Inicio
- Archivo de seguimiento creado
- Plan de ejecución inicializado

---

**Próxima acción:** Ejecutar suite completa de tests para obtener estado inicial

"""

    # Escribir archivo
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"✅ Archivo de seguimiento creado: {filepath}")
    return filepath


if __name__ == "__main__":
    create_test_tracking_file()


