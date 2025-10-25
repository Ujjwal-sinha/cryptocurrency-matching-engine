"""
Order type definitions and enums for the matching engine.

This module defines the core order types and sides supported by the engine,
following REG NMS principles and standard financial market conventions.
"""

from enum import Enum
from typing import Optional


class OrderType(Enum):
    """
    Supported order types in the matching engine.
    
    Following standard financial market conventions:
    - MARKET: Execute immediately at best available price
    - LIMIT: Execute at specified price or better
    - IOC: Immediate or Cancel - execute now or cancel unfilled portion
    - FOK: Fill or Kill - execute entire order now or cancel everything
    """
    MARKET = "market"
    LIMIT = "limit"
    IOC = "ioc"  # Immediate or Cancel
    FOK = "fok"  # Fill or Kill


class OrderSide(Enum):
    """
    Order sides for buy and sell orders.
    
    - BUY: Orders to purchase the asset
    - SELL: Orders to sell the asset
    """
    BUY = "buy"
    SELL = "sell"


class OrderStatus(Enum):
    """
    Order status tracking throughout the lifecycle.
    
    - PENDING: Order submitted but not yet processed
    - PARTIALLY_FILLED: Order partially executed
    - FILLED: Order completely executed
    - CANCELLED: Order cancelled by user or system
    - REJECTED: Order rejected due to validation failure
    """
    PENDING = "pending"
    PARTIALLY_FILLED = "partially_filled"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"


def validate_order_type(order_type: str) -> OrderType:
    """
    Validate and convert string order type to OrderType enum.
    
    Args:
        order_type: String representation of order type
        
    Returns:
        OrderType enum value
        
    Raises:
        ValueError: If order_type is invalid
    """
    try:
        return OrderType(order_type.lower())
    except ValueError:
        raise ValueError(f"Invalid order type: {order_type}. Must be one of: {[ot.value for ot in OrderType]}")


def validate_order_side(side: str) -> OrderSide:
    """
    Validate and convert string order side to OrderSide enum.
    
    Args:
        side: String representation of order side
        
    Returns:
        OrderSide enum value
        
    Raises:
        ValueError: If side is invalid
    """
    try:
        return OrderSide(side.lower())
    except ValueError:
        raise ValueError(f"Invalid order side: {side}. Must be one of: {[os.value for os in OrderSide]}")


def is_marketable_order(order_type: OrderType) -> bool:
    """
    Check if an order type is marketable (can execute immediately).
    
    Args:
        order_type: The order type to check
        
    Returns:
        True if the order type is marketable
    """
    return order_type in [OrderType.MARKET, OrderType.IOC, OrderType.FOK]


def requires_price(order_type: OrderType) -> bool:
    """
    Check if an order type requires a price specification.
    
    Args:
        order_type: The order type to check
        
    Returns:
        True if the order type requires a price
    """
    return order_type in [OrderType.LIMIT, OrderType.IOC, OrderType.FOK]
