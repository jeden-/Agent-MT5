#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Testy jednostkowe dla modułu feedback_loop.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from enum import Enum, auto
import sys

# Mock dla klas używanych w feedback_loop.py, aby uniknąć problemów z importami
class MockSignalType(Enum):
    BUY = "BUY"
    SELL = "SELL"
    CLOSE = "CLOSE"
    NO_ACTION = "NO_ACTION"

class MockSignalStrength(Enum):
    WEAK = "WEAK"
    MODERATE = "MODERATE"
    STRONG = "STRONG"
    VERY_STRONG = "VERY_STRONG"

class MockSignalSource(Enum):
    TECHNICAL = "TECHNICAL"
    FUNDAMENTAL = "FUNDAMENTAL"
    AI = "AI"
    COMBINED = "COMBINED"
    MANUAL = "MANUAL"

class MockValidationResult(Enum):
    VALID = auto()
    REJECTED_RISK_POLICY = auto()
    REJECTED_POSITION_LIMIT = auto()
    REJECTED_OTHER = auto()

# Tworzenie mocków dla modułów
mock_signal_generator = Mock()
mock_signal_generator.SignalType = MockSignalType
mock_signal_generator.SignalStrength = MockSignalStrength
mock_signal_generator.SignalSource = MockSignalSource

mock_signal_validator = Mock()
mock_signal_validator.ValidationResult = MockValidationResult

mock_signal_repository = Mock()
mock_trade_repository = Mock()
mock_position_manager = Mock()
mock_config_manager = Mock()

# Patch'ujemy importy w module feedback_loop
with patch.dict('sys.modules', {
    'src.analysis.signal_generator': mock_signal_generator,
    'src.analysis.signal_validator': mock_signal_validator,
    'src.database.signal_repository': Mock(get_signal_repository=Mock(return_value=mock_signal_repository)),
    'src.database.trade_repository': Mock(get_trade_repository=Mock(return_value=mock_trade_repository)),
    'src.position_management.position_manager': Mock(get_position_manager=Mock(return_value=mock_position_manager)),
    'src.utils.config_manager': Mock(ConfigManager=Mock(return_value=mock_config_manager))
}):
    from src.analysis.feedback_loop import FeedbackLoop, LearningStrategy


class TestFeedbackLoop(unittest.TestCase):
    """Testy dla klasy FeedbackLoop."""
    
    def setUp(self):
        """Przygotowanie środowiska testowego."""
        # Resetowanie singletona przed każdym testem
        FeedbackLoop._instance = None
        
        # Konfiguracja mocków
        mock_config_manager.get_config_section.return_value = {
            'learning_strategy': 'HYBRID',
            'optimization_interval_hours': 4,
            'min_data_points': 50,
            'performance_metrics': ['profit_factor', 'win_rate', 'avg_profit', 'max_drawdown'],
            'learning_rate': 0.05,
            'signal_history_days': 30,
            'weight_recent_trades': True,
            'recency_half_life_days': 5,
            'parameter_bounds': {
                'rsi_oversold': [20, 40],
                'rsi_overbought': [60, 80],
                'macd_signal_period': [5, 15],
                'bollinger_std': [1.5, 3.0],
                'risk_reward_min': [1.5, 3.0],
                'stop_loss_atr_multiplier': [1.0, 4.0]
            }
        }
        
        # Inicjalizacja instancji FeedbackLoop
        self.feedback_loop = FeedbackLoop()
        
        # Przygotowanie przykładowych danych testowych
        self.sample_signals = self._create_sample_signals()
        self.sample_trades = self._create_sample_trades()
    
    def _create_sample_signals(self):
        """Tworzy przykładowe sygnały tradingowe do testów."""
        return [
            {
                'id': 1,
                'symbol': 'EURUSD',
                'type': 'BUY',
                'strength': 'STRONG',
                'source': 'TECHNICAL',
                'timeframe': 'H1',
                'timestamp': datetime.now() - timedelta(days=10),
                'ai_model': 'claude'
            },
            {
                'id': 2,
                'symbol': 'GBPUSD',
                'type': 'SELL',
                'strength': 'MODERATE',
                'source': 'AI',
                'timeframe': 'M15',
                'timestamp': datetime.now() - timedelta(days=8),
                'ai_model': 'grok'
            },
            {
                'id': 3,
                'symbol': 'EURUSD',
                'type': 'SELL',
                'strength': 'WEAK',
                'source': 'COMBINED',
                'timeframe': 'D1',
                'timestamp': datetime.now() - timedelta(days=5),
                'ai_model': 'deepseek'
            },
            {
                'id': 4,
                'symbol': 'USDJPY',
                'type': 'BUY',
                'strength': 'VERY_STRONG',
                'source': 'TECHNICAL',
                'timeframe': 'H4',
                'timestamp': datetime.now() - timedelta(days=3),
                'ai_model': None
            }
        ]
    
    def _create_sample_trades(self):
        """Tworzy przykładowe transakcje do testów."""
        return [
            {
                'id': 101,
                'symbol': 'EURUSD',
                'type': 'BUY',
                'signal_id': 1,
                'open_time': datetime.now() - timedelta(days=10),
                'close_time': datetime.now() - timedelta(days=9),
                'profit': 100.0,
                'volume': 0.1
            },
            {
                'id': 102,
                'symbol': 'GBPUSD',
                'type': 'SELL',
                'signal_id': 2,
                'open_time': datetime.now() - timedelta(days=8),
                'close_time': datetime.now() - timedelta(days=7),
                'profit': -50.0,
                'volume': 0.2
            },
            {
                'id': 103,
                'symbol': 'EURUSD',
                'type': 'SELL',
                'signal_id': 3,
                'open_time': datetime.now() - timedelta(days=5),
                'close_time': datetime.now() - timedelta(days=4),
                'profit': 75.0,
                'volume': 0.1
            },
            {
                'id': 104,
                'symbol': 'USDJPY',
                'type': 'BUY',
                'signal_id': 4,
                'open_time': datetime.now() - timedelta(days=3),
                'close_time': datetime.now() - timedelta(days=2),
                'profit': 120.0,
                'volume': 0.3
            }
        ]
    
    def test_singleton_pattern(self):
        """Test wzorca Singleton."""
        # Tworzenie drugiej instancji
        second_instance = FeedbackLoop()
        
        # Weryfikacja, że to ta sama instancja
        self.assertIs(self.feedback_loop, second_instance)
    
    def test_initialize(self):
        """Test, czy inicjalizacja działa poprawnie."""
        # Weryfikacja, czy zależności zostały poprawnie zainicjalizowane
        self.assertEqual(self.feedback_loop.signal_repository, mock_signal_repository)
        self.assertEqual(self.feedback_loop.trade_repository, mock_trade_repository)
        self.assertEqual(self.feedback_loop.position_manager, mock_position_manager)
        
        # Sprawdzenie, czy config został poprawnie wczytany
        self.assertEqual(self.feedback_loop.config['learning_strategy'], 'HYBRID')
        
        # Weryfikacja, czy inne atrybuty zostały zainicjalizowane
        self.assertIsInstance(self.feedback_loop.strategy_performance, dict)
        self.assertIsInstance(self.feedback_loop.signal_quality_metrics, dict)
        self.assertIsInstance(self.feedback_loop.model_performance, dict)
        self.assertIsInstance(self.feedback_loop.parameter_history, dict)
    
    def test_analyze_performance(self):
        """Test analizy wydajności historycznej."""
        # Przygotowanie
        self.feedback_loop._get_historical_signals = Mock(return_value=self.sample_signals)
        self.feedback_loop._get_historical_trades = Mock(return_value=self.sample_trades)
        
        # Wykonanie
        result = self.feedback_loop.analyze_performance(symbol='EURUSD', days=30)
        
        # Weryfikacja
        self.feedback_loop._get_historical_signals.assert_called_once()
        self.feedback_loop._get_historical_trades.assert_called_once()
        
        # Sprawdź, czy wynik zawiera oczekiwane sekcje
        self.assertIn('overall', result)
        self.assertIn('by_source', result)
        self.assertIn('by_strength', result)
        self.assertIn('by_model', result)
        
        # Sprawdź, czy dane zostały zapisane w pamięci podręcznej
        self.assertIn('EURUSD', self.feedback_loop.strategy_performance)
    
    def test_get_historical_signals(self):
        """Test pobierania historycznych sygnałów."""
        # Przygotowanie
        from_date = datetime.now() - timedelta(days=30)
        mock_signal_repository.get_signals_by_symbol.return_value = self.sample_signals
        
        # Wykonanie
        result = self.feedback_loop._get_historical_signals('EURUSD', from_date)
        
        # Weryfikacja
        mock_signal_repository.get_signals_by_symbol.assert_called_once_with('EURUSD', from_date)
        self.assertEqual(result, self.sample_signals)
    
    def test_get_historical_trades(self):
        """Test pobierania historycznych transakcji."""
        # Przygotowanie
        from_date = datetime.now() - timedelta(days=30)
        mock_trade_repository.get_trades_by_symbol.return_value = self.sample_trades
        
        # Wykonanie
        result = self.feedback_loop._get_historical_trades('EURUSD', from_date)
        
        # Weryfikacja
        mock_trade_repository.get_trades_by_symbol.assert_called_once_with('EURUSD', from_date)
        self.assertEqual(result, self.sample_trades)
    
    def test_merge_signals_with_trades(self):
        """Test łączenia sygnałów z transakcjami."""
        # Przygotowanie
        signals_df = pd.DataFrame(self.sample_signals)
        trades_df = pd.DataFrame(self.sample_trades)
        
        # Wykonanie
        result = self.feedback_loop._merge_signals_with_trades(signals_df, trades_df)
        
        # Weryfikacja
        self.assertIsInstance(result, pd.DataFrame)
        self.assertIn('profit', result.columns)
        self.assertIn('success', result.columns)
    
    def test_calculate_metrics(self):
        """Test obliczania metryk wydajności."""
        # Przygotowanie
        data = pd.DataFrame({
            'symbol': ['EURUSD', 'GBPUSD', 'EURUSD', 'USDJPY'],
            'profit': [100.0, -50.0, 75.0, 120.0],
            'success': [True, False, True, True]
        })
        
        # Wykonanie
        result = self.feedback_loop._calculate_metrics(data)
        
        # Weryfikacja
        self.assertIn('count', result)
        self.assertIn('win_rate', result)
        self.assertIn('profit_factor', result)
        self.assertIn('avg_profit', result)
        self.assertIn('total_profit', result)
        self.assertIn('max_drawdown', result)
        
        # Sprawdź, czy wartości są obliczone poprawnie
        self.assertEqual(result['count'], 4)
        self.assertEqual(result['win_rate'], 0.75)  # 3 z 4 transakcji są zyskowne
        self.assertAlmostEqual(result['avg_profit'], 61.25, places=2)  # (100 - 50 + 75 + 120) / 4
    
    def test_optimize_parameters(self):
        """Test optymalizacji parametrów."""
        # Przygotowanie
        self.feedback_loop.analyze_performance = Mock(return_value={
            'overall': {
                'win_rate': 0.75,
                'profit_factor': 2.0
            },
            'by_source': {
                'TECHNICAL': {'win_rate': 0.8, 'profit_factor': 2.5}
            },
            'by_strength': {
                'STRONG': {'win_rate': 0.7, 'profit_factor': 1.8}
            }
        })
        
        # Ustawienie daty ostatniej optymalizacji na dawno temu, aby test przeszedł
        self.feedback_loop.last_optimization = datetime.now() - timedelta(days=1)
        
        # Wykonanie
        result = self.feedback_loop.optimize_parameters(symbol='EURUSD')
        
        # Weryfikacja
        self.feedback_loop.analyze_performance.assert_called_once()
        self.assertIsInstance(result, dict)
        
        # Sprawdź, czy parametry zostały zapisane w historii
        self.assertIn('EURUSD', self.feedback_loop.parameter_history)
    
    def test_get_signal_quality(self):
        """Test oceny jakości sygnału."""
        # Przygotowanie
        self.feedback_loop.strategy_performance = {
            'EURUSD': {
                'overall': {'win_rate': 0.7, 'profit_factor': 2.0},
                'by_source': {'TECHNICAL': {'win_rate': 0.8, 'profit_factor': 2.5}},
                'by_strength': {'STRONG': {'win_rate': 0.75, 'profit_factor': 2.2}},
                'by_model': {'claude': {'win_rate': 0.65, 'profit_factor': 1.8}}
            }
        }
        
        signal = {
            'symbol': 'EURUSD',
            'source': 'TECHNICAL',
            'strength': 'STRONG',
            'ai_model': 'claude'
        }
        
        # Wykonanie
        result = self.feedback_loop.get_signal_quality(signal)
        
        # Weryfikacja
        self.assertIsInstance(result, float)
        self.assertTrue(0 <= result <= 1)
    
    def test_update_model_weights(self):
        """Test aktualizacji wag modeli AI."""
        # Przygotowanie
        self.feedback_loop.analyze_performance = Mock(return_value={
            'by_model': {
                'claude': {'win_rate': 0.7, 'profit_factor': 2.0},
                'grok': {'win_rate': 0.6, 'profit_factor': 1.5},
                'deepseek': {'win_rate': 0.8, 'profit_factor': 2.5}
            }
        })
        
        # Wykonanie
        result = self.feedback_loop.update_model_weights()
        
        # Weryfikacja
        self.assertIsInstance(result, dict)
        self.assertIn('claude', result)
        self.assertIn('grok', result)
        self.assertIn('deepseek', result)
        
        # Sprawdź, czy suma wag wynosi 1.0
        self.assertAlmostEqual(sum(result.values()), 1.0, places=5)
    
    def test_get_feedback_stats(self):
        """Test pobierania statystyk mechanizmu feedback loop."""
        # Wykonanie
        result = self.feedback_loop.get_feedback_stats()
        
        # Weryfikacja
        self.assertIsInstance(result, dict)
        self.assertIn('strategy_performance', result)
        self.assertIn('model_performance', result)
        self.assertIn('parameter_history', result)
        self.assertIn('last_optimization', result)
        self.assertIn('learning_strategy', result)
    
    def test_weighted_average(self):
        """Test funkcji obliczającej średnią ważoną."""
        # Przygotowanie
        value_weight_pairs = [
            (0.7, 0.4),
            (0.8, 0.3),
            (0.75, 0.2),
            (0.65, 0.1)
        ]
        
        # Wykonanie
        result = self.feedback_loop._weighted_average(value_weight_pairs)
        
        # Weryfikacja
        expected = (0.7 * 0.4 + 0.8 * 0.3 + 0.75 * 0.2 + 0.65 * 0.1) / 1.0
        self.assertAlmostEqual(result, expected, places=5)


if __name__ == '__main__':
    unittest.main() 