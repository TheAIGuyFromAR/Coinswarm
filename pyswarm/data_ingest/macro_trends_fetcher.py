"""
Macro Economic Trends Fetcher

Fetches macro economic indicators for correlation with crypto prices.

Data Sources:
1. FRED (Federal Reserve Economic Data) - FREE API
2. Yahoo Finance - FREE (for indices)
3. Quandl - FREE tier available

Indicators:
- Fed Funds Rate (interest rates)
- CPI (inflation)
- Unemployment Rate
- S&P 500 (stock market)
- DXY (Dollar Index)
- Gold Price
- 10Y Treasury Yield
"""

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta

try:
    import httpx
except ImportError:
    import requests as httpx

from coinswarm.data_ingest.base import DataPoint

logger = logging.getLogger(__name__)


@dataclass
class MacroIndicator:
    """Single macro economic data point"""
    name: str
    value: float
    timestamp: datetime
    unit: str  # "percent", "index", "usd"


class MacroTrendsFetcher:
    """
    Fetch macro economic data from FRED and other sources.

    FRED API is free but requires API key:
    https://fred.stlouisfed.org/docs/api/api_key.html
    """

    def __init__(self, fred_api_key: str | None = None):
        self.fred_api_key = fred_api_key
        self.fred_url = "https://api.stlouisfed.org/fred/series/observations"

        # Macro indicators to track
        self.indicators = {
            "FEDFUNDS": {
                "name": "Fed Funds Rate",
                "unit": "percent",
                "description": "Federal funds effective rate (interest rates)"
            },
            "CPIAUCSL": {
                "name": "CPI",
                "unit": "index",
                "description": "Consumer Price Index (inflation)"
            },
            "UNRATE": {
                "name": "Unemployment Rate",
                "unit": "percent",
                "description": "US unemployment rate"
            },
            "DGS10": {
                "name": "10Y Treasury",
                "unit": "percent",
                "description": "10-year treasury constant maturity rate"
            },
            "DEXUSEU": {
                "name": "Dollar Index",
                "unit": "index",
                "description": "US Dollar vs Euro exchange rate"
            },
            "GOLDAMGBD228NLBM": {
                "name": "Gold Price",
                "unit": "usd",
                "description": "Gold fixing price per troy ounce"
            }
        }

    async def fetch_all_indicators(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> dict[str, list[MacroIndicator]]:
        """
        Fetch all macro indicators for date range.

        Args:
            start_date: Start date
            end_date: End date

        Returns:
            Dict mapping indicator name → list of data points
        """

        if not self.fred_api_key:
            logger.warning("FRED API key not provided. Returning empty macro data.")
            logger.info("Get a free API key: https://fred.stlouisfed.org/docs/api/api_key.html")
            return {}

        logger.info(f"Fetching {len(self.indicators)} macro indicators...")
        logger.info(f"Date range: {start_date.date()} to {end_date.date()}")

        all_data = {}

        # Fetch all indicators in parallel
        tasks = [
            self._fetch_indicator(
                series_id=series_id,
                start_date=start_date,
                end_date=end_date
            )
            for series_id in self.indicators.keys()
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        for series_id, data in zip(self.indicators.keys(), results, strict=False):
            if isinstance(data, Exception):
                logger.warning(f"✗ {series_id}: {data}")
            else:
                all_data[series_id] = data
                logger.info(f"✓ {self.indicators[series_id]['name']}: {len(data)} data points")

        return all_data

    async def _fetch_indicator(
        self,
        series_id: str,
        start_date: datetime,
        end_date: datetime
    ) -> list[MacroIndicator]:
        """
        Fetch a single indicator from FRED.

        FRED API docs: https://fred.stlouisfed.org/docs/api/fred/
        """

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    self.fred_url,
                    params={
                        "series_id": series_id,
                        "api_key": self.fred_api_key,
                        "file_type": "json",
                        "observation_start": start_date.strftime("%Y-%m-%d"),
                        "observation_end": end_date.strftime("%Y-%m-%d")
                    },
                    timeout=30.0
                )
                response.raise_for_status()
                data = response.json()

                indicators = []

                for obs in data.get("observations", []):
                    try:
                        value = obs.get("value")
                        if value == ".":  # FRED uses "." for missing data
                            continue

                        indicator = MacroIndicator(
                            name=self.indicators[series_id]["name"],
                            value=float(value),
                            timestamp=datetime.strptime(obs["date"], "%Y-%m-%d"),
                            unit=self.indicators[series_id]["unit"]
                        )

                        indicators.append(indicator)

                    except (ValueError, KeyError) as e:
                        logger.debug(f"Skipping invalid observation: {obs} - {e}")
                        continue

                return indicators

        except Exception as e:
            logger.error(f"Error fetching {series_id}: {e}")
            raise

    def convert_to_datapoints(
        self,
        macro_data: dict[str, list[MacroIndicator]]
    ) -> list[DataPoint]:
        """
        Convert macro indicators to DataPoint objects.

        Creates one DataPoint per date with all indicators.
        """

        # Group by date
        by_date: dict[datetime, dict] = {}

        for _series_id, indicators in macro_data.items():
            for indicator in indicators:
                date = indicator.timestamp.date()

                if date not in by_date:
                    by_date[date] = {}

                by_date[date][indicator.name.lower().replace(" ", "_")] = indicator.value

        # Convert to DataPoints
        data_points = []

        for date, values in sorted(by_date.items()):
            data_point = DataPoint(
                source="fred",
                symbol="MACRO",
                timeframe="1d",
                timestamp=datetime.combine(date, datetime.min.time()),
                data=values,
                quality_score=1.0
            )

            data_points.append(data_point)

        return data_points

    async def get_current_rates(self) -> dict[str, float]:
        """
        Get current values for all indicators.

        Useful for live trading.
        """

        end_date = datetime.now()
        start_date = end_date - timedelta(days=7)  # Last week

        all_data = await self.fetch_all_indicators(start_date, end_date)

        current_values = {}

        for _series_id, indicators in all_data.items():
            if indicators:
                # Get most recent value
                latest = indicators[-1]
                current_values[latest.name] = latest.value

        return current_values


# Alternative free sources (no API key needed)

async def fetch_sp500_yahoo(start_date: datetime, end_date: datetime) -> list[MacroIndicator]:
    """
    Fetch S&P 500 from Yahoo Finance.

    No API key needed.
    """

    try:
        import yfinance as yf

        ticker = yf.Ticker("^GSPC")  # S&P 500
        hist = ticker.history(start=start_date, end=end_date)

        indicators = []

        for date, row in hist.iterrows():
            indicator = MacroIndicator(
                name="S&P 500",
                value=float(row["Close"]),
                timestamp=date.to_pydatetime(),
                unit="index"
            )

            indicators.append(indicator)

        logger.info(f"✓ S&P 500: {len(indicators)} data points (Yahoo Finance)")

        return indicators

    except ImportError:
        logger.warning("yfinance not installed. Install: pip install yfinance")
        return []
    except Exception as e:
        logger.error(f"Error fetching S&P 500: {e}")
        return []


# Example usage
if __name__ == "__main__":
    async def demo():
        # Demo without API key (will return empty)
        fetcher = MacroTrendsFetcher()

        print("\n" + "="*70)
        print("FRED API SETUP INSTRUCTIONS")
        print("="*70)
        print("\n1. Go to: https://fred.stlouisfed.org/")
        print("2. Create free account")
        print("3. Request API key: https://fred.stlouisfed.org/docs/api/api_key.html")
        print("4. Set environment variable: export FRED_API_KEY=your_key_here")
        print("\nOr pass to constructor:")
        print("  fetcher = MacroTrendsFetcher(fred_api_key='your_key')")
        print("\nIndicators available:")

        for series_id, info in fetcher.indicators.items():
            print(f"  - {info['name']:20} ({series_id})")
            print(f"    {info['description']}")

        print("\n" + "="*70 + "\n")

        # Demo with API key (if available)
        import os
        fred_key = os.getenv("FRED_API_KEY")

        if fred_key:
            fetcher = MacroTrendsFetcher(fred_api_key=fred_key)

            end = datetime.now()
            start = end - timedelta(days=90)

            data = await fetcher.fetch_all_indicators(start, end)

            print(f"\nFetched macro data for {len(data)} indicators\n")

            # Show current rates
            current = await fetcher.get_current_rates()

            print("Current Macro Indicators:")
            print("-"*70)
            for name, value in current.items():
                print(f"  {name:20} {value:>10.2f}")

            print()

    asyncio.run(demo())
