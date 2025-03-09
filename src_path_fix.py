"""
Moduł naprawiający importy dla projektu Trading Agent MT5.
"""

import sys
import os
import importlib.util
import importlib.machinery
from pathlib import Path


class SrcPathFinder:
    """Własny PathFinder, który przekierowuje importy z 'src.' do lokalnego katalogu."""
    
    @classmethod
    def find_spec(cls, fullname, path=None, target=None):
        # Sprawdź, czy import dotyczy modułu z przedrostkiem 'src.'
        if not fullname.startswith('src.'):
            return None
        
        # Pobierz ścieżkę bez przedrostka 'src.'
        name_without_prefix = fullname[4:]  # obetnij 'src.'
        
        # Znajdź główny katalog projektu
        project_root = Path(__file__).parent
        
        # Przekształć ścieżkę modułu na ścieżkę pliku
        module_parts = name_without_prefix.split('.')
        module_path = project_root / 'src' / Path(*module_parts)
        
        # Sprawdź, czy to jest pakiet (katalog z __init__.py)
        if (module_path / '__init__.py').exists():
            # To jest pakiet
            return importlib.machinery.ModuleSpec(
                fullname,
                importlib.machinery.SourceFileLoader(fullname, str(module_path / '__init__.py')),
                is_package=True
            )
        
        # Sprawdź, czy to jest moduł (plik .py)
        if (module_path.parent / f"{module_path.name}.py").exists():
            # To jest moduł
            return importlib.machinery.ModuleSpec(
                fullname,
                importlib.machinery.SourceFileLoader(fullname, str(module_path.parent / f"{module_path.name}.py")),
                is_package=False
            )
        
        return None


# Zarejestruj nasz PathFinder na początku sys.meta_path
sys.meta_path.insert(0, SrcPathFinder)

# Dodaj katalog projektu do sys.path
project_root = os.path.abspath(os.path.dirname(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Dodaj katalog src do sys.path
src_path = os.path.join(project_root, 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

# Upewnij się, że katalogi unittest są w sys.path
required_directories = [
    os.path.join(project_root, 'src', 'tests'),
    os.path.join(project_root, 'src', 'tests', 'unit'),
    os.path.join(project_root, 'src', 'tests', 'unit', 'analysis')
]

for directory in required_directories:
    if os.path.exists(directory) and directory not in sys.path:
        sys.path.insert(0, directory)

# Utwórz wszystkie brakujące katalogi __pycache__ i __init__.py, aby Python traktował je jako pakiety
for directory in required_directories:
    if not os.path.exists(directory):
        os.makedirs(directory, exist_ok=True)
    
    init_file = os.path.join(directory, '__init__.py')
    if not os.path.exists(init_file):
        with open(init_file, 'w') as f:
            f.write('# Auto-generated __init__.py\n')

# Dodaj zmienną środowiskową PYTHONPATH
os.environ['PYTHONPATH'] = project_root 