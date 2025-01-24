import asyncio
import os
import logging
from pathlib import Path
import asyncssh
from app.core.config import settings
from typing import Optional

logger = logging.getLogger(__name__)
logger.setLevel(getattr(logging, settings.QUERY_LISTENER_LOG_LEVEL))

class FileTransferService:
    def __init__(self):
        # Create tmp directory
        self.tmp_dir = Path(settings.TMP_EXPORT_LOCATION)
        self.ensure_directory(self.tmp_dir)
        self.max_retries = 3
        self.retry_delay = 2  # seconds
        logger.info(f"Initialized FileTransferService with tmp dir: {self.tmp_dir}")

    def ensure_directory(self, path: Path) -> None:
        """Ensure directory exists, create if it doesn't."""
        try:
            path.mkdir(parents=True, exist_ok=True)
            logger.info(f"Ensured directory exists: {path}")
        except Exception as e:
            logger.error(f"Error creating directory {path}: {str(e)}")
            raise

    async def transfer_file(self, local_path: str, remote_path: str, user_id: str) -> bool:
        """Transfer a file from temporary storage to user's export location via SCP with retries."""
        try:
            # Ensure local directory exists
            self.ensure_directory(Path(os.path.dirname(local_path)))
            
            # Ensure remote directory exists
            remote_dir = os.path.dirname(remote_path)
            self.ensure_directory(Path(remote_dir))
            
            logger.info(f"Starting file transfer for user {user_id}: {local_path} -> {remote_path}")
            
            # For development, just copy the file
            try:
                import shutil
                shutil.copy2(local_path, remote_path)
                logger.info(f"Successfully copied file for user {user_id}")
                return True
            except Exception as e:
                logger.error(f"Error copying file: {str(e)}")
                return False
            
        except Exception as e:
            logger.error(f"Error in transfer_file: {str(e)}", exc_info=True)
            return False

    def cleanup_tmp_file(self, file_path: str) -> bool:
        """Remove temporary file after successful transfer."""
        try:
            Path(file_path).unlink()
            logger.info(f"Successfully cleaned up temporary file: {file_path}")
            return True
        except Exception as e:
            logger.error(f"Error cleaning up temporary file {file_path}: {str(e)}", exc_info=True)
            return False

    def get_tmp_path(self, filename: str) -> str:
        """Generate a temporary file path for query results."""
        tmp_path = self.tmp_dir / filename
        self.ensure_directory(tmp_path.parent)
        return str(tmp_path)

class Progress:
    def __init__(self, total_size: int):
        self.total_size = total_size
        self.transferred = 0
        self.last_percentage = 0

    def update(self, transferred: int, _: Optional[int] = None) -> None:
        """Update progress and log if significant change."""
        self.transferred = transferred
        percentage = int((transferred / self.total_size) * 100)
        
        # Log every 10% progress
        if percentage >= self.last_percentage + 10:
            logger.info(f"Transfer progress: {percentage}% ({transferred}/{self.total_size} bytes)")
            self.last_percentage = percentage

# Create singleton instance
file_transfer_service = FileTransferService() 