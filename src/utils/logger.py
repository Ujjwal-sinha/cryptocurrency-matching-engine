"""
Logging configuration for the matching engine.

This module provides comprehensive logging setup with different
log levels, formatters, and handlers for different components.
"""

import logging
import logging.handlers
import os
import sys
from datetime import datetime
from typing import Optional


def setup_logging(
    level: str = "INFO",
    log_file: Optional[str] = None,
    max_file_size: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5
) -> None:
    """
    Set up logging configuration for the matching engine.
    
    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Path to log file (optional)
        max_file_size: Maximum log file size in bytes
        backup_count: Number of backup files to keep
    """
    # Convert string level to logging constant
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    
    # Create formatters
    detailed_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    simple_formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%H:%M:%S'
    )
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)
    
    # Clear existing handlers
    root_logger.handlers.clear()
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(numeric_level)
    console_handler.setFormatter(simple_formatter)
    root_logger.addHandler(console_handler)
    
    # File handler (if specified)
    if log_file:
        # Create logs directory if it doesn't exist
        log_dir = os.path.dirname(log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir)
        
        # Rotating file handler
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=max_file_size,
            backupCount=backup_count
        )
        file_handler.setLevel(numeric_level)
        file_handler.setFormatter(detailed_formatter)
        root_logger.addHandler(file_handler)
    
    # Set specific logger levels
    logging.getLogger('websockets').setLevel(logging.WARNING)
    logging.getLogger('asyncio').setLevel(logging.WARNING)
    
    # Log startup message
    logger = logging.getLogger(__name__)
    logger.info(f"Logging initialized - Level: {level}, File: {log_file or 'Console only'}")


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance for a specific module.
    
    Args:
        name: Logger name (usually __name__)
        
    Returns:
        Logger instance
    """
    return logging.getLogger(name)


class MatchingEngineLogger:
    """
    Specialized logger for matching engine operations.
    
    Provides structured logging for orders, trades, and system events.
    """
    
    def __init__(self, name: str = "matching_engine"):
        self.logger = logging.getLogger(name)
        self.order_logger = logging.getLogger(f"{name}.orders")
        self.trade_logger = logging.getLogger(f"{name}.trades")
        self.performance_logger = logging.getLogger(f"{name}.performance")
    
    def log_order_submission(self, order_id: str, symbol: str, order_type: str, side: str, quantity: str, price: str = None) -> None:
        """Log order submission."""
        self.order_logger.info(
            f"ORDER_SUBMIT|{order_id}|{symbol}|{order_type}|{side}|{quantity}|{price or 'N/A'}"
        )
    
    def log_order_execution(self, order_id: str, status: str, filled_quantity: str, average_price: str) -> None:
        """Log order execution."""
        self.order_logger.info(
            f"ORDER_EXEC|{order_id}|{status}|{filled_quantity}|{average_price}"
        )
    
    def log_trade_execution(self, trade_id: str, symbol: str, price: str, quantity: str, aggressor_side: str) -> None:
        """Log trade execution."""
        self.trade_logger.info(
            f"TRADE_EXEC|{trade_id}|{symbol}|{price}|{quantity}|{aggressor_side}"
        )
    
    def log_performance_metric(self, metric_name: str, value: float, unit: str = "ms") -> None:
        """Log performance metric."""
        self.performance_logger.info(
            f"PERF_METRIC|{metric_name}|{value}|{unit}"
        )
    
    def log_system_event(self, event: str, details: str = "") -> None:
        """Log system event."""
        self.logger.info(f"SYSTEM_EVENT|{event}|{details}")
    
    def log_error(self, component: str, error: str, order_id: str = None) -> None:
        """Log error."""
        context = f"|{order_id}" if order_id else ""
        self.logger.error(f"ERROR|{component}|{error}{context}")


def create_audit_logger(log_file: str = "logs/audit.log") -> logging.Logger:
    """
    Create a dedicated audit logger for compliance.
    
    Args:
        log_file: Path to audit log file
        
    Returns:
        Audit logger instance
    """
    # Create logs directory if it doesn't exist
    log_dir = os.path.dirname(log_file)
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    # Create audit logger
    audit_logger = logging.getLogger("audit")
    audit_logger.setLevel(logging.INFO)
    
    # Prevent propagation to root logger
    audit_logger.propagate = False
    
    # Create file handler for audit log
    audit_handler = logging.handlers.RotatingFileHandler(
        log_file,
        maxBytes=50 * 1024 * 1024,  # 50MB
        backupCount=10
    )
    
    # Audit formatter - structured for easy parsing
    audit_formatter = logging.Formatter(
        '%(asctime)s|%(levelname)s|%(message)s',
        datefmt='%Y-%m-%d %H:%M:%S.%f'
    )
    audit_handler.setFormatter(audit_formatter)
    
    audit_logger.addHandler(audit_handler)
    
    return audit_logger


def log_order_audit(audit_logger: logging.Logger, action: str, order_data: dict) -> None:
    """
    Log order action to audit trail.
    
    Args:
        audit_logger: Audit logger instance
        action: Action performed (SUBMIT, EXECUTE, CANCEL, REJECT)
        order_data: Order data dictionary
    """
    audit_logger.info(
        f"ORDER_{action}|"
        f"ID:{order_data.get('order_id', 'N/A')}|"
        f"SYMBOL:{order_data.get('symbol', 'N/A')}|"
        f"TYPE:{order_data.get('order_type', 'N/A')}|"
        f"SIDE:{order_data.get('side', 'N/A')}|"
        f"QTY:{order_data.get('quantity', 'N/A')}|"
        f"PRICE:{order_data.get('price', 'N/A')}"
    )


def log_trade_audit(audit_logger: logging.Logger, trade_data: dict) -> None:
    """
    Log trade execution to audit trail.
    
    Args:
        audit_logger: Audit logger instance
        trade_data: Trade data dictionary
    """
    audit_logger.info(
        f"TRADE_EXECUTE|"
        f"ID:{trade_data.get('trade_id', 'N/A')}|"
        f"SYMBOL:{trade_data.get('symbol', 'N/A')}|"
        f"PRICE:{trade_data.get('price', 'N/A')}|"
        f"QTY:{trade_data.get('quantity', 'N/A')}|"
        f"AGGRESSOR:{trade_data.get('aggressor_side', 'N/A')}|"
        f"MAKER:{trade_data.get('maker_order_id', 'N/A')}|"
        f"TAKER:{trade_data.get('taker_order_id', 'N/A')}"
    )
