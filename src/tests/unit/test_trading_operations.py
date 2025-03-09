import unittest
from unittest.mock import patch, MagicMock, call, Mock
import json
import sys
import os
import io

# Dodanie ścieżki nadrzędnej, aby zaimportować moduły
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

# Import modułu do testowania przed wywoływaniem patcha
from scripts.http_mt5_server import MT5RequestHandler

class TestTradingOperations(unittest.TestCase):
    """Testy jednostkowe dla operacji handlowych."""

    def setUp(self):
        """Przygotowanie wspólnych elementów dla wszystkich testów."""
        # Przygotowanie handler mocka
        self.handler = MagicMock()
        self.handler.send_response = MagicMock()
        self.handler.send_header = MagicMock()
        self.handler.end_headers = MagicMock()
        self.handler.wfile = MagicMock()
        self.handler.wfile.write = MagicMock()
    
    @patch('scripts.http_mt5_server.command_queue')
    @patch('scripts.http_mt5_server.commands_lock')
    def test_handle_open_position(self, mock_lock, mock_queue):
        """Test obsługi otwierania pozycji."""
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
        
        # Symulacja listy komend
        commands_list = []
        
        # Konfiguracja mocków
        mock_lock.__enter__ = MagicMock()
        mock_lock.__exit__ = MagicMock()
        mock_queue.__getitem__ = MagicMock(return_value=commands_list)
        
        # Zapisujemy oryginalną metodę __setitem__
        original_setitem = type(mock_queue).__setitem__
        
        # Definiujemy nową metodę __setitem__, która dodaje komendę do naszej listy
        def setitem_side_effect(self, key, value):
            nonlocal commands_list
            commands_list = value  # Aktualizujemy listę komend
            return original_setitem(self, key, value)
        
        # Zastępujemy metodę __setitem__ naszą implementacją
        type(mock_queue).__setitem__ = setitem_side_effect
        
        # Wywołanie testowanej metody
        MT5RequestHandler.handle_open_position(self.handler, data)
        
        # Sprawdzenie czy odpowiedź HTTP jest poprawna
        self.handler.send_response.assert_called_once_with(200)
        self.handler.send_header.assert_called_with('Content-Type', 'application/json')
        self.handler.end_headers.assert_called_once()
        
        # Sprawdzamy, czy polecenie zostało dodane do listy komend
        self.assertEqual(len(commands_list), 1)
        
        # Sprawdzamy czy polecenie ma poprawne parametry
        command = commands_list[0]
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
        # Przygotowanie danych dla testu
        data = {
            'ea_id': 'EA_TEST',
            'ticket': 12345,
            'volume': 0.1  # Opcjonalnie - częściowe zamknięcie
        }
        
        # Symulacja listy komend
        commands_list = []
        
        # Konfiguracja mocków
        mock_lock.__enter__ = MagicMock()
        mock_lock.__exit__ = MagicMock()
        mock_queue.__getitem__ = MagicMock(return_value=commands_list)
        
        # Zapisujemy oryginalną metodę __setitem__
        original_setitem = type(mock_queue).__setitem__
        
        # Definiujemy nową metodę __setitem__, która dodaje komendę do naszej listy
        def setitem_side_effect(self, key, value):
            nonlocal commands_list
            commands_list = value  # Aktualizujemy listę komend
            return original_setitem(self, key, value)
        
        # Zastępujemy metodę __setitem__ naszą implementacją
        type(mock_queue).__setitem__ = setitem_side_effect
        
        # Wywołanie testowanej metody
        MT5RequestHandler.handle_close_position(self.handler, data)
        
        # Sprawdzenie czy odpowiedź HTTP jest poprawna
        self.handler.send_response.assert_called_once_with(200)
        self.handler.send_header.assert_called_with('Content-Type', 'application/json')
        self.handler.end_headers.assert_called_once()
        
        # Sprawdzamy, czy polecenie zostało dodane do listy komend
        self.assertEqual(len(commands_list), 1)
        
        # Sprawdzamy czy polecenie ma poprawne parametry
        command = commands_list[0]
        self.assertEqual(command['action'], 'CLOSE_POSITION')
        self.assertEqual(command['ticket'], 12345)
        self.assertEqual(command['volume'], 0.1)
    
    @patch('scripts.http_mt5_server.command_queue')
    @patch('scripts.http_mt5_server.commands_lock')
    def test_handle_modify_position(self, mock_lock, mock_queue):
        """Test obsługi modyfikacji pozycji."""
        # Przygotowanie danych dla testu
        data = {
            'ea_id': 'EA_TEST',
            'ticket': 12345,
            'sl': 1.09500,
            'tp': 1.12500
        }
        
        # Symulacja listy komend
        commands_list = []
        
        # Konfiguracja mocków
        mock_lock.__enter__ = MagicMock()
        mock_lock.__exit__ = MagicMock()
        mock_queue.__getitem__ = MagicMock(return_value=commands_list)
        
        # Zapisujemy oryginalną metodę __setitem__
        original_setitem = type(mock_queue).__setitem__
        
        # Definiujemy nową metodę __setitem__, która dodaje komendę do naszej listy
        def setitem_side_effect(self, key, value):
            nonlocal commands_list
            commands_list = value  # Aktualizujemy listę komend
            return original_setitem(self, key, value)
        
        # Zastępujemy metodę __setitem__ naszą implementacją
        type(mock_queue).__setitem__ = setitem_side_effect
        
        # Wywołanie testowanej metody
        MT5RequestHandler.handle_modify_position(self.handler, data)
        
        # Sprawdzenie czy odpowiedź HTTP jest poprawna
        self.handler.send_response.assert_called_once_with(200)
        self.handler.send_header.assert_called_with('Content-Type', 'application/json')
        self.handler.end_headers.assert_called_once()
        
        # Sprawdzamy, czy polecenie zostało dodane do listy komend
        self.assertEqual(len(commands_list), 1)
        
        # Sprawdzamy czy polecenie ma poprawne parametry
        command = commands_list[0]
        self.assertEqual(command['action'], 'MODIFY_POSITION')
        self.assertEqual(command['ticket'], 12345)
        self.assertEqual(command['sl'], 1.09500)
        self.assertEqual(command['tp'], 1.12500)
    
    @patch('scripts.http_mt5_server.account_info')
    @patch('scripts.http_mt5_server.commands_lock')
    def test_handle_get_account_info(self, mock_lock, mock_account_info):
        """Test obsługi pobierania informacji o koncie."""
        # Przygotowanie danych dla testu
        query = {'ea_id': ['EA_TEST']}
        
        # Symulujemy obecność danych konta w słowniku
        account_data = {
            'account': 12345,
            'balance': 10000.0,
            'equity': 10500.0,
            'margin': 1000.0,
            'free_margin': 9500.0,
            'currency': 'USD',
            'profit': 500.0,
            'name': 'Test Account',
            'leverage': 100,
            'last_update': '2025-03-10 12:00:00'
        }
        
        # Konfiguracja mocków
        mock_lock.__enter__ = MagicMock()
        mock_lock.__exit__ = MagicMock()
        mock_account_info.__getitem__ = MagicMock(return_value=account_data)
        mock_account_info.__contains__ = MagicMock(return_value=True)
        
        # Przygotowanie wyjścia dla wfile.write
        output = io.BytesIO()
        self.handler.wfile.write = lambda x: output.write(x)
        
        # Wywołanie testowanej metody
        MT5RequestHandler.handle_get_account_info(self.handler, query)
        
        # Sprawdzenie czy odpowiedź HTTP jest poprawna
        self.handler.send_response.assert_called_once_with(200)
        self.handler.send_header.assert_called_with('Content-Type', 'application/json')
        self.handler.end_headers.assert_called_once()
        
        # Parsujemy dane JSON z output
        output_value = output.getvalue()
        response_json = json.loads(output_value.decode('utf-8'))
        
        # Sprawdzamy strukturę odpowiedzi
        self.assertEqual(response_json['status'], 'ok')
        self.assertIn('account_info', response_json)
        
        # Sprawdzamy czy dane konta są poprawne
        account_info = response_json['account_info']
        self.assertEqual(account_info['account'], 12345)
        self.assertEqual(account_info['balance'], 10000.0)
        self.assertEqual(account_info['equity'], 10500.0)
        self.assertEqual(account_info['margin'], 1000.0)
        self.assertEqual(account_info['free_margin'], 9500.0)
        self.assertEqual(account_info['currency'], 'USD')
        self.assertEqual(account_info['profit'], 500.0)
        self.assertEqual(account_info['name'], 'Test Account')
        self.assertEqual(account_info['leverage'], 100)
        self.assertEqual(account_info['last_update'], '2025-03-10 12:00:00')
    
    @patch('scripts.http_mt5_server.account_info')
    @patch('scripts.http_mt5_server.commands_lock')
    def test_handle_get_account_info_missing(self, mock_lock, mock_account_info):
        """Test obsługi pobierania informacji o koncie gdy brak danych."""
        # Przygotowanie danych dla testu
        query = {'ea_id': ['EA_MISSING']}
        
        # Konfiguracja mocków
        mock_lock.__enter__ = MagicMock()
        mock_lock.__exit__ = MagicMock()
        mock_account_info.__contains__ = MagicMock(return_value=False)
        
        # Przygotowanie wyjścia dla wfile.write
        output = io.BytesIO()
        self.handler.wfile.write = lambda x: output.write(x)
        
        # Wywołanie testowanej metody
        MT5RequestHandler.handle_get_account_info(self.handler, query)
        
        # Sprawdzenie czy odpowiedź HTTP jest poprawna
        self.handler.send_response.assert_called_once_with(200)
        self.handler.send_header.assert_called_with('Content-Type', 'application/json')
        self.handler.end_headers.assert_called_once()
        
        # Parsujemy dane JSON z output
        output_value = output.getvalue()
        response_json = json.loads(output_value.decode('utf-8'))
        
        # Sprawdzamy strukturę odpowiedzi
        self.assertEqual(response_json['status'], 'warning')
        self.assertIn('message', response_json)
        self.assertIn('account_info', response_json)
        self.assertEqual(response_json['account_info'], {})

if __name__ == '__main__':
    unittest.main() 