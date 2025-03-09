#!/usr/bin/env python
# -*- coding: utf-8 -*-

import unittest
import socket
import threading
import time
import queue
from unittest.mock import patch, MagicMock, call
from datetime import datetime, timedelta

from src.mt5_bridge.mt5_server import MT5Server

class TestMT5Server(unittest.TestCase):
    """Testy jednostkowe dla klasy MT5Server."""
    
    def setUp(self):
        """Przygotowanie przed każdym testem."""
        # Używamy innego portu niż domyślny, aby nie kolidować z innymi testami
        self.server = MT5Server(host='127.0.0.1', port=6789)
        
        # Mockujemy socket serwera
        self.mock_server_socket = MagicMock()
        self.server.server_socket = self.mock_server_socket
        
        # Mockujemy klienta
        self.mock_client = MagicMock()
        self.server.clients = [self.mock_client]
        
    def tearDown(self):
        """Sprzątanie po każdym teście."""
        if self.server.is_running:
            self.server.stop()
            
    @patch('socket.socket')
    def test_start(self, mock_socket):
        """Test uruchamiania serwera."""
        # Przygotowanie mocków
        mock_socket_instance = MagicMock()
        mock_socket.return_value = mock_socket_instance
        
        # Uruchamiamy serwer
        result = self.server.start()
        
        # Sprawdzamy czy serwer został uruchomiony
        self.assertTrue(result)
        self.assertTrue(self.server.is_running)
        
        # Sprawdzamy czy socket został skonfigurowany prawidłowo
        mock_socket_instance.setsockopt.assert_called_once()
        mock_socket_instance.bind.assert_called_once_with(('127.0.0.1', 6789))
        mock_socket_instance.listen.assert_called_once()
        mock_socket_instance.settimeout.assert_called_once()
    
    def test_stop(self):
        """Test zatrzymywania serwera."""
        # Ustawiamy serwer jako uruchomiony
        self.server.is_running = True
        
        # Zatrzymujemy serwer
        self.server.stop()
        
        # Sprawdzamy czy serwer został zatrzymany
        self.assertFalse(self.server.is_running)
        self.mock_client.close.assert_called_once()
        self.mock_server_socket.close.assert_called_once()
        self.assertEqual(len(self.server.clients), 0)
    
    def test_is_connected_no_connection(self):
        """Test sprawdzania połączenia gdy nie ma aktywnego połączenia."""
        # Bez ustawionego last_connection_time
        self.assertFalse(self.server.is_connected())
    
    def test_is_connected_recent_connection(self):
        """Test sprawdzania połączenia gdy połączenie jest aktywne."""
        # Ustawiamy ostatnie połączenie na teraz
        self.server.last_connection_time = datetime.now()
        self.assertTrue(self.server.is_connected())
    
    def test_is_connected_old_connection(self):
        """Test sprawdzania połączenia gdy połączenie jest nieaktywne."""
        # Ustawiamy ostatnie połączenie na 15 sekund temu
        self.server.last_connection_time = datetime.now() - timedelta(seconds=15)
        self.assertFalse(self.server.is_connected())
    
    def test_send_command_server_not_running(self):
        """Test wysyłania komendy gdy serwer nie jest uruchomiony."""
        # Serwer nie jest uruchomiony
        self.server.is_running = False
        
        # Próbujemy wysłać komendę
        result = self.server.send_command("TEST", "data")
        
        # Sprawdzamy czy komenda nie została wysłana
        self.assertFalse(result)
        self.assertTrue(self.server.command_queue.empty())
    
    def test_send_command_server_running(self):
        """Test wysyłania komendy gdy serwer jest uruchomiony."""
        # Serwer jest uruchomiony
        self.server.is_running = True
        
        # Wysyłamy komendę
        result = self.server.send_command("TEST", "data")
        
        # Sprawdzamy czy komenda została dodana do kolejki
        self.assertTrue(result)
        self.assertFalse(self.server.command_queue.empty())
        command = self.server.command_queue.get()
        self.assertEqual(command, "TEST:data")
    
    def test_register_callback(self):
        """Test rejestracji callbacku."""
        # Tworzymy testowy callback
        def test_callback(data):
            pass
        
        # Rejestrujemy callback
        self.server.register_callback("TEST_TYPE", test_callback)
        
        # Sprawdzamy czy callback został zarejestrowany
        self.assertIn("TEST_TYPE", self.server.callback_handlers)
        self.assertEqual(self.server.callback_handlers["TEST_TYPE"], test_callback)
    
    def test_get_market_data_no_data(self):
        """Test pobierania danych rynkowych gdy nie ma danych."""
        # Sprawdzamy czy zwracany jest pusty słownik
        self.assertEqual(self.server.get_market_data(), {})
        self.assertEqual(self.server.get_market_data("EURUSD"), {})
    
    def test_get_market_data_with_data(self):
        """Test pobierania danych rynkowych gdy są dane."""
        # Dodajemy dane rynkowe
        test_data = {"BID": 1.1, "ASK": 1.2}
        self.server.last_market_data = {"EURUSD": test_data}
        
        # Sprawdzamy czy zwracane są poprawne dane
        self.assertEqual(self.server.get_market_data("EURUSD"), test_data)
        self.assertEqual(self.server.get_market_data(), {"EURUSD": test_data})
    
    def test_request_account_info(self):
        """Test żądania informacji o koncie."""
        # Mockujemy metodę send_command
        self.server.send_command = MagicMock(return_value=True)
        
        # Wysyłamy żądanie
        result = self.server.request_account_info()
        
        # Sprawdzamy czy żądanie zostało wysłane
        self.assertTrue(result)
        self.server.send_command.assert_called_once_with("GET_ACCOUNT_INFO")
    
    def test_request_market_data(self):
        """Test żądania danych rynkowych."""
        # Mockujemy metodę send_command
        self.server.send_command = MagicMock(return_value=True)
        
        # Wysyłamy żądanie
        result = self.server.request_market_data("EURUSD")
        
        # Sprawdzamy czy żądanie zostało wysłane
        self.assertTrue(result)
        self.server.send_command.assert_called_once_with("GET_MARKET_DATA", "SYMBOL:EURUSD")
    
    def test_open_position(self):
        """Test wysyłania komendy otwarcia pozycji."""
        # Mockujemy metodę send_command
        self.server.send_command = MagicMock(return_value=True)
        
        # Wysyłamy komendę
        result = self.server.open_position("EURUSD", "BUY", 0.1, 1.1, 1.09, 1.12)
        
        # Sprawdzamy czy komenda została wysłana
        self.assertTrue(result)
        expected_data = "SYMBOL:EURUSD;TYPE:BUY;VOLUME:0.1;PRICE:1.1;SL:1.09;TP:1.12"
        self.server.send_command.assert_called_once_with("OPEN_POSITION", expected_data)
    
    def test_close_position(self):
        """Test wysyłania komendy zamknięcia pozycji."""
        # Mockujemy metodę send_command
        self.server.send_command = MagicMock(return_value=True)
        
        # Wysyłamy komendę
        result = self.server.close_position(12345)
        
        # Sprawdzamy czy komenda została wysłana
        self.assertTrue(result)
        self.server.send_command.assert_called_once_with("CLOSE_POSITION", "TICKET:12345")
    
    def test_modify_position(self):
        """Test wysyłania komendy modyfikacji pozycji."""
        # Mockujemy metodę send_command
        self.server.send_command = MagicMock(return_value=True)
        
        # Wysyłamy komendę
        result = self.server.modify_position(12345, 1.09, 1.12)
        
        # Sprawdzamy czy komenda została wysłana
        self.assertTrue(result)
        expected_data = "TICKET:12345;SL:1.09;TP:1.12"
        self.server.send_command.assert_called_once_with("MODIFY_POSITION", expected_data)
    
    def test_ping(self):
        """Test wysyłania pinga."""
        # Mockujemy metodę send_command
        self.server.send_command = MagicMock(return_value=True)
        
        # Wysyłamy ping
        result = self.server.ping()
        
        # Sprawdzamy czy ping został wysłany
        self.assertTrue(result)
        self.server.send_command.assert_called_once_with("PING")
    
    @patch('src.mt5_bridge.mt5_server.logger')
    def test_handle_message(self, mock_logger):
        """Test obsługi wiadomości."""
        # Mockujemy metody obsługi różnych typów wiadomości
        self.server._handle_market_data = MagicMock()
        self.server._handle_positions_update = MagicMock()
        self.server._handle_account_info = MagicMock()
        
        # Testujemy obsługę różnych typów wiadomości
        test_cases = [
            ("MARKET_DATA", "data", self.server._handle_market_data),
            ("POSITIONS_UPDATE", "data", self.server._handle_positions_update),
            ("ACCOUNT_INFO", "data", self.server._handle_account_info),
            ("INIT", "data", None),
            ("DEINIT", "data", None),
            ("ERROR", "data", None),
            ("SUCCESS", "data", None),
            ("PONG", "data", None),
            ("CLOSE", "data", None),
            ("UNKNOWN", "data", None)
        ]
        
        for message_type, message_data, handler in test_cases:
            # Resetujemy mocki
            if handler:
                handler.reset_mock()
            mock_logger.reset_mock()
            
            # Wywołujemy metodę
            self.server._handle_message(message_type, message_data)
            
            # Sprawdzamy czy odpowiedni handler został wywołany
            if handler:
                handler.assert_called_once_with(message_data)
            
            # Dla nieznanych typów sprawdzamy logowanie ostrzeżenia
            if message_type == "UNKNOWN":
                mock_logger.warning.assert_called_once()
    
    def test_parse_data(self):
        """Test parsowania danych."""
        # Testujemy parsowanie danych
        test_cases = [
            # Input, Expected Output
            (
                "SYMBOL:EURUSD;BID:1.1;ASK:1.2;SPREAD:10",
                {"SYMBOL": "EURUSD", "BID": 1.1, "ASK": 1.2, "SPREAD": 10}
            ),
            (
                "TICKET:12345;SYMBOL:EURUSD;TYPE:BUY;VOLUME:0.1",
                {"TICKET": 12345, "SYMBOL": "EURUSD", "TYPE": "BUY", "VOLUME": 0.1}
            ),
            (
                "BALANCE:1000;EQUITY:1100;MARGIN:100;FREE_MARGIN:900",
                {"BALANCE": 1000, "EQUITY": 1100, "MARGIN": 100, "FREE_MARGIN": 900}
            ),
            (
                "", {}  # Pusty string powinien zwrócić pusty słownik
            ),
            (
                "INVALID_FORMAT", {}  # Nieprawidłowy format powinien zwrócić pusty słownik
            )
        ]
        
        for input_data, expected_output in test_cases:
            result = self.server._parse_data(input_data)
            self.assertEqual(result, expected_output)
    
    @patch('src.mt5_bridge.mt5_server.logger')
    def test_handle_market_data(self, mock_logger):
        """Test obsługi danych rynkowych."""
        # Testujemy poprawne dane
        data = "SYMBOL:EURUSD;BID:1.1;ASK:1.2"
        self.server._handle_market_data(data)
        
        # Sprawdzamy czy dane zostały zapisane
        self.assertIn("EURUSD", self.server.last_market_data)
        self.assertEqual(self.server.last_market_data["EURUSD"]["BID"], 1.1)
        self.assertEqual(self.server.last_market_data["EURUSD"]["ASK"], 1.2)
        
        # Testujemy niepoprawne dane
        mock_logger.reset_mock()
        self.server._handle_market_data("INVALID_DATA")
        mock_logger.warning.assert_called_once()
    
    @patch('src.mt5_bridge.mt5_server.logger')
    def test_handle_positions_update(self, mock_logger):
        """Test obsługi aktualizacji pozycji."""
        # Testujemy poprawne dane z wieloma pozycjami
        data = "TICKET:1;SYMBOL:EURUSD;TYPE:BUY;VOLUME:0.1|TICKET:2;SYMBOL:GBPUSD;TYPE:SELL;VOLUME:0.2"
        self.server._handle_positions_update(data)
        
        # Sprawdzamy czy dane zostały zapisane
        self.assertEqual(len(self.server.last_positions_data), 2)
        self.assertIn(1, self.server.last_positions_data)
        self.assertIn(2, self.server.last_positions_data)
        self.assertEqual(self.server.last_positions_data[1]["SYMBOL"], "EURUSD")
        self.assertEqual(self.server.last_positions_data[2]["SYMBOL"], "GBPUSD")
        
        # Testujemy puste dane (brak pozycji)
        self.server._handle_positions_update("")
        self.assertEqual(self.server.last_positions_data, {})
        
        # Testujemy niepoprawne dane
        self.server._handle_positions_update("INVALID_DATA")
        # Nie powinno być ostrzeżenia, ponieważ po prostu nie dodajemy pozycji
        self.assertEqual(self.server.last_positions_data, {})
    
    @patch('src.mt5_bridge.mt5_server.logger')
    def test_handle_account_info(self, mock_logger):
        """Test obsługi informacji o koncie."""
        # Testujemy poprawne dane
        data = "BALANCE:1000;EQUITY:1100;MARGIN:100;FREE_MARGIN:900"
        self.server._handle_account_info(data)
        
        # Sprawdzamy czy dane zostały zapisane
        self.assertEqual(self.server.last_account_info["BALANCE"], 1000)
        self.assertEqual(self.server.last_account_info["EQUITY"], 1100)
        self.assertEqual(self.server.last_account_info["MARGIN"], 100)
        self.assertEqual(self.server.last_account_info["FREE_MARGIN"], 900)
        
        # Testujemy niepoprawne dane
        mock_logger.reset_mock()
        self.server._handle_account_info("INVALID_DATA")
        mock_logger.warning.assert_called_once()


if __name__ == '__main__':
    unittest.main() 