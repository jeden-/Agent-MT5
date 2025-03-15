#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Test dla endpointu /mt5/account.
"""

import unittest
from unittest.mock import patch, MagicMock
import json
from datetime import datetime
import sys
import os

# Dodanie katalogu głównego projektu do ścieżki, aby umożliwić importy
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.mt5_bridge.server import app
from fastapi.testclient import TestClient

class TestMT5AccountEndpoint(unittest.TestCase):
    """Testy dla endpointu /mt5/account."""

    def setUp(self):
        """Przygotowanie środowiska testowego."""
        self.client = TestClient(app)
        
    @patch('src.mt5_bridge.server.mt5_server_instance')
    def test_get_account_info_success(self, mock_mt5_server_instance):
        """Test pobierania informacji o koncie - przypadek powodzenia."""
        # Przygotowanie mocka
        mock_real_mt5_server = MagicMock()
        mock_mt5_server_instance.real_mt5_server = mock_real_mt5_server
        
        # Ustawienie wartości zwracanej przez mock
        mock_real_mt5_server.get_account_info.return_value = {
            "login": 12345678,
            "balance": 10000.0,
            "equity": 10250.0,
            "margin": 2000.0,
            "free_margin": 8250.0,
            "margin_level": 512.5,
            "leverage": 100,
            "currency": "USD"
        }
        
        # Wywołanie endpointu
        response = self.client.get("/mt5/account")
        
        # Sprawdzenie odpowiedzi
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "ok")
        self.assertIn("account_info", data)
        self.assertIn("timestamp", data)
        
        # Sprawdzenie danych konta
        account_info = data["account_info"]
        self.assertEqual(account_info["login"], 12345678)
        self.assertEqual(account_info["balance"], 10000.0)
        self.assertEqual(account_info["equity"], 10250.0)
        self.assertEqual(account_info["margin"], 2000.0)
        self.assertEqual(account_info["free_margin"], 8250.0)
        self.assertEqual(account_info["margin_level"], 512.5)
        self.assertEqual(account_info["leverage"], 100)
        self.assertEqual(account_info["currency"], "USD")
        
        # Sprawdzenie, czy metoda get_account_info została wywołana
        mock_real_mt5_server.get_account_info.assert_called_once()
        
    @patch('src.mt5_bridge.server.mt5_server_instance')
    def test_get_account_info_mt5_not_available(self, mock_mt5_server_instance):
        """Test pobierania informacji o koncie - przypadek gdy MT5 nie jest dostępny."""
        # Ustawienie mocka tak, aby MT5 nie był dostępny
        mock_mt5_server_instance.real_mt5_server = None
        
        # Wywołanie endpointu
        response = self.client.get("/mt5/account")
        
        # Sprawdzenie odpowiedzi
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "ok")
        self.assertIn("account_info", data)
        self.assertIn("timestamp", data)
        
        # Sprawdzenie, czy zwrócono przykładowe dane
        account_info = data["account_info"]
        self.assertEqual(account_info["login"], 12345678)
        self.assertEqual(account_info["balance"], 10000)
        self.assertEqual(account_info["equity"], 10250)
        self.assertEqual(account_info["margin"], 2000)
        self.assertEqual(account_info["free_margin"], 8250)
        self.assertEqual(account_info["margin_level"], 512.5)
        self.assertEqual(account_info["leverage"], 100)
        self.assertEqual(account_info["currency"], "USD")
        
    @patch('src.mt5_bridge.server.mt5_server_instance')
    def test_get_account_info_exception(self, mock_mt5_server_instance):
        """Test pobierania informacji o koncie - przypadek gdy wystąpi wyjątek."""
        # Przygotowanie mocka
        mock_real_mt5_server = MagicMock()
        mock_mt5_server_instance.real_mt5_server = mock_real_mt5_server
        
        # Ustawienie mocka tak, aby rzucał wyjątek
        mock_real_mt5_server.get_account_info.side_effect = Exception("Test exception")
        
        # Wywołanie endpointu
        response = self.client.get("/mt5/account")
        
        # Sprawdzenie odpowiedzi
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "ok")
        self.assertIn("account_info", data)
        self.assertIn("timestamp", data)
        
        # Sprawdzenie, czy zwrócono przykładowe dane
        account_info = data["account_info"]
        self.assertEqual(account_info["login"], 12345678)
        self.assertEqual(account_info["balance"], 10000)
        self.assertEqual(account_info["equity"], 10250)
        self.assertEqual(account_info["margin"], 2000)
        self.assertEqual(account_info["free_margin"], 8250)
        self.assertEqual(account_info["margin_level"], 512.5)
        self.assertEqual(account_info["leverage"], 100)
        self.assertEqual(account_info["currency"], "USD")
        
        # Sprawdzenie, czy metoda get_account_info została wywołana
        mock_real_mt5_server.get_account_info.assert_called_once()

if __name__ == '__main__':
    unittest.main() 