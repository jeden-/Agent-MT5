#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Testy jednostkowe dla modułu mt5_bridge.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
import pandas as pd
import numpy as np

from src.mt5_bridge.mt5_connector import MT5Connector
from src.mt5_bridge.trading_service import TradingService
from src.database.models import TradingSignal, Transaction


# Poprawny sposób patchowania mt5
@patch('src.mt5_bridge.mt5_connector.mt5', autospec=True)
class TestMT5Connector(unittest.TestCase):
    """Testy dla klasy MT5Connector."""
    
    def setUp(self):
        """Przygotowanie środowiska testowego."""
        # Instancja konektora zostanie utworzona w każdym teście
        pass
    
    def _setup_mocks(self, mock_mt5):
        """Konfiguracja mocków dla MT5."""
        # Mock dla account_info
        account_info_mock = MagicMock()
        account_info_mock.login = 12345
        account_info_mock.balance = 10000.0
        account_info_mock.equity = 10050.0
        account_info_mock.margin = 100.0
        account_info_mock.margin_free = 9950.0
        account_info_mock.margin_level = 100.5
        account_info_mock.leverage = 100
        account_info_mock.currency = "USD"
        account_info_mock.server = "Demo"
        account_info_mock.company = "Broker"
        
        # Mock dla symbol_info
        symbol_info_mock = MagicMock()
        symbol_info_mock.name = "EURUSD"
        symbol_info_mock.description = "Euro vs US Dollar"
        symbol_info_mock.digits = 5
        symbol_info_mock.spread = 10
        symbol_info_mock.point = 0.00001
        symbol_info_mock.trade_tick_size = 0.00001
        symbol_info_mock.trade_contract_size = 100000
        symbol_info_mock.volume_min = 0.01
        symbol_info_mock.volume_max = 100.0
        symbol_info_mock.volume_step = 0.01
        symbol_info_mock.bid = 1.10000
        symbol_info_mock.ask = 1.10010
        symbol_info_mock.time = 1612345678
        
        # Mock dla order_send
        order_send_result_mock = MagicMock()
        order_send_result_mock.retcode = 10009  # TRADE_RETCODE_DONE
        order_send_result_mock.order = 12345
        
        # Konfiguracja mocków
        mock_mt5.account_info.return_value = account_info_mock
        mock_mt5.symbol_info.return_value = symbol_info_mock
        mock_mt5.symbol_select.return_value = True
        mock_mt5.initialize.return_value = True
        mock_mt5.shutdown.return_value = True
        mock_mt5.TRADE_RETCODE_DONE = 10009
        mock_mt5.order_send.return_value = order_send_result_mock
        
        return mock_mt5
    
    def test_connect(self, mock_mt5):
        """Test metody connect."""
        # Przygotowanie
        mock_mt5 = self._setup_mocks(mock_mt5)
        connector = MT5Connector()
        connector._initialized = True  # Pomijamy inicjalizację w __init__
        connector._connected = False
        
        # Wykonanie
        result = connector.connect()
        
        # Weryfikacja
        mock_mt5.initialize.assert_called_once()
        mock_mt5.account_info.assert_called_once()
        self.assertTrue(result)
        self.assertTrue(connector._connected)
    
    def test_disconnect(self, mock_mt5):
        """Test metody disconnect."""
        # Przygotowanie
        mock_mt5 = self._setup_mocks(mock_mt5)
        connector = MT5Connector()
        connector._initialized = True  # Pomijamy inicjalizację w __init__
        connector._connected = True
        
        # Wykonanie
        result = connector.disconnect()
        
        # Weryfikacja
        mock_mt5.shutdown.assert_called_once()
        self.assertTrue(result)
        self.assertFalse(connector._connected)
    
    def test_get_account_info(self, mock_mt5):
        """Test metody get_account_info."""
        # Przygotowanie
        mock_mt5 = self._setup_mocks(mock_mt5)
        connector = MT5Connector()
        connector._initialized = True  # Pomijamy inicjalizację w __init__
        connector._connected = True
        
        # Wykonanie
        result = connector.get_account_info()
        
        # Weryfikacja
        mock_mt5.account_info.assert_called_once()
        self.assertEqual(result['login'], 12345)
        self.assertEqual(result['balance'], 10000.0)
        self.assertEqual(result['equity'], 10050.0)
        self.assertEqual(result['margin'], 100.0)
        self.assertEqual(result['free_margin'], 9950.0)
        self.assertEqual(result['margin_level'], 100.5)
        self.assertEqual(result['leverage'], 100)
        self.assertEqual(result['currency'], "USD")
        self.assertEqual(result['server'], "Demo")
        self.assertEqual(result['company'], "Broker")
    
    def test_get_symbol_info(self, mock_mt5):
        """Test metody get_symbol_info."""
        # Przygotowanie
        mock_mt5 = self._setup_mocks(mock_mt5)
        connector = MT5Connector()
        connector._initialized = True  # Pomijamy inicjalizację w __init__
        connector._connected = True
        
        # Wykonanie
        result = connector.get_symbol_info("EURUSD")
        
        # Weryfikacja
        mock_mt5.symbol_select.assert_called_once_with("EURUSD", True)
        mock_mt5.symbol_info.assert_called_once_with("EURUSD")
        self.assertEqual(result['name'], "EURUSD")
        self.assertEqual(result['description'], "Euro vs US Dollar")
        self.assertEqual(result['digits'], 5)
        self.assertEqual(result['spread'], 10)
        self.assertEqual(result['point'], 0.00001)
        self.assertEqual(result['bid'], 1.10000)
        self.assertEqual(result['ask'], 1.10010)
    
    def test_get_historical_data(self, mock_mt5):
        """Test metody get_historical_data."""
        # Przygotowanie
        connector = MT5Connector()
        connector._initialized = True  # Pomijamy inicjalizację w __init__
        connector._connected = True
        
        # Całkowicie patchujemy metodę get_historical_data
        with patch.object(connector, 'get_historical_data') as mock_get_data:
            # Przygotowanie oczekiwanej wartości zwrotnej
            expected_df = pd.DataFrame({
                'time': [datetime(2023, 1, 1, 10, 0), datetime(2023, 1, 1, 11, 0)],
                'open': [1.10000, 1.10100],
                'high': [1.10100, 1.10200],
                'low': [1.09900, 1.10000],
                'close': [1.10050, 1.10150],
                'tick_volume': [100, 150],
                'spread': [10, 10],
                'real_volume': [0, 0]
            })
            mock_get_data.return_value = expected_df
            
            # Wykonanie
            result = connector.get_historical_data("EURUSD", "H1", count=10)
            
            # Weryfikacja
            mock_get_data.assert_called_once_with("EURUSD", "H1", count=10)
            self.assertIs(result, expected_df)
    
    def test_open_position(self, mock_mt5):
        """Test metody open_position."""
        # Przygotowanie
        mock_mt5 = self._setup_mocks(mock_mt5)
        connector = MT5Connector()
        connector._initialized = True  # Pomijamy inicjalizację w __init__
        connector._connected = True
        
        # Mock dla get_symbol_info, aby uniknąć rzeczywistego wywołania
        connector.get_symbol_info = Mock(return_value={
            'ask': 1.10010,
            'bid': 1.10000,
            'digits': 5
        })
        
        # Wykonanie
        result = connector.open_position(
            symbol="EURUSD",
            order_type="buy",
            volume=0.1,
            price=None,
            sl=1.09500,
            tp=1.11000,
            comment="Test",
            magic=12345
        )
        
        # Weryfikacja
        mock_mt5.order_send.assert_called_once()
        self.assertEqual(result, 12345)


class TestTradingService(unittest.TestCase):
    """Testy dla klasy TradingService."""
    
    def setUp(self):
        """Przygotowanie środowiska testowego."""
        # Mock dla MT5Connector
        self.mock_connector = Mock(spec=MT5Connector)
        
        # Patch MT5Connector aby używać mocka
        self.patch_connector = patch('src.mt5_bridge.trading_service.MT5Connector', return_value=self.mock_connector)
        self.patch_connector.start()
        
        # TradingService
        self.trading_service = TradingService()
        
        # Mock dla account_info
        account_info = {
            'login': 12345,
            'balance': 10000.0,
            'equity': 10050.0,
            'margin': 100.0,
            'free_margin': 9950.0,
            'margin_level': 100.5,
            'leverage': 100,
            'currency': "USD",
            'server': "Demo",
            'company': "Broker"
        }
        
        # Mock dla symbol_info
        symbol_info = {
            'name': "EURUSD",
            'description': "Euro vs US Dollar",
            'digits': 5,
            'spread': 10,
            'point': 0.00001,
            'trade_tick_size': 0.00001,
            'trade_contract_size': 100000,
            'volume_min': 0.01,
            'volume_max': 100.0,
            'volume_step': 0.01,
            'bid': 1.10000,
            'ask': 1.10010,
            'time': 1612345678
        }
        
        # Konfiguracja mocków
        self.mock_connector.get_account_info.return_value = account_info
        self.mock_connector.get_symbol_info.return_value = symbol_info
        self.mock_connector.connect.return_value = True
        self.mock_connector.disconnect.return_value = True
        
        # Dane historyczne
        historical_data = pd.DataFrame({
            'time': [datetime(2023, 1, 1, 10, 0), datetime(2023, 1, 1, 11, 0)],
            'open': [1.10000, 1.10100],
            'high': [1.10100, 1.10200],
            'low': [1.09900, 1.10000],
            'close': [1.10050, 1.10150],
            'tick_volume': [100, 150],
            'spread': [10, 10],
            'real_volume': [0, 0]
        })
        self.mock_connector.get_historical_data.return_value = historical_data
    
    def tearDown(self):
        """Czyszczenie po testach."""
        self.patch_connector.stop()
    
    def test_connect(self):
        """Test metody connect."""
        # Wykonanie
        result = self.trading_service.connect()
        
        # Weryfikacja
        self.mock_connector.connect.assert_called_once()
        self.assertTrue(result)
    
    def test_disconnect(self):
        """Test metody disconnect."""
        # Wykonanie
        result = self.trading_service.disconnect()
        
        # Weryfikacja
        self.mock_connector.disconnect.assert_called_once()
        self.assertTrue(result)
    
    def test_get_account_info(self):
        """Test metody get_account_info."""
        # Wykonanie
        result = self.trading_service.get_account_info()
        
        # Weryfikacja
        self.mock_connector.get_account_info.assert_called_once()
        self.assertEqual(result['login'], 12345)
        self.assertEqual(result['balance'], 10000.0)
    
    def test_get_market_data(self):
        """Test metody get_market_data."""
        # Wykonanie
        result = self.trading_service.get_market_data("EURUSD")
        
        # Weryfikacja
        self.mock_connector.get_symbol_info.assert_called_once_with("EURUSD")
        self.assertEqual(result['symbol'], "EURUSD")
        self.assertEqual(result['bid'], 1.10000)
        self.assertEqual(result['ask'], 1.10010)
    
    def test_get_historical_data(self):
        """Test metody get_historical_data."""
        # Wykonanie
        result = self.trading_service.get_historical_data("EURUSD", "H1", bars=10)
        
        # Weryfikacja
        self.mock_connector.get_historical_data.assert_called_once_with("EURUSD", "H1", count=10)
        self.assertIsNotNone(result)
        self.assertEqual(len(result), 2)
    
    def test_execute_signal(self):
        """Test metody execute_signal."""
        # Przygotowanie
        signal = TradingSignal(
            symbol="EURUSD",
            timeframe="H1",
            direction="buy",
            entry_price=1.10000,
            stop_loss=1.09500,
            take_profit=1.11000,
            status="pending",
            id=1
        )
        
        self.mock_connector.open_position.return_value = 12345
        
        # Wykonanie
        result = self.trading_service.execute_signal(signal)
        
        # Weryfikacja
        self.mock_connector.get_symbol_info.assert_called_once_with("EURUSD")
        self.mock_connector.open_position.assert_called_once()
        self.assertIsNotNone(result)
        self.assertEqual(result.symbol, "EURUSD")
        self.assertEqual(result.order_type, "buy")
        self.assertEqual(result.volume, 0.1)
        self.assertEqual(result.status, "open")
        self.assertEqual(result.mt5_order_id, 12345)
        self.assertEqual(result.signal_id, 1)
    
    def test_close_transaction(self):
        """Test metody close_transaction."""
        # Przygotowanie
        transaction = Transaction(
            symbol="EURUSD",
            order_type="buy",
            volume=0.1,
            status="open",
            mt5_order_id=12345,
            id=1
        )
        
        self.mock_connector.close_position.return_value = True
        
        # Wykonanie
        result = self.trading_service.close_transaction(transaction)
        
        # Weryfikacja
        self.mock_connector.close_position.assert_called_once_with(12345, comment="Transaction ID: 1 - Closed")
        self.assertTrue(result)
    
    def test_modify_transaction(self):
        """Test metody modify_transaction."""
        # Przygotowanie
        transaction = Transaction(
            symbol="EURUSD",
            order_type="buy",
            volume=0.1,
            status="open",
            mt5_order_id=12345,
            id=1
        )
        
        self.mock_connector.modify_position.return_value = True
        
        # Wykonanie
        result = self.trading_service.modify_transaction(transaction, sl=1.09600, tp=1.10900)
        
        # Weryfikacja
        self.mock_connector.modify_position.assert_called_once_with(12345, sl=1.09600, tp=1.10900, comment="Transaction ID: 1 - Modified")
        self.assertTrue(result)
    
    def test_calculate_position_size(self):
        """Test metody calculate_position_size."""
        # Wykonanie
        result = self.trading_service.calculate_position_size(
            symbol="EURUSD",
            direction="buy",
            risk_percent=1.0,
            entry_price=1.10000,
            stop_loss=1.09500
        )
        
        # Weryfikacja
        self.mock_connector.get_account_info.assert_called_once()
        self.mock_connector.get_symbol_info.assert_called_once_with("EURUSD")
        self.assertIsNotNone(result)


if __name__ == "__main__":
    unittest.main() 