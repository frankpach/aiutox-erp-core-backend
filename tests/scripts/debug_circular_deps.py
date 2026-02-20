#!/usr/bin/env python3
"""
Script para detectar dependencias circulares en los imports del backend.
"""

import ast
import importlib
import sys
import threading
from pathlib import Path

# Agregar el directorio backend al path
backend_path = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_path))


class DependencyAnalyzer(ast.NodeVisitor):
    """Analizador AST para encontrar imports."""

    def __init__(self, current_module: str):
        self.current_module = current_module
        self.imports: set[str] = set()

    def visit_Import(self, node):
        for alias in node.names:
            if alias.name.startswith("app."):
                self.imports.add(alias.name)
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        if node.module and node.module.startswith("app."):
            self.imports.add(node.module)
        self.generic_visit(node)


def get_module_imports(module_path: Path, module_name: str) -> set[str]:
    """Extrae imports de un módulo usando AST."""
    try:
        with open(module_path, encoding="utf-8") as f:
            content = f.read()

        tree = ast.parse(content)
        analyzer = DependencyAnalyzer(module_name)
        analyzer.visit(tree)
        return analyzer.imports

    except Exception as e:
        print(f"   ❌ Error analizando {module_path}: {e}")
        return set()


def build_dependency_graph() -> dict[str, set[str]]:
    """Construye el grafo de dependencias de módulos app.*"""
    print("🔍 CONSTRUYENDO GRAFO DE DEPENDENCIAS")
    print("=" * 50)

    dependency_graph: dict[str, set[str]] = {}
    app_dir = backend_path / "app"

    # Encontrar todos los archivos Python
    python_files = []
    for root, dirs, files in os.walk(app_dir):
        for file in files:
            if file.endswith(".py") and not file.startswith("__"):
                rel_path = Path(root).relative_to(app_dir)
                module_name = (
                    f"app.{rel_path.stem}.{file[:-3]}"
                    if rel_path != Path(".")
                    else f"app.{file[:-3]}"
                )
                python_files.append((Path(root) / file, module_name))

    print(f"📦 Analizando {len(python_files)} archivos Python...")

    for file_path, module_name in python_files:
        imports = get_module_imports(file_path, module_name)
        dependency_graph[module_name] = imports
        print(f"   📄 {module_name}: {len(imports)} imports")

    return dependency_graph


def find_circular_dependencies(
    dependency_graph: dict[str, set[str]],
) -> list[list[str]]:
    """Encuentra dependencias circulares usando DFS."""
    print("\n🔍 BUSCANDO DEPENDENCIAS CIRCULARES")
    print("=" * 50)

    def dfs(node: str, path: list[str], visited: set[str]) -> list[list[str]]:
        """Búsqueda en profundidad para detectar ciclos."""
        if node in path:
            # Encontramos un ciclo
            cycle_start = path.index(node)
            cycle = path[cycle_start:] + [node]
            return [cycle]

        if node in visited:
            return []

        visited.add(node)
        path.append(node)

        cycles = []
        for neighbor in dependency_graph.get(node, set()):
            cycles.extend(dfs(neighbor, path.copy(), visited.copy()))

        return cycles

    all_cycles = []
    for node in dependency_graph:
        cycles = dfs(node, [], set())
        all_cycles.extend(cycles)

    # Eliminar ciclos duplicados
    unique_cycles = []
    seen_cycles = set()

    for cycle in all_cycles:
        # Normalizar ciclo (rotar para empezar en el módulo más pequeño)
        min_index = cycle.index(min(cycle))
        normalized = tuple(cycle[min_index:] + cycle[:min_index])

        if normalized not in seen_cycles:
            seen_cycles.add(normalized)
            unique_cycles.append(cycle)

    return unique_cycles


def test_problematic_imports():
    """Prueba imports que podrían causar problemas."""
    print("\n🧪 PROBANDO IMPORTS PROBLEMÁTICOS")
    print("=" * 50)

    # Módulos sospechosos basados en el diagnóstico anterior
    problematic_modules = [
        "app.core.db.session",
        "app.core.auth.rate_limit",
        "app.api.v1.auth",
        "app.api.v1.users",
        "app.features.tasks.statuses",
    ]

    for module in problematic_modules:
        print(f"\n📦 Probando {module}:")

        def import_with_timeout():
            try:
                importlib.import_module(module)
                return True, None
            except Exception as e:
                return False, str(e)

        result = [None]
        exception = [None]

        def import_thread():
            try:
                success, exc = import_with_timeout()
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
            print("   ⏰ TIMEOUT - posible dependencia circular")
        elif result[0]:
            print("   ✅ OK")
        else:
            print(f"   ❌ ERROR: {exception[0]}")


def main():
    """Función principal."""
    print("🔍 ANÁLISIS DE DEPENDENCIAS CIRCULARES")
    print("=" * 60)

    # Paso 1: Construir grafo de dependencias
    dependency_graph = build_dependency_graph()

    # Paso 2: Encontrar ciclos
    cycles = find_circular_dependencies(dependency_graph)

    if cycles:
        print(f"\n⚠️ SE ENCONTRARON {len(cycles)} DEPENDENCIAS CIRCULARES:")
        for i, cycle in enumerate(cycles, 1):
            print(f"\n🔄 Ciclo {i}:")
            for j, module in enumerate(cycle):
                arrow = " → " if j < len(cycle) - 1 else ""
                print(f"   {module}{arrow}")
    else:
        print("\n✅ No se encontraron dependencias circulares")

    # Paso 3: Probar imports problemáticos
    test_problematic_imports()

    # Paso 4: Análisis de módulos que importan session
    print("\n📊 MÓDULOS QUE IMPORTAN app.core.db.session:")
    session_importers = []
    for module, imports in dependency_graph.items():
        if "app.core.db.session" in imports:
            session_importers.append(module)

    for module in session_importers:
        print(f"   📦 {module}")

    print("\n📊 MÓDULOS QUE IMPORTAN app.core.auth.rate_limit:")
    rate_limit_importers = []
    for module, imports in dependency_graph.items():
        if "app.core.auth.rate_limit" in imports:
            rate_limit_importers.append(module)

    for module in rate_limit_importers:
        print(f"   📦 {module}")

    print("\n💡 RECOMENDACIONES:")
    if cycles:
        print("   1. Romper las dependencias circulares encontradas")
        print("   2. Mover imports a dentro de funciones cuando sea posible")
        print("   3. Usar inyección de dependencias en lugar de imports directos")
    else:
        print("   1. El problema puede estar en la inicialización de módulos")
        print("   2. Revisa si hay código de inicialización pesado")
        print("   3. Considera usar lazy loading para módulos pesados")

    return len(cycles) == 0


if __name__ == "__main__":
    import os  # Import aquí para evitar problemas

    main()
