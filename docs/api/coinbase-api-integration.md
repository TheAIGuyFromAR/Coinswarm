# Coinbase Advanced API Integration Plan

## Overview

This document details the integration strategy for Coinbase Advanced Trade API, including authentication, endpoints, data structures, WebSocket feeds, and error handling patterns.

---

## API Fundamentals

### Base URLs

```
Production:  https://api.coinbase.com
Sandbox:     https://api-sandbox.coinbase.com (limited availability)
```

### Authentication

Coinbase uses **HMAC-SHA256** signatures for authentication.

**Required Credentials**:
- API Key
- API Secret (base64-encoded)
- Passphrase (optional for some endpoints)

**Authentication Flow**:
1. Generate timestamp (Unix epoch in seconds)
2. Create pre-hash string: `timestamp + method + requestPath + body`
3. Decode API secret from base64
4. Create HMAC SHA256 signature
5. Base64 encode the signature
6. Include headers:
   - `CB-ACCESS-KEY`: Your API key
   - `CB-ACCESS-SIGN`: Generated signature
   - `CB-ACCESS-TIMESTAMP`: Timestamp used in signature
   - `CB-ACCESS-PASSPHRASE`: Your passphrase (if required)

**Example Signature Generation (Python)**:
```python
import hmac
import hashlib
import base64
import time

def generate_signature(api_secret: str, timestamp: str, method: str,
                       request_path: str, body: str = '') -> str:
    message = timestamp + method + request_path + body
    secret_decoded = base64.b64decode(api_secret)
    signature = hmac.new(
        secret_decoded,
        message.encode('utf-8'),
        hashlib.sha256
    )
    return base64.b64encode(signature.digest()).decode('utf-8')
```

---

## REST API Endpoints

### Account & Portfolio

#### Get All Accounts
```http
GET /api/v3/brokerage/accounts
```
Returns list of all trading accounts with balances.

**Response**:
```json
{
  "accounts": [
    {
      "uuid": "account-uuid",
      "name": "BTC Wallet",
      "currency": "BTC",
      "available_balance": {
        "value": "0.5",
        "currency": "BTC"
      },
      "default": true,
      "active": true,
      "created_at": "2023-01-01T00:00:00Z",
      "type": "ACCOUNT_TYPE_CRYPTO"
    }
  ]
}
```

#### Get Account Details
```http
GET /api/v3/brokerage/accounts/{account_uuid}
```

---

### Market Data

#### Get Products (Trading Pairs)
```http
GET /api/v3/brokerage/products
```
Returns all available trading pairs.

**Query Parameters**:
- `product_type`: SPOT, FUTURE
- `product_ids`: Comma-separated list of product IDs

**Response**:
```json
{
  "products": [
    {
      "product_id": "BTC-USD",
      "price": "43250.50",
      "price_percentage_change_24h": "2.45",
      "volume_24h": "1234567.89",
      "volume_percentage_change_24h": "5.23",
      "base_currency": "BTC",
      "quote_currency": "USD",
      "base_increment": "0.00000001",
      "quote_increment": "0.01",
      "base_min_size": "0.0001",
      "base_max_size": "10000",
      "min_market_funds": "1",
      "max_market_funds": "1000000",
      "status": "online",
      "trading_disabled": false
    }
  ]
}
```

#### Get Product Ticker
```http
GET /api/v3/brokerage/products/{product_id}/ticker
```

#### Get Product Candles
```http
GET /api/v3/brokerage/products/{product_id}/candles
```

**Query Parameters**:
- `start`: Unix timestamp (seconds)
- `end`: Unix timestamp (seconds)
- `granularity`: ONE_MINUTE, FIVE_MINUTE, FIFTEEN_MINUTE, THIRTY_MINUTE, ONE_HOUR, TWO_HOUR, SIX_HOUR, ONE_DAY

**Response**:
```json
{
  "candles": [
    {
      "start": "1640995200",
      "low": "43000.00",
      "high": "43500.00",
      "open": "43200.00",
      "close": "43350.00",
      "volume": "123.456"
    }
  ]
}
```

#### Get Product Order Book
```http
GET /api/v3/brokerage/products/{product_id}/book
```

**Query Parameters**:
- `level`: 1 (best bid/ask), 2 (full order book)

---

### Order Management

#### Create Order
```http
POST /api/v3/brokerage/orders
```

**Request Body**:
```json
{
  "client_order_id": "uuid-client-generated",
  "product_id": "BTC-USD",
  "side": "BUY",
  "order_configuration": {
    "market_market_ioc": {
      "quote_size": "100"
    }
  }
}
```

**Order Types**:

1. **Market Order**:
```json
{
  "order_configuration": {
    "market_market_ioc": {
      "quote_size": "100"  // or "base_size": "0.001"
    }
  }
}
```

2. **Limit Order - Good Till Cancelled**:
```json
{
  "order_configuration": {
    "limit_limit_gtc": {
      "base_size": "0.001",
      "limit_price": "43000.00",
      "post_only": false
    }
  }
}
```

3. **Limit Order - Good Till Date**:
```json
{
  "order_configuration": {
    "limit_limit_gtd": {
      "base_size": "0.001",
      "limit_price": "43000.00",
      "end_time": "2024-12-31T23:59:59Z",
      "post_only": false
    }
  }
}
```

4. **Stop Limit Order**:
```json
{
  "order_configuration": {
    "stop_limit_stop_limit_gtc": {
      "base_size": "0.001",
      "limit_price": "43000.00",
      "stop_price": "42500.00",
      "stop_direction": "STOP_DIRECTION_STOP_DOWN"
    }
  }
}
```

**Response**:
```json
{
  "success": true,
  "order_id": "order-uuid",
  "success_response": {
    "order_id": "order-uuid",
    "product_id": "BTC-USD",
    "side": "BUY",
    "client_order_id": "uuid-client-generated"
  }
}
```

#### Cancel Orders
```http
POST /api/v3/brokerage/orders/batch_cancel
```

**Request Body**:
```json
{
  "order_ids": ["order-uuid-1", "order-uuid-2"]
}
```

#### List Orders
```http
GET /api/v3/brokerage/orders/batch
```

**Query Parameters**:
- `order_ids`: Comma-separated order UUIDs
- `product_id`: Filter by product
- `order_status`: OPEN, FILLED, CANCELLED, EXPIRED, FAILED
- `limit`: Max 1000
- `start_date`: ISO 8601 format
- `end_date`: ISO 8601 format

#### Get Order
```http
GET /api/v3/brokerage/orders/historical/{order_id}
```

---

### Fills (Trade History)

#### List Fills
```http
GET /api/v3/brokerage/orders/historical/fills
```

**Query Parameters**:
- `order_id`: Filter by specific order
- `product_id`: Filter by product
- `start_sequence_timestamp`: ISO 8601 timestamp
- `end_sequence_timestamp`: ISO 8601 timestamp
- `limit`: Max 1000

**Response**:
```json
{
  "fills": [
    {
      "entry_id": "fill-uuid",
      "trade_id": "trade-uuid",
      "order_id": "order-uuid",
      "trade_time": "2024-01-01T12:00:00Z",
      "trade_type": "FILL",
      "price": "43250.50",
      "size": "0.001",
      "commission": "0.43250",
      "product_id": "BTC-USD",
      "sequence_timestamp": "2024-01-01T12:00:00.123456Z",
      "liquidity_indicator": "TAKER",
      "size_in_quote": true,
      "user_id": "user-uuid",
      "side": "BUY"
    }
  ]
}
```

---

## WebSocket API

### Connection

```
Production:  wss://advanced-trade-ws.coinbase.com
```

### Authentication

Send authentication message immediately after connection:

```json
{
  "type": "subscribe",
  "product_ids": ["BTC-USD", "ETH-USD"],
  "channel": "level2",
  "api_key": "your-api-key",
  "timestamp": "1640995200",
  "signature": "generated-signature"
}
```

### Channels

#### 1. Ticker Channel
Real-time price updates.

**Subscribe**:
```json
{
  "type": "subscribe",
  "product_ids": ["BTC-USD"],
  "channel": "ticker"
}
```

**Message Format**:
```json
{
  "channel": "ticker",
  "client_id": "",
  "timestamp": "2024-01-01T12:00:00.123456Z",
  "sequence_num": 0,
  "events": [
    {
      "type": "ticker",
      "tickers": [
        {
          "type": "ticker",
          "product_id": "BTC-USD",
          "price": "43250.50",
          "volume_24_h": "1234567.89",
          "low_24_h": "42000.00",
          "high_24_h": "44000.00",
          "low_52_w": "15000.00",
          "high_52_w": "69000.00",
          "price_percent_chg_24_h": "2.45"
        }
      ]
    }
  ]
}
```

#### 2. Level2 Channel
Order book updates (50 levels).

**Subscribe**:
```json
{
  "type": "subscribe",
  "product_ids": ["BTC-USD"],
  "channel": "level2"
}
```

**Snapshot Message**:
```json
{
  "channel": "level2",
  "events": [
    {
      "type": "snapshot",
      "product_id": "BTC-USD",
      "updates": [
        {
          "side": "bid",
          "event_time": "2024-01-01T12:00:00Z",
          "price_level": "43250.50",
          "new_quantity": "1.5"
        }
      ]
    }
  ]
}
```

**Update Message**:
```json
{
  "channel": "level2",
  "events": [
    {
      "type": "update",
      "product_id": "BTC-USD",
      "updates": [
        {
          "side": "bid",
          "event_time": "2024-01-01T12:00:01Z",
          "price_level": "43250.50",
          "new_quantity": "0"  // 0 means removed
        }
      ]
    }
  ]
}
```

#### 3. Market Trades Channel
Real-time trade executions.

**Subscribe**:
```json
{
  "type": "subscribe",
  "product_ids": ["BTC-USD"],
  "channel": "market_trades"
}
```

**Message Format**:
```json
{
  "channel": "market_trades",
  "events": [
    {
      "type": "update",
      "trades": [
        {
          "trade_id": "12345",
          "product_id": "BTC-USD",
          "price": "43250.50",
          "size": "0.001",
          "side": "BUY",
          "time": "2024-01-01T12:00:00.123Z"
        }
      ]
    }
  ]
}
```

#### 4. User Channel
Account updates (orders, fills).

**Subscribe**:
```json
{
  "type": "subscribe",
  "product_ids": ["BTC-USD"],
  "channel": "user",
  "api_key": "your-api-key",
  "timestamp": "1640995200",
  "signature": "generated-signature"
}
```

**Order Update**:
```json
{
  "channel": "user",
  "events": [
    {
      "type": "update",
      "orders": [
        {
          "order_id": "order-uuid",
          "client_order_id": "client-uuid",
          "cumulative_quantity": "0.001",
          "leaves_quantity": "0",
          "avg_price": "43250.50",
          "total_fees": "0.43250",
          "status": "FILLED",
          "product_id": "BTC-USD",
          "creation_time": "2024-01-01T12:00:00Z",
          "order_side": "BUY",
          "order_type": "MARKET"
        }
      ]
    }
  ]
}
```

---

## Rate Limits

### REST API
- **Public Endpoints**: 10 requests/second
- **Private Endpoints**: 15 requests/second
- **Burst**: Up to 30 requests in a short window

**Rate Limit Headers**:
```
cb-rate-limit-burst: 30
cb-rate-limit-remaining: 28
cb-rate-limit-reset: 1640995200
```

### WebSocket
- **Max Connections**: 8 per API key
- **Max Subscriptions**: 100 products per connection
- **Message Rate**: No explicit limit, but excessive messages may be disconnected

---

## Error Handling

### HTTP Error Codes

| Code | Meaning | Action |
|------|---------|--------|
| 400 | Bad Request | Check request format |
| 401 | Unauthorized | Verify API credentials |
| 403 | Forbidden | Check permissions/rate limits |
| 404 | Not Found | Verify resource exists |
| 429 | Too Many Requests | Implement backoff |
| 500 | Internal Server Error | Retry with exponential backoff |
| 503 | Service Unavailable | Retry with exponential backoff |

### Error Response Format

```json
{
  "error": "INVALID_ARGUMENT",
  "message": "Invalid product_id",
  "error_details": "Product BTC-USDT does not exist",
  "preview_failure_reason": "UNKNOWN_FAILURE_REASON"
}
```

### Common Error Codes

- `INVALID_ARGUMENT`: Malformed request
- `INSUFFICIENT_FUNDS`: Not enough balance
- `INVALID_ORDER_SIZE`: Order size too small/large
- `PRODUCT_NOT_FOUND`: Invalid product ID
- `ORDER_NOT_FOUND`: Order does not exist
- `RATE_LIMIT_EXCEEDED`: Too many requests

---

## Best Practices

### 1. Connection Management

```python
import asyncio
import websockets

class CoinbaseWebSocket:
    def __init__(self):
        self.ws = None
        self.reconnect_delay = 1
        self.max_reconnect_delay = 60

    async def connect(self):
        while True:
            try:
                self.ws = await websockets.connect(
                    "wss://advanced-trade-ws.coinbase.com"
                )
                await self.authenticate()
                await self.subscribe()
                self.reconnect_delay = 1
                await self.receive_messages()
            except Exception as e:
                print(f"Connection error: {e}")
                await asyncio.sleep(self.reconnect_delay)
                self.reconnect_delay = min(
                    self.reconnect_delay * 2,
                    self.max_reconnect_delay
                )
```

### 2. Rate Limit Management

```python
import time
from collections import deque

class RateLimiter:
    def __init__(self, max_requests: int, window_seconds: int):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests = deque()

    async def acquire(self):
        now = time.time()
        # Remove old requests outside window
        while self.requests and self.requests[0] < now - self.window_seconds:
            self.requests.popleft()

        if len(self.requests) >= self.max_requests:
            sleep_time = self.requests[0] + self.window_seconds - now
            await asyncio.sleep(sleep_time)
            return await self.acquire()

        self.requests.append(now)
```

### 3. Order Validation

```python
def validate_order(product: dict, order: dict) -> bool:
    base_increment = float(product['base_increment'])
    quote_increment = float(product['quote_increment'])
    base_min = float(product['base_min_size'])

    if 'base_size' in order:
        size = float(order['base_size'])
        if size < base_min:
            raise ValueError(f"Size {size} below minimum {base_min}")
        if size % base_increment != 0:
            raise ValueError(f"Size {size} not multiple of {base_increment}")

    if 'limit_price' in order:
        price = float(order['limit_price'])
        if price % quote_increment != 0:
            raise ValueError(f"Price {price} not multiple of {quote_increment}")

    return True
```

### 4. Signature Caching

```python
from functools import lru_cache
import time

class CoinbaseAuth:
    def __init__(self, api_key, api_secret, passphrase):
        self.api_key = api_key
        self.api_secret = api_secret
        self.passphrase = passphrase

    def get_headers(self, method: str, request_path: str, body: str = ''):
        timestamp = str(int(time.time()))
        signature = generate_signature(
            self.api_secret, timestamp, method, request_path, body
        )
        return {
            'CB-ACCESS-KEY': self.api_key,
            'CB-ACCESS-SIGN': signature,
            'CB-ACCESS-TIMESTAMP': timestamp,
            'CB-ACCESS-PASSPHRASE': self.passphrase,
            'Content-Type': 'application/json'
        }
```

---

## Data Models

### Python Pydantic Models

```python
from pydantic import BaseModel, Field
from typing import Optional, Literal
from datetime import datetime
from decimal import Decimal

class Product(BaseModel):
    product_id: str
    price: Decimal
    base_currency: str
    quote_currency: str
    base_increment: Decimal
    quote_increment: Decimal
    base_min_size: Decimal
    base_max_size: Decimal
    status: str
    trading_disabled: bool

class Account(BaseModel):
    uuid: str
    name: str
    currency: str
    available_balance: Decimal
    hold: Decimal = Decimal('0')

class Order(BaseModel):
    client_order_id: str
    product_id: str
    side: Literal['BUY', 'SELL']
    order_type: Literal['MARKET', 'LIMIT', 'STOP_LIMIT']
    size: Optional[Decimal] = None
    quote_size: Optional[Decimal] = None
    limit_price: Optional[Decimal] = None
    stop_price: Optional[Decimal] = None
    post_only: bool = False

class Fill(BaseModel):
    entry_id: str
    trade_id: str
    order_id: str
    trade_time: datetime
    price: Decimal
    size: Decimal
    commission: Decimal
    product_id: str
    side: Literal['BUY', 'SELL']
    liquidity_indicator: Literal['MAKER', 'TAKER']
```

---

## Testing Strategy

### 1. Sandbox Environment
- Use sandbox credentials for development
- Test all order types and edge cases
- Validate error handling

### 2. Paper Trading
- Run parallel to sandbox with live data
- Track theoretical P&L
- Validate strategy logic

### 3. Live Testing
- Start with minimal capital
- Single product initially
- Gradual scale-up

---

## Integration Checklist

- [ ] Set up API credentials (sandbox + production)
- [ ] Implement authentication and signature generation
- [ ] Create REST API client with rate limiting
- [ ] Create WebSocket client with reconnection logic
- [ ] Implement order placement and cancellation
- [ ] Implement market data fetching
- [ ] Implement account and position tracking
- [ ] Create data models and validation
- [ ] Write unit tests for all API methods
- [ ] Write integration tests with sandbox
- [ ] Document error scenarios and recovery
- [ ] Set up monitoring and alerting

---

**Last Updated**: 2025-10-31
**Status**: Planning Phase
**Next**: MCP Server Design
<!-- Cleared: Content moved to API_strategies_and_guides.md -->
