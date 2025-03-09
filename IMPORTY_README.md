# Rozwiązanie problemów z importami w projekcie AgentMT5

## Problem

W projekcie AgentMT5 występują problemy z importami modułów, które utrudniają uruchamianie testów jednostkowych i rozwój nowych komponentów. Główne problemy to:

1. Niespójność stylów importu (bezwzględne vs. względne)
2. Importy z przedrostkiem `src.` nie działają poprawnie w różnych kontekstach uruchamiania
3. Problemy z cyklicznymi zależnościami między modułami

## Rozwiązanie

Zaimplementowaliśmy kilka narzędzi pomocniczych, które rozwiązują te problemy:

### 1. Skrypty do uruchamiania testów

- `run_tests.ps1` (PowerShell) - skrypt do uruchamiania testów w systemie Windows
- `run_tests.sh` (Bash) - skrypt do uruchamiania testów w systemach Unix/Linux

Skrypty te ustawiają odpowiednio zmienną środowiskową `PYTHONPATH` i uruchamiają testy z poprawnie skonfigurowanym środowiskiem.

### 2. Moduł naprawiający importy

Plik `src_path_fix.py` zawiera implementację własnego `PathFinder`, który przekierowuje importy z przedrostkiem `src.` do odpowiednich modułów w lokalnym katalogu.

### 3. Plik konfiguracyjny dla testów

Plik `conftest.py` zawiera monkey-patching dla funkcji importu, który rozwiązuje problemy z importami w testach.

## Jak używać

### Uruchamianie testów

Aby uruchomić testy, użyj jednego z poniższych poleceń:

```powershell
# Windows (PowerShell)
.\run_tests.ps1 src.tests.unit.analysis.test_feedback_loop  # Uruchom konkretny test
.\run_tests.ps1 all                                         # Uruchom wszystkie testy
```

```bash
# Unix/Linux (Bash)
./run_tests.sh src.tests.unit.analysis.test_feedback_loop   # Uruchom konkretny test
./run_tests.sh all                                          # Uruchom wszystkie testy
```

### Uruchamianie aplikacji

Aby uruchomić aplikację z poprawnie skonfigurowanym środowiskiem, użyj:

```powershell
# Windows (PowerShell)
.\run_app.ps1
```

### Tworzenie nowych modułów

Przy tworzeniu nowych modułów, zalecamy używanie następującego wzorca importów:

```python
# Importy wewnętrzne
try:
    # Próbujemy importu z przedrostkiem src (dla testów z katalogu głównego)
    from src.analysis.signal_generator import SignalType
    from src.database.signal_repository import SignalRepository
except ImportError:
    # Próbujemy importu względnego (dla uruchamiania z katalogu src)
    from .signal_generator import SignalType
    from ..database.signal_repository import SignalRepository
```

Ten wzorzec zapewnia, że importy będą działać poprawnie niezależnie od kontekstu uruchamiania.

## Długoterminowe rozwiązanie

Dla długoterminowego rozwiązania problemów z importami, zalecamy:

1. Standaryzację stylu importów w całym projekcie
2. Utworzenie pliku `setup.py` lub `pyproject.toml` i instalację projektu jako pakietu
3. Refaktoryzację struktury projektu, aby uniknąć cyklicznych zależności
4. Dodanie testów integracyjnych, które weryfikują poprawność importów

## Autorzy

Zespół AgentMT5 