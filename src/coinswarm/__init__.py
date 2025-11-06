"""
Coinswarm - Intelligent Multi-Agent Trading System

A memory-augmented multi-agent reinforcement learning system for cryptocurrency
and equities trading with quorum-governed decision making.
"""

__version__ = "0.1.0"
__author__ = "Coinswarm Team"
__description__ = "Intelligent Multi-Agent Trading System with Memory-Augmented MARL"

# Expose commonly used components
from coinswarm.core.config import settings

__all__ = ["__version__", "settings"]
