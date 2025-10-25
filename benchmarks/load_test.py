"""
Load testing and benchmarking for the matching engine.

This module provides comprehensive load testing to verify
performance requirements and identify bottlenecks.
"""

import asyncio
import random
import time
from decimal import Decimal
from typing import List, Dict, Any
import statistics

from src.core.matching_engine import MatchingEngine
from src.core.order import Order
from src.core.order_types import OrderType, OrderSide
from src.utils.performance import get_performance_monitor


class LoadTester:
    """
    Load testing utility for the matching engine.
    """
    
    def __init__(self, matching_engine: MatchingEngine):
        """Initialize load tester."""
        self.engine = matching_engine
        self.performance_monitor = get_performance_monitor()
        self.results = []
    
    def generate_random_orders(self, count: int, symbol: str = "BTC-USDT") -> List[Order]:
        """
        Generate random orders for testing.
        
        Args:
            count: Number of orders to generate
            symbol: Trading symbol
            
        Returns:
            List of random orders
        """
        orders = []
        
        for i in range(count):
            # Random order type and side
            order_type = random.choice([OrderType.LIMIT, OrderType.MARKET, OrderType.IOC, OrderType.FOK])
            side = random.choice([OrderSide.BUY, OrderSide.SELL])
            
            # Random quantity
            quantity = Decimal(str(round(random.uniform(0.1, 10.0), 8)))
            
            # Random price for limit orders
            price = None
            if order_type in [OrderType.LIMIT, OrderType.IOC, OrderType.FOK]:
                price = Decimal(str(round(random.uniform(40000, 60000), 2)))
            
            order = Order(
                order_id=f"load_test_{i}",
                symbol=symbol,
                order_type=order_type,
                side=side,
                quantity=quantity,
                price=price
            )
            orders.append(order)
        
        return orders
    
    def benchmark_order_processing(self, order_count: int, symbol: str = "BTC-USDT") -> Dict[str, Any]:
        """
        Benchmark order processing performance.
        
        Args:
            order_count: Number of orders to process
            symbol: Trading symbol
            
        Returns:
            Performance metrics
        """
        print(f"Benchmarking {order_count} orders for {symbol}...")
        
        # Generate random orders
        orders = self.generate_random_orders(order_count, symbol)
        
        # Measure processing time
        start_time = time.perf_counter()
        total_trades = 0
        
        for order in orders:
            trades = self.engine.submit_order(order)
            total_trades += len(trades)
        
        end_time = time.perf_counter()
        
        # Calculate metrics
        total_time = end_time - start_time
        orders_per_second = order_count / total_time
        trades_per_second = total_trades / total_time
        
        # Get system stats
        system_stats = self.performance_monitor.get_system_stats()
        
        results = {
            "order_count": order_count,
            "total_time_seconds": total_time,
            "orders_per_second": orders_per_second,
            "trades_executed": total_trades,
            "trades_per_second": trades_per_second,
            "average_latency_ms": (total_time / order_count) * 1000,
            "memory_usage_mb": system_stats.get("memory_rss_mb", 0),
            "cpu_percent": system_stats.get("cpu_percent", 0),
        }
        
        self.results.append(results)
        return results
    
    def benchmark_concurrent_orders(self, order_count: int, symbol: str = "BTC-USDT") -> Dict[str, Any]:
        """
        Benchmark concurrent order processing.
        
        Args:
            order_count: Number of orders to process
            symbol: Trading symbol
            
        Returns:
            Performance metrics
        """
        print(f"Benchmarking {order_count} concurrent orders for {symbol}...")
        
        # Generate random orders
        orders = self.generate_random_orders(order_count, symbol)
        
        # Process orders concurrently
        start_time = time.perf_counter()
        
        # Simulate concurrent processing by batching
        batch_size = 100
        total_trades = 0
        
        for i in range(0, order_count, batch_size):
            batch = orders[i:i + batch_size]
            
            # Process batch
            for order in batch:
                trades = self.engine.submit_order(order)
                total_trades += len(trades)
        
        end_time = time.perf_counter()
        
        # Calculate metrics
        total_time = end_time - start_time
        orders_per_second = order_count / total_time
        trades_per_second = total_trades / total_time
        
        results = {
            "order_count": order_count,
            "total_time_seconds": total_time,
            "orders_per_second": orders_per_second,
            "trades_executed": total_trades,
            "trades_per_second": trades_per_second,
            "average_latency_ms": (total_time / order_count) * 1000,
        }
        
        self.results.append(results)
        return results
    
    def benchmark_market_data_generation(self, symbol: str = "BTC-USDT", duration_seconds: int = 60) -> Dict[str, Any]:
        """
        Benchmark market data generation performance.
        
        Args:
            symbol: Trading symbol
            duration_seconds: Test duration in seconds
            
        Returns:
            Performance metrics
        """
        print(f"Benchmarking market data generation for {symbol} for {duration_seconds} seconds...")
        
        # Ensure order book exists
        if symbol not in self.engine.order_books:
            self.engine.add_order_book(symbol)
        
        # Generate orders continuously
        start_time = time.time()
        order_count = 0
        trade_count = 0
        
        while time.time() - start_time < duration_seconds:
            # Generate random order
            orders = self.generate_random_orders(1, symbol)
            order = orders[0]
            
            # Submit order
            trades = self.engine.submit_order(order)
            
            order_count += 1
            trade_count += len(trades)
        
        end_time = time.time()
        total_time = end_time - start_time
        
        results = {
            "duration_seconds": total_time,
            "orders_processed": order_count,
            "trades_executed": trade_count,
            "orders_per_second": order_count / total_time,
            "trades_per_second": trade_count / total_time,
        }
        
        self.results.append(results)
        return results
    
    def stress_test(self, max_orders: int = 10000, symbol: str = "BTC-USDT") -> Dict[str, Any]:
        """
        Stress test the matching engine.
        
        Args:
            max_orders: Maximum number of orders to process
            symbol: Trading symbol
            
        Returns:
            Stress test results
        """
        print(f"Stress testing with up to {max_orders} orders for {symbol}...")
        
        # Generate orders
        orders = self.generate_random_orders(max_orders, symbol)
        
        # Process orders and measure performance
        start_time = time.perf_counter()
        successful_orders = 0
        failed_orders = 0
        total_trades = 0
        
        for order in orders:
            try:
                trades = self.engine.submit_order(order)
                successful_orders += 1
                total_trades += len(trades)
            except Exception as e:
                failed_orders += 1
                print(f"Order failed: {str(e)}")
        
        end_time = time.perf_counter()
        total_time = end_time - start_time
        
        # Get final system stats
        system_stats = self.performance_monitor.get_system_stats()
        
        results = {
            "max_orders": max_orders,
            "successful_orders": successful_orders,
            "failed_orders": failed_orders,
            "success_rate": successful_orders / max_orders,
            "total_trades": total_trades,
            "total_time_seconds": total_time,
            "orders_per_second": successful_orders / total_time,
            "trades_per_second": total_trades / total_time,
            "memory_usage_mb": system_stats.get("memory_rss_mb", 0),
            "memory_growth_mb": system_stats.get("memory_growth_mb", 0),
            "cpu_percent": system_stats.get("cpu_percent", 0),
        }
        
        self.results.append(results)
        return results
    
    def get_summary(self) -> Dict[str, Any]:
        """Get summary of all benchmark results."""
        if not self.results:
            return {"message": "No benchmark results available"}
        
        # Calculate aggregate statistics
        orders_per_second = [r.get("orders_per_second", 0) for r in self.results]
        trades_per_second = [r.get("trades_per_second", 0) for r in self.results]
        latencies = [r.get("average_latency_ms", 0) for r in self.results]
        
        return {
            "total_benchmarks": len(self.results),
            "orders_per_second": {
                "min": min(orders_per_second) if orders_per_second else 0,
                "max": max(orders_per_second) if orders_per_second else 0,
                "avg": statistics.mean(orders_per_second) if orders_per_second else 0,
            },
            "trades_per_second": {
                "min": min(trades_per_second) if trades_per_second else 0,
                "max": max(trades_per_second) if trades_per_second else 0,
                "avg": statistics.mean(trades_per_second) if trades_per_second else 0,
            },
            "latency_ms": {
                "min": min(latencies) if latencies else 0,
                "max": max(latencies) if latencies else 0,
                "avg": statistics.mean(latencies) if latencies else 0,
            },
            "results": self.results
        }


def run_benchmarks():
    """Run comprehensive benchmarks."""
    print("Starting matching engine benchmarks...")
    
    # Initialize matching engine
    engine = MatchingEngine()
    engine.add_order_book("BTC-USDT")
    
    # Create load tester
    tester = LoadTester(engine)
    
    # Run benchmarks
    print("\n=== Order Processing Benchmarks ===")
    tester.benchmark_order_processing(1000, "BTC-USDT")
    tester.benchmark_order_processing(5000, "BTC-USDT")
    tester.benchmark_order_processing(10000, "BTC-USDT")
    
    print("\n=== Concurrent Processing Benchmarks ===")
    tester.benchmark_concurrent_orders(1000, "BTC-USDT")
    tester.benchmark_concurrent_orders(5000, "BTC-USDT")
    
    print("\n=== Market Data Generation Benchmarks ===")
    tester.benchmark_market_data_generation("BTC-USDT", 30)
    
    print("\n=== Stress Tests ===")
    tester.stress_test(10000, "BTC-USDT")
    
    # Print summary
    print("\n=== Benchmark Summary ===")
    summary = tester.get_summary()
    print(f"Total benchmarks: {summary['total_benchmarks']}")
    print(f"Orders per second - Min: {summary['orders_per_second']['min']:.2f}, "
          f"Max: {summary['orders_per_second']['max']:.2f}, "
          f"Avg: {summary['orders_per_second']['avg']:.2f}")
    print(f"Trades per second - Min: {summary['trades_per_second']['min']:.2f}, "
          f"Max: {summary['trades_per_second']['max']:.2f}, "
          f"Avg: {summary['trades_per_second']['avg']:.2f}")
    print(f"Latency (ms) - Min: {summary['latency_ms']['min']:.2f}, "
          f"Max: {summary['latency_ms']['max']:.2f}, "
          f"Avg: {summary['latency_ms']['avg']:.2f}")
    
    return summary


if __name__ == "__main__":
    run_benchmarks()
