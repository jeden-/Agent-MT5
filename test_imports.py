"""
Skrypt testujący importy w projekcie Trading Agent MT5.
"""

# Dodaj katalog główny projektu do sys.path
import sys
import os
import importlib

project_root = os.path.abspath(os.path.dirname(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Sprawdź, czy możemy zaimportować moduły z src
modules_to_test = [
    'src.analysis',
    'src.mt5_bridge.mt5_client',
    'src.database.market_data_repository'
]

print("Testowanie importów:")
print("-" * 40)

all_successful = True

for module_name in modules_to_test:
    try:
        module = importlib.import_module(module_name)
        print(f"✓ Sukces: {module_name}")
    except Exception as e:
        all_successful = False
        print(f"✗ Błąd: {module_name}")
        print(f"  {type(e).__name__}: {str(e)}")

print("-" * 40)
if all_successful:
    print("Wszystkie importy działają poprawnie!")
else:
    print("Niektóre importy nie działają. Sprawdź szczegóły powyżej.")

print("\nZawartość sys.path:")
for i, path in enumerate(sys.path):
    print(f"{i}. {path}") 