"""Data models for migration management."""

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class MigrationInfo:
    """Information about a single migration."""

    revision: str
    down_revision: str | None
    file: str
    applied: bool
    applied_date: datetime | None = None
    description: str | None = None


@dataclass
class MigrationStatus:
    """Complete migration status."""

    current_revision: str | None
    applied: list[MigrationInfo] = field(default_factory=list)
    pending: list[MigrationInfo] = field(default_factory=list)
    orphaned: list[str] = field(default_factory=list)


@dataclass
class SchemaDiff:
    """Schema differences between models and database."""

    missing_tables: list[str] = field(default_factory=list)
    extra_tables: list[str] = field(default_factory=list)
    missing_columns: list[tuple[str, str]] = field(default_factory=list)  # (table, column)
    extra_columns: list[tuple[str, str]] = field(default_factory=list)  # (table, column)
    column_type_mismatches: list[tuple[str, str, str, str]] = field(
        default_factory=list
    )  # (table, column, expected, actual)


@dataclass
class VerificationResult:
    """Result of migration verification."""

    applied_match: bool
    schema_match: bool
    integrity_ok: bool
    issues: list[str] = field(default_factory=list)
    schema_diff: SchemaDiff | None = None


@dataclass
class IntegrityResult:
    """Result of integrity verification."""

    valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


@dataclass
class SchemaVerificationResult:
    """Result of schema verification."""

    match: bool
    diff: SchemaDiff
    issues: list[str] = field(default_factory=list)


@dataclass
class MigrationResult:
    """Result of a migration operation."""

    success: bool
    applied_count: int = 0
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    applied_migrations: list[str] = field(default_factory=list)
















