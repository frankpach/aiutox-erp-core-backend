"""Script para actualizar archivo de seguimiento de tests después de ejecución."""

import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

# Add backend to path
backend_dir = Path(__file__).parent.parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))


def find_latest_tracking_file() -> Optional[Path]:
    """Encontrar el archivo de seguimiento más reciente."""
    analysis_dir = backend_dir / "tests" / "analysis"
    if not analysis_dir.exists():
        return None

    tracking_files = list(analysis_dir.glob("last_test_*.md"))
    if not tracking_files:
        return None

    # Ordenar por fecha de modificación (más reciente primero)
    tracking_files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return tracking_files[0]


def parse_pytest_output(output: str) -> dict:
    """
    Parsear salida de pytest para extraer estadísticas.

    Args:
        output: Salida del comando pytest

    Returns:
        Diccionario con estadísticas
    """
    stats = {
        "total": 0,
        "passed": 0,
        "failed": 0,
        "skipped": 0,
        "errors": 0,
        "duration": 0.0,
    }

    # Buscar línea de resumen (ej: "10 passed, 2 failed, 1 skipped in 5.23s")
    summary_pattern = r"(\d+)\s+passed|(\d+)\s+failed|(\d+)\s+skipped|(\d+)\s+error"
    duration_pattern = r"in\s+([\d.]+)s"

    for line in output.split("\n"):
        # Buscar passed
        if match := re.search(r"(\d+)\s+passed", line):
            stats["passed"] = int(match.group(1))
        # Buscar failed
        if match := re.search(r"(\d+)\s+failed", line):
            stats["failed"] = int(match.group(1))
        # Buscar skipped
        if match := re.search(r"(\d+)\s+skipped", line):
            stats["skipped"] = int(match.group(1))
        # Buscar errors
        if match := re.search(r"(\d+)\s+error", line):
            stats["errors"] = int(match.group(1))
        # Buscar duración
        if match := re.search(duration_pattern, line):
            stats["duration"] = float(match.group(1))

    stats["total"] = stats["passed"] + stats["failed"] + stats["skipped"] + stats["errors"]
    return stats


def update_tracking_file(
    module_name: str,
    test_file: str,
    pytest_output: str,
    status: str = "✅ Completado",
    errors: Optional[list[str]] = None,
    actions: Optional[list[str]] = None,
) -> Path:
    """
    Actualizar archivo de seguimiento con resultados de test.

    Args:
        module_name: Nombre del módulo
        test_file: Ruta del archivo de test
        pytest_output: Salida completa de pytest
        status: Estado del módulo
        errors: Lista de errores encontrados
        actions: Lista de acciones realizadas

    Returns:
        Path al archivo actualizado
    """
    tracking_file = find_latest_tracking_file()
    if not tracking_file:
        print("❌ No se encontró archivo de seguimiento. Crear uno primero.")
        return None

    # Parsear estadísticas
    stats = parse_pytest_output(pytest_output)

    # Leer contenido actual
    with open(tracking_file, "r", encoding="utf-8") as f:
        content = f.read()

    # Preparar nueva sección
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    errors_list = errors or []
    actions_list = actions or [f"Ejecutado test del módulo {module_name}"]

    # Crear sección de actualización
    update_section = f"""
## Actualización: {timestamp}

### Módulo: {module_name} - {status}

**Archivo de test:** `{test_file}`
**Última ejecución:** {timestamp}

**Resultado:**
- Tests totales: {stats['total']}
- Tests pasando: {stats['passed']} ✅
- Tests fallando: {stats['failed']} ❌
- Tests saltados: {stats['skipped']} ⏭️
- Errores: {stats['errors']} ⚠️
- Tiempo de ejecución: {stats['duration']:.2f}s

**Salida completa:**
```
{pytest_output[:2000]}...
```

**Errores encontrados:**
"""
    for i, error in enumerate(errors_list, 1):
        update_section += f"{i}. {error} - Estado: ⏳ Pendiente\n"

    update_section += "\n**Acciones realizadas:**\n"
    for action in actions_list:
        update_section += f"- {timestamp} - {action}\n"

    # Agregar al historial
    if "## 📝 Historial de Actualizaciones" in content:
        # Insertar después del título del historial
        content = content.replace(
            "## 📝 Historial de Actualizaciones",
            f"## 📝 Historial de Actualizaciones\n{update_section}",
        )
    else:
        # Agregar al final
        content += f"\n{update_section}\n"

    # Actualizar resumen general si existe
    if "### Resumen General" in content:
        # Actualizar estadísticas generales (simplificado)
        pass

    # Actualizar última actualización
    content = re.sub(
        r"\*\*Última actualización:\*\*.*",
        f"**Última actualización:** {timestamp}",
        content,
    )

    # Escribir archivo actualizado
    with open(tracking_file, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"✅ Archivo de seguimiento actualizado: {tracking_file}")
    return tracking_file


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Actualizar archivo de seguimiento de tests")
    parser.add_argument("--module", required=True, help="Nombre del módulo")
    parser.add_argument("--test-file", required=True, help="Ruta del archivo de test")
    parser.add_argument("--output", help="Salida de pytest (o leer de stdin)")
    parser.add_argument("--status", default="✅ Completado", help="Estado del módulo")
    parser.add_argument("--errors", nargs="*", help="Lista de errores encontrados")
    parser.add_argument("--actions", nargs="*", help="Lista de acciones realizadas")

    args = parser.parse_args()

    # Leer salida de pytest
    if args.output:
        pytest_output = args.output
    else:
        pytest_output = sys.stdin.read()

    update_tracking_file(
        module_name=args.module,
        test_file=args.test_file,
        pytest_output=pytest_output,
        status=args.status,
        errors=args.errors,
        actions=args.actions,
    )

