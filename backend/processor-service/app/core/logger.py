import logging
import sys
from logging.handlers import RotatingFileHandler
import os
from pathlib import Path
from datetime import datetime

class Logger:
    _instance = None
    _initialized = False
    _log_file = None
    _handlers = {}

    def __new__(cls, logger_name: str = None, log_level=logging.INFO):
        if cls._instance is None:
            cls._instance = super(Logger, cls).__new__(cls)
        return cls._instance

    def __init__(self, logger_name: str = None, log_level=logging.INFO):
        if not self._initialized:
            # Create logs directory if it doesn't exist
            self.logs_dir = Path("logs")
            self.logs_dir.mkdir(exist_ok=True)
            
            # Generate timestamp for log file (only once per application start)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            self._log_file = self.logs_dir / f"app_{timestamp}.log"
            
            # Configure root logger
            root_logger = logging.getLogger()
            root_logger.setLevel(log_level)

            # Remove existing handlers if any
            for handler in root_logger.handlers[:]:
                root_logger.removeHandler(handler)

            # Console handler for root logger
            if 'console' not in self._handlers:
                console_handler = logging.StreamHandler(sys.stdout)
                console_handler.setLevel(log_level)
                console_formatter = logging.Formatter(
                    '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s'
                )
                console_handler.setFormatter(console_formatter)
                root_logger.addHandler(console_handler)
                self._handlers['console'] = console_handler

            # File handler for root logger
            if 'file' not in self._handlers:
                file_handler = RotatingFileHandler(
                    self._log_file,
                    maxBytes=10*1024*1024,  # 10MB
                    backupCount=5
                )
                file_handler.setLevel(log_level)
                file_formatter = logging.Formatter(
                    '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s'
                )
                file_handler.setFormatter(file_formatter)
                root_logger.addHandler(file_handler)
                self._handlers['file'] = file_handler

            self._initialized = True

        # Get or create logger for the specific name
        self.logger = logging.getLogger(logger_name or "root")
        self.logger.setLevel(log_level)

    def get_logger(self):
        return self.logger

    @classmethod
    def get_log_file(cls):
        return cls._log_file if cls._instance else None

    def info(self, message: str):
        self.logger.info(message)
    
    def error(self, message: str):
        self.logger.error(message)
    
    def warning(self, message: str):
        self.logger.warning(message)
    
    def debug(self, message: str):
        self.logger.debug(message)
    
    def critical(self, message: str):
        self.logger.critical(message)

# Create a default logger instance
default_logger = Logger("root").get_logger() 