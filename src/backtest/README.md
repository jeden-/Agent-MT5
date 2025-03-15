# System Backtestingu dla AgentMT5

Ten moduł zawiera kompletne rozwiązanie do backtestingu strategii tradingowych, optymalizacji parametrów i walidacji walk-forward dla systemu AgentMT5.

## Główne komponenty

### 1. Silnik backtestingu (`backtest_engine.py`)
Centralny komponent odpowiedzialny za przeprowadzanie backtestingu strategii na danych historycznych:
- Zaawansowana pętla backtestingu z dokładną symulacją ticków
- Zarządzanie pozycjami i zleceniami
- Generowanie metryk i statystyk wydajności
- Konfigurowalny poprzez klasę `BacktestConfig`

### 2. Menedżer danych historycznych (`historical_data_manager.py`)
Odpowiada za pobieranie, przechowywanie i zarządzanie danymi historycznymi:
- Efektywny mechanizm cache'owania danych w formacie Parquet
- Automatyczna aktualizacja danych w cache'u
- Wsparcie dla różnych timeframe'ów i symboli

### 3. Interfejs strategii (`strategy.py`)
Abstrakcyjna klasa definiująca interfejs dla strategii tradingowych:
- Wspólny interfejs dla wszystkich strategii (`TradingStrategy`)
- Konfiguracja strategii poprzez klasę `StrategyConfig`
- Mechanizm generowania sygnałów handlowych

### 4. Przykładowe strategie
Zestaw gotowych strategii do testowania:
- `SimpleMovingAverageStrategy` - strategia oparta na przecięciu średnich kroczących
- `RSIStrategy` - strategia wykorzystująca wskaźnik RSI
- `BollingerBandsStrategy` - strategia oparta na wstęgach Bollingera
- `MACDStrategy` - strategia wykorzystująca wskaźnik MACD
- `CombinedIndicatorsStrategy` - strategia łącząca różne wskaźniki (odzwierciedla główny generator sygnałów)

### 5. Zarządzanie pozycjami (`position_manager.py`)
Moduł odpowiedzialny za zarządzanie pozycjami i zleceniami:
- Implementacja trailing stop, breakeven i częściowego zamykania pozycji
- Zarządzanie zleceniami oczekującymi
- Walidacja pozycji i zarządzanie ryzykiem

### 6. Raportowanie i wizualizacja (`backtest_metrics.py`)
Generowanie raportów i wizualizacji wyników backtestingu:
- Interaktywne wykresy (krzywa kapitału, drawdown, statystyki)
- Szczegółowe metryki wydajności (win rate, profit factor, itp.)
- Eksport wyników do różnych formatów (HTML, CSV, Excel)

### 7. Optymalizacja parametrów (`parameter_optimizer.py`)
System optymalizacji parametrów strategii:
- Przeszukiwanie siatki (grid search) dla różnych kombinacji parametrów
- Wielowątkowe przetwarzanie dla przyspieszenia optymalizacji
- Zapisywanie i ładowanie wyników optymalizacji

### 8. Testowanie walk-forward (`walk_forward_tester.py`)
System do walidacji strategii metodą walk-forward:
- Testowanie strategii na następujących po sobie okresach
- Optymalizacja parametrów na okresie treningowym i testowanie na okresie testowym
- Generowanie szczegółowych raportów z testów walk-forward

### 9. Interfejs użytkownika (`backtest_ui.py`) - w trakcie implementacji
Interfejs użytkownika oparty na Streamlit do interaktywnej pracy z systemem:
- Konfiguracja i uruchamianie backtestów
- Wizualizacja wyników
- Optymalizacja parametrów strategii

## Jak korzystać z systemu backtestingu

### Uruchomienie pojedynczego backtestu

```python
from datetime import datetime, timedelta
from src.backtest.backtest_engine import BacktestEngine, BacktestConfig
from src.backtest.strategies.sma_strategy import SimpleMovingAverageStrategy
from src.backtest.strategy import StrategyConfig

# Konfiguracja strategii
strategy_config = StrategyConfig(
    stop_loss_pips=50,
    take_profit_pips=100,
    position_size_pct=1.0,
    params={
        'fast_period': 10,
        'slow_period': 30
    }
)

# Utworzenie strategii
strategy = SimpleMovingAverageStrategy(config=strategy_config)

# Konfiguracja backtestingu
end_date = datetime.now()
start_date = end_date - timedelta(days=30)

backtest_config = BacktestConfig(
    symbol="EURUSD",
    timeframe="H1",
    start_date=start_date,
    end_date=end_date,
    initial_balance=10000.0,
    position_size_pct=1.0,
    commission=0.0001,
    use_cache=True,
    strategy_name="SMA_Test"
)

# Uruchomienie backtestingu
engine = BacktestEngine(config=backtest_config, strategy=strategy)
result = engine.run()

# Generowanie raportu
from src.backtest.backtest_metrics import generate_report
report_path = generate_report(result, output_dir="backtest_results")

print(f"Backtest zakończony. Raport zapisany w: {report_path}")
print(f"Zysk netto: {result.metrics['net_profit']:.2f} USD")
print(f"Win rate: {result.metrics['win_rate']*100:.2f}%")
print(f"Profit factor: {result.metrics['profit_factor']:.2f}")
```

### Optymalizacja parametrów strategii

```python
from datetime import datetime, timedelta
from src.backtest.parameter_optimizer import ParameterOptimizer
from src.backtest.strategies.rsi_strategy import RSIStrategy

# Przestrzeń parametrów do przeszukania
parameter_space = {
    'rsi_period': [7, 14, 21],
    'overbought_threshold': [70, 75, 80],
    'oversold_threshold': [20, 25, 30],
    'stop_loss_pips': [30, 50, 70],
    'take_profit_pips': [60, 100, 140]
}

# Inicjalizacja optymalizatora
optimizer = ParameterOptimizer(
    strategy_class=RSIStrategy,
    parameter_space=parameter_space,
    evaluation_metric="net_profit",
    workers=4  # Liczba równoległych procesów
)

# Przeprowadzenie optymalizacji
end_date = datetime.now()
start_date = end_date - timedelta(days=90)

results = optimizer.grid_search(
    symbol="GBPUSD",
    timeframe="H4",
    start_date=start_date,
    end_date=end_date,
    use_cache=True
)

# Analiza wyników
for i, result in enumerate(results[:5]):
    print(f"Top {i+1}:")
    print(f"  Parametry: {result['params']}")
    print(f"  Zysk netto: {result['metrics']['net_profit']:.2f} USD")
    print(f"  Win rate: {result['metrics']['win_rate']*100:.2f}%")
    print(f"  Profit factor: {result['metrics']['profit_factor']:.2f}")
```

### Przeprowadzenie testu walk-forward

```python
from datetime import datetime, timedelta
from src.backtest.walk_forward_tester import WalkForwardTester
from src.backtest.strategies.macd_strategy import MACDStrategy

# Przestrzeń parametrów
parameter_space = {
    'fast_period': [8, 12, 16],
    'slow_period': [21, 26, 30],
    'signal_period': [7, 9, 11],
    'stop_loss_pips': [50, 70],
    'take_profit_pips': [100, 150]
}

# Inicjalizacja testera walk-forward
tester = WalkForwardTester(
    strategy_class=MACDStrategy,
    parameter_space=parameter_space,
    train_days=60,     # Okres treningowy
    test_days=30,      # Okres testowy
    step_days=30,      # Krok przesunięcia okna
    anchor_mode="rolling",
    evaluation_metric="net_profit",
    workers=4
)

# Przeprowadzenie testu
end_date = datetime.now()
start_date = end_date - timedelta(days=180)  # 6 miesięcy danych

results = tester.run(
    symbol="USDJPY",
    timeframe="H4",
    start_date=start_date,
    end_date=end_date,
    use_cache=True
)

# Wygenerowanie raportu
tester.generate_report("USDJPY", "H4")
```

### Uruchomienie backtestingu z linii poleceń

System backtestingu można również uruchomić z linii poleceń przy użyciu modułu `start.py` w głównym katalogu projektu:

```bash
python start.py --backtest --symbol EURUSD --timeframe H1 --days 30 --strategy SMA
```

Dostępne opcje:
- `--backtest` - uruchamia moduł backtestingu
- `--symbol` - symbol instrumentu (np. EURUSD, GBPUSD)
- `--timeframe` - timeframe (np. M5, M15, H1, H4, D1)
- `--days` - liczba dni do backtestu
- `--strategy` - nazwa strategii (SMA, RSI, BB, MACD, COMBINED)
- `--output` - katalog wyjściowy dla wyników (domyślnie: backtest_results)

## Instalacja i wymagania

System backtestingu jest integralną częścią projektu AgentMT5 i nie wymaga dodatkowej instalacji poza zależnościami głównego projektu.

Główne zależności:
- pandas
- numpy
- matplotlib
- plotly
- streamlit (dla interfejsu użytkownika)
- MetaTrader5 (dla dostępu do danych historycznych)

## Struktura katalogów

```
src/backtest/
├── backtest_engine.py       # Główny silnik backtestingu
├── strategy.py              # Abstrakcyjna definicja strategii
├── historical_data_manager.py # Zarządzanie danymi historycznymi
├── position_manager.py      # Zarządzanie pozycjami
├── backtest_metrics.py      # Raportowanie i metryki
├── parameter_optimizer.py   # Optymalizacja parametrów
├── walk_forward_tester.py   # Testy walk-forward
├── backtest_ui.py           # Interfejs użytkownika (Streamlit)
├── examples/                # Przykłady użycia
│   ├── strategy_backtest_example.py
│   ├── optimization_example.py
│   └── walkforward_example.py
├── strategies/              # Implementacje strategii
│   ├── sma_strategy.py
│   ├── rsi_strategy.py
│   ├── bb_strategy.py
│   ├── macd_strategy.py
│   └── combined_strategy.py
└── tests/                   # Testy jednostkowe i integracyjne
    ├── test_backtest_engine.py
    ├── test_strategies.py
    └── test_metrics.py
```

## Stan implementacji

Aktualny stan implementacji jest śledzony w pliku `BACKTEST_TODO.md`. Większość kluczowych komponentów jest już zaimplementowana i gotowa do użycia. Obecnie trwają prace nad interfejsem użytkownika (UI) i optymalizacją parametrów głównego generatora sygnałów.

## Dalszy rozwój

Planowane są następujące ulepszenia:
1. Integracja z zewnętrznymi źródłami danych (poza MT5)
2. Wsparcie dla strategii opartych na uczeniu maszynowym
3. Dodanie analizy Monte Carlo dla lepszej oceny ryzyka
4. Rozbudowa interfejsu użytkownika o dodatkowe funkcje
5. Optymalizacja wydajności dla bardzo dużych zbiorów danych

## Dokumentacja API

Pełna dokumentacja API dostępna jest w komentarzach kodu i zostanie wygenerowana w ramach Etapu 7 (Dokumentacja i wdrożenie).

# Dokumentacja modułu backtestingu

## Spis treści

1. [Wprowadzenie](#wprowadzenie)
2. [Architektura](#architektura)
3. [Komponenty](#komponenty)
   - [HistoricalDataManager](#historicaldatamanager)
   - [BacktestEngine](#backtestengine)
   - [TradingStrategy](#tradingstrategy)
   - [PositionManager](#positionmanager)
   - [BacktestMetrics](#backtestmetrics)
   - [ParameterOptimizer](#parameteroptimizer)
   - [WalkForwardTester](#walkforwardtester)
4. [Przepływy pracy](#przepływy-pracy)
   - [Podstawowy backtest](#podstawowy-backtest)
   - [Optymalizacja parametrów](#optymalizacja-parametrów)
   - [Testowanie walk-forward](#testowanie-walk-forward)
5. [Integracja z interfejsem użytkownika](#integracja-z-interfejsem-użytkownika)
6. [Przykłady](#przykłady)

## Wprowadzenie

Moduł backtestingu umożliwia testowanie strategii tradingowych na danych historycznych. System pozwala na:
- Testowanie różnych strategii handlowych
- Optymalizację parametrów strategii
- Analizę wyników za pomocą różnych metryk
- Generowanie raportów i wizualizacji
- Przeprowadzanie testów walk-forward

## Architektura

Moduł backtestingu został zaprojektowany zgodnie z wzorcem architektonicznym opartym na komponentach, co umożliwia elastyczność, modularność i łatwość rozszerzania. Główne elementy architektury:

```
┌─────────────────────┐      ┌───────────────────┐     ┌────────────────────┐
│ HistoricalDataManager │────▶│   BacktestEngine   │────▶│ Backtest Results   │
└─────────────────────┘      └───────────────────┘     └────────────────────┘
                                      ▲                           │
                                      │                           │
                              ┌───────┴───────┐                   │
                              │ TradingStrategy │                   │
                              └───────────────┘                   │
                                                                  │
                                      ▲                           ▼
                                      │                  ┌────────────────────┐
                      ┌───────────────┴────────────┐    │   BacktestMetrics   │
                      │                            │    └────────────────────┘
           ┌──────────┴──────────┐     ┌──────────┴──────────┐        │
           │ ParameterOptimizer  │     │   WalkForwardTester  │        │
           └─────────────────────┘     └─────────────────────┘        │
                                                                      ▼
                                                           ┌────────────────────┐
                                                           │ Report Generator   │
                                                           └────────────────────┘
```

## Komponenty

### HistoricalDataManager

Klasa odpowiedzialna za zarządzanie danymi historycznymi. Główne funkcje:

- Pobieranie danych historycznych z MetaTrader 5
- Zarządzanie cache'm danych w formacie Parquet
- Preprocesowanie danych (agregacja, obliczanie wskaźników)

#### API

```python
class HistoricalDataManager:
    def __init__(self, cache_dir="market_data_cache"):
        # ...
    
    def get_historical_data(self, symbol, timeframe, start_date, end_date):
        # Zwraca DataFrame z danymi OHLCV dla podanego symbolu i timeframe'u
    
    def cache_data(self, symbol, timeframe, data):
        # Zapisuje dane do cache'u
    
    def load_cached_data(self, symbol, timeframe, start_date, end_date):
        # Ładuje dane z cache'u
    
    def update_cache(self, symbol, timeframe, end_date=None):
        # Aktualizuje cache nowych danych
```

### BacktestEngine

Silnik backtestingu odpowiedzialny za uruchamianie testów. Główne funkcje:

- Uruchamianie backtestów strategii na danych historycznych
- Zarządzanie pozycjami i kapitałem
- Generowanie wyników i metryk

#### API

```python
class BacktestConfig:
    def __init__(self, symbol, timeframe, start_date, end_date, 
                 initial_capital=10000, risk_per_trade=0.01, 
                 include_fees=True, commission=0.0, spread=0.0):
        # ...

class BacktestEngine:
    def __init__(self, config, strategy=None, position_manager=None):
        # ...
    
    def run(self):
        # Uruchamia backtest i zwraca wyniki
    
    def generate_report(self, output_dir=None, filename=None):
        # Generuje raport HTML z wynikami
```

### TradingStrategy

Interfejs dla strategii tradingowych. Strategie muszą implementować metodę `generate_signals`.

#### API

```python
class TradingStrategy(ABC):
    @abstractmethod
    def generate_signals(self, data):
        """
        Generuje sygnały handlowe na podstawie danych.
        
        Args:
            data: DataFrame z danymi rynkowymi
            
        Returns:
            Lista obiektów StrategySignal
        """
        pass
```

Dostępne implementacje strategii:

- **SimpleMovingAverageStrategy**: Strategia oparta na przecięciach średnich kroczących
- **RSIStrategy**: Strategia wykorzystująca wskaźnik RSI do identyfikacji wykupienia/wyprzedania
- **BollingerBandsStrategy**: Strategia oparta na wstęgach Bollingera
- **MACDStrategy**: Strategia wykorzystująca wskaźnik MACD
- **CombinedIndicatorsStrategy**: Strategia łącząca różne wskaźniki techniczne, odpowiadająca logice głównego generatora sygnałów systemu AgentMT5

### PositionManager

Klasa odpowiedzialna za zarządzanie pozycjami w trakcie backtestingu. Główne funkcje:

- Otwieranie i zamykanie pozycji
- Zarządzanie stop lossami i take profitami
- Implementacja trailing stopów i breakeven

#### API

```python
class PositionManager:
    def __init__(self, initial_capital=10000, risk_per_trade=0.01, 
                 include_fees=True, commission=0.0, spread=0.0):
        # ...
    
    def open_position(self, symbol, position_type, price, stop_loss, take_profit, 
                      volume=None, risk_amount=None, risk_pct=None):
        # Otwiera nową pozycję
    
    def close_position(self, position_id, price, time):
        # Zamyka istniejącą pozycję
    
    def update_position(self, position_id, current_price, current_time):
        # Aktualizuje pozycję (np. trailing stop)
    
    def apply_trailing_stop(self, position_id, current_price):
        # Stosuje trailing stop dla pozycji
```

### BacktestMetrics

Moduł do obliczania metryk wydajności backtestingu. Dostępne metryki:

- Net Profit
- Win Rate
- Profit Factor
- Sharpe Ratio
- Max Drawdown
- Calmar Ratio
- Sortino Ratio
- Average Trade
- Average Win/Loss

#### API

```python
def calculate_metrics(backtest_result):
    """
    Oblicza metryki wydajności na podstawie wyników backtestingu.
    
    Args:
        backtest_result: Obiekt BacktestResult zawierający wyniki
        
    Returns:
        Słownik z metrykami
    """
    # ...
```

### ParameterOptimizer

Klasa do optymalizacji parametrów strategii. Główne funkcje:

- Grid Search - przeszukiwanie siatki parametrów
- Random Search - losowe przeszukiwanie przestrzeni parametrów
- Optymalizacja wielowątkowa

#### API

```python
class OptimizationConfig:
    def __init__(self, param_grid, fitness_metric='sharpe_ratio', n_jobs=1):
        # ...

class ParameterOptimizer:
    def __init__(self, strategy_class, backtest_config, optimization_config, 
                 create_strategy=None):
        # ...
    
    def grid_search(self):
        # Przeprowadza przeszukiwanie siatki parametrów
    
    def random_search(self, n_iter=30):
        # Przeprowadza losowe przeszukiwanie przestrzeni parametrów
    
    def set_parameter_constraint(self, constraint_function):
        # Ustawia funkcję ograniczającą parametry
```

### WalkForwardTester

Klasa do przeprowadzania testów walk-forward. Główne funkcje:

- Podział danych na okna treningowe i testowe
- Optymalizacja parametrów w oknie treningowym
- Testowanie na oknie testowym
- Łączenie wyników z różnych okien

#### API

```python
class WalkForwardConfig:
    def __init__(self, train_size, test_size, step, optimize_metric='sharpe_ratio'):
        # ...

class WalkForwardTester:
    def __init__(self, strategy_class, param_grid, symbol, timeframe, 
                 start_date, end_date, walk_forward_config, create_strategy=None):
        # ...
    
    def run(self):
        # Przeprowadza test walk-forward
```

## Przepływy pracy

### Podstawowy backtest

```python
# 1. Importowanie niezbędnych modułów
from src.backtest.backtest_engine import BacktestEngine, BacktestConfig
from src.backtest.strategy import SimpleMovingAverageStrategy
from datetime import datetime

# 2. Konfiguracja backtestingu
config = BacktestConfig(
    symbol="EURUSD",
    timeframe="H1",
    start_date=datetime(2022, 1, 1),
    end_date=datetime(2022, 12, 31),
    initial_capital=10000,
    risk_per_trade=0.01,
    include_fees=True
)

# 3. Tworzenie strategii
strategy = SimpleMovingAverageStrategy(fast_ma_period=10, slow_ma_period=50)

# 4. Uruchomienie backtestingu
engine = BacktestEngine(config, strategy=strategy)
result = engine.run()

# 5. Analiza wyników
print(f"Net Profit: {result.net_profit}")
print(f"Win Rate: {result.win_rate * 100:.2f}%")
print(f"Profit Factor: {result.profit_factor:.2f}")
print(f"Max Drawdown: {result.max_drawdown * 100:.2f}%")
print(f"Liczba transakcji: {len(result.trades)}")

# 6. Generowanie raportu
engine.generate_report(output_dir="reports", filename="eurusd_sma_backtest")
```

### Optymalizacja parametrów

```python
# 1. Importowanie niezbędnych modułów
from src.backtest.backtest_engine import BacktestConfig
from src.backtest.parameter_optimizer import ParameterOptimizer, OptimizationConfig
from src.backtest.strategy import RSIStrategy
from datetime import datetime

# 2. Konfiguracja backtestingu
backtest_config = BacktestConfig(
    symbol="EURUSD",
    timeframe="H1",
    start_date=datetime(2022, 1, 1),
    end_date=datetime(2022, 12, 31),
    initial_capital=10000,
    risk_per_trade=0.01
)

# 3. Parametry do optymalizacji
param_grid = {
    'rsi_period': [7, 14, 21],
    'oversold': [20, 25, 30],
    'overbought': [70, 75, 80]
}

# 4. Konfiguracja optymalizacji
optimization_config = OptimizationConfig(
    param_grid=param_grid,
    fitness_metric='sharpe_ratio',
    n_jobs=-1  # Użyj wszystkich dostępnych rdzeni
)

# 5. Uruchomienie optymalizacji
optimizer = ParameterOptimizer(
    strategy_class=RSIStrategy,
    backtest_config=backtest_config,
    optimization_config=optimization_config
)

# 6. Grid search
results = optimizer.grid_search()

# 7. Analiza wyników
best_params = results[0]['params']
print(f"Najlepsze parametry: {best_params}")
print(f"Sharpe Ratio: {results[0]['metrics']['sharpe_ratio']:.2f}")
```

### Testowanie walk-forward

```python
# 1. Importowanie niezbędnych modułów
from src.backtest.walk_forward_tester import WalkForwardTester, WalkForwardConfig
from src.backtest.strategy import BollingerBandsStrategy
from datetime import datetime

# 2. Parametry do optymalizacji
param_grid = {
    'bb_period': [10, 20, 30],
    'bb_std': [1.5, 2.0, 2.5]
}

# 3. Konfiguracja walk-forward
walk_forward_config = WalkForwardConfig(
    train_size=60,  # 60 dni treningu
    test_size=30,   # 30 dni testu
    step=30,        # Krok 30 dni
    optimize_metric='net_profit'
)

# 4. Inicjalizacja testera walk-forward
tester = WalkForwardTester(
    strategy_class=BollingerBandsStrategy,
    param_grid=param_grid,
    symbol="EURUSD",
    timeframe="H1",
    start_date=datetime(2022, 1, 1),
    end_date=datetime(2022, 12, 31),
    walk_forward_config=walk_forward_config
)

# 5. Uruchomienie testu walk-forward
results = tester.run()

# 6. Analiza wyników
print(f"Liczba okien: {len(results['windows'])}")
print(f"Łączny zysk: {results['combined_metrics']['net_profit']:.2f}")

# 7. Parametry dla poszczególnych okien
for i, window in enumerate(results['windows']):
    print(f"Okno {i+1}: {window['params']}, zysk: {window['metrics']['net_profit']:.2f}")
```

## Integracja z interfejsem użytkownika

Moduł backtestingu został zintegrowany z interfejsem użytkownika (Streamlit) poprzez zakładkę "Backtesting" w głównym menu aplikacji. Interfejs umożliwia:

1. **Konfigurację backtestingu**:
   - Wybór instrumentu i timeframe'u
   - Określenie okresu backtestingu
   - Wybór strategii i ustawienie jej parametrów
   - Konfigurację zarządzania ryzykiem

2. **Wyświetlanie wyników**:
   - Podsumowanie metryk wydajności
   - Wykresy krzywej kapitału
   - Tabela transakcji

3. **Optymalizację parametrów**:
   - Wybór metody optymalizacji (grid search, random search, walk-forward)
   - Określenie zakresu parametrów do optymalizacji
   - Wizualizacja przestrzeni parametrów

4. **Generowanie raportów**:
   - Eksport wyników do plików HTML i Excel
   - Generowanie szczegółowych raportów z wykresami

## Przykłady

W katalogu `src/backtest/examples` znajdują się przykładowe skrypty demonstrujące różne aspekty modułu backtestingu:

- `backtest_example.py` - Podstawowy przykład uruchomienia backtestingu
- `strategy_backtest_example.py` - Przykłady użycia różnych strategii
- `position_management_example.py` - Demonstracja zaawansowanego zarządzania pozycjami
- `combined_strategy_example.py` - Przykład strategii kombinowanej (odwzorowanie generatora sygnałów)
- `advanced_reporting_example.py` - Generowanie zaawansowanych raportów i wizualizacji

Aby uruchomić przykład, przejdź do katalogu `src/backtest/examples` i wykonaj:

```bash
python backtest_example.py
```

## Rozszerzanie modułu

### Dodawanie nowej strategii

Aby dodać nową strategię, należy utworzyć klasę dziedziczącą po `TradingStrategy` i zaimplementować metodę `generate_signals`:

```python
from src.backtest.strategy import TradingStrategy
from src.backtest.strategy import StrategySignal, SignalType

class MyCustomStrategy(TradingStrategy):
    def __init__(self, param1=10, param2=20):
        super().__init__()
        self.param1 = param1
        self.param2 = param2
        self.name = "MyCustomStrategy"
    
    def generate_signals(self, data):
        signals = []
        # Logika generowania sygnałów na podstawie danych
        # ...
        return signals
```

### Dodawanie nowych metryk

Aby dodać nową metrykę, należy rozszerzyć funkcję `calculate_metrics` w module `backtest_metrics.py`:

```python
def calculate_metrics(backtest_result):
    # Istniejące metryki...
    
    # Nowa metryka
    my_new_metric = calculate_my_new_metric(backtest_result)
    
    metrics['my_new_metric'] = my_new_metric
    return metrics

def calculate_my_new_metric(backtest_result):
    # Implementacja obliczania nowej metryki
    # ...
    return result
```

## Znane problemy i ograniczenia

### Ostrzeżenia SettingWithCopyWarning z pandas

W silniku backtestingu (`backtest_engine.py`) mogą pojawić się ostrzeżenia `SettingWithCopyWarning` z biblioteki pandas podczas wykonywania testów. Te ostrzeżenia są związane z przypisywaniem wartości do kolumn w DataFrame, który może być fragmentem (slice) innego DataFrame. 

Przykład ostrzeżenia:
```
SettingWithCopyWarning: A value is trying to be set on a copy of a slice from a DataFrame.
Try using .loc[row_indexer,col_indexer] = value instead

See the caveats in the documentation: https://pandas.pydata.org/pandas-docs/stable/user_guide/indexing.html#returning-a-view-versus-a-copy
```

**Wpływ na działanie systemu:** Te ostrzeżenia nie wpływają na poprawność wyników backtestingu ani na funkcjonalność systemu. Są to jedynie informacje diagnostyczne z biblioteki pandas.

**Planowane rozwiązanie:** W przyszłych wersjach ostrzeżenia zostaną wyeliminowane przez użycie metody `.loc` do przypisywania wartości:
```python
self.market_data.loc[:, 'symbol'] = self.config.symbol
self.market_data.loc[:, 'timeframe'] = self.config.timeframe
```

zamiast obecnego:
```python
self.market_data['symbol'] = self.config.symbol
self.market_data['timeframe'] = self.config.timeframe
```

### Inne znane ograniczenia

1. **Wydajność dla małych timeframe'ów** - przetwarzanie danych dla timeframe'ów M1/M5 może być powolne dla długich okresów (>6 miesięcy)
2. **Symulacja spreadu** - system używa stałej wartości spreadu, co może nie odzwierciedlać dokładnie zmiennych warunków rynkowych
3. **Dostępność danych** - dla niektórych instrumentów dane historyczne mogą być niepełne lub niedostępne dla starszych okresów

---

Dokumentacja została wygenerowana: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} 

## Optymalizacja parametrów strategii

Moduł optymalizacji oferuje narzędzia do automatycznego wyszukiwania optymalnych parametrów dla strategii handlowych. Optymalizacji mogą podlegać:

1. Wagi wskaźników technicznych
2. Progi decyzyjne
3. Parametry techniczne wskaźników (okresy, mnożniki itp.)

### Korzystanie z optymalizatora parametrów

#### Z poziomu kodu Python:

```python
from backtest.optimize_generator import SignalGeneratorOptimizer
from datetime import datetime, timedelta

# Inicjalizacja optymalizatora
optimizer = SignalGeneratorOptimizer(
    symbols=["EURUSD", "GBPUSD"],
    timeframes=["H1", "H4"],
    optimization_days=90,
    evaluation_metric="sharpe_ratio"
)

# Optymalizacja wag wskaźników dla jednej pary
end_date = datetime.now()
start_date = end_date - timedelta(days=90)
results = optimizer.optimize_weights("EURUSD", "H1", start_date, end_date)

# Optymalizacja progów decyzyjnych
results = optimizer.optimize_thresholds("EURUSD", "H1", start_date, end_date)

# Optymalizacja parametrów technicznych
results = optimizer.optimize_technical_params("EURUSD", "H1", start_date, end_date)

# Pełna optymalizacja (wagi, progi, parametry techniczne)
results = optimizer.run_all_optimizations("EURUSD", "H1")

# Optymalizacja dla wszystkich par symbol-timeframe
all_results = optimizer.run_all_combinations()
```

#### Z linii komend:

Można również uruchomić optymalizację z linii komend za pomocą skryptu `optimize_run.py`:

```
# Pełna optymalizacja dla domyślnych par
python src/backtest/optimize_run.py

# Optymalizacja tylko wag dla określonych symboli i timeframe'ów
python src/backtest/optimize_run.py --weights --symbols EURUSD GBPUSD --timeframes H1 H4

# Optymalizacja progów decyzyjnych
python src/backtest/optimize_run.py --thresholds --symbols EURUSD --timeframes H1

# Optymalizacja parametrów technicznych z inną metryką oceny
python src/backtest/optimize_run.py --technical --metric profit_factor

# Optymalizacja dla pojedynczej pary symbol:timeframe
python src/backtest/optimize_run.py --single EURUSD:H1 --days 60
```

### Interpretacja wyników optymalizacji

Po zakończeniu optymalizacji generowany jest raport w katalogu `optimization_results`, zawierający:

1. **Tabela podsumowująca** - zawiera najlepsze wyniki dla każdej pary symbol-timeframe
2. **Szczegółowe wyniki** - dla każdej pary zawiera optymalne parametry i metryki
3. **Wnioski i rekomendacje** - miejsce na ręczne wpisy analityczne

Metryki używane do oceny strategii:
- **Net Profit** - całkowity zysk/strata
- **Win Rate** - procent zyskownych transakcji
- **Profit Factor** - stosunek zysków do strat
- **Sharpe Ratio** - stosunek średniego zwrotu do odchylenia standardowego
- **Calmar Ratio** - stosunek średniego rocznego zwrotu do maksymalnego drawdownu

### Uwagi dotyczące optymalizacji

1. **Overfitting** - należy uważać na nadmierne dopasowanie strategii do danych historycznych. Zaleca się testowanie zoptymalizowanych parametrów na różnych okresach i instrumentach.

2. **Koszt obliczeniowy** - pełna optymalizacja może być czasochłonna, szczególnie dla dużych przestrzeni parametrów. W takich przypadkach warto korzystać z opcji `--workers` do równoległego przetwarzania.

3. **Stabilność wyników** - zaleca się analizowanie nie tylko najlepszego zestawu parametrów, ale również kilku kolejnych najlepszych zestawów, aby ocenić stabilność strategii.

4. **Okresowa aktualizacja** - parametry strategii powinny być regularnie aktualizowane, aby uwzględniać zmieniające się warunki rynkowe. 