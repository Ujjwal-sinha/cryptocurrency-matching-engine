"""
Tests for the core matching engine functionality.

This module tests the matching engine's core functionality including
order processing, trade execution, and REG NMS compliance.
"""

import unittest
from decimal import Decimal
from datetime import datetime, timezone

from src.core.matching_engine import MatchingEngine
from src.core.order import Order
from src.core.order_types import OrderType, OrderSide, OrderStatus


class TestMatchingEngine(unittest.TestCase):
    """Test cases for the matching engine."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.engine = MatchingEngine()
        self.engine.add_order_book("BTC-USDT")
    
    def test_market_buy_order(self):
        """Test market buy order execution."""
        # Place a limit sell order first
        sell_order = Order(
            symbol="BTC-USDT",
            order_type=OrderType.LIMIT,
            side=OrderSide.SELL,
            quantity=Decimal('1.0'),
            price=Decimal('50000.0')
        )
        self.engine.submit_order(sell_order)
        
        # Place a market buy order
        buy_order = Order(
            symbol="BTC-USDT",
            order_type=OrderType.MARKET,
            side=OrderSide.BUY,
            quantity=Decimal('0.5')
        )
        
        trades = self.engine.submit_order(buy_order)
        
        # Assertions
        self.assertEqual(len(trades), 1)
        self.assertEqual(trades[0].price, Decimal('50000.0'))
        self.assertEqual(trades[0].quantity, Decimal('0.5'))
        self.assertEqual(trades[0].aggressor_side, OrderSide.BUY)
        self.assertEqual(buy_order.status, OrderStatus.FILLED)
        
        # Check sell order status in order book
        order_book = self.engine.get_order_book("BTC-USDT")
        book_sell_order = order_book.get_order(sell_order.order_id)
        self.assertIsNotNone(book_sell_order)
        self.assertEqual(book_sell_order.status, OrderStatus.PARTIALLY_FILLED)
    
    def test_market_sell_order(self):
        """Test market sell order execution."""
        # Place a limit buy order first
        buy_order = Order(
            symbol="BTC-USDT",
            order_type=OrderType.LIMIT,
            side=OrderSide.BUY,
            quantity=Decimal('1.0'),
            price=Decimal('50000.0')
        )
        self.engine.submit_order(buy_order)
        
        # Place a market sell order
        sell_order = Order(
            symbol="BTC-USDT",
            order_type=OrderType.MARKET,
            side=OrderSide.SELL,
            quantity=Decimal('0.5')
        )
        
        trades = self.engine.submit_order(sell_order)
        
        # Assertions
        self.assertEqual(len(trades), 1)
        self.assertEqual(trades[0].price, Decimal('50000.0'))
        self.assertEqual(trades[0].quantity, Decimal('0.5'))
        self.assertEqual(trades[0].aggressor_side, OrderSide.SELL)
        self.assertEqual(sell_order.status, OrderStatus.FILLED)
        
        # Check buy order status in order book
        order_book = self.engine.get_order_book("BTC-USDT")
        book_buy_order = order_book.get_order(buy_order.order_id)
        self.assertIsNotNone(book_buy_order)
        self.assertEqual(book_buy_order.status, OrderStatus.PARTIALLY_FILLED)
    
    def test_limit_order_resting(self):
        """Test limit order resting on the book."""
        # Place a limit buy order that won't match
        buy_order = Order(
            symbol="BTC-USDT",
            order_type=OrderType.LIMIT,
            side=OrderSide.BUY,
            quantity=Decimal('1.0'),
            price=Decimal('49000.0')  # Lower than any sell orders
        )
        
        trades = self.engine.submit_order(buy_order)
        
        # Assertions
        self.assertEqual(len(trades), 0)
        self.assertEqual(buy_order.status, OrderStatus.PENDING)
        
        # Check order book
        order_book = self.engine.get_order_book("BTC-USDT")
        best_bid, best_ask = order_book.get_bbo()
        self.assertEqual(best_bid, Decimal('49000.0'))
        self.assertIsNone(best_ask)
    
    def test_price_time_priority(self):
        """Test price-time priority matching."""
        # Place first limit sell order
        sell_order1 = Order(
            symbol="BTC-USDT",
            order_type=OrderType.LIMIT,
            side=OrderSide.SELL,
            quantity=Decimal('1.0'),
            price=Decimal('50000.0')
        )
        self.engine.submit_order(sell_order1)
        
        # Place second limit sell order at same price
        sell_order2 = Order(
            symbol="BTC-USDT",
            order_type=OrderType.LIMIT,
            side=OrderSide.SELL,
            quantity=Decimal('1.0'),
            price=Decimal('50000.0')
        )
        self.engine.submit_order(sell_order2)
        
        # Place market buy order for 1.5 units
        buy_order = Order(
            symbol="BTC-USDT",
            order_type=OrderType.MARKET,
            side=OrderSide.BUY,
            quantity=Decimal('1.5')
        )
        
        trades = self.engine.submit_order(buy_order)
        
        # Assertions - should match first order completely, second order partially
        self.assertEqual(len(trades), 2)
        self.assertEqual(trades[0].quantity, Decimal('1.0'))
        self.assertEqual(trades[1].quantity, Decimal('0.5'))
        self.assertEqual(trades[0].maker_order_id, sell_order1.order_id)
        self.assertEqual(trades[1].maker_order_id, sell_order2.order_id)
        
        # Check order statuses in order book
        order_book = self.engine.get_order_book("BTC-USDT")
        book_sell_order1 = order_book.get_order(sell_order1.order_id)
        book_sell_order2 = order_book.get_order(sell_order2.order_id)
        
        # First order should be filled, second should be partially filled
        self.assertIsNone(book_sell_order1)  # Should be removed from book
        self.assertIsNotNone(book_sell_order2)
        self.assertEqual(book_sell_order2.status, OrderStatus.PARTIALLY_FILLED)
    
    def test_ioc_order(self):
        """Test Immediate-or-Cancel order."""
        # Place a limit sell order
        sell_order = Order(
            symbol="BTC-USDT",
            order_type=OrderType.LIMIT,
            side=OrderSide.SELL,
            quantity=Decimal('1.0'),
            price=Decimal('50000.0')
        )
        self.engine.submit_order(sell_order)
        
        # Place IOC buy order for more than available
        ioc_order = Order(
            symbol="BTC-USDT",
            order_type=OrderType.IOC,
            side=OrderSide.BUY,
            quantity=Decimal('2.0'),
            price=Decimal('50000.0')
        )
        
        trades = self.engine.submit_order(ioc_order)
        
        # Assertions - should fill what's available and cancel the rest
        self.assertEqual(len(trades), 1)
        self.assertEqual(trades[0].quantity, Decimal('1.0'))
        self.assertEqual(ioc_order.status, OrderStatus.PARTIALLY_FILLED)
        self.assertEqual(ioc_order.filled_quantity, Decimal('1.0'))
    
    def test_fok_order_success(self):
        """Test Fill-or-Kill order that can be filled."""
        # Place a limit sell order
        sell_order = Order(
            symbol="BTC-USDT",
            order_type=OrderType.LIMIT,
            side=OrderSide.SELL,
            quantity=Decimal('1.0'),
            price=Decimal('50000.0')
        )
        self.engine.submit_order(sell_order)
        
        # Place FOK buy order for available quantity
        fok_order = Order(
            symbol="BTC-USDT",
            order_type=OrderType.FOK,
            side=OrderSide.BUY,
            quantity=Decimal('1.0'),
            price=Decimal('50000.0')
        )
        
        trades = self.engine.submit_order(fok_order)
        
        # Assertions - should fill completely
        self.assertEqual(len(trades), 1)
        self.assertEqual(trades[0].quantity, Decimal('1.0'))
        self.assertEqual(fok_order.status, OrderStatus.FILLED)
    
    def test_fok_order_failure(self):
        """Test Fill-or-Kill order that cannot be filled."""
        # Place a limit sell order
        sell_order = Order(
            symbol="BTC-USDT",
            order_type=OrderType.LIMIT,
            side=OrderSide.SELL,
            quantity=Decimal('1.0'),
            price=Decimal('50000.0')
        )
        self.engine.submit_order(sell_order)
        
        # Place FOK buy order for more than available
        fok_order = Order(
            symbol="BTC-USDT",
            order_type=OrderType.FOK,
            side=OrderSide.BUY,
            quantity=Decimal('2.0'),
            price=Decimal('50000.0')
        )
        
        trades = self.engine.submit_order(fok_order)
        
        # Assertions - should reject completely
        self.assertEqual(len(trades), 0)
        self.assertEqual(fok_order.status, OrderStatus.REJECTED)
    
    def test_order_cancellation(self):
        """Test order cancellation."""
        # Place a limit order
        order = Order(
            symbol="BTC-USDT",
            order_type=OrderType.LIMIT,
            side=OrderSide.BUY,
            quantity=Decimal('1.0'),
            price=Decimal('50000.0')
        )
        self.engine.submit_order(order)
        
        # Cancel the order
        success = self.engine.cancel_order(order.order_id, "BTC-USDT")
        
        # Assertions
        self.assertTrue(success)
        
        # Check order status in order book (should be cancelled)
        order_book = self.engine.get_order_book("BTC-USDT")
        book_order = order_book.get_order(order.order_id)
        self.assertIsNone(book_order)  # Should be removed from book
        
        # Check order book is empty
        order_book = self.engine.get_order_book("BTC-USDT")
        best_bid, best_ask = order_book.get_bbo()
        self.assertIsNone(best_bid)
        self.assertIsNone(best_ask)
    
    def test_multiple_symbols(self):
        """Test handling multiple trading symbols."""
        # Add another order book
        self.engine.add_order_book("ETH-USDT")
        
        # Place orders on different symbols
        btc_order = Order(
            symbol="BTC-USDT",
            order_type=OrderType.LIMIT,
            side=OrderSide.BUY,
            quantity=Decimal('1.0'),
            price=Decimal('50000.0')
        )
        
        eth_order = Order(
            symbol="ETH-USDT",
            order_type=OrderType.LIMIT,
            side=OrderSide.BUY,
            quantity=Decimal('10.0'),
            price=Decimal('3000.0')
        )
        
        self.engine.submit_order(btc_order)
        self.engine.submit_order(eth_order)
        
        # Check both order books
        btc_book = self.engine.get_order_book("BTC-USDT")
        eth_book = self.engine.get_order_book("ETH-USDT")
        
        btc_bid, btc_ask = btc_book.get_bbo()
        eth_bid, eth_ask = eth_book.get_bbo()
        
        self.assertEqual(btc_bid, Decimal('50000.0'))
        self.assertEqual(eth_bid, Decimal('3000.0'))
    
    def test_invalid_order_validation(self):
        """Test order validation."""
        # Test invalid quantity - this should raise an exception during Order creation
        with self.assertRaises(ValueError):
            invalid_order = Order(
                symbol="BTC-USDT",
                order_type=OrderType.LIMIT,
                side=OrderSide.BUY,
                quantity=Decimal('-1.0'),  # Negative quantity
                price=Decimal('50000.0')
            )
    
    def test_statistics(self):
        """Test engine statistics."""
        # Submit some orders
        order1 = Order(
            symbol="BTC-USDT",
            order_type=OrderType.LIMIT,
            side=OrderSide.BUY,
            quantity=Decimal('1.0'),
            price=Decimal('50000.0')
        )
        
        order2 = Order(
            symbol="BTC-USDT",
            order_type=OrderType.LIMIT,
            side=OrderSide.SELL,
            quantity=Decimal('1.0'),
            price=Decimal('50000.0')
        )
        
        self.engine.submit_order(order1)
        trades = self.engine.submit_order(order2)
        
        # Check statistics
        stats = self.engine.get_statistics()
        self.assertEqual(stats['total_orders_processed'], 2)
        self.assertEqual(stats['total_trades_executed'], 1)
        self.assertGreater(Decimal(stats['total_volume']), 0)


if __name__ == '__main__':
    unittest.main()
