"""
Logging infrastructure for FreqTrade web interface.

Provides centralized logging configuration with consistent formatting.
"""

import logging
import os
import sys
from typing import Optional


def get_logger(
    name: str,
    level: Optional[str] = None
) -> logging.Logger:
    """
    Get a configured logger instance with consistent formatting.
    
    Args:
        name: Logger name (typically __name__ from calling module)
        level: Log level ('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL')
               If None, uses LOG_LEVEL environment variable or defaults to 'INFO'
    
    Returns:
        Configured logging.Logger instance
        
    Examples:
        >>> logger = get_logger(__name__)
        >>> logger.info("Application started")
        >>> logger.error("An error occurred", exc_info=True)
    """
    # Get logger instance
    logger = logging.getLogger(name)
    
    # Only configure if not already configured (avoid duplicate handlers)
    if not logger.handlers:
        # Determine log level
        if level is None:
            level = os.getenv('LOG_LEVEL', 'INFO').upper()
        
        # Validate level
        numeric_level = getattr(logging, level, logging.INFO)
        logger.setLevel(numeric_level)
        
        # Create console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(numeric_level)
        
        # Create formatter
        formatter = logging.Formatter(
            fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        console_handler.setFormatter(formatter)
        
        # Add handler to logger
        logger.addHandler(console_handler)
        
        # Prevent propagation to root logger (avoid duplicate logs)
        logger.propagate = False
    
    return logger


def configure_flask_logger(app, level: Optional[str] = None):
    """
    Configure Flask's built-in logger to use consistent formatting.
    
    Args:
        app: Flask application instance
        level: Log level (uses LOG_LEVEL env var or 'INFO' if None)
    """
    if level is None:
        level = os.getenv('LOG_LEVEL', 'INFO').upper()
    
    numeric_level = getattr(logging, level, logging.INFO)
    app.logger.setLevel(numeric_level)
    
    # Clear existing handlers
    app.logger.handlers.clear()
    
    # Add our formatted handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(numeric_level)
    formatter = logging.Formatter(
        fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_handler.setFormatter(formatter)
    app.logger.addHandler(console_handler)
