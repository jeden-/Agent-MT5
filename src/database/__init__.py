"""
Moduł zarządzający bazą danych PostgreSQL
"""

from .db_manager import DatabaseManager
from .models import (
    Instrument, TradingSetup, TradingSignal, Transaction,
    OrderModification, AccountSnapshot, SystemLog,
    AIStats, PerformanceMetric
)
from .repository import (
    Repository, InstrumentRepository, TradingSetupRepository,
    TradingSignalRepository, TransactionRepository,
    AccountSnapshotRepository, SystemLogRepository,
    AIStatsRepository, PerformanceMetricRepository
)

__all__ = [
    'DatabaseManager',
    'Instrument', 'TradingSetup', 'TradingSignal', 'Transaction',
    'OrderModification', 'AccountSnapshot', 'SystemLog',
    'AIStats', 'PerformanceMetric',
    'Repository', 'InstrumentRepository', 'TradingSetupRepository',
    'TradingSignalRepository', 'TransactionRepository',
    'AccountSnapshotRepository', 'SystemLogRepository',
    'AIStatsRepository', 'PerformanceMetricRepository'
] 