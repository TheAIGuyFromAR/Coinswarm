"""
Coinbase MCP Server

Model Context Protocol server for Coinbase Advanced Trade API integration.
Exposes resources and tools for Claude agent interaction with trading capabilities.

Based on: docs/architecture/mcp-server-design.md
"""

import asyncio
from typing import Any, Dict, List, Optional

import structlog
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import (
    Resource,
    Tool,
    TextContent,
    ImageContent,
    EmbeddedResource,
)

from coinswarm.api.coinbase_client import CoinbaseAPIClient, OrderSide, OrderType, TimeInForce
from coinswarm.core.config import settings

logger = structlog.get_logger(__name__)


class CoinbaseMCPServer:
    """
    MCP Server for Coinbase Advanced Trade API.

    Provides resources (account, market data, orders) and tools (place_order,
    cancel_order, etc.) for Claude agent integration.
    """

    def __init__(self):
        """Initialize MCP server with Coinbase client"""
        self.server = Server("coinbase-trading")
        self.coinbase_client: Optional[CoinbaseAPIClient] = None
        self.logger = logger.bind(component="mcp_server")

        # Register handlers
        self._register_resource_handlers()
        self._register_tool_handlers()
        self._register_prompt_handlers()

    async def _get_client(self) -> CoinbaseAPIClient:
        """Get or create Coinbase API client"""
        if not self.coinbase_client:
            self.coinbase_client = CoinbaseAPIClient()
            await self.coinbase_client.__aenter__()
        return self.coinbase_client

    # ========================================================================
    # Resource Handlers
    # ========================================================================

    def _register_resource_handlers(self) -> None:
        """Register MCP resource handlers"""

        @self.server.list_resources()
        async def list_resources() -> List[Resource]:
            """List available resources"""
            return [
                Resource(
                    uri="coinbase://accounts",
                    name="Trading Accounts",
                    mimeType="application/json",
                    description="List all trading accounts with balances",
                ),
                Resource(
                    uri="coinbase://products",
                    name="Trading Products",
                    mimeType="application/json",
                    description="List all available trading products",
                ),
                Resource(
                    uri="coinbase://orders",
                    name="Orders",
                    mimeType="application/json",
                    description="List all orders (open and historical)",
                ),
                Resource(
                    uri="coinbase://fills",
                    name="Fills",
                    mimeType="application/json",
                    description="List all executed fills",
                ),
            ]

        @self.server.read_resource()
        async def read_resource(uri: str) -> str:
            """Read resource by URI"""
            client = await self._get_client()

            if uri == "coinbase://accounts":
                accounts = await client.list_accounts()
                return self._format_accounts(accounts)

            elif uri == "coinbase://products":
                products = await client.list_products()
                return self._format_products(products)

            elif uri == "coinbase://orders":
                orders = await client.list_orders(limit=50)
                return self._format_orders(orders)

            elif uri == "coinbase://fills":
                fills = await client.list_fills(limit=50)
                return self._format_fills(fills)

            elif uri.startswith("coinbase://account/"):
                account_id = uri.split("/")[-1]
                account = await client.get_account(account_id)
                return self._format_account(account)

            elif uri.startswith("coinbase://product/"):
                product_id = uri.split("/")[-1]
                product = await client.get_product(product_id)
                ticker = await client.get_product_ticker(product_id)
                return self._format_product_with_ticker(product, ticker)

            elif uri.startswith("coinbase://order/"):
                order_id = uri.split("/")[-1]
                order = await client.get_order(order_id)
                return self._format_order(order)

            else:
                raise ValueError(f"Unknown resource URI: {uri}")

    # ========================================================================
    # Tool Handlers
    # ========================================================================

    def _register_tool_handlers(self) -> None:
        """Register MCP tool handlers"""

        @self.server.list_tools()
        async def list_tools() -> List[Tool]:
            """List available tools"""
            return [
                Tool(
                    name="get_market_data",
                    description="Get real-time market data for a trading product",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "product_id": {
                                "type": "string",
                                "description": "Product ID (e.g., BTC-USD, ETH-USD)",
                            }
                        },
                        "required": ["product_id"],
                    },
                ),
                Tool(
                    name="get_historical_candles",
                    description="Get historical price candles for a product",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "product_id": {
                                "type": "string",
                                "description": "Product ID (e.g., BTC-USD)",
                            },
                            "start": {
                                "type": "integer",
                                "description": "Start time (Unix timestamp)",
                            },
                            "end": {"type": "integer", "description": "End time (Unix timestamp)"},
                            "granularity": {
                                "type": "string",
                                "description": "Candle size (ONE_MINUTE, FIVE_MINUTE, etc.)",
                                "default": "ONE_MINUTE",
                            },
                        },
                        "required": ["product_id", "start", "end"],
                    },
                ),
                Tool(
                    name="place_market_order",
                    description="Place a market order (immediate execution at current price)",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "product_id": {"type": "string", "description": "Product ID"},
                            "side": {
                                "type": "string",
                                "enum": ["BUY", "SELL"],
                                "description": "Order side",
                            },
                            "size": {
                                "type": "string",
                                "description": "Amount in base currency (optional if quote_size provided)",
                            },
                            "quote_size": {
                                "type": "string",
                                "description": "Amount in quote currency (optional if size provided)",
                            },
                        },
                        "required": ["product_id", "side"],
                    },
                ),
                Tool(
                    name="place_limit_order",
                    description="Place a limit order (execute only at specified price or better)",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "product_id": {"type": "string", "description": "Product ID"},
                            "side": {
                                "type": "string",
                                "enum": ["BUY", "SELL"],
                                "description": "Order side",
                            },
                            "size": {"type": "string", "description": "Amount in base currency"},
                            "limit_price": {"type": "string", "description": "Limit price"},
                            "post_only": {
                                "type": "boolean",
                                "description": "Post-only flag (maker-only)",
                                "default": False,
                            },
                        },
                        "required": ["product_id", "side", "size", "limit_price"],
                    },
                ),
                Tool(
                    name="cancel_order",
                    description="Cancel an open order",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "order_id": {"type": "string", "description": "Order UUID to cancel"}
                        },
                        "required": ["order_id"],
                    },
                ),
                Tool(
                    name="get_account_balance",
                    description="Get balance for a specific account",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "account_id": {
                                "type": "string",
                                "description": "Account UUID (optional, returns all if not provided)",
                            }
                        },
                    },
                ),
            ]

        @self.server.call_tool()
        async def call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
            """Execute tool by name"""
            client = await self._get_client()

            try:
                if name == "get_market_data":
                    result = await self._get_market_data(client, arguments)

                elif name == "get_historical_candles":
                    result = await self._get_historical_candles(client, arguments)

                elif name == "place_market_order":
                    result = await self._place_market_order(client, arguments)

                elif name == "place_limit_order":
                    result = await self._place_limit_order(client, arguments)

                elif name == "cancel_order":
                    result = await self._cancel_order(client, arguments)

                elif name == "get_account_balance":
                    result = await self._get_account_balance(client, arguments)

                else:
                    raise ValueError(f"Unknown tool: {name}")

                return [TextContent(type="text", text=result)]

            except Exception as e:
                self.logger.error("tool_execution_error", tool=name, error=str(e))
                return [TextContent(type="text", text=f"Error: {str(e)}")]

    # ========================================================================
    # Prompt Handlers
    # ========================================================================

    def _register_prompt_handlers(self) -> None:
        """Register MCP prompt handlers"""

        @self.server.list_prompts()
        async def list_prompts() -> List[Dict[str, Any]]:
            """List available prompts"""
            return [
                {
                    "name": "market_analysis",
                    "description": "Analyze current market conditions for a product",
                    "arguments": [
                        {
                            "name": "product_id",
                            "description": "Product ID to analyze",
                            "required": True,
                        }
                    ],
                },
                {
                    "name": "trade_execution",
                    "description": "Execute a trade with risk validation",
                    "arguments": [
                        {"name": "product_id", "description": "Product ID", "required": True},
                        {"name": "side", "description": "BUY or SELL", "required": True},
                        {"name": "size", "description": "Trade size", "required": True},
                    ],
                },
            ]

    # ========================================================================
    # Tool Implementation Methods
    # ========================================================================

    async def _get_market_data(
        self, client: CoinbaseAPIClient, args: Dict[str, Any]
    ) -> str:
        """Get market data for a product"""
        product_id = args["product_id"]
        ticker = await client.get_product_ticker(product_id)
        product = await client.get_product(product_id)

        return f"""Market Data for {product_id}:
- Price: ${ticker.get('price', 'N/A')}
- 24h Volume: {ticker.get('volume', 'N/A')}
- Best Bid: ${ticker.get('best_bid', 'N/A')}
- Best Ask: ${ticker.get('best_ask', 'N/A')}
- Quote Increment: {product.get('quote_increment', 'N/A')}
- Base Increment: {product.get('base_increment', 'N/A')}
"""

    async def _get_historical_candles(
        self, client: CoinbaseAPIClient, args: Dict[str, Any]
    ) -> str:
        """Get historical candles"""
        candles = await client.get_product_candles(
            product_id=args["product_id"],
            start=args["start"],
            end=args["end"],
            granularity=args.get("granularity", "ONE_MINUTE"),
        )

        result = f"Historical candles for {args['product_id']} ({len(candles)} candles):\n\n"
        for candle in candles[:10]:  # Show first 10
            result += f"Time: {candle.get('start')}, O: {candle.get('open')}, H: {candle.get('high')}, L: {candle.get('low')}, C: {candle.get('close')}, V: {candle.get('volume')}\n"

        if len(candles) > 10:
            result += f"\n... and {len(candles) - 10} more candles"

        return result

    async def _place_market_order(
        self, client: CoinbaseAPIClient, args: Dict[str, Any]
    ) -> str:
        """Place market order"""
        # Validate order before placing
        validation = await self._validate_order(client, args)
        if not validation["valid"]:
            return f"Order validation failed: {validation['reason']}"

        result = await client.create_market_order(
            product_id=args["product_id"],
            side=OrderSide(args["side"]),
            size=args.get("size"),
            quote_size=args.get("quote_size"),
        )

        order_id = result.get("success_response", {}).get("order_id", "N/A")
        return f"Market order placed successfully. Order ID: {order_id}"

    async def _place_limit_order(
        self, client: CoinbaseAPIClient, args: Dict[str, Any]
    ) -> str:
        """Place limit order"""
        # Validate order before placing
        validation = await self._validate_order(client, args)
        if not validation["valid"]:
            return f"Order validation failed: {validation['reason']}"

        result = await client.create_limit_order(
            product_id=args["product_id"],
            side=OrderSide(args["side"]),
            size=args["size"],
            limit_price=args["limit_price"],
            post_only=args.get("post_only", False),
        )

        order_id = result.get("success_response", {}).get("order_id", "N/A")
        return f"Limit order placed successfully. Order ID: {order_id}"

    async def _cancel_order(
        self, client: CoinbaseAPIClient, args: Dict[str, Any]
    ) -> str:
        """Cancel order"""
        result = await client.cancel_order(args["order_id"])
        return f"Order cancelled successfully: {result}"

    async def _get_account_balance(
        self, client: CoinbaseAPIClient, args: Dict[str, Any]
    ) -> str:
        """Get account balance"""
        if account_id := args.get("account_id"):
            account = await client.get_account(account_id)
            return self._format_account(account)
        else:
            accounts = await client.list_accounts()
            return self._format_accounts(accounts)

    async def _validate_order(
        self, client: CoinbaseAPIClient, args: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Validate order against risk limits and trading rules.

        Returns:
            Dictionary with 'valid' (bool) and 'reason' (str) keys
        """
        # Get current account balance
        accounts = await client.list_accounts()

        # TODO: Implement full risk validation based on settings.trading limits
        # For now, basic validation

        product_id = args.get("product_id", "")
        if not product_id:
            return {"valid": False, "reason": "Product ID required"}

        side = args.get("side", "")
        if side not in ["BUY", "SELL"]:
            return {"valid": False, "reason": "Invalid side (must be BUY or SELL)"}

        return {"valid": True, "reason": ""}

    # ========================================================================
    # Formatting Methods
    # ========================================================================

    def _format_accounts(self, accounts: List[Dict[str, Any]]) -> str:
        """Format accounts list for display"""
        result = f"Trading Accounts ({len(accounts)}):\n\n"
        for account in accounts:
            result += f"- {account.get('currency', 'N/A')}: "
            result += f"{account.get('available_balance', {}).get('value', '0')} available, "
            result += f"{account.get('hold', {}).get('value', '0')} on hold\n"
        return result

    def _format_account(self, account: Dict[str, Any]) -> str:
        """Format single account for display"""
        return f"""Account: {account.get('uuid', 'N/A')}
Currency: {account.get('currency', 'N/A')}
Available: {account.get('available_balance', {}).get('value', '0')}
Hold: {account.get('hold', {}).get('value', '0')}
"""

    def _format_products(self, products: List[Dict[str, Any]]) -> str:
        """Format products list for display"""
        result = f"Trading Products ({len(products)}):\n\n"
        for product in products[:20]:  # Show first 20
            result += f"- {product.get('product_id', 'N/A')}: "
            result += f"{product.get('base_currency', 'N/A')}/{product.get('quote_currency', 'N/A')}\n"
        if len(products) > 20:
            result += f"\n... and {len(products) - 20} more products"
        return result

    def _format_product_with_ticker(
        self, product: Dict[str, Any], ticker: Dict[str, Any]
    ) -> str:
        """Format product with ticker data"""
        return f"""Product: {product.get('product_id', 'N/A')}
Base: {product.get('base_currency', 'N/A')}
Quote: {product.get('quote_currency', 'N/A')}
Price: ${ticker.get('price', 'N/A')}
24h Volume: {ticker.get('volume', 'N/A')}
Best Bid: ${ticker.get('best_bid', 'N/A')}
Best Ask: ${ticker.get('best_ask', 'N/A')}
"""

    def _format_orders(self, orders: List[Dict[str, Any]]) -> str:
        """Format orders list for display"""
        result = f"Orders ({len(orders)}):\n\n"
        for order in orders:
            result += f"- {order.get('order_id', 'N/A')[:8]}... "
            result += f"{order.get('product_id', 'N/A')} "
            result += f"{order.get('side', 'N/A')} "
            result += f"{order.get('status', 'N/A')}\n"
        return result

    def _format_order(self, order: Dict[str, Any]) -> str:
        """Format single order for display"""
        return f"""Order: {order.get('order_id', 'N/A')}
Product: {order.get('product_id', 'N/A')}
Side: {order.get('side', 'N/A')}
Type: {order.get('order_type', 'N/A')}
Status: {order.get('status', 'N/A')}
Size: {order.get('order_configuration', {}).get('base_size', 'N/A')}
"""

    def _format_fills(self, fills: List[Dict[str, Any]]) -> str:
        """Format fills list for display"""
        result = f"Fills ({len(fills)}):\n\n"
        for fill in fills:
            result += f"- {fill.get('product_id', 'N/A')} "
            result += f"{fill.get('side', 'N/A')} "
            result += f"{fill.get('size', 'N/A')} @ "
            result += f"${fill.get('price', 'N/A')}\n"
        return result

    # ========================================================================
    # Server Lifecycle
    # ========================================================================

    async def run(self) -> None:
        """Run the MCP server"""
        self.logger.info("starting_mcp_server", server_name="coinbase-trading")

        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                self.server.create_initialization_options(),
            )

    async def cleanup(self) -> None:
        """Cleanup resources"""
        if self.coinbase_client:
            await self.coinbase_client.__aexit__(None, None, None)


async def main() -> None:
    """Main entry point"""
    server = CoinbaseMCPServer()
    try:
        await server.run()
    finally:
        await server.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
