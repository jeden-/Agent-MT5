"""
Konfiguracja pytest i rozwiązanie problemów z importami.
"""

import sys
import os
import importlib.util
import importlib.machinery
from pathlib import Path
import builtins
import types


# Zapisz oryginalną funkcję __import__
original_import = builtins.__import__


def patched_import(name, globals=None, locals=None, fromlist=(), level=0):
    """
    Zastępuje standardową funkcję importu, aby obsłużyć import modułów z przedrostkiem 'src.'.
    """
    # Jeśli import nie zaczyna się od 'src.', używamy oryginalnej funkcji importu
    if not name.startswith('src.'):
        return original_import(name, globals, locals, fromlist, level)
    
    try:
        # Najpierw spróbuj standardowego importu
        return original_import(name, globals, locals, fromlist, level)
    except ImportError as e:
        # Jeśli się nie powiodło, spróbuj załadować moduł ręcznie
        module_name = name
        module_parts = name.split('.')
        
        # Znajdź główny katalog projektu
        project_root = Path(__file__).parent
        
        # Buduj ścieżkę do modułu
        module_path = project_root
        for part in module_parts:
            module_path = module_path / part
        
        # Dodaj .py do ostatniej części (o ile to nie jest pakiet)
        if not (module_path / "__init__.py").exists():
            module_path = module_path.parent / f"{module_path.name}.py"
        else:
            module_path = module_path / "__init__.py"
        
        # Jeśli plik istnieje, załaduj go
        if module_path.exists():
            spec = importlib.util.spec_from_file_location(module_name, module_path)
            if spec:
                module = importlib.util.module_from_spec(spec)
                sys.modules[module_name] = module
                spec.loader.exec_module(module)
                
                # Obsługa fromlist (import from)
                if fromlist:
                    result = module
                else:
                    # Dla prostego importu zwracamy najwyższy moduł
                    result = sys.modules[module_parts[0]]
                
                return result
        
        # Jeśli nadal się nie powiodło, propaguj oryginalny błąd
        raise e


# Podmieniamy standardową funkcję importu naszą patchowaną wersją
builtins.__import__ = patched_import


def add_module_to_path():
    """Dodaje katalog główny projektu do sys.path."""
    # Ścieżka do katalogu głównego projektu
    project_root = Path(__file__).parent
    src_path = project_root / "src"
    
    # Dodaj ścieżki do sys.path
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    
    if str(src_path) not in sys.path:
        sys.path.insert(0, str(src_path))
    
    # Zapamiętaj, że dodaliśmy ścieżki
    sys.path_fixed = True


# Dodaj ścieżki projektu do sys.path
add_module_to_path()


# Monkeypatch dla sys.meta_path, aby obsługiwał importy z przedrostkiem 'src.'
class SrcFinder:
    @classmethod
    def find_spec(cls, fullname, path=None, target=None):
        if not fullname.startswith('src.'):
            return None
        
        # Reszta kodu jest obsługiwana przez patched_import
        return None


# Dodaj SrcFinder do sys.meta_path
sys.meta_path.insert(0, SrcFinder) 