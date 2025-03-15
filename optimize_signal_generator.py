#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Skrypt uruchomieniowy dla optymalizacji parametrów generatora sygnałów.

Uruchamia proces optymalizacji parametrów głównego generatora sygnałów,
przekazując wszystkie argumenty z linii poleceń.

Użycie:
    python optimize_signal_generator.py --symbol EURUSD --timeframe H1 --method walk-forward

"""

import sys
import os

# Upewniamy się, że bieżący katalog jest w ścieżce
sys.path.insert(0, os.path.abspath('.'))

# Importujemy main z modułu
from src.backtest.optimize_signal_generator import main

if __name__ == "__main__":
    # Uruchamiamy główną funkcję
    main() 