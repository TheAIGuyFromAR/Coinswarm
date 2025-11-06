# MCP Server Architecture for Coinbase API

## Overview

This document outlines the design of the Model Context Protocol (MCP) server that will provide Claude agents with secure, structured access to the Coinbase Advanced Trade API. The MCP server acts as a bridge between AI agents and the trading infrastructure.

---

## What is MCP?

**Model Context Protocol (MCP)** is an open standard developed by Anthropic that enables AI models to securely connect to external data sources and tools. MCP provides:

- **Standardized communication** between AI and data sources
- **Security boundaries** with controlled access
- **Resource management** for files, databases, and APIs
- **Tool exposure** for AI-driven actions
- **Prompt templates** for common operations

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    Claude Agents Layer                       │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────────┐   │
│  │ Orchestrator│  │ Trading Agent│  │ Analysis Agent   │   │
│  └─────────────┘  └──────────────┘  └──────────────────┘   │
└────────────────────────┬────────────────────────────────────┘
                         │ MCP Protocol
                         │
┌────────────────────────▼────────────────────────────────────┐
│                 MCP Server (Coinbase)                        │
│  ┌────────────────────────────────────────────────────┐     │
│  │              Resource Handlers                      │     │
│  │  • account://balances                              │     │
│  │  • market://ticker/{symbol}                        │     │
│  │  • order://status/{id}                             │     │
│  │  • history://fills                                 │     │
│  └────────────────────────────────────────────────────┘     │
│  ┌────────────────────────────────────────────────────┐     │
│  │              Tool Handlers                          │     │
│  │  • place_order(product, side, size, ...)          │     │
│  │  • cancel_order(order_id)                          │     │
│  │  • get_market_data(symbol, granularity)            │     │
│  │  • subscribe_ticker(symbols)                       │     │
│  └────────────────────────────────────────────────────┘     │
│  ┌────────────────────────────────────────────────────┐     │
│  │              Prompt Templates                       │     │
│  │  • analyze_position                                │     │
│  │  • risk_check                                      │     │
│  │  • market_summary                                  │     │
│  └────────────────────────────────────────────────────┘     │
└────────────────────────┬────────────────────────────────────┘
                         │ Coinbase API Client
                         │
┌────────────────────────▼────────────────────────────────────┐
│              Coinbase Advanced Trade API                     │
│           (REST + WebSocket)                                │
└─────────────────────────────────────────────────────────────┘
```

---

## MCP Server Components

### 1. Resources

Resources represent **read-only data** that agents can access. Each resource is identified by a URI.

#### Account Resources

**`account://balances`**
- Returns all account balances
- Updates periodically or on-demand
- Includes available and held amounts

**`account://positions`**
- Returns current open positions
- Calculated from balances + market prices
- Includes unrealized P&L

**`account://profile`**
- Account metadata and limits
- Trading permissions
- Fee tiers

#### Market Resources

**`market://ticker/{product_id}`**
- Current ticker data for a product
- Price, volume, 24h change
- Real-time or cached (configurable)

**`market://orderbook/{product_id}`**
- Current order book snapshot
- Level 2 data (50 levels)
- Bid/ask spreads

**`market://candles/{product_id}?granularity=1h&count=100`**
- Historical OHLCV data
- Configurable timeframe and count
- Supports multiple granularities

**`market://products`**
- List of all available trading pairs
- Includes trading status and parameters
- Cached with periodic refresh

#### Order Resources

**`order://active`**
- All open orders across products
- Includes pending and partially filled
- Real-time updates via WebSocket

**`order://history?start={timestamp}&end={timestamp}`**
- Historical orders
- Filterable by product, status, date
- Paginated results

**`order://status/{order_id}`**
- Detailed status of specific order
- Fill information
- Timestamps and fees

#### History Resources

**`history://fills?product={product_id}&start={timestamp}`**
- Trade execution history
- Commission and fee data
- Maker/taker designation

**`history://transfers`**
- Deposit and withdrawal history
- Blockchain transaction IDs
- Status tracking

---

### 2. Tools

Tools represent **actions** that agents can perform. Each tool has defined parameters and validation.

#### Trading Tools

**`place_order`**
```python
{
  "name": "place_order",
  "description": "Place a new order on Coinbase",
  "inputSchema": {
    "type": "object",
    "properties": {
      "product_id": {"type": "string", "description": "Trading pair (e.g., BTC-USD)"},
      "side": {"type": "string", "enum": ["BUY", "SELL"]},
      "order_type": {"type": "string", "enum": ["MARKET", "LIMIT", "STOP_LIMIT"]},
      "size": {"type": "string", "description": "Base currency amount (optional)"},
      "quote_size": {"type": "string", "description": "Quote currency amount (optional)"},
      "limit_price": {"type": "string", "description": "Limit price (required for LIMIT)"},
      "stop_price": {"type": "string", "description": "Stop price (required for STOP_LIMIT)"},
      "client_order_id": {"type": "string", "description": "Optional client ID"},
      "post_only": {"type": "boolean", "default": false}
    },
    "required": ["product_id", "side", "order_type"]
  }
}
```

**Safety Features**:
- Order size validation against account balance
- Price validation against current market (prevent fat finger)
- Maximum order size limits
- Dry-run mode for testing
- Confirmation required for large orders

**`cancel_order`**
```python
{
  "name": "cancel_order",
  "description": "Cancel an existing order",
  "inputSchema": {
    "type": "object",
    "properties": {
      "order_id": {"type": "string", "description": "Order ID to cancel"}
    },
    "required": ["order_id"]
  }
}
```

**`cancel_all_orders`**
```python
{
  "name": "cancel_all_orders",
  "description": "Cancel all open orders",
  "inputSchema": {
    "type": "object",
    "properties": {
      "product_id": {"type": "string", "description": "Optional product filter"}
    }
  }
}
```

#### Market Data Tools

**`get_market_data`**
```python
{
  "name": "get_market_data",
  "description": "Fetch current market data for products",
  "inputSchema": {
    "type": "object",
    "properties": {
      "product_ids": {"type": "array", "items": {"type": "string"}},
      "include_orderbook": {"type": "boolean", "default": false},
      "include_ticker": {"type": "boolean", "default": true}
    },
    "required": ["product_ids"]
  }
}
```

**`get_historical_candles`**
```python
{
  "name": "get_historical_candles",
  "description": "Fetch OHLCV candle data",
  "inputSchema": {
    "type": "object",
    "properties": {
      "product_id": {"type": "string"},
      "granularity": {
        "type": "string",
        "enum": ["1m", "5m", "15m", "30m", "1h", "2h", "6h", "1d"]
      },
      "start": {"type": "string", "format": "date-time"},
      "end": {"type": "string", "format": "date-time"}
    },
    "required": ["product_id", "granularity"]
  }
}
```

#### Analysis Tools

**`calculate_position_metrics`**
```python
{
  "name": "calculate_position_metrics",
  "description": "Calculate P&L, risk metrics for positions",
  "inputSchema": {
    "type": "object",
    "properties": {
      "product_id": {"type": "string", "description": "Optional product filter"}
    }
  }
}
```

**`check_trade_risk`**
```python
{
  "name": "check_trade_risk",
  "description": "Validate trade against risk parameters",
  "inputSchema": {
    "type": "object",
    "properties": {
      "product_id": {"type": "string"},
      "side": {"type": "string", "enum": ["BUY", "SELL"]},
      "size": {"type": "string"},
      "price": {"type": "string"}
    },
    "required": ["product_id", "side", "size"]
  }
}
```

---

### 3. Prompt Templates

Reusable prompts for common agent tasks.

**`analyze_position`**
```
Analyze my current position in {product_id}.

Current holdings:
{position_data}

Market data:
{market_data}

Recent trades:
{recent_fills}

Provide:
1. Unrealized P&L
2. Entry price vs current price
3. Risk assessment
4. Suggested actions (hold/exit/scale)
```

**`risk_check`**
```
Evaluate the risk of this proposed trade:

Order details:
- Product: {product_id}
- Side: {side}
- Size: {size}
- Type: {order_type}
- Price: {price}

Current portfolio:
{portfolio}

Risk parameters:
- Max position size: {max_position}
- Max order value: {max_value}
- Max portfolio allocation: {max_allocation}%

Approve or reject with reasoning.
```

**`market_summary`**
```
Provide a market summary for {product_ids}.

For each product include:
1. Current price and 24h change
2. Volume and liquidity assessment
3. Recent price action (support/resistance)
4. Notable events or news
5. Sentiment indicators

Data available:
{market_data}
```

---

## Implementation Details

### Server Structure

```python
# mcp_server/coinbase_server.py

from mcp.server import Server
from mcp.types import Resource, Tool, Prompt
import asyncio

class CoinbaseMCPServer(Server):
    def __init__(self, config: dict):
        super().__init__("coinbase-trading")
        self.coinbase_client = CoinbaseAPIClient(config)
        self.register_handlers()

    def register_handlers(self):
        # Register resources
        self.add_resource_handler("account://balances", self.get_balances)
        self.add_resource_handler("market://ticker/*", self.get_ticker)
        self.add_resource_handler("order://active", self.get_active_orders)

        # Register tools
        self.add_tool("place_order", self.place_order_handler)
        self.add_tool("cancel_order", self.cancel_order_handler)
        self.add_tool("get_market_data", self.get_market_data_handler)

        # Register prompts
        self.add_prompt("analyze_position", self.analyze_position_prompt)
        self.add_prompt("risk_check", self.risk_check_prompt)

    async def get_balances(self, uri: str) -> Resource:
        accounts = await self.coinbase_client.get_accounts()
        return Resource(
            uri=uri,
            mimeType="application/json",
            text=json.dumps(accounts, indent=2)
        )

    async def place_order_handler(self, arguments: dict) -> dict:
        # Validate order
        validation = await self.validate_order(arguments)
        if not validation['valid']:
            return {'error': validation['reason']}

        # Place order
        result = await self.coinbase_client.place_order(arguments)
        return result
```

### Configuration

```yaml
# config/mcp_server.yaml

server:
  name: coinbase-trading
  version: 1.0.0
  host: localhost
  port: 8765

coinbase:
  api_key: ${COINBASE_API_KEY}
  api_secret: ${COINBASE_API_SECRET}
  api_passphrase: ${COINBASE_API_PASSPHRASE}
  environment: sandbox  # sandbox | production

safety:
  max_order_value_usd: 1000
  max_position_size_pct: 25  # % of portfolio
  require_confirmation_above_usd: 500
  dry_run_mode: true

rate_limits:
  rest_requests_per_second: 10
  websocket_max_connections: 4

caching:
  products_ttl_seconds: 3600
  ticker_ttl_seconds: 5
  orderbook_ttl_seconds: 1

logging:
  level: INFO
  file: logs/mcp_server.log
  rotation: daily
```

---

## Security Considerations

### 1. Authentication & Authorization

**API Key Management**:
- Store credentials in environment variables or secure vault
- Never log or expose credentials
- Use separate keys for sandbox and production
- Implement key rotation strategy

**Agent Permissions**:
```python
class AgentPermissions:
    VIEWER = ['read_accounts', 'read_market_data']
    ANALYST = VIEWER + ['read_orders', 'read_fills']
    TRADER = ANALYST + ['place_order', 'cancel_order']
    ADMIN = TRADER + ['modify_config', 'view_logs']
```

### 2. Order Safety

**Pre-flight Checks**:
- Validate order size against balance
- Check price against current market (prevent 10x errors)
- Enforce maximum order values
- Rate limit order placement
- Require two-factor confirmation for large orders

**Circuit Breakers**:
```python
class CircuitBreaker:
    def __init__(self):
        self.max_orders_per_minute = 10
        self.max_loss_per_day = 1000  # USD
        self.max_position_size = 0.25  # 25% of portfolio

    async def check_order(self, order: dict) -> tuple[bool, str]:
        # Check order rate
        if self.order_count_last_minute() > self.max_orders_per_minute:
            return False, "Order rate limit exceeded"

        # Check daily loss
        if self.loss_today() > self.max_loss_per_day:
            return False, "Daily loss limit reached"

        # Check position sizing
        if self.position_size_after_order(order) > self.max_position_size:
            return False, "Position size limit exceeded"

        return True, ""
```

### 3. Data Privacy

- Sanitize logs (remove sensitive data)
- Encrypt credentials at rest
- Use TLS for all communications
- Implement audit trail for all trades

---

## Error Handling

### Connection Failures

```python
async def handle_connection_error(error: Exception):
    if isinstance(error, websockets.ConnectionClosed):
        await reconnect_with_backoff()
    elif isinstance(error, RateLimitError):
        await asyncio.sleep(error.retry_after)
    else:
        log_error(error)
        alert_admin(error)
```

### API Errors

```python
class CoinbaseError(Exception):
    ERROR_CODES = {
        'INSUFFICIENT_FUNDS': 'Not enough balance',
        'INVALID_ORDER_SIZE': 'Order size invalid',
        'PRODUCT_NOT_FOUND': 'Trading pair not found',
        'ORDER_NOT_FOUND': 'Order does not exist'
    }

    @classmethod
    def from_response(cls, response: dict):
        error_code = response.get('error')
        message = cls.ERROR_CODES.get(error_code, 'Unknown error')
        return cls(f"{error_code}: {message}")
```

---

## Testing Strategy

### Unit Tests
```python
# tests/test_mcp_server.py

import pytest
from mcp_server import CoinbaseMCPServer

@pytest.mark.asyncio
async def test_get_balances():
    server = CoinbaseMCPServer(test_config)
    resource = await server.get_balances("account://balances")
    assert resource.mimeType == "application/json"
    data = json.loads(resource.text)
    assert 'accounts' in data

@pytest.mark.asyncio
async def test_place_order_validation():
    server = CoinbaseMCPServer(test_config)
    result = await server.place_order_handler({
        'product_id': 'BTC-USD',
        'side': 'BUY',
        'order_type': 'MARKET',
        'size': '1000000'  # Unrealistic size
    })
    assert 'error' in result
```

### Integration Tests
```python
@pytest.mark.asyncio
async def test_end_to_end_order_flow():
    # Connect to sandbox
    server = CoinbaseMCPServer(sandbox_config)

    # Get initial balance
    balance = await server.get_balances("account://balances")

    # Place order
    order_result = await server.place_order_handler({
        'product_id': 'BTC-USD',
        'side': 'BUY',
        'order_type': 'MARKET',
        'quote_size': '10'
    })
    assert order_result['success']

    # Check order status
    await asyncio.sleep(2)
    order_status = await server.get_order_status(order_result['order_id'])
    assert order_status['status'] in ['FILLED', 'OPEN']
```

---

## Monitoring & Observability

### Metrics to Track

```python
# Latency
- api_request_duration_seconds
- websocket_message_latency_ms
- order_placement_time_ms

# Volume
- orders_placed_total
- orders_cancelled_total
- api_requests_total
- websocket_messages_received_total

# Errors
- api_errors_total (by error_code)
- websocket_disconnections_total
- order_rejections_total

# Business
- trading_volume_usd
- position_sizes_by_product
- pnl_realized_usd
- pnl_unrealized_usd
```

### Logging

```python
import structlog

logger = structlog.get_logger()

# Log all orders
logger.info(
    "order_placed",
    order_id=order_id,
    product=product_id,
    side=side,
    size=size,
    order_type=order_type,
    agent_id=agent_id
)

# Log errors with context
logger.error(
    "api_error",
    error_code=error.code,
    error_message=error.message,
    endpoint=endpoint,
    request_id=request_id
)
```

---

## Deployment

### Docker Container

```dockerfile
# Dockerfile

FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy server code
COPY mcp_server/ ./mcp_server/
COPY config/ ./config/

# Create logs directory
RUN mkdir -p logs

# Run server
CMD ["python", "-m", "mcp_server.coinbase_server"]
```

### docker-compose.yml

```yaml
version: '3.8'

services:
  mcp-server:
    build: .
    ports:
      - "8765:8765"
    environment:
      - COINBASE_API_KEY=${COINBASE_API_KEY}
      - COINBASE_API_SECRET=${COINBASE_API_SECRET}
      - COINBASE_API_PASSPHRASE=${COINBASE_API_PASSPHRASE}
      - ENVIRONMENT=sandbox
    volumes:
      - ./logs:/app/logs
      - ./config:/app/config
    restart: unless-stopped
```

---

## Development Roadmap

### Phase 1: Core Infrastructure (Week 1-2)
- [ ] Set up MCP server framework
- [ ] Implement Coinbase API client
- [ ] Add basic resources (accounts, market data)
- [ ] Add basic tools (place_order, cancel_order)
- [ ] Write unit tests

### Phase 2: Safety & Reliability (Week 3)
- [ ] Implement order validation
- [ ] Add circuit breakers
- [ ] Implement rate limiting
- [ ] Add error handling and retries
- [ ] WebSocket reconnection logic

### Phase 3: Advanced Features (Week 4)
- [ ] Add all order types support
- [ ] Implement prompt templates
- [ ] Add caching layer
- [ ] Position tracking and P&L
- [ ] Integration tests with sandbox

### Phase 4: Production Ready (Week 5-6)
- [ ] Security audit
- [ ] Load testing
- [ ] Monitoring and alerting
- [ ] Documentation
- [ ] Deployment automation

---

**Last Updated**: 2025-10-31
**Status**: Planning Phase
**Next**: Information Sources Documentation
