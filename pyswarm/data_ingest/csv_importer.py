"""
CSV Data Importer

Import historical data from CSV files (Binance format or custom).

Supports:
- Binance historical data archive (https://data.binance.vision/)
- Custom CSV files
- Multiple symbols from directory
"""

import csv
import logging
from datetime import datetime
from pathlib import Path

from coinswarm.data_ingest.base import DataPoint

logger = logging.getLogger(__name__)


class CSVImporter:
    """
    Import historical data from CSV files.

    Binance CSV format:
    timestamp, open, high, low, close, volume, close_time, quote_volume,
    trades, taker_buy_base, taker_buy_quote, ignore
    """

    def __init__(self, data_dir: str = "data/historical"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)

    def import_binance_csv(
        self,
        file_path: str,
        symbol: str = None,
        timeframe: str = "1h"
    ) -> list[DataPoint]:
        """
        Import Binance historical data CSV.

        CSV format (from https://data.binance.vision/):
        open_time, open, high, low, close, volume, close_time, quote_volume,
        trades, taker_buy_base, taker_buy_quote, ignore

        Args:
            file_path: Path to CSV file
            symbol: Trading pair (e.g., "BTCUSDT") - extracted from filename if None
            timeframe: Candle interval (e.g., "1h")

        Returns:
            List of DataPoint objects
        """

        if symbol is None:
            # Extract from filename (e.g., "BTCUSDT-1h-2024-10.csv")
            symbol = Path(file_path).stem.split('-')[0]

        logger.info(f"Importing {symbol} from {file_path}")

        data_points = []

        try:
            with open(file_path) as f:
                reader = csv.reader(f)

                for row in reader:
                    try:
                        # Parse Binance CSV format
                        timestamp_ms = int(row[0])
                        open_price = float(row[1])
                        high = float(row[2])
                        low = float(row[3])
                        close = float(row[4])
                        volume = float(row[5])

                        # Convert timestamp
                        timestamp = datetime.fromtimestamp(timestamp_ms / 1000)

                        # Create DataPoint
                        data_point = DataPoint(
                            source="binance_csv",
                            symbol=symbol,
                            timeframe=timeframe,
                            timestamp=timestamp,
                            data={
                                "open": open_price,
                                "high": high,
                                "low": low,
                                "close": close,
                                "price": close,  # Use close as price
                                "volume": volume
                            },
                            quality_score=1.0
                        )

                        data_points.append(data_point)

                    except (ValueError, IndexError) as e:
                        logger.warning(f"Skipping invalid row: {row} - {e}")
                        continue

            logger.info(f"Imported {len(data_points)} candles for {symbol}")

            if data_points:
                logger.info(f"Date range: {data_points[0].timestamp} to {data_points[-1].timestamp}")

            return data_points

        except Exception as e:
            logger.error(f"Error importing {file_path}: {e}")
            return []

    def import_custom_csv(
        self,
        file_path: str,
        symbol: str,
        timestamp_col: str = "timestamp",
        price_col: str = "price",
        volume_col: str = "volume",
        timeframe: str = "1h"
    ) -> list[DataPoint]:
        """
        Import custom CSV with configurable columns.

        CSV must have headers.

        Args:
            file_path: Path to CSV file
            symbol: Trading pair
            timestamp_col: Column name for timestamp
            price_col: Column name for price
            volume_col: Column name for volume
            timeframe: Candle interval

        Returns:
            List of DataPoint objects
        """

        logger.info(f"Importing {symbol} from custom CSV: {file_path}")

        data_points = []

        try:
            with open(file_path) as f:
                reader = csv.DictReader(f)

                for row in reader:
                    try:
                        # Parse timestamp (multiple formats)
                        timestamp_str = row[timestamp_col]

                        # Try ISO format first
                        try:
                            timestamp = datetime.fromisoformat(timestamp_str)
                        except:
                            # Try Unix timestamp
                            try:
                                timestamp = datetime.fromtimestamp(float(timestamp_str))
                            except:
                                # Try other formats
                                timestamp = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")

                        # Parse price and volume
                        price = float(row[price_col])
                        volume = float(row.get(volume_col, 0))

                        # Create DataPoint
                        data_point = DataPoint(
                            source="custom_csv",
                            symbol=symbol,
                            timeframe=timeframe,
                            timestamp=timestamp,
                            data={
                                "price": price,
                                "volume": volume,
                                **{k: float(v) for k, v in row.items()
                                   if k not in [timestamp_col] and v.replace('.', '').replace('-', '').isdigit()}
                            },
                            quality_score=1.0
                        )

                        data_points.append(data_point)

                    except Exception as e:
                        logger.warning(f"Skipping invalid row: {row} - {e}")
                        continue

            logger.info(f"Imported {len(data_points)} data points for {symbol}")

            return data_points

        except Exception as e:
            logger.error(f"Error importing {file_path}: {e}")
            return []

    def import_directory(
        self,
        directory: str = None,
        pattern: str = "*.csv"
    ) -> dict:
        """
        Import all CSV files from a directory.

        Args:
            directory: Directory to scan (defaults to self.data_dir)
            pattern: Filename pattern (e.g., "*.csv", "BTCUSDT*.csv")

        Returns:
            Dict mapping symbol → List[DataPoint]
        """

        if directory is None:
            directory = self.data_dir

        directory = Path(directory)

        logger.info(f"Scanning {directory} for {pattern}")

        all_data = {}

        for csv_file in directory.glob(pattern):
            # Extract symbol from filename
            symbol = csv_file.stem.split('-')[0]

            data = self.import_binance_csv(str(csv_file), symbol=symbol)

            if data:
                all_data[symbol] = data

        logger.info(f"Imported data for {len(all_data)} symbols")

        return all_data


def download_binance_data_instructions():
    """
    Print instructions for downloading Binance historical data.
    """

    print("""
    ╔════════════════════════════════════════════════════════════════╗
    ║  HOW TO DOWNLOAD BINANCE HISTORICAL DATA                       ║
    ╚════════════════════════════════════════════════════════════════╝

    Option 1: Via Browser
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    1. Go to: https://data.binance.vision/
    2. Navigate: data/spot/monthly/klines/BTCUSDT/1h/
    3. Download files like: BTCUSDT-1h-2024-10.zip
    4. Unzip to: Coinswarm/data/historical/

    Option 2: Via Command Line (Linux/Mac)
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    cd Coinswarm
    mkdir -p data/historical

    # Download BTC data (last 3 months)
    wget https://data.binance.vision/data/spot/monthly/klines/BTCUSDT/1h/BTCUSDT-1h-2024-08.zip
    wget https://data.binance.vision/data/spot/monthly/klines/BTCUSDT/1h/BTCUSDT-1h-2024-09.zip
    wget https://data.binance.vision/data/spot/monthly/klines/BTCUSDT/1h/BTCUSDT-1h-2024-10.zip

    # Download ETH data
    wget https://data.binance.vision/data/spot/monthly/klines/ETHUSDT/1h/ETHUSDT-1h-2024-08.zip
    wget https://data.binance.vision/data/spot/monthly/klines/ETHUSDT/1h/ETHUSDT-1h-2024-09.zip
    wget https://data.binance.vision/data/spot/monthly/klines/ETHUSDT/1h/ETHUSDT-1h-2024-10.zip

    # Download SOL data
    wget https://data.binance.vision/data/spot/monthly/klines/SOLUSDT/1h/SOLUSDT-1h-2024-08.zip
    wget https://data.binance.vision/data/spot/monthly/klines/SOLUSDT/1h/SOLUSDT-1h-2024-09.zip
    wget https://data.binance.vision/data/spot/monthly/klines/SOLUSDT/1h/SOLUSDT-1h-2024-10.zip

    # Unzip all
    unzip -d data/historical "*.zip"

    Option 3: Via Python
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    python scripts/download_binance_data.py --symbols BTCUSDT ETHUSDT SOLUSDT --months 3

    Then use:
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    from coinswarm.data_ingest.csv_importer import CSVImporter

    importer = CSVImporter(data_dir="data/historical")
    data = importer.import_directory()

    print(f"Loaded {len(data)} symbols")
    """)


if __name__ == "__main__":
    # Print download instructions
    download_binance_data_instructions()
