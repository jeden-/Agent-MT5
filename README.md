# AgentMT5 - System automatycznego handlu z wykorzystaniem sztucznej inteligencji

## Opis projektu

AgentMT5 to zaawansowany system automatycznego handlu wykorzystujący sztuczną inteligencję do analizy rynku i podejmowania decyzji tradingowych. Projekt integruje zaawansowane modele AI (Claude, Grok, DeepSeek) z platformą MetaTrader 5, zapewniając autonomiczne zarządzanie pozycjami przy zachowaniu ścisłej kontroli ryzyka.

## Cele projektu

Głównym celem projektu jest stworzenie systemu, który:
- Wykorzystuje zaawansowane algorytmy AI do analizy rynku finansowego
- Automatycznie podejmuje decyzje tradingowe oparte na analizie danych
- Zarządza ryzykiem i pozycjami w sposób autonomiczny
- Dąży do podwojenia powierzonego kapitału w możliwie najkrótszym czasie
- Zapewnia stabilną i niezawodną komunikację między MT5 a silnikiem AI

## Komponenty systemu

System składa się z następujących komponentów:

### Expert Advisor (EA) dla MetaTrader 5
- Znajduje się w katalogu `src/mt5_ea/`
- Odpowiada za bezpośrednią interakcję z platformą tradingową
- Zbiera dane rynkowe i wykonuje operacje handlowe
- Komunikuje się z serwerem poprzez protokół HTTP

### Serwer komunikacyjny
- Znajduje się w katalogu `src/mt5_bridge/`
- Obsługuje komunikację między EA a silnikiem AI
- Zapewnia przetwarzanie komunikatów HTTP
- Wykorzystuje `BaseHTTPRequestHandler` i `ThreadingMixIn` do obsługi wielu połączeń

### Silnik AI
- Analizuje dane rynkowe dostarczone przez EA
- Generuje sygnały i rekomendacje handlowe
- Wykorzystuje zaawansowane modele uczenia maszynowego

## System łatek (patches)

AgentMT5 implementuje system łatek (ang. patches), który pozwala na dynamiczne modyfikowanie zachowania klas i funkcji bez potrzeby bezpośredniej modyfikacji kodu źródłowego. System ten jest szczególnie przydatny do szybkiego rozwiązywania problemów, testowania nowych rozwiązań i zachowania kompatybilności wstecznej.

### Zalety stosowania łatek
- Zwiększa bezpieczeństwo wprowadzania zmian
- Pozwala na szybkie reagowanie na problemy w produkcji
- Umożliwia przeprowadzanie testów A/B różnych implementacji
- Centralizuje zmiany w jednym miejscu, co ułatwia zarządzanie

### Główne łatki systemu
- **PositionManager** - rozwiązuje problem z inicjalizacją managera pozycji
- **DatabaseManager** - dodaje brakujące metody do obsługi bazy danych
- **TradingService** - naprawia problemy z przetwarzaniem sygnałów tradingowych
- **SignalGenerator** - rozwiązuje problemy z generowaniem sygnałów

### Aplikowanie łatek
Łatki są aplikowane podczas uruchamiania systemu przez funkcję `apply_all_patches()` z modułu `src/utils/patches.py`. Status aplikowania łatek jest logowany, co pozwala na szybkie diagnozowanie problemów.

## Model komunikacji z MetaTrader 5

System wykorzystuje dwa kanały komunikacji z platformą MetaTrader 5:

### 1. Expert Advisor (EA)
- **Zadania**: Wykonywanie operacji handlowych (otwieranie i zamykanie pozycji), które są blokowane w API przez brokera
- **Protokół**: Komunikacja HTTP w formacie JSON
- **Kierunek**: Dwukierunkowy - EA wysyła dane o rynku i pozycjach, serwer zwraca komendy
- **Endpointy**:
  - `/position/update` - aktualizacja informacji o pozycjach
  - `/market/data` - przesyłanie danych rynkowych
  - `/account/info` - informacje o koncie (przestarzałe)
  - `/mt5/account` - informacje o koncie MT5 (zalecane)
  - `/commands` - pobieranie komend od serwera przez EA
  - `/ping` - sprawdzanie połączenia

### 2. Bezpośrednie API MetaTrader 5
- **Zadania**: Pobieranie historii transakcji, danych historycznych i statystyk konta
- **Biblioteka**: Python MetaTrader5 (`pip install MetaTrader5`)
- **Implementacja**: Bezpośrednie wywołania API z poziomu serwera
- **Zalety**:
  - Szybszy dostęp do danych historycznych
  - Niezależność od EA dla operacji odczytu
  - Możliwość pobrania większej ilości danych

Ten hybrydowy model pozwala wykorzystać zalety obu podejść:
- EA zajmuje się tylko tym, co wymaga uprawnień brokera (operacje handlowe)
- API Python pozwala na bezpośredni dostęp do danych bez obciążania EA

## Aktualny status projektu

Na ten moment zrealizowano:

1. **Expert Advisor (EA) dla MetaTrader 5**:
   - Pełna implementacja EA z obsługą komunikacji HTTP
   - Mechanizm inicjalizacji, deinicjalizacji i obsługi timera
   - Wysyłanie i odbieranie danych w formacie JSON
   - Obsługa podstawowych operacji handlowych
   - Automatyczne odświeżanie i synchronizacja pozycji

2. **Serwer komunikacyjny HTTP**:
   - Implementacja wielowątkowego serwera HTTP
   - Obsługa wszystkich niezbędnych endpointów
   - Integracja z API MetaTrader 5 w Pythonie
   - Mechanizmy odzyskiwania po błędach
   - Monitorowanie stanu połączenia

3. **Interfejs użytkownika**:
   - Dashboard do monitorowania systemu w czasie rzeczywistym
   - Wyświetlanie aktywnych pozycji i ich statusu
   - Monitorowanie historii transakcji
   - Wizualizacja wyników handlowych
   - Analityka wydajności modeli AI
   - Automatyczne odświeżanie danych z konfigurowalnym interwałem
   - Pełna synchronizacja z rzeczywistymi danymi z MT5
   - Zaawansowane wykresy i wizualizacje danych
   - Panel sterowania agentem (start, stop, restart)
   - Konfiguracja parametrów handlowych

4. **Integracja z API MetaTrader 5**:
   - Bezpośrednie pobieranie historii transakcji
   - Automatyczne odświeżanie danych
   - Obsługa wielu instrumentów jednocześnie

5. **Zarządzanie ryzykiem**:
   - Mechanizmy kontroli ryzyka
   - Walidacja zleceń przed wykonaniem
   - Automatyczne zarządzanie stop-loss
   - Trailing stop i break-even funkcjonalność

6. **Zarządzanie pozycjami**:
   - Limity liczby otwartych pozycji (domyślnie max 1 na symbol, max 5 łącznie)
   - Skrypt do zamykania nadmiarowych pozycji (`close_excess_positions.py`) wykorzystujący komunikację z EA
   - Mechanizm omijania ograniczeń API MT5 przy zamykaniu pozycji (poprzez EA)
   - Możliwość ręcznego zamykania nadmiarowych pozycji przez MT5
   - Monitorowanie liczby otwartych pozycji
   - Automatyczne odrzucanie nowych pozycji po przekroczeniu limitów

7. **Integracja modeli AI**:
   - Połączenie z zaawansowanymi modelami (Claude, Grok, DeepSeek)
   - System routingu zapytań między modelami
   - Analiza wydajności modeli w czasie rzeczywistym

## Problemy i wyzwania

Aktualnie rozwiązane problemy:
- ✅ Komunikacja między EA a serwerem HTTP
- ✅ Wyświetlanie aktualnych pozycji i historii transakcji
- ✅ Integracja bezpośrednio z API MetaTrader 5
- ✅ Stabilność połączenia i obsługa błędów

Pozostałe wyzwania:
- Testy wydajnościowe przy dużym obciążeniu
- Testy bezpieczeństwa komunikacji HTTP
- Finalizacja dokumentacji technicznej
- Rozszerzenie systemu powiadomień

## Znane problemy

### Ostrzeżenia SettingWithCopyWarning z pandas

W modułu backtestingu mogą pojawić się ostrzeżenia `SettingWithCopyWarning` z biblioteki pandas. Te ostrzeżenia informują o potencjalnych problemach z modyfikacją kopii fragmentu DataFrame, ale nie wpływają na faktyczne działanie systemu. 

Przykładowe ostrzeżenie:
```
SettingWithCopyWarning: A value is trying to be set on a copy of a slice from a DataFrame.
Try using .loc[row_indexer,col_indexer] = value instead
```

**Planowane rozwiązanie:** W przyszłych wersjach zostanie to poprawione przez użycie metody `.loc` do przypisywania wartości, np.:
```python
self.market_data.loc[:, 'symbol'] = self.config.symbol
self.market_data.loc[:, 'timeframe'] = self.config.timeframe
```

zamiast:
```python
self.market_data['symbol'] = self.config.symbol
self.market_data['timeframe'] = self.config.timeframe
```

## Instrukcja użycia

1. **Konfiguracja środowiska**
   ```bash
   # Klonowanie repozytorium
   git clone https://github.com/twój-użytkownik/AgentMT5.git
   cd AgentMT5

   # Utworzenie i aktywacja wirtualnego środowiska
   python -m venv venv
   source venv/bin/activate  # Na Windows: venv\Scripts\activate

   # Instalacja zależności
   pip install -r requirements.txt
   ```

2. **Instalacja Expert Advisor (EA)**
   - Skompiluj EA z katalogu `src/mt5_ea/simple_http_AgentMT5_EA.mq5` w MetaEditor
   - Załaduj skompilowany EA na wykres w MetaTrader 5
   - Skonfiguruj parametry EA (domyślny adres serwera: `http://127.0.0.1:5555`)

3. **Uruchomienie serwera HTTP i interfejsu**
   ```bash
   # Bezpośrednie uruchomienie obu komponentów
   python scripts/run_interface.py
   
   # LUB oddzielne uruchomienie komponentów w różnych terminalach
   # Terminal 1 - Serwer HTTP
   python src/mt5_bridge/mt5_server.py
   
   # Terminal 2 - Interfejs użytkownika
   python scripts/start_interface_simple.py
   ```

4. **Dostęp do interfejsu użytkownika**
   - Otwórz przeglądarkę i przejdź do adresu: http://localhost:8501
   - Interfejs pozwala na:
     - Monitorowanie aktywnych pozycji i ich zarządzanie
     - Przeglądanie historii transakcji i wyników
     - Śledzenie sygnałów i analiz AI w czasie rzeczywistym
     - Kontrolę i konfigurację agenta
     - Dostosowanie parametrów odświeżania danych
     - Monitorowanie stanu połączenia z MT5
     - Zarządzanie alertami i powiadomieniami

5. **Monitorowanie logów**
   - Logi serwera HTTP: `logs/mt5_server.log`
   - Logi interfejsu: `logs/interface.log`
   - Logi EA: dostępne w zakładce "Eksperci" w MetaTrader 5

## Plany rozwoju

W najbliższej przyszłości planowane są:
- Dalsza optymalizacja komunikacji HTTP między EA a serwerem
- Integracja zaawansowanych algorytmów AI
- Rozwój mechanizmów zarządzania ryzykiem
- Wdrożenie zaawansowanego systemu backtestingu (szczegóły w `src/backtest/BACKTEST_TODO.md`)
- Implementacja automatycznego dostrajania parametrów

### Plan wdrożenia backtestingu

Opracowano szczegółowy plan wdrożenia zaawansowanego systemu backtestingu, który obejmuje:

1. **Mechanizm cache'owania danych historycznych** - implementacja wydajnego systemu przechowywania danych w formacie Parquet
2. **Abstrakcyjny interfejs strategii** - elastyczna architektura pozwalająca na łatwe dodawanie nowych strategii
3. **Zaawansowane zarządzanie pozycjami** - trailing stop, breakeven, częściowe zamykanie pozycji
4. **Ulepszone raportowanie i wizualizacja** - interaktywne raporty i porównywanie strategii
5. **System optymalizacji parametrów** - grid search, algorytmy genetyczne, kroswalidacja

Pełny harmonogram i szczegóły planu znajdują się w `src/backtest/BACKTEST_TODO.md`.

## Licencja

Projekt jest własnością prywatną. Wszelkie prawa zastrzeżone.

## Funkcje

- Połączenie z MetaTrader 5 poprzez komunikację HTTP
- Zarządzanie pozycjami (otwieranie, zamykanie, modyfikacja)
- Analiza rynku przy użyciu AI
- Zarządzanie ryzykiem
- Monitorowanie stanu systemu
- Interfejs użytkownika (Streamlit)
- Zapis i analiza danych w bazie PostgreSQL

## Architektura

```
AgentMT5/
├── src/                      # Kod źródłowy
│   ├── ai_models/            # Modele AI
│   ├── database/             # Baza danych
│   ├── monitoring/           # Monitoring
│   ├── mt5_bridge/           # Most MT5
│   ├── mt5_ea/               # Expert Advisor
│   ├── position_management/  # Zarządzanie pozycjami
│   ├── risk_management/      # Zarządzanie ryzykiem
│   ├── ui/                   # Interfejs użytkownika
│   └── utils/                # Narzędzia
├── docs/                     # Dokumentacja
├── scripts/                  # Skrypty
├── tests/                    # Testy
├── config/                   # Konfiguracja
└── README.md                 # Ten plik
```

## Baza danych

Projekt wykorzystuje bazę danych PostgreSQL do przechowywania danych o transakcjach, sygnałach handlowych i innych informacjach.

### Konfiguracja bazy danych

1. **Uruchomienie bazy danych** - możesz użyć Docker:

```bash
# Uruchomienie bazy danych PostgreSQL za pomocą Docker Compose
docker-compose up -d postgres

# Uruchomienie PostgreSQL i pgAdmin
docker-compose up -d
```

2. **Konfiguracja połączenia**:

```bash
# Konfiguracja parametrów połączenia
python scripts/setup_postgres.py --host localhost --port 5432 --db agent_mt5 --user postgres
```

3. **Inicjalizacja bazy danych**:

```bash
# Inicjalizacja tabel i początkowych danych
python scripts/db_cli.py init
```

4. **Zarządzanie bazą danych**:

```bash
# Sprawdzenie statusu bazy danych
python scripts/db_cli.py status

# Wykonanie zapytania do tabeli
python scripts/db_cli.py query --table instruments

# Wykonanie niestandardowego zapytania SQL
python scripts/db_cli.py sql --query "SELECT * FROM trading_setups WHERE symbol = 'EURUSD'"

# Czyszczenie tabeli
python scripts/db_cli.py clear --table trading_signals --confirm
```

5. **PgAdmin**: po uruchomieniu docker-compose, pgAdmin będzie dostępny pod adresem http://localhost:5050 (domyślne dane logowania: admin@agentmt5.com / admin)

### Schemat bazy danych

Baza danych zawiera następujące główne tabele:
- **instruments** - instrumenty handlowe
- **trading_setups** - strategie handlowe
- **trading_signals** - sygnały handlowe
- **transactions** - transakcje
- **order_modifications** - modyfikacje zleceń
- **account_snapshots** - migawki stanu konta
- **system_logs** - logi systemowe
- **ai_stats** - statystyki AI
- **performance_metrics** - metryki wydajności

## Instalacja

```bash
# Klonowanie repozytorium
git clone https://github.com/twój-użytkownik/AgentMT5.git
cd AgentMT5

# Instalacja zależności
pip install -r requirements.txt

# Konfiguracja bazy danych
python scripts/setup_postgres.py

# Inicjalizacja bazy danych
python scripts/db_cli.py init
```

## Uruchomienie

```bash
# Główna metoda uruchomienia całego systemu
python start.py

# Alternatywne metody uruchomienia poszczególnych komponentów:
# Uruchomienie serwera HTTP dla MT5
python scripts/http_mt5_server.py --host 127.0.0.1 --port 5555

# Uruchomienie interfejsu użytkownika
cd src/ui
streamlit run app.py --server.port 8501 --server.address 0.0.0.0 --server.maxUploadSize 5

# LUB użyj skryptu pomocniczego
python scripts/run_interface.py --ui-port 8501 --ui-host 0.0.0.0

# Interfejs będzie dostępny pod adresem:
# http://localhost:8501
```

## Testy

```bash
# Uruchomienie wszystkich testów
python -m unittest discover tests

# Uruchomienie testów jednostkowych
python -m unittest discover tests/unit

# Uruchomienie testów integracyjnych
python -m unittest discover tests/integration
```

## Dokumentacja

Dokumentacja projektu dostępna jest w katalogu `docs/`.

## Licencja

Ten projekt jest objęty licencją [MIT](LICENSE).

## Aktualizacje

### Marzec 2025
- **Dokumentacja techniczna**: Zaktualizowano dokumentację API, dodano opis nowego endpointu `/mt5/account`
- **Diagnostyka**: Dodano sekcję diagnostyki i rozwiązywania problemów z połączeniem
- **Dokumenty**: Skonsolidowano i uporządkowano pliki dokumentacji w katalogu `/docs`

Pełne podsumowanie zmian w dokumentacji znajduje się w pliku [docs/PODSUMOWANIE_DOKUMENTACJI.md](docs/PODSUMOWANIE_DOKUMENTACJI.md).