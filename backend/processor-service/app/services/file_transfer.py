import asyncio
import os
import logging
import shutil
from pathlib import Path
import asyncssh
from app.core.config import settings
from typing import Optional
from app.db.models import UserSettings, Query, QueryStatus  # Import QueryStatus
from datetime import datetime

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

    async def transfer_file(self, local_path: str, remote_path: str, user_id: str, query: Query) -> bool:
        """Transfer a file from temporary storage to user's export location via SCP with retries.
        
        Args:
            local_path: Path to the local file to transfer
            remote_path: Destination path on the remote server
            user_id: ID of the user performing the transfer
            query: Query object containing status and error information
        """
        try:
            # Ensure local directory exists and file is readable
            local_path = os.path.abspath(local_path)
            if not os.path.exists(local_path):
                error_msg = f"Local file not found: {local_path}"
                query.status = QueryStatus.failed.value
                query.error_message = error_msg
                raise FileNotFoundError(error_msg)
            
            # Convert paths to use forward slashes and normalize
            local_path = local_path.replace('\\', '/')
            remote_path = remote_path.replace('\\', '/')
            logger.info(f"Final remote path: {remote_path}")
            # Extract remote directory by splitting the remote path
            remote_dir = os.path.dirname(remote_path)
            logger.info(f"Remote directory path: {remote_dir}")
            retries = 0
            last_error = None
            
            while retries < self.max_retries:
                try:
                    async with await self.get_ssh_connection(query) as ssh:
                        # First, ensure remote directory exists
                        mkdir_cmd = f'mkdir -p "{remote_dir}"'
                        result = await ssh.run(mkdir_cmd)
                        if result.exit_status != 0:
                            raise Exception(f"Failed to create remote directory: {result.stderr}")
                        
                        # Transfer the file using SCP
                        logger.info(f"Starting SCP transfer: {local_path} -> {remote_path}")
                        await asyncssh.scp(local_path, (ssh, remote_path))
                        
                        # Verify the file exists and set permissions
                        verify_cmd = f'ls -l "{remote_path}"'
                        result = await ssh.run(verify_cmd)
                        if result.exit_status == 0:
                            await ssh.run(f'chmod 644 "{remote_path}"')
                            return True
                        else:
                            raise Exception(f"File transfer verification failed: {result.stderr}")
                            
                except Exception as ssh_error:
                    last_error = str(ssh_error)
                    logger.error(f"SSH transfer attempt {retries + 1} failed: {last_error}")
                    if retries + 1 < self.max_retries:
                        retries += 1
                        await asyncio.sleep(self.retry_delay)
                        continue
                    else:
                        # Update query status and error message
                        query.status = QueryStatus.failed.value
                        query.error_message = f"SSH transfer failed after {self.max_retries} attempts: {last_error}"
                        raise Exception(query.error_message)
            
            return False
            
        except Exception as e:
            # Ensure query status is updated on any error
            query.status = QueryStatus.failed.value
            query.error_message = str(e)
            raise
        finally:
            # Always clean up temporary files
            try:
                if os.path.exists(local_path):
                    os.remove(local_path)
                    logger.info(f"Cleaned up temporary file: {local_path}")
                await self.cleanup_tmp_directory()
            except Exception as cleanup_error:
                logger.error(f"Error during cleanup: {str(cleanup_error)}")

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