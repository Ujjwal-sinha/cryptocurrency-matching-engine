#!/usr/bin/env python3
"""
Main entry point for the cryptocurrency matching engine.

This script starts both the REST API and WebSocket servers
for the matching engine.
"""

import asyncio
import logging
import signal
import sys
import threading
import time
from typing import Optional

from src.core.matching_engine import MatchingEngine
from src.api.rest_api import create_app
from src.api.websocket_api import WebSocketServer
from src.utils.logger import setup_logging, get_logger
from src.utils.performance import get_performance_monitor
from src.config.settings import get_settings

logger = get_logger(__name__)


class MatchingEngineServer:
    """
    Main server class that manages both REST and WebSocket servers.
    """
    
    def __init__(self):
        """Initialize the server."""
        self.settings = get_settings()
        self.matching_engine = MatchingEngine()
        self.rest_app = None
        self.websocket_server = None
        self.rest_thread = None
        self.websocket_task = None
        self.running = False
        
        # Setup logging
        setup_logging(
            level=self.settings.log_level,
            log_file=self.settings.log_file
        )
        
        logger.info("Matching engine server initialized")
    
    def start(self) -> None:
        """Start both REST and WebSocket servers."""
        try:
            logger.info("Starting matching engine server...")
            
            # Start REST API server in a separate thread
            self._start_rest_server()
            
            # Start WebSocket server in the main thread
            self._start_websocket_server()
            
        except KeyboardInterrupt:
            logger.info("Received interrupt signal, shutting down...")
            self.stop()
        except Exception as e:
            logger.error(f"Error starting server: {str(e)}")
            sys.exit(1)
    
    def _start_rest_server(self) -> None:
        """Start REST API server in a separate thread."""
        def run_rest_server():
            try:
                self.rest_app = create_app()
                logger.info(f"Starting REST API server on {self.settings.rest_host}:{self.settings.rest_port}")
                self.rest_app.run(
                    host=self.settings.rest_host,
                    port=self.settings.rest_port,
                    debug=self.settings.debug,
                    use_reloader=False  # Disable reloader in production
                )
            except Exception as e:
                logger.error(f"Error starting REST server: {str(e)}")
        
        self.rest_thread = threading.Thread(target=run_rest_server, daemon=True)
        self.rest_thread.start()
        
        # Give the server time to start
        time.sleep(1)
    
    def _start_websocket_server(self) -> None:
        """Start WebSocket server."""
        try:
            self.websocket_server = WebSocketServer(
                self.matching_engine,
                host=self.settings.websocket_host,
                port=self.settings.websocket_port
            )
            
            logger.info(f"Starting WebSocket server on {self.settings.websocket_host}:{self.settings.websocket_port}")
            
            # Run WebSocket server
            asyncio.run(self.websocket_server.start())
            
        except Exception as e:
            logger.error(f"Error starting WebSocket server: {str(e)}")
            raise
    
    def stop(self) -> None:
        """Stop the server."""
        logger.info("Stopping matching engine server...")
        self.running = False
        
        # Stop WebSocket server
        if self.websocket_server:
            # WebSocket server will stop when the event loop exits
            pass
        
        # Stop REST server
        if self.rest_thread and self.rest_thread.is_alive():
            # REST server will stop when the thread exits
            pass
        
        logger.info("Server stopped")


def signal_handler(signum, frame):
    """Handle shutdown signals."""
    logger.info(f"Received signal {signum}, shutting down...")
    sys.exit(0)


def main():
    """Main entry point."""
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # Create and start server
        server = MatchingEngineServer()
        server.start()
        
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt, shutting down...")
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
