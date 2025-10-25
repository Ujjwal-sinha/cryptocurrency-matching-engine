"""
API layer for the cryptocurrency matching engine.

This module provides REST and WebSocket APIs for order submission,
market data streaming, and trade execution feeds.
"""

from .rest_api import create_app
from .websocket_api import WebSocketServer
from .validators import validate_order_request, validate_symbol

__all__ = [
    "create_app",
    "WebSocketServer", 
    "validate_order_request",
    "validate_symbol",
]
