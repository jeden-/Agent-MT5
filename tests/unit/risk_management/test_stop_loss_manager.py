#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Testy jednostkowe dla menedżera stop-lossów w systemie zarządzania ryzykiem.

Ten moduł zawiera testy dla klasy StopLossManager, która odpowiada
za zarządzanie poziomami stop-loss w systemie tradingowym, w tym
mechanizmy trailing-stop i automatycznego dostosowywania SL.
"""

import unittest
from unittest.mock import MagicMock, patch
import sys
import os
from datetime import datetime, timedelta

# Dodanie katalogu głównego projektu do PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../')))

from src.risk_management.stop_loss_manager import StopLossManager, get_stop_loss_manager


class TestStopLossManager(unittest.TestCase):
    """Testy dla klasy StopLossManager."""

    def setUp(self):
        """Przygotowanie środowiska testowego przed każdym testem."""
        # Patchujemy singleton, aby każdy test miał nową instancję
        self.sl_manager_patcher = patch('src.risk_management.stop_loss_manager.StopLossManager._instance', None)
        self.sl_manager_patcher.start()
        
        # Mockowanie bazy danych, mostu MT5 i menedżera pozycji
        self.mock_db = MagicMock()
        self.mock_mt5_bridge = MagicMock()
        self.mock_position_manager = MagicMock()
        
        # Pobieranie instancji StopLossManager
        self.sl_manager = get_stop_loss_manager()
        
        # Mockowanie metod lub pól używanych w testach
        self.sl_manager.db = self.mock_db
        self.sl_manager.mt5_bridge = self.mock_mt5_bridge
        self.sl_manager.position_manager = self.mock_position_manager
        
        # Przykładowa pozycja BUY
        self.buy_position = {
            "ticket": 12345,
            "symbol": "EURUSD",
            "type": "BUY",
            "volume": 0.1,
            "open_price": 1.1200,
            "current_price": 1.1250,
            "stop_loss": 1.1150,
            "take_profit": 1.1300,
            "profit": 50.0,
            "open_time": datetime.now() - timedelta(hours=2)
        }
        
        # Przykładowa pozycja SELL
        self.sell_position = {
            "ticket": 12346,
            "symbol": "GBPUSD",
            "type": "SELL",
            "volume": 0.2,
            "open_price": 1.3100,
            "current_price": 1.3050,
            "stop_loss": 1.3150,
            "take_profit": 1.3000,
            "profit": 100.0,
            "open_time": datetime.now() - timedelta(hours=1)
        }

    def tearDown(self):
        """Sprzątanie po każdym teście."""
        self.sl_manager_patcher.stop()

    def test_init(self):
        """Test inicjalizacji obiektu StopLossManager."""
        self.assertIsNotNone(self.sl_manager)
        self.assertEqual(self.sl_manager.db, self.mock_db)
        self.assertEqual(self.sl_manager.mt5_bridge, self.mock_mt5_bridge)
        self.assertEqual(self.sl_manager.position_manager, self.mock_position_manager)

    def test_calculate_trailing_stop_buy(self):
        """Test obliczania trailing-stop dla pozycji BUY."""
        # Obecny stop loss: 1.1150
        # Obecna cena: 1.1250
        # Trailing step: 0.0010 (10 pips)
        # Oczekiwany nowy stop loss: 1.1150 + 0.0050 = 1.1200 (50 pips ruchu)
        new_sl = self.sl_manager.calculate_trailing_stop(
            position=self.buy_position,
            trailing_step=0.0010,
            activation_pips=20  # Aktywuje trailing stop po 20 pipsach zysku
        )
        
        # Pozycja znajduje się 50 pipsów na plusie, więc powinna przenieść SL
        # SL powinien być podniesiony do 1.1200 (cena otwarcia)
        self.assertEqual(new_sl, 1.1200)

    def test_calculate_trailing_stop_sell(self):
        """Test obliczania trailing-stop dla pozycji SELL."""
        # Obecny stop loss: 1.3150
        # Obecna cena: 1.3050
        # Trailing step: 0.0010 (10 pips)
        # Oczekiwany nowy stop loss: 1.3150 - 0.0050 = 1.3100 (50 pips ruchu)
        new_sl = self.sl_manager.calculate_trailing_stop(
            position=self.sell_position,
            trailing_step=0.0010,
            activation_pips=20  # Aktywuje trailing stop po 20 pipsach zysku
        )
        
        # Pozycja znajduje się 50 pipsów na plusie, więc powinna przenieść SL
        # SL powinien być obniżony do 1.3100 (cena otwarcia)
        self.assertEqual(new_sl, 1.3100)

    def test_calculate_trailing_stop_not_activated(self):
        """Test gdy trailing-stop nie zostaje aktywowany (za mały zysk)."""
        # Zmodyfikujmy pozycję, aby była tylko 5 pipsów na plusie
        buy_position_small_profit = self.buy_position.copy()
        buy_position_small_profit["current_price"] = 1.1205  # Tylko 5 pipsów zysku
        
        new_sl = self.sl_manager.calculate_trailing_stop(
            position=buy_position_small_profit,
            trailing_step=0.0010,
            activation_pips=20  # Aktywuje trailing stop po 20 pipsach zysku
        )
        
        # SL nie powinien się zmienić, ponieważ zysk jest za mały
        self.assertEqual(new_sl, buy_position_small_profit["stop_loss"])

    def test_update_stop_loss(self):
        """Test aktualizacji stop-loss dla pozycji."""
        # Mockowanie metody modify_position z mt5_bridge
        self.mock_mt5_bridge.modify_position.return_value = {"status": "success"}
        
        # Nowy poziom stop-loss
        new_sl = 1.1180
        
        # Wywołanie testowanej metody
        result = self.sl_manager.update_stop_loss(self.buy_position, new_sl)
        
        # Sprawdzenie wyniku
        self.assertTrue(result)
        
        # Sprawdzenie, czy modify_position zostało wywołane z właściwymi parametrami
        self.mock_mt5_bridge.modify_position.assert_called_once_with(
            ticket=self.buy_position["ticket"],
            stop_loss=new_sl,
            take_profit=self.buy_position["take_profit"]
        )
        
        # Test przypadku, gdy modyfikacja się nie powiedzie
        self.mock_mt5_bridge.modify_position.return_value = {"status": "error", "message": "Failed to modify"}
        
        # Wywołanie testowanej metody ponownie
        result = self.sl_manager.update_stop_loss(self.buy_position, new_sl)
        
        # Sprawdzenie wyniku
        self.assertFalse(result)

    def test_update_trailing_stops_for_all_positions(self):
        """Test aktualizacji trailing-stop dla wszystkich pozycji."""
        # Mockowanie metody get_active_positions
        self.mock_position_manager.get_active_positions.return_value = [self.buy_position, self.sell_position]
        
        # Mockowanie metody calculate_trailing_stop
        self.sl_manager.calculate_trailing_stop = MagicMock()
        self.sl_manager.calculate_trailing_stop.side_effect = [1.1200, 1.3100]  # Dla BUY i SELL pozycji
        
        # Mockowanie metody update_stop_loss
        self.sl_manager.update_stop_loss = MagicMock(return_value=True)
        
        # Wywołanie testowanej metody
        updated_positions = self.sl_manager.update_trailing_stops_for_all_positions(
            trailing_step=0.0010,
            activation_pips=20
        )
        
        # Powinny zostać zaktualizowane 2 pozycje
        self.assertEqual(len(updated_positions), 2)
        
        # Sprawdzenie, czy calculate_trailing_stop zostało wywołane dla obu pozycji
        self.assertEqual(self.sl_manager.calculate_trailing_stop.call_count, 2)
        
        # Sprawdzenie, czy update_stop_loss zostało wywołane dla obu pozycji
        self.assertEqual(self.sl_manager.update_stop_loss.call_count, 2)
        
        # Sprawdzenie wywołań dla pierwszej pozycji
        self.sl_manager.calculate_trailing_stop.assert_any_call(
            position=self.buy_position,
            trailing_step=0.0010,
            activation_pips=20
        )
        self.sl_manager.update_stop_loss.assert_any_call(self.buy_position, 1.1200)
        
        # Sprawdzenie wywołań dla drugiej pozycji
        self.sl_manager.calculate_trailing_stop.assert_any_call(
            position=self.sell_position,
            trailing_step=0.0010,
            activation_pips=20
        )
        self.sl_manager.update_stop_loss.assert_any_call(self.sell_position, 1.3100)

    def test_calculate_break_even_level(self):
        """Test obliczania poziomu break-even."""
        # Dla pozycji BUY:
        # Cena otwarcia: 1.1200
        # Break-even offset: 0.0005 (5 pips powyżej ceny otwarcia)
        # Oczekiwany break-even: 1.1205
        be_level = self.sl_manager.calculate_break_even_level(self.buy_position, 0.0005)
        self.assertEqual(be_level, 1.1205)
        
        # Dla pozycji SELL:
        # Cena otwarcia: 1.3100
        # Break-even offset: 0.0005 (5 pips poniżej ceny otwarcia)
        # Oczekiwany break-even: 1.3095
        be_level = self.sl_manager.calculate_break_even_level(self.sell_position, 0.0005)
        self.assertEqual(be_level, 1.3095)

    def test_move_to_break_even(self):
        """Test przenoszenia stop-loss na poziom break-even."""
        # Mockowanie metody calculate_break_even_level
        self.sl_manager.calculate_break_even_level = MagicMock(return_value=1.1205)
        
        # Mockowanie metody update_stop_loss
        self.sl_manager.update_stop_loss = MagicMock(return_value=True)
        
        # Wywołanie testowanej metody
        result = self.sl_manager.move_to_break_even(
            position=self.buy_position,
            activation_pips=30,  # Aktywuje break-even po 30 pipsach zysku
            offset_pips=5  # 5 pipsów powyżej ceny otwarcia
        )
        
        # Sprawdzenie wyniku (powinien przenieść SL)
        self.assertTrue(result)
        
        # Sprawdzenie, czy calculate_break_even_level zostało wywołane
        self.sl_manager.calculate_break_even_level.assert_called_once_with(
            self.buy_position, 0.0005
        )
        
        # Sprawdzenie, czy update_stop_loss zostało wywołane
        self.sl_manager.update_stop_loss.assert_called_once_with(
            self.buy_position, 1.1205
        )
        
        # Test przypadku, gdy zysk jest za mały
        buy_position_small_profit = self.buy_position.copy()
        buy_position_small_profit["current_price"] = 1.1220  # Tylko 20 pipsów zysku
        
        # Reset mocków
        self.sl_manager.calculate_break_even_level.reset_mock()
        self.sl_manager.update_stop_loss.reset_mock()
        
        # Wywołanie testowanej metody
        result = self.sl_manager.move_to_break_even(
            position=buy_position_small_profit,
            activation_pips=30,  # Aktywuje break-even po 30 pipsach zysku
            offset_pips=5  # 5 pipsów powyżej ceny otwarcia
        )
        
        # Sprawdzenie wyniku (nie powinien przenieść SL)
        self.assertFalse(result)
        
        # calculate_break_even_level i update_stop_loss nie powinny być wywołane
        self.sl_manager.calculate_break_even_level.assert_not_called()
        self.sl_manager.update_stop_loss.assert_not_called()


if __name__ == '__main__':
    unittest.main() 