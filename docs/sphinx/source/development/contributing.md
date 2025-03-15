# Współpraca przy projekcie

## Wprowadzenie

Dziękujemy za zainteresowanie projektem AgentMT5! Ten dokument zawiera informacje na temat sposobu współpracy przy rozwoju projektu, zgłaszania błędów i propozycji nowych funkcji.

## Jak zacząć

1. Sklonuj repozytorium:
   ```bash
   git clone https://github.com/jeden-/AgentMT5.git
   cd AgentMT5
   ```

2. Utwórz i aktywuj wirtualne środowisko:
   ```bash
   python -m venv venv
   # Windows
   venv\Scripts\activate
   # Linux/Mac
   source venv/bin/activate
   ```

3. Zainstaluj zależności deweloperskie:
   ```bash
   pip install -r requirements-dev.txt
   ```

4. Skonfiguruj pre-commit hooks:
   ```bash
   pre-commit install
   ```

## Struktura projektu

```
AgentMT5/
├── docs/                  # Dokumentacja
├── scripts/               # Skrypty pomocnicze
├── src/                   # Kod źródłowy
│   ├── ai_controller/     # Moduł kontrolera AI
│   ├── mt5_bridge/        # Moduł komunikacji z MT5
│   ├── position_manager/  # Moduł zarządzania pozycjami
│   ├── monitoring/        # Moduł monitorowania
│   ├── ui/                # Interfejs użytkownika
│   └── utils/             # Narzędzia pomocnicze
├── tests/                 # Testy
│   ├── unit/              # Testy jednostkowe
│   ├── integration/       # Testy integracyjne
│   └── performance/       # Testy wydajnościowe
├── .env.example           # Przykładowy plik konfiguracyjny
├── main.py                # Główny plik aplikacji
└── requirements.txt       # Zależności
```

## Proces rozwoju

### Gałęzie

- `main` - gałąź główna, zawiera stabilny kod
- `develop` - gałąź rozwojowa, zawiera najnowsze zmiany
- `feature/*` - gałęzie funkcji, tworzone dla nowych funkcjonalności
- `bugfix/*` - gałęzie naprawy błędów
- `release/*` - gałęzie wydań

### Workflow

1. Utwórz nową gałąź z `develop`:
   ```bash
   git checkout develop
   git pull
   git checkout -b feature/nazwa-funkcji
   ```

2. Wprowadź zmiany i przetestuj je:
   ```bash
   # Wprowadź zmiany
   # Uruchom testy
   pytest
   ```

3. Zatwierdź zmiany:
   ```bash
   git add .
   git commit -m "Dodano funkcję X"
   ```

4. Wypchnij zmiany do repozytorium:
   ```bash
   git push origin feature/nazwa-funkcji
   ```

5. Utwórz Pull Request do gałęzi `develop`

## Standardy kodowania

### Styl kodu

Projekt używa standardu PEP 8 dla kodu Python. Używamy narzędzi:

- `black` - do formatowania kodu
- `isort` - do sortowania importów
- `flake8` - do sprawdzania zgodności z PEP 8
- `mypy` - do sprawdzania typów

### Dokumentacja kodu

Wszystkie funkcje, klasy i moduły powinny być udokumentowane za pomocą docstringów w formacie Google:

```python
def funkcja(parametr1: str, parametr2: int) -> bool:
    """Krótki opis funkcji.
    
    Dłuższy opis funkcji, który może zawierać więcej szczegółów.
    
    Args:
        parametr1: Opis pierwszego parametru.
        parametr2: Opis drugiego parametru.
        
    Returns:
        Opis wartości zwracanej.
        
    Raises:
        ValueError: Kiedy parametr1 jest pusty.
    """
    if not parametr1:
        raise ValueError("parametr1 nie może być pusty")
    # Implementacja
    return True
```

## Testowanie

### Testy jednostkowe

Testy jednostkowe znajdują się w katalogu `tests/unit/`. Używamy `pytest` do uruchamiania testów:

```bash
# Uruchom wszystkie testy
pytest

# Uruchom testy dla konkretnego modułu
pytest tests/unit/test_mt5_bridge.py

# Uruchom testy z pokryciem kodu
pytest --cov=src
```

### Testy integracyjne

Testy integracyjne znajdują się w katalogu `tests/integration/`. Wymagają one działającego środowiska MT5:

```bash
pytest tests/integration/
```

### Testy wydajnościowe

Testy wydajnościowe znajdują się w katalogu `tests/performance/`:

```bash
pytest tests/performance/
```

## Zgłaszanie błędów

Jeśli znalazłeś błąd, zgłoś go za pomocą systemu Issues na GitHubie:

1. Sprawdź, czy błąd nie został już zgłoszony
2. Utwórz nowe zgłoszenie z dokładnym opisem błędu
3. Dołącz kroki do odtworzenia błędu
4. Dołącz logi, zrzuty ekranu i inne pomocne informacje

## Propozycje nowych funkcji

Propozycje nowych funkcji można zgłaszać za pomocą systemu Issues na GitHubie:

1. Sprawdź, czy podobna funkcja nie została już zaproponowana
2. Utwórz nowe zgłoszenie z dokładnym opisem funkcji
3. Wyjaśnij, dlaczego funkcja jest potrzebna i jakie problemy rozwiązuje
4. Jeśli to możliwe, dołącz przykłady użycia

## Publikowanie wydań

Proces publikowania nowych wydań:

1. Utwórz gałąź `release/X.Y.Z` z `develop`
2. Zaktualizuj numer wersji w pliku `version.py`
3. Zaktualizuj plik `CHANGELOG.md`
4. Przetestuj wydanie
5. Utwórz Pull Request do `main`
6. Po zatwierdzeniu, utwórz tag z numerem wersji
7. Scal zmiany z `main` z powrotem do `develop`

## Kontakt

Jeśli masz pytania dotyczące współpracy przy projekcie, skontaktuj się z nami:

- GitHub: https://github.com/jeden-/AgentMT5 