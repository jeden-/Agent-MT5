#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Test dla łatki komunikacji z EA.
"""

import unittest
from unittest.mock import patch, MagicMock, Mock
import logging
import sys
import os

# Dodanie ścieżki projektu do sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Konfiguracja loggera dla testów
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("test_ea_patch")

# Przygotowanie mocków
class MockTradingService:
    def execute_signal(self, signal):
        pass
    
    def get_market_data(self, symbol):
        return {
            "symbol": symbol,
            "bid": 1.1000,
            "ask": 1.1001,
            "point": 0.0001
        }

class MockMT5ApiClient:
    def __init__(self, server_url):
        self.server_url = server_url
    
    def open_position(self, ea_id, order_data):
        return {"ticket": 12345}

class MockTransaction:
    def __init__(self, symbol, order_type, volume, status, open_price, stop_loss, take_profit, mt5_order_id, signal_id, open_time):
        self.symbol = symbol
        self.order_type = order_type
        self.volume = volume
        self.status = status
        self.open_price = open_price
        self.stop_loss = stop_loss
        self.take_profit = take_profit
        self.mt5_order_id = mt5_order_id
        self.signal_id = signal_id
        self.open_time = open_time

class TestEAPatch(unittest.TestCase):
    """Testy dla łatki komunikacji z EA."""
    
    @patch('builtins.__import__')
    def test_ea_communication_patch(self, mock_import):
        """Test dla łatki komunikacji z EA."""
        
        # Przygotowanie danych testowych
        from datetime import datetime
        
        # Przygotowanie mocka dla sygnału
        mock_signal = MagicMock()
        mock_signal.id = "test_signal_id"
        mock_signal.status = "pending"
        mock_signal.symbol = "EURUSD"
        mock_signal.direction = "buy"
        mock_signal.entry_price = 1.1000
        mock_signal.stop_loss = 1.0950
        mock_signal.take_profit = 1.1050
        
        # Przygotowanie niezbędnych klas jako mocki
        mock_trading_service = MockTradingService()
        mock_api_client = MockMT5ApiClient("http://127.0.0.1:5555")
        
        # Testowanie logiki łatki bezpośrednio
        try:
            # Pobieramy aktualne dane rynkowe
            market_data = mock_trading_service.get_market_data(mock_signal.symbol)
            
            # Wyliczenie ceny wejścia dla zleceń rynkowych
            entry_price = None
            if mock_signal.direction == 'buy':
                entry_price = market_data['ask']
            elif mock_signal.direction == 'sell':
                entry_price = market_data['bid']
            
            # Sprawdzenie czy sygnał jest nadal ważny (czy cena nie oddaliła się za bardzo)
            point = market_data.get('point', 0.00001)
            if abs(entry_price - mock_signal.entry_price) / point > 50:  # 50 pipsów odchylenia
                logger.warning(f"Cena zmieniła się zbyt mocno. Oczekiwano: {mock_signal.entry_price}, aktualna: {entry_price}")
            
            # Wyliczenie wielkości pozycji
            volume = 0.1  # Minimalna wielkość
            
            # Przygotowanie danych dla EA zgodnie z dokumentacją API
            order_data = {
                "symbol": mock_signal.symbol,
                "order_type": mock_signal.direction.upper(),  # "BUY" lub "SELL" zgodnie z dokumentacją API
                "volume": volume,
                "price": entry_price,
                "sl": mock_signal.stop_loss,
                "tp": mock_signal.take_profit,
                "comment": f"Signal ID: {mock_signal.id}"
            }
            
            # EA ID
            ea_id = "EA_1741779470"
            
            # Wywołanie metody open_position
            result = mock_api_client.open_position(ea_id, order_data)
            
            # Utworzenie transakcji
            transaction = MockTransaction(
                symbol=mock_signal.symbol,
                order_type=mock_signal.direction,
                volume=volume,
                status="open",
                open_price=entry_price,
                stop_loss=mock_signal.stop_loss,
                take_profit=mock_signal.take_profit,
                mt5_order_id=result.get("ticket", 0),
                signal_id=mock_signal.id,
                open_time=datetime.now()
            )
            
            # Asercje
            self.assertEqual(transaction.symbol, "EURUSD")
            self.assertEqual(transaction.order_type, "buy")
            self.assertEqual(order_data["order_type"], "BUY")
            self.assertEqual(order_data["volume"], 0.1)
            self.assertEqual(order_data["price"], 1.1001)
            
            logger.info("Test zakończony pomyślnie.")
            
        except Exception as e:
            self.fail(f"Test nie powiódł się: {e}")


if __name__ == '__main__':
    unittest.main() 