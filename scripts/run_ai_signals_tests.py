#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Skrypt do uruchomienia testów dla endpointu /ai/signals/latest.
"""

import os
import sys
import unittest
import logging
from datetime import datetime

# Dodanie katalogu głównego projektu do ścieżki, aby umożliwić importy
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Konfiguracja logowania
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f"logs/ai_signals_tests_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

def run_tests():
    """Uruchamia testy dla endpointu /ai/signals/latest."""
    logger.info("Rozpoczynam testy dla endpointu /ai/signals/latest")
    
    # Utworzenie katalogu na logi, jeśli nie istnieje
    os.makedirs('logs', exist_ok=True)
    
    # Znalezienie i uruchomienie testów
    test_loader = unittest.TestLoader()
    
    # Testy jednostkowe
    endpoint_tests = test_loader.discover('tests/mt5_bridge', pattern='test_ai_signals_endpoint.py')
    
    # Uruchomienie testów
    test_runner = unittest.TextTestRunner(verbosity=2)
    result = test_runner.run(endpoint_tests)
    
    # Podsumowanie wyników
    logger.info(f"Testy zakończone. Wyniki: {result.testsRun} testów, {len(result.errors)} błędów, {len(result.failures)} niepowodzeń")
    
    # Zwrócenie kodu wyjścia
    return 0 if result.wasSuccessful() else 1

if __name__ == '__main__':
    sys.exit(run_tests()) 