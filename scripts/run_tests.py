#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Skrypt do uruchamiania testów jednostkowych i integracyjnych.
"""

import os
import sys
import argparse
import unittest
import logging
from datetime import datetime

# Dodanie głównego katalogu projektu do PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

def setup_logging():
    """Konfiguracja logowania."""
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    date_format = '%Y-%m-%d %H:%M:%S'
    
    # Upewnienie się, że katalog logów istnieje
    if not os.path.exists('logs'):
        os.makedirs('logs')
    
    # Plik logów
    log_file = f'logs/tests_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
    
    logging.basicConfig(
        level=logging.INFO,
        format=log_format,
        datefmt=date_format,
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    return logging.getLogger('tests')

def discover_tests(test_type='all'):
    """
    Odkrywanie testów do uruchomienia.
    
    Args:
        test_type (str): Typ testów do uruchomienia ('all', 'unit', 'integration').
    
    Returns:
        unittest.TestSuite: Zestaw testów do uruchomienia.
    """
    test_loader = unittest.TestLoader()
    test_suite = unittest.TestSuite()
    
    # Ścieżka do testów
    tests_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'src', 'tests')
    
    if test_type in ['all', 'unit']:
        unit_tests_dir = os.path.join(tests_dir, 'unit')
        if os.path.exists(unit_tests_dir):
            unit_tests = test_loader.discover(unit_tests_dir, pattern='test_*.py')
            test_suite.addTests(unit_tests)
    
    if test_type in ['all', 'integration']:
        integration_tests_dir = os.path.join(tests_dir, 'integration')
        if os.path.exists(integration_tests_dir):
            integration_tests = test_loader.discover(integration_tests_dir, pattern='test_*.py')
            test_suite.addTests(integration_tests)
    
    return test_suite

def run_tests(test_type='all'):
    """
    Uruchamianie testów.
    
    Args:
        test_type (str): Typ testów do uruchomienia ('all', 'unit', 'integration').
    
    Returns:
        bool: True jeśli wszystkie testy przeszły pomyślnie, False w przeciwnym razie.
    """
    logger = setup_logging()
    logger.info(f"Uruchamianie testów typu: {test_type}")
    
    test_suite = discover_tests(test_type)
    
    logger.info(f"Znaleziono {test_suite.countTestCases()} testów")
    
    # Uruchomienie testów
    test_runner = unittest.TextTestRunner(verbosity=2)
    test_result = test_runner.run(test_suite)
    
    # Logowanie wyników
    logger.info(f"Wykonano {test_result.testsRun} testów")
    logger.info(f"Testy zaliczone: {test_result.testsRun - len(test_result.errors) - len(test_result.failures)}")
    logger.info(f"Testy oblane: {len(test_result.failures)}")
    logger.info(f"Błędy: {len(test_result.errors)}")
    
    if test_result.errors:
        logger.error("Błędy podczas wykonywania testów:")
        for test, error in test_result.errors:
            logger.error(f"{test}: {error}")
    
    if test_result.failures:
        logger.error("Niepowodzenia testów:")
        for test, failure in test_result.failures:
            logger.error(f"{test}: {failure}")
    
    # Powrót True jeśli wszystkie testy przeszły pomyślnie
    return len(test_result.errors) == 0 and len(test_result.failures) == 0

def main():
    """Główna funkcja skryptu."""
    parser = argparse.ArgumentParser(description='Uruchamianie testów dla Trading Agent MT5')
    parser.add_argument('--type', choices=['all', 'unit', 'integration'], default='all',
                        help='Typ testów do uruchomienia (domyślnie: all)')
    args = parser.parse_args()
    
    success = run_tests(args.type)
    
    # Kod wyjścia 0 jeśli testy przeszły pomyślnie, 1 w przeciwnym razie
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main() 