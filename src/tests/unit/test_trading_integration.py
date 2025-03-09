#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Testy jednostkowe dla modułu trading_integration.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
import time
import threading
from enum import Enum, auto

# Mock dla klas używanych w trading_integration.py
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

class MockOrderValidationResult(Enum):
    VALID = "valid"
    INVALID_SYMBOL = "invalid_symbol"
    INVALID_VOLUME = "invalid_volume"
    INVALID_PRICE = "invalid_price"
    INVALID_SL = "invalid_stop_loss"
    INVALID_TP = "invalid_take_profit"
    POSITION_LIMIT_EXCEEDED = "position_limit_exceeded"
    EXPOSURE_LIMIT_EXCEEDED = "exposure_limit_exceeded"
    RISK_REWARD_INVALID = "risk_reward_invalid"
    OTHER_ERROR = "other_error"

# Patch dla modułów
with patch.dict('sys.modules', {
    'src.analysis.signal_generator': Mock(
        SignalGenerator=Mock,
        SignalType=MockSignalType,
        SignalStrength=MockSignalStrength,
        SignalSource=MockSignalSource
    ),
    'src.analysis.signal_validator': Mock(
        SignalValidator=Mock,
        ValidationResult=MockValidationResult
    ),
    'src.analysis.feedback_loop': Mock(
        FeedbackLoop=Mock
    ),
    'src.mt5_bridge.trading_service': Mock(
        TradingService=Mock
    ),
    'src.position_management.position_manager': Mock(
        PositionManager=Mock
    ),
    'src.risk_management.risk_manager': Mock(
        RiskManager=Mock,
        OrderValidationResult=MockOrderValidationResult
    ),
    'src.database.trade_repository': Mock(
        TradeRepository=Mock
    )
}):
    from src.trading_integration import (
        TradingIntegration, TradingDecision, TradingDecisionStatus,
        get_trading_integration
    )


class TestTradingIntegration(unittest.TestCase):
    """Testy dla klasy TradingIntegration."""
    
    def setUp(self):
        """Przygotowanie środowiska testowego."""
        # Resetowanie singletona przed każdym testem
        TradingIntegration._instance = None
        
        # Tworzenie mocków dla zależności
        self.signal_generator_mock = Mock()
        self.signal_validator_mock = Mock()
        self.feedback_loop_mock = Mock()
        self.trading_service_mock = Mock()
        self.position_manager_mock = Mock()
        self.risk_manager_mock = Mock()
        self.trade_repository_mock = Mock()
        
        # Patch dla konstruktorów klas
        with patch('src.trading_integration.SignalGenerator', return_value=self.signal_generator_mock), \
             patch('src.trading_integration.SignalValidator', return_value=self.signal_validator_mock), \
             patch('src.trading_integration.FeedbackLoop', return_value=self.feedback_loop_mock), \
             patch('src.trading_integration.TradingService', return_value=self.trading_service_mock), \
             patch('src.trading_integration.PositionManager', return_value=self.position_manager_mock), \
             patch('src.trading_integration.RiskManager', return_value=self.risk_manager_mock), \
             patch('src.trading_integration.TradeRepository', return_value=self.trade_repository_mock):
            # Inicjalizacja instancji TradingIntegration
            self.trading_integration = TradingIntegration()
        
        # Konfiguracja trading_service_mock
        self.trading_service_mock.connect.return_value = True
        self.trading_service_mock.disconnect.return_value = True
        
        # Wyłączenie wątku decyzyjnego w testach
        self.original_decision_loop = self.trading_integration._decision_loop
        self.trading_integration._decision_loop = lambda: None
    
    def tearDown(self):
        """Czyszczenie po testach."""
        # Przywracanie oryginalnej metody _decision_loop
        if hasattr(self, 'original_decision_loop'):
            self.trading_integration._decision_loop = self.original_decision_loop
        
        # Zatrzymanie TradingIntegration, jeśli jest uruchomione
        if self.trading_integration.is_running:
            self.trading_integration.stop()
    
    def test_singleton_pattern(self):
        """Test wzorca Singleton."""
        # Tworzenie drugiej instancji
        second_instance = TradingIntegration()
        
        # Weryfikacja, że to ta sama instancja
        self.assertIs(self.trading_integration, second_instance)
    
    def test_initialize(self):
        """Test, czy inicjalizacja działa poprawnie."""
        # Weryfikacja inicjalizacji komponentów
        self.assertEqual(self.trading_integration.signal_generator, self.signal_generator_mock)
        self.assertEqual(self.trading_integration.signal_validator, self.signal_validator_mock)
        self.assertEqual(self.trading_integration.feedback_loop, self.feedback_loop_mock)
        self.assertEqual(self.trading_integration.trading_service, self.trading_service_mock)
        self.assertEqual(self.trading_integration.position_manager, self.position_manager_mock)
        self.assertEqual(self.trading_integration.risk_manager, self.risk_manager_mock)
        self.assertEqual(self.trading_integration.trade_repository, self.trade_repository_mock)
        
        # Weryfikacja początkowego stanu
        self.assertFalse(self.trading_integration.is_running)
        self.assertFalse(self.trading_integration.trading_enabled)
        self.assertIsInstance(self.trading_integration.decisions, list)
        self.assertIsInstance(self.trading_integration.decisions_history, list)
    
    def test_start_stop(self):
        """Test uruchamiania i zatrzymywania integracji."""
        # Uruchomienie
        result = self.trading_integration.start()
        
        # Weryfikacja
        self.assertTrue(result)
        self.assertTrue(self.trading_integration.is_running)
        self.trading_service_mock.connect.assert_called_once()
        
        # Zatrzymanie
        result = self.trading_integration.stop()
        
        # Weryfikacja
        self.assertTrue(result)
        self.assertFalse(self.trading_integration.is_running)
        self.trading_service_mock.disconnect.assert_called_once()
    
    def test_enable_trading(self):
        """Test włączania i wyłączania automatycznego handlu."""
        # Ustawienie wartości początkowej
        self.trading_integration.trading_enabled = False
        
        # Włączenie handlu
        self.trading_integration.enable_trading(True)
        self.assertTrue(self.trading_integration.trading_enabled)
        
        # Wyłączenie handlu
        self.trading_integration.enable_trading(False)
        self.assertFalse(self.trading_integration.trading_enabled)
    
    def test_analyze_market(self):
        """Test analizy rynku."""
        # Konfiguracja mocków
        self.trading_integration._get_monitored_symbols = Mock(return_value=["EURUSD"])
        self.trading_service_mock.get_market_data.return_value = {'symbol': 'EURUSD', 'bid': 1.1000, 'ask': 1.1001}
        
        self.signal_generator_mock.generate_signals.return_value = [
            {'symbol': 'EURUSD', 'type': 'BUY', 'id': 1}
        ]
        
        self.signal_validator_mock.validate_signal.return_value = MockValidationResult.VALID
        self.feedback_loop_mock.get_signal_quality.return_value = 0.8
        
        self.trading_integration._create_trading_decision = Mock(return_value=TradingDecision(
            symbol='EURUSD', action='BUY', volume=0.1, quality_score=0.8
        ))
        
        self.trading_integration._validate_decision_risk = Mock(return_value=MockOrderValidationResult.VALID)
        
        # Wykonanie
        self.trading_integration.analyze_market()
        
        # Weryfikacja
        self.trading_service_mock.get_market_data.assert_called_once_with("EURUSD")
        self.signal_generator_mock.generate_signals.assert_called_once()
        self.signal_validator_mock.validate_signal.assert_called_once()
        self.feedback_loop_mock.get_signal_quality.assert_called_once()
        self.trading_integration._create_trading_decision.assert_called_once()
        self.trading_integration._validate_decision_risk.assert_called_once()
        
        # Sprawdzenie, czy decyzja została dodana do listy
        self.assertEqual(len(self.trading_integration.decisions), 1)
        self.assertEqual(self.trading_integration.decisions[0].symbol, 'EURUSD')
        self.assertEqual(self.trading_integration.decisions[0].action, 'BUY')
    
    def test_process_pending_decisions(self):
        """Test przetwarzania oczekujących decyzji."""
        # Konfiguracja
        self.trading_integration.trading_enabled = True
        
        # Dodanie decyzji do przetworzenia
        decision = TradingDecision(symbol='EURUSD', action='BUY', volume=0.1)
        self.trading_integration.decisions.append(decision)
        
        # Mock dla _execute_decision
        self.trading_integration._execute_decision = Mock(return_value={'ticket': 12345})
        self.trading_integration._record_executed_decision = Mock()
        
        # Wykonanie
        self.trading_integration.process_pending_decisions()
        
        # Weryfikacja
        self.trading_integration._execute_decision.assert_called_once_with(decision)
        self.trading_integration._record_executed_decision.assert_called_once()
        
        # Sprawdzenie, czy decyzja została przeniesiona do historii
        self.assertEqual(len(self.trading_integration.decisions), 0)
        self.assertEqual(len(self.trading_integration.decisions_history), 1)
        self.assertEqual(self.trading_integration.decisions_history[0].status, TradingDecisionStatus.EXECUTED)
        self.assertEqual(self.trading_integration.decisions_history[0].ticket, 12345)
    
    def test_create_trading_decision(self):
        """Test tworzenia decyzji handlowej."""
        # Konfiguracja
        signal = {
            'symbol': 'EURUSD',
            'type': 'BUY',
            'id': 1
        }
        
        self.trading_service_mock.get_market_data.return_value = {
            'symbol': 'EURUSD',
            'bid': 1.1000,
            'ask': 1.1001
        }
        
        self.trading_service_mock.get_account_info.return_value = {
            'balance': 10000.0
        }
        
        self.trading_service_mock.get_symbol_info.return_value = {
            'trade_contract_size': 100000,
            'volume_min': 0.01,
            'volume_step': 0.01,
            'point': 0.0001
        }
        
        # Wykonanie
        result = self.trading_integration._create_trading_decision(signal, 0.8)
        
        # Weryfikacja
        self.assertIsInstance(result, TradingDecision)
        self.assertEqual(result.symbol, 'EURUSD')
        self.assertEqual(result.action, 'BUY')
        self.assertGreater(result.volume, 0)
        self.assertIsNotNone(result.stop_loss)
        self.assertIsNotNone(result.take_profit)
        self.assertEqual(result.signal_id, 1)
        self.assertEqual(result.quality_score, 0.8)
    
    def test_get_trading_integration(self):
        """Test funkcji get_trading_integration."""
        # Wykonanie
        integration = get_trading_integration()
        
        # Weryfikacja
        self.assertIsInstance(integration, TradingIntegration)
        self.assertIs(integration, self.trading_integration)


if __name__ == '__main__':
    unittest.main() 