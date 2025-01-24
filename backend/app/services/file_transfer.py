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
        self.tmp_dir = Path(settings.TMP_EXPORT_LOCATION)
        self.tmp_dir.mkdir(parents=True, exist_ok=True)
        self.max_retries = 3
        self.retry_delay = 2  # seconds
        logger.info(f"Initialized FileTransferService with tmp dir: {self.tmp_dir}")

    async def transfer_file(self, local_path: str, remote_path: str, user_id: str) -> bool:
        """Transfer a file from temporary storage to user's export location via SCP with retries."""
        for attempt in range(self.max_retries):
            try:
                # Prepare connection options
                conn_options = {
                    'host': settings.SCP_HOST,
                    'port': settings.SCP_PORT,
                    'username': settings.SCP_USER,
                }
                
                if settings.SCP_KEY_FILE:
                    conn_options['client_keys'] = [settings.SCP_KEY_FILE]
                elif settings.SCP_PASSWORD:
                    conn_options['password'] = settings.SCP_PASSWORD
                
                logger.info(f"Starting file transfer for user {user_id} (attempt {attempt + 1}/{self.max_retries}): {local_path} -> {remote_path}")
                
                async with asyncssh.connect(**conn_options) as conn:
                    # Create remote directory if it doesn't exist
                    try:
                        await asyncio.shield(
                            conn.run(f'mkdir -p "{os.path.dirname(remote_path)}"')
                        )
                    except Exception as e:
                        logger.warning(f"Error creating remote directory: {str(e)}")
                        # Continue anyway as directory might already exist
                    
                    # Get file size for progress tracking
                    file_size = os.path.getsize(local_path)
                    progress = Progress(file_size)
                    
                    # Start transfer with progress callback
                    await asyncio.shield(
                        asyncssh.scp(local_path, (conn, remote_path), 
                                   progress_handler=progress.update)
                    )
                    
                    # Verify file was transferred
                    try:
                        result = await conn.run(f'stat "{remote_path}"')
                        if result.exit_status == 0:
                            logger.info(f"Successfully transferred file for user {user_id}")
                            return True
                    except Exception as e:
                        logger.error(f"Error verifying file transfer: {str(e)}")
                        raise  # Re-raise to trigger retry
                
            except Exception as e:
                if attempt < self.max_retries - 1:
                    delay = self.retry_delay * (attempt + 1)  # Exponential backoff
                    logger.warning(
                        f"Transfer attempt {attempt + 1} failed for user {user_id}: {str(e)}. "
                        f"Retrying in {delay} seconds..."
                    )
                    await asyncio.sleep(delay)
                else:
                    logger.error(
                        f"All transfer attempts failed for user {user_id}: {str(e)}", 
                        exc_info=True
                    )
                    return False
        
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
        return str(self.tmp_dir / filename)

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