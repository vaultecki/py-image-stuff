# Copyright [2025] [ecki]
# SPDX-License-Identifier: Apache-2.0

# -*- coding: utf-8 -*-
"""
Shared Logging Utility
Provides consistent logging across all image processing tools.
"""
import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler
from datetime import datetime


class ColoredFormatter(logging.Formatter):
    """Custom formatter with colors for console output"""

    # ANSI color codes
    COLORS = {
        'DEBUG': '\033[36m',  # Cyan
        'INFO': '\033[32m',  # Green
        'WARNING': '\033[33m',  # Yellow
        'ERROR': '\033[31m',  # Red
        'CRITICAL': '\033[35m',  # Magenta
        'RESET': '\033[0m'  # Reset
    }

    def format(self, record):
        """Format log record with colors"""
        # Add color to level name
        if sys.stdout.isatty():  # Only use colors if outputting to terminal
            levelname = record.levelname
            if levelname in self.COLORS:
                record.levelname = f"{self.COLORS[levelname]}{levelname}{self.COLORS['RESET']}"

        return super().format(record)


class ToolLogger:
    """
    Centralized logging utility for image processing tools.

    Features:
    - File and console logging
    - Log rotation (max 10MB per file, 5 backups)
    - Colored console output
    - Contextual information (timestamp, module, function)
    - Exception logging with traceback
    """

    def __init__(self, tool_name, log_dir="config/logs", log_level=logging.INFO,
                 log_to_file=True, log_to_console=True, max_bytes=10 * 1024 * 1024,
                 backup_count=5):
        """
        Initialize logger for a specific tool.

        Args:
            tool_name: Name of the tool (used for log file name)
            log_dir: Directory for log files
            log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            log_to_file: Enable file logging
            log_to_console: Enable console logging
            max_bytes: Maximum size of log file before rotation (default: 10MB)
            backup_count: Number of backup files to keep (default: 5)
        """
        self.tool_name = tool_name
        self.log_dir = Path(log_dir)
        self.log_level = log_level

        # Create log directory if it doesn't exist
        self.log_dir.mkdir(parents=True, exist_ok=True)

        # Create logger
        self.logger = logging.getLogger(tool_name)
        self.logger.setLevel(log_level)

        # Remove existing handlers to avoid duplicates
        self.logger.handlers.clear()

        # Create formatters
        detailed_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(module)s:%(funcName)s:%(lineno)d - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

        simple_formatter = ColoredFormatter(
            '%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%H:%M:%S'
        )

        # File handler with rotation
        if log_to_file:
            log_file = self.log_dir / f"{tool_name}.log"
            file_handler = RotatingFileHandler(
                log_file,
                maxBytes=max_bytes,
                backupCount=backup_count,
                encoding='utf-8'
            )
            file_handler.setLevel(log_level)
            file_handler.setFormatter(detailed_formatter)
            self.logger.addHandler(file_handler)

        # Console handler with colors
        if log_to_console:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(log_level)
            console_handler.setFormatter(simple_formatter)
            self.logger.addHandler(console_handler)

        # Log initialization
        self.logger.info(f"Logger initialized for {tool_name}")
        self.logger.debug(f"Log directory: {self.log_dir.absolute()}")
        self.logger.debug(f"Log level: {logging.getLevelName(log_level)}")

    def debug(self, message, **kwargs):
        """Log debug message"""
        self.logger.debug(message, **kwargs)

    def info(self, message, **kwargs):
        """Log info message"""
        self.logger.info(message, **kwargs)

    def warning(self, message, **kwargs):
        """Log warning message"""
        self.logger.warning(message, **kwargs)

    def error(self, message, exc_info=False, **kwargs):
        """
        Log error message

        Args:
            message: Error message
            exc_info: Include exception traceback
        """
        self.logger.error(message, exc_info=exc_info, **kwargs)

    def critical(self, message, exc_info=False, **kwargs):
        """
        Log critical message

        Args:
            message: Critical message
            exc_info: Include exception traceback
        """
        self.logger.critical(message, exc_info=exc_info, **kwargs)

    def exception(self, message, **kwargs):
        """
        Log exception with full traceback.
        Should be called from exception handler.
        """
        self.logger.exception(message, **kwargs)

    def log_operation_start(self, operation_name, **params):
        """
        Log the start of an operation with parameters.

        Args:
            operation_name: Name of the operation
            **params: Operation parameters
        """
        param_str = ", ".join(f"{k}={v}" for k, v in params.items())
        self.info(f"Starting operation: {operation_name}({param_str})")

    def log_operation_end(self, operation_name, success=True, duration=None, **results):
        """
        Log the end of an operation with results.

        Args:
            operation_name: Name of the operation
            success: Whether operation succeeded
            duration: Duration in seconds
            **results: Operation results
        """
        status = "SUCCESS" if success else "FAILED"
        result_str = ", ".join(f"{k}={v}" for k, v in results.items())

        if duration:
            msg = f"Operation {operation_name} {status} in {duration:.2f}s"
        else:
            msg = f"Operation {operation_name} {status}"

        if result_str:
            msg += f" - {result_str}"

        if success:
            self.info(msg)
        else:
            self.error(msg)

    def log_file_operation(self, operation, filepath, success=True, error=None):
        """
        Log file operations (read, write, delete).

        Args:
            operation: Type of operation (read, write, delete)
            filepath: Path to file
            success: Whether operation succeeded
            error: Error message if failed
        """
        if success:
            self.info(f"File {operation}: {filepath}")
        else:
            self.error(f"File {operation} failed: {filepath} - {error}")

    def log_user_action(self, action, details=None):
        """
        Log user actions for UX analysis.

        Args:
            action: User action (e.g., "button_click", "file_load")
            details: Additional details
        """
        if details:
            self.debug(f"User action: {action} - {details}")
        else:
            self.debug(f"User action: {action}")

    def log_performance_metric(self, metric_name, value, unit=None):
        """
        Log performance metrics.

        Args:
            metric_name: Name of metric
            value: Metric value
            unit: Unit of measurement
        """
        if unit:
            self.debug(f"Performance metric: {metric_name} = {value} {unit}")
        else:
            self.debug(f"Performance metric: {metric_name} = {value}")

    def create_session_log(self):
        """Create a session-specific log entry"""
        session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.info(f"=== New Session Started: {session_id} ===")
        return session_id

    def end_session_log(self, session_id=None):
        """End session log"""
        if session_id:
            self.info(f"=== Session Ended: {session_id} ===")
        else:
            self.info("=== Session Ended ===")


def get_logger(tool_name, **kwargs):
    """
    Convenience function to get a configured logger.

    Args:
        tool_name: Name of the tool
        **kwargs: Additional arguments for ToolLogger

    Returns:
        ToolLogger instance
    """
    return ToolLogger(tool_name, **kwargs)


# Exception decorator for automatic error logging
def log_exceptions(logger):
    """
    Decorator to automatically log exceptions.

    Usage:
        @log_exceptions(logger)
        def my_function():
            # function code
    """

    def decorator(func):
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger.exception(f"Exception in {func.__name__}: {str(e)}")
                raise

        return wrapper

    return decorator


# Context manager for operation logging
class LoggedOperation:
    """
    Context manager for logging operations with timing.

    Usage:
        with LoggedOperation(logger, "image_processing", image_path=path):
            # operation code
    """

    def __init__(self, logger, operation_name, **params):
        self.logger = logger
        self.operation_name = operation_name
        self.params = params
        self.start_time = None
        self.success = False

    def __enter__(self):
        """Start operation logging"""
        self.start_time = datetime.now()
        self.logger.log_operation_start(self.operation_name, **self.params)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """End operation logging"""
        duration = (datetime.now() - self.start_time).total_seconds()

        if exc_type is None:
            self.success = True
            self.logger.log_operation_end(
                self.operation_name,
                success=True,
                duration=duration
            )
        else:
            self.logger.log_operation_end(
                self.operation_name,
                success=False,
                duration=duration,
                error=str(exc_val)
            )
            self.logger.exception(f"Exception in {self.operation_name}")

        # Don't suppress exception
        return False


# Example usage
if __name__ == "__main__":
    # Create logger
    logger = get_logger("test_tool", log_level=logging.DEBUG)

    # Test different log levels
    logger.debug("This is a debug message")
    logger.info("This is an info message")
    logger.warning("This is a warning message")
    logger.error("This is an error message")
    logger.critical("This is a critical message")

    # Test operation logging
    logger.log_operation_start("test_operation", param1="value1", param2=42)
    logger.log_operation_end("test_operation", success=True, duration=1.5, result="success")

    # Test file operation logging
    logger.log_file_operation("read", "/path/to/file.txt", success=True)
    logger.log_file_operation("write", "/path/to/output.txt", success=False, error="Permission denied")

    # Test user action logging
    logger.log_user_action("button_click", "save_button")

    # Test performance metric logging
    logger.log_performance_metric("processing_time", 2.5, "seconds")

    # Test context manager
    with LoggedOperation(logger, "complex_operation", input_file="test.png"):
        # Simulate some work
        import time

        time.sleep(0.1)

    # Test exception logging
    try:
        raise ValueError("Test exception")
    except Exception:
        logger.exception("Caught an exception")

    print(f"\nLogs written to: {logger.log_dir.absolute()}")
