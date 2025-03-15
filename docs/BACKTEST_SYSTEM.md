# Dokumentacja Techniczna Systemu Backtestingu AgentMT5

**Autor:** Zespół AgentMT5  
**Data aktualizacji:** 14.04.2024  
**Wersja:** 1.0

## Spis treści

1. [Wprowadzenie](#wprowadzenie)
2. [Architektura systemu](#architektura-systemu)
3. [Główne komponenty](#główne-komponenty)
   - [HistoricalDataManager](#historicaldatamanager)
   - [BacktestEngine](#backtestengine)
   - [TradingStrategy](#tradingstrategy)
   - [PositionManager](#positionmanager)
   - [ParameterOptimizer](#parameteroptimizer)
   - [WalkForwardTester](#walkforwardtester)
4. [Integracja z UI](#integracja-z-ui)
5. [Strategie handlowe](#strategie-handlowe)
6. [Optymalizacja parametrów](#optymalizacja-parametrów)
7. [Testy wydajnościowe](#testy-wydajnościowe)
8. [Znane ograniczenia](#znane-ograniczenia)
9. [Instrukcje dla użytkownika](#instrukcje-dla-użytkownika)
10. [Plany rozwoju](#plany-rozwoju)
11. [Tryby backtestingu](#tryby-backtestingu)

## Wprowadzenie

System backtestingu AgentMT5 to zaawansowane narzędzie do testowania strategii handlowych na danych historycznych, umożliwiające ocenę skuteczności strategii przed zastosowaniem ich w rzeczywistym handlu. System oferuje:

- Testowanie na danych historycznych z różnych źródeł, w tym MT5
- Optymalizację parametrów strategii z wykorzystaniem różnych metod
- Walidację strategii z wykorzystaniem metody walk-forward testing
- Generowanie szczegółowych raportów z wynikami backtestów
- Integrację z interfejsem użytkownika dla łatwej konfiguracji i analizy wyników

System backtestingu jest kluczowym elementem platformy AgentMT5, umożliwiającym weryfikację strategii generowanych przez modele AI oraz optymalizację ich parametrów.

## Architektura systemu

System backtestingu AgentMT5 ma architekturę modułową, co pozwala na łatwą rozbudowę i dostosowywanie do różnych potrzeb. Główne komponenty systemu to:

```
┌───────────────────┐      ┌──────────────────┐      ┌─────────────────┐
│HistoricalDataMgr │─────▶│  BacktestEngine  │◀─────│TradingStrategy  │
└───────────────────┘      └──────────────────┘      └─────────────────┘
                                   ▲  │                       ▲
                                   │  ▼                       │
                           ┌─────────────────┐      ┌─────────────────┐
                           │PositionManager  │      │BacktestResult   │
                           └─────────────────┘      └─────────────────┘
                                                             │
                                                             ▼
                                                    ┌─────────────────┐
                                                    │BacktestMetrics  │
                                                    └─────────────────┘
```

## Główne komponenty

### HistoricalDataManager

Odpowiada za pobieranie, przetwarzanie i cachowanie danych historycznych. Kluczowe funkcje:

- Pobieranie danych z MT5 dla wybranych instrumentów i timeframe'ów
- Cachowanie danych w formatach zoptymalizowanych (Parquet)
- Walidacja i czyszczenie danych (obsługa missing values, duplikatów)
- Optymalizacja pamięci dla dużych zbiorów danych

**Przykładowe użycie:**

```python
from src.backtest.historical_data_manager import HistoricalDataManager

# Inicjalizacja menedżera danych
data_manager = HistoricalDataManager()

# Pobieranie danych historycznych
data = data_manager.get_historical_data(
    symbol="EURUSD",
    timeframe="M15",
    start_date=datetime(2023, 1, 1),
    end_date=datetime(2023, 12, 31),
    use_cache=True
)
```

### BacktestEngine

Centralny komponent wykonujący backtesting strategii. Kluczowe funkcje:

- Symulacja warunków rynkowych na danych historycznych
- Wykonywanie strategii handlowych na danych historycznych
- Zarządzanie pozycjami handlowymi w czasie symulacji
- Generowanie wyników i metryk wydajności strategii

**Przykładowe użycie:**

```python
from src.backtest.backtest_engine import BacktestEngine
from src.backtest.strategies.sma_strategy import SimpleMovingAverageStrategy

# Konfiguracja backtestingu
config = BacktestConfig(
    symbol="EURUSD",
    timeframe="M15",
    start_date=datetime(2023, 1, 1),
    end_date=datetime(2023, 12, 31),
    initial_balance=10000,
    lot_size=0.1,
    use_cache=True
)

# Inicjalizacja strategii
strategy = SimpleMovingAverageStrategy(fast_period=10, slow_period=30)

# Inicjalizacja silnika backtestingu
engine = BacktestEngine(config)

# Wykonanie backtestingu
result = engine.run(strategy)

# Wyświetlenie wyników
print(f"Profit: {result.metrics.net_profit}")
print(f"Max Drawdown: {result.metrics.max_drawdown}%")
print(f"Win Rate: {result.metrics.win_rate}%")
```

### TradingStrategy

Interfejs (klasa abstrakcyjna) definiujący strategię handlową. Kluczowe metody:

- `generate_signals` - generowanie sygnałów kupna/sprzedaży na podstawie danych
- `set_parameters` - ustawianie parametrów strategii
- `get_parameters` - pobieranie aktualnych parametrów strategii

**Przykład implementacji strategii:**

```python
from src.backtest.trading_strategy import TradingStrategy
import pandas as pd
import numpy as np

class SimpleMovingAverageStrategy(TradingStrategy):
    def __init__(self, fast_period=10, slow_period=30):
        super().__init__()
        self.name = "Simple Moving Average"
        self.fast_period = fast_period
        self.slow_period = slow_period
        
    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        # Kopie danych do przetwarzania
        df = data.copy()
        
        # Obliczanie średnich kroczących
        df["fast_ma"] = df["close"].rolling(window=self.fast_period).mean()
        df["slow_ma"] = df["close"].rolling(window=self.slow_period).mean()
        
        # Inicjalizacja kolumny sygnałów
        df["signal"] = 0
        
        # Generowanie sygnałów
        df.loc[df["fast_ma"] > df["slow_ma"], "signal"] = 1  # Sygnał kupna
        df.loc[df["fast_ma"] < df["slow_ma"], "signal"] = -1  # Sygnał sprzedaży
        
        return df
    
    def set_parameters(self, parameters: dict):
        if "fast_period" in parameters:
            self.fast_period = parameters["fast_period"]
        if "slow_period" in parameters:
            self.slow_period = parameters["slow_period"]
    
    def get_parameters(self) -> dict:
        return {
            "fast_period": self.fast_period,
            "slow_period": self.slow_period
        }
```

### PositionManager

Zarządza pozycjami handlowymi podczas backtestingu. Kluczowe funkcje:

- Otwieranie i zamykanie pozycji na podstawie sygnałów
- Zarządzanie stop loss i take profit
- Obsługa mechanizmów trailing stop, breakeven
- Zarządzanie ryzykiem zgodnie z ustawieniami

**Przykładowe użycie:**

```python
from src.backtest.position_manager import PositionManager

# Inicjalizacja menedżera pozycji
position_manager = PositionManager(
    initial_balance=10000,
    risk_per_trade=0.02,  # 2% ryzyka na transakcję
    use_trailing_stop=True,
    trailing_stop_pips=20,
    use_breakeven=True,
    breakeven_pips=15
)

# Symulowane otwieranie pozycji
position_id = position_manager.open_position(
    symbol="EURUSD",
    direction="BUY",
    lot_size=0.1,
    open_price=1.0650,
    sl_price=1.0600,
    tp_price=1.0750,
    timestamp=datetime(2023, 2, 15, 10, 30)
)

# Symulowane aktualizowanie pozycji
position_manager.update_positions(
    current_price=1.0670,
    timestamp=datetime(2023, 2, 15, 11, 30)
)

# Symulowane zamykanie pozycji
position_manager.close_position(
    position_id=position_id,
    close_price=1.0700,
    timestamp=datetime(2023, 2, 15, 14, 30)
)
```

### ParameterOptimizer

Odpowiada za optymalizację parametrów strategii. Kluczowe funkcje:

- Przeszukiwanie przestrzeni parametrów (grid search, random search)
- Równoległe wykonywanie backtestów dla różnych kombinacji parametrów
- Walidacja krzyżowa do zapobiegania przeuczeniu
- Raportowanie najlepszych zestawów parametrów

**Przykładowe użycie:**

```python
from src.backtest.parameter_optimizer import ParameterOptimizer
from src.backtest.strategies.sma_strategy import SimpleMovingAverageStrategy

# Definicja przestrzeni parametrów
parameter_space = {
    "fast_period": range(5, 21, 5),  # [5, 10, 15, 20]
    "slow_period": range(20, 101, 20)  # [20, 40, 60, 80, 100]
}

# Konfiguracja backtestingu
config = BacktestConfig(
    symbol="EURUSD",
    timeframe="M15",
    start_date=datetime(2023, 1, 1),
    end_date=datetime(2023, 12, 31),
    initial_balance=10000,
    lot_size=0.1,
    use_cache=True
)

# Inicjalizacja strategii i optymalizatora
strategy = SimpleMovingAverageStrategy()
optimizer = ParameterOptimizer(
    strategy=strategy,
    config=config,
    parameter_space=parameter_space,
    metric="net_profit",  # Metryka optymalizacji
    max_workers=4  # Liczba równoległych wątków
)

# Uruchomienie optymalizacji
results = optimizer.optimize()

# Wyświetlenie najlepszych parametrów
best_params = results["best_parameters"]
print(f"Najlepsze parametry: {best_params}")
print(f"Profit: {results['best_result']}")
```

### WalkForwardTester

Implementuje metodologię walk-forward testingu. Kluczowe funkcje:

- Dzielenie danych na okresy in-sample i out-of-sample
- Optymalizacja parametrów na danych in-sample
- Walidacja na danych out-of-sample
- Agregacja wyników z wielu okresów testowych

**Przykładowe użycie:**

```python
from src.backtest.walk_forward_tester import WalkForwardTester
from src.backtest.strategies.sma_strategy import SimpleMovingAverageStrategy

# Definicja przestrzeni parametrów
parameter_space = {
    "fast_period": range(5, 21, 5),
    "slow_period": range(20, 101, 20)
}

# Konfiguracja backtestingu
config = BacktestConfig(
    symbol="EURUSD",
    timeframe="M15",
    start_date=datetime(2022, 1, 1),
    end_date=datetime(2023, 12, 31),
    initial_balance=10000,
    lot_size=0.1,
    use_cache=True
)

# Inicjalizacja strategii i testera walk-forward
strategy = SimpleMovingAverageStrategy()
wf_tester = WalkForwardTester(
    strategy=strategy,
    config=config,
    parameter_space=parameter_space,
    window_size=180,  # dni
    step_size=90,     # dni
    train_size=0.7,   # 70% danych to in-sample
    max_workers=4
)

# Uruchomienie walk-forward testingu
results = wf_tester.run()

# Wyświetlenie wyników
print(f"Średni profit: {results['average_profit']}")
print(f"Średni drawdown: {results['average_drawdown']}%")
print(f"Robustność: {results['robustness_score']}")
```

## Integracja z UI

System backtestingu jest w pełni zintegrowany z interfejsem użytkownika AgentMT5 poprzez zakładkę "Backtesting". Integracja obejmuje:

### Konfiguracja backtestów

- Wybór instrumentu handlowego i timeframe'u
- Wybór strategii i konfiguracja jej parametrów
- Ustawienia kapitału początkowego i zarządzania ryzykiem
- Wybór zakresu dat dla backtestingu

### Widok wyników

- Tabela wyników z kluczowymi metrykami (profit, drawdown, win rate)
- Interaktywne wykresy wydajności strategii
- Szczegółowa lista transakcji z możliwością filtrowania
- Eksport wyników do CSV/Excel

### Optymalizacja parametrów

- Konfiguracja przestrzeni parametrów
- Wybór metody optymalizacji i metryki
- Wizualizacja wyników dla różnych kombinacji parametrów
- Walk-forward testing dla walidacji strategii

### Dokumentacja

- Podręcznik użytkownika z instrukcjami krok po kroku
- Opisy dostępnych strategii i ich parametrów
- Wyjaśnienia metod optymalizacji i metryk
- Best practices dla przeprowadzania backtestów

## Strategie handlowe

System backtestingu AgentMT5 wspiera różne strategie handlowe, w tym:

### Simple Moving Average (SMA)

Strategia oparta na przecięciach szybkiej i wolnej średniej kroczącej.

**Parametry:**
- `fast_period` - okres szybszej średniej kroczącej
- `slow_period` - okres wolniejszej średniej kroczącej

### Relative Strength Index (RSI)

Strategia oparta na wskaźniku RSI, generująca sygnały na podstawie poziomów wykupienia i wyprzedania.

**Parametry:**
- `rsi_period` - okres RSI
- `overbought_level` - poziom wykupienia (domyślnie 70)
- `oversold_level` - poziom wyprzedania (domyślnie 30)

### Bollinger Bands

Strategia wykorzystująca wstęgi Bollingera, generująca sygnały na podstawie przebić górnej i dolnej wstęgi.

**Parametry:**
- `bb_period` - okres średniej kroczącej
- `bb_std` - liczba odchyleń standardowych (domyślnie 2)

### MACD

Strategia oparta na wskaźniku MACD (Moving Average Convergence Divergence).

**Parametry:**
- `fast_period` - okres szybkiego EMA
- `slow_period` - okres wolnego EMA
- `signal_period` - okres linii sygnałowej

### Combined Indicators

Strategia łącząca różne wskaźniki techniczne, odwzorowująca działanie głównego generatora sygnałów AgentMT5.

**Parametry:**
- `rsi_period` - okres RSI
- `ma_period` - okres średniej kroczącej
- `bb_period` - okres wstęg Bollingera
- `macd_fast` - szybki okres MACD
- `macd_slow` - wolny okres MACD
- `macd_signal` - okres sygnału MACD
- `rsi_weight` - waga sygnału RSI
- `ma_weight` - waga sygnału MA
- `bb_weight` - waga sygnału Bollinger Bands
- `macd_weight` - waga sygnału MACD

## Optymalizacja parametrów

System backtestingu AgentMT5
oferuje różne metody optymalizacji parametrów, w tym:

### Grid Search

Systematyczne przeszukiwanie całej przestrzeni parametrów, testowanie wszystkich możliwych kombinacji.

**Zalety:**
- Dokładne znalezienie globalnego optimum
- Przejrzystość i łatwość interpretacji wyników

**Wady:**
- Wysoka złożoność obliczeniowa dla dużych przestrzeni parametrów
- Długi czas optymalizacji dla wielu parametrów

### Random Search

Losowe próbkowanie kombinacji parametrów z określonej przestrzeni.

**Zalety:**
- Szybsze działanie niż grid search
- Dobra eksploracja przestrzeni parametrów

**Wady:**
- Może nie znaleźć globalnego optimum
- Wymaga większej liczby iteracji dla dużych przestrzeni

### Walk-Forward Optimization

Łączy optymalizację parametrów z walidacją na out-of-sample data.

**Zalety:**
- Realistyczna ocena przyszłej wydajności strategii
- Redukcja ryzyka przeuczenia
- Testowanie stabilności parametrów w czasie

**Wady:**
- Bardziej złożona procedura
- Wymaga więcej danych historycznych

### Metryki optymalizacji

System wspiera optymalizację pod kątem różnych metryk, w tym:

- **Net Profit** - całkowity zysk netto
- **Sharpe Ratio** - stosunek zysku do zmienności
- **Max Drawdown** - maksymalne obsunięcie kapitału
- **Win Rate** - procent zyskownych transakcji
- **Profit Factor** - stosunek zysków do strat
- **Expected Payoff** - średni zysk na transakcję

## Testy wydajnościowe

System backtestingu AgentMT5 przeszedł szczegółowe testy wydajnościowe, które potwierdziły jego zdolność do efektywnego przetwarzania dużych zbiorów danych. Wyniki testów:

### Test dużego zbioru danych M1

- Przetworzono 5000 świec M1
- Osiągnięto wydajność ponad 55 świec/sekundę
- Test zakończony sukcesem, powyżej progu 50 świec/sekundę

### Test zużycia pamięci podczas optymalizacji

- Zmierzono przyrost pamięci podczas optymalizacji z wieloma kombinacjami
- Przyrost pamięci wyniósł tylko ~12 MB
- Test zakończony sukcesem, znacznie poniżej limitu 200 MB

### Test optymalizacji wielu kombinacji

- Testowano 20 kombinacji parametrów
- Średni czas wykonania wyniósł ~50 sekund na kombinację
- Test zakończony sukcesem, poniżej limitu 70 sekund

## Znane ograniczenia

System backtestingu AgentMT5 ma pewne ograniczenia, o których należy pamiętać:

1. **Wydajność dla dużych zbiorów danych**
   - Przetwarzanie danych M1 za okres dłuższy niż 1 rok może powodować znaczące obciążenie pamięci
   - Zalecane jest stosowanie cache'owania danych i ograniczanie zakresu dat dla najmniejszych timeframe'ów

2. **Dokładność symulacji**
   - Backtesting nie uwzględnia poślizgów cenowych (slippage)
   - Nie symuluje dokładnie głębokości rynku i płynności
   - Wyniki backtestingu mogą różnić się od rzeczywistych wyników handlowych

3. **Ostrzeżenia pandas**
   - System może generować ostrzeżenia `SettingWithCopyWarning` w niektórych miejscach
   - Nie wpływają one na poprawność wyników, ale wskazują na potencjalne miejsca optymalizacji kodu

4. **Ograniczenia optymalizacji**
   - Grid search może być bardzo czasochłonny dla dużych przestrzeni parametrów
   - Zalecane jest ograniczenie liczby kombinacji do rozsądnej wartości (<1000)

## Instrukcje dla użytkownika

### Jak przeprowadzić backtest

1. Przejdź do zakładki "Backtesting" w interfejsie AgentMT5
2. W sekcji "Konfiguracja" wybierz:
   - Instrument (np. EURUSD)
   - Timeframe (np. M15)
   - Zakres dat (od-do)
   - Strategię handlową
   - Parametry strategii
   - Kapitał początkowy i lot size
3. Kliknij przycisk "Uruchom backtest"
4. Przejdź do zakładki "Wyniki", aby zobaczyć szczegółowe wyniki backtestingu

### Jak przeprowadzić optymalizację parametrów

1. Przejdź do zakładki "Backtesting" w interfejsie AgentMT5
2. W sekcji "Konfiguracja" wybierz instrument, timeframe i zakres dat
3. Wybierz strategię handlową
4. Przejdź do zakładki "Optymalizacja"
5. Dla każdego parametru określ zakres wartości (min, max, krok)
6. Wybierz metodę optymalizacji (Grid Search, Random Search, Walk-Forward)
7. Wybierz metrykę optymalizacji (np. Net Profit, Sharpe Ratio)
8. Kliknij przycisk "Uruchom optymalizację"
9. Przejdź do wyników optymalizacji, aby zobaczyć najlepsze zestawy parametrów

### Best practices

1. **Wybór zakresu dat**
   - Używaj wystarczająco długiego okresu, aby uwzględnić różne warunki rynkowe
   - Zawsze weryfikuj strategię na danych out-of-sample

2. **Optymalizacja parametrów**
   - Unikaj nadmiernej optymalizacji, która może prowadzić do przeuczenia
   - Zawsze weryfikuj zoptymalizowane parametry na danych out-of-sample
   - Stosuj walk-forward testing dla bardziej realistycznej oceny

3. **Zarządzanie ryzykiem**
   - Ustawiaj realistyczne poziomy Stop Loss i Take Profit
   - Ogranicz wielkość pozycji do rozsądnego % kapitału
   - Testuj strategie z różnymi poziomami zarządzania ryzykiem

4. **Interpretacja wyników**
   - Nie kieruj się wyłącznie zyskiem - analizuj również inne metryki
   - Zwracaj uwagę na stabilność wyników i drawdown
   - Porównuj wyniki z różnymi benchmarkami

## Plany rozwoju

Plany rozwoju systemu backtestingu AgentMT5 obejmują:

1. **Optymalizacja wydajności**
   - Dalsze usprawnienia dla pracy z dużymi zbiorami danych
   - Refaktoryzacja kodu celem eliminacji ostrzeżeń pandas
   - Implementacja bardziej efektywnych algorytmów optymalizacji

2. **Rozszerzenie funkcjonalności**
   - Dodanie nowych strategii handlowych
   - Implementacja zaawansowanych metod optymalizacji (np. algorytmy genetyczne)
   - Dodanie zaawansowanych metryk oceny strategii

3. **Integracje**
   - Integracja z CI/CD dla automatycznego testowania strategii
   - Automatyczne porównywanie wyników strategii z poprzednimi wersjami
   - Możliwość bezpośredniego wdrażania zoptymalizowanych strategii do systemu handlowego

4. **Ulepszone raportowanie**
   - Dodanie nowych typów wykresów i wizualizacji
   - Rozszerzenie opcji eksportu raportów
   - Implementacja alertów i powiadomień o wydajności strategii

## 7. Tryby backtestingu

System backtestingu AgentMT5 oferuje dwa tryby pracy, dostosowane do różnych poziomów zaawansowania użytkowników:

### 7.1. Tryb automatyczny (dla początkujących)

Tryb automatyczny został zaprojektowany z myślą o użytkownikach, którzy dopiero zaczynają przygodę z backtestingiem strategii lub chcą szybko przetestować podejście handlowe bez zagłębiania się w szczegóły techniczne.

#### Kluczowe cechy trybu automatycznego:

- **Uproszczony interfejs** - minimalna liczba parametrów do skonfigurowania
- **Automatyczna analiza rynku** - system analizuje dane historyczne i wykrywa warunki rynkowe (trend, konsolidacja, zmienność)
- **Dobór optymalnej strategii** - na podstawie warunków rynkowych system rekomenduje najbardziej odpowiednią strategię
- **Dostosowanie parametrów do profilu ryzyka** - parametry strategii są automatycznie dostosowywane na podstawie wybranego profilu ryzyka (Konserwatywny, Zrównoważony, Agresywny)
- **Możliwość przejścia do trybu zaawansowanego** - po wykonaniu automatycznego backtestu istnieje możliwość przejścia do trybu zaawansowanego z zachowaniem dobranych parametrów

#### Jak działa analiza warunków rynkowych:

1. **Analiza trendu** - wykorzystuje wskaźniki ADX, +DI, -DI oraz wzajemną relację średnich kroczących dla określenia siły i kierunku trendu
2. **Analiza zmienności** - wykorzystuje ATR (Average True Range) oraz zmienność historyczną (odchylenie standardowe zwrotów) do określenia poziomu zmienności rynku
3. **Analiza konsolidacji** - wykorzystuje szerokość pasm Bollingera oraz czas przebywania RSI w okolicy wartości neutralnych do określenia, czy rynek jest w konsolidacji

#### Automatyczny dobór strategii:

| Warunki rynkowe | Rekomendowana strategia | Uzasadnienie |
| --- | --- | --- |
| Silny trend wzrostowy/spadkowy | SimpleMovingAverage | Najlepiej sprawdza się przy czystych trendach |
| Umiarkowany trend | SimpleMovingAverage / MACD | Dobra równowaga między podążaniem za trendem a unikaniem szumu |
| Konsolidacja (rynek w zakresie) | BollingerBands | Efektywnie wykorzystuje odbicia od krawędzi zakresu |
| Wysoka zmienność | RSI | Pomaga unikać fałszywych sygnałów w zmiennych warunkach |
| Niska zmienność | MACD | Dobrze radzi sobie z wykrywaniem niewielkich zmian impulsu cenowego |

### 7.2. Tryb zaawansowany (dla ekspertów)

Tryb zaawansowany daje pełną kontrolę nad wszystkimi aspektami backtestingu, umożliwiając doświadczonym traderom i badaczom szczegółowe dostrojenie strategii i parametrów testów.

#### Kluczowe cechy trybu zaawansowanego:

- **Pełna kontrola nad parametrami strategii** - szczegółowa konfiguracja wszystkich parametrów technicznych strategii
- **Dogłębna analiza wyników** - rozbudowane metryki i wizualizacje wyników
- **Możliwość optymalizacji parametrów** - trzy metody optymalizacji (Grid Search, Random Search, Walk Forward)
- **Generowanie raportów** - eksport wyników do różnych formatów (HTML, Excel)
- **Konfiguracja zarządzania ryzykiem** - szczegółowe ustawienia kapitału początkowego i ryzyka na transakcję

#### Dostępne funkcjonalności:

1. **Konfigurator backtestingu** - ustawienia instrumentu, timeframe'u, strategii, zakresu dat, kapitału, ryzyka
2. **Parametry strategii** - szczegółowa konfiguracja parametrów technicznych dla wybranej strategii
3. **Wyniki i raporty** - szczegółowe wyniki, metryki, wykresy, historia transakcji, eksport danych
4. **Optymalizacja parametrów** - narzędzia do znajdowania optymalnych parametrów dla wybranej strategii

### 7.3. Przepływ pracy z systemem backtestingu

Oto zalecany przepływ pracy z systemem backtestingu AgentMT5:

1. **Dla nowych użytkowników**:
   - Rozpocznij od trybu automatycznego
   - Przetestuj różne instrumenty i okresy
   - Sprawdź wyniki dla różnych profili ryzyka
   - Po znalezieniu obiecującej konfiguracji, przejdź do trybu zaawansowanego z zachowanymi parametrami

2. **Dla doświadczonych użytkowników**:
   - Zacznij bezpośrednio w trybie zaawansowanym
   - Skonfiguruj parametry strategii zgodnie z własną wiedzą i doświadczeniem
   - Przeprowadź optymalizację dla znalezienia najlepszych parametrów
   - Wykonaj testy walk-forward dla oceny odporności strategii