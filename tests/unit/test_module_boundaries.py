"""Architecture guardrails for business modules."""

import ast
from pathlib import Path


def test_modules_do_not_import_each_other_directly():
    modules_dir = Path(__file__).resolve().parents[2] / "app" / "modules"
    assert modules_dir.exists()

    errors: list[str] = []

    for module_dir in modules_dir.iterdir():
        if not module_dir.is_dir() or module_dir.name.startswith("_"):
            continue

        module_name = module_dir.name

        for py_file in module_dir.rglob("*.py"):
            if py_file.name.startswith("__"):
                continue

            try:
                tree = ast.parse(
                    py_file.read_text(encoding="utf-8"), filename=str(py_file)
                )
            except SyntaxError as e:
                errors.append(f"SyntaxError parsing {py_file}: {e}")
                continue

            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom) and node.module:
                    if not node.module.startswith("app.modules."):
                        continue

                    parts = node.module.split(".")
                    if len(parts) < 3:
                        continue

                    imported_module_name = parts[2]

                    if imported_module_name != module_name:
                        errors.append(
                            f"{py_file}: forbidden import from '{node.module}' (module '{module_name}' must not import other business modules)"
                        )

    assert not errors, "\n".join(errors)
