import os
import shutil
from typing import BinaryIO, Optional
import logging

logger = logging.getLogger("trustscan_storage")

class StorageService:
    async def save(self, file_id: str, file_obj: BinaryIO) -> str:
        raise NotImplementedError

    async def get(self, file_id: str) -> Optional[str]:
        """Returns local path or URL to the file, or None if not found."""
        raise NotImplementedError

    async def delete(self, file_id: str) -> bool:
        raise NotImplementedError

    async def exists(self, file_id: str) -> bool:
        raise NotImplementedError


class LocalStorageService(StorageService):
    def __init__(self, base_dir: str):
        self.base_dir = base_dir
        os.makedirs(self.base_dir, exist_ok=True)

    def _get_path(self, file_id: str) -> str:
        # Prevent path traversal
        safe_id = os.path.basename(file_id)
        return os.path.join(self.base_dir, safe_id)

    async def save(self, file_id: str, file_obj: BinaryIO) -> str:
        file_path = self._get_path(file_id)
        try:
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file_obj, buffer)
            return file_id
        except Exception as e:
            logger.error(f"Failed to save local file {file_id}: {e}")
            raise RuntimeError(f"Storage failure")

    async def get(self, file_id: str) -> Optional[str]:
        file_path = self._get_path(file_id)
        if os.path.exists(file_path):
            return file_path
        return None

    async def delete(self, file_id: str) -> bool:
        file_path = self._get_path(file_id)
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
                return True
            except OSError as e:
                logger.error(f"Failed to delete local file {file_id}: {e}")
                return False
        return False

    async def exists(self, file_id: str) -> bool:
        file_path = self._get_path(file_id)
        return os.path.exists(file_path)


class AzureStorageService(StorageService):
    def __init__(self, connection_string: str, container_name: str):
        self.connection_string = connection_string
        self.container_name = container_name
        # Note: real Azure implementation requires azure-storage-blob dependency.
        # This acts as an interface that would be wired up in production.

    async def save(self, file_id: str, file_obj: BinaryIO) -> str:
        if not self.connection_string:
            raise RuntimeError("Azure Storage is not configured")
        # Pseudo code for Azure
        # blob_client = self.blob_service_client.get_blob_client(container=self.container_name, blob=file_id)
        # blob_client.upload_blob(file_obj)
        return file_id

    async def get(self, file_id: str) -> Optional[str]:
        # Pseudo code for Azure
        # would return a SAS URL or download stream
        return None

    async def delete(self, file_id: str) -> bool:
        # Pseudo code for Azure
        return True

    async def exists(self, file_id: str) -> bool:
        return False


# Singleton provider initialized based on configuration
from app.core.config import settings

def get_storage_service() -> StorageService:
    if settings.STORAGE_PROVIDER == "AZURE":
        return AzureStorageService(
            connection_string=settings.AZURE_STORAGE_CONNECTION_STRING,
            container_name=settings.AZURE_STORAGE_CONTAINER
        )
    else:
        # Default to local secure storage
        # Kept safely out of public asset tree
        storage_path = os.path.join(os.path.dirname(__file__), "..", "..", "storage_secure")
        return LocalStorageService(base_dir=storage_path)
