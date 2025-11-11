"""
Cross-Pair Pattern Detection

Detects patterns ACROSS multiple trading pairs:
- Correlation patterns
- Cointegration (spread trading)
- Lead-lag relationships
- Divergence patterns
"""

from .correlation_detector import CorrelationDetector
from .cointegration_tester import CointegrationTester
from .lead_lag_analyzer import LeadLagAnalyzer
from .arbitrage_detector import ArbitrageDetector

__all__ = [
    "CorrelationDetector",
    "CointegrationTester",
    "LeadLagAnalyzer",
    "ArbitrageDetector",
]
