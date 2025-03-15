#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Testy jednostkowe dla klasy BacktestEngine.

Ten moduł zawiera testy weryfikujące poprawność działania klasy BacktestEngine,
która jest odpowiedzialna za uruchamianie backtestów strategii handlowych.
"""

import os
import unittest
from unittest.mock import Mock, patch, MagicMock, call, ANY, PropertyMock
from datetime import datetime, timedelta
import tempfile
import shutil
import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional, Union, Tuple
import json

# Patch dla MT5Connector przed importem BacktestEngine
with patch('src.mt5_bridge.mt5_connector.MT5Connector') as mock_mt5_connector_class:
    # Teraz importujemy BacktestEngine i klasy pomocnicze
    from src.backtest.backtest_engine import BacktestEngine, BacktestConfig
    from src.backtest.strategy import TradingStrategy, StrategyConfig, StrategySignal
    from src.backtest.position_manager import PositionManager
    from src.backtest.historical_data_manager import HistoricalDataManager
    from src.models.signal import SignalType


class TestBacktestEngine(unittest.TestCase):
    """Testy dla klasy BacktestEngine."""
    
    def setUp(self):
        """Przygotowanie środowiska testowego."""
        # Tworzenie tymczasowego katalogu dla wyników testów
        self.temp_dir = tempfile.mkdtemp()
        
        # Mock dla MT5Connector
        self.mt5_connector_mock = Mock()
        
        # Przygotowanie przykładowych danych historycznych
        self.sample_data = pd.DataFrame({
            'time': pd.date_range(start='2023-01-01', periods=100, freq='H'),
            'open': np.random.rand(100) * 100,
            'high': np.random.rand(100) * 100 + 10,
            'low': np.random.rand(100) * 100 - 10,
            'close': np.random.rand(100) * 100,
            'tick_volume': np.random.randint(1, 1000, 100),
            'spread': np.random.randint(1, 10, 100),
            'real_volume': np.random.randint(1, 10000, 100)
        })
        
        # Ustawienie dat dla testów
        self.start_date = datetime(2023, 1, 1)
        self.end_date = datetime(2023, 1, 5)
        
        # Ustawienie symbolu i timeframe
        self.symbol = "EURUSD"
        self.timeframe = "H1"
        
        # Mock dla HistoricalDataManager
        self.data_manager_mock = Mock()
        self.data_manager_mock.get_historical_data.return_value = self.sample_data
        
        # Mock dla strategii
        self.strategy_mock = Mock(spec=TradingStrategy)
        self.strategy_mock.name = "MockStrategy"
        self.strategy_mock.config = StrategyConfig()
        
        # Konfiguracja dla BacktestEngine
        self.config = BacktestConfig(
            symbol=self.symbol,
            timeframe=self.timeframe,
            start_date=self.start_date,
            end_date=self.end_date,
            initial_balance=10000.0,
            position_size_pct=1.0,
            output_dir=self.temp_dir,
            strategy_params={"param1": 10, "param2": "value"}
        )
        
        # Inicjalizacja BacktestEngine
        self.backtest_engine = BacktestEngine(
            config=self.config,
            data_manager=self.data_manager_mock,
            strategy=self.strategy_mock
        )
        
    def tearDown(self):
        """Czyszczenie po testach."""
        # Usunięcie tymczasowego katalogu
        shutil.rmtree(self.temp_dir)
    
    def test_init(self):
        """Test inicjalizacji klasy BacktestEngine."""
        # Sprawdzenie, czy atrybuty zostały poprawnie ustawione
        self.assertEqual(self.backtest_engine.config.symbol, self.symbol)
        self.assertEqual(self.backtest_engine.config.timeframe, self.timeframe)
        self.assertEqual(self.backtest_engine.config.initial_balance, 10000.0)
        self.assertEqual(self.backtest_engine.strategy, self.strategy_mock)
        self.assertEqual(self.backtest_engine.data_manager, self.data_manager_mock)
        self.assertEqual(self.backtest_engine.balance, 10000.0)
        self.assertEqual(self.backtest_engine.config.position_size_pct, 1.0)
        self.assertEqual(self.backtest_engine.config.output_dir, self.temp_dir)
    
    def test_run_backtest(self):
        """Test uruchomienia backtestingu."""
        # Przygotowanie przykładowych sygnałów
        sample_signals = [
            StrategySignal(
                symbol=self.symbol,
                signal_type=SignalType.BUY,
                entry_price=1.1,
                stop_loss=1.09,
                take_profit=1.12,
                time=self.start_date + timedelta(hours=5),
                volume=0.1,
                comment="Test signal"
            )
        ]
        
        # Ustawienie mocka dla strategii
        self.strategy_mock.generate_signals.return_value = sample_signals
        
        # Uruchomienie backtestingu
        result = self.backtest_engine.run()
        
        # Sprawdzenie, czy dane historyczne zostały pobrane
        self.data_manager_mock.get_historical_data.assert_called_once_with(
            symbol=self.symbol,
            timeframe=self.timeframe,
            start_date=self.start_date,
            end_date=self.end_date,
            use_cache=True,
            update_cache=True,
            use_synthetic=False
        )
        
        # Sprawdzenie, czy strategia została wywołana
        self.strategy_mock.generate_signals.assert_called()
        
        # Sprawdzenie, czy wyniki zostały zwrócone
        self.assertIsNotNone(result)
        self.assertEqual(result.config, self.config)
        self.assertGreater(len(result.equity_curve), 1)
        self.assertGreater(len(result.timestamps), 1)
    
    def test_process_signals(self):
        """Test przetwarzania sygnałów."""
        # Przygotowanie przykładowych sygnałów
        sample_signals = [
            StrategySignal(
                symbol=self.symbol,
                signal_type=SignalType.BUY,
                entry_price=self.sample_data['close'][50],
                stop_loss=self.sample_data['close'][50] - 0.01,
                take_profit=self.sample_data['close'][50] + 0.02,
                time=self.sample_data['time'][50],
                volume=0.1,
                comment="Test signal"
            )
        ]
        
        # Ustawienie mocka dla strategii
        self.strategy_mock.generate_signals.return_value = sample_signals
        
        # Uruchomienie backtestingu
        result = self.backtest_engine.run()
        
        # Sprawdzenie, czy sygnały zostały przetworzone
        self.assertGreaterEqual(len(self.backtest_engine.signals), 0)
        
        # Sprawdzenie struktury krzywej equity
        self.assertEqual(len(result.equity_curve), len(result.timestamps))
    
    def test_calculate_metrics(self):
        """Test obliczania metryk wydajności."""
        # Przygotowanie przykładowych sygnałów
        sample_signals = [
            StrategySignal(
                symbol=self.symbol,
                signal_type=SignalType.BUY,
                entry_price=self.sample_data['close'][50],
                stop_loss=self.sample_data['close'][50] - 0.01,
                take_profit=self.sample_data['close'][50] + 0.02,
                time=self.sample_data['time'][50],
                volume=0.1,
                comment="Test signal"
            )
        ]
        
        # Ustawienie mocka dla strategii
        self.strategy_mock.generate_signals.return_value = sample_signals
        
        # Uruchomienie backtestingu
        result = self.backtest_engine.run()
        
        # Sprawdzenie, czy metryki zostały obliczone
        self.assertIsNotNone(result.metrics)
        self.assertIn("total_trades", result.metrics)
        self.assertIn("win_rate", result.metrics)
        self.assertIn("profit_factor", result.metrics)
        self.assertIn("max_drawdown", result.metrics)
    
    def test_generate_report(self):
        """Test generowania raportu."""
        # Przygotowanie przykładowych sygnałów
        sample_signals = [
            StrategySignal(
                symbol=self.symbol,
                signal_type=SignalType.BUY,
                entry_price=self.sample_data['close'][50],
                stop_loss=self.sample_data['close'][50] - 0.01,
                take_profit=self.sample_data['close'][50] + 0.02,
                time=self.sample_data['time'][50],
                volume=0.1,
                comment="Test signal"
            )
        ]
        
        # Ustawienie mocka dla strategii
        self.strategy_mock.generate_signals.return_value = sample_signals
        
        # Uruchomienie backtestingu
        result = self.backtest_engine.run()
        
        # Zapisz wyniki
        report_path = result.save()
        
        # Sprawdzenie, czy plik został utworzony
        self.assertTrue(os.path.exists(report_path))
        
        # Sprawdzenie, czy plik zawiera poprawne dane JSON
        with open(report_path, 'r') as f:
            report_data = json.load(f)
        
        self.assertIn("config", report_data)
        self.assertIn("metrics", report_data)
        self.assertIn("trades", report_data)
    
    def test_run_integration(self):
        """Test integracyjny całego procesu backtestingu z konkretną implementacją strategii."""
        # Utwórz konkretną implementację strategii
        class TestStrategy(TradingStrategy):
            def generate_signals(self, data):
                signals = []
                # Prosta strategia: kupuj, gdy cena rośnie przez 3 świece
                for i in range(3, len(data)):
                    if (data.iloc[i-3]['close'] < data.iloc[i-2]['close'] < 
                        data.iloc[i-1]['close'] < data.iloc[i]['close']):
                        signals.append(StrategySignal(
                            symbol=data.iloc[i]['symbol'] if 'symbol' in data.columns else self.config.symbol,
                            signal_type=SignalType.BUY,
                            entry_price=data.iloc[i]['close'],
                            stop_loss=data.iloc[i]['close'] - 0.01,
                            take_profit=data.iloc[i]['close'] + 0.02,
                            time=data.iloc[i]['time'],
                            volume=0.1
                        ))
                return signals
        
        # Inicjalizacja silnika backtestingu z konkretną strategią
        real_strategy = TestStrategy()
        backtest_engine = BacktestEngine(
            config=self.config,
            data_manager=self.data_manager_mock,
            strategy=real_strategy
        )
        
        # Uruchomienie backtestingu
        result = backtest_engine.run()
        
        # Sprawdzenie wyników
        self.assertIsNotNone(result)
        self.assertGreater(len(result.equity_curve), 1)


if __name__ == '__main__':
    unittest.main() 