"""
Cross-Pair Pattern Detection

Detects patterns ACROSS multiple trading pairs:
- Correlation patterns
- Cointegration (spread trading)
- Lead-lag relationships
- Divergence patterns
"""

from .arbitrage_detector import ArbitrageDetector
from .cointegration_tester import CointegrationTester
from .correlation_detector import CorrelationDetector
from .lead_lag_analyzer import LeadLagAnalyzer

__all__ = [
    "CorrelationDetector",
    "CointegrationTester",
    "LeadLagAnalyzer",
    "ArbitrageDetector",
]
