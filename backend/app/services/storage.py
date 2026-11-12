import os
import uuid
import hmac
import hashlib
import time
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from app.core.config import get_settings

settings = get_settings()


class BaseStorageService(ABC):
    @abstractmethod
    def generate_signed_upload_url(
        self, filename: str, content_type: str, expires_in: int = 3600
    ) -> Dict[str, Any]:
        """Generate a signed URL or token for direct video upload."""
        pass

    @abstractmethod
    def save_uploaded_file(self, file_content: bytes, filename: str) -> str:
        """Save file bytes directly to storage."""
        pass

    @abstractmethod
    def get_storage_path(self, relative_path: str) -> str:
        """Return absolute path or URL for a stored file."""
        pass


class LocalStorageService(BaseStorageService):
    def __init__(self, storage_dir: Optional[str] = None):
        self.storage_dir = storage_dir or settings.STORAGE_DIR
        self.uploads_dir = os.path.join(self.storage_dir, "uploads")
        os.makedirs(self.uploads_dir, exist_ok=True)

    def _generate_signature(self, file_id: str, expires_at: int) -> str:
        message = f"{file_id}:{expires_at}".encode("utf-8")
        secret = settings.SECRET_KEY.encode("utf-8")
        return hmac.new(secret, message, hashlib.sha256).hexdigest()

    def verify_token(self, file_id: str, expires_at: int, token: str) -> bool:
        if time.time() > expires_at:
            return False
        expected = self._generate_signature(file_id, expires_at)
        return hmac.compare_digest(expected, token)

    def generate_signed_upload_url(
        self, filename: str, content_type: str, expires_in: int = 3600
    ) -> Dict[str, Any]:
        file_id = f"{uuid.uuid4().hex}_{filename}"
        expires_at = int(time.time()) + expires_in
        signature = self._generate_signature(file_id, expires_at)

        upload_url = f"/api/upload/file?file_id={file_id}&expires={expires_at}&token={signature}"

        return {
            "file_id": file_id,
            "upload_url": upload_url,
            "storage_type": "local",
            "expires_at": expires_at,
            "method": "POST",
            "headers": {
                "Content-Type": content_type
            }
        }

    def save_uploaded_file(self, file_content: bytes, filename: str) -> str:
        safe_filename = f"{uuid.uuid4().hex}_{os.path.basename(filename)}"
        target_path = os.path.join(self.uploads_dir, safe_filename)
        with open(target_path, "wb") as f:
            f.write(file_content)
        return target_path

    def get_storage_path(self, relative_path: str) -> str:
        if os.path.isabs(relative_path):
            return relative_path
        return os.path.join(self.storage_dir, relative_path)


def get_storage_service() -> BaseStorageService:
    # Extensible for S3 / Cloudflare R2
    return LocalStorageService()
