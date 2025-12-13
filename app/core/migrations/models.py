"""Data models for migration management."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional


@dataclass
class MigrationInfo:
    """Information about a single migration."""

    revision: str
    down_revision: Optional[str]
    file: str
    applied: bool
    applied_date: Optional[datetime] = None
    description: Optional[str] = None


@dataclass
class MigrationStatus:
    """Complete migration status."""

    current_revision: Optional[str]
    applied: List[MigrationInfo] = field(default_factory=list)
    pending: List[MigrationInfo] = field(default_factory=list)
    orphaned: List[str] = field(default_factory=list)


@dataclass
class SchemaDiff:
    """Schema differences between models and database."""

    missing_tables: List[str] = field(default_factory=list)
    extra_tables: List[str] = field(default_factory=list)
    missing_columns: List[tuple[str, str]] = field(default_factory=list)  # (table, column)
    extra_columns: List[tuple[str, str]] = field(default_factory=list)  # (table, column)
    column_type_mismatches: List[tuple[str, str, str, str]] = field(
        default_factory=list
    )  # (table, column, expected, actual)


@dataclass
class VerificationResult:
    """Result of migration verification."""

    applied_match: bool
    schema_match: bool
    integrity_ok: bool
    issues: List[str] = field(default_factory=list)
    schema_diff: Optional[SchemaDiff] = None


@dataclass
class IntegrityResult:
    """Result of integrity verification."""

    valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


@dataclass
class SchemaVerificationResult:
    """Result of schema verification."""

    match: bool
    diff: SchemaDiff
    issues: List[str] = field(default_factory=list)


@dataclass
class MigrationResult:
    """Result of a migration operation."""

    success: bool
    applied_count: int = 0
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    applied_migrations: List[str] = field(default_factory=list)









