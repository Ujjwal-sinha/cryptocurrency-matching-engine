"""
Core matching engine implementing REG NMS principles.

This module contains the main MatchingEngine class that orchestrates
order matching, trade execution, and market data dissemination.
"""

import logging
from decimal import Decimal
from typing import Dict, List, Optional, Callable, Any
from datetime import datetime, timezone

from .order import Order, Trade
from .order_book import OrderBook
from .order_types import OrderType, OrderSide, OrderStatus

logger = logging.getLogger(__name__)


class MatchingEngine:
    """
    High-performance matching engine implementing REG NMS principles.
    
    Features:
    - Price-time priority matching
    - Internal order protection (no trade-throughs)
    - Support for Market, Limit, IOC, and FOK orders
    - Real-time trade execution and market data
    - Comprehensive logging and monitoring
    """
  
    def __init__(self):
        """Initialize the matching engine."""
        self.order_books: Dict[str, OrderBook] = {}
     
        # Callbacks for real-time data
        self.trade_callbacks: List[Callable[[Trade], None]] = []
        self.market_data_callbacks: List[Callable[[Dict[str, Any]], None]] = []
        
        # Statistics
        self.total_orders_processed = 0
        self.total_trades_executed = 0
        self.total_volume = Decimal('0')
        
        # Performance monitoring
        self.start_time = datetime.now(timezone.utc)
        
        logger.info("Matching engine initialized")
    
    def add_order_book(self, symbol: str) -> OrderBook:
        """
        Add a new order book for a trading symbol.
        
        Args:
            symbol: Trading symbol (e.g., "BTC-USDT")
            
        Returns:
            The created OrderBook instance
        """
        if symbol in self.order_books:
            logger.warning(f"Order book for {symbol} already exists")
            return self.order_books[symbol]
        
        order_book = OrderBook(symbol)
        self.order_books[symbol] = order_book
        logger.info(f"Added order book for {symbol}")
        
        return order_book
    
    def submit_order(self, order: Order) -> List[Trade]:
        """
        Submit an order to the matching engine.
        
        Args:
            order: The order to submit
            
        Returns:
            List of trades executed
        """
        try:
            # Validate order
            if not self._validate_order(order):
                return []
            
            # Ensure order book exists
            if order.symbol not in self.order_books:
                self.add_order_book(order.symbol)
            
            order_book = self.order_books[order.symbol]
            
            # Process order based on type
            trades = self._process_order(order, order_book)
            
            # Update statistics
            self.total_orders_processed += 1
            self.total_trades_executed += len(trades)
            for trade in trades:
                self.total_volume += trade.notional_value
            
            # Notify callbacks
            self._notify_trades(trades)
            self._notify_market_data(order.symbol)
            
            logger.info(f"Processed order {order.order_id}: {len(trades)} trades executed")
            
            return trades
            
        except Exception as e:
            logger.error(f"Error processing order {order.order_id}: {str(e)}")
            order.status = OrderStatus.REJECTED
            return []
    
    def _validate_order(self, order: Order) -> bool:
        """
        Validate order parameters.
        
        Args:
            order: Order to validate
            
        Returns:
            True if valid, False otherwise
        """
        try:
            # Basic validation
            if not order.symbol:
                logger.error("Order symbol cannot be empty")
                return False
            
            if order.quantity <= 0:
                logger.error(f"Order quantity must be positive: {order.quantity}")
                return False
            
            # Order type specific validation
            if order.order_type in [OrderType.LIMIT, OrderType.IOC, OrderType.FOK]:
                if order.price is None or order.price <= 0:
                    logger.error(f"Price required for {order.order_type.value} orders: {order.price}")
                    return False
            
            # IOC and FOK specific validation
            if order.order_type == OrderType.FOK:
                if not self._can_fill_fully(order):
                    logger.warning(f"FOK order {order.order_id} cannot be filled fully")
                    order.status = OrderStatus.REJECTED
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Order validation error: {str(e)}")
            return False
    
    def _process_order(self, order: Order, order_book: OrderBook) -> List[Trade]:
        """
        Process order based on its type.
        
        Args:
            order: Order to process
            order_book: Target order book
            
        Returns:
            List of executed trades
        """
        if order.order_type == OrderType.MARKET:
            return self._handle_market_order(order, order_book)
        elif order.order_type == OrderType.LIMIT:
            return self._handle_limit_order(order, order_book)
        elif order.order_type == OrderType.IOC:
            return self._handle_ioc_order(order, order_book)
        elif order.order_type == OrderType.FOK:
            return self._handle_fok_order(order, order_book)
        else:
            logger.error(f"Unknown order type: {order.order_type}")
            order.status = OrderStatus.REJECTED
            return []
    
    def _handle_market_order(self, order: Order, order_book: OrderBook) -> List[Trade]:
        """Handle market order execution."""
        logger.debug(f"Processing market order {order.order_id}")
        trades = order_book.add_order(order)
        
        if trades:
            order.status = OrderStatus.FILLED if order.is_fully_filled else OrderStatus.PARTIALLY_FILLED
        else:
            order.status = OrderStatus.REJECTED
            logger.warning(f"Market order {order.order_id} could not be executed")
        
        return trades
    
    def _handle_limit_order(self, order: Order, order_book: OrderBook) -> List[Trade]:
        """Handle limit order execution."""
        logger.debug(f"Processing limit order {order.order_id}")
        trades = order_book.add_order(order)
        
        if trades:
            if order.is_fully_filled:
                order.status = OrderStatus.FILLED
            else:
                order.status = OrderStatus.PARTIALLY_FILLED
        else:
            # Order rests on the book
            order.status = OrderStatus.PENDING
        
        return trades
    
    def _handle_ioc_order(self, order: Order, order_book: OrderBook) -> List[Trade]:
        """Handle Immediate-or-Cancel order execution."""
        logger.debug(f"Processing IOC order {order.order_id}")
        trades = order_book.add_order(order)
        
        if trades:
            if order.is_fully_filled:
                order.status = OrderStatus.FILLED
            else:
                order.status = OrderStatus.PARTIALLY_FILLED
        else:
            # IOC order cannot rest on book
            order.status = OrderStatus.CANCELLED
            logger.info(f"IOC order {order.order_id} cancelled - no immediate execution")
        
        return trades
    
    def _handle_fok_order(self, order: Order, order_book: OrderBook) -> List[Trade]:
        """Handle Fill-or-Kill order execution."""
        logger.debug(f"Processing FOK order {order.order_id}")
        
        # Check if order can be filled completely
        if not self._can_fill_fully(order):
            order.status = OrderStatus.REJECTED
            logger.info(f"FOK order {order.order_id} rejected - cannot fill fully")
            return []
        
        # Execute the order
        trades = order_book.add_order(order)
        
        if trades and order.is_fully_filled:
            order.status = OrderStatus.FILLED
        else:
            order.status = OrderStatus.REJECTED
            logger.warning(f"FOK order {order.order_id} failed to fill completely")
        
        return trades
    
    def _can_fill_fully(self, order: Order) -> bool:
        """
        Check if an order can be filled completely.
        
        Args:
            order: Order to check
            
        Returns:
            True if order can be filled completely
        """
        if order.symbol not in self.order_books:
            return False
        
        order_book = self.order_books[order.symbol]
        
        if order.side == OrderSide.BUY:
            # Check if we have enough ask volume at or below the price
            available_quantity = Decimal('0')
            for ask_price in sorted(order_book.asks.keys()):
                if ask_price <= order.price:
                    available_quantity += order_book.asks[ask_price].total_quantity
                    if available_quantity >= order.quantity:
                        return True
        else:
            # Check if we have enough bid volume at or above the price
            available_quantity = Decimal('0')
            for bid_price in sorted(order_book.bids.keys(), reverse=True):
                if bid_price >= order.price:
                    available_quantity += order_book.bids[bid_price].total_quantity
                    if available_quantity >= order.quantity:
                        return True
        
        return False
    
    def cancel_order(self, order_id: str, symbol: str) -> bool:
        """
        Cancel an order.
        
        Args:
            order_id: ID of order to cancel
            symbol: Trading symbol
            
        Returns:
            True if order was cancelled
        """
        if symbol not in self.order_books:
            logger.error(f"Order book for {symbol} not found")
            return False
        
        order_book = self.order_books[symbol]
        success = order_book.cancel_order(order_id)
        
        if success:
            logger.info(f"Cancelled order {order_id}")
            self._notify_market_data(symbol)
        else:
            logger.warning(f"Failed to cancel order {order_id}")
        
        return success
    
    def get_order_book(self, symbol: str) -> Optional[OrderBook]:
        """Get order book for a symbol."""
        return self.order_books.get(symbol)
    
    def get_bbo(self, symbol: str) -> tuple[Optional[Decimal], Optional[Decimal]]:
        """Get Best Bid and Offer for a symbol."""
        if symbol not in self.order_books:
            return None, None
        
        return self.order_books[symbol].get_bbo()
    
    def get_order_book_depth(self, symbol: str, side: str, depth: int = 10) -> List[List[str]]:
        """Get order book depth for a symbol."""
        if symbol not in self.order_books:
            return []
        
        return self.order_books[symbol].get_order_book_depth(side, depth)
    
    def get_order(self, order_id: str, symbol: str) -> Optional[Order]:
        """Get order by ID and symbol."""
        if symbol not in self.order_books:
            return None
        
        return self.order_books[symbol].get_order(order_id)
    
    def add_trade_callback(self, callback: Callable[[Trade], None]) -> None:
        """Add callback for trade executions."""
        self.trade_callbacks.append(callback)
    
    def add_market_data_callback(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        """Add callback for market data updates."""
        self.market_data_callbacks.append(callback)
    
    def _notify_trades(self, trades: List[Trade]) -> None:
        """Notify trade callbacks."""
        for trade in trades:
            for callback in self.trade_callbacks:
                try:
                    callback(trade)
                except Exception as e:
                    logger.error(f"Error in trade callback: {str(e)}")
    
    def _notify_market_data(self, symbol: str) -> None:
        """Notify market data callbacks."""
        if symbol not in self.order_books:
            return
        
        order_book = self.order_books[symbol]
        best_bid, best_ask = order_book.get_bbo()
        
        market_data = {
            "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
            "symbol": symbol,
            "bids": order_book.get_order_book_depth("bids", 10),
            "asks": order_book.get_order_book_depth("asks", 10),
            "best_bid": str(best_bid) if best_bid else None,
            "best_ask": str(best_ask) if best_ask else None,
        }
        
        for callback in self.market_data_callbacks:
            try:
                callback(market_data)
            except Exception as e:
                logger.error(f"Error in market data callback: {str(e)}")
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get engine statistics."""
        uptime = datetime.now(timezone.utc) - self.start_time
        
        return {
            "uptime_seconds": uptime.total_seconds(),
            "total_orders_processed": self.total_orders_processed,
            "total_trades_executed": self.total_trades_executed,
            "total_volume": str(self.total_volume),
            "active_symbols": list(self.order_books.keys()),
            "orders_per_second": self.total_orders_processed / max(uptime.total_seconds(), 1),
            "trades_per_second": self.total_trades_executed / max(uptime.total_seconds(), 1),
        }
    
    def get_symbol_statistics(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get statistics for a specific symbol."""
        if symbol not in self.order_books:
            return None
        
        return self.order_books[symbol].get_statistics()
