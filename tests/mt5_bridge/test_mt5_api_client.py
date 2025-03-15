#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Test integracyjny dla MT5ApiClient.
"""

import unittest
from unittest.mock import patch, MagicMock
import json
import sys
import os
import requests

# Dodanie katalogu głównego projektu do ścieżki, aby umożliwić importy
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.mt5_bridge.mt5_api_client import MT5ApiClient

class TestMT5ApiClient(unittest.TestCase):
    """Testy dla MT5ApiClient."""

    def setUp(self):
        """Przygotowanie środowiska testowego."""
        self.client = MT5ApiClient(host='localhost', port=8000)
        
    @patch('src.mt5_bridge.mt5_api_client.requests.get')
    def test_get_account_info_success(self, mock_get):
        """Test pobierania informacji o koncie - przypadek powodzenia."""
        # Przygotowanie mocka
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "ok",
            "account_info": {
                "login": 12345678,
                "balance": 10000.0,
                "equity": 10250.0,
                "margin": 2000.0,
                "free_margin": 8250.0,
                "margin_level": 512.5,
                "leverage": 100,
                "currency": "USD"
            },
            "timestamp": "2025-03-12T03:00:00.000Z"
        }
        mock_get.return_value = mock_response
        
        # Wywołanie metody
        result = self.client.get_account_info()
        
        # Sprawdzenie wyniku
        self.assertIsNotNone(result)
        self.assertEqual(result["status"], "ok")
        self.assertIn("account_info", result)
        
        # Sprawdzenie danych konta
        account_info = result["account_info"]
        self.assertEqual(account_info["login"], 12345678)
        self.assertEqual(account_info["balance"], 10000.0)
        self.assertEqual(account_info["equity"], 10250.0)
        self.assertEqual(account_info["margin"], 2000.0)
        self.assertEqual(account_info["free_margin"], 8250.0)
        self.assertEqual(account_info["margin_level"], 512.5)
        self.assertEqual(account_info["leverage"], 100)
        self.assertEqual(account_info["currency"], "USD")
        
        # Sprawdzenie, czy metoda get została wywołana z odpowiednim URL
        mock_get.assert_called_once_with(
            'http://localhost:8000/mt5/account',
            headers={'Content-Type': 'application/json'},
            timeout=10
        )
        
    @patch('src.mt5_bridge.mt5_api_client.requests.get')
    def test_get_account_info_connection_error(self, mock_get):
        """Test pobierania informacji o koncie - przypadek błędu połączenia."""
        # Ustawienie mocka tak, aby rzucał wyjątek ConnectionError
        mock_get.side_effect = requests.exceptions.ConnectionError("Connection error")
        
        # Wywołanie metody
        result = self.client.get_account_info()
        
        # Sprawdzenie wyniku
        self.assertEqual(result, {})
        
        # Sprawdzenie, czy metoda get została wywołana z odpowiednim URL
        mock_get.assert_called_once_with(
            'http://localhost:8000/mt5/account',
            headers={'Content-Type': 'application/json'},
            timeout=10
        )
        
    @patch('src.mt5_bridge.mt5_api_client.requests.get')
    def test_get_account_info_timeout(self, mock_get):
        """Test pobierania informacji o koncie - przypadek timeout."""
        # Ustawienie mocka tak, aby rzucał wyjątek Timeout
        mock_get.side_effect = requests.exceptions.Timeout("Timeout")
        
        # Wywołanie metody
        result = self.client.get_account_info()
        
        # Sprawdzenie wyniku
        self.assertEqual(result, {})
        
        # Sprawdzenie, czy metoda get została wywołana z odpowiednim URL
        mock_get.assert_called_once_with(
            'http://localhost:8000/mt5/account',
            headers={'Content-Type': 'application/json'},
            timeout=10
        )
        
    @patch('src.mt5_bridge.mt5_api_client.requests.get')
    def test_get_account_info_http_error(self, mock_get):
        """Test pobierania informacji o koncie - przypadek błędu HTTP."""
        # Przygotowanie mocka
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("HTTP Error")
        mock_get.return_value = mock_response
        
        # Wywołanie metody
        result = self.client.get_account_info()
        
        # Sprawdzenie wyniku
        self.assertEqual(result, {})
        
        # Sprawdzenie, czy metoda get została wywołana z odpowiednim URL
        mock_get.assert_called_once_with(
            'http://localhost:8000/mt5/account',
            headers={'Content-Type': 'application/json'},
            timeout=10
        )

if __name__ == '__main__':
    unittest.main() 