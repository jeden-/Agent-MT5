"""
Trading Agent MT5 - Główny pakiet
"""

import sys
import os

# Dodaj ścieżkę głównego katalogu projektu na początku sys.path
project_root = os.path.abspath(os.path.dirname(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# To pozwoli na importy zarówno z "src." jak i bez tego przedrostka 