#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Testy jednostkowe dla modułu zarządzania ryzykiem.

Ten moduł zawiera testy dla głównej klasy RiskManager, która odpowiada
za całościowe zarządzanie ryzykiem w systemie tradingowym.
"""

import unittest
from unittest.mock import MagicMock, patch
import sys
import os
from datetime import datetime

# Dodanie katalogu głównego projektu do PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../')))

from src.risk_management.risk_manager import RiskManager, RiskParameters, OrderValidationResult, RiskLevel, get_risk_manager


class TestRiskManager(unittest.TestCase):
    """Testy dla klasy RiskManager."""

    def setUp(self):
        """Przygotowanie środowiska testowego przed każdym testem."""
        # Patchujemy singleton, aby każdy test miał nową instancję
        self.risk_manager_patcher = patch('src.risk_management.risk_manager.RiskManager._instance', None)
        self.risk_manager_patcher.start()
        
        # Mockowanie bazy danych
        self.mock_db = MagicMock()
        
        # Pobieranie instancji RiskManager
        self.risk_manager = get_risk_manager()
        
        # Mockowanie metod lub pól używanych w testach
        self.risk_manager.db = self.mock_db
        
        # Ustawienie parametrów ryzyka
        self.risk_params = RiskParameters(
            max_positions_per_symbol=3,
            max_positions_total=10,
            max_daily_loss_percent=2.0,
            max_position_size_percent=5.0
        )
        self.risk_manager.parameters = self.risk_params

    def tearDown(self):
        """Sprzątanie po każdym teście."""
        self.risk_manager_patcher.stop()

    def test_init(self):
        """Test inicjalizacji obiektu RiskManager."""
        self.assertIsNotNone(self.risk_manager)
        self.assertEqual(self.risk_manager.db, self.mock_db)
        self.assertEqual(self.risk_manager.parameters, self.risk_params)

    def test_validate_order_valid(self):
        """Test walidacji poprawnego zlecenia."""
        # Przygotowanie mockowanych danych
        order_data = {
            "symbol": "EURUSD",
            "volume": 0.1,
            "price": 1.1234,
            "type": "BUY",
            "stop_loss": 1.1200,
            "take_profit": 1.1300
        }
        
        # Mockowanie metod wykorzystywanych przez validate_order
        self.risk_manager._validate_symbol = MagicMock(return_value=True)
        self.risk_manager._validate_volume = MagicMock(return_value=True)
        self.risk_manager._validate_price = MagicMock(return_value=True)
        self.risk_manager._validate_sl_tp = MagicMock(return_value=True)
        self.risk_manager._check_position_limits = MagicMock(return_value=True)
        self.risk_manager._check_exposure_limits = MagicMock(return_value=True)
        self.risk_manager._check_risk_reward_ratio = MagicMock(return_value=True)
        
        # Wywołanie testowanej metody
        result = self.risk_manager.validate_order(order_data)
        
        # Sprawdzenie wyniku
        self.assertEqual(result, OrderValidationResult.VALID)
        
        # Weryfikacja, że wszystkie metody walidacji zostały wywołane
        self.risk_manager._validate_symbol.assert_called_once_with(order_data["symbol"])
        self.risk_manager._validate_volume.assert_called_once_with(order_data["volume"])
        self.risk_manager._validate_price.assert_called_once_with(order_data["price"])
        self.risk_manager._validate_sl_tp.assert_called_once_with(order_data)
        self.risk_manager._check_position_limits.assert_called_once_with(order_data["symbol"])
        self.risk_manager._check_exposure_limits.assert_called_once_with(order_data)
        self.risk_manager._check_risk_reward_ratio.assert_called_once_with(order_data)

    def test_validate_order_invalid_symbol(self):
        """Test walidacji zlecenia z niepoprawnym symbolem."""
        order_data = {"symbol": "INVALID", "volume": 0.1, "price": 1.1234}
        
        # Mockowanie metody _validate_symbol, aby zwróciła False
        self.risk_manager._validate_symbol = MagicMock(return_value=False)
        
        # Wywołanie testowanej metody
        result = self.risk_manager.validate_order(order_data)
        
        # Sprawdzenie wyniku
        self.assertEqual(result, OrderValidationResult.INVALID_SYMBOL)

    def test_calculate_position_risk(self):
        """Test obliczania ryzyka pozycji."""
        # Dane testowe
        position_data = {
            "symbol": "EURUSD",
            "volume": 0.1,
            "open_price": 1.1234,
            "stop_loss": 1.1200,
            "account_balance": 10000
        }
        
        # Oczekiwany wynik: ryzyko = (1.1234 - 1.1200) * 0.1 * 10000 EUR/USD * 100000 (lot size) / 10000 (balance) * 100%
        expected_risk_percent = 0.34
        
        # Wywołanie testowanej metody
        result = self.risk_manager.calculate_position_risk(position_data)
        
        # Sprawdzenie wyniku z zaokrągleniem do 2 miejsc po przecinku
        self.assertAlmostEqual(result, expected_risk_percent, places=2)

    def test_get_current_risk_level(self):
        """Test pobierania aktualnego poziomu ryzyka."""
        # Mockowanie metody _calculate_total_exposure
        self.risk_manager._calculate_total_exposure = MagicMock(return_value=0.2)  # 20% ekspozycji
        
        # Wywołanie testowanej metody
        result = self.risk_manager.get_current_risk_level()
        
        # Sprawdzenie wyniku (przy 20% ekspozycji powinien być MEDIUM)
        self.assertEqual(result, RiskLevel.MEDIUM)
        
        # Test dla niższego poziomu ekspozycji
        self.risk_manager._calculate_total_exposure = MagicMock(return_value=0.05)  # 5% ekspozycji
        result = self.risk_manager.get_current_risk_level()
        self.assertEqual(result, RiskLevel.LOW)
        
        # Test dla wysokiego poziomu ekspozycji
        self.risk_manager._calculate_total_exposure = MagicMock(return_value=0.35)  # 35% ekspozycji
        result = self.risk_manager.get_current_risk_level()
        self.assertEqual(result, RiskLevel.HIGH)
        
        # Test dla krytycznego poziomu ekspozycji
        self.risk_manager._calculate_total_exposure = MagicMock(return_value=0.5)  # 50% ekspozycji
        result = self.risk_manager.get_current_risk_level()
        self.assertEqual(result, RiskLevel.CRITICAL)


if __name__ == '__main__':
    unittest.main() 