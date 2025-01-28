import asyncio
import os
import logging
from pathlib import Path
import asyncssh
from app.core.config import settings
from typing import Optional
from app.db.models import UserSettings  # Import from models instead of schemas

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

    async def get_ssh_connection(self):
        """Create an SSH connection using user settings or defaults"""
        try:
            # First check if user has their own SSH credentials
            if (self.settings and 
                self.settings.ssh_username and 
                (self.settings.ssh_password or self.settings.ssh_key)):
                # Use user's credentials
                host = settings.SSH_HOST
                port = settings.SSH_PORT
                username = self.settings.ssh_username
                password = self.settings.ssh_password if self.settings.ssh_password else None
                ssh_key = self.settings.ssh_key
                key_passphrase = self.settings.ssh_key_passphrase.get_secret_value() if self.settings.ssh_key_passphrase else None
                logger.info("Using user's SSH credentials")
            else:
                # Fall back to environment settings
                host = settings.SSH_HOST
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

    async def upload_file(self, local_path: str, remote_path: str):
        """Upload a file to the remote server"""
        try:
            async with await self.get_ssh_connection() as conn:
                await asyncssh.scp(local_path, (conn, remote_path))
                logger.info(f"Successfully uploaded {local_path} to {remote_path}")
                return True
        except Exception as e:
            logger.error(f"File upload failed: {str(e)}")
            raise

    async def download_file(self, remote_path: str, local_path: str):
        """Download a file from the remote server"""
        try:
            async with await self.get_ssh_connection() as conn:
                await asyncssh.scp((conn, remote_path), local_path)
                logger.info(f"Successfully downloaded {remote_path} to {local_path}")
                return True
        except Exception as e:
            logger.error(f"File download failed: {str(e)}")
            raise

    async def list_remote_files(self, remote_path: str = "~/shared"):
        """List files in the remote directory"""
        try:
            async with await self.get_ssh_connection() as conn:
                result = await conn.run(f'ls -la {remote_path}')
                return result.stdout
        except Exception as e:
            logger.error(f"Failed to list remote files: {str(e)}")
            raise

    async def transfer_file(self, local_path: str, remote_path: str, user_id: str) -> bool:
        """Transfer a file from temporary storage to user's export location via SCP with retries."""
        retries = 0
        while retries < self.max_retries:
            try:
                # Ensure local directory exists and file is readable
                local_path = os.path.abspath(local_path)
                if not os.path.exists(local_path):
                    raise FileNotFoundError(f"Local file not found: {local_path}")
                
                # Convert paths to use forward slashes and normalize
                local_path = local_path.replace('\\', '/')
                remote_path = remote_path.replace('\\', '/')
                
                # Get remote directory path from user settings or fall back to default
                logger.info(f"Current settings type: {type(self.settings)}")
                logger.info(f"Settings content: {self.settings}")
                
                if self.settings and self.settings.export_location:
                    remote_dir = self.settings.export_location.strip().replace('\\', '/').rstrip('/')
                    logger.info(f"Using export location from user settings: {remote_dir}")
                else:
                    logger.info("Falling back to default export location because:")
                    if not self.settings:
                        logger.info("- settings is None")
                    elif not self.settings.export_location:
                        logger.info("- export_location is empty or None")
                    remote_dir = settings.DEFAULT_EXPORT_LOCATION.strip().replace('\\', '/').rstrip('/')
                    logger.info(f"Using default export location: {remote_dir}")
                
                # Clean up the filename and ensure it uses forward slashes
                filename = os.path.basename(remote_path).replace('\\', '/')
                
                # Construct the final remote path using clean components
                remote_path = f"{remote_dir}/{filename}"
                logger.info(f"Final remote path: {remote_path}")
                
                # Try SSH transfer
                try:
                    async with await self.get_ssh_connection() as ssh:
                        # First, ensure remote directory exists
                        mkdir_cmd = f'mkdir -p "{remote_dir}"'
                        logger.info(f"Creating remote directory with command: {mkdir_cmd}")
                        result = await ssh.run(mkdir_cmd)
                        if result.exit_status != 0:
                            logger.error(f"Failed to create remote directory: {result.stderr}")
                            raise Exception(f"Failed to create remote directory: {result.stderr}")
                        
                        # List the directory contents before transfer
                        logger.info(f"Listing remote directory contents before transfer")
                        result = await ssh.run(f'ls -la "{remote_dir}"')
                        logger.info(f"Remote directory contents before transfer:\n{result.stdout}")
                        
                        # Transfer the file using SCP
                        logger.info(f"Starting SCP transfer: {local_path} -> {remote_path}")
                        try:
                            await asyncssh.scp(local_path, (ssh, remote_path))
                            logger.info("SCP transfer completed")
                        except Exception as scp_error:
                            logger.error(f"SCP transfer failed: {str(scp_error)}")
                            raise
                        
                        # Verify the file exists and has correct permissions
                        verify_cmd = f'ls -l "{remote_path}"'
                        logger.info(f"Verifying file with command: {verify_cmd}")
                        result = await ssh.run(verify_cmd)
                        if result.exit_status == 0:
                            logger.info(f"File transfer verified. File details: {result.stdout}")
                            # Set appropriate permissions
                            chmod_cmd = f'chmod 644 "{remote_path}"'
                            logger.info(f"Setting file permissions with command: {chmod_cmd}")
                            await ssh.run(chmod_cmd)
                            return True
                        else:
                            logger.error(f"File transfer verification failed: {result.stderr}")
                            raise Exception(f"File transfer verification failed: {result.stderr}")
                            
                except Exception as ssh_error:
                    logger.error(f"SSH transfer failed: {str(ssh_error)}", exc_info=True)
                    if retries + 1 < self.max_retries:
                        logger.warning(f"Retrying transfer... ({retries + 1}/{self.max_retries})")
                        retries += 1
                        await asyncio.sleep(self.retry_delay)
                        continue
                    else:
                        # Don't fall back to local copy for permission errors
                        if "Permission denied" in str(ssh_error):
                            logger.error("Permission denied error - not falling back to local copy")
                            raise ssh_error
                        
                        # Fall back to local copy for development
                        logger.warning("All SSH transfer attempts failed, falling back to local copy")
                        import shutil
                        remote_dir = os.path.dirname(remote_path)
                        try:
                            os.makedirs(remote_dir, exist_ok=True)
                            shutil.copy2(local_path, remote_path)
                            logger.info(f"Successfully copied file locally")
                            return True
                        except Exception as copy_error:
                            logger.error(f"Local copy failed: {str(copy_error)}")
                            raise Exception(f"Transfer failed and local copy failed: {str(copy_error)}")
                
            except Exception as e:
                logger.error(f"Transfer attempt {retries + 1} failed: {str(e)}", exc_info=True)
                if retries + 1 < self.max_retries:
                    retries += 1
                    await asyncio.sleep(self.retry_delay)
                else:
                    logger.error("All transfer attempts failed")
                    raise Exception(f"All transfer attempts failed: {str(e)}")
        
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