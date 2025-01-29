import asyncio
import os
import logging
import shutil
from pathlib import Path
import asyncssh
from app.core.config import settings
from typing import Optional, List
from app.db.models import UserSettings, Query, QueryStatus  # Import QueryStatus
from datetime import datetime
import aiofiles
import io
import math
from concurrent.futures import ThreadPoolExecutor

# Configure logger with console handler
logger = logging.getLogger(__name__)
logger.setLevel(getattr(logging, settings.QUERY_LISTENER_LOG_LEVEL))

# Add console handler if not already present
if not logger.handlers:
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

class FileTransferService:
    def __init__(self, user_settings: Optional[UserSettings] = None):
        """Initialize FileTransferService with optional user settings.
        
        Args:
            user_settings: Optional UserSettings object containing user's SSH credentials.
                         If not provided, will use environment settings.
        """
        self.settings = user_settings
        # Create tmp directory
        self.tmp_dir = Path(settings.TMP_EXPORT_LOCATION)
        self.ensure_directory(self.tmp_dir)
        self.max_retries = 3
        self.retry_delay = 2  # seconds
        self.chunk_size = 100 * 1024 * 1024  # 8MB chunks
        self.max_concurrent_chunks = 10
        self.executor = ThreadPoolExecutor(max_workers=4)
        
        # Log initialization details
        if user_settings and user_settings.ssh_username:
            logger.info(f"Initialized FileTransferService with user SSH credentials (username: {user_settings.ssh_username})")
        else:
            logger.info("Initialized FileTransferService with environment SSH credentials")
        logger.info(f"Using tmp directory: {self.tmp_dir}")

    def ensure_directory(self, path: Path) -> None:
        """Ensure directory exists, create if it doesn't."""
        try:
            path.mkdir(parents=True, exist_ok=True)
            logger.info(f"Ensured directory exists: {path}")
        except Exception as e:
            logger.error(f"Error creating directory {path}: {str(e)}")
            raise

    async def get_ssh_connection(self, query: Optional[Query] = None):
        """Create an SSH connection using query settings, user settings, or defaults
        
        Args:
            query: Optional Query object that may contain SSH hostname override
        """
        try:
            # First check if query has SSH hostname specified
            if query and query.ssh_hostname:
                host = query.ssh_hostname
                logger.info(f"Using SSH hostname from query: {host}")
            # Then check if user has their own SSH settings
            elif self.settings and self.settings.ssh_hostname:
                host = self.settings.ssh_hostname
                logger.info(f"Using SSH hostname from user settings: {host}")
            else:
                # Fall back to environment settings
                host = settings.SSH_HOST
                logger.info(f"Using default SSH hostname: {host}")

            # Get remaining connection details from user settings or environment
            if (self.settings and 
                self.settings.ssh_username and 
                (self.settings.ssh_password or self.settings.ssh_key)):
                # Use user's credentials
                port = self.settings.ssh_port or settings.SSH_PORT
                username = self.settings.ssh_username
                password = self.settings.ssh_password if self.settings.ssh_password else None
                ssh_key = self.settings.ssh_key
                key_passphrase = self.settings.ssh_key_passphrase.get_secret_value() if self.settings.ssh_key_passphrase else None
                logger.info("Using user's SSH credentials")
            else:
                # Fall back to environment settings
                port = settings.SSH_PORT
                username = settings.SSH_USERNAME
                password = settings.SSH_PASSWORD
                ssh_key = settings.SSH_KEY
                key_passphrase = settings.SSH_KEY_PASSPHRASE
                logger.info("Using environment SSH credentials")

            # Log connection attempt details (excluding sensitive info)
            logger.info(f"Attempting SSH connection to {host}:{port}")
            logger.info(f"Using username: {username}")
            logger.info(f"Authentication method: {'SSH key' if ssh_key else 'Password'}")

            ssh_options = {
                'host': host,
                'port': port,
                'username': username,
                'known_hosts': None,  # In production, you should validate known hosts
                'keepalive_interval': settings.SSH_KEEPALIVE_INTERVAL,
                'connect_timeout': settings.SSH_TIMEOUT
            }

            if ssh_key:
                # Use SSH key authentication if key is provided
                logger.info("Using SSH key authentication")
                # Create a temporary file for the SSH key
                import tempfile
                with tempfile.NamedTemporaryFile(mode='w', delete=False) as key_file:
                    key_file.write(ssh_key)
                    key_path = key_file.name
                
                try:
                    ssh_options['client_keys'] = [key_path]
                    if key_passphrase:
                        ssh_options['passphrase'] = key_passphrase
                    
                    client = await asyncssh.connect(**ssh_options)
                    logger.info("SSH connection established successfully using key authentication")
                finally:
                    # Clean up the temporary key file
                    try:
                        os.unlink(key_path)
                    except:
                        pass
            else:
                # Use password authentication
                if not password:
                    raise ValueError("No password provided for SSH connection")
                    
                logger.info("Using password authentication")
                ssh_options['password'] = password
                client = await asyncssh.connect(**ssh_options)
                logger.info("SSH connection established successfully using password authentication")

            # Test the connection
            result = await client.run('pwd')
            logger.info(f"Current remote directory: {result.stdout.strip()}")
            
            return client
        except asyncssh.DisconnectError as e:
            logger.error(f"SSH connection failed - disconnected: {str(e)}")
            raise
        except asyncssh.ProcessError as e:
            logger.error(f"SSH process error: {str(e)}")
            raise
        except asyncssh.PermissionDenied as e:
            logger.error(f"SSH permission denied: {str(e)}")
            raise
        except asyncssh.ChannelOpenError as e:
            logger.error(f"SSH channel open failed: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"SSH connection failed: {str(e)}", exc_info=True)
            raise

    async def upload_file(self, local_path: str, remote_path: str, query: Optional[Query] = None):
        """Upload a file to the remote server"""
        try:
            async with await self.get_ssh_connection(query) as conn:
                await asyncssh.scp(local_path, (conn, remote_path))
                logger.info(f"Successfully uploaded {local_path} to {remote_path}")
                return True
        except Exception as e:
            logger.error(f"File upload failed: {str(e)}")
            if query:
                query.status = QueryStatus.failed.value
                query.error_message = f"File upload failed: {str(e)}"
            raise

    async def download_file(self, remote_path: str, local_path: str, query: Optional[Query] = None):
        """Download a file from the remote server"""
        try:
            async with await self.get_ssh_connection(query) as conn:
                await asyncssh.scp((conn, remote_path), local_path)
                logger.info(f"Successfully downloaded {remote_path} to {local_path}")
                return True
        except Exception as e:
            logger.error(f"File download failed: {str(e)}")
            if query:
                query.status = QueryStatus.failed.value
                query.error_message = f"File download failed: {str(e)}"
            raise

    async def list_remote_files(self, remote_path: str = "~/shared", query: Optional[Query] = None):
        """List files in the remote directory"""
        try:
            async with await self.get_ssh_connection(query) as conn:
                result = await conn.run(f'ls -la {remote_path}')
                return result.stdout
        except Exception as e:
            logger.error(f"Failed to list remote files: {str(e)}")
            if query:
                query.status = QueryStatus.failed.value
                query.error_message = f"Failed to list remote files: {str(e)}"
            raise

    async def cleanup_tmp_directory(self):
        """Clean up the temporary exports directory."""
        try:
            if self.tmp_dir.exists():
                shutil.rmtree(str(self.tmp_dir))
                logger.info(f"Successfully cleaned up temporary directory: {self.tmp_dir}")
                # Recreate empty directory
                self.ensure_directory(self.tmp_dir)
        except Exception as e:
            logger.error(f"Error cleaning up temporary directory {self.tmp_dir}: {str(e)}", exc_info=True)
            raise

    async def _transfer_chunk(self, ssh, local_path: str, remote_path: str, 
                            start: int, end: int, compress: bool = True) -> None:
        """Transfer a chunk of the file using specified byte range."""
        try:
            async with aiofiles.open(local_path, 'rb') as f:
                await f.seek(start)
                chunk = await f.read(end - start)
                
                if compress:
                    # Create SFTP client for this connection
                    async with ssh.start_sftp_client() as sftp:
                        # Write directly using SFTP with compression
                        async with sftp.open(f"{remote_path}.{start}", "wb") as remote_file:
                            await remote_file.write(chunk)
                else:
                    # Create a temporary file for the chunk
                    chunk_name = f"{os.path.basename(remote_path)}.part{start}"
                    temp_path = os.path.join(self.tmp_dir, chunk_name)
                    
                    async with aiofiles.open(temp_path, 'wb') as temp_f:
                        await temp_f.write(chunk)
                    
                    # Transfer using SCP
                    await asyncssh.scp(temp_path, (ssh, f"{remote_path}.{start}"))
                    # Clean up temporary chunk file
                    os.unlink(temp_path)
                
                logger.debug(f"Transferred chunk {start}-{end} of {remote_path}")
        except Exception as e:
            logger.error(f"Error transferring chunk {start}-{end}: {str(e)}")
            raise

    async def _assemble_chunks(self, ssh, remote_path: str, chunk_starts: List[int]) -> None:
        """Assemble the chunks on the remote server."""
        try:
            # Sort chunk starts to ensure correct order
            chunk_starts.sort()
            
            # First create empty target file
            await ssh.run(f'touch "{remote_path}"')
            
            # Concatenate all chunks sequentially
            for start in chunk_starts:
                chunk_path = f"{remote_path}.{start}"
                concat_cmd = f'cat "{chunk_path}" >> "{remote_path}"'
                result = await ssh.run(concat_cmd)
                if result.exit_status != 0:
                    raise Exception(f"Failed to concatenate chunk {chunk_path}: {result.stderr}")
            
            # Clean up chunk files one by one to avoid command line length issues
            for start in chunk_starts:
                chunk_path = f"{remote_path}.{start}"
                await ssh.run(f'rm -f "{chunk_path}"')
            
            logger.info(f"Successfully assembled chunks for {remote_path}")
        except Exception as e:
            logger.error(f"Error assembling chunks: {str(e)}")
            raise

    async def transfer_file(self, local_path: str, remote_path: str, user_id: str, query: Query) -> bool:
        """Transfer a file using parallel chunks with compression."""
        try:
            local_path = os.path.abspath(local_path)
            if not os.path.exists(local_path):
                error_msg = f"Local file not found: {local_path}"
                query.status = QueryStatus.failed.value
                query.error_message = error_msg
                raise FileNotFoundError(error_msg)

            file_size = os.path.getsize(local_path)
            num_chunks = math.ceil(file_size / self.chunk_size)
            chunk_starts = [i * self.chunk_size for i in range(num_chunks)]
            
            logger.info(f"Starting parallel transfer of {local_path} ({file_size} bytes) in {num_chunks} chunks")
            
            async with await self.get_ssh_connection(query) as ssh:
                # Ensure remote directory exists and clean up any existing file
                remote_dir = os.path.dirname(remote_path)
                await ssh.run(f'mkdir -p "{remote_dir}"; rm -f "{remote_path}"')
                
                # Transfer chunks in parallel
                tasks = []
                for i in range(0, len(chunk_starts), self.max_concurrent_chunks):
                    chunk_group = chunk_starts[i:i + self.max_concurrent_chunks]
                    group_tasks = []
                    
                    for start in chunk_group:
                        end = min(start + self.chunk_size, file_size)
                        task = self._transfer_chunk(ssh, local_path, remote_path, start, end)
                        group_tasks.append(task)
                    
                    # Wait for current group to complete before starting next group
                    await asyncio.gather(*group_tasks)
                    tasks.extend(group_tasks)
                
                # Assemble chunks on remote server
                await self._assemble_chunks(ssh, remote_path, chunk_starts)
                
                # Verify file size
                result = await ssh.run(f'stat -f %z "{remote_path}" || stat --format="%s" "{remote_path}"')
                if result.exit_status == 0:
                    remote_size = int(result.stdout.strip())
                    if remote_size != file_size:
                        raise Exception(f"File size mismatch: local={file_size}, remote={remote_size}")
                
                logger.info(f"Successfully transferred {local_path} to {remote_path}")
                return True
                
        except Exception as e:
            logger.error(f"File transfer failed: {str(e)}")
            query.status = QueryStatus.failed.value
            query.error_message = f"File transfer failed: {str(e)}"
            raise

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