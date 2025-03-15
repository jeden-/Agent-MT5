# Testy jednostkowe i wydajnościowe systemu backtestingu

Ten katalog zawiera testy jednostkowe i wydajnościowe dla systemu backtestingu. Poniżej znajduje się opis poszczególnych plików testowych oraz instrukcje ich uruchamiania.

## Struktura testów

- `test_historical_data_manager.py` - testy dla klasy `HistoricalDataManager`
- `test_backtest_engine.py` - testy dla klasy `BacktestEngine`
- `test_trading_strategies.py` - testy dla strategii handlowych
- `test_parameter_optimizer.py` - testy dla systemu optymalizacji parametrów
- `test_performance.py` - testy wydajnościowe dla całego systemu backtestingu
- `test_integration.py` - testy integracyjne dla całego workflow backtestingu
- `test_combined_strategy.py` - testy dla strategii kombinowanej wskaźników

## Uruchamianie testów

### Uruchamianie wszystkich testów jednostkowych

Aby uruchomić wszystkie testy jednostkowe, wykonaj poniższą komendę z głównego katalogu projektu:

```bash
python -m unittest discover -s src/backtest/tests
```

### Uruchamianie pojedynczego pliku testowego

Aby uruchomić testy z pojedynczego pliku, wykonaj:

```bash
python -m unittest src/backtest/tests/test_backtest_engine.py
```

### Uruchamianie pojedynczego testu

Aby uruchomić pojedynczy test, wykonaj:

```bash
python -m unittest src.backtest.tests.test_backtest_engine.TestBacktestEngine.test_backtest_run_with_mock_data
```

### Uruchamianie testów wydajnościowych

Testy wydajnościowe mogą zająć więcej czasu i wymagają więcej zasobów systemowych:

```bash
python -m unittest src/backtest/tests/test_performance.py
```

## Uwagi dotyczące testowania

### Mocki dla MT5

Niektóre testy używają mocków dla `MT5Connector`, więc nie wymagają rzeczywistego połączenia z terminalem MT5. Jeśli chcesz uruchomić testy integracyjne, które korzystają z rzeczywistego połączenia, upewnij się, że terminal MT5 jest uruchomiony i połączony.

### Testy wydajnościowe

Testy wydajnościowe generują duże ilości danych, co może wpłynąć na zużycie pamięci. Zalecane jest uruchamianie ich na maszynie z co najmniej 8GB RAM. Testy te są oznaczone odpowiednimi asercjami, które sprawdzają czy wydajność jest zgodna z oczekiwaniami.

### Diagnostyka problemów

Jeśli napotkasz problemy podczas uruchamiania testów, sprawdź:

1. Czy wszystkie zależności są poprawnie zainstalowane: `pip install -r requirements.txt`
2. Czy ścieżki są poprawnie skonfigurowane (w niektórych testach modyfikujemy `sys.path`)
3. Czy terminal MT5 jest uruchomiony i połączony (dla testów integracyjnych)
4. Czy masz wystarczającą ilość pamięci RAM dla testów wydajnościowych

## Rozszerzanie testów

Podczas dodawania nowych funkcjonalności do systemu backtestingu, należy również dodać odpowiednie testy. Zalecane jest stosowanie podejścia TDD (Test-Driven Development), czyli napisanie testu przed implementacją funkcjonalności.

### Dodawanie nowych testów wydajnościowych

Testy wydajnościowe powinny sprawdzać:
- Zużycie pamięci
- Szybkość przetwarzania danych
- Wydajność w przypadku dużych zbiorów danych lub wielu kombinacji parametrów

### Dodawanie nowych testów strategii

Podczas dodawania nowej strategii handlowej, należy dodać testy, które sprawdzają:
- Generowanie sygnałów w różnych warunkach rynkowych (trend wzrostowy, spadkowy, rynek neutralny)
- Poprawność poziomów entry, SL, TP
- Zachowanie strategii na znanych scenariuszach testowych 