#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Testy jednostkowe dla modułu śledzenia ekspozycji w systemie zarządzania ryzykiem.

Ten moduł zawiera testy dla klasy ExposureTracker, która odpowiada
za monitorowanie łącznej ekspozycji na ryzyko w systemie tradingowym.
"""

import unittest
from unittest.mock import MagicMock, patch
import sys
import os
from datetime import datetime, timedelta

# Dodanie katalogu głównego projektu do PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../')))

from src.risk_management.exposure_tracker import ExposureTracker, get_exposure_tracker


class TestExposureTracker(unittest.TestCase):
    """Testy dla klasy ExposureTracker."""

    def setUp(self):
        """Przygotowanie środowiska testowego przed każdym testem."""
        # Patchujemy singleton, aby każdy test miał nową instancję
        self.tracker_patcher = patch('src.risk_management.exposure_tracker.ExposureTracker._instance', None)
        self.tracker_patcher.start()
        
        # Mockowanie bazy danych i menedżera pozycji
        self.mock_db = MagicMock()
        self.mock_position_manager = MagicMock()
        
        # Pobieranie instancji ExposureTracker
        self.tracker = get_exposure_tracker()
        
        # Mockowanie metod lub pól używanych w testach
        self.tracker.db = self.mock_db
        self.tracker.position_manager = self.mock_position_manager
        
        # Mockowanie aktywnych pozycji
        self.mock_positions = [
            {
                "ticket": 12345,
                "symbol": "EURUSD",
                "type": "BUY",
                "volume": 0.1,
                "open_price": 1.1234,
                "current_price": 1.1250,
                "stop_loss": 1.1200,
                "take_profit": 1.1300,
                "profit": 16.0,
                "open_time": datetime.now() - timedelta(hours=2)
            },
            {
                "ticket": 12346,
                "symbol": "GBPUSD",
                "type": "SELL",
                "volume": 0.2,
                "open_price": 1.3100,
                "current_price": 1.3080,
                "stop_loss": 1.3150,
                "take_profit": 1.3000,
                "profit": 40.0,
                "open_time": datetime.now() - timedelta(hours=1)
            }
        ]
        self.mock_position_manager.get_active_positions.return_value = self.mock_positions
        
        # Mockowanie informacji o koncie
        self.mock_account_info = {
            "balance": 10000.0,
            "equity": 10056.0,
            "margin": 250.0,
            "free_margin": 9806.0,
            "margin_level": 4022.4,
            "currency": "USD"
        }

    def tearDown(self):
        """Sprzątanie po każdym teście."""
        self.tracker_patcher.stop()

    def test_init(self):
        """Test inicjalizacji obiektu ExposureTracker."""
        self.assertIsNotNone(self.tracker)
        self.assertEqual(self.tracker.db, self.mock_db)
        self.assertEqual(self.tracker.position_manager, self.mock_position_manager)

    def test_calculate_total_exposure(self):
        """Test obliczania całkowitej ekspozycji."""
        # Mockowanie metody get_account_info
        self.tracker.get_account_info = MagicMock(return_value=self.mock_account_info)
        
        # Wywołanie testowanej metody
        exposure = self.tracker.calculate_total_exposure()
        
        # Oczekiwane obliczenie:
        # margin / balance * 100% = 250 / 10000 * 100% = 2.5%
        self.assertAlmostEqual(exposure, 0.025, places=3)  # 2.5%
        
        # Sprawdzenie, czy get_account_info zostało wywołane
        self.tracker.get_account_info.assert_called_once()

    def test_get_positions_by_symbol(self):
        """Test pobierania pozycji dla określonego symbolu."""
        # Mockowanie metody get_active_positions
        self.tracker.get_active_positions = MagicMock(return_value=self.mock_positions)
        
        # Wywołanie testowanej metody dla EURUSD
        positions_eurusd = self.tracker.get_positions_by_symbol("EURUSD")
        
        # Powinniśmy dostać jedną pozycję EURUSD
        self.assertEqual(len(positions_eurusd), 1)
        self.assertEqual(positions_eurusd[0]["symbol"], "EURUSD")
        
        # Wywołanie testowanej metody dla GBPUSD
        positions_gbpusd = self.tracker.get_positions_by_symbol("GBPUSD")
        
        # Powinniśmy dostać jedną pozycję GBPUSD
        self.assertEqual(len(positions_gbpusd), 1)
        self.assertEqual(positions_gbpusd[0]["symbol"], "GBPUSD")
        
        # Wywołanie testowanej metody dla AUDUSD (nie ma pozycji)
        positions_audusd = self.tracker.get_positions_by_symbol("AUDUSD")
        
        # Nie powinno być żadnych pozycji
        self.assertEqual(len(positions_audusd), 0)

    def test_calculate_symbol_exposure(self):
        """Test obliczania ekspozycji dla określonego symbolu."""
        # Mockowanie metody get_account_info
        self.tracker.get_account_info = MagicMock(return_value=self.mock_account_info)
        
        # Mockowanie metody get_positions_by_symbol
        self.tracker.get_positions_by_symbol = MagicMock()
        
        # Mockowanie dla EURUSD (jedna pozycja)
        self.tracker.get_positions_by_symbol.side_effect = lambda symbol: [self.mock_positions[0]] if symbol == "EURUSD" else []
        
        # Wywołanie testowanej metody dla EURUSD
        exposure_eurusd = self.tracker.calculate_symbol_exposure("EURUSD")
        
        # Oczekiwane obliczenie:
        # Zakładamy, że margin dla EURUSD to około 0.1 lota * 1000 USD = 100 USD
        # 100 USD / 10000 USD * 100% = 1%
        self.assertAlmostEqual(exposure_eurusd, 0.01, places=2)  # 1%
        
        # Mockowanie dla GBPUSD (jedna pozycja)
        self.tracker.get_positions_by_symbol.side_effect = lambda symbol: [self.mock_positions[1]] if symbol == "GBPUSD" else []
        
        # Wywołanie testowanej metody dla GBPUSD
        exposure_gbpusd = self.tracker.calculate_symbol_exposure("GBPUSD")
        
        # Oczekiwane obliczenie:
        # Zakładamy, że margin dla GBPUSD to około 0.2 lota * 1000 USD = 200 USD
        # 200 USD / 10000 USD * 100% = 2%
        self.assertAlmostEqual(exposure_gbpusd, 0.02, places=2)  # 2%

    def test_calculate_daily_pnl(self):
        """Test obliczania dziennego zysku/straty."""
        # Mockowanie metody get_positions_opened_today
        today_date = datetime.now().date()
        today_positions = [
            {
                "ticket": 12347,
                "symbol": "EURUSD",
                "type": "BUY",
                "volume": 0.1,
                "open_price": 1.1234,
                "current_price": 1.1250,
                "profit": 16.0,
                "open_time": datetime.now() - timedelta(hours=2)
            },
            {
                "ticket": 12348,
                "symbol": "GBPUSD",
                "type": "SELL",
                "volume": 0.2,
                "open_price": 1.3100,
                "current_price": 1.3080,
                "profit": 40.0,
                "open_time": datetime.now() - timedelta(hours=1)
            }
        ]
        
        # Mockujemy metody db.execute_query
        self.mock_db.execute_query.return_value = [
            {"profit": 16.0}, 
            {"profit": 40.0}
        ]
        
        # Wywołanie testowanej metody
        daily_pnl = self.tracker.calculate_daily_pnl()
        
        # Oczekiwany wynik: 16.0 + 40.0 = 56.0
        self.assertEqual(daily_pnl, 56.0)
        
        # Sprawdzenie czy zapytanie SQL zostało wykonane
        self.mock_db.execute_query.assert_called_once()
        
        # Mockowanie wyniku dla straty
        self.mock_db.execute_query.return_value = [
            {"profit": -20.0}, 
            {"profit": -15.0}
        ]
        
        # Wywołanie testowanej metody ponownie
        daily_pnl = self.tracker.calculate_daily_pnl()
        
        # Oczekiwany wynik: -20.0 + -15.0 = -35.0
        self.assertEqual(daily_pnl, -35.0)

    def test_get_exposure_report(self):
        """Test generowania raportu ekspozycji."""
        # Mockowanie metod używanych w get_exposure_report
        self.tracker.calculate_total_exposure = MagicMock(return_value=0.025)  # 2.5%
        self.tracker.calculate_symbol_exposure = MagicMock()
        self.tracker.calculate_symbol_exposure.side_effect = lambda symbol: 0.01 if symbol == "EURUSD" else (0.02 if symbol == "GBPUSD" else 0.0)
        self.tracker.calculate_daily_pnl = MagicMock(return_value=56.0)
        self.tracker.get_active_positions = MagicMock(return_value=self.mock_positions)
        self.tracker.get_account_info = MagicMock(return_value=self.mock_account_info)
        
        # Wywołanie testowanej metody
        report = self.tracker.get_exposure_report()
        
        # Sprawdzenie struktury raportu
        self.assertIn("timestamp", report)
        self.assertIn("total_exposure", report)
        self.assertIn("symbols_exposure", report)
        self.assertIn("daily_pnl", report)
        self.assertIn("positions_count", report)
        self.assertIn("account_info", report)
        
        # Sprawdzenie wartości raportu
        self.assertEqual(report["total_exposure"], 0.025)
        self.assertEqual(report["daily_pnl"], 56.0)
        self.assertEqual(report["positions_count"], 2)
        self.assertEqual(report["symbols_exposure"]["EURUSD"], 0.01)
        self.assertEqual(report["symbols_exposure"]["GBPUSD"], 0.02)
        self.assertEqual(report["account_info"], self.mock_account_info)


if __name__ == '__main__':
    unittest.main() 