# Cryptocurrency Matching Engine

A high-performance cryptocurrency matching engine implementing REG NMS principles for price-time priority and internal order protection.

## Features

- **REG NMS Compliance**: Implements price-time priority matching and prevents internal trade-throughs
- **Order Types**: Supports Market, Limit, IOC (Immediate-or-Cancel), and FOK (Fill-or-Kill) orders
- **High Performance**: Designed to handle 1000+ orders per second with sub-millisecond latency
- **Real-time APIs**: REST API for order submission and WebSocket API for real-time market data
- **Comprehensive Testing**: Unit tests, integration tests, and performance benchmarks
- **Production Ready**: Robust error handling, logging, and monitoring

## Architecture

### Core Components

1. **Matching Engine** (`src/core/matching_engine.py`)
   - Main orchestrator for order processing
   - Implements REG NMS principles
   - Manages multiple order books

2. **Order Book** (`src/core/order_book.py`)
   - Efficient data structures using heaps and deques
   - Price-time priority management
   - BBO (Best Bid/Offer) calculation

3. **Order Types** (`src/core/order.py`, `src/core/order_types.py`)
   - Order and Trade data structures
   - Order type definitions and validation
   - Comprehensive serialization support

4. **APIs** (`src/api/`)
   - REST API for order submission and queries
   - WebSocket API for real-time market data
   - Input validation and error handling

5. **Utilities** (`src/utils/`)
   - Logging configuration
   - Performance monitoring
   - Benchmarking tools

## Installation

### Prerequisites

- Python 3.8 or higher
- pip package manager

### Setup

1. **Navigate to project directory**
   ```bash
   cd /Users/ujjwalsinha/cryptocurrency\ matching\ engine
   ```

2. **Create virtual environment** (if not already created)
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run tests**
   ```bash
   python -m pytest tests/ -v
   ```

## Usage

### Starting the Server

```bash
python main.py
```

This will start both the REST API server (port 5000) and WebSocket server (port 8765).

### REST API

#### Submit an Order

```bash
curl -X POST http://localhost:5000/orders \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "BTC-USDT",
    "order_type": "limit",
    "side": "buy",
    "quantity": "1.0",
    "price": "50000.0"
  }'
```

#### Get Order Book

```bash
curl http://localhost:5000/orderbook/BTC-USDT?depth=10
```

#### Get Statistics

```bash
curl http://localhost:5000/statistics
```

### WebSocket API

#### Connect to WebSocket

```javascript
const ws = new WebSocket('ws://localhost:8765');

ws.onopen = function() {
    // Subscribe to market data
    ws.send(JSON.stringify({
        type: 'subscribe',
        symbol: 'BTC-USDT'
    }));
};

ws.onmessage = function(event) {
    const data = JSON.parse(event.data);
    console.log('Received:', data);
};
```

#### Available Message Types

- `subscribe`: Subscribe to market data for a symbol
- `unsubscribe`: Unsubscribe from market data
- `get_orderbook`: Get current order book snapshot
- `ping`: Ping the server

## Order Types

### Market Order
Executes immediately at the best available price.

```json
{
  "symbol": "BTC-USDT",
  "order_type": "market",
  "side": "buy",
  "quantity": "1.0"
}
```

### Limit Order
Executes at specified price or better, rests on book if not immediately marketable.

```json
{
  "symbol": "BTC-USDT",
  "order_type": "limit",
  "side": "buy",
  "quantity": "1.0",
  "price": "50000.0"
}
```

### IOC (Immediate-or-Cancel)
Executes immediately or cancels unfilled portion.

```json
{
  "symbol": "BTC-USDT",
  "order_type": "ioc",
  "side": "buy",
  "quantity": "1.0",
  "price": "50000.0"
}
```

### FOK (Fill-or-Kill)
Executes completely or cancels entirely.

```json
{
  "symbol": "BTC-USDT",
  "order_type": "fok",
  "side": "buy",
  "quantity": "1.0",
  "price": "50000.0"
}
```

## REG NMS Compliance

The matching engine implements key REG NMS principles:

1. **Price-Time Priority**: Orders are matched first by price (better prices first), then by time (first-in-first-out)
2. **Internal Order Protection**: Prevents trade-throughs by always matching at the best available price
3. **Order Type Compliance**: Properly handles all required order types with appropriate execution rules

## Performance

### Benchmarks

Run performance benchmarks:

```bash
python benchmarks/load_test.py
```

### Target Performance

- **Throughput**: 1000+ orders per second
- **Latency**: < 1ms for order matching
- **Memory**: Efficient memory usage with minimal allocations
- **Concurrency**: Supports multiple concurrent connections

### Monitoring

The engine includes comprehensive performance monitoring:

- Order processing latency
- Trade execution metrics
- Memory usage tracking
- System resource monitoring

## Testing

### Unit Tests

```bash
python -m pytest tests/ -v
```

### Integration Tests

```bash
python -m pytest tests/ -v -k "integration"
```

### Performance Tests

```bash
python benchmarks/load_test.py
```

## Configuration

Environment variables can be used to configure the engine:

```bash
# Server configuration
export REST_HOST=0.0.0.0
export REST_PORT=5000
export WEBSOCKET_HOST=localhost
export WEBSOCKET_PORT=8765

# Logging
export LOG_LEVEL=INFO
export LOG_FILE=logs/matching_engine.log

# Performance
export MAX_ORDERS_PER_SECOND=10000
export MAX_ORDER_BOOK_DEPTH=100

# Validation
export MIN_QUANTITY=0.00000001
export MAX_QUANTITY=1000000
export MIN_PRICE=0.00000001
export MAX_PRICE=10000000
```

## API Documentation

### REST API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |
| POST | `/orders` | Submit order |
| GET | `/orders/{order_id}` | Get order details |
| DELETE | `/orders/{order_id}` | Cancel order |
| GET | `/orderbook/{symbol}` | Get order book |
| GET | `/symbols` | Get active symbols |
| GET | `/statistics` | Get engine statistics |

### WebSocket Messages

#### Subscribe to Market Data
```json
{
  "type": "subscribe",
  "symbol": "BTC-USDT"
}
```

#### Market Data Update
```json
{
  "type": "orderbook",
  "symbol": "BTC-USDT",
  "timestamp": "2024-01-01T12:00:00.000000Z",
  "bids": [["50000.0", "1.5"], ["49999.0", "2.0"]],
  "asks": [["50001.0", "1.0"], ["50002.0", "1.5"]],
  "best_bid": "50000.0",
  "best_ask": "50001.0"
}
```

#### Trade Execution
```json
{
  "type": "trade",
  "timestamp": "2024-01-01T12:00:00.000000Z",
  "symbol": "BTC-USDT",
  "trade_id": "trade_123",
  "price": "50000.0",
  "quantity": "1.0",
  "aggressor_side": "buy",
  "maker_order_id": "order_456",
  "taker_order_id": "order_789"
}
```

## Development

### Project Structure

```
cryptocurrency-matching-engine/
├── src/
│   ├── core/           # Core matching engine logic
│   ├── api/            # REST and WebSocket APIs
│   ├── utils/          # Utilities and helpers
│   └── config/         # Configuration management
├── tests/              # Test suite
├── benchmarks/         # Performance benchmarks
├── docs/               # Documentation
├── requirements.txt    # Python dependencies
├── setup.py           # Package setup
└── main.py            # Entry point
```

### Code Quality

The project follows Python best practices:

- Type hints throughout
- Comprehensive docstrings
- Unit test coverage
- Error handling
- Logging

### Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Run the test suite
6. Submit a pull request

## License

This project is proprietary and confidential. All rights reserved.

## Support

For questions or issues, please contact the development team.

---

**Note**: This matching engine is designed for educational and demonstration purposes. For production use, additional security, persistence, and compliance features may be required.