"""Script to verify migration files are syntactically correct and well-structured."""

import ast
import re
from pathlib import Path
from typing import List, Tuple


def check_migration_file(file_path: Path) -> Tuple[bool, List[str]]:
    """Check if a migration file is valid."""
    errors = []

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Parse as Python AST
        try:
            tree = ast.parse(content)
        except SyntaxError as e:
            errors.append(f"Syntax error: {e}")
            return False, errors

        # Check for required functions
        has_upgrade = False
        has_downgrade = False
        has_revision = False

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                if node.name == "upgrade":
                    has_upgrade = True
                elif node.name == "downgrade":
                    has_downgrade = True
            elif isinstance(node, ast.AnnAssign):
                # Handle: revision: str = "xxx"
                if isinstance(node.target, ast.Name) and node.target.id == "revision":
                    has_revision = True
            elif isinstance(node, ast.Assign):
                # Handle: revision = "xxx"
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == "revision":
                        has_revision = True

        if not has_revision:
            errors.append("Missing 'revision' variable")
        if not has_upgrade:
            errors.append("Missing 'upgrade()' function")
        if not has_downgrade:
            errors.append("Missing 'downgrade()' function")

        # Check for required imports
        has_alembic_op = False
        has_sqlalchemy = False

        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                if node.module == "alembic" and any(alias.name == "op" for alias in node.names):
                    has_alembic_op = True
                elif node.module and ("sqlalchemy" in node.module or "sa" in [alias.name for alias in node.names]):
                    has_sqlalchemy = True
            elif isinstance(node, ast.Import):
                # Check for: import sqlalchemy as sa
                for alias in node.names:
                    if alias.name == "sqlalchemy" or (alias.asname and "sa" in alias.asname):
                        has_sqlalchemy = True

        if not has_alembic_op:
            errors.append("Missing 'from alembic import op'")
        # Note: sqlalchemy import is optional if using op.execute() with raw SQL
        # Only warn if upgrade/downgrade functions use sa.* without import
        if not has_sqlalchemy:
            # Check if code uses sa. or sqlalchemy. without import
            if re.search(r'\bsa\.|\bsqlalchemy\.', content):
                errors.append("Missing sqlalchemy imports (code uses sa.* or sqlalchemy.*)")

        return len(errors) == 0, errors

    except Exception as e:
        errors.append(f"Error reading file: {e}")
        return False, errors


def check_migration_chain(migrations_dir: Path) -> Tuple[bool, List[str]]:
    """Check that migration chain is valid."""
    errors = []

    # Find all migration files
    migration_files = sorted(migrations_dir.glob("*.py"))

    if not migration_files:
        errors.append("No migration files found")
        return False, errors

    # Extract revision IDs and dependencies
    revisions = {}
    for file_path in migration_files:
        if file_path.name == "__init__.py" or file_path.name == "env.py":
            continue

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            # Extract revision (can be: revision: str = "xxx" or revision = "xxx")
            revision_match = re.search(
                r'revision\s*:\s*[^=]*=\s*["\']([^"\']+)["\']|revision\s*=\s*["\']([^"\']+)["\']',
                content
            )
            if not revision_match:
                errors.append(f"{file_path.name}: Could not find revision ID")
                continue

            revision_id = revision_match.group(1) or revision_match.group(2)

            # Extract down_revision (can be: down_revision: Union[str, None] = "xxx" or down_revision = "xxx" or None)
            down_revision_match = re.search(
                r'down_revision\s*:\s*[^=]*=\s*["\']?([^"\',\s\)]+)["\']?|down_revision\s*=\s*["\']?([^"\',\s\)]+)["\']?',
                content
            )
            down_revision = None
            if down_revision_match:
                down_revision = down_revision_match.group(1) or down_revision_match.group(2)
                if down_revision and down_revision.strip() in ("None", "null"):
                    down_revision = None

            revisions[revision_id] = {
                "file": file_path.name,
                "down_revision": down_revision,
            }
        except Exception as e:
            errors.append(f"{file_path.name}: Error parsing - {e}")

    # Check chain
    if not revisions:
        errors.append("No valid revisions found")
        return False, errors

    # Find root (revision with down_revision = None)
    root_revisions = [
        rev_id for rev_id, info in revisions.items() if info["down_revision"] is None
    ]

    if len(root_revisions) != 1:
        errors.append(f"Expected exactly one root revision, found {len(root_revisions)}")

    # Check that all revisions are connected
    visited = set()
    current = root_revisions[0] if root_revisions else None

    while current:
        if current in visited:
            errors.append(f"Circular dependency detected: {current}")
            break
        visited.add(current)
        # Find next revision
        next_rev = None
        for rev_id, info in revisions.items():
            if info["down_revision"] == current:
                if next_rev:
                    errors.append(f"Multiple revisions depend on {current}")
                    break
                next_rev = rev_id
        current = next_rev

    missing = set(revisions.keys()) - visited
    if missing:
        errors.append(f"Orphaned revisions (not in chain): {missing}")

    return len(errors) == 0, errors


def main():
    """Main verification function."""
    print("=" * 60)
    print("VERIFICACIÓN DE MIGRACIONES")
    print("=" * 60)

    migrations_dir = Path(__file__).parent.parent / "migrations" / "versions"

    if not migrations_dir.exists():
        print(f"❌ Migrations directory not found: {migrations_dir}")
        return 1

    print(f"\n📁 Verificando migraciones en: {migrations_dir}")

    all_valid = True

    # Check individual files
    print("\n" + "-" * 60)
    print("1. Verificando archivos individuales...")
    print("-" * 60)

    migration_files = sorted(migrations_dir.glob("*.py"))
    for file_path in migration_files:
        if file_path.name in ("__init__.py", "env.py"):
            continue

        is_valid, errors = check_migration_file(file_path)
        if is_valid:
            print(f"✅ {file_path.name}")
        else:
            print(f"❌ {file_path.name}")
            for error in errors:
                print(f"   - {error}")
            all_valid = False

    # Check migration chain
    print("\n" + "-" * 60)
    print("2. Verificando cadena de migraciones...")
    print("-" * 60)

    chain_valid, chain_errors = check_migration_chain(migrations_dir)
    if chain_valid:
        print("✅ Cadena de migraciones válida")
    else:
        print("❌ Problemas en la cadena de migraciones:")
        for error in chain_errors:
            print(f"   - {error}")
        all_valid = False

    # Summary
    print("\n" + "=" * 60)
    if all_valid:
        print("✅ TODAS LAS VERIFICACIONES PASARON")
        return 0
    else:
        print("❌ ALGUNAS VERIFICACIONES FALLARON")
        return 1


if __name__ == "__main__":
    exit(main())

