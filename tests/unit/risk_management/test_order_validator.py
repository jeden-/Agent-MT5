#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Testy jednostkowe dla walidatora zleceń w module zarządzania ryzykiem.

Ten moduł zawiera testy dla klasy OrderValidator, która odpowiada
za walidację zleceń tradingowych pod kątem różnych reguł ryzyka.
"""

import unittest
from unittest.mock import MagicMock, patch
import sys
import os
from datetime import datetime

# Dodanie katalogu głównego projektu do PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../')))

from src.risk_management.order_validator import OrderValidator, get_order_validator
from src.risk_management.risk_manager import OrderValidationResult


class TestOrderValidator(unittest.TestCase):
    """Testy dla klasy OrderValidator."""

    def setUp(self):
        """Przygotowanie środowiska testowego przed każdym testem."""
        # Patchujemy singleton, aby każdy test miał nową instancję
        self.validator_patcher = patch('src.risk_management.order_validator.OrderValidator._instance', None)
        self.validator_patcher.start()
        
        # Mockowanie bazy danych
        self.mock_db = MagicMock()
        
        # Pobieranie instancji OrderValidator
        self.validator = get_order_validator()
        
        # Mockowanie metod lub pól używanych w testach
        self.validator.db = self.mock_db
        
        # Przykładowe informacje o symbolach
        self.mock_symbols_info = {
            "EURUSD": {"min_volume": 0.01, "max_volume": 50.0, "digits": 5},
            "GBPUSD": {"min_volume": 0.01, "max_volume": 50.0, "digits": 5},
            "GOLD": {"min_volume": 0.01, "max_volume": 20.0, "digits": 2}
        }
        self.validator.symbols_info = self.mock_symbols_info

    def tearDown(self):
        """Sprzątanie po każdym teście."""
        self.validator_patcher.stop()

    def test_init(self):
        """Test inicjalizacji obiektu OrderValidator."""
        self.assertIsNotNone(self.validator)
        self.assertEqual(self.validator.db, self.mock_db)
        self.assertEqual(self.validator.symbols_info, self.mock_symbols_info)

    def test_validate_symbol_valid(self):
        """Test walidacji poprawnego symbolu."""
        # Symbole znajdujące się w symbols_info powinny być poprawne
        self.assertTrue(self.validator.validate_symbol("EURUSD"))
        self.assertTrue(self.validator.validate_symbol("GBPUSD"))
        self.assertTrue(self.validator.validate_symbol("GOLD"))

    def test_validate_symbol_invalid(self):
        """Test walidacji niepoprawnego symbolu."""
        # Symbole nie znajdujące się w symbols_info powinny być niepoprawne
        self.assertFalse(self.validator.validate_symbol("INVALID"))
        self.assertFalse(self.validator.validate_symbol("BTCUSD"))  # Zakładamy, że nie ma w mock_symbols_info

    def test_validate_volume_valid(self):
        """Test walidacji poprawnego wolumenu."""
        # Wolumeny w zakresie min_volume - max_volume powinny być poprawne
        self.assertTrue(self.validator.validate_volume("EURUSD", 0.01))
        self.assertTrue(self.validator.validate_volume("EURUSD", 1.0))
        self.assertTrue(self.validator.validate_volume("EURUSD", 50.0))
        
        self.assertTrue(self.validator.validate_volume("GOLD", 0.01))
        self.assertTrue(self.validator.validate_volume("GOLD", 10.0))
        self.assertTrue(self.validator.validate_volume("GOLD", 20.0))

    def test_validate_volume_invalid(self):
        """Test walidacji niepoprawnego wolumenu."""
        # Wolumeny poza zakresem min_volume - max_volume powinny być niepoprawne
        self.assertFalse(self.validator.validate_volume("EURUSD", 0.0))
        self.assertFalse(self.validator.validate_volume("EURUSD", -1.0))
        self.assertFalse(self.validator.validate_volume("EURUSD", 50.01))
        
        self.assertFalse(self.validator.validate_volume("GOLD", 0.0))
        self.assertFalse(self.validator.validate_volume("GOLD", -0.01))
        self.assertFalse(self.validator.validate_volume("GOLD", 20.01))
        
        # Test dla nieistniejącego symbolu
        self.assertFalse(self.validator.validate_volume("INVALID", 1.0))

    def test_validate_stop_loss_valid(self):
        """Test walidacji poprawnego stop loss."""
        # Dla kupna (BUY) stop loss powinien być poniżej ceny otwarcia
        self.assertTrue(self.validator.validate_stop_loss("BUY", 1.1234, 1.1200))
        
        # Dla sprzedaży (SELL) stop loss powinien być powyżej ceny otwarcia
        self.assertTrue(self.validator.validate_stop_loss("SELL", 1.1234, 1.1300))

    def test_validate_stop_loss_invalid(self):
        """Test walidacji niepoprawnego stop loss."""
        # Dla kupna (BUY) stop loss nie powinien być powyżej ceny otwarcia
        self.assertFalse(self.validator.validate_stop_loss("BUY", 1.1234, 1.1300))
        
        # Dla sprzedaży (SELL) stop loss nie powinien być poniżej ceny otwarcia
        self.assertFalse(self.validator.validate_stop_loss("SELL", 1.1234, 1.1200))
        
        # Stop loss równy cenie otwarcia nie powinien być poprawny
        self.assertFalse(self.validator.validate_stop_loss("BUY", 1.1234, 1.1234))
        self.assertFalse(self.validator.validate_stop_loss("SELL", 1.1234, 1.1234))
        
        # Negatywny stop loss nie powinien być poprawny
        self.assertFalse(self.validator.validate_stop_loss("BUY", 1.1234, -1.0))
        self.assertFalse(self.validator.validate_stop_loss("SELL", 1.1234, -1.0))

    def test_validate_take_profit_valid(self):
        """Test walidacji poprawnego take profit."""
        # Dla kupna (BUY) take profit powinien być powyżej ceny otwarcia
        self.assertTrue(self.validator.validate_take_profit("BUY", 1.1234, 1.1300))
        
        # Dla sprzedaży (SELL) take profit powinien być poniżej ceny otwarcia
        self.assertTrue(self.validator.validate_take_profit("SELL", 1.1234, 1.1200))

    def test_validate_take_profit_invalid(self):
        """Test walidacji niepoprawnego take profit."""
        # Dla kupna (BUY) take profit nie powinien być poniżej ceny otwarcia
        self.assertFalse(self.validator.validate_take_profit("BUY", 1.1234, 1.1200))
        
        # Dla sprzedaży (SELL) take profit nie powinien być powyżej ceny otwarcia
        self.assertFalse(self.validator.validate_take_profit("SELL", 1.1234, 1.1300))
        
        # Take profit równy cenie otwarcia nie powinien być poprawny
        self.assertFalse(self.validator.validate_take_profit("BUY", 1.1234, 1.1234))
        self.assertFalse(self.validator.validate_take_profit("SELL", 1.1234, 1.1234))
        
        # Negatywny take profit nie powinien być poprawny
        self.assertFalse(self.validator.validate_take_profit("BUY", 1.1234, -1.0))
        self.assertFalse(self.validator.validate_take_profit("SELL", 1.1234, -1.0))

    def test_check_risk_reward_ratio_valid(self):
        """Test sprawdzania poprawnego stosunku ryzyka do zysku."""
        # Stosunek ryzyka do zysku powinien być co najmniej 1:1.5
        
        # Dla kupna (BUY):
        # Ryzyko = open_price - stop_loss = 1.1234 - 1.1134 = 0.01
        # Zysk = take_profit - open_price = 1.1384 - 1.1234 = 0.015
        # Stosunek 1:1.5
        self.assertTrue(self.validator.check_risk_reward_ratio("BUY", 1.1234, 1.1134, 1.1384))
        
        # Dla sprzedaży (SELL):
        # Ryzyko = stop_loss - open_price = 1.1334 - 1.1234 = 0.01
        # Zysk = open_price - take_profit = 1.1234 - 1.1084 = 0.015
        # Stosunek 1:1.5
        self.assertTrue(self.validator.check_risk_reward_ratio("SELL", 1.1234, 1.1334, 1.1084))

    def test_check_risk_reward_ratio_invalid(self):
        """Test sprawdzania niepoprawnego stosunku ryzyka do zysku."""
        # Stosunek ryzyka do zysku powinien być co najmniej 1:1.5
        
        # Dla kupna (BUY):
        # Ryzyko = open_price - stop_loss = 1.1234 - 1.1134 = 0.01
        # Zysk = take_profit - open_price = 1.1334 - 1.1234 = 0.01
        # Stosunek 1:1 (za niski)
        self.assertFalse(self.validator.check_risk_reward_ratio("BUY", 1.1234, 1.1134, 1.1334))
        
        # Dla sprzedaży (SELL):
        # Ryzyko = stop_loss - open_price = 1.1334 - 1.1234 = 0.01
        # Zysk = open_price - take_profit = 1.1234 - 1.1134 = 0.01
        # Stosunek 1:1 (za niski)
        self.assertFalse(self.validator.check_risk_reward_ratio("SELL", 1.1234, 1.1334, 1.1134))

    def test_validate_order_full(self):
        """Test pełnej walidacji zlecenia."""
        # Mockowanie metod składowych
        self.validator.validate_symbol = MagicMock(return_value=True)
        self.validator.validate_volume = MagicMock(return_value=True)
        self.validator.validate_stop_loss = MagicMock(return_value=True)
        self.validator.validate_take_profit = MagicMock(return_value=True)
        self.validator.check_risk_reward_ratio = MagicMock(return_value=True)
        
        # Dane zlecenia
        order_data = {
            "symbol": "EURUSD",
            "type": "BUY",
            "volume": 0.1,
            "price": 1.1234,
            "stop_loss": 1.1200,
            "take_profit": 1.1300
        }
        
        # Walidacja powinna się powieść
        result = self.validator.validate_order(order_data)
        self.assertEqual(result, OrderValidationResult.VALID)
        
        # Sprawdzenie, czy wszystkie metody walidacji zostały wywołane
        self.validator.validate_symbol.assert_called_once_with(order_data["symbol"])
        self.validator.validate_volume.assert_called_once_with(order_data["symbol"], order_data["volume"])
        self.validator.validate_stop_loss.assert_called_once_with(order_data["type"], order_data["price"], order_data["stop_loss"])
        self.validator.validate_take_profit.assert_called_once_with(order_data["type"], order_data["price"], order_data["take_profit"])
        self.validator.check_risk_reward_ratio.assert_called_once_with(
            order_data["type"], order_data["price"], order_data["stop_loss"], order_data["take_profit"]
        )


if __name__ == '__main__':
    unittest.main() 