#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Skrypt do generowania raportu z testów dla endpointu /mt5/account.
"""

import os
import sys
import unittest
import logging
import json
from datetime import datetime

# Dodanie katalogu głównego projektu do ścieżki, aby umożliwić importy
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import klasy TestReporter
from src.utils.test_reporter import TestReporter

# Konfiguracja logowania
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f"logs/test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

class TestResult:
    """Klasa reprezentująca wynik testu."""
    
    def __init__(self, name, passed, error=None):
        self.name = name
        self.passed = passed
        self.error = error

def run_tests_and_generate_report():
    """Uruchamia testy i generuje raport."""
    logger.info("Rozpoczynam testy i generowanie raportu")
    
    # Utworzenie katalogów, jeśli nie istnieją
    os.makedirs('logs', exist_ok=True)
    os.makedirs('reports', exist_ok=True)
    
    # Znalezienie i uruchomienie testów
    test_loader = unittest.TestLoader()
    
    # Testy jednostkowe
    endpoint_tests = test_loader.discover('tests/mt5_bridge', pattern='test_mt5_account_endpoint.py')
    
    # Testy integracyjne
    api_client_tests = test_loader.discover('tests/mt5_bridge', pattern='test_mt5_api_client.py')
    
    # Połączenie testów
    all_tests = unittest.TestSuite([endpoint_tests, api_client_tests])
    
    # Uruchomienie testów z własnym collectoremm wyników
    results = []
    
    class CustomTestResult(unittest.TestResult):
        def addSuccess(self, test):
            super().addSuccess(test)
            results.append(TestResult(test.id(), True))
            
        def addError(self, test, err):
            super().addError(test, err)
            results.append(TestResult(test.id(), False, str(err[1])))
            
        def addFailure(self, test, err):
            super().addFailure(test, err)
            results.append(TestResult(test.id(), False, str(err[1])))
    
    test_result = CustomTestResult()
    all_tests.run(test_result)
    
    # Generowanie raportu
    reporter = TestReporter()
    report = reporter.generate_test_report(results)
    
    # Zapisanie raportu do pliku
    report_file = f"reports/mt5_account_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, default=str)
    
    logger.info(f"Raport zapisany do pliku: {report_file}")
    
    # Wyświetlenie podsumowania
    logger.info(f"Testy zakończone. Wyniki: {report['total_tests']} testów, {report['passed']} zaliczonych, {report['failed']} niezaliczonych")
    
    # Zwrócenie kodu wyjścia
    return 0 if report['failed'] == 0 else 1

if __name__ == '__main__':
    sys.exit(run_tests_and_generate_report()) 