"""
Moduł bazy danych do przechowywania i pobierania danych.

Ten moduł zawiera klasy do zarządzania połączeniem z bazą danych,
modele danych oraz repozytoria do interakcji z bazą danych.
"""

from .models import (
    TradingSignal,
    Transaction,
    Instrument,
    TradingSetup,
    AccountSnapshot,
    SystemLog,
    AIStats,
    PerformanceMetric,
    AIUsageRecord,
    MarketData,
    SignalEvaluation
)

from .db_manager import DatabaseManager
from .repository import Repository
from .ai_usage_repository import AIUsageRepository, get_ai_usage_repository
from .market_data_repository import MarketDataRepository, get_market_data_repository
from .signal_repository import SignalRepository, get_signal_repository
from .signal_evaluation_repository import SignalEvaluationRepository, get_signal_evaluation_repository
from .trade_repository import TradeRepository, get_trade_repository

__all__ = [
    'DatabaseManager',
    'Repository',
    'TradingSignal',
    'Transaction',
    'Instrument',
    'TradingSetup',
    'AccountSnapshot',
    'SystemLog',
    'AIStats',
    'PerformanceMetric',
    'AIUsageRecord',
    'MarketData',
    'SignalEvaluation',
    'AIUsageRepository',
    'get_ai_usage_repository',
    'MarketDataRepository',
    'get_market_data_repository',
    'SignalRepository',
    'get_signal_repository',
    'SignalEvaluationRepository',
    'get_signal_evaluation_repository',
    'TradeRepository',
    'get_trade_repository'
] 