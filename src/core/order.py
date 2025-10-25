"""
Order and Trade data structures for the matching engine.

This module defines the core data structures for orders and trades,
with proper validation, serialization, and type safety.
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional, Dict, Any
import json

from .order_types import OrderType, OrderSide, OrderStatus


@dataclass
class Order:
    """
    Represents a trading order in the matching engine.
    
    Orders are immutable once created to ensure data integrity.
    All monetary values use Decimal for precise arithmetic.
    """
    
    # Core order identification
    order_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    symbol: str = ""
    
    # Order specification
    order_type: OrderType = OrderType.LIMIT
    side: OrderSide = OrderSide.BUY
    quantity: Decimal = Decimal('0')
    price: Optional[Decimal] = None
    
    # Metadata
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    status: OrderStatus = OrderStatus.PENDING
    
    # Execution tracking
    filled_quantity: Decimal = Decimal('0')
    average_price: Decimal = Decimal('0')
    
    def __post_init__(self):
        """Validate order after initialization."""
        self._validate()
    
    def _validate(self) -> None:
        """
        Validate order parameters according to business rules.
        
        Raises:
            ValueError: If order parameters are invalid
        """
        if not self.symbol:
            raise ValueError("Symbol cannot be empty")
        
        if self.quantity <= 0:
            raise ValueError(f"Quantity must be positive, got: {self.quantity}")
        
        if self.order_type in [OrderType.LIMIT, OrderType.IOC, OrderType.FOK]:
            if self.price is None:
                raise ValueError(f"Price is required for {self.order_type.value} orders")
            if self.price <= 0:
                raise ValueError(f"Price must be positive, got: {self.price}")
        
        if self.filled_quantity < 0:
            raise ValueError("Filled quantity cannot be negative")
        
        if self.filled_quantity > self.quantity:
            raise ValueError("Filled quantity cannot exceed total quantity")
    
    @property
    def remaining_quantity(self) -> Decimal:
        """Calculate remaining unfilled quantity."""
        return self.quantity - self.filled_quantity
    
    @property
    def is_fully_filled(self) -> bool:
        """Check if order is completely filled."""
        return self.remaining_quantity <= 0
    
    @property
    def is_partially_filled(self) -> bool:
        """Check if order is partially filled."""
        return self.filled_quantity > 0 and not self.is_fully_filled
    
    def can_fill_quantity(self, quantity: Decimal) -> bool:
        """
        Check if order can be filled with given quantity.
        
        Args:
            quantity: Quantity to check
            
        Returns:
            True if order can be filled with this quantity
        """
        return quantity <= self.remaining_quantity
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert order to dictionary for serialization."""
        return {
            "order_id": self.order_id,
            "symbol": self.symbol,
            "order_type": self.order_type.value,
            "side": self.side.value,
            "quantity": str(self.quantity),
            "price": str(self.price) if self.price else None,
            "timestamp": self.timestamp.isoformat(),
            "status": self.status.value,
            "filled_quantity": str(self.filled_quantity),
            "average_price": str(self.average_price),
            "remaining_quantity": str(self.remaining_quantity),
        }
    
    def to_json(self) -> str:
        """Convert order to JSON string."""
        return json.dumps(self.to_dict(), indent=2)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Order':
        """Create order from dictionary."""
        return cls(
            order_id=data.get("order_id", str(uuid.uuid4())),
            symbol=data["symbol"],
            order_type=OrderType(data["order_type"]),
            side=OrderSide(data["side"]),
            quantity=Decimal(data["quantity"]),
            price=Decimal(data["price"]) if data.get("price") else None,
            timestamp=datetime.fromisoformat(data["timestamp"].replace('Z', '+00:00')),
            status=OrderStatus(data.get("status", "pending")),
            filled_quantity=Decimal(data.get("filled_quantity", "0")),
            average_price=Decimal(data.get("average_price", "0")),
        )


@dataclass
class Trade:
    """
    Represents a trade execution in the matching engine.
    
    Trades are created when orders are matched and executed.
    Each trade has a unique ID and tracks both parties involved.
    """
    
    # Trade identification
    trade_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    symbol: str = ""
    
    # Trade details
    price: Decimal = Decimal('0')
    quantity: Decimal = Decimal('0')
    aggressor_side: OrderSide = OrderSide.BUY
    
    # Order references
    maker_order_id: str = ""
    taker_order_id: str = ""
    
    # Metadata
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    # Fee information (optional)
    maker_fee: Decimal = Decimal('0')
    taker_fee: Decimal = Decimal('0')
    
    def __post_init__(self):
        """Validate trade after initialization."""
        self._validate()
    
    def _validate(self) -> None:
        """
        Validate trade parameters.
        
        Raises:
            ValueError: If trade parameters are invalid
        """
        if not self.symbol:
            raise ValueError("Symbol cannot be empty")
        
        if self.price <= 0:
            raise ValueError(f"Price must be positive, got: {self.price}")
        
        if self.quantity <= 0:
            raise ValueError(f"Quantity must be positive, got: {self.quantity}")
        
        if not self.maker_order_id:
            raise ValueError("Maker order ID cannot be empty")
        
        if not self.taker_order_id:
            raise ValueError("Taker order ID cannot be empty")
        
        if self.maker_fee < 0:
            raise ValueError("Maker fee cannot be negative")
        
        if self.taker_fee < 0:
            raise ValueError("Taker fee cannot be negative")
    
    @property
    def total_fee(self) -> Decimal:
        """Calculate total fees for this trade."""
        return self.maker_fee + self.taker_fee
    
    @property
    def notional_value(self) -> Decimal:
        """Calculate notional value of the trade."""
        return self.price * self.quantity
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert trade to dictionary for serialization."""
        return {
            "trade_id": self.trade_id,
            "symbol": self.symbol,
            "price": str(self.price),
            "quantity": str(self.quantity),
            "aggressor_side": self.aggressor_side.value,
            "maker_order_id": self.maker_order_id,
            "taker_order_id": self.taker_order_id,
            "timestamp": self.timestamp.isoformat(),
            "maker_fee": str(self.maker_fee),
            "taker_fee": str(self.taker_fee),
            "total_fee": str(self.total_fee),
            "notional_value": str(self.notional_value),
        }
    
    def to_json(self) -> str:
        """Convert trade to JSON string."""
        return json.dumps(self.to_dict(), indent=2)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Trade':
        """Create trade from dictionary."""
        return cls(
            trade_id=data.get("trade_id", str(uuid.uuid4())),
            symbol=data["symbol"],
            price=Decimal(data["price"]),
            quantity=Decimal(data["quantity"]),
            aggressor_side=OrderSide(data["aggressor_side"]),
            maker_order_id=data["maker_order_id"],
            taker_order_id=data["taker_order_id"],
            timestamp=datetime.fromisoformat(data["timestamp"].replace('Z', '+00:00')),
            maker_fee=Decimal(data.get("maker_fee", "0")),
            taker_fee=Decimal(data.get("taker_fee", "0")),
        )
