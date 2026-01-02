"""Files module for file and document management."""

# Import tasks to register them
from app.core.files import tasks  # noqa: F401

from app.core.files.service import FileService
from app.core.files.storage import (
    BaseStorageBackend,
    HybridStorageBackend,
    LocalStorageBackend,
    S3StorageBackend,
)

__all__ = [
    "FileService",
    "BaseStorageBackend",
    "LocalStorageBackend",
    "S3StorageBackend",
    "HybridStorageBackend",
]

