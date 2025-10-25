"""
Input validation utilities for the API layer.

This module provides comprehensive validation for order requests,
market data queries, and other API inputs to ensure data integrity.
"""

import re
from decimal import Decimal, InvalidOperation
from typing import Dict, Any, Optional, Tuple
import logging

from ..core.order_types import OrderType, OrderSide

logger = logging.getLogger(__name__)

# Symbol validation pattern (e.g., BTC-USDT, ETH-BTC)
SYMBOL_PATTERN = re.compile(r'^[A-Z0-9]+-[A-Z0-9]+$')

# Minimum and maximum values
MIN_QUANTITY = Decimal('0.00000001')
MAX_QUANTITY = Decimal('1000000')
MIN_PRICE = Decimal('0.00000001')
MAX_PRICE = Decimal('10000000')


def validate_symbol(symbol: str) -> Tuple[bool, Optional[str]]:
    """
    Validate trading symbol format.
    
    Args:
        symbol: Trading symbol to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not symbol:
        return False, "Symbol cannot be empty"
    
    if not isinstance(symbol, str):
        return False, "Symbol must be a string"
    
    if not SYMBOL_PATTERN.match(symbol):
        return False, f"Invalid symbol format: {symbol}. Expected format: BASE-QUOTE (e.g., BTC-USDT)"
    
    return True, None


def validate_quantity(quantity: Any) -> Tuple[bool, Optional[str], Optional[Decimal]]:
    """
    Validate order quantity.
    
    Args:
        quantity: Quantity to validate
        
    Returns:
        Tuple of (is_valid, error_message, parsed_quantity)
    """
    if quantity is None:
        return False, "Quantity is required", None
    
    try:
        qty = Decimal(str(quantity))
    except (InvalidOperation, ValueError, TypeError):
        return False, f"Invalid quantity format: {quantity}", None
    
    if qty <= 0:
        return False, "Quantity must be positive", None
    
    if qty < MIN_QUANTITY:
        return False, f"Quantity too small. Minimum: {MIN_QUANTITY}", None
    
    if qty > MAX_QUANTITY:
        return False, f"Quantity too large. Maximum: {MAX_QUANTITY}", None
    
    return True, None, qty


def validate_price(price: Any, order_type: OrderType) -> Tuple[bool, Optional[str], Optional[Decimal]]:
    """
    Validate order price.
    
    Args:
        price: Price to validate
        order_type: Type of order
        
    Returns:
        Tuple of (is_valid, error_message, parsed_price)
    """
    # Market orders don't need price
    if order_type == OrderType.MARKET:
        return True, None, None
    
    if price is None:
        return False, f"Price is required for {order_type.value} orders", None
    
    try:
        prc = Decimal(str(price))
    except (InvalidOperation, ValueError, TypeError):
        return False, f"Invalid price format: {price}", None
    
    if prc <= 0:
        return False, "Price must be positive", None
    
    if prc < MIN_PRICE:
        return False, f"Price too small. Minimum: {MIN_PRICE}", None
    
    if prc > MAX_PRICE:
        return False, f"Price too large. Maximum: {MAX_PRICE}", None
    
    return True, None, prc


def validate_order_type(order_type: Any) -> Tuple[bool, Optional[str], Optional[OrderType]]:
    """
    Validate order type.
    
    Args:
        order_type: Order type to validate
        
    Returns:
        Tuple of (is_valid, error_message, parsed_order_type)
    """
    if not order_type:
        return False, "Order type is required", None
    
    if not isinstance(order_type, str):
        return False, "Order type must be a string", None
    
    try:
        ot = OrderType(order_type.lower())
    except ValueError:
        valid_types = [ot.value for ot in OrderType]
        return False, f"Invalid order type: {order_type}. Must be one of: {valid_types}", None
    
    return True, None, ot


def validate_order_side(side: Any) -> Tuple[bool, Optional[str], Optional[OrderSide]]:
    """
    Validate order side.
    
    Args:
        side: Order side to validate
        
    Returns:
        Tuple of (is_valid, error_message, parsed_order_side)
    """
    if not side:
        return False, "Order side is required", None
    
    if not isinstance(side, str):
        return False, "Order side must be a string", None
    
    try:
        os = OrderSide(side.lower())
    except ValueError:
        valid_sides = [os.value for os in OrderSide]
        return False, f"Invalid order side: {side}. Must be one of: {valid_sides}", None
    
    return True, None, os


def validate_order_request(data: Dict[str, Any]) -> Tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
    """
    Validate complete order request.
    
    Args:
        data: Order request data
        
    Returns:
        Tuple of (is_valid, error_message, parsed_data)
    """
    try:
        # Validate required fields
        required_fields = ['symbol', 'order_type', 'side', 'quantity']
        for field in required_fields:
            if field not in data:
                return False, f"Missing required field: {field}", None
        
        # Validate symbol
        is_valid, error = validate_symbol(data['symbol'])
        if not is_valid:
            return False, error, None
        
        # Validate order type
        is_valid, error, order_type = validate_order_type(data['order_type'])
        if not is_valid:
            return False, error, None
        
        # Validate order side
        is_valid, error, order_side = validate_order_side(data['side'])
        if not is_valid:
            return False, error, None
        
        # Validate quantity
        is_valid, error, quantity = validate_quantity(data['quantity'])
        if not is_valid:
            return False, error, None
        
        # Validate price (if required)
        price = None
        if order_type in [OrderType.LIMIT, OrderType.IOC, OrderType.FOK]:
            is_valid, error, price = validate_price(data.get('price'), order_type)
            if not is_valid:
                return False, error, None
        
        # Build validated data
        validated_data = {
            'symbol': data['symbol'],
            'order_type': order_type,
            'side': order_side,
            'quantity': quantity,
            'price': price,
        }
        
        return True, None, validated_data
        
    except Exception as e:
        logger.error(f"Error validating order request: {str(e)}")
        return False, f"Validation error: {str(e)}", None


def validate_depth_request(symbol: str, depth: Any) -> Tuple[bool, Optional[str], Optional[int]]:
    """
    Validate order book depth request.
    
    Args:
        symbol: Trading symbol
        depth: Depth parameter
        
    Returns:
        Tuple of (is_valid, error_message, parsed_depth)
    """
    # Validate symbol
    is_valid, error = validate_symbol(symbol)
    if not is_valid:
        return False, error, None
    
    # Validate depth
    if depth is None:
        depth = 10  # Default depth
    else:
        try:
            depth = int(depth)
        except (ValueError, TypeError):
            return False, f"Invalid depth format: {depth}. Must be an integer", None
        
        if depth <= 0:
            return False, "Depth must be positive", None
        
        if depth > 100:
            return False, "Depth too large. Maximum: 100", None
    
    return True, None, depth


def validate_cancel_request(data: Dict[str, Any]) -> Tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
    """
    Validate order cancellation request.
    
    Args:
        data: Cancel request data
        
    Returns:
        Tuple of (is_valid, error_message, parsed_data)
    """
    try:
        # Validate required fields
        required_fields = ['order_id', 'symbol']
        for field in required_fields:
            if field not in data:
                return False, f"Missing required field: {field}", None
        
        # Validate symbol
        is_valid, error = validate_symbol(data['symbol'])
        if not is_valid:
            return False, error, None
        
        # Validate order ID
        order_id = data['order_id']
        if not order_id or not isinstance(order_id, str):
            return False, "Order ID must be a non-empty string", None
        
        validated_data = {
            'order_id': order_id,
            'symbol': data['symbol'],
        }
        
        return True, None, validated_data
        
    except Exception as e:
        logger.error(f"Error validating cancel request: {str(e)}")
        return False, f"Validation error: {str(e)}", None


def sanitize_string(value: Any, max_length: int = 100) -> str:
    """
    Sanitize string input to prevent injection attacks.
    
    Args:
        value: Value to sanitize
        max_length: Maximum allowed length
        
    Returns:
        Sanitized string
    """
    if not isinstance(value, str):
        value = str(value)
    
    # Remove potentially dangerous characters
    sanitized = re.sub(r'[<>"\']', '', value)
    
    # Truncate if too long
    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length]
    
    return sanitized.strip()
