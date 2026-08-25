"""Structured logging for the ad automation system."""

import logging
import json
from pathlib import Path
from datetime import datetime
from typing import Optional, Any


class StructuredLogger:
    """Logger with structured output support."""
    
    def __init__(self, log_dir: Path, name: str = "ad_automation"):
        """
        Initialize logger.
        
        Args:
            log_dir: Directory for log files
            name: Logger name
        """
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.name = name
        
        # Create logger
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.DEBUG)
        
        # Remove existing handlers
        self.logger.handlers.clear()
        
        # File handler
        log_file = self.log_dir / f"{name}.log"
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        # Formatter
        formatter = logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        # Add handlers
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
    
    def info(self, message: str, **kwargs) -> None:
        """Log info message."""
        self._log("INFO", message, **kwargs)
    
    def warning(self, message: str, **kwargs) -> None:
        """Log warning message."""
        self._log("WARNING", message, **kwargs)
    
    def error(self, message: str, **kwargs) -> None:
        """Log error message."""
        self._log("ERROR", message, **kwargs)
    
    def debug(self, message: str, **kwargs) -> None:
        """Log debug message."""
        self._log("DEBUG", message, **kwargs)
    
    def _log(self, level: str, message: str, **kwargs) -> None:
        """
        Internal logging with structured fields.
        
        Args:
            level: Log level (INFO, WARNING, ERROR, DEBUG)
            message: Log message
            **kwargs: Additional structured fields
        """
        # Build log entry
        if kwargs:
            structured = " | ".join(f"{k}={v}" for k, v in kwargs.items())
            log_message = f"{message} | {structured}"
        else:
            log_message = message
        
        # Log at appropriate level
        method = getattr(self.logger, level.lower(), self.logger.info)
        method(log_message)
    
    def log_step(
        self,
        ad_id: str,
        title: str,
        step: str,
        status: str,
        error: Optional[str] = None,
        **kwargs
    ) -> None:
        """
        Log a processing step.
        
        Args:
            ad_id: Advertisement ID
            title: Advertisement title
            step: Processing step name
            status: Step status (in_progress, completed, failed, skipped)
            error: Error message if failed
            **kwargs: Additional fields
        """
        extra_fields = " | ".join(f"{k}={v}" for k, v in kwargs.items())
        
        if error:
            message = f"{ad_id} | {title} | {step} | {status} | ERROR: {error}"
            if extra_fields:
                message += f" | {extra_fields}"
            self.error(message)
        else:
            message = f"{ad_id} | {title} | {step} | {status}"
            if extra_fields:
                message += f" | {extra_fields}"
            self.info(message)
    
    def save_json_log(self, filename: str, data: Any) -> Path:
        """
        Save data as JSON log file.
        
        Args:
            filename: Name of log file (without extension)
            data: Data to save
            
        Returns:
            Path to saved file
        """
        log_file = self.log_dir / f"{filename}.json"
        log_file.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding='utf-8')
        return log_file


def create_logger(log_dir: Optional[Path] = None) -> StructuredLogger:
    """
    Create and return a logger instance.
    
    Args:
        log_dir: Log directory (defaults to ./logs)
        
    Returns:
        StructuredLogger instance
    """
    if log_dir is None:
        log_dir = Path("logs")
    
    return StructuredLogger(log_dir)
