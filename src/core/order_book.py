"""
Order book implementation with price-time priority.

This module implements an efficient order book using heap-based
price levels and deque-based FIFO order management for optimal
performance in high-frequency trading scenarios.
"""

import heapq
from collections import deque
from decimal import Decimal
from typing import Dict, List, Tuple, Optional, Iterator
import logging

from .order import Order, Trade
from .order_types import OrderSide, OrderType, OrderStatus

logger = logging.getLogger(__name__)


class PriceLevel:
    """
    Represents a price level in the order book.
    
    Maintains orders at the same price in FIFO (first-in-first-out) order
    to ensure proper time priority within each price level.
    """
    
    def __init__(self, price: Decimal):
        """
        Initialize a price level.
        
        Args:
            price: The price level for this group of orders
        """
        self.price = price
        self.orders: deque = deque()  # FIFO queue for time priority
        self.total_quantity = Decimal('0')
        self.order_count = 0
    
    def add_order(self, order: Order) -> None:
        """
        Add an order to this price level.
        
        Args:
            order: The order to add
        """
        self.orders.append(order)
        self.total_quantity += order.quantity
        self.order_count += 1
        logger.debug(f"Added order {order.order_id} to price level {self.price}")
    
    def remove_order(self, order: Order) -> bool:
        """
        Remove an order from this price level.
        
        Args:
            order: The order to remove
            
        Returns:
            True if order was found and removed, False otherwise
        """
        try:
            self.orders.remove(order)
            self.total_quantity -= order.quantity
            self.order_count -= 1
            logger.debug(f"Removed order {order.order_id} from price level {self.price}")
            return True
        except ValueError:
            logger.warning(f"Order {order.order_id} not found in price level {self.price}")
            return False
    
    def get_orders(self) -> List[Order]:
        """
        Get all orders in this price level.
        
        Returns:
            List of orders in FIFO order
        """
        return list(self.orders)
    
    def is_empty(self) -> bool:
        """Check if this price level is empty."""
        return len(self.orders) == 0
    
    def __len__(self) -> int:
        """Return number of orders in this price level."""
        return len(self.orders)
    
    def __repr__(self) -> str:
        return f"PriceLevel(price={self.price}, orders={len(self.orders)}, quantity={self.total_quantity})"


class OrderBook:
    """
    High-performance order book implementation.
    
    Uses heap-based price level management for O(log n) operations
    and deque-based FIFO order management for time priority.
    """
    
    def __init__(self, symbol: str):
        """
        Initialize order book for a trading symbol.
        
        Args:
            symbol: Trading symbol (e.g., "BTC-USDT")
        """
        self.symbol = symbol
        
        # Order storage: price -> PriceLevel
        self.bids: Dict[Decimal, PriceLevel] = {}
        self.asks: Dict[Decimal, PriceLevel] = {}
        
        # Price level heaps for efficient best price lookup
        # Use negative prices for bids to create max-heap behavior
        self.bid_prices: List[Decimal] = []  # Max heap (negated)
        self.ask_prices: List[Decimal] = []  # Min heap
        
        # Order lookup for O(1) access
        self.orders: Dict[str, Order] = {}
        
        # Statistics
        self.total_bid_quantity = Decimal('0')
        self.total_ask_quantity = Decimal('0')
        self.last_trade_price: Optional[Decimal] = None
        
        logger.info(f"Initialized order book for {symbol}")
    
    def add_order(self, order: Order) -> List[Trade]:
        """
        Add an order to the order book and execute any matches.
        
        Args:
            order: The order to add
            
        Returns:
            List of trades executed
        """
        if order.symbol != self.symbol:
            raise ValueError(f"Order symbol {order.symbol} does not match book symbol {self.symbol}")
        
        self.orders[order.order_id] = order
        trades = []
        
        if order.side == OrderSide.BUY:
            trades = self._match_buy_order(order)
        else:
            trades = self._match_sell_order(order)
        
        # Update statistics
        self._update_statistics()
        
        return trades
    
    def _match_buy_order(self, order: Order) -> List[Trade]:
        """
        Match a buy order against existing sell orders.
        
        Args:
            order: The buy order to match
            
        Returns:
            List of trades executed
        """
        trades = []
        remaining_quantity = order.quantity
        
        # Process asks in price-time priority order
        while remaining_quantity > 0 and self.ask_prices:
            best_ask_price = heapq.heappop(self.ask_prices)
            
            if best_ask_price not in self.asks:
                continue
            
            price_level = self.asks[best_ask_price]
            
            # Match against orders at this price level
            while remaining_quantity > 0 and price_level.orders:
                resting_order = price_level.orders[0]
                
                # Calculate trade quantity
                trade_quantity = min(remaining_quantity, resting_order.remaining_quantity)
                
                # Create trade
                trade = Trade(
                    symbol=order.symbol,
                    price=best_ask_price,
                    quantity=trade_quantity,
                    aggressor_side=OrderSide.BUY,
                    maker_order_id=resting_order.order_id,
                    taker_order_id=order.order_id
                )
                trades.append(trade)
                
                # Update order quantities
                remaining_quantity -= trade_quantity
                resting_order.filled_quantity += trade_quantity
                order.filled_quantity += trade_quantity
                
                # Update average prices
                self._update_average_price(resting_order, trade)
                self._update_average_price(order, trade)
                
                # Update the order in the orders dictionary
                self.orders[resting_order.order_id] = resting_order
                
                # Remove fully filled resting order
                if resting_order.is_fully_filled:
                    resting_order.status = OrderStatus.FILLED
                    price_level.orders.popleft()
                    del self.orders[resting_order.order_id]
                else:
                    resting_order.status = OrderStatus.PARTIALLY_FILLED
                    break
            
            # Re-add price level to heap if not empty
            if not price_level.is_empty():
                heapq.heappush(self.ask_prices, best_ask_price)
            else:
                del self.asks[best_ask_price]
        
        # Add remaining quantity as limit order if not market order
        if remaining_quantity > 0 and order.order_type != OrderType.MARKET:
            self._add_limit_buy_order(order, remaining_quantity)
        elif remaining_quantity > 0:
            # Market order with remaining quantity - reject
            order.status = OrderStatus.REJECTED
            logger.warning(f"Market order {order.order_id} partially filled, rejecting remaining {remaining_quantity}")
        elif trades:
            # Order was fully filled
            order.status = OrderStatus.FILLED
        
        return trades
    
    def _match_sell_order(self, order: Order) -> List[Trade]:
        """
        Match a sell order against existing buy orders.
        
        Args:
            order: The sell order to match
            
        Returns:
            List of trades executed
        """
        trades = []
        remaining_quantity = order.quantity
        
        # Process bids in price-time priority order
        while remaining_quantity > 0 and self.bid_prices:
            # Negate to get max bid price
            best_bid_price = -heapq.heappop(self.bid_prices)
            
            if best_bid_price not in self.bids:
                continue
            
            price_level = self.bids[best_bid_price]
            
            # Match against orders at this price level
            while remaining_quantity > 0 and price_level.orders:
                resting_order = price_level.orders[0]
                
                # Calculate trade quantity
                trade_quantity = min(remaining_quantity, resting_order.remaining_quantity)
                
                # Create trade
                trade = Trade(
                    symbol=order.symbol,
                    price=best_bid_price,
                    quantity=trade_quantity,
                    aggressor_side=OrderSide.SELL,
                    maker_order_id=resting_order.order_id,
                    taker_order_id=order.order_id
                )
                trades.append(trade)
                
                # Update order quantities
                remaining_quantity -= trade_quantity
                resting_order.filled_quantity += trade_quantity
                order.filled_quantity += trade_quantity
                
                # Update average prices
                self._update_average_price(resting_order, trade)
                self._update_average_price(order, trade)
                
                # Update the order in the orders dictionary
                self.orders[resting_order.order_id] = resting_order
                
                # Remove fully filled resting order
                if resting_order.is_fully_filled:
                    resting_order.status = OrderStatus.FILLED
                    price_level.orders.popleft()
                    del self.orders[resting_order.order_id]
                else:
                    resting_order.status = OrderStatus.PARTIALLY_FILLED
                    break
            
            # Re-add price level to heap if not empty
            if not price_level.is_empty():
                heapq.heappush(self.bid_prices, -best_bid_price)
            else:
                del self.bids[best_bid_price]
        
        # Add remaining quantity as limit order if not market order
        if remaining_quantity > 0 and order.order_type != OrderType.MARKET:
            self._add_limit_sell_order(order, remaining_quantity)
        elif remaining_quantity > 0:
            # Market order with remaining quantity - reject
            order.status = OrderStatus.REJECTED
            logger.warning(f"Market order {order.order_id} partially filled, rejecting remaining {remaining_quantity}")
        elif trades:
            # Order was fully filled
            order.status = OrderStatus.FILLED
        
        return trades
    
    def _add_limit_buy_order(self, order: Order, quantity: Decimal) -> None:
        """Add a limit buy order to the book."""
        if order.price not in self.bids:
            self.bids[order.price] = PriceLevel(order.price)
            heapq.heappush(self.bid_prices, -order.price)  # Negate for max-heap
        
        # Create new order with remaining quantity
        limit_order = Order(
            order_id=order.order_id,
            symbol=order.symbol,
            order_type=OrderType.LIMIT,
            side=OrderSide.BUY,
            quantity=quantity,
            price=order.price,
            timestamp=order.timestamp
        )
        
        self.bids[order.price].add_order(limit_order)
        self.orders[order.order_id] = limit_order
        order.status = OrderStatus.PENDING
    
    def _add_limit_sell_order(self, order: Order, quantity: Decimal) -> None:
        """Add a limit sell order to the book."""
        if order.price not in self.asks:
            self.asks[order.price] = PriceLevel(order.price)
            heapq.heappush(self.ask_prices, order.price)
        
        # Create new order with remaining quantity
        limit_order = Order(
            order_id=order.order_id,
            symbol=order.symbol,
            order_type=OrderType.LIMIT,
            side=OrderSide.SELL,
            quantity=quantity,
            price=order.price,
            timestamp=order.timestamp
        )
        
        self.asks[order.price].add_order(limit_order)
        self.orders[order.order_id] = limit_order
        order.status = OrderStatus.PENDING
    
    def _update_average_price(self, order: Order, trade: Trade) -> None:
        """Update average price for an order after a trade."""
        if order.filled_quantity > 0:
            total_value = order.average_price * (order.filled_quantity - trade.quantity) + trade.price * trade.quantity
            order.average_price = total_value / order.filled_quantity
    
    def _update_statistics(self) -> None:
        """Update order book statistics."""
        self.total_bid_quantity = sum(level.total_quantity for level in self.bids.values())
        self.total_ask_quantity = sum(level.total_quantity for level in self.asks.values())
    
    def get_bbo(self) -> Tuple[Optional[Decimal], Optional[Decimal]]:
        """
        Get Best Bid and Offer (BBO).
        
        Returns:
            Tuple of (best_bid, best_ask) prices
        """
        best_bid = None
        best_ask = None
        
        if self.bid_prices:
            best_bid = -self.bid_prices[0]  # Negate back from max-heap
        
        if self.ask_prices:
            best_ask = self.ask_prices[0]
        
        return best_bid, best_ask
    
    def get_order_book_depth(self, side: str, depth: int = 10) -> List[List[str]]:
        """
        Get order book depth for a specific side.
        
        Args:
            side: "bids" or "asks"
            depth: Maximum number of price levels to return
            
        Returns:
            List of [price, quantity] pairs
        """
        if side == "bids":
            # Get top bid prices (highest first)
            bid_prices = sorted(self.bids.keys(), reverse=True)[:depth]
            return [[str(price), str(self.bids[price].total_quantity)] for price in bid_prices]
        else:
            # Get top ask prices (lowest first)
            ask_prices = sorted(self.asks.keys())[:depth]
            return [[str(price), str(self.asks[price].total_quantity)] for price in ask_prices]
    
    def get_order(self, order_id: str) -> Optional[Order]:
        """Get order by ID."""
        return self.orders.get(order_id)
    
    def cancel_order(self, order_id: str) -> bool:
        """
        Cancel an order.
        
        Args:
            order_id: ID of order to cancel
            
        Returns:
            True if order was found and cancelled
        """
        order = self.orders.get(order_id)
        if not order:
            return False
        
        if order.side == OrderSide.BUY and order.price in self.bids:
            self.bids[order.price].remove_order(order)
            if self.bids[order.price].is_empty():
                del self.bids[order.price]
                # Remove from heap
                try:
                    self.bid_prices.remove(-order.price)
                    heapq.heapify(self.bid_prices)
                except ValueError:
                    pass
        elif order.side == OrderSide.SELL and order.price in self.asks:
            self.asks[order.price].remove_order(order)
            if self.asks[order.price].is_empty():
                del self.asks[order.price]
                # Remove from heap
                try:
                    self.ask_prices.remove(order.price)
                    heapq.heapify(self.ask_prices)
                except ValueError:
                    pass
        
        order.status = OrderStatus.CANCELLED
        del self.orders[order_id]
        self._update_statistics()
        
        return True
    
    def get_statistics(self) -> Dict[str, any]:
        """Get order book statistics."""
        best_bid, best_ask = self.get_bbo()
        spread = best_ask - best_bid if best_bid and best_ask else None
        
        return {
            "symbol": self.symbol,
            "best_bid": str(best_bid) if best_bid else None,
            "best_ask": str(best_ask) if best_ask else None,
            "spread": str(spread) if spread else None,
            "total_bid_quantity": str(self.total_bid_quantity),
            "total_ask_quantity": str(self.total_ask_quantity),
            "bid_levels": len(self.bids),
            "ask_levels": len(self.asks),
            "total_orders": len(self.orders),
            "last_trade_price": str(self.last_trade_price) if self.last_trade_price else None,
        }
