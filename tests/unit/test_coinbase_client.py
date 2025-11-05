"""
Unit tests for Coinbase API Client

Tests authentication, signature generation, and core API methods.
"""

import base64
import hashlib
import hmac
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from coinswarm.api.coinbase_client import (
    CoinbaseAPIClient,
    OrderSide,
    OrderType,
    TimeInForce,
)


class TestCoinbaseAPIClient:
    """Test suite for CoinbaseAPIClient"""

    @pytest.fixture
    def api_client(self):
        """Create test API client"""
        return CoinbaseAPIClient(
            api_key="test_api_key",
            api_secret=base64.b64encode(b"test_secret").decode("utf-8"),
            base_url="https://api.coinbase.com",
        )

    def test_initialization(self, api_client):
        """Test client initialization"""
        assert api_client.api_key == "test_api_key"
        assert api_client.base_url == "https://api.coinbase.com"

    def test_initialization_without_credentials(self):
        """Test initialization fails without credentials"""
        with patch("coinswarm.api.coinbase_client.settings") as mock_settings:
            mock_settings.coinbase.coinbase_api_key = ""
            mock_settings.coinbase.coinbase_api_secret = ""
            with pytest.raises(ValueError, match="API key and secret must be provided"):
                CoinbaseAPIClient()

    def test_generate_signature(self, api_client):
        """Test HMAC-SHA256 signature generation"""
        timestamp = "1234567890"
        method = "GET"
        request_path = "/api/v3/brokerage/accounts"
        body = ""

        signature = api_client._generate_signature(timestamp, method, request_path, body)

        # Verify signature is base64 encoded
        assert isinstance(signature, str)
        assert len(signature) > 0

        # Decode and verify it's valid base64
        decoded = base64.b64decode(signature)
        assert isinstance(decoded, bytes)

    def test_generate_signature_with_body(self, api_client):
        """Test signature generation with request body"""
        timestamp = "1234567890"
        method = "POST"
        request_path = "/api/v3/brokerage/orders"
        body = '{"product_id":"BTC-USD","side":"BUY"}'

        signature = api_client._generate_signature(timestamp, method, request_path, body)
        assert isinstance(signature, str)
        assert len(signature) > 0

    def test_build_headers(self, api_client):
        """Test request header building"""
        method = "GET"
        request_path = "/api/v3/brokerage/accounts"

        headers = api_client._build_headers(method, request_path)

        # Check required headers
        assert "CB-ACCESS-KEY" in headers
        assert "CB-ACCESS-SIGN" in headers
        assert "CB-ACCESS-TIMESTAMP" in headers
        assert "Content-Type" in headers

        assert headers["CB-ACCESS-KEY"] == "test_api_key"
        assert headers["Content-Type"] == "application/json"

    @pytest.mark.asyncio
    async def test_context_manager(self, api_client):
        """Test async context manager"""
        async with api_client as client:
            assert client.session is not None

        # Session should be closed after exiting context
        assert api_client.session.closed

    @pytest.mark.asyncio
    async def test_list_accounts(self, api_client):
        """Test list_accounts method"""
        mock_response = {
            "accounts": [
                {
                    "uuid": "abc-123",
                    "currency": "USD",
                    "available_balance": {"value": "1000.00"},
                },
                {
                    "uuid": "def-456",
                    "currency": "BTC",
                    "available_balance": {"value": "0.5"},
                },
            ]
        }

        with patch.object(api_client, "_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response

            async with api_client:
                accounts = await api_client.list_accounts()

            assert len(accounts) == 2
            assert accounts[0]["currency"] == "USD"
            assert accounts[1]["currency"] == "BTC"

    @pytest.mark.asyncio
    async def test_get_account(self, api_client):
        """Test get_account method"""
        account_id = "abc-123"
        mock_response = {
            "account": {
                "uuid": account_id,
                "currency": "USD",
                "available_balance": {"value": "1000.00"},
            }
        }

        with patch.object(api_client, "_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response

            async with api_client:
                account = await api_client.get_account(account_id)

            assert account["uuid"] == account_id
            assert account["currency"] == "USD"

    @pytest.mark.asyncio
    async def test_list_products(self, api_client):
        """Test list_products method"""
        mock_response = {
            "products": [
                {"product_id": "BTC-USD", "base_currency": "BTC", "quote_currency": "USD"},
                {"product_id": "ETH-USD", "base_currency": "ETH", "quote_currency": "USD"},
            ]
        }

        with patch.object(api_client, "_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response

            async with api_client:
                products = await api_client.list_products()

            assert len(products) == 2
            assert products[0]["product_id"] == "BTC-USD"
            assert products[1]["product_id"] == "ETH-USD"

    @pytest.mark.asyncio
    async def test_get_product_ticker(self, api_client):
        """Test get_product_ticker method"""
        product_id = "BTC-USD"
        mock_response = {
            "price": "50000.00",
            "volume": "1000.5",
            "best_bid": "49999.00",
            "best_ask": "50001.00",
        }

        with patch.object(api_client, "_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response

            async with api_client:
                ticker = await api_client.get_product_ticker(product_id)

            assert ticker["price"] == "50000.00"
            assert ticker["best_bid"] == "49999.00"

    @pytest.mark.asyncio
    async def test_create_market_order(self, api_client):
        """Test create_market_order method"""
        mock_response = {
            "success_response": {"order_id": "order-123", "status": "PENDING"}
        }

        with patch.object(api_client, "_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response

            async with api_client:
                result = await api_client.create_market_order(
                    product_id="BTC-USD", side=OrderSide.BUY, quote_size="100.00"
                )

            assert result["success_response"]["order_id"] == "order-123"

    @pytest.mark.asyncio
    async def test_create_market_order_validation(self, api_client):
        """Test market order validation"""
        async with api_client:
            with pytest.raises(ValueError, match="Either size or quote_size must be specified"):
                await api_client.create_market_order(
                    product_id="BTC-USD", side=OrderSide.BUY
                )

    @pytest.mark.asyncio
    async def test_create_limit_order(self, api_client):
        """Test create_limit_order method"""
        mock_response = {
            "success_response": {"order_id": "order-456", "status": "PENDING"}
        }

        with patch.object(api_client, "_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response

            async with api_client:
                result = await api_client.create_limit_order(
                    product_id="BTC-USD",
                    side=OrderSide.BUY,
                    size="0.01",
                    limit_price="49000.00",
                )

            assert result["success_response"]["order_id"] == "order-456"

    @pytest.mark.asyncio
    async def test_cancel_order(self, api_client):
        """Test cancel_order method"""
        order_id = "order-123"
        mock_response = {"results": [{"success": True, "order_id": order_id}]}

        with patch.object(api_client, "_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response

            async with api_client:
                result = await api_client.cancel_order(order_id)

            assert result["results"][0]["order_id"] == order_id

    @pytest.mark.asyncio
    async def test_list_orders(self, api_client):
        """Test list_orders method"""
        mock_response = {
            "orders": [
                {"order_id": "order-1", "product_id": "BTC-USD", "status": "OPEN"},
                {"order_id": "order-2", "product_id": "ETH-USD", "status": "FILLED"},
            ]
        }

        with patch.object(api_client, "_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response

            async with api_client:
                orders = await api_client.list_orders(product_id="BTC-USD")

            assert len(orders) == 2
            assert orders[0]["status"] == "OPEN"

    @pytest.mark.asyncio
    async def test_get_product_candles(self, api_client):
        """Test get_product_candles method"""
        mock_response = {
            "candles": [
                {
                    "start": "1234567890",
                    "open": "50000",
                    "high": "51000",
                    "low": "49500",
                    "close": "50500",
                    "volume": "100",
                }
            ]
        }

        with patch.object(api_client, "_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response

            async with api_client:
                candles = await api_client.get_product_candles(
                    product_id="BTC-USD",
                    start=1234567890,
                    end=1234567900,
                    granularity="ONE_MINUTE",
                )

            assert len(candles) == 1
            assert candles[0]["open"] == "50000"
            assert candles[0]["close"] == "50500"


class TestEnums:
    """Test enum classes"""

    def test_order_side_enum(self):
        """Test OrderSide enum"""
        assert OrderSide.BUY.value == "BUY"
        assert OrderSide.SELL.value == "SELL"

    def test_order_type_enum(self):
        """Test OrderType enum"""
        assert OrderType.MARKET.value == "MARKET"
        assert OrderType.LIMIT.value == "LIMIT"
        assert OrderType.STOP_LIMIT.value == "STOP_LIMIT"

    def test_time_in_force_enum(self):
        """Test TimeInForce enum"""
        assert TimeInForce.GTC.value == "GOOD_UNTIL_CANCELLED"
        assert TimeInForce.IOC.value == "IMMEDIATE_OR_CANCEL"
