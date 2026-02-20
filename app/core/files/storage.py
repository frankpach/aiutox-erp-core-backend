"""Storage backends for file storage."""

import logging
import os
from abc import ABC, abstractmethod
from pathlib import Path

from app.core.config_file import get_settings

logger = logging.getLogger(__name__)


class BaseStorageBackend(ABC):
    """Abstract base class for storage backends."""

    @abstractmethod
    async def upload(self, file_content: bytes, path: str) -> str:
        """Upload file content to storage.

        Args:
            file_content: File content as bytes
            path: Storage path/key

        Returns:
            Storage path/key where file was saved
        """
        pass

    @abstractmethod
    async def download(self, path: str) -> bytes:
        """Download file content from storage.

        Args:
            path: Storage path/key

        Returns:
            File content as bytes
        """
        pass

    @abstractmethod
    async def delete(self, path: str) -> bool:
        """Delete file from storage.

        Args:
            path: Storage path/key

        Returns:
            True if deleted successfully, False otherwise
        """
        pass

    @abstractmethod
    async def exists(self, path: str) -> bool:
        """Check if file exists in storage.

        Args:
            path: Storage path/key

        Returns:
            True if file exists, False otherwise
        """
        pass

    @abstractmethod
    async def get_url(self, path: str) -> str | None:
        """Get public URL for file.

        Args:
            path: Storage path/key

        Returns:
            Public URL or None if not available
        """
        pass


class LocalStorageBackend(BaseStorageBackend):
    """Local filesystem storage backend."""

    def __init__(self, base_path: str | None = None):
        """Initialize local storage backend.

        Args:
            base_path: Base directory for file storage (default: ./storage)
        """
        self.settings = get_settings()
        if base_path is None:
            base_path = os.getenv("STORAGE_BASE_PATH", "./storage")
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)

    def _get_full_path(self, path: str) -> Path:
        """Get full filesystem path for a storage path."""
        return self.base_path / path

    async def upload(self, file_content: bytes, path: str) -> str:
        """Upload file to local storage."""
        full_path = self._get_full_path(path)
        full_path.parent.mkdir(parents=True, exist_ok=True)

        with open(full_path, "wb") as f:
            f.write(file_content)

        logger.info(f"File uploaded to local storage: {full_path}")
        return path

    async def download(self, path: str) -> bytes:
        """Download file from local storage."""
        full_path = self._get_full_path(path)
        if not full_path.exists():
            raise FileNotFoundError(f"File not found: {path}")

        with open(full_path, "rb") as f:
            return f.read()

    async def delete(self, path: str) -> bool:
        """Delete file from local storage."""
        full_path = self._get_full_path(path)
        if not full_path.exists():
            return False

        try:
            full_path.unlink()
            logger.info(f"File deleted from local storage: {full_path}")
            return True
        except Exception as e:
            logger.error(f"Error deleting file {path}: {e}")
            return False

    async def exists(self, path: str) -> bool:
        """Check if file exists in local storage."""
        full_path = self._get_full_path(path)
        return full_path.exists()

    async def get_url(self, path: str) -> str | None:
        """Get local file URL (relative path)."""
        # For local storage, return relative path
        # In production, this would be served via a static file server
        return f"/files/{path}"


class S3StorageBackend(BaseStorageBackend):
    """AWS S3 storage backend."""

    def __init__(
        self,
        bucket_name: str | None = None,
        aws_access_key_id: str | None = None,
        aws_secret_access_key: str | None = None,
        region: str | None = None,
    ):
        """Initialize S3 storage backend.

        Args:
            bucket_name: S3 bucket name
            aws_access_key_id: AWS access key ID
            aws_secret_access_key: AWS secret access key
            region: AWS region
        """
        self.settings = get_settings()
        self.bucket_name = bucket_name or os.getenv("S3_BUCKET_NAME", "")
        self.aws_access_key_id = aws_access_key_id or os.getenv("AWS_ACCESS_KEY_ID", "")
        self.aws_secret_access_key = aws_secret_access_key or os.getenv(
            "AWS_SECRET_ACCESS_KEY", ""
        )
        self.region = region or os.getenv("AWS_REGION", "us-east-1")

        # boto3 will be imported only if S3 is used
        self._boto3_client = None

    def _get_client(self):
        """Get boto3 S3 client (lazy initialization)."""
        if self._boto3_client is None:
            try:
                import boto3

                self._boto3_client = boto3.client(
                    "s3",
                    aws_access_key_id=self.aws_access_key_id,
                    aws_secret_access_key=self.aws_secret_access_key,
                    region_name=self.region,
                )
            except ImportError:
                raise ImportError(
                    "boto3 is required for S3 storage. Install it with: pip install boto3"
                )
        return self._boto3_client

    async def upload(self, file_content: bytes, path: str) -> str:
        """Upload file to S3."""
        import asyncio

        client = self._get_client()

        def _upload():
            client.put_object(Bucket=self.bucket_name, Key=path, Body=file_content)

        await asyncio.to_thread(_upload)
        logger.info(f"File uploaded to S3: s3://{self.bucket_name}/{path}")
        return path

    async def download(self, path: str) -> bytes:
        """Download file from S3."""
        import asyncio

        client = self._get_client()

        def _download():
            response = client.get_object(Bucket=self.bucket_name, Key=path)
            return response["Body"].read()

        return await asyncio.to_thread(_download)

    async def delete(self, path: str) -> bool:
        """Delete file from S3."""
        import asyncio

        client = self._get_client()

        def _delete():
            try:
                client.delete_object(Bucket=self.bucket_name, Key=path)
                return True
            except Exception as e:
                logger.error(f"Error deleting file from S3 {path}: {e}")
                return False

        result = await asyncio.to_thread(_delete)
        if result:
            logger.info(f"File deleted from S3: s3://{self.bucket_name}/{path}")
        return result

    async def exists(self, path: str) -> bool:
        """Check if file exists in S3."""
        import asyncio

        client = self._get_client()

        def _exists():
            try:
                client.head_object(Bucket=self.bucket_name, Key=path)
                return True
            except client.exceptions.NoSuchKey:
                return False
            except Exception:
                return False

        return await asyncio.to_thread(_exists)

    async def get_url(self, path: str) -> str | None:
        """Get S3 public URL."""
        if not self.bucket_name:
            return None
        return f"https://{self.bucket_name}.s3.{self.region}.amazonaws.com/{path}"


class HybridStorageBackend(BaseStorageBackend):
    """Hybrid storage backend that selects between local and S3 based on configuration."""

    def __init__(self, use_s3: bool = False, **kwargs):
        """Initialize hybrid storage backend.

        Args:
            use_s3: Whether to use S3 (default: False, uses local)
            **kwargs: Additional arguments for storage backends
        """
        if use_s3:
            self.backend = S3StorageBackend(**kwargs)
        else:
            self.backend = LocalStorageBackend(**kwargs)

    async def upload(self, file_content: bytes, path: str) -> str:
        """Upload file using selected backend."""
        return await self.backend.upload(file_content, path)

    async def download(self, path: str) -> bytes:
        """Download file using selected backend."""
        return await self.backend.download(path)

    async def delete(self, path: str) -> bool:
        """Delete file using selected backend."""
        return await self.backend.delete(path)

    async def exists(self, path: str) -> bool:
        """Check if file exists using selected backend."""
        return await self.backend.exists(path)

    async def get_url(self, path: str) -> str | None:
        """Get file URL using selected backend."""
        return await self.backend.get_url(path)
