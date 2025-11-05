"""
Soundness tests for Binance Data Ingestor

Tests determinism, latency, and data consistency.
"""

import pytest
import time
from datetime import datetime
from unittest.mock import AsyncMock, patch

from coinswarm.data_ingest.exchanges.binance import BinanceIngestor
from coinswarm.data_ingest.base import DataPoint


class TestBinanceDeterminism:
    """Test Binance ingestor deterministic behavior"""

    def test_symbol_normalization_deterministic(self):
        """Test that symbol normalization is deterministic"""
        ingestor = BinanceIngestor()

        known_symbols = ["BTC-USD", "ETH-USD", "SOL-USD"]

        # Same input should always produce same output
        for _ in range(10):
            result1 = ingestor._normalize_symbol_from_binance("BTCUSDT", known_symbols)
            result2 = ingestor._normalize_symbol_from_binance("BTCUSDT", known_symbols)
            assert result1 == result2

            result3 = ingestor._normalize_symbol_from_binance("ETHUSDT", known_symbols)
            result4 = ingestor._normalize_symbol_from_binance("ETHUSDT", known_symbols)
            assert result3 == result4

    def test_trade_parsing_deterministic(self):
        """Test that trade data parsing is deterministic"""
        ingestor = BinanceIngestor()

        trade_data = {
            "s": "BTCUSDT",
            "t": 12345,
            "p": "50000.00",
            "q": "0.5",
            "T": 1704110400000,
            "m": False,
        }

        symbols = ["BTC-USD"]

        # Parse multiple times
        results = []
        for _ in range(5):
            dp = ingestor._parse_trade(trade_data, symbols)
            results.append((dp.data["price"], dp.data["quantity"], dp.data["trade_id"]))

        # All results should be identical
        assert all(r == results[0] for r in results)

    def test_kline_parsing_deterministic(self):
        """Test that kline parsing is deterministic"""
        ingestor = BinanceIngestor()

        kline_data = {
            "s": "BTCUSDT",
            "k": {
                "t": 1704110400000,
                "i": "1m",
                "o": "50000.00",
                "h": "50500.00",
                "l": "49800.00",
                "c": "50200.00",
                "v": "100.5",
                "x": True,
            },
        }

        symbols = ["BTC-USD"]

        # Parse multiple times
        ohlc_values = []
        for _ in range(5):
            dp = ingestor._parse_kline(kline_data, symbols)
            ohlc_values.append(
                (
                    dp.data["open"],
                    dp.data["high"],
                    dp.data["low"],
                    dp.data["close"],
                    dp.data["volume"],
                )
            )

        # All OHLC values should be identical
        assert all(v == ohlc_values[0] for v in ohlc_values)

    def test_orderbook_parsing_deterministic(self):
        """Test that orderbook parsing is deterministic"""
        ingestor = BinanceIngestor()

        orderbook_data = {
            "s": "BTCUSDT",
            "E": 1704110400000,
            "b": [["50000", "1.5"], ["49999", "2.0"]],
            "a": [["50001", "1.0"], ["50002", "1.5"]],
        }

        symbols = ["BTC-USD"]

        # Parse multiple times
        spreads = []
        for _ in range(5):
            dp = ingestor._parse_orderbook(orderbook_data, symbols)
            best_bid = dp.data["bids"][0][0]
            best_ask = dp.data["asks"][0][0]
            spreads.append(best_ask - best_bid)

        # All spreads should be identical
        assert all(s == spreads[0] for s in spreads)

    @pytest.mark.asyncio
    async def test_quality_score_calculation_deterministic(self):
        """Test that quality score calculation is deterministic"""
        ingestor = BinanceIngestor()

        # Mock OHLCV data
        ohlcv = [1704110400000, 50000.0, 50500.0, 49800.0, 50200.0, 100.5]

        # Calculate quality score multiple times
        scores = []
        for _ in range(5):
            score = ingestor._calculate_quality_score(ohlcv)
            scores.append(score)

        # All scores should be identical
        assert all(s == scores[0] for s in scores)
        # Score should be in valid range
        assert all(0.0 <= s <= 1.0 for s in scores)


class TestBinanceLatency:
    """Test Binance ingestor latency requirements"""

    def test_symbol_normalization_latency(self):
        """Test that symbol normalization is fast"""
        ingestor = BinanceIngestor()

        known_symbols = ["BTC-USD", "ETH-USD", "SOL-USD", "AVAX-USD", "DOT-USD"]
        raw_symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "AVAXUSDT", "DOTUSDT"] * 20

        start = time.perf_counter()
        for raw in raw_symbols:
            ingestor._normalize_symbol_from_binance(raw, known_symbols)
        duration = time.perf_counter() - start

        # 100 normalizations should be < 50ms
        assert duration < 0.05

    def test_trade_parsing_latency(self):
        """Test that trade parsing is fast"""
        ingestor = BinanceIngestor()

        trade_data = {
            "s": "BTCUSDT",
            "t": 12345,
            "p": "50000.00",
            "q": "0.5",
            "T": 1704110400000,
            "m": False,
        }

        symbols = ["BTC-USD"]

        start = time.perf_counter()
        for _ in range(100):
            ingestor._parse_trade(trade_data, symbols)
        duration = time.perf_counter() - start

        # 100 trade parses should be < 50ms
        assert duration < 0.05

    def test_kline_parsing_latency(self):
        """Test that kline parsing is fast"""
        ingestor = BinanceIngestor()

        kline_data = {
            "s": "BTCUSDT",
            "k": {
                "t": 1704110400000,
                "i": "1m",
                "o": "50000.00",
                "h": "50500.00",
                "l": "49800.00",
                "c": "50200.00",
                "v": "100.5",
                "x": True,
            },
        }

        symbols = ["BTC-USD"]

        start = time.perf_counter()
        for _ in range(100):
            ingestor._parse_kline(kline_data, symbols)
        duration = time.perf_counter() - start

        # 100 kline parses should be < 50ms
        assert duration < 0.05

    def test_orderbook_parsing_latency(self):
        """Test that orderbook parsing is fast"""
        ingestor = BinanceIngestor()

        orderbook_data = {
            "s": "BTCUSDT",
            "E": 1704110400000,
            "b": [["50000", "1.5"], ["49999", "2.0"]] * 10,
            "a": [["50001", "1.0"], ["50002", "1.5"]] * 10,
        }

        symbols = ["BTC-USD"]

        start = time.perf_counter()
        for _ in range(50):
            ingestor._parse_orderbook(orderbook_data, symbols)
        duration = time.perf_counter() - start

        # 50 orderbook parses (20 levels each) should be < 100ms
        assert duration < 0.1

    def test_quality_score_calculation_latency(self):
        """Test that quality score calculation is fast"""
        ingestor = BinanceIngestor()

        ohlcv_data = [
            [1704110400000, 50000.0, 50500.0, 49800.0, 50200.0, 100.5]
            for _ in range(100)
        ]

        start = time.perf_counter()
        for ohlcv in ohlcv_data:
            ingestor._calculate_quality_score(ohlcv)
        duration = time.perf_counter() - start

        # 100 quality score calculations should be < 50ms
        assert duration < 0.05

    @pytest.mark.asyncio
    async def test_datapoint_creation_latency(self):
        """Test that DataPoint creation is fast"""
        ingestor = BinanceIngestor()

        start = time.perf_counter()
        for i in range(1000):
            dp = DataPoint(
                source="binance",
                symbol="BTC-USD",
                timeframe="tick",
                timestamp=datetime.now(),
                data={"price": 50000 + i, "volume": 1.0},
            )
        duration = time.perf_counter() - start

        # 1000 DataPoint creations should be < 100ms
        assert duration < 0.1
