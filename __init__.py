"""
Backend package for Real-Time Trading Analytics Platform

This package contains all backend components:
- data_ingestion: WebSocket data streaming from Binance
- storage: Database management and data persistence
- analytics_engine: Quantitative analytics and computations
- alert_manager: Alert creation and monitoring
"""

__version__ = '1.0.0'
__author__ = 'Trading Analytics Team'

# Import main classes for easy access
from .data_ingestion import DataIngestionService
from .storage import DatabaseManager
from .analytics_engine import AnalyticsEngine
from .alert_manager import AlertManager

__all__ = [
    'DataIngestionService',
    'DatabaseManager',
    'AnalyticsEngine',
    'AlertManager'
]