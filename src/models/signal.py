#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Definicje modeli związanych z sygnałami handlowymi.
"""

from enum import Enum, auto

class SignalType(Enum):
    """Typy sygnałów handlowych."""
    BUY = auto()      # Sygnał kupna
    SELL = auto()     # Sygnał sprzedaży
    CLOSE = auto()    # Sygnał zamknięcia pozycji
    NO_ACTION = auto() # Brak akcji 