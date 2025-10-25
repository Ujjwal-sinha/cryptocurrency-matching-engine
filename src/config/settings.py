"""
Configuration settings for the matching engine.

This module provides centralized configuration management
with environment variable support and validation.
"""

import os
from typing import Optional, Dict, Any
from decimal import Decimal


class Settings:
    """
    Configuration settings for the matching engine.
    
    Supports environment variables and provides sensible defaults.
    """
    
    def __init__(self):
        """Initialize settings from environment variables."""
        # Server configuration
        self.rest_host = os.getenv("REST_HOST", "0.0.0.0")
        self.rest_port = int(os.getenv("REST_PORT", "5000"))
        self.websocket_host = os.getenv("WEBSOCKET_HOST", "localhost")
        self.websocket_port = int(os.getenv("WEBSOCKET_PORT", "8765"))
        
        # Logging configuration
        self.log_level = os.getenv("LOG_LEVEL", "INFO")
        self.log_file = os.getenv("LOG_FILE", "logs/matching_engine.log")
        self.audit_log_file = os.getenv("AUDIT_LOG_FILE", "logs/audit.log")
        
        # Performance configuration
        self.max_orders_per_second = int(os.getenv("MAX_ORDERS_PER_SECOND", "10000"))
        self.max_order_book_depth = int(os.getenv("MAX_ORDER_BOOK_DEPTH", "100"))
        self.max_price_levels = int(os.getenv("MAX_PRICE_LEVELS", "1000"))
        
        # Order validation
        self.min_quantity = Decimal(os.getenv("MIN_QUANTITY", "0.00000001"))
        self.max_quantity = Decimal(os.getenv("MAX_QUANTITY", "1000000"))
        self.min_price = Decimal(os.getenv("MIN_PRICE", "0.00000001"))
        self.max_price = Decimal(os.getenv("MAX_PRICE", "10000000"))
        
        # Fee configuration (optional)
        self.maker_fee_rate = Decimal(os.getenv("MAKER_FEE_RATE", "0.001"))  # 0.1%
        self.taker_fee_rate = Decimal(os.getenv("TAKER_FEE_RATE", "0.001"))  # 0.1%
        
        # WebSocket configuration
        self.websocket_ping_interval = int(os.getenv("WEBSOCKET_PING_INTERVAL", "20"))
        self.websocket_ping_timeout = int(os.getenv("WEBSOCKET_PING_TIMEOUT", "10"))
        self.websocket_max_connections = int(os.getenv("WEBSOCKET_MAX_CONNECTIONS", "1000"))
        
        # Performance monitoring
        self.enable_performance_monitoring = os.getenv("ENABLE_PERFORMANCE_MONITORING", "true").lower() == "true"
        self.performance_log_interval = int(os.getenv("PERFORMANCE_LOG_INTERVAL", "60"))  # seconds
        
        # Persistence (optional)
        self.enable_persistence = os.getenv("ENABLE_PERSISTENCE", "false").lower() == "true"
        self.persistence_file = os.getenv("PERSISTENCE_FILE", "data/order_books.json")
        
        # Security
        self.enable_cors = os.getenv("ENABLE_CORS", "true").lower() == "true"
        self.cors_origins = os.getenv("CORS_ORIGINS", "*").split(",")
        
        # Debug mode
        self.debug = os.getenv("DEBUG", "false").lower() == "true"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert settings to dictionary."""
        return {
            "rest_host": self.rest_host,
            "rest_port": self.rest_port,
            "websocket_host": self.websocket_host,
            "websocket_port": self.websocket_port,
            "log_level": self.log_level,
            "log_file": self.log_file,
            "audit_log_file": self.audit_log_file,
            "max_orders_per_second": self.max_orders_per_second,
            "max_order_book_depth": self.max_order_book_depth,
            "max_price_levels": self.max_price_levels,
            "min_quantity": str(self.min_quantity),
            "max_quantity": str(self.max_quantity),
            "min_price": str(self.min_price),
            "max_price": str(self.max_price),
            "maker_fee_rate": str(self.maker_fee_rate),
            "taker_fee_rate": str(self.taker_fee_rate),
            "websocket_ping_interval": self.websocket_ping_interval,
            "websocket_ping_timeout": self.websocket_ping_timeout,
            "websocket_max_connections": self.websocket_max_connections,
            "enable_performance_monitoring": self.enable_performance_monitoring,
            "performance_log_interval": self.performance_log_interval,
            "enable_persistence": self.enable_persistence,
            "persistence_file": self.persistence_file,
            "enable_cors": self.enable_cors,
            "cors_origins": self.cors_origins,
            "debug": self.debug,
        }
    
    def validate(self) -> None:
        """Validate configuration settings."""
        errors = []
        
        # Validate ports
        if not (1 <= self.rest_port <= 65535):
            errors.append(f"Invalid REST port: {self.rest_port}")
        
        if not (1 <= self.websocket_port <= 65535):
            errors.append(f"Invalid WebSocket port: {self.websocket_port}")
        
        # Validate quantities and prices
        if self.min_quantity <= 0:
            errors.append(f"Min quantity must be positive: {self.min_quantity}")
        
        if self.max_quantity <= self.min_quantity:
            errors.append(f"Max quantity must be greater than min quantity: {self.max_quantity} <= {self.min_quantity}")
        
        if self.min_price <= 0:
            errors.append(f"Min price must be positive: {self.min_price}")
        
        if self.max_price <= self.min_price:
            errors.append(f"Max price must be greater than min price: {self.max_price} <= {self.min_price}")
        
        # Validate fee rates
        if self.maker_fee_rate < 0 or self.maker_fee_rate > 1:
            errors.append(f"Maker fee rate must be between 0 and 1: {self.maker_fee_rate}")
        
        if self.taker_fee_rate < 0 or self.taker_fee_rate > 1:
            errors.append(f"Taker fee rate must be between 0 and 1: {self.taker_fee_rate}")
        
        # Validate performance settings
        if self.max_orders_per_second <= 0:
            errors.append(f"Max orders per second must be positive: {self.max_orders_per_second}")
        
        if self.max_order_book_depth <= 0:
            errors.append(f"Max order book depth must be positive: {self.max_order_book_depth}")
        
        if self.max_price_levels <= 0:
            errors.append(f"Max price levels must be positive: {self.max_price_levels}")
        
        if errors:
            raise ValueError(f"Configuration validation failed: {'; '.join(errors)}")


# Global settings instance
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """
    Get the global settings instance.
    
    Returns:
        Settings instance
    """
    global _settings
    if _settings is None:
        _settings = Settings()
        _settings.validate()
    return _settings


def reload_settings() -> Settings:
    """
    Reload settings from environment variables.
    
    Returns:
        New settings instance
    """
    global _settings
    _settings = Settings()
    _settings.validate()
    return _settings
