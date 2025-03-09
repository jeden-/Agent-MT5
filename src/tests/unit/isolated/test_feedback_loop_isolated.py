#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Testy jednostkowe izolowane dla modułu feedback_loop.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
import sys
import os
import importlib.util
import logging

# Konfiguracja logowania
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Dodanie katalogu głównego projektu do ścieżki Pythona
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../../')))

# Funkcja do ładowania modułu feedback_loop bezpośrednio
def load_feedback_loop_module():
    """Ładuje moduł feedback_loop bezpośrednio, bez importowania __init__.py."""
    file_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), 
                          'analysis', 'feedback_loop.py')
    
    # Sprawdzenie, czy plik istnieje
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Nie znaleziono pliku: {file_path}")
    
    # Przygotowanie konfiguracji
    mock_config = {
        'learning_strategy': 'HYBRID',
        'optimization_interval_hours': 4,  # Uwaga: to musi być int, nie Mock
        'min_data_points': 50,
        'performance_metrics': ['profit_factor', 'win_rate', 'avg_profit', 'max_drawdown'],
        'learning_rate': 0.05,
        'signal_history_days': 30,
        'parameter_bounds': {
            'rsi_oversold': [20, 40],
            'rsi_overbought': [60, 80],
            'macd_signal_period': [5, 15],
            'bollinger_std': [1.5, 3.0],
            'risk_reward_min': [1.5, 3.0],
            'stop_loss_atr_multiplier': [1.0, 4.0]
        }
    }
    
    # Mockowanie ConfigManagera
    config_manager_mock = Mock()
    config_manager_mock.get_config_section = Mock(return_value=mock_config)
    
    # Załadowanie modułu
    spec = importlib.util.spec_from_file_location("feedback_loop", file_path)
    module = importlib.util.module_from_spec(spec)
    
    # Mockowanie zależności przed załadowaniem modułu
    modules_to_mock = {
        'src.analysis.signal_generator': Mock(
            SignalType=Mock(BUY="BUY", SELL="SELL", CLOSE="CLOSE", NO_ACTION="NO_ACTION"),
            SignalStrength=Mock(WEAK="WEAK", MODERATE="MODERATE", STRONG="STRONG", VERY_STRONG="VERY_STRONG"),
            SignalSource=Mock(TECHNICAL="TECHNICAL", FUNDAMENTAL="FUNDAMENTAL", AI="AI", COMBINED="COMBINED", MANUAL="MANUAL")
        ),
        'src.analysis.signal_validator': Mock(
            ValidationResult=Mock(VALID="VALID", REJECTED_RISK_POLICY="REJECTED_RISK_POLICY")
        ),
        'src.database.signal_repository': Mock(),
        'src.database.trade_repository': Mock(),
        'src.position_management.position_manager': Mock(),
        'src.utils.config_manager': Mock(
            ConfigManager=Mock(return_value=config_manager_mock)
        ),
        'src.mt5_bridge.mt5_client': Mock(),
        'logging': Mock(getLogger=Mock(return_value=Mock()))
    }
    
    # Patchujemy moduły
    for module_name, mock_module in modules_to_mock.items():
        if module_name not in sys.modules:
            sys.modules[module_name] = mock_module
    
    # Wykonaj moduł
    spec.loader.exec_module(module)
    
    return module


# Załaduj moduł feedback_loop
feedback_loop_module = load_feedback_loop_module()
FeedbackLoop = feedback_loop_module.FeedbackLoop
LearningStrategy = feedback_loop_module.LearningStrategy


class TestFeedbackLoopIsolated(unittest.TestCase):
    """Testy izolowane dla klasy FeedbackLoop."""
    
    def setUp(self):
        """Przygotowanie środowiska testowego."""
        logger.debug("Rozpoczynam setUp")
        
        # Resetowanie singletona przed każdym testem
        if hasattr(FeedbackLoop, '_instance') and FeedbackLoop._instance is not None:
            FeedbackLoop._instance = None
            logger.debug("Zresetowano instancję singletona FeedbackLoop")
        
        # Utworzenie mocków dla zależności
        self.mock_signal_repository = Mock()
        self.mock_trade_repository = Mock()
        self.mock_position_manager = Mock()
        
        # Konfiguracja mock dla ConfigManager
        self.mock_config = {
            'learning_strategy': 'HYBRID',
            'optimization_interval_hours': 4,
            'min_data_points': 50,
            'performance_metrics': ['profit_factor', 'win_rate', 'avg_profit', 'max_drawdown'],
            'learning_rate': 0.05,
            'signal_history_days': 30,
            'parameter_bounds': {
                'rsi_oversold': [20, 40],
                'rsi_overbought': [60, 80],
                'macd_signal_period': [5, 15],
                'bollinger_std': [1.5, 3.0],
                'risk_reward_min': [1.5, 3.0],
                'stop_loss_atr_multiplier': [1.0, 4.0]
            }
        }
        
        # Patchowanie funkcji get_* w module
        sys.modules['src.database.signal_repository'].get_signal_repository = \
            Mock(return_value=self.mock_signal_repository)
        logger.debug("Mockuję get_signal_repository")
        
        sys.modules['src.database.trade_repository'].get_trade_repository = \
            Mock(return_value=self.mock_trade_repository)
        logger.debug("Mockuję get_trade_repository")
        
        sys.modules['src.position_management.position_manager'].get_position_manager = \
            Mock(return_value=self.mock_position_manager)
        logger.debug("Mockuję get_position_manager")
        
        # Inicjalizacja instancji FeedbackLoop
        logger.debug("Tworzę instancję FeedbackLoop")
        self.feedback_loop = FeedbackLoop()
        logger.debug("Inicjalizacja FeedbackLoop zakończona")
    
    def test_singleton_pattern(self):
        """Test wzorca Singleton."""
        # Tworzenie drugiej instancji
        second_instance = FeedbackLoop()
        
        # Weryfikacja, że to ta sama instancja
        self.assertIs(self.feedback_loop, second_instance)
    
    def test_initialize(self):
        """Test inicjalizacji."""
        logger.debug("Rozpoczynam test_initialize")
        
        # Weryfikacja, czy zależności zostały poprawnie zainicjalizowane
        logger.debug(f"Signal repo: {self.feedback_loop.signal_repository}, Mock: {self.mock_signal_repository}")
        logger.debug(f"Trade repo: {self.feedback_loop.trade_repository}, Mock: {self.mock_trade_repository}")
        logger.debug(f"Position mgr: {self.feedback_loop.position_manager}, Mock: {self.mock_position_manager}")
        
        # Weryfikacja, czy zależności zostały poprawnie zainicjalizowane
        self.assertIsNotNone(self.feedback_loop.signal_repository)
        self.assertIsNotNone(self.feedback_loop.trade_repository)
        self.assertIsNotNone(self.feedback_loop.position_manager)
        
        # Weryfikacja, czy inne atrybuty zostały zainicjalizowane
        self.assertIsInstance(self.feedback_loop.strategy_performance, dict)
        self.assertIsInstance(self.feedback_loop.signal_quality_metrics, dict)
        self.assertIsInstance(self.feedback_loop.model_performance, dict)
        self.assertIsInstance(self.feedback_loop.parameter_history, dict)
        
        # Weryfikacja konfiguracji
        self.assertIsNotNone(self.feedback_loop.config)
        self.assertIsInstance(self.feedback_loop.optimization_interval, timedelta)


if __name__ == '__main__':
    unittest.main() 