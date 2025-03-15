#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Moduł zawierający funkcje pomocnicze do operacji na ścieżkach.
"""

import os
import sys
from pathlib import Path

def get_project_root() -> str:
    """
    Zwraca ścieżkę do katalogu głównego projektu.
    
    Returns:
        str: Ścieżka do katalogu głównego projektu
    """
    # Jeśli uruchamiamy z pakietu, znajdź katalog główny projektu
    if __package__:
        # Ścieżka do katalogu, w którym znajduje się ten plik
        current_dir = os.path.dirname(os.path.abspath(__file__))
        # Ścieżka do katalogu głównego projektu (dwa poziomy wyżej)
        return os.path.abspath(os.path.join(current_dir, '..', '..'))
    
    # Jeśli uruchamiamy bezpośrednio ten plik
    return os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')) 