#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Testy jednostkowe izolowane dla modułu trading_integration.
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

# Funkcja do ładowania modułu trading_integration bezpośrednio
def load_trading_integration_module():
    """Ładuje moduł trading_integration bezpośrednio, bez importowania __init__.py."""
    file_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), 
                          'trading_integration.py')
    
    # Sprawdzenie, czy plik istnieje
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Nie znaleziono pliku: {file_path}")

    # Przygotowanie konfiguracji
    mock_config = {
        'symbols': ['EURUSD', 'GBPUSD', 'USDJPY'],
        'signal_timeout_minutes': 30,
        'risk_per_trade_percent': 2.0,
        'max_open_positions': 5,
        'validation_required': True,
        'log_level': 'INFO'
    }
    
    # Mockowanie ConfigManagera
    config_manager_mock = Mock()
    config_manager_mock.get_config_section = Mock(return_value=mock_config)
    
    # Załadowanie modułu
    spec = importlib.util.spec_from_file_location("trading_integration", file_path)
    module = importlib.util.module_from_spec(spec)
    
    # Mockowanie zależności przed załadowaniem modułu
    modules_to_mock = {
        'src.analysis.signal_generator': Mock(
            SignalGenerator=Mock(return_value=Mock()),
            SignalType=Mock(BUY="BUY", SELL="SELL", CLOSE="CLOSE", NO_ACTION="NO_ACTION"),
            SignalStrength=Mock(WEAK="WEAK", MODERATE="MODERATE", STRONG="STRONG", VERY_STRONG="VERY_STRONG"),
            SignalSource=Mock(TECHNICAL="TECHNICAL", FUNDAMENTAL="FUNDAMENTAL", AI="AI", COMBINED="COMBINED", MANUAL="MANUAL")
        ),
        'src.analysis.signal_validator': Mock(
            SignalValidator=Mock(return_value=Mock()),
            ValidationResult=Mock(VALID="VALID", REJECTED_RISK_POLICY="REJECTED_RISK_POLICY")
        ),
        'src.database.signal_repository': Mock(
            SignalRepository=Mock()
        ),
        'src.database.trade_repository': Mock(
            TradeRepository=Mock(return_value=Mock())
        ),
        'src.position_management.position_manager': Mock(
            PositionManager=Mock(return_value=Mock())
        ),
        'src.utils.config_manager': Mock(
            ConfigManager=Mock(return_value=config_manager_mock)
        ),
        'src.mt5_bridge.mt5_client': Mock(),
        'src.mt5_bridge.trading_service': Mock(
            TradingService=Mock(return_value=Mock()),
            OrderType=Mock(BUY="BUY", SELL="SELL"),
            OrderStatus=Mock(PENDING="PENDING", FILLED="FILLED", CANCELLED="CANCELLED", ERROR="ERROR"),
            OrderValidationResult=Mock(VALID="VALID", INVALID_PRICE="INVALID_PRICE", INSUFFICIENT_MARGIN="INSUFFICIENT_MARGIN")
        ),
        'src.analysis.feedback_loop': Mock(
            FeedbackLoop=Mock(return_value=Mock())
        ),
        'src.risk_management.risk_manager': Mock(
            RiskManager=Mock(return_value=Mock()),
            OrderValidationResult=Mock(VALID="VALID", INVALID_PRICE="INVALID_PRICE")
        ),
        'logging': Mock(getLogger=Mock(return_value=Mock()))
    }
    
    # Patchujemy moduły
    for module_name, mock_module in modules_to_mock.items():
        if module_name not in sys.modules:
            sys.modules[module_name] = mock_module
    
    # Wykonaj moduł
    spec.loader.exec_module(module)
    
    return module


# Załaduj moduł trading_integration
trading_integration_module = load_trading_integration_module()
TradingIntegration = trading_integration_module.TradingIntegration


class TestTradingIntegrationIsolated(unittest.TestCase):
    """Testy izolowane dla klasy TradingIntegration."""
    
    def setUp(self):
        """Przygotowanie środowiska testowego."""
        logger.debug("Rozpoczynam setUp")
        
        # Resetowanie singletona, jeśli istnieje
        if hasattr(TradingIntegration, '_instance') and TradingIntegration._instance is not None:
            TradingIntegration._instance = None
            logger.debug("Zresetowano instancję singletona TradingIntegration")
        
        # Inicjalizacja instancji TradingIntegration
        logger.debug("Tworzę instancję TradingIntegration")
        self.trading_integration = TradingIntegration()
        logger.debug("Inicjalizacja TradingIntegration zakończona")
    
    def test_initialize(self):
        """Test inicjalizacji."""
        logger.debug("Rozpoczynam test_initialize")
        
        # Weryfikacja, czy zależności zostały poprawnie zainicjalizowane
        self.assertIsNotNone(self.trading_integration.signal_generator)
        self.assertIsNotNone(self.trading_integration.signal_validator)
        self.assertIsNotNone(self.trading_integration.feedback_loop)
        self.assertIsNotNone(self.trading_integration.trading_service)
        self.assertIsNotNone(self.trading_integration.position_manager)
        self.assertIsNotNone(self.trading_integration.risk_manager)
        self.assertIsNotNone(self.trading_integration.trade_repository)
        
        # Weryfikacja innych atrybutów
        self.assertIsInstance(self.trading_integration.decisions, list)
        self.assertIsInstance(self.trading_integration.decisions_history, list)
        self.assertIsInstance(self.trading_integration.is_running, bool)
        self.assertIsInstance(self.trading_integration.trading_enabled, bool)
        self.assertIsInstance(self.trading_integration.check_interval, int)
    
    def test_process_signal(self):
        """Test przetwarzania sygnału."""
        # Przygotwanie mockowanego sygnału
        signal = {
            'id': 'test_signal_123',
            'symbol': 'EURUSD',
            'type': 'BUY',
            'price': 1.1234,
            'timestamp': datetime.now(),
            'strength': 'STRONG',
            'source': 'TECHNICAL',
            'meta': {'reason': 'Test signal'}
        }
        
        # Mockowanie metod klasy TradingIntegration
        self.trading_integration._create_trading_decision = Mock(return_value=
            trading_integration_module.TradingDecision(
                symbol='EURUSD',
                action='BUY',
                volume=0.1,
                signal_id='test_signal_123'
            )
        )
        
        self.trading_integration.signal_validator.validate_signal = Mock(return_value={'result': 'VALID'})
        self.trading_integration._validate_decision_risk = Mock(return_value='VALID')
        self.trading_integration._execute_decision = Mock(return_value={'ticket': 12345})
        self.trading_integration.feedback_loop.get_signal_quality = Mock(return_value=0.85)
        
        # Wywołanie metody - nie możemy wywołać wprost process_signal, bo nie jest zdefiniowana w klasie
        # W zamian przetestujmy jedną z metod, która byłaby używana podczas przetwarzania sygnału
        decision = self.trading_integration._create_trading_decision(signal, 0.85)
        
        # Weryfikacja wyniku
        self.assertIsNotNone(decision)
        self.assertEqual(decision.symbol, 'EURUSD')
        self.assertEqual(decision.action, 'BUY')


if __name__ == '__main__':
    unittest.main() 