"""
Moduł backtestingu do testowania strategii handlowych na danych historycznych.

Ten moduł zawiera narzędzia do przeprowadzania backtestów strategii handlowych,
analizowania wyników i generowania raportów.
"""

from .backtest_engine import BacktestEngine, BacktestResult, BacktestConfig
from .backtest_metrics import calculate_metrics, generate_report

__all__ = [
    'BacktestEngine',
    'BacktestResult',
    'BacktestConfig',
    'calculate_metrics',
    'generate_report'
] 