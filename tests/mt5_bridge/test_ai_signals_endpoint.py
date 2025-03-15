#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Test dla endpointu /ai/signals/latest.
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

class TestAISignalsLatestEndpoint(unittest.TestCase):
    """Testy dla endpointu /ai/signals/latest."""

    def setUp(self):
        """Przygotowanie środowiska testowego."""
        self.client = TestClient(app)
        
    def test_get_latest_ai_signals_success(self):
        """Test pobierania najnowszych sygnałów AI - przypadek powodzenia."""
        # Wywołanie endpointu
        response = self.client.get("/ai/signals/latest")
        
        # Sprawdzenie odpowiedzi
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "ok")
        self.assertIn("signals", data)
        
        # Sprawdzenie sygnałów
        signals = data["signals"]
        self.assertIsInstance(signals, list)
        self.assertGreaterEqual(len(signals), 1)
        
        # Sprawdzenie struktury sygnału
        if signals:
            signal = signals[0]
            self.assertIn("id", signal)
            self.assertIn("model", signal)
            self.assertIn("symbol", signal)
            self.assertIn("type", signal)
            self.assertIn("confidence", signal)
            self.assertIn("timestamp", signal)
            self.assertIn("executed", signal)
            self.assertIn("profit", signal)
    
    @patch('src.mt5_bridge.server.datetime')
    def test_get_latest_ai_signals_with_specific_symbols(self, mock_datetime):
        """Test pobierania najnowszych sygnałów AI z konkretnymi symbolami."""
        # Ustawienie mocka dla datetime
        mock_now = MagicMock()
        mock_now.isoformat.return_value = "2025-03-12T09:35:26.316Z"
        mock_datetime.now.return_value = mock_now
        
        # Wywołanie endpointu
        response = self.client.get("/ai/signals/latest")
        
        # Sprawdzenie odpowiedzi
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "ok")
        
        # Sprawdzenie, czy sygnały zawierają US100 i SILVER
        signals = data["signals"]
        symbols = [signal["symbol"] for signal in signals]
        self.assertIn("US100", symbols)
        self.assertIn("SILVER", symbols)
        
        # Sprawdzenie szczegółów sygnałów
        for signal in signals:
            if signal["symbol"] == "US100":
                self.assertEqual(signal["model"], "Claude")
                self.assertEqual(signal["type"], "BUY")
                self.assertAlmostEqual(signal["confidence"], 0.85)
                self.assertEqual(signal["timestamp"], "2025-03-12T09:35:26.316Z")
                self.assertFalse(signal["executed"])
                self.assertIsNone(signal["profit"])
            elif signal["symbol"] == "SILVER":
                self.assertEqual(signal["model"], "Grok")
                self.assertEqual(signal["type"], "SELL")
                self.assertAlmostEqual(signal["confidence"], 0.78)
                self.assertEqual(signal["timestamp"], "2025-03-12T09:35:26.316Z")
                self.assertFalse(signal["executed"])
                self.assertIsNone(signal["profit"])

if __name__ == '__main__':
    unittest.main() 