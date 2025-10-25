"""
REST API for the cryptocurrency matching engine.

This module provides HTTP endpoints for order submission, order book queries,
and system statistics following RESTful principles.
"""

import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Dict, Any, Optional
import json

from flask import Flask, request, jsonify, Response
from flask_cors import CORS

from ..core.matching_engine import MatchingEngine
from ..core.order import Order
from ..core.order_types import OrderType, OrderSide
from .validators import (
    validate_order_request,
    validate_symbol,
    validate_depth_request,
    validate_cancel_request,
    sanitize_string
)

logger = logging.getLogger(__name__)

# Global matching engine instance
matching_engine = MatchingEngine()


def create_app() -> Flask:
    """
    Create and configure the Flask application.
    
    Returns:
        Configured Flask application
    """
    app = Flask(__name__)
    CORS(app)  # Enable CORS for all routes
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Register routes
    register_routes(app)
    
    logger.info("REST API initialized")
    return app


def register_routes(app: Flask) -> None:
    """Register all API routes."""
    
    @app.route('/health', methods=['GET'])
    def health_check():
        """Health check endpoint."""
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.now(timezone.utc).isoformat() + 'Z',
            'version': '1.0.0'
        })
    
    @app.route('/orders', methods=['POST'])
    def submit_order():
        """
        Submit a new order to the matching engine.
        
        Request body:
        {
            "symbol": "BTC-USDT",
            "order_type": "limit",
            "side": "buy",
            "quantity": "1.0",
            "price": "50000.0"
        }
        """
        try:
            # Get and validate request data
            data = request.get_json()
            if not data:
                return jsonify({'error': 'Request body must be JSON'}), 400
            
            # Validate order request
            is_valid, error, validated_data = validate_order_request(data)
            if not is_valid:
                return jsonify({'error': error}), 400
            
            # Create order
            order = Order(
                symbol=validated_data['symbol'],
                order_type=validated_data['order_type'],
                side=validated_data['side'],
                quantity=validated_data['quantity'],
                price=validated_data['price']
            )
            
            # Submit to matching engine
            trades = matching_engine.submit_order(order)
            
            # Prepare response
            response_data = {
                'order_id': order.order_id,
                'status': order.status.value,
                'symbol': order.symbol,
                'order_type': order.order_type.value,
                'side': order.side.value,
                'quantity': str(order.quantity),
                'price': str(order.price) if order.price else None,
                'filled_quantity': str(order.filled_quantity),
                'remaining_quantity': str(order.remaining_quantity),
                'average_price': str(order.average_price),
                'timestamp': order.timestamp.isoformat() + 'Z',
                'trades': [trade.to_dict() for trade in trades]
            }
            
            logger.info(f"Order submitted: {order.order_id}")
            return jsonify(response_data), 200
            
        except Exception as e:
            logger.error(f"Error submitting order: {str(e)}")
            return jsonify({'error': 'Internal server error'}), 500
    
    @app.route('/orders/<order_id>', methods=['GET'])
    def get_order(order_id: str):
        """
        Get order details by ID.
        
        Query parameters:
        - symbol: Trading symbol (required)
        """
        try:
            symbol = request.args.get('symbol')
            if not symbol:
                return jsonify({'error': 'Symbol parameter is required'}), 400
            
            # Validate symbol
            is_valid, error = validate_symbol(symbol)
            if not is_valid:
                return jsonify({'error': error}), 400
            
            # Get order
            order = matching_engine.get_order(order_id, symbol)
            if not order:
                return jsonify({'error': 'Order not found'}), 404
            
            return jsonify(order.to_dict()), 200
            
        except Exception as e:
            logger.error(f"Error getting order: {str(e)}")
            return jsonify({'error': 'Internal server error'}), 500
    
    @app.route('/orders/<order_id>', methods=['DELETE'])
    def cancel_order(order_id: str):
        """
        Cancel an order.
        
        Request body:
        {
            "symbol": "BTC-USDT"
        }
        """
        try:
            data = request.get_json() or {}
            data['order_id'] = order_id
            
            # Validate cancel request
            is_valid, error, validated_data = validate_cancel_request(data)
            if not is_valid:
                return jsonify({'error': error}), 400
            
            # Cancel order
            success = matching_engine.cancel_order(
                validated_data['order_id'],
                validated_data['symbol']
            )
            
            if success:
                return jsonify({'message': 'Order cancelled successfully'}), 200
            else:
                return jsonify({'error': 'Order not found or already cancelled'}), 404
                
        except Exception as e:
            logger.error(f"Error cancelling order: {str(e)}")
            return jsonify({'error': 'Internal server error'}), 500
    
    @app.route('/orderbook/<symbol>', methods=['GET'])
    def get_order_book(symbol: str):
        """
        Get order book for a symbol.
        
        Query parameters:
        - depth: Number of price levels to return (default: 10, max: 100)
        """
        try:
            # Validate symbol
            is_valid, error = validate_symbol(symbol)
            if not is_valid:
                return jsonify({'error': error}), 400
            
            # Validate depth
            depth = request.args.get('depth', 10)
            is_valid, error, depth = validate_depth_request(symbol, depth)
            if not is_valid:
                return jsonify({'error': error}), 400
            
            # Get order book
            order_book = matching_engine.get_order_book(symbol)
            if not order_book:
                return jsonify({'error': 'Order book not found'}), 404
            
            # Get BBO and depth
            best_bid, best_ask = order_book.get_bbo()
            bids = order_book.get_order_book_depth('bids', depth)
            asks = order_book.get_order_book_depth('asks', depth)
            
            response_data = {
                'symbol': symbol,
                'timestamp': datetime.now(timezone.utc).isoformat() + 'Z',
                'best_bid': str(best_bid) if best_bid else None,
                'best_ask': str(best_ask) if best_ask else None,
                'spread': str(best_ask - best_bid) if best_bid and best_ask else None,
                'bids': bids,
                'asks': asks,
                'statistics': order_book.get_statistics()
            }
            
            return jsonify(response_data), 200
            
        except Exception as e:
            logger.error(f"Error getting order book: {str(e)}")
            return jsonify({'error': 'Internal server error'}), 500
    
    @app.route('/symbols', methods=['GET'])
    def get_symbols():
        """Get list of active trading symbols."""
        try:
            symbols = list(matching_engine.order_books.keys())
            return jsonify({
                'symbols': symbols,
                'count': len(symbols),
                'timestamp': datetime.now(timezone.utc).isoformat() + 'Z'
            }), 200
            
        except Exception as e:
            logger.error(f"Error getting symbols: {str(e)}")
            return jsonify({'error': 'Internal server error'}), 500
    
    @app.route('/statistics', methods=['GET'])
    def get_statistics():
        """Get engine statistics."""
        try:
            stats = matching_engine.get_statistics()
            return jsonify(stats), 200
            
        except Exception as e:
            logger.error(f"Error getting statistics: {str(e)}")
            return jsonify({'error': 'Internal server error'}), 500
    
    @app.route('/statistics/<symbol>', methods=['GET'])
    def get_symbol_statistics(symbol: str):
        """Get statistics for a specific symbol."""
        try:
            # Validate symbol
            is_valid, error = validate_symbol(symbol)
            if not is_valid:
                return jsonify({'error': error}), 400
            
            stats = matching_engine.get_symbol_statistics(symbol)
            if not stats:
                return jsonify({'error': 'Symbol not found'}), 404
            
            return jsonify(stats), 200
            
        except Exception as e:
            logger.error(f"Error getting symbol statistics: {str(e)}")
            return jsonify({'error': 'Internal server error'}), 500
    
    @app.errorhandler(404)
    def not_found(error):
        """Handle 404 errors."""
        return jsonify({'error': 'Endpoint not found'}), 404
    
    @app.errorhandler(405)
    def method_not_allowed(error):
        """Handle 405 errors."""
        return jsonify({'error': 'Method not allowed'}), 405
    
    @app.errorhandler(500)
    def internal_error(error):
        """Handle 500 errors."""
        logger.error(f"Internal server error: {str(error)}")
        return jsonify({'error': 'Internal server error'}), 500


def run_server(host: str = '0.0.0.0', port: int = 5000, debug: bool = False) -> None:
    """
    Run the REST API server.
    
    Args:
        host: Host to bind to
        port: Port to bind to
        debug: Enable debug mode
    """
    app = create_app()
    logger.info(f"Starting REST API server on {host}:{port}")
    app.run(host=host, port=port, debug=debug)


if __name__ == '__main__':
    run_server(debug=True)
