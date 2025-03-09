import unittest
from unittest.mock import MagicMock, patch
import json
import os
import sys
from datetime import datetime

# Dodajemy ścieżkę główną projektu do sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../')))

# Import testowanego modułu (zostanie utworzony później)
from src.position_management.position_manager import PositionManager, Position, PositionStatus, PositionError

class TestPositionManager(unittest.TestCase):
    def setUp(self):
        """Przygotowanie środowiska testowego przed każdym testem."""
        # Mockowanie bazy danych i innych zewnętrznych zależności
        self.db_mock = MagicMock()
        self.api_client_mock = MagicMock()
        
        # Tworzenie instancji Position Managera z zmockowanymi zależnościami
        self.position_manager = PositionManager(
            db_connection=self.db_mock,
            api_client=self.api_client_mock
        )
    
    def tearDown(self):
        """Czyszczenie po każdym teście."""
        pass
    
    def test_add_position(self):
        """Test dodawania nowej pozycji."""
        # Dane testowe
        position_data = {
            "ea_id": "EA_1741521231",
            "ticket": 89216817,
            "symbol": "GOLD.pro",
            "type": "BUY",
            "volume": 0.10,
            "open_price": 2917.28,
            "current_price": 2910.18,
            "sl": 0.0,
            "tp": 0.0,
            "profit": -274.52,
            "open_time": "2025.03.07 09:03"
        }
        
        # Wykonanie testu
        position = self.position_manager.add_position(position_data)
        
        # Asercje
        self.assertIsInstance(position, Position)
        self.assertEqual(position.ticket, 89216817)
        self.assertEqual(position.symbol, "GOLD.pro")
        self.assertEqual(position.type, "BUY")
        self.assertEqual(position.volume, 0.10)
        self.assertEqual(position.status, PositionStatus.OPEN)
        
        # Sprawdzenie wywołania bazy danych
        self.db_mock.save_position.assert_called_once()
    
    def test_get_position_by_ticket(self):
        """Test pobierania pozycji po numerze ticketu."""
        # Dane testowe
        ticket = 89216817
        mock_position = Position(
            ea_id="EA_1741521231",
            ticket=ticket,
            symbol="GOLD.pro",
            type="BUY",
            volume=0.10,
            open_price=2917.28,
            current_price=2910.18,
            sl=0.0,
            tp=0.0,
            profit=-274.52,
            open_time=datetime.strptime("2025.03.07 09:03", "%Y.%m.%d %H:%M"),
            status=PositionStatus.OPEN
        )
        
        # Konfiguracja mocka
        self.position_manager._positions = {ticket: mock_position}
        
        # Wykonanie testu
        position = self.position_manager.get_position_by_ticket(ticket)
        
        # Asercje
        self.assertEqual(position, mock_position)
    
    def test_get_position_by_ticket_not_found(self):
        """Test pobierania pozycji, która nie istnieje."""
        # Wykonanie testu
        with self.assertRaises(PositionError):
            self.position_manager.get_position_by_ticket(999999)
    
    def test_update_position(self):
        """Test aktualizacji istniejącej pozycji."""
        # Dane testowe
        ticket = 89216817
        mock_position = Position(
            ea_id="EA_1741521231",
            ticket=ticket,
            symbol="GOLD.pro",
            type="BUY",
            volume=0.10,
            open_price=2917.28,
            current_price=2910.18,
            sl=0.0,
            tp=0.0,
            profit=-274.52,
            open_time=datetime.strptime("2025.03.07 09:03", "%Y.%m.%d %H:%M"),
            status=PositionStatus.OPEN
        )
        
        # Konfiguracja mocka
        self.position_manager._positions = {ticket: mock_position}
        
        # Nowe dane
        update_data = {
            "current_price": 2920.50,
            "profit": 50.21,
            "sl": 2900.0,
            "tp": 2950.0
        }
        
        # Wykonanie testu
        updated_position = self.position_manager.update_position(ticket, update_data)
        
        # Asercje
        self.assertEqual(updated_position.current_price, 2920.50)
        self.assertEqual(updated_position.profit, 50.21)
        self.assertEqual(updated_position.sl, 2900.0)
        self.assertEqual(updated_position.tp, 2950.0)
        
        # Sprawdzenie wywołania bazy danych
        self.db_mock.update_position.assert_called_once()
    
    def test_close_position(self):
        """Test zamykania pozycji."""
        # Dane testowe
        ticket = 89216817
        mock_position = Position(
            ea_id="EA_1741521231",
            ticket=ticket,
            symbol="GOLD.pro",
            type="BUY",
            volume=0.10,
            open_price=2917.28,
            current_price=2910.18,
            sl=0.0,
            tp=0.0,
            profit=-274.52,
            open_time=datetime.strptime("2025.03.07 09:03", "%Y.%m.%d %H:%M"),
            status=PositionStatus.OPEN
        )
        
        # Konfiguracja mocka
        self.position_manager._positions = {ticket: mock_position}
        
        # Dane zamknięcia
        close_data = {
            "close_price": 2925.0,
            "close_time": "2025.03.08 14:30",
            "profit": 85.5
        }
        
        # Wykonanie testu
        closed_position = self.position_manager.close_position(ticket, close_data)
        
        # Asercje
        self.assertEqual(closed_position.status, PositionStatus.CLOSED)
        self.assertEqual(closed_position.close_price, 2925.0)
        self.assertEqual(closed_position.profit, 85.5)
        self.assertIsNotNone(closed_position.close_time)
        
        # Sprawdzenie wywołania bazy danych
        self.db_mock.update_position.assert_called_once()
    
    def test_get_active_positions(self):
        """Test pobierania aktywnych pozycji."""
        # Dane testowe
        positions = {
            1: Position(ea_id="EA_1", ticket=1, symbol="EURUSD", type="BUY", volume=0.1,
                      open_price=1.1, current_price=1.12, sl=0, tp=0, profit=20,
                      open_time=datetime.now(), status=PositionStatus.OPEN),
            2: Position(ea_id="EA_1", ticket=2, symbol="GBPUSD", type="SELL", volume=0.2,
                      open_price=1.3, current_price=1.29, sl=0, tp=0, profit=15,
                      open_time=datetime.now(), status=PositionStatus.OPEN),
            3: Position(ea_id="EA_1", ticket=3, symbol="USDJPY", type="BUY", volume=0.1,
                      open_price=110, current_price=109, sl=0, tp=0, profit=-10,
                      open_time=datetime.now(), status=PositionStatus.CLOSED)
        }
        
        # Konfiguracja mocka
        self.position_manager._positions = positions
        
        # Wykonanie testu
        active_positions = self.position_manager.get_active_positions()
        
        # Asercje
        self.assertEqual(len(active_positions), 2)
        self.assertIn(positions[1], active_positions)
        self.assertIn(positions[2], active_positions)
        self.assertNotIn(positions[3], active_positions)
    
    def test_get_positions_by_ea_id(self):
        """Test pobierania pozycji dla konkretnego EA."""
        # Dane testowe
        positions = {
            1: Position(ea_id="EA_1", ticket=1, symbol="EURUSD", type="BUY", volume=0.1,
                      open_price=1.1, current_price=1.12, sl=0, tp=0, profit=20,
                      open_time=datetime.now(), status=PositionStatus.OPEN),
            2: Position(ea_id="EA_2", ticket=2, symbol="GBPUSD", type="SELL", volume=0.2,
                      open_price=1.3, current_price=1.29, sl=0, tp=0, profit=15,
                      open_time=datetime.now(), status=PositionStatus.OPEN),
            3: Position(ea_id="EA_1", ticket=3, symbol="USDJPY", type="BUY", volume=0.1,
                      open_price=110, current_price=109, sl=0, tp=0, profit=-10,
                      open_time=datetime.now(), status=PositionStatus.CLOSED)
        }
        
        # Konfiguracja mocka
        self.position_manager._positions = positions
        
        # Wykonanie testu
        ea_positions = self.position_manager.get_positions_by_ea_id("EA_1")
        
        # Asercje
        self.assertEqual(len(ea_positions), 2)
        self.assertIn(positions[1], ea_positions)
        self.assertIn(positions[3], ea_positions)
        self.assertNotIn(positions[2], ea_positions)
    
    def test_sync_positions_with_mt5(self):
        """Test synchronizacji pozycji z MT5."""
        # Dane testowe z MT5
        mt5_positions = [
            {
                "ea_id": "EA_1741521231",
                "ticket": 89216817,
                "symbol": "GOLD.pro",
                "type": "BUY",
                "volume": 0.10,
                "open_price": 2917.28,
                "current_price": 2930.18,  # Zmieniona cena
                "sl": 2900.0,  # Nowy stop loss
                "tp": 2950.0,  # Nowy take profit
                "profit": 125.48,  # Zmieniony profit
                "open_time": "2025.03.07 09:03"
            },
            {
                "ea_id": "EA_1741521231",
                "ticket": 89216820,  # Nowa pozycja
                "symbol": "EURUSD.pro",
                "type": "SELL",
                "volume": 0.20,
                "open_price": 1.0834,
                "current_price": 1.0825,
                "sl": 1.0850,
                "tp": 1.0800,
                "profit": 18.0,
                "open_time": "2025.03.08 10:15"
            }
        ]
        
        # Konfiguracja mocków
        existing_position = Position(
            ea_id="EA_1741521231",
            ticket=89216817,
            symbol="GOLD.pro",
            type="BUY",
            volume=0.10,
            open_price=2917.28,
            current_price=2910.18,  # Stara cena
            sl=0.0,  # Brak SL
            tp=0.0,  # Brak TP
            profit=-274.52,  # Stary profit
            open_time=datetime.strptime("2025.03.07 09:03", "%Y.%m.%d %H:%M"),
            status=PositionStatus.OPEN
        )
        
        self.position_manager._positions = {89216817: existing_position}
        self.api_client_mock.get_active_positions.return_value = mt5_positions
        
        # Wykonanie testu
        self.position_manager.sync_positions_with_mt5("EA_1741521231")
        
        # Asercje
        self.assertEqual(len(self.position_manager._positions), 2)
        
        # Sprawdzenie aktualizacji istniejącej pozycji
        updated_position = self.position_manager._positions[89216817]
        self.assertEqual(updated_position.current_price, 2930.18)
        self.assertEqual(updated_position.sl, 2900.0)
        self.assertEqual(updated_position.tp, 2950.0)
        self.assertEqual(updated_position.profit, 125.48)
        
        # Sprawdzenie dodania nowej pozycji
        new_position = self.position_manager._positions[89216820]
        self.assertEqual(new_position.symbol, "EURUSD.pro")
        self.assertEqual(new_position.type, "SELL")
        self.assertEqual(new_position.volume, 0.20)
        
        # Sprawdzenie wywołań bazy danych
        self.assertEqual(self.db_mock.update_position.call_count, 1)
        self.assertEqual(self.db_mock.save_position.call_count, 1)

if __name__ == '__main__':
    unittest.main() 