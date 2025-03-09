#!/usr/bin/env python
"""
Skrypt uruchamia testy jednostkowe dla modułu AI.
"""

import os
import sys
import unittest
import argparse
import logging
from pathlib import Path

# Konfiguracja logowania
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("ai_tests")

# Dodanie katalogu głównego projektu do ścieżki Pythona
PROJECT_ROOT = Path(__file__).parent.parent.absolute()
sys.path.insert(0, str(PROJECT_ROOT))


def run_ai_tests(verbose: bool = False, pattern: str = None) -> bool:
    """
    Uruchamia testy jednostkowe dla modułu AI.
    
    Args:
        verbose: Czy wyświetlać szczegółowe informacje
        pattern: Wzorzec nazw testów do uruchomienia
        
    Returns:
        bool: Czy wszystkie testy zakończyły się sukcesem
    """
    logger.info("Uruchamianie testów jednostkowych dla modułu AI...")
    
    # Ustawienie poziomu szczegółowości
    verbosity = 2 if verbose else 1
    
    # Utworzenie testera
    test_loader = unittest.TestLoader()
    
    # Ścieżka do katalogu z testami AI
    test_dir = os.path.join(PROJECT_ROOT, "tests", "unit", "ai_models")
    
    # Jeśli podano wzorzec, uruchom testy dopasowane do wzorca
    if pattern:
        test_pattern = f"test*{pattern}*.py"
        logger.info(f"Wyszukiwanie testów dopasowanych do wzorca: {test_pattern}")
        test_suite = test_loader.discover(test_dir, pattern=test_pattern)
    else:
        # W przeciwnym razie uruchom wszystkie testy
        test_suite = test_loader.discover(test_dir)
    
    # Uruchomienie testów
    test_runner = unittest.TextTestRunner(verbosity=verbosity)
    result = test_runner.run(test_suite)
    
    # Podsumowanie
    total_tests = result.testsRun
    failed_tests = len(result.failures) + len(result.errors)
    
    logger.info(f"Ukończono {total_tests} testów.")
    logger.info(f"  Sukcesów: {total_tests - failed_tests}")
    logger.info(f"  Niepowodzeń: {failed_tests}")
    
    # Zwraca True, jeśli wszystkie testy zakończyły się sukcesem
    return failed_tests == 0


def main():
    """
    Główna funkcja programu.
    """
    parser = argparse.ArgumentParser(description="Uruchamia testy jednostkowe dla modułu AI")
    parser.add_argument("--verbose", "-v", action="store_true", help="Wyświetla szczegółowe informacje o testach")
    parser.add_argument("--pattern", "-p", type=str, help="Wzorzec nazw testów do uruchomienia (np. 'deepseek' dla testów związanych z DeepSeek)")
    
    args = parser.parse_args()
    
    # Uruchomienie testów
    success = run_ai_tests(verbose=args.verbose, pattern=args.pattern)
    
    # Zwrócenie kodu wyjścia: 0 dla sukcesu, 1 dla niepowodzenia
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main()) 