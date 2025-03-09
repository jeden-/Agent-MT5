import unittest
from unittest.mock import patch, MagicMock
import json
import sys
import os

# Dodanie ścieżki nadrzędnej, aby zaimportować moduły
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

class TestTradingOperations(unittest.TestCase):
    """Testy jednostkowe dla operacji handlowych."""

    @patch('scripts.http_mt5_server.command_queue')
    @patch('scripts.http_mt5_server.commands_lock')
    def test_handle_open_position(self, mock_lock, mock_queue):
        """Test obsługi otwierania pozycji."""
        from scripts.http_mt5_server import MT5RequestHandler
        
        # Przygotowanie mocków
        mock_lock.__enter__ = MagicMock()
        mock_lock.__exit__ = MagicMock()
        
        # Przygotowanie mock dla słownika command_queue
        commands = []
        mock_queue.__getitem__ = MagicMock(return_value=commands)
        
        # Przygotowanie mock dla __setitem__, który zapisuje dane w mocku
        def side_effect(key, value):
            self.assertEqual(key, 'EA_TEST')
            self.assertEqual(len(value), 1)
            commands.append(value[0])
        
        mock_queue.__setitem__ = MagicMock(side_effect=side_effect)
        
        handler = MagicMock()
        handler.send_response = MagicMock()
        handler.send_header = MagicMock()
        handler.end_headers = MagicMock()
        handler.wfile = MagicMock()
        handler.wfile.write = MagicMock()
        
        # Przygotowanie danych dla testu
        data = {
            'ea_id': 'EA_TEST',
            'symbol': 'EURUSD',
            'order_type': 'BUY',
            'volume': 0.1,
            'price': 1.10000,
            'sl': 1.09000,
            'tp': 1.12000,
            'comment': 'Test order'
        }
        
        # Wywołanie testowanej metody
        MT5RequestHandler.handle_open_position(handler, data)
        
        # Sprawdzenie czy odpowiedź jest poprawna
        handler.send_response.assert_called_once_with(200)
        handler.send_header.assert_called_with('Content-Type', 'application/json')
        handler.end_headers.assert_called_once()
        
        # Sprawdzenie czy polecenie zostało dodane do kolejki
        mock_queue.__setitem__.assert_called_once()
        
        # Sprawdzenie czy polecenie ma poprawną strukturę
        self.assertEqual(len(commands), 1)
        command = commands[0]
        self.assertEqual(command['action'], 'OPEN_POSITION')
        self.assertEqual(command['symbol'], 'EURUSD')
        self.assertEqual(command['type'], 'BUY')
        self.assertEqual(command['volume'], 0.1)
        self.assertEqual(command['price'], 1.10000)
        self.assertEqual(command['sl'], 1.09000)
        self.assertEqual(command['tp'], 1.12000)
        self.assertEqual(command['comment'], 'Test order')
    
    @patch('scripts.http_mt5_server.command_queue')
    @patch('scripts.http_mt5_server.commands_lock')
    def test_handle_close_position(self, mock_lock, mock_queue):
        """Test obsługi zamykania pozycji."""
        from scripts.http_mt5_server import MT5RequestHandler
        
        # Przygotowanie mocków
        mock_lock.__enter__ = MagicMock()
        mock_lock.__exit__ = MagicMock()
        
        # Przygotowanie mock dla słownika command_queue
        commands = []
        mock_queue.__getitem__ = MagicMock(return_value=commands)
        
        # Przygotowanie mock dla __setitem__, który zapisuje dane w mocku
        def side_effect(key, value):
            self.assertEqual(key, 'EA_TEST')
            self.assertEqual(len(value), 1)
            commands.append(value[0])
        
        mock_queue.__setitem__ = MagicMock(side_effect=side_effect)
        
        handler = MagicMock()
        handler.send_response = MagicMock()
        handler.send_header = MagicMock()
        handler.end_headers = MagicMock()
        handler.wfile = MagicMock()
        handler.wfile.write = MagicMock()
        
        # Przygotowanie danych dla testu
        data = {
            'ea_id': 'EA_TEST',
            'ticket': 12345,
            'volume': 0.1  # Opcjonalnie - częściowe zamknięcie
        }
        
        # Wywołanie testowanej metody
        MT5RequestHandler.handle_close_position(handler, data)
        
        # Sprawdzenie czy odpowiedź jest poprawna
        handler.send_response.assert_called_once_with(200)
        handler.send_header.assert_called_with('Content-Type', 'application/json')
        handler.end_headers.assert_called_once()
        
        # Sprawdzenie czy polecenie zostało dodane do kolejki
        mock_queue.__setitem__.assert_called_once()
        
        # Sprawdzenie czy polecenie ma poprawną strukturę
        self.assertEqual(len(commands), 1)
        command = commands[0]
        self.assertEqual(command['action'], 'CLOSE_POSITION')
        self.assertEqual(command['ticket'], 12345)
        self.assertEqual(command['volume'], 0.1)
    
    @patch('scripts.http_mt5_server.command_queue')
    @patch('scripts.http_mt5_server.commands_lock')
    def test_handle_modify_position(self, mock_lock, mock_queue):
        """Test obsługi modyfikacji pozycji."""
        from scripts.http_mt5_server import MT5RequestHandler
        
        # Przygotowanie mocków
        mock_lock.__enter__ = MagicMock()
        mock_lock.__exit__ = MagicMock()
        
        # Przygotowanie mock dla słownika command_queue
        commands = []
        mock_queue.__getitem__ = MagicMock(return_value=commands)
        
        # Przygotowanie mock dla __setitem__, który zapisuje dane w mocku
        def side_effect(key, value):
            self.assertEqual(key, 'EA_TEST')
            self.assertEqual(len(value), 1)
            commands.append(value[0])
        
        mock_queue.__setitem__ = MagicMock(side_effect=side_effect)
        
        handler = MagicMock()
        handler.send_response = MagicMock()
        handler.send_header = MagicMock()
        handler.end_headers = MagicMock()
        handler.wfile = MagicMock()
        handler.wfile.write = MagicMock()
        
        # Przygotowanie danych dla testu
        data = {
            'ea_id': 'EA_TEST',
            'ticket': 12345,
            'sl': 1.09500,
            'tp': 1.12500
        }
        
        # Wywołanie testowanej metody
        MT5RequestHandler.handle_modify_position(handler, data)
        
        # Sprawdzenie czy odpowiedź jest poprawna
        handler.send_response.assert_called_once_with(200)
        handler.send_header.assert_called_with('Content-Type', 'application/json')
        handler.end_headers.assert_called_once()
        
        # Sprawdzenie czy polecenie zostało dodane do kolejki
        mock_queue.__setitem__.assert_called_once()
        
        # Sprawdzenie czy polecenie ma poprawną strukturę
        self.assertEqual(len(commands), 1)
        command = commands[0]
        self.assertEqual(command['action'], 'MODIFY_POSITION')
        self.assertEqual(command['ticket'], 12345)
        self.assertEqual(command['sl'], 1.09500)
        self.assertEqual(command['tp'], 1.12500)

if __name__ == '__main__':
    unittest.main() 