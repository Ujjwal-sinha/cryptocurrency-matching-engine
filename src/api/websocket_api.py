"""
WebSocket API for real-time market data and trade feeds.

This module provides WebSocket endpoints for streaming real-time
market data, trade executions, and order book updates.
"""
import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Set, Dict, Any, Optional, Callable
import websockets
from websockets.legacy.server import WebSocketServerProtocol

from ..core.matching_engine import MatchingEngine
from ..core.order import Trade
from .validators import validate_symbol

logger = logging.getLogger(__name__)


class WebSocketServer:
    """
    WebSocket server for real-time data streaming.
    
    Handles multiple client connections and broadcasts market data
    and trade executions to subscribed clients.
    """
    
    def __init__(self, matching_engine: MatchingEngine, host: str = 'localhost', port: int = 8765):
        """
        Initialize WebSocket server.
        
        Args:
            matching_engine: Matching engine instance
            host: Host to bind to
            port: Port to bind to
        """
        self.matching_engine = matching_engine
        self.host = host
        self.port = port
        
        # Client management
        self.clients: Set[WebSocketServerProtocol] = set()
        self.subscriptions: Dict[WebSocketServerProtocol, Set[str]] = {}
        
        # Register callbacks
        self.matching_engine.add_trade_callback(self._on_trade)
        self.matching_engine.add_market_data_callback(self._on_market_data)
        
        logger.info(f"WebSocket server initialized on {host}:{port}")
    
    async def start(self) -> None:
        """Start the WebSocket server."""
        logger.info(f"Starting WebSocket server on {self.host}:{self.port}")
        
        async with websockets.serve(
            self._handle_client,
            self.host,
            self.port,
            ping_interval=20,
            ping_timeout=10,
            close_timeout=10
        ):
            await asyncio.Future()  # Run forever
    
    async def _handle_client(self, websocket: WebSocketServerProtocol, path: str) -> None:
        """
        Handle new client connection.
        
        Args:
            websocket: WebSocket connection
            path: Request path
        """
        client_address = f"{websocket.remote_address[0]}:{websocket.remote_address[1]}"
        logger.info(f"Client connected: {client_address}")
        
        # Add client to tracking
        self.clients.add(websocket)
        self.subscriptions[websocket] = set()
        
        try:
            # Send welcome message
            await self._send_message(websocket, {
                'type': 'connection',
                'status': 'connected',
                'timestamp': datetime.now(timezone.utc).isoformat() + 'Z',
                'message': 'Connected to matching engine WebSocket'
            })
            
            # Handle messages from client
            async for message in websocket:
                await self._handle_message(websocket, message)
                
        except websockets.exceptions.ConnectionClosed:
            logger.info(f"Client disconnected: {client_address}")
        except Exception as e:
            logger.error(f"Error handling client {client_address}: {str(e)}")
        finally:
            # Clean up client
            self.clients.discard(websocket)
            self.subscriptions.pop(websocket, None)
    
    async def _handle_message(self, websocket: WebSocketServerProtocol, message: str) -> None:
        """
        Handle message from client.
        
        Args:
            websocket: WebSocket connection
            message: Message from client
        """
        try:
            data = json.loads(message)
            message_type = data.get('type', '').lower()
            
            if message_type == 'subscribe':
                await self._handle_subscribe(websocket, data)
            elif message_type == 'unsubscribe':
                await self._handle_unsubscribe(websocket, data)
            elif message_type == 'ping':
                await self._handle_ping(websocket, data)
            elif message_type == 'get_orderbook':
                await self._handle_get_orderbook(websocket, data)
            else:
                await self._send_error(websocket, f"Unknown message type: {message_type}")
                
        except json.JSONDecodeError:
            await self._send_error(websocket, "Invalid JSON format")
        except Exception as e:
            logger.error(f"Error handling message: {str(e)}")
            await self._send_error(websocket, f"Error processing message: {str(e)}")
    
    async def _handle_subscribe(self, websocket: WebSocketServerProtocol, data: Dict[str, Any]) -> None:
        """Handle subscription request."""
        symbol = data.get('symbol', '').upper()
        
        if not symbol:
            await self._send_error(websocket, "Symbol is required for subscription")
            return
        
        # Validate symbol
        is_valid, error = validate_symbol(symbol)
        if not is_valid:
            await self._send_error(websocket, error)
            return
        
        # Add to subscriptions
        self.subscriptions[websocket].add(symbol)
        
        # Send confirmation
        await self._send_message(websocket, {
            'type': 'subscription',
            'status': 'subscribed',
            'symbol': symbol,
            'timestamp': datetime.now(timezone.utc).isoformat() + 'Z'
        })
        
        # Send current order book
        await self._send_orderbook_update(websocket, symbol)
        
        logger.info(f"Client subscribed to {symbol}")
    
    async def _handle_unsubscribe(self, websocket: WebSocketServerProtocol, data: Dict[str, Any]) -> None:
        """Handle unsubscription request."""
        symbol = data.get('symbol', '').upper()
        
        if symbol:
            self.subscriptions[websocket].discard(symbol)
            await self._send_message(websocket, {
                'type': 'subscription',
                'status': 'unsubscribed',
                'symbol': symbol,
                'timestamp': datetime.now(timezone.utc).isoformat() + 'Z'
            })
        else:
            # Unsubscribe from all
            self.subscriptions[websocket].clear()
            await self._send_message(websocket, {
                'type': 'subscription',
                'status': 'unsubscribed_all',
                'timestamp': datetime.now(timezone.utc).isoformat() + 'Z'
            })
        
        logger.info(f"Client unsubscribed from {symbol or 'all'}")
    
    async def _handle_ping(self, websocket: WebSocketServerProtocol, data: Dict[str, Any]) -> None:
        """Handle ping request."""
        await self._send_message(websocket, {
            'type': 'pong',
            'timestamp': datetime.now(timezone.utc).isoformat() + 'Z'
        })
    
    async def _handle_get_orderbook(self, websocket: WebSocketServerProtocol, data: Dict[str, Any]) -> None:
        """Handle get orderbook request."""
        symbol = data.get('symbol', '').upper()
        depth = data.get('depth', 10)
        
        if not symbol:
            await self._send_error(websocket, "Symbol is required")
            return
        
        # Validate symbol
        is_valid, error = validate_symbol(symbol)
        if not is_valid:
            await self._send_error(websocket, error)
            return
        
        # Send order book
        await self._send_orderbook_update(websocket, symbol, depth)
    
    async def _send_orderbook_update(self, websocket: WebSocketServerProtocol, symbol: str, depth: int = 10) -> None:
        """Send order book update to client."""
        try:
            order_book = self.matching_engine.get_order_book(symbol)
            if not order_book:
                await self._send_error(websocket, f"Order book not found for {symbol}")
                return
            
            best_bid, best_ask = order_book.get_bbo()
            bids = order_book.get_order_book_depth('bids', depth)
            asks = order_book.get_order_book_depth('asks', depth)
            
            await self._send_message(websocket, {
                'type': 'orderbook',
                'symbol': symbol,
                'timestamp': datetime.now(timezone.utc).isoformat() + 'Z',
                'bids': bids,
                'asks': asks,
                'best_bid': str(best_bid) if best_bid else None,
                'best_ask': str(best_ask) if best_ask else None,
                'spread': str(best_ask - best_bid) if best_bid and best_ask else None
            })
            
        except Exception as e:
            logger.error(f"Error sending order book update: {str(e)}")
            await self._send_error(websocket, f"Error getting order book: {str(e)}")
    
    async def _send_message(self, websocket: WebSocketServerProtocol, message: Dict[str, Any]) -> None:
        """Send message to client."""
        try:
            await websocket.send(json.dumps(message))
        except websockets.exceptions.ConnectionClosed:
            logger.debug("Client connection closed while sending message")
        except Exception as e:
            logger.error(f"Error sending message: {str(e)}")
    
    async def _send_error(self, websocket: WebSocketServerProtocol, error_message: str) -> None:
        """Send error message to client."""
        await self._send_message(websocket, {
            'type': 'error',
            'message': error_message,
            'timestamp': datetime.now(timezone.utc).isoformat() + 'Z'
        })
    
    def _on_trade(self, trade: Trade) -> None:
        """Handle trade execution callback."""
        asyncio.create_task(self._broadcast_trade(trade))
    
    def _on_market_data(self, market_data: Dict[str, Any]) -> None:
        """Handle market data callback."""
        asyncio.create_task(self._broadcast_market_data(market_data))
    
    async def _broadcast_trade(self, trade: Trade) -> None:
        """Broadcast trade to subscribed clients."""
        if not self.clients:
            return
        
        trade_data = {
            'type': 'trade',
            'timestamp': trade.timestamp.isoformat() + 'Z',
            'symbol': trade.symbol,
            'trade_id': trade.trade_id,
            'price': str(trade.price),
            'quantity': str(trade.quantity),
            'aggressor_side': trade.aggressor_side.value,
            'maker_order_id': trade.maker_order_id,
            'taker_order_id': trade.taker_order_id,
            'notional_value': str(trade.notional_value)
        }
        
        # Send to clients subscribed to this symbol
        tasks = []
        for websocket in self.clients.copy():
            if trade.symbol in self.subscriptions.get(websocket, set()):
                tasks.append(self._send_message(websocket, trade_data))
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _broadcast_market_data(self, market_data: Dict[str, Any]) -> None:
        """Broadcast market data to subscribed clients."""
        if not self.clients:
            return
        
        symbol = market_data.get('symbol')
        if not symbol:
            return
        
        # Send to clients subscribed to this symbol
        tasks = []
        for websocket in self.clients.copy():
            if symbol in self.subscriptions.get(websocket, set()):
                tasks.append(self._send_message(websocket, market_data))
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
    
    def get_client_count(self) -> int:
        """Get number of connected clients."""
        return len(self.clients)
    
    def get_subscription_count(self) -> Dict[str, int]:
        """Get subscription counts by symbol."""
        counts = {}
        for subscriptions in self.subscriptions.values():
            for symbol in subscriptions:
                counts[symbol] = counts.get(symbol, 0) + 1
        return counts


async def run_websocket_server(matching_engine: MatchingEngine, host: str = 'localhost', port: int = 8765) -> None:
    """
    Run the WebSocket server.
    
    Args:
        matching_engine: Matching engine instance
        host: Host to bind to
        port: Port to bind to
    """
    server = WebSocketServer(matching_engine, host, port)
    await server.start()


if __name__ == '__main__':
    from ..core.matching_engine import MatchingEngine
    
    matching_engine = MatchingEngine()
    asyncio.run(run_websocket_server(matching_engine))
