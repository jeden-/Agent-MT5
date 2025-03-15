#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Testy jednostkowe dla modułu backtestingu.
"""

import unittest
import os
import sys
import logging
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from pathlib import Path

# Dodaj katalog główny projektu do ścieżki
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from src.backtest import BacktestEngine, BacktestConfig, BacktestResult
from src.backtest.backtest_metrics import calculate_metrics, generate_report

# Wyłącz logowanie podczas testów
logging.basicConfig(level=logging.ERROR)


class MockedMT5Connector:
    """
    Klasa zaślepki dla MT5Connector do testów.
    """
    
    def __init__(self):
        self.historical_data = None
        self.symbol_info = {
            "EURUSD": {"point": 0.00001},
            "GBPUSD": {"point": 0.00001},
            "USDJPY": {"point": 0.01}
        }
    
    def get_historical_data(self, symbol, timeframe, start_time, end_time, count):
        """
        Tworzy sztuczne dane historyczne dla testów.
        """
        # Generuj sztuczne dane
        dates = pd.date_range(start=start_time, end=end_time, periods=min(count, 1000))
        base_price = 1.1000 if symbol == "EURUSD" else (1.3000 if symbol == "GBPUSD" else 110.00)
        
        # Generuj losowe ruchy cen
        np.random.seed(42)  # Dla powtarzalności testów
        price_changes = np.random.normal(0, 0.0010, len(dates))
        
        # Tworzenie DataFrame
        close_prices = base_price + np.cumsum(price_changes)
        open_prices = close_prices - price_changes
        high_prices = np.maximum(close_prices, open_prices) + np.random.uniform(0, 0.0010, len(dates))
        low_prices = np.minimum(close_prices, open_prices) - np.random.uniform(0, 0.0010, len(dates))
        volumes = np.random.randint(100, 1000, len(dates))
        spreads = np.ones(len(dates)) * 10  # Stały spread 10 punktów
        
        # Tworzenie DataFrame z danymi
        data = {
            'time': dates,
            'open': open_prices,
            'high': high_prices,
            'low': low_prices,
            'close': close_prices,
            'tick_volume': volumes,
            'spread': spreads,
            'real_volume': volumes
        }
        
        df = pd.DataFrame(data)
        self.historical_data = df
        return df
    
    def get_symbol_info(self, symbol):
        """
        Zwraca informacje o symbolu.
        """
        return self.symbol_info.get(symbol, {"point": 0.00001})


class TestBacktest(unittest.TestCase):
    """
    Testy dla modułu backtestingu.
    """
    
    def setUp(self):
        """
        Konfiguracja testów.
        """
        # Ustawienia testowe
        self.end_date = datetime.now()
        self.start_date = self.end_date - timedelta(days=30)
        
        # Testowa konfiguracja
        self.config = BacktestConfig(
            symbol="EURUSD",
            timeframe="H1",
            start_date=self.start_date,
            end_date=self.end_date,
            initial_balance=10000.0,
            position_size_pct=1.0,
            commission=0.0,
            slippage=2.0,
            use_spread=True,
            min_volume=0.01,
            max_volume=1.0,
            strategy_name="test_strategy",
            output_dir="test_results"
        )
        
        # Podmień konnektor MT5 na zaślepkę
        from src.backtest.backtest_engine import BacktestEngine
        self.original_get_mt5_connector = BacktestEngine.mt5_connector
        BacktestEngine.mt5_connector = MockedMT5Connector()
        
        # Podmień generator sygnałów na zaślepkę
        from unittest.mock import MagicMock
        from src.database.models import TradingSignal
        
        self.mock_signal = TradingSignal(
            symbol="EURUSD",
            timeframe="H1",
            direction="BUY",
            entry_price=1.1050,
            stop_loss=1.1000,
            take_profit=1.1150,
            confidence=0.8
        )
        
        self.mock_signal_generator = MagicMock()
        self.mock_signal_generator.generate_signal_from_data.return_value = self.mock_signal
        
    def tearDown(self):
        """
        Czyszczenie po testach.
        """
        # Usuń katalog testowy jeśli istnieje
        import shutil
        if os.path.exists("test_results"):
            shutil.rmtree("test_results")
    
    def test_backtest_config(self):
        """
        Test konfiguracji backtestingu.
        """
        # Sprawdź czy podstawowe parametry są poprawnie ustawione
        self.assertEqual(self.config.symbol, "EURUSD")
        self.assertEqual(self.config.timeframe, "H1")
        self.assertEqual(self.config.initial_balance, 10000.0)
        self.assertEqual(self.config.position_size_pct, 1.0)
        
    def test_backtest_result_save(self):
        """
        Test zapisywania wyników backtestingu.
        """
        # Utwórz testowy obiekt wyników
        result = BacktestResult(
            config=self.config,
            trades=[],
            equity_curve=[10000.0, 10100.0, 10200.0],
            timestamps=[self.start_date, self.start_date + timedelta(days=1), self.start_date + timedelta(days=2)],
            balance=10200.0,
            metrics={"net_profit": 200.0, "win_rate": 60.0}
        )
        
        # Zapisz wyniki do pliku
        filename = result.save()
        
        # Sprawdź czy plik został utworzony
        self.assertTrue(os.path.exists(filename))
        
        # Sprawdź zawartość pliku
        import json
        with open(filename, 'r') as f:
            data = json.load(f)
            
        self.assertEqual(data["config"]["symbol"], "EURUSD")
        self.assertEqual(data["balance"], 10200.0)
        self.assertEqual(data["metrics"]["net_profit"], 200.0)
        
    def test_calculate_metrics(self):
        """
        Test obliczania metryk backtestingu.
        """
        from src.backtest.backtest_metrics import calculate_metrics
        from src.backtest.backtest_engine import BacktestTrade
        
        # Utwórz testowe transakcje
        trades = [
            BacktestTrade(
                signal_id="test1",
                symbol="EURUSD",
                direction="BUY",
                entry_price=1.1050,
                stop_loss=1.1000,
                take_profit=1.1150,
                entry_time=self.start_date,
                volume=0.1,
                exit_price=1.1150,
                exit_time=self.start_date + timedelta(hours=5),
                profit=100.0,
                pips=100.0,
                status="closed",
                hit_target=True,
                hit_stop=False,
                reason="take_profit"
            ),
            BacktestTrade(
                signal_id="test2",
                symbol="EURUSD",
                direction="BUY",
                entry_price=1.1060,
                stop_loss=1.1010,
                take_profit=1.1160,
                entry_time=self.start_date + timedelta(days=1),
                volume=0.1,
                exit_price=1.1010,
                exit_time=self.start_date + timedelta(days=1, hours=3),
                profit=-50.0,
                pips=-50.0,
                status="closed",
                hit_target=False,
                hit_stop=True,
                reason="stop_loss"
            ),
            BacktestTrade(
                signal_id="test3",
                symbol="EURUSD",
                direction="SELL",
                entry_price=1.1070,
                stop_loss=1.1120,
                take_profit=1.1020,
                entry_time=self.start_date + timedelta(days=2),
                volume=0.1,
                exit_price=1.1020,
                exit_time=self.start_date + timedelta(days=2, hours=6),
                profit=50.0,
                pips=50.0,
                status="closed",
                hit_target=True,
                hit_stop=False,
                reason="take_profit"
            )
        ]
        
        # Utwórz testowy obiekt wyników
        result = BacktestResult(
            config=self.config,
            trades=trades,
            equity_curve=[10000.0, 10100.0, 10050.0, 10100.0],
            timestamps=[
                self.start_date, 
                self.start_date + timedelta(hours=5), 
                self.start_date + timedelta(days=1, hours=3), 
                self.start_date + timedelta(days=2, hours=6)
            ],
            balance=10100.0,
            drawdowns=[0.0, 0.0, 0.5, 0.0]
        )
        
        # Oblicz metryki
        metrics = calculate_metrics(result)
        
        # Sprawdź podstawowe metryki
        self.assertEqual(metrics["net_profit"], 100.0)
        self.assertEqual(metrics["total_trades"], 3)
        self.assertEqual(metrics["winning_trades"], 2)
        self.assertEqual(metrics["losing_trades"], 1)
        self.assertAlmostEqual(metrics["win_rate"], 66.66666666666667)
        self.assertEqual(metrics["avg_profit"], 75.0)
        self.assertEqual(metrics["avg_loss"], -50.0)
        
    def test_generate_report(self):
        """
        Test generowania raportu z wynikami backtestingu.
        """
        from src.backtest.backtest_metrics import generate_report
        from src.backtest.backtest_engine import BacktestTrade
        
        # Utwórz testowe transakcje
        trades = [
            BacktestTrade(
                signal_id="test1",
                symbol="EURUSD",
                direction="BUY",
                entry_price=1.1050,
                stop_loss=1.1000,
                take_profit=1.1150,
                entry_time=self.start_date,
                volume=0.1,
                exit_price=1.1150,
                exit_time=self.start_date + timedelta(hours=5),
                profit=100.0,
                pips=100.0,
                status="closed",
                hit_target=True,
                hit_stop=False,
                reason="take_profit"
            )
        ]
        
        # Utwórz testowy obiekt wyników
        result = BacktestResult(
            config=self.config,
            trades=trades,
            equity_curve=[10000.0, 10100.0],
            timestamps=[self.start_date, self.start_date + timedelta(hours=5)],
            balance=10100.0,
            drawdowns=[0.0, 0.0],
            metrics={
                "net_profit": 100.0,
                "net_profit_percent": 1.0,
                "total_trades": 1,
                "winning_trades": 1,
                "losing_trades": 0,
                "win_rate": 100.0,
                "avg_profit": 100.0,
                "avg_loss": 0.0,
                "largest_profit": 100.0,
                "largest_loss": 0.0,
                "profit_factor": float('inf'),
                "reward_risk_ratio": float('inf'),
                "max_drawdown": 0.0,
                "avg_drawdown": 0.0,
                "sharpe_ratio": 0.0,
                "volatility": 0.0,
                "avg_trade_duration_hours": 5.0,
                "expected_value": 100.0,
                "buy_trades": 1,
                "sell_trades": 0,
                "buy_win_rate": 100.0,
                "sell_win_rate": 0.0
            }
        )
        
        # Generuj raport
        report_path = generate_report(result)
        
        # Sprawdź czy raport został wygenerowany
        self.assertTrue(os.path.exists(report_path))
        self.assertTrue(os.path.exists(os.path.join(self.config.output_dir, f"{self.config.symbol}_{self.config.timeframe}_{self.config.test_id}_charts.png")))


if __name__ == "__main__":
    unittest.main() 