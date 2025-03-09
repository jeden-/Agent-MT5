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
- Komunikuje się z serwerem poprzez gniazda (sockets)

### Serwer komunikacyjny
- Znajduje się w katalogu `src/server/`
- Obsługuje komunikację między EA a silnikiem AI
- Zapewnia trwałe połączenie i przetwarzanie komunikatów
- Dostępne są różne implementacje serwera (standardowy, persistentny, keep-alive)

### Silnik AI
- Analizuje dane rynkowe dostarczone przez EA
- Generuje sygnały i rekomendacje handlowe
- Wykorzystuje zaawansowane modele uczenia maszynowego

## Aktualny status projektu

Na ten moment zrealizowano:

1. **Expert Advisor (EA) dla MetaTrader 5**:
   - Podstawowa struktura EA z obsługą komunikacji socket
   - Mechanizm inicjalizacji, deinicjalizacji i obsługi timera
   - Funkcje wysyłania i odbierania danych
   - Obsługa podstawowych operacji handlowych

2. **Serwer komunikacyjny**:
   - Implementacja podstawowego serwera socket
   - Alternatywne implementacje z obsługą trwałego połączenia
   - Obsługa protokołu komunikacyjnego

3. **Narzędzia diagnostyczne**:
   - Skrypty do testowania połączenia
   - Monitorowanie stanu komunikacji

## Problemy i wyzwania

Aktualnie trwają prace nad stabilizacją połączenia socket między EA a serwerem. Zidentyfikowane problemy:
- Socket rozłącza się po krótkim czasie komunikacji
- Potrzebne są mechanizmy keep-alive i ponownego łączenia
- Wymaga poprawy obsługa błędów i wyjątków

## Instrukcja użycia

1. Skompiluj EA z katalogu `src/mt5_ea/AgentMT5_EA.mq5` w MetaEditor
2. Uruchom jeden z serwerów komunikacyjnych:
   ```
   python scripts/run_mt5_server.py
   ```
   lub
   ```
   python scripts/persistent_mt5_server.py
   ```
3. Załaduj skompilowany EA na wykres w MetaTrader 5
4. Skonfiguruj parametry EA (adres serwera, port, interwały)

## Plany rozwoju

W najbliższej przyszłości planowane są:
- Stabilizacja połączenia socket między EA a serwerem
- Integracja zaawansowanych algorytmów AI
- Rozwój mechanizmów zarządzania ryzykiem
- Testy z wykorzystaniem danych historycznych
- Implementacja automatycznego dostrajania parametrów

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
# Uruchomienie serwera HTTP dla MT5
python scripts/http_mt5_server.py --host 127.0.0.1 --port 5555

# Uruchomienie interfejsu użytkownika
cd src/ui
streamlit run app.py
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