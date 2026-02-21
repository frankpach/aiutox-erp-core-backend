"""Code generation utilities."""

import sys
from pathlib import Path

from jinja2 import Environment, FileSystemLoader
from rich.console import Console

# Add backend to path
backend_dir = Path(__file__).parent.parent.parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

console = Console()

# Template directory
TEMPLATES_DIR = Path(__file__).parent / "templates"


def _get_template_env() -> Environment:
    """Get Jinja2 template environment.

    Returns:
        Jinja2 Environment configured for templates
    """
    return Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        trim_blocks=True,
        lstrip_blocks=True,
    )


def _to_snake_case(name: str) -> str:
    """Convert PascalCase or camelCase to snake_case.

    Args:
        name: Name in PascalCase or camelCase

    Returns:
        Name in snake_case
    """
    import re

    # Insert underscore before uppercase letters (except first)
    s1 = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", name)
    # Insert underscore before uppercase letters that follow lowercase
    s2 = re.sub("([a-z0-9])([A-Z])", r"\1_\2", s1)
    return s2.lower()


def _to_pascal_case(name: str) -> str:
    """Convert snake_case to PascalCase.

    Args:
        name: Name in snake_case

    Returns:
        Name in PascalCase
    """
    return "".join(word.capitalize() for word in name.split("_"))


def _normalize_name(name: str) -> str:
    """Normalize entity name (remove common suffixes, convert to PascalCase).

    Args:
        name: Entity name (e.g., "User", "user", "user_model")

    Returns:
        Normalized name in PascalCase
    """
    # Remove common suffixes
    for suffix in ["_model", "_service", "_repository", "_router", "_schema"]:
        if name.lower().endswith(suffix):
            name = name[: -len(suffix)]

    # Convert to PascalCase
    if "_" in name:
        return _to_pascal_case(name)
    elif name[0].islower():
        return name.capitalize()
    return name


def generate_model(name: str, output_dir: Path | None = None) -> Path:
    """Generate SQLAlchemy model file.

    Args:
        name: Model name (e.g., "User", "Product")
        output_dir: Output directory (default: app/models/)

    Returns:
        Path to generated file

    Raises:
        FileExistsError: If file already exists
    """
    normalized_name = _normalize_name(name)
    env = _get_template_env()
    template = env.get_template("model.py.j2")

    if output_dir is None:
        output_dir = backend_dir / "app" / "models"

    output_file = output_dir / f"{_to_snake_case(normalized_name)}.py"

    if output_file.exists():
        raise FileExistsError(f"Model file already exists: {output_file}")

    content = template.render(name=normalized_name)
    output_file.write_text(content, encoding="utf-8")

    console.print(f"[green]Ô£ô Generated model: {output_file}[/green]")
    return output_file


def generate_service(name: str, output_dir: Path | None = None) -> Path:
    """Generate service file.

    Args:
        name: Service name (e.g., "User", "Product")
        output_dir: Output directory (default: app/services/)

    Returns:
        Path to generated file

    Raises:
        FileExistsError: If file already exists
    """
    normalized_name = _normalize_name(name)
    env = _get_template_env()
    template = env.get_template("service.py.j2")

    if output_dir is None:
        output_dir = backend_dir / "app" / "services"

    output_file = output_dir / f"{_to_snake_case(normalized_name)}_service.py"

    if output_file.exists():
        raise FileExistsError(f"Service file already exists: {output_file}")

    content = template.render(name=normalized_name)
    output_file.write_text(content, encoding="utf-8")

    console.print(f"[green]Ô£ô Generated service: {output_file}[/green]")
    return output_file


def generate_repository(name: str, output_dir: Path | None = None) -> Path:
    """Generate repository file.

    Args:
        name: Repository name (e.g., "User", "Product")
        output_dir: Output directory (default: app/repositories/)

    Returns:
        Path to generated file

    Raises:
        FileExistsError: If file already exists
    """
    normalized_name = _normalize_name(name)
    env = _get_template_env()
    template = env.get_template("repository.py.j2")

    if output_dir is None:
        output_dir = backend_dir / "app" / "repositories"

    output_file = output_dir / f"{_to_snake_case(normalized_name)}_repository.py"

    if output_file.exists():
        raise FileExistsError(f"Repository file already exists: {output_file}")

    content = template.render(name=normalized_name)
    output_file.write_text(content, encoding="utf-8")

    console.print(f"[green]Ô£ô Generated repository: {output_file}[/green]")
    return output_file


def generate_router(name: str, output_dir: Path | None = None) -> Path:
    """Generate FastAPI router file.

    Args:
        name: Router name (e.g., "User", "Product")
        output_dir: Output directory (default: app/api/v1/)

    Returns:
        Path to generated file

    Raises:
        FileExistsError: If file already exists
    """
    normalized_name = _normalize_name(name)
    env = _get_template_env()
    template = env.get_template("router.py.j2")

    if output_dir is None:
        output_dir = backend_dir / "app" / "api" / "v1"

    output_file = output_dir / f"{_to_snake_case(normalized_name)}.py"

    if output_file.exists():
        raise FileExistsError(f"Router file already exists: {output_file}")

    content = template.render(name=normalized_name)
    output_file.write_text(content, encoding="utf-8")

    console.print(f"[green]Ô£ô Generated router: {output_file}[/green]")
    return output_file


def generate_schema(name: str, output_dir: Path | None = None) -> Path:
    """Generate Pydantic schema file.

    Args:
        name: Schema name (e.g., "User", "Product")
        output_dir: Output directory (default: app/schemas/)

    Returns:
        Path to generated file

    Raises:
        FileExistsError: If file already exists
    """
    normalized_name = _normalize_name(name)
    env = _get_template_env()
    template = env.get_template("schema.py.j2")

    if output_dir is None:
        output_dir = backend_dir / "app" / "schemas"

    output_file = output_dir / f"{_to_snake_case(normalized_name)}.py"

    if output_file.exists():
        raise FileExistsError(f"Schema file already exists: {output_file}")

    content = template.render(name=normalized_name)
    output_file.write_text(content, encoding="utf-8")

    console.print(f"[green]Ô£ô Generated schema: {output_file}[/green]")
    return output_file


def generate_module(name: str, entities: list[str] = None) -> dict[str, Path]:
    """Generate complete module with all components.

    Args:
        name: Module name (e.g., "Product", "Order")
        entities: List of entity names (default: [name])

    Returns:
        Dictionary mapping component type to generated file path

    Raises:
        FileExistsError: If any file already exists
    """
    if entities is None:
        entities = [name]

    generated_files = {}

    for entity_name in entities:
        normalized_entity = _normalize_name(entity_name)

        # Generate all components
        try:
            generated_files[f"{normalized_entity}_model"] = generate_model(
                normalized_entity
            )
            generated_files[f"{normalized_entity}_schema"] = generate_schema(
                normalized_entity
            )
            generated_files[f"{normalized_entity}_repository"] = generate_repository(
                normalized_entity
            )
            generated_files[f"{normalized_entity}_service"] = generate_service(
                normalized_entity
            )
            generated_files[f"{normalized_entity}_router"] = generate_router(
                normalized_entity
            )
        except FileExistsError as e:
            console.print(f"[red]Ô£ù Error: {e}[/red]")
            # Clean up already generated files
            for file_path in generated_files.values():
                if file_path.exists():
                    file_path.unlink()
            raise

    console.print(
        f"\n[green]Ô£ô Generated complete module '{name}' with {len(entities)} entity(ies)[/green]"
    )
    return generated_files


def generate_seeder(name: str, output_dir: Path | None = None) -> Path:
    """Generate seeder file.

    Args:
        name: Seeder name (e.g., "User", "Product", "Database")
        output_dir: Output directory (default: database/seeders/)

    Returns:
        Path to generated file

    Raises:
        FileExistsError: If file already exists
    """
    normalized_name = _normalize_name(name)
    env = _get_template_env()
    template = env.get_template("seeder.py.j2")

    if output_dir is None:
        output_dir = backend_dir / "database" / "seeders"

    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / f"{_to_snake_case(normalized_name)}_seeder.py"

    if output_file.exists():
        raise FileExistsError(f"Seeder file already exists: {output_file}")

    content = template.render(name=normalized_name)
    output_file.write_text(content, encoding="utf-8")

    console.print(f"[green]Ô£ô Generated seeder: {output_file}[/green]")
    return output_file
