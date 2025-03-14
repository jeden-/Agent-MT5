# Dokumentacja Techniczna AgentMT5

## 1. Wstęp

AgentMT5 to zaawansowany system automatycznego handlu wykorzystujący sztuczną inteligencję do analizy rynku i podejmowania decyzji tradingowych. System integruje zaawansowane modele AI (Claude, Grok, DeepSeek) z platformą MetaTrader 5, zapewniając autonomiczne zarządzanie pozycjami przy zachowaniu ścisłej kontroli ryzyka.

### 1.1 Cel projektu

Głównym celem projektu jest stworzenie systemu, który:
- Wykorzystuje zaawansowane algorytmy AI do analizy rynku finansowego
- Automatycznie podejmuje decyzje tradingowe oparte na analizie danych
- Zarządza ryzykiem i pozycjami w sposób autonomiczny
- Dąży do podwojenia powierzonego kapitału w możliwie najkrótszym czasie

## 2. Architektura systemu

### 2.1 Schemat blokowy systemu

System składa się z następujących głównych komponentów:

```
┌───────────────────┐    ┌───────────────────┐    ┌───────────────────┐
│   MetaTrader 5    │◄───┤   MT5 Bridge      │◄───┤  Agent Controller │
│   (Terminal)      │    │   (Komunikacja)    │    │  (Logika decyzyjna)│
└───────────────────┘    └───────────────────┘    └─────────┬─────────┘
                                                            │
                          ┌──────────────────────────────────┴───────────────────┐
                          │                                                      │
                  ┌───────────────────┐                              ┌───────────────────┐
                  │  Position Manager │                              │   Risk Manager    │
                  │ (Zarządzanie     │                              │ (Zarządzanie      │
                  │  pozycjami)      │                              │  ryzykiem)        │
                  └───────────────────┘                              └───────────────────┘
                          │                                                      │
                          └──────────────────────────────────┬───────────────────┘
                                                            │
                                                ┌───────────────────┐
                                                │    AI Models      │
                                                │   (Claude, Grok,  │
                                                │    DeepSeek)      │
                                                └───────────────────┘
```

### 2.2 Struktura katalogów projektu

```
AgentMT5/
├── src/                      # Kod źródłowy
│   ├── ai_models/            # Modele AI
│   │   ├── ai_router.py      # Router zapytań do różnych modeli AI
│   │   ├── claude_api.py     # Integracja z Claude API
│   │   ├── grok_api.py       # Integracja z Grok API
│   │   └── deepseek_api.py   # Integracja z DeepSeek API
│   ├── database/             # Baza danych
│   ├── monitoring/           # Moduły monitorowania
│   ├── mt5_bridge/           # Most komunikacyjny z MT5
│   │   ├── mt5_server.py     # Serwer komunikacyjny
│   │   └── server.py         # Serwer HTTP (FastAPI)
│   ├── mt5_ea/               # Expert Advisor
│   ├── position_management/  # Zarządzanie pozycjami
│   │   ├── position_manager.py # Zarządzanie pozycjami
│   │   ├── db_manager.py     # Zarządzanie bazą danych pozycji
│   │   └── mt5_api_client.py # Klient API MT5
│   ├── risk_management/      # Zarządzanie ryzykiem
│   │   ├── risk_manager.py   # Zarządzanie ryzykiem
│   │   ├── stop_loss_manager.py # Zarządzanie stop-lossami
│   │   ├── exposure_tracker.py # Śledzenie ekspozycji
│   │   └── order_validator.py # Walidacja zleceń
│   ├── ui/                   # Interfejs użytkownika
│   └── utils/                # Narzędzia pomocnicze
│   ├── agent_controller.py   # Główny kontroler agenta
│   └── trading_integration.py # Integracja z handlem
├── docs/                     # Dokumentacja
├── scripts/                  # Skrypty pomocnicze
├── tests/                    # Testy jednostkowe i integracyjne
├── config/                   # Pliki konfiguracyjne
└── .env                      # Zmienne środowiskowe
```

## 3. Komponenty systemu

### 3.1 MetaTrader 5 Bridge (src/mt5_bridge/)

#### 3.1.1 MT5Server (mt5_server.py)

Moduł odpowiedzialny za komunikację z platformą MetaTrader 5. Wykorzystuje bibliotekę `MetaTrader5` do bezpośredniego łączenia się z terminalem MT5.

**Kluczowe funkcje:**
- Pobieranie danych rynkowych
- Pobieranie informacji o koncie
- Pobieranie danych o otwartych pozycjach
- Pobieranie historii transakcji
- Zarządzanie połączeniem z MT5

#### 3.1.2 Serwer HTTP (server.py)

Serwer HTTP wykorzystujący FastAPI do udostępnienia REST API dla komunikacji z interfejsem użytkownika oraz EA (Expert Advisor).

**Główne endpointy:**
- `/ping` - sprawdzenie połączenia (GET/POST)
- `/market/data` - obsługa danych rynkowych (GET/POST)
- `/position/update` - aktualizacja informacji o pozycjach (POST)
- `/mt5/account` - informacje o koncie MT5 (GET)
- `/account/info` - informacje o koncie (GET) - przestarzały, użyj `/mt5/account`
- `/commands` - pobieranie komend do wykonania przez EA (GET)
- `/agent/start`, `/agent/stop`, `/agent/status` - zarządzanie agentem (POST/GET)
- `/agent/config`, `/agent/config/history`, `/agent/config/restore` - zarządzanie konfiguracją agenta (POST/GET)
- `/monitoring/*` - endpointy monitoringu (GET)

#### 3.1.3 Endpointy API

##### Endpoint `/mt5/account`

Endpoint służy do pobierania informacji o koncie MetaTrader 5.

**Metoda:** `GET`

**URL:** `http://localhost:8000/mt5/account`

**Parametry:** Brak

**Odpowiedź (powodzenie):**
```json
{
  "status": "ok",
  "account_info": {
    "login": 12345678,
    "balance": 10000.0,
    "equity": 10250.0,
    "margin": 2000.0,
    "free_margin": 8250.0,
    "margin_level": 512.5,
    "leverage": 100,
    "currency": "USD"
  },
  "timestamp": "2025-03-12T03:00:00.000Z"
}
```

**Uwaga:** W przypadku błędu połączenia z MT5, system zwraca przykładowe dane o koncie z flagą `status: "ok"` dla zachowania kompatybilności z istniejącymi klientami.

##### Endpoint `/market/data`

Endpoint służy do obsługi danych rynkowych.

**Metoda:** `POST` (dla aktualizacji danych), `GET` (dla pobrania danych)

**URL:** `http://localhost:8000/market/data`

**Parametry (POST):**
```json
{
  "ea_id": "EA12345",
  "symbol": "EURUSD.pro",
  "bid": 1.0750,
  "ask": 1.0752,
  "last": 1.0751,
  "volume": 100,
  "time": "2025-03-12T03:00:00.000Z",
  "timeframe": "M1",
  "data": {
    "additional_info": "..."
  }
}
```

**Odpowiedź (GET):**
```json
{
  "status": "ok",
  "market_data": {
    "EURUSD.pro": {
      "bid": 1.0750,
      "ask": 1.0752,
      "last": 1.0751,
      "time": "2025-03-12T03:00:00.000Z"
    },
    "GBPUSD.pro": {
      "bid": 1.2650,
      "ask": 1.2652,
      "last": 1.2651,
      "time": "2025-03-12T03:00:00.000Z"
    }
  },
  "timestamp": "2025-03-12T03:00:00.000Z"
}
```

##### Endpoint `/position/update`

Endpoint służy do aktualizacji informacji o pozycjach.

**Metoda:** `POST`

**URL:** `http://localhost:8000/position/update`

**Parametry:**
```json
{
  "ea_id": "EA12345",
  "positions": [
    {
      "ticket": 123456789,
      "symbol": "EURUSD.pro",
      "type": "buy",
      "volume": 0.1,
      "open_price": 1.0750,
      "sl": 1.0700,
      "tp": 1.0800,
      "profit": 25.0,
      "comment": "Agent trade"
    }
  ]
}
```

**Odpowiedź:**
```json
{
  "status": "ok",
  "message": "Positions updated",
  "timestamp": "2025-03-12T03:00:00.000Z"
}
```

### 3.2 Agent Controller (agent_controller.py)

Główny moduł zarządzający cyklem życia agenta handlowego, odpowiedzialny za koordynację wszystkich komponentów systemu.

**Kluczowe funkcje:**
- Inicjalizacja komponentów
- Uruchamianie/zatrzymywanie/restartowanie agenta
- Zarządzanie trybami pracy agenta (obserwacja, półautomatyczny, automatyczny)
- Koordynacja procesów analizy rynku i podejmowania decyzji
- Zarządzanie konfiguracją agenta

**Tryby pracy agenta:**
- `OBSERVATION` - tylko analiza rynku, bez podejmowania decyzji
- `SEMI_AUTOMATIC` - propozycje transakcji wymagają zatwierdzenia
- `AUTOMATIC` - pełna automatyzacja decyzji handlowych

### 3.3 Position Management (src/position_management/)

#### 3.3.1 PositionManager (position_manager.py)

Moduł odpowiedzialny za zarządzanie cyklem życia pozycji handlowych.

**Kluczowe funkcje:**
- Otwieranie nowych pozycji
- Modyfikacja istniejących pozycji
- Zamykanie pozycji
- Śledzenie statusu pozycji
- Implementacja strategii zarządzania pozycjami (trailing stop, break-even, itp.)

#### 3.3.2 DB Manager (db_manager.py)

Moduł odpowiedzialny za zarządzanie bazą danych pozycji.

**Kluczowe funkcje:**
- Zapisywanie informacji o pozycjach
- Aktualizacja statusu pozycji
- Przechowywanie historii transakcji
- Generowanie raportów

### 3.4 Risk Management (src/risk_management/)

#### 3.4.1 RiskManager (risk_manager.py)

Moduł odpowiedzialny za zarządzanie ryzykiem handlowym.

**Kluczowe funkcje:**
- Weryfikacja zgodności z limitami alokacji
- Kontrola ekspozycji na instrumenty
- Obliczanie optymalnej wielkości pozycji
- Walidacja zleceń pod kątem ryzyka

#### 3.4.2 StopLossManager (stop_loss_manager.py)

Moduł odpowiedzialny za zarządzanie stop-lossami.

**Kluczowe funkcje:**
- Obliczanie optymalnych poziomów stop-loss
- Implementacja strategii trailing stop
- Zarządzanie break-even

#### 3.4.3 ExposureTracker (exposure_tracker.py)

Moduł śledzący ekspozycję na różne instrumenty i rynki.

**Kluczowe funkcje:**
- Monitorowanie ekspozycji na instrumenty
- Analiza korelacji między pozycjami
- Raportowanie łącznej ekspozycji

### 3.5 AI Models (src/ai_models/)

#### 3.5.1 AI Router (ai_router.py)

Moduł odpowiedzialny za routing zapytań do różnych modeli AI.

**Kluczowe funkcje:**
- Wybór najlepszego modelu AI dla danego zapytania
- Zarządzanie limitami API
- Monitoring wydajności modeli
- Obsługa błędów i fallback

#### 3.5.2 Integracje z modelami AI

- **ClaudeAPI** (claude_api.py) - integracja z API Claude
- **GrokAPI** (grok_api.py) - integracja z API Grok
- **DeepSeekAPI** (deepseek_api.py) - integracja z API DeepSeek

**Wspólne funkcje:**
- Przygotowanie zapytań
- Parsowanie odpowiedzi
- Obsługa błędów
- Monitorowanie limitów i kosztów

### 3.6 Generator sygnałów (src/analysis/signal_generator.py)

Moduł odpowiedzialny za analizę danych rynkowych i generowanie sygnałów handlowych na podstawie różnych źródeł i strategii analitycznych.

#### 3.6.1 Główne komponenty

- `SignalGenerator`: Klasa główna generująca sygnały handlowe na podstawie analizy technicznej, fundamentalnej i AI.
- `SignalType`: Enum definiujący typy sygnałów (BUY, SELL, NEUTRAL).
- `SignalStrength`: Enum określający siłę sygnału (WEAK, MODERATE, STRONG).
- `SignalSource`: Enum identyfikujący źródło sygnału (TECHNICAL, FUNDAMENTAL, AI_BASED, COMBINED).

#### 3.6.2 Kluczowe funkcje

- `generate_signal`: Główna metoda generująca sygnały handlowe na podstawie aktualnych danych rynkowych.
- `generate_signal_from_data`: Metoda generująca sygnały na podstawie dostarczonych danych historycznych (używana głównie w backtestingu).
- `_analyze_technical`: Przeprowadza analizę techniczną na podstawie wskaźników i formacji cenowych.
- `_analyze_fundamental`: Analizuje dane fundamentalne i wydarzenia ekonomiczne.
- `_analyze_ai_based`: Wykorzystuje modele AI do przewidywania ruchu cen.
- `_combine_signals`: Łączy sygnały z różnych źródeł w jeden spójny sygnał końcowy.
- `_select_model_name`: Wybiera odpowiedni model AI na podstawie pewności sygnału i innych parametrów.

#### 3.6.3 Proces generowania sygnałów

1. **Pobieranie danych**: Uzyskanie aktualnych lub historycznych danych rynkowych.
2. **Analiza techniczna**: Obliczanie wskaźników technicznych i identyfikacja formacji.
3. **Analiza fundamentalna**: Ocena wpływu danych ekonomicznych i wydarzeń rynkowych.
4. **Analiza AI**: Wykorzystanie modeli uczenia maszynowego do prognozowania ruchów ceny.
5. **Integracja wyników**: Połączenie sygnałów z różnych źródeł z uwzględnieniem ich wagi.
6. **Filtrowanie sygnałów**: Eliminacja słabych lub sprzecznych sygnałów.
7. **Generowanie sygnału końcowego**: Utworzenie sygnału z określeniem typu, siły i pewności.
8. **Zapisanie w bazie danych**: Archiwizacja sygnału do celów analizy i oceny.

#### 3.6.4 Integracja z backtestingiem

Generator sygnałów jest kluczowym komponentem w systemie backtestingu, gdzie metoda `generate_signal_from_data` analizuje segmenty danych historycznych, symulując proces generowania sygnałów w czasie rzeczywistym. Metoda ta przyjmuje dane w formacie DataFrame i zwraca sygnał handlowy, który jest następnie wykorzystywany przez silnik backtestingu do symulacji decyzji handlowych.

### 3.7 System oceny jakości sygnałów (src/analysis/signal_evaluator.py)

Moduł odpowiedzialny za śledzenie, analizowanie i ocenę jakości generowanych sygnałów handlowych. System ten stanowi kluczowy element pętli sprzężenia zwrotnego, umożliwiając ciągłe doskonalenie algorytmów generowania sygnałów.

#### 3.7.1 Główne komponenty

- `SignalEvaluator`: Klasa odpowiedzialna za ocenę jakości sygnałów handlowych.
- `SignalEvaluationRepository`: Repozytorium do przechowywania i pobierania ocen sygnałów.

#### 3.7.2 Kluczowe funkcje

- `register_new_signal`: Rejestruje nowy sygnał handlowy do oceny.
- `update_evaluation`: Aktualizuje ocenę sygnału na podstawie aktualnej ceny rynkowej.
- `check_open_evaluations`: Sprawdza wszystkie otwarte oceny i aktualizuje je.
- `get_signal_performance`: Pobiera statystyki wydajności sygnałów.
- `get_performance_by_confidence`: Analizuje wydajność sygnałów według poziomów pewności.
- `get_performance_by_timeframe`: Analizuje wydajność sygnałów według ram czasowych.

#### 3.7.3 Proces oceny sygnałów

1. **Rejestracja nowych sygnałów**: Każdy nowo wygenerowany sygnał handlowy jest rejestrowany w systemie oceny.
2. **Regularne aktualizacje**: System regularnie sprawdza status zarejestrowanych sygnałów, monitorując czy cena rynkowa osiągnęła poziom take-profit lub stop-loss.
3. **Zamknięcie oceny**: Po osiągnięciu take-profit, stop-loss lub po upływie maksymalnego czasu, ocena sygnału jest zamykana z odpowiednim statusem.
4. **Analiza statystyczna**: System generuje statystyki dotyczące skuteczności sygnałów, w tym wskaźniki sukcesu, średnie zyski i straty.

#### 3.7.4 Metryki oceny

- **Wskaźnik sukcesu**: Procent sygnałów, które osiągnęły cel zysku.
- **Średni zysk/strata**: Średnie wartości zrealizowanych zysków i strat.
- **Współczynnik ryzyko-zysk**: Stosunek średniego zysku do średniej straty.
- **Wydajność według pewności**: Analiza skuteczności sygnałów pogrupowanych według poziomu pewności (niska, średnia, wysoka).
- **Wydajność według ramy czasowej**: Analiza skuteczności sygnałów pogrupowanych według ram czasowych (M15, H1, H4, D1).

#### 3.7.5 Zastosowanie metryk w systemie

Metryki generowane przez system oceny jakości sygnałów są wykorzystywane do:
- Ciągłego doskonalenia algorytmów generowania sygnałów.
- Filtrowania sygnałów o niskiej jakości przed ich wykorzystaniem w handlu.
- Dostosowywania parametrów zarządzania pozycjami na podstawie historycznej skuteczności.
- Optymalizacji alokacji kapitału w oparciu o statystyki wydajności różnych typów sygnałów.

System oceny jakości sygnałów stanowi istotny element pętli sprzężenia zwrotnego, umożliwiający samouczenie się i ciągłe doskonalenie agenta handlowego.

### 3.8 System backtestingu (src/backtest)

Moduł odpowiedzialny za testowanie strategii handlowych na danych historycznych. System backtestingu pozwala na symulację działania strategii w różnych warunkach rynkowych, ocenę ich skuteczności i optymalizację parametrów przed zastosowaniem w środowisku rzeczywistym.

#### 3.8.1 Komponenty

- `HistoricalDataManager`: Klasa zarządzająca danymi historycznymi, odpowiedzialna za pobieranie, cachowanie i przetwarzanie danych do backtestingu.
- `TradingStrategy`: Interfejs abstrakcyjny dla strategii handlowych, definiujący główne metody wymagane do generowania sygnałów.
- `BacktestEngine`: Główna klasa silnika backtestingu odpowiedzialna za symulację handlu na danych historycznych.
- `BacktestConfig`: Klasa konfiguracyjna definiująca parametry backtestingu, takie jak symbol, ramy czasowe, saldo początkowe, itp.
- `BacktestResult`: Klasa przechowująca wyniki backtestingu, w tym transakcje, krzywą equity, metryki wydajności.
- `BacktestTrade`: Reprezentacja pojedynczej transakcji w procesie backtestingu.

#### 3.8.2 Strategie handlowe

System backtestingu implementuje następujące strategie handlowe:

1. **SimpleMovingAverageStrategy**: Strategia oparta na przecięciach średnich kroczących o różnych okresach.
2. **RSIStrategy**: Strategia wykorzystująca wskaźnik RSI do identyfikacji poziomów wykupienia i wyprzedania.
3. **BollingerBandsStrategy**: Strategia oparta na wstęgach Bollingera, generująca sygnały przy przebiciach górnej i dolnej wstęgi.
4. **MACDStrategy**: Strategia wykorzystująca wskaźnik MACD, identyfikująca sygnały na podstawie przecięć linii MACD i linii sygnałowej.
5. **CombinedIndicatorsStrategy**: Strategia odwzorowująca działanie głównego generatora sygnałów, łącząca różne wskaźniki z odpowiednimi wagami.

Kluczową cechą systemu jest strategia `CombinedIndicatorsStrategy`, która replikuje logikę głównego generatora sygnałów używanego w systemie produkcyjnym. Ta strategia umożliwia dokładne testowanie i optymalizację parametrów używanych w rzeczywistym handlu.

#### 3.8.3 Główne funkcje

- `HistoricalDataManager.get_historical_data`: Pobiera dane historyczne z MT5 lub z lokalnego cache.
- `TradingStrategy.generate_signals`: Generuje sygnały handlowe na podstawie dostarczonych danych historycznych.
- `BacktestEngine.run`: Uruchamia proces backtestingu na podstawie zadanej konfiguracji i strategii.
- `calculate_metrics`: Oblicza metryki wydajności na podstawie wyników backtestingu.
- `generate_report`: Generuje szczegółowy raport z wynikami backtestingu, w tym wykresy i tabele statystyk.
- `BacktestResult.save`: Zapisuje wyniki backtestingu do pliku w formacie JSON.

#### 3.8.4 Proces backtestingu

1. **Konfiguracja**: Definiowanie parametrów backtestingu, takich jak instrumenty, ramy czasowe, okres testów, wielkość pozycji.
2. **Inicjalizacja strategii**: Wybór i konfiguracja strategii handlowej do testowania.
3. **Ładowanie danych**: Pobieranie historycznych danych cenowych z platformy MT5 lub z lokalnego cache'u przez `HistoricalDataManager`.
4. **Generowanie sygnałów**: Analiza danych historycznych i generowanie sygnałów handlowych przez wybraną strategię.
5. **Symulacja handlu**: Przetwarzanie sygnałów handlowych i symulacja otwierania/zamykania pozycji.
6. **Kalkulacja zysków/strat**: Obliczanie wyników finansowych dla każdej transakcji.
7. **Analiza wyników**: Obliczanie metryk wydajności, takich jak win rate, profit factor, drawdown.
8. **Raportowanie**: Tworzenie szczegółowego raportu z wynikami backtestingu.

#### 3.8.5 Mierzone metryki

- **Net Profit**: Całkowity zysk/strata z wszystkich transakcji.
- **Win Rate**: Procent zyskownych transakcji.
- **Profit Factor**: Stosunek zysków do strat.
- **Maximum Drawdown**: Maksymalny procentowy spadek kapitału od szczytu.
- **Sharpe Ratio**: Stosunek średniego zwrotu do odchylenia standardowego.
- **Average Trade**: Średni zysk/strata na transakcję.
- **Average Winning Trade**: Średni zysk na wygraną transakcję.
- **Average Losing Trade**: Średnia strata na przegraną transakcję.
- **Maximum Consecutive Winners/Losers**: Maksymalna liczba kolejnych zyskownych/stratnych transakcji.

#### 3.8.6 Zastosowanie backtestingu w systemie

Backtesting jest wykorzystywany do:

- Testowania różnych strategii handlowych przed ich wdrożeniem.
- Optymalizacji parametrów handlowych, takich jak wielkości pozycji, poziomy stop loss i take profit.
- Dostrajania wag wskaźników i progów decyzyjnych używanych w głównym generatorze sygnałów.
- Oceny wydajności strategii w różnych warunkach rynkowych.
- Porównywania różnych instrumentów i ram czasowych.
- Walidacji zmian w algorytmach handlowych.

#### 3.8.7 Integracja z głównym systemem handlowym

System backtestingu jest zintegrowany z głównym systemem handlowym poprzez:

1. **Replikację logiki generowania sygnałów**: Strategia `CombinedIndicatorsStrategy` odwzorowuje działanie głównego generatora sygnałów w `src/analysis/signal_generator.py`.
2. **Współdzielenie parametrów**: Wagi wskaźników i progi decyzyjne są synchronizowane między systemem backtestingu a głównym generatorem sygnałów.
3. **Optymalizację parametrów**: Wyniki backtestingu są wykorzystywane do optymalizacji parametrów używanych w produkcji.
4. **Walidację zmian**: Każda zmiana w algorytmach handlowych jest testowana poprzez backtest przed wdrożeniem.

Główną zaletą tej integracji jest możliwość systematycznej optymalizacji parametrów generatora sygnałów i szybkie testowanie nowych pomysłów przed ich wdrożeniem w środowisku produkcyjnym.

System backtestingu stanowi kluczowe narzędzie w procesie rozwoju, optymalizacji i walidacji strategii handlowych, minimalizując ryzyko strat w handlu rzeczywistym.

## 4. Przepływ danych i procesy

### 4.1 Inicjalizacja systemu

1. Uruchomienie serwera HTTP (server.py)
2. Inicjalizacja MT5Server i połączenie z terminalem MetaTrader 5
3. Inicjalizacja AgentController
4. Inicjalizacja komponentów (PositionManager, RiskManager, itp.)
5. System gotowy do pracy

### 4.2 Proces analizy rynku

1. Agent pobiera dane rynkowe z MT5Server
2. Dane są analizowane przez modele AI
3. Generowane są potencjalne setupy handlowe
4. Setupy są filtrowane i oceniane pod kątem jakości
5. Najlepsze setupy są weryfikowane przez RiskManager
6. Jeśli setup jest akceptowalny, przygotowywane jest zlecenie

### 4.3 Proces otwierania pozycji

1. AgentController decyduje o otwarciu pozycji
2. RiskManager weryfikuje zgodność z limitami ryzyka
3. PositionManager przygotowuje parametry pozycji
4. Zlecenie jest przekazywane do MT5Server
5. MT5Server wykonuje zlecenie przez MT5
6. PositionManager inicjalizuje zarządzanie cyklem życia pozycji
7. Pozycja jest zapisywana w bazie danych

### 4.4 Zarządzanie otwartymi pozycjami

1. PositionManager monitoruje otwarte pozycje
2. Dla każdej pozycji wykonywane są akcje zgodne z bieżącym etapem cyklu życia
3. StopLossManager aktualizuje poziomy stop-loss i take-profit
4. W razie potrzeby pozycje są modyfikowane lub zamykane

## 5. Konfiguracja systemu

### 5.1 Zmienne środowiskowe (.env)

Kluczowe zmienne środowiskowe:
- API_KEYS dla modeli AI (CLAUDE_API_KEY, GROK_API_KEY, DEEPSEEK_API_KEY)
- Parametry połączenia z bazą danych
- Konfiguracja serwera HTTP
- Ścieżka do terminala MT5

### 5.2 Konfiguracja agenta

Konfiguracja agenta obejmuje:
- Tryb pracy (observation, semi_automatic, automatic)
- Limity ryzyka (maksymalna ekspozycja, maksymalna strata, itp.)
- Konfiguracja instrumentów (limity alokacji, parametry strategii)

## 6. Monitorowanie i raportowanie

System oferuje rozbudowane funkcje monitorowania i raportowania:
- Monitorowanie aktywnych pozycji
- Śledzenie wydajności modeli AI
- Raportowanie wyników handlowych
- Monitorowanie stanu systemu

## 7. Zarządzanie pozycjami

### 7.1 Limity pozycji

System AgentMT5 posiada wbudowane mechanizmy ograniczające liczbę otwieranych pozycji, aby zapewnić odpowiednie zarządzanie ryzykiem. Limity te są zdefiniowane w klasie `RiskParameters` w module `src/risk_management/risk_manager.py`:

```python
@dataclass
class RiskParameters:
    max_positions_per_symbol: int = 1  # Maksymalna liczba pozycji na jeden symbol
    max_positions_total: int = 5       # Maksymalna całkowita liczba pozycji
    # ... inne parametry
```

Domyślne wartości to:
- Maksymalnie 1 pozycja na symbol
- Maksymalnie 5 pozycji w całym systemie

Te limity zapobiegają nadmiernemu otwieraniu pozycji przez system, co mogłoby prowadzić do zwiększonego ryzyka.

### 7.2 Zamykanie nadmiarowych pozycji

#### 7.2.1 Automatyczne zamykanie nadmiarowych pozycji

System posiada skrypt `close_excess_positions.py`, który automatycznie identyfikuje i zamyka nadmiarowe pozycje zgodnie z ustawionymi limitami (maksymalnie 1 pozycja na symbol, maksymalnie 5 pozycji łącznie).

Skrypt wykorzystuje łatkę `patched_close_position`, która umożliwia zamykanie pozycji przez Expert Advisor (EA) zamiast bezpośrednio przez API MT5, co pozwala obejść ograniczenia nałożone przez brokera.

Aby uruchomić skrypt, należy wykonać:

```bash
python close_excess_positions.py
```

Skrypt działa w następujący sposób:
1. Inicjalizuje połączenie z MT5
2. Pobiera parametry z `RiskManager` (maksymalna liczba pozycji na symbol)
3. Pobiera wszystkie otwarte pozycje
4. Grupuje pozycje według symbolu i typu
5. Dla każdego symbolu i typu, jeśli liczba pozycji przekracza limit, identyfikuje nadmiarowe pozycje (te z najmniejszym zyskiem)
6. Zamyka nadmiarowe pozycje wykorzystując EA poprzez komunikację HTTP

#### 7.2.2 Ręczne zamykanie nadmiarowych pozycji

W przypadku, gdy skrypt automatyczny nie zadziała poprawnie lub gdy konieczne jest ręczne zarządzanie pozycjami, można zamknąć nadmiarowe pozycje bezpośrednio w terminalu MetaTrader 5:

1. Otwórz terminal MetaTrader 5
2. Przejdź do zakładki "Terminal" (Ctrl+T)
3. Wybierz zakładkę "Handel"
4. Zobaczysz listę wszystkich otwartych pozycji
5. Posortuj pozycje według symbolu, klikając na nagłówek kolumny "Symbol"
6. Dla każdego symbolu, który ma więcej niż 1 otwartą pozycję:
   - Pozostaw najlepszą pozycję (z największym zyskiem lub najmniejszą stratą)
   - Zamknij pozostałe pozycje, klikając prawym przyciskiem myszy na pozycję i wybierając "Zamknij pozycję"

#### 7.2.3 Komunikacja z EA do zamykania pozycji

System wykorzystuje komunikację HTTP z EA w celu zamykania pozycji, co pozwala obejść ograniczenia API MT5. Proces zamykania pozycji przez EA wygląda następująco:

1. System wykorzystuje funkcję `patched_close_position` z modułu `src.utils.patches`
2. Funkcja identyfikuje pozycję do zamknięcia na podstawie numeru ticketu
3. Tworzy instancję `MT5ApiClient` i wybiera odpowiedni EA ID
4. Wysyła żądanie do endpointu `/position/close` na serwerze HTTP
5. EA wykonuje operację zamykania pozycji w terminalu MT5
6. Wynik operacji jest zwracany do systemu

Szczegółowa dokumentacja komunikacji z EA znajduje się w pliku `docs/ea_patch.md`.

### 7.3 Skrypt do zamykania nadmiarowych pozycji

System zawiera również skrypt `close_excess_positions.py`, który próbuje automatycznie zamknąć nadmiarowe pozycje. Jednak ze względu na ograniczenia API brokera, skrypt może nie działać poprawnie. W takim przypadku należy zastosować metodę ręcznego zamykania pozycji opisaną powyżej.

```bash
python close_excess_positions.py
```

### 7.4 Monitorowanie liczby pozycji

Aby monitorować liczbę otwartych pozycji, można użyć skryptu testowego:

```bash
python test_open_position.py
```

Skrypt ten wyświetli listę wszystkich otwartych pozycji, co pozwoli na ocenę, czy konieczne jest ręczne zamknięcie nadmiarowych pozycji.

## 8. Wdrażanie i testowanie

### 8.1 Instalacja i uruchomienie

```bash
# Klonowanie repozytorium
git clone https://github.com/your-user/AgentMT5.git
cd AgentMT5

# Utworzenie i aktywacja wirtualnego środowiska
python -m venv venv
source venv/bin/activate  # Na Windows: venv\Scripts\activate

# Instalacja zależności
pip install -r requirements.txt

# Uruchomienie systemu
python start.py
```

### 8.2 Testowanie

System obejmuje kompleksowe testy:
- Testy jednostkowe (pytest)
- Testy integracyjne

### 8.3 System backtestingu

System backtestingu w AgentMT5 to kompleksowe narzędzie do testowania i optymalizacji strategii handlowych na danych historycznych. Umożliwia ocenę skuteczności strategii przed ich zastosowaniem w rzeczywistym handlu.

#### 8.3.1 Główne komponenty systemu backtestingu

1. **HistoricalDataManager** - zarządza pobieraniem, przetwarzaniem i cachowaniem danych historycznych z MT5
2. **BacktestEngine** - centralny komponent wykonujący backtesting strategii na danych historycznych
3. **TradingStrategy** - interfejs definiujący strategię handlową i metody generowania sygnałów
4. **PositionManager** - zarządza pozycjami handlowymi podczas backtestingu, w tym SL, TP i trailing stop
5. **ParameterOptimizer** - optymalizuje parametry strategii za pomocą różnych metod (grid search, random search)
6. **WalkForwardTester** - implementuje metodologię walk-forward testingu dla realistycznej oceny strategii

#### 8.3.2 Strategie handlowe

System wspiera różne strategie handlowe, w tym:
- **Simple Moving Average (SMA)** - oparta na przecięciach średnich kroczących
- **Relative Strength Index (RSI)** - wykorzystująca poziomy wykupienia i wyprzedania
- **Bollinger Bands** - oparta na przebiciach wstęg Bollingera
- **MACD** - wykorzystująca przecięcia linii MACD i sygnału
- **Combined Indicators** - łącząca różne wskaźniki techniczne, odzwierciedlająca działanie głównego generatora sygnałów

#### 8.3.3 Integracja z UI

System backtestingu jest w pełni zintegrowany z interfejsem użytkownika poprzez zakładkę "Backtesting", która umożliwia:
- Konfigurację backtestów (wybór instrumentu, timeframe'u, strategii, parametrów)
- Wyświetlanie wyników (tabele, wykresy, metryki wydajności)
- Optymalizację parametrów strategii
- Dostęp do dokumentacji i best practices

#### 8.3.4 Testy wydajnościowe

System przeszedł kompleksowe testy wydajnościowe, potwierdzające jego zdolność do efektywnego przetwarzania dużych zbiorów danych:
- Skuteczne przetwarzanie dużych zbiorów danych (>5000 świec M1)
- Niskie zużycie pamięci podczas optymalizacji parametrów
- Efektywna optymalizacja wielu kombinacji parametrów

#### 8.3.5 Dokumentacja systemu backtestingu

Szczegółowa dokumentacja systemu backtestingu znajduje się w pliku [BACKTEST_SYSTEM.md](./BACKTEST_SYSTEM.md), zawierająca:
- Szczegółowy opis architektury i komponentów
- Przykłady użycia i implementacji własnych strategii
- Instrukcje przeprowadzania backtestów i optymalizacji parametrów
- Best practices i znane ograniczenia

## 9. Bezpieczeństwo

System implementuje szereg mechanizmów bezpieczeństwa:
- Obsługa błędów i wyjątków
- Limity ekspozycji i ryzyka
- Walidacja zleceń przed wykonaniem
- Monitoring i alerty

## 10. System łatek (patches)

W celu zwiększenia stabilności systemu i szybkiego reagowania na problemy, AgentMT5 implementuje zaawansowany system łatek (patches). System ten pozwala na dynamiczne modyfikowanie zachowania klas i funkcji bez potrzeby bezpośredniej modyfikacji kodu źródłowego.

### 10.1 Architektura systemu łatek

System łatek jest zaimplementowany w module `src/utils/patches.py` i składa się z:
- Funkcji do aplikowania poszczególnych łatek
- Centralnej funkcji `apply_all_patches()` do aplikowania wszystkich dostępnych łatek
- Mechanizmów bezpieczeństwa do przywracania oryginalnej funkcjonalności w przypadku błędów

### 10.2 Dostępne łatki

Aktualnie system zawiera następujące łatki:

#### 10.2.1 PositionManager

```python
def patch_position_manager() -> bool:
```

**Problem**: Klasa `PositionManager` wymaga parametru `config` w konstruktorze, ale funkcja `get_position_manager()` nie przekazuje tego parametru.

**Rozwiązanie**: Łatka modyfikuje konstruktor `PositionManager.__init__` tak, aby akceptował opcjonalny parametr `config` oraz aktualizuje funkcję `get_position_manager()`, aby przekazywała pusty słownik jako konfigurację.

#### 10.2.2 DatabaseManager

```python
def patch_db_manager() -> bool:
```

**Problem**: Klasa `DatabaseManager` nie posiada metody `save_trading_signal`, która jest wymagana przez `SignalGenerator`.

**Rozwiązanie**: Łatka dodaje metodę `save_trading_signal` do klasy `DatabaseManager`, która loguje próbę zapisu sygnału handlowego bez faktycznego zapisywania do bazy danych.

#### 10.2.3 TradingService

```python
def patch_trading_service() -> bool:
```

**Problem**: Metoda `execute_signal` w klasie `TradingService` próbuje używać metody `get` na obiekcie `TradingSignal`, która nie istnieje.

**Rozwiązanie**: Łatka zastępuje implementację metody `execute_signal`, używając bezpośredniego dostępu do atrybutów zamiast metody `get`.

#### 10.2.4 SignalGenerator

```python
def patch_signal_generator() -> bool:
```

**Problem**: Konstruktor klasy `SignalGenerator` nie akceptuje parametru `config`, który jest przekazywany w niektórych miejscach.

**Rozwiązanie**: Łatka modyfikuje konstruktor `SignalGenerator.__init__` tak, aby akceptował opcjonalny parametr `config`.

**Dodatkowe naprawione problemy**:
1. Dodano metodę `generate_signal_from_data` do klasy `SignalGenerator`, która umożliwia generowanie sygnałów na podstawie danych historycznych. Jest to kluczowe dla funkcjonalności backtestingu.
2. Naprawiono wywołanie metody `_select_model_name()` w metodzie `generate_signal()`, dodając brakujący parametr `confidence`.

### 10.3 Zastosowanie łatek

Łatki są aplikowane podczas uruchamiania systemu. Odpowiednie wywołanie funkcji znajduje się w pliku `start.py`:

```python
from src.utils.patches import apply_all_patches

# Aplikuj wszystkie łatki systemowe
patches_results = apply_all_patches()
logger.info(f"Zaaplikowano łatki: {sum(1 for v in patches_results.values() if v)}/{len(patches_results)} pomyślnie")
```

### 10.4 Zalety podejścia łatkowego

1. **Bezpieczeństwo** - łatki minimalizują ryzyko wprowadzenia nowych błędów w krytycznych komponentach
2. **Elastyczność** - łatki można łatwo włączać/wyłączać w zależności od potrzeb
3. **Tymczasowość** - łatki zapewniają natychmiastowe rozwiązania, podczas gdy docelowe poprawki mogą wymagać bardziej złożonych zmian
4. **Śledzenie zmian** - wszystkie łatki są zebrane w jednym miejscu, co ułatwia zarządzanie
5. **Kompatybilność wsteczna** - łatki nie zmieniają struktury kodu źródłowego, co jest ważne dla aktualizacji

## 11. Rozwój i rozszerzenia

Planowane rozszerzenia systemu:
- Integracja z dodatkowymi modelami AI
- Optymalizacja strategii zarządzania pozycjami
- Rozbudowa interfejsu użytkownika
- Zaawansowana analityka wyników

## 12. Słownik pojęć

- **EA (Expert Advisor)** - program automatycznego handlu w platformie MetaTrader 5
- **MT5** - MetaTrader 5, platforma handlowa
- **Setup** - potencjalna okazja handlowa
- **SL (Stop Loss)** - poziom ceny, przy którym pozycja jest automatycznie zamykana w celu ograniczenia strat
- **TP (Take Profit)** - poziom ceny, przy którym pozycja jest automatycznie zamykana w celu realizacji zysku
- **Break-even** - punkt, w którym transakcja nie przynosi ani zysku, ani straty
- **Łatka (Patch)** - dynamiczna modyfikacja zachowania klasy lub funkcji bez zmiany kodu źródłowego

## 13. FAQ - Często zadawane pytania

### 13.1 Jak uruchomić system?
Aby uruchomić system, należy:
1. Aktywować środowisko wirtualne (venv)
2. Uruchomić terminal MT5
3. Uruchomić serwer HTTP (`python start.py`)
4. Załadować EA na wykres w MT5

### 13.2 Jak monitorować stan systemu?
Stan systemu można monitorować poprzez:
1. Interfejs użytkownika dostępny pod adresem http://localhost:8501
2. Logi systemowe w katalogu logs/
3. Endpointy monitorowania API

### 13.3 Jak zmienić tryb pracy agenta?
Tryb pracy agenta można zmienić poprzez:
1. Interfejs użytkownika
2. Wywołanie endpointu `/agent/start` z odpowiednim parametrem `mode`

## 14. Diagnostyka i rozwiązywanie problemów

### 14.1 Problemy z połączeniem API

#### 14.1.1 'NoneType' object has no attribute 'status_code'

Ten błąd występuje, gdy klient API próbuje połączyć się z nieistniejącym endpointem lub gdy serwer MT5 nie odpowiada. Komunikat wskazuje, że funkcja `send_request()` zwróciła `None` zamiast obiektu odpowiedzi HTTP.

**Rozwiązanie:**
1. Sprawdź czy endpoint jest poprawnie skonfigurowany w kliencie API
2. Upewnij się, że serwer HTTP działa na oczekiwanym porcie (np. 8000)
3. Sprawdź logi serwera pod kątem błędów
4. Zweryfikuj, czy zdefiniowano handler dla endpointu w klasie `MT5Server`

#### 14.1.2 Problemy z inicjalizacją MT5

Jeśli MT5 nie inicjalizuje się poprawnie, sprawdź:
1. Czy terminal MT5 jest uruchomiony
2. Czy masz odpowiednie uprawnienia do połączenia z MT5
3. Czy biblioteka MetaTrader5 dla Python jest poprawnie zainstalowana
4. Czy Expert Advisor jest załadowany na odpowiednim wykresie

### 14.2 Porty używane przez system

- Port 8000: Główny serwer API FastAPI
- Port 5555: Port komunikacji z Expert Advisor MT5
- Port 8080: Dodatkowy port używany przez niektóre konfiguracje

Aby zmienić port używany przez klienta MT5ApiClient, można:

1. Użyć zmiennej środowiskowej:
   ```
   export MT5_SERVER_PORT=8000
   ```

2. Lub w kodzie:
   ```python
   client = get_mt5_api_client(host='127.0.0.1', port=8000)
   ``` 

## Wspierane instrumenty

System obsługuje następujące instrumenty finansowe:

- EURUSD.pro - Para walutowa Euro/Dolar amerykański
- GBPUSD.pro - Para walutowa Funt brytyjski/Dolar amerykański
- GOLD.pro - Złoto
- US100.pro - Indeks US NASDAQ 100
- SILVER.pro - Srebro

Dla każdego instrumentu można skonfigurować indywidualne parametry handlowe, takie jak maksymalny rozmiar lota czy aktywność.

```json
{
  "request": {
    "action": "OPEN_POSITION",
    "symbol": "EURUSD.pro",
    "order_type": "BUY",
    "volume": 0.1,
    "price": null,
    "sl": 1.08234,
    "tp": 1.09876,
    "comment": "AI Signal #45678",
    "magic": 12345
  }
}
```

```json
{
  "EURUSD.pro": {
    "active": true,
    "max_lot_size": 0.1,
    "pip_value": 10,
    "timeframes": ["M5", "M15", "H1"]
  },
  "GBPUSD.pro": {
    "active": true,
    "max_lot_size": 0.1,
    "pip_value": 10,
    "timeframes": ["M5", "M15", "H1"]
  }
}
```

```json
{
  "request": {
    "action": "GET_MARKET_DATA",
    "symbol": "EURUSD.pro"
  }
} 