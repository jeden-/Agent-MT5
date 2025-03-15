# Testy jednostkowe dla modułu backtestingu

W tym katalogu znajdują się testy jednostkowe dla modułu backtestingu, który jest odpowiedzialny za symulację strategii handlowych na danych historycznych.

## Struktura testów

- `test_historical_data_manager.py` - Testy dla klasy `HistoricalDataManager`, która zarządza danymi historycznymi
- *Kolejne pliki testów będą dodawane w miarę postępu prac*

## Cele testów

Testy jednostkowe mają na celu zweryfikowanie poprawności działania poszczególnych komponentów modułu backtestingu. W szczególności, testy weryfikują:

1. Poprawność pobierania danych historycznych z MT5
2. Poprawność mechanizmu cache'owania danych
3. Obsługę błędów i wyjątków
4. Generowanie danych syntetycznych (jeśli zaimplementowane)
5. Czyszczenie i walidację danych

## Uruchamianie testów

Testy można uruchomić za pomocą modułu `unittest` Pythona:

```bash
# Uruchomienie wszystkich testów
python -m unittest discover -s tests/unit/backtest

# Uruchomienie konkretnego testu
python -m unittest tests/unit/backtest/test_historical_data_manager.py
```

Alternatywnie można użyć modułu `pytest`:

```bash
# Uruchomienie wszystkich testów
pytest tests/unit/backtest

# Uruchomienie konkretnego testu
pytest tests/unit/backtest/test_historical_data_manager.py
```

## Raporty z testów

Raporty z testów są generowane w formacie HTML i zapisywane w katalogu `reports/tests`. Raport zawiera informacje o:

- Liczbie przeprowadzonych testów
- Liczbie testów zakończonych sukcesem
- Liczbie testów zakończonych niepowodzeniem
- Pokryciu kodu testami

## Zależności

Do uruchomienia testów wymagane są następujące pakiety:

- `unittest` (wbudowany w Pythona)
- `pytest` (opcjonalnie, do bardziej zaawansowanych funkcji testowania)
- `pandas` (do testów z DataFrame)
- `numpy` (do generowania danych testowych)

## Zasady pisania testów

Przy tworzeniu nowych testów należy przestrzegać następujących zasad:

1. Każda klasa w module backtestingu powinna mieć odpowiadającą jej klasę testową
2. Nazwa pliku testowego powinna zaczynać się od prefiksu `test_`
3. Nazwa metody testowej powinna zaczynać się od prefiksu `test_`
4. Testy powinny być niezależne od siebie (każdy test powinien móc być uruchomiony osobno)
5. Testy nie powinny zależeć od zewnętrznych zasobów (zewnętrzne zależności powinny być mockowane)
6. Testy powinny być dobrze udokumentowane

## Plan rozwoju testów

1. Testy dla `HistoricalDataManager` - **Zaimplementowane**
2. Testy dla `BacktestEngine` - Planowane
3. Testy dla strategii handlowych - Planowane
4. Testy dla `PositionManager` - Planowane
5. Testy integracyjne dla całego systemu backtestingu - Planowane 