#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Skrypt do uruchamiania testów dla Trading Agent MT5.
"""

import sys
import os
import unittest
import importlib

# Dodaj katalog główny projektu do sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

# Załaduj conftest.py, który naprawi importy
import conftest

def run_test(test_path):
    """
    Uruchamia wskazany test lub wszystkie testy.
    
    Args:
        test_path: Ścieżka do modułu testowego (np. src.tests.unit.analysis.test_feedback_loop)
                  lub "all" dla uruchomienia wszystkich testów
    """
    if test_path == "all":
        # Uruchom wszystkie testy
        test_loader = unittest.TestLoader()
        tests = test_loader.discover("src/tests")
        test_runner = unittest.TextTestRunner(verbosity=2)
        test_runner.run(tests)
    else:
        # Uruchom wskazany test
        try:
            # Zaimportuj moduł testowy
            test_module = importlib.import_module(test_path)
            
            # Uruchom testy bezpośrednio z modułu
            suite = unittest.defaultTestLoader.loadTestsFromModule(test_module)
            test_runner = unittest.TextTestRunner(verbosity=2)
            test_runner.run(suite)
        except ImportError as e:
            print(f"Nie można zaimportować modułu {test_path}: {e}")
            sys.exit(1)

if __name__ == "__main__":
    # Sprawdź, czy podano ścieżkę do testu
    if len(sys.argv) > 1:
        test_path = sys.argv[1]
    else:
        test_path = "all"
    
    run_test(test_path) 