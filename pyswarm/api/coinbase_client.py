"""
Coinbase Advanced Trade API Client

Implements REST and WebSocket clients for Coinbase Advanced Trade API
with HMAC-SHA256 authentication and rate limiting.

Based on: docs/api/coinbase-api-integration.md
"""

import base64
import hashlib
import hmac
import json
import time
from typing import Any, Dict, List, Optional
from decimal import Decimal
from enum import Enum

import aiohttp
import structlog
from tenacity import retry, stop_after_attempt, wait_exponential

from coinswarm.core.config import settings

logger = structlog.get_logger(__name__)


class OrderSide(str, Enum):
    """Order side enumeration"""

    BUY = "BUY"
    SELL = "SELL"


class OrderType(str, Enum):
    """Order type enumeration"""

    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP_LIMIT = "STOP_LIMIT"


class TimeInForce(str, Enum):
    """Time in force enumeration"""

    GTC = "GOOD_UNTIL_CANCELLED"
    GTD = "GOOD_UNTIL_DATE_TIME"
    IOC = "IMMEDIATE_OR_CANCEL"
    FOK = "FILL_OR_KILL"


class CoinbaseAPIClient:
    """
    Coinbase Advanced Trade API client with authentication and rate limiting.

    Handles REST API calls with automatic signature generation and retry logic.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
        base_url: Optional[str] = None,
    ):
        """
        Initialize Coinbase API client.

        Args:
            api_key: Coinbase API key (defaults to config)
            api_secret: Coinbase API secret (defaults to config)
            base_url: API base URL (defaults to config)
        """
        self.api_key = api_key or settings.coinbase.coinbase_api_key
        self.api_secret = api_secret or settings.coinbase.coinbase_api_secret
        self.base_url = base_url or settings.coinbase.coinbase_api_base_url

        if not self.api_key or not self.api_secret:
            raise ValueError("Coinbase API key and secret must be provided")

        self.session: Optional[aiohttp.ClientSession] = None
        self.logger = logger.bind(component="coinbase_client")

    async def __aenter__(self) -> "CoinbaseAPIClient":
        """Async context manager entry"""
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit"""
        if self.session:
            await self.session.close()

    def _generate_signature(
        self, timestamp: str, method: str, request_path: str, body: str = ""
    ) -> str:
        """
        Generate HMAC-SHA256 signature for API request.

        Args:
            timestamp: Unix timestamp as string
            method: HTTP method (GET, POST, etc.)
            request_path: API endpoint path (e.g., /api/v3/brokerage/orders)
            body: Request body as JSON string

        Returns:
            Base64-encoded signature
        """
        message = timestamp + method + request_path + body
        secret_decoded = base64.b64decode(self.api_secret)
        signature = hmac.new(secret_decoded, message.encode("utf-8"), hashlib.sha256)
        return base64.b64encode(signature.digest()).decode("utf-8")

    def _build_headers(self, method: str, request_path: str, body: str = "") -> Dict[str, str]:
        """
        Build authenticated request headers.

        Args:
            method: HTTP method
            request_path: API endpoint path
            body: Request body as JSON string

        Returns:
            Dictionary of HTTP headers
        """
        timestamp = str(int(time.time()))
        signature = self._generate_signature(timestamp, method, request_path, body)

        return {
            "CB-ACCESS-KEY": self.api_key,
            "CB-ACCESS-SIGN": signature,
            "CB-ACCESS-TIMESTAMP": timestamp,
            "Content-Type": "application/json",
        }

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        reraise=True,
    )
    async def _request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Make authenticated API request with retry logic.

        Args:
            method: HTTP method
            endpoint: API endpoint (e.g., /api/v3/brokerage/accounts)
            params: Query parameters
            data: Request body data

        Returns:
            API response as dictionary

        Raises:
            aiohttp.ClientError: On request failure
        """
        if not self.session:
            raise RuntimeError("Client session not initialized. Use async context manager.")

        url = f"{self.base_url}{endpoint}"
        body = json.dumps(data) if data else ""
        headers = self._build_headers(method, endpoint, body)

        self.logger.debug(
            "api_request",
            method=method,
            endpoint=endpoint,
            params=params,
            has_data=bool(data),
        )

        async with self.session.request(
            method, url, headers=headers, params=params, data=body if body else None
        ) as response:
            response_data = await response.json()

            if response.status >= 400:
                self.logger.error(
                    "api_error",
                    status=response.status,
                    error=response_data,
                    endpoint=endpoint,
                )
                response.raise_for_status()

            self.logger.debug(
                "api_response", status=response.status, endpoint=endpoint, data=response_data
            )

            return response_data

    # ========================================================================
    # Account Endpoints
    # ========================================================================

    async def list_accounts(self) -> List[Dict[str, Any]]:
        """
        Get list of all trading accounts.

        Returns:
            List of account dictionaries with balances
        """
        response = await self._request("GET", "/api/v3/brokerage/accounts")
        return response.get("accounts", [])

    async def get_account(self, account_id: str) -> Dict[str, Any]:
        """
        Get specific account details.

        Args:
            account_id: Account UUID

        Returns:
            Account details dictionary
        """
        response = await self._request("GET", f"/api/v3/brokerage/accounts/{account_id}")
        return response.get("account", {})

    # ========================================================================
    # Product Endpoints
    # ========================================================================

    async def list_products(self) -> List[Dict[str, Any]]:
        """
        Get list of all available trading products.

        Returns:
            List of product dictionaries
        """
        response = await self._request("GET", "/api/v3/brokerage/products")
        return response.get("products", [])

    async def get_product(self, product_id: str) -> Dict[str, Any]:
        """
        Get specific product details.

        Args:
            product_id: Product ID (e.g., BTC-USD)

        Returns:
            Product details dictionary
        """
        response = await self._request("GET", f"/api/v3/brokerage/products/{product_id}")
        return response

    async def get_product_ticker(self, product_id: str) -> Dict[str, Any]:
        """
        Get current ticker for a product.

        Args:
            product_id: Product ID (e.g., BTC-USD)

        Returns:
            Ticker data with price, volume, etc.
        """
        response = await self._request("GET", f"/api/v3/brokerage/products/{product_id}/ticker")
        return response

    async def get_product_candles(
        self,
        product_id: str,
        start: int,
        end: int,
        granularity: str = "ONE_MINUTE",
    ) -> List[Dict[str, Any]]:
        """
        Get historical candles for a product.

        Args:
            product_id: Product ID (e.g., BTC-USD)
            start: Start time (Unix timestamp)
            end: End time (Unix timestamp)
            granularity: Candle size (ONE_MINUTE, FIVE_MINUTE, etc.)

        Returns:
            List of candle dictionaries
        """
        params = {"start": start, "end": end, "granularity": granularity}
        response = await self._request(
            "GET", f"/api/v3/brokerage/products/{product_id}/candles", params=params
        )
        return response.get("candles", [])

    # ========================================================================
    # Order Endpoints
    # ========================================================================

    async def create_market_order(
        self,
        product_id: str,
        side: OrderSide,
        size: Optional[str] = None,
        quote_size: Optional[str] = None,
        client_order_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Create a market order.

        Args:
            product_id: Product ID (e.g., BTC-USD)
            side: BUY or SELL
            size: Amount in base currency (for BTC-USD, this is BTC)
            quote_size: Amount in quote currency (for BTC-USD, this is USD)
            client_order_id: Optional client-specified order ID

        Returns:
            Order response with order_id and status
        """
        if not size and not quote_size:
            raise ValueError("Either size or quote_size must be specified")

        order_config: Dict[str, Any] = {"market_market_ioc": {}}
        if quote_size:
            order_config["market_market_ioc"]["quote_size"] = quote_size
        elif size:
            order_config["market_market_ioc"]["base_size"] = size

        data = {
            "product_id": product_id,
            "side": side.value,
            "order_configuration": order_config,
        }

        if client_order_id:
            data["client_order_id"] = client_order_id

        return await self._request("POST", "/api/v3/brokerage/orders", data=data)

    async def create_limit_order(
        self,
        product_id: str,
        side: OrderSide,
        size: str,
        limit_price: str,
        time_in_force: TimeInForce = TimeInForce.GTC,
        post_only: bool = False,
        client_order_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Create a limit order.

        Args:
            product_id: Product ID (e.g., BTC-USD)
            side: BUY or SELL
            size: Amount in base currency
            limit_price: Limit price
            time_in_force: Time in force policy
            post_only: Post-only flag (maker-only)
            client_order_id: Optional client-specified order ID

        Returns:
            Order response with order_id and status
        """
        order_config = {
            "limit_limit_gtc": {
                "base_size": size,
                "limit_price": limit_price,
                "post_only": post_only,
            }
        }

        data = {
            "product_id": product_id,
            "side": side.value,
            "order_configuration": order_config,
        }

        if client_order_id:
            data["client_order_id"] = client_order_id

        return await self._request("POST", "/api/v3/brokerage/orders", data=data)

    async def cancel_order(self, order_id: str) -> Dict[str, Any]:
        """
        Cancel an order.

        Args:
            order_id: Order UUID

        Returns:
            Cancellation confirmation
        """
        data = {"order_ids": [order_id]}
        return await self._request("POST", "/api/v3/brokerage/orders/batch_cancel", data=data)

    async def list_orders(
        self,
        product_id: Optional[str] = None,
        order_status: Optional[List[str]] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        List orders with optional filters.

        Args:
            product_id: Filter by product ID
            order_status: Filter by status (OPEN, FILLED, CANCELLED, etc.)
            limit: Maximum number of orders to return

        Returns:
            List of order dictionaries
        """
        params: Dict[str, Any] = {"limit": limit}
        if product_id:
            params["product_id"] = product_id
        if order_status:
            params["order_status"] = order_status

        response = await self._request("GET", "/api/v3/brokerage/orders/historical/batch", params=params)
        return response.get("orders", [])

    async def get_order(self, order_id: str) -> Dict[str, Any]:
        """
        Get specific order details.

        Args:
            order_id: Order UUID

        Returns:
            Order details dictionary
        """
        response = await self._request("GET", f"/api/v3/brokerage/orders/historical/{order_id}")
        return response.get("order", {})

    # ========================================================================
    # Fills Endpoint
    # ========================================================================

    async def list_fills(
        self,
        order_id: Optional[str] = None,
        product_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        Get list of fills (executed trades).

        Args:
            order_id: Filter by order ID
            product_id: Filter by product ID
            limit: Maximum number of fills to return

        Returns:
            List of fill dictionaries
        """
        params: Dict[str, Any] = {"limit": limit}
        if order_id:
            params["order_id"] = order_id
        if product_id:
            params["product_id"] = product_id

        response = await self._request("GET", "/api/v3/brokerage/orders/historical/fills", params=params)
        return response.get("fills", [])
