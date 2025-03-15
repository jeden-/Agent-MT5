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
+-------------------------+        +--------------------+
|                         |        |                    |
|  MetaTrader 5 Terminal  |<------>|  Expert Advisor    |
|                         |        |  (MQL5)            |
+-----------+-------------+        +---------+----------+
            |                                |
            | PyMT5                          | HTTP
            v                                v
+-------------------------+        +--------------------+
|                         |        |                    |
|  Agent AI (Python)      |<------>|  API Server (HTTP) |
|                         |        |                    |
+-----------+-------------+        +---------+----------+
            |                                |
            |                                |
            v                                v
+-------------------------+        +--------------------+
|                         |        |                    |
|  Modele AI (ML)         |        |  UI (Streamlit)    |
|                         |        |                    |
+-------------------------+        +--------------------+
```

### 2.2 Opis komponentów

- **MetaTrader 5 Terminal**: Platforma handlowa używana do łączenia się z brokerem i wykonywania transakcji
- **Expert Advisor (EA)**: Skrypt MQL5 działający w terminalu MT5, odpowiedzialny za wykonywanie operacji handlowych
- **Agent AI**: Główny moduł systemu, odpowiedzialny za analizę danych i podejmowanie decyzji tradingowych
- **API Server**: Serwer HTTP zapewniający REST API dla komunikacji między komponentami systemu
- **Modele AI**: Zaawansowane modele uczenia maszynowego i AI do analizy rynku
- **UI (Streamlit)**: Interfejs użytkownika do monitorowania i kontrolowania systemu

## 3. Szczegółowy opis komponentów

### 3.1 Struktura katalogów

```
AgentMT5/
│
├── src/
│   ├── agent/
│   │   ├── agent.py              # Główny moduł agenta
│   │   ├── strategy.py           # Strategie handlowe
│   │   ├── risk_manager.py       # Zarządzanie ryzykiem
│   │   └── models/               # Modele ML/AI
│   │
│   ├── mt5_bridge/
│   │   ├── mt5_api_client.py     # Klient API MT5
│   │   ├── mt5_connector.py      # Konektor MT5 (PyMT5)
│   │   └── server.py             # Serwer HTTP (FastAPI)
│   │
│   ├── ui/
│   │   ├── app.py                # Aplikacja Streamlit
│   │   ├── components/           # Komponenty UI
│   │   └── data_handler.py       # Obsługa danych dla UI
│   │
│   └── utils/
│       ├── logger.py             # Konfiguracja logowania
│       ├── config.py             # Obsługa konfiguracji
│       └── data_utils.py         # Narzędzia do obsługi danych
│
├── tests/                        # Testy jednostkowe i integracyjne
│
├── docs/                         # Dokumentacja
│
├── mt5_ea/                       # Pliki Expert Advisor (MQL5)
│
├── config/                       # Pliki konfiguracyjne
│
├── logs/                         # Logi aplikacji
│
└── requirements.txt              # Zależności Pythona
```

### 3.1.1 MT5 Connector (mt5_connector.py)

Moduł odpowiedzialny za komunikację z terminalem MT5 za pomocą biblioteki PyMT5. Główne funkcje:

- Inicjalizacja połączenia z terminalem MT5
- Pobieranie danych historycznych i aktualnych notowań
- Wykonywanie operacji handlowych (otwieranie, zamykanie, modyfikacja pozycji)

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
  "symbol": "EURUSD",
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
    "EURUSD": {
      "bid": 1.0750,
      "ask": 1.0752,
      "last": 1.0751,
      "time": "2025-03-12T03:00:00.000Z"
    },
    "GBPUSD": {
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
      "symbol": "EURUSD",
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

Moduł zarządzający pracą agenta AI, odpowiedzialny za:

- Uruchamianie i zatrzymywanie agenta
- Przełączanie między trybami pracy (analiza, handel automatyczny, tryb manualny)
- Monitorowanie stanu agenta i generowanie raportów

#### 3.2.1 Tryby pracy agenta

Agent może działać w następujących trybach:

1. **Tryb analizy** - analizuje rynek bez wykonywania transakcji
2. **Tryb automatyczny** - samodzielnie podejmuje decyzje i wykonuje transakcje
3. **Tryb półautomatyczny** - proponuje transakcje do zatwierdzenia przez użytkownika
4. **Tryb manualny** - użytkownik podejmuje decyzje, agent dostarcza analizy

#### 3.2.2 Przełączanie trybów

Zmiana trybu odbywa się poprzez:

1. Interfejs użytkownika
2. Wywołanie endpointu `/agent/start` z odpowiednim parametrem `mode`

## 4. Interfejs użytkownika

### 4.1 Architektura interfejsu

Interfejs użytkownika AgentMT5 to aplikacja webowa zbudowana przy użyciu Streamlit, która umożliwia monitorowanie i kontrolowanie systemu tradingowego AgentMT5. Interfejs zapewnia dostęp do danych handlowych w czasie rzeczywistym, analiz AI oraz kontroli nad agentem.

### 4.2 Główne funkcje interfejsu

- **Dashboard** - prezentacja kluczowych wskaźników i stanu systemu
- **Pozycje** - aktualnie otwarte pozycje i historia transakcji
- **Analiza** - wyniki analizy rynku generowane przez modele AI
- **Konfiguracja** - ustawienia agenta i parametry strategii handlowej
- **Logi** - logi systemowe i raportowanie błędów

## 5. Integracja z MetaTrader 5

### 5.1 Expert Advisor (MT5_EA.mq5)

Expert Advisor to skrypt napisany w języku MQL5, który:

- Komunikuje się z serwerem HTTP poprzez wysyłanie i odbieranie zapytań HTTP
- Wykonuje operacje handlowe na podstawie komend otrzymanych z serwera
- Przesyła aktualne dane rynkowe i informacje o pozycjach do serwera

### 5.2 Komunikacja EA z serwerem

Komunikacja odbywa się poprzez zapytania HTTP:

1. EA okresowo pobiera komendy z serwera (endpoint `/commands`)
2. EA wysyła aktualne dane rynkowe do serwera (endpoint `/market/data`)
3. EA informuje serwer o zmianach w pozycjach (endpoint `/position/update`)

## 6. Modele AI

### 6.1 Architektura modeli

System wykorzystuje następujące modele AI:

- **Claude** - duży model językowy do analizy sentymentu rynkowego i informacji ekonomicznych
- **Grok** - model do interpretacji danych rynkowych i prognozowania
- **DeepSeek** - model głębokiego uczenia do analizy wzorców cenowych

### 6.2 Zarządzanie modelami

Modele są zarządzane przez moduł `model_manager.py`, który odpowiada za:

- Inicjalizację modelów
- Przekazywanie danych do modeli
- Przetwarzanie wyników analizy modeli
- Integrację wyników z różnych modeli

## 7. Strategia handlowa

### 7.1 Framework strategii

System umożliwia definiowanie i implementację różnych strategii handlowych poprzez framework zawarty w module `strategy.py`. Każda strategia musi implementować następujące metody:

- `analyze_market()` - analiza danych rynkowych
- `generate_signals()` - generowanie sygnałów handlowych
- `execute_signals()` - wykonanie sygnałów (otwieranie/zamykanie pozycji)

### 7.2 Zarządzanie ryzykiem

Moduł `risk_manager.py` implementuje funkcje związane z zarządzaniem ryzykiem:

- Określanie wielkości pozycji (lot size) na podstawie kapitału i ryzyka
- Kalkulacja poziomów Stop Loss i Take Profit
- Monitorowanie ekspozycji na ryzyko i dostosowywanie parametrów

## 8. Instalacja i uruchomienie

### 8.1 Wymagania

- Python 3.10+
- MetaTrader 5 Terminal
- Zależności z pliku `requirements.txt`

### 8.2 Kroki instalacji

1. Sklonować repozytorium
2. Zainstalować zależności: `pip install -r requirements.txt`
3. Skonfigurować połączenie z MT5 w pliku `config/mt5_config.yml`
4. Skopiować pliki EA do katalogu MT5 (`MQL5/Experts/`)
5. Skompilować EA w edytorze MetaEditor

### 8.3 Uruchomienie

1. Uruchomić terminal MT5
2. Dodać EA do wykresu
3. Uruchomić serwer HTTP (`python run.py`)
4. Uruchomić interfejs użytkownika (`python -m src.ui.app`)

## 9. Diagnostyka i rozwiązywanie problemów

### 9.1 Problemy z połączeniem API

#### 9.1.1 'NoneType' object has no attribute 'status_code'

Ten błąd występuje, gdy klient API próbuje połączyć się z nieistniejącym endpointem lub gdy serwer MT5 nie odpowiada. Komunikat wskazuje, że funkcja `send_request()` zwróciła `None` zamiast obiektu odpowiedzi HTTP.

**Rozwiązanie:**
1. Sprawdź czy endpoint jest poprawnie skonfigurowany w kliencie API
2. Upewnij się, że serwer HTTP działa na oczekiwanym porcie (np. 8000)
3. Sprawdź logi serwera pod kątem błędów
4. Zweryfikuj, czy zdefiniowano handler dla endpointu w klasie `MT5Server`

#### 9.1.2 Problemy z inicjalizacją MT5

Jeśli MT5 nie inicjalizuje się poprawnie, sprawdź:
1. Czy terminal MT5 jest uruchomiony
2. Czy masz odpowiednie uprawnienia do połączenia z MT5
3. Czy biblioteka MetaTrader5 dla Python jest poprawnie zainstalowana
4. Czy Expert Advisor jest załadowany na odpowiednim wykresie

### 9.2 Porty używane przez system

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

## 10. Interfejs Użytkownika

### 10.1 Architektura Interfejsu

Interfejs użytkownika AgentMT5 to aplikacja webowa zbudowana przy użyciu Streamlit, która umożliwia monitorowanie i kontrolowanie systemu tradingowego AgentMT5. Interfejs zapewnia dostęp do danych handlowych w czasie rzeczywistym, analiz AI oraz kontroli nad agentem.

#### 10.1.1 Komponenty Interfejsu

Interfejs użytkownika jest zbudowany w oparciu o następujące komponenty:

- **Streamlit** - framework do tworzenia aplikacji webowych w Pythonie
- **Plotly** - biblioteka do tworzenia interaktywnych wykresów
- **Pandas** - biblioteka do analizy danych
- **MT5ApiClient** - klient API do komunikacji z serwerem MT5

#### 10.1.2 Struktura Kodu

Główny plik aplikacji to `src/ui/app.py`, który zawiera następujące komponenty:

- **Funkcje pomocnicze** - formatowanie danych, obsługa API, itp.
- **Funkcje renderujące** - odpowiedzialne za wyświetlanie poszczególnych zakładek
- **Funkcja główna** - inicjalizacja aplikacji i obsługa nawigacji

#### 10.1.3 Komunikacja z MT5

Interfejs komunikuje się z serwerem MT5 za pomocą klienta API (`MT5ApiClient`), który wysyła żądania HTTP do serwera MT5. Klient API obsługuje następujące endpointy:

- `/monitoring/connections` - informacje o połączeniach z MT5
- `/monitoring/positions` - informacje o aktywnych pozycjach
- `/monitoring/transactions` - historia transakcji
- `/monitoring/performance` - statystyki wydajności
- `/monitoring/status` - status systemu
- `/monitoring/resources` - informacje o zasobach systemowych
- `/monitoring/alerts` - aktywne alerty
- `/mt5/account` - informacje o koncie MT5
- `/ai/models` - informacje o modelach AI
- `/ai/signals` - sygnały handlowe generowane przez modele AI
- `/ai/signals/latest` - najnowsze sygnały handlowe
- `/agent/status` - status agenta
- `/agent/start` - uruchomienie agenta
- `/agent/stop` - zatrzymanie agenta
- `/agent/restart` - restart agenta
- `/agent/config` - konfiguracja agenta

### 10.2 Funkcje Interfejsu

#### 10.2.1 Live Monitor

Zakładka Live Monitor wyświetla:

- Status systemu i połączenia z MT5
- Saldo konta i equity
- Bieżący zysk/stratę
- Informacje o ostatniej transakcji
- Listę aktywnych pozycji z możliwością zarządzania nimi

#### 10.2.2 Performance Dashboard

Zakładka Performance Dashboard wyświetla:

- Kluczowe wskaźniki wydajności (win rate, profit factor, itp.)
- Wykres skumulowanego P/L
- Wykres wyników per instrument
- Pełną historię transakcji

#### 10.2.3 AI Analytics

Zakładka AI Analytics wyświetla:

- Aktualne sygnały handlowe generowane przez modele AI
- Wydajność poszczególnych modeli AI
- Analizę sygnałów AI
- Korelację między sygnałami AI a wynikami handlowymi

#### 10.2.4 System Status

Zakładka System Status wyświetla:

- Ogólny status systemu
- Status poszczególnych komponentów
- Informacje o zasobach systemowych (CPU, pamięć, dysk)
- Aktywne alerty

#### 10.2.5 Control Panel

Zakładka Control Panel umożliwia:

- Uruchamianie, zatrzymywanie i restartowanie agenta
- Wybór trybu pracy agenta (obserwacyjny, półautomatyczny, automatyczny)
- Konfigurację limitów ryzyka
- Konfigurację parametrów dla poszczególnych instrumentów

### 10.3 Funkcje Automatycznego Odświeżania

Interfejs obsługuje automatyczne odświeżanie danych:

- Domyślny interwał odświeżania wynosi 10 sekund
- Użytkownik może dostosować interwał odświeżania w zakresie 5-60 sekund
- Pasek postępu pokazuje czas do następnego odświeżenia
- Każda zakładka ma również przycisk do ręcznego odświeżenia danych

### 10.4 Obsługa Błędów

Interfejs obsługuje różne scenariusze błędów:

- Brak połączenia z serwerem MT5
- Brak danych z serwera
- Błędy API

W przypadku błędów, interfejs wyświetla odpowiednie komunikaty i instrukcje dla użytkownika.

### 10.5 Uruchamianie Interfejsu

Aby uruchomić interfejs, należy wykonać następujące kroki:

1. Upewnić się, że serwer MT5 jest uruchomiony
2. Uruchomić skrypt `scripts/run_interface.py`
3. Otworzyć przeglądarkę i przejść do adresu `http://localhost:8501`

### 10.6 Konfiguracja

Interfejs można skonfigurować za pomocą zmiennych środowiskowych:

- `SERVER_URL` - adres serwera MT5 (domyślnie: `http://127.0.0.1:5555`)
- `REFRESH_INTERVAL` - interwał odświeżania w sekundach (domyślnie: `10`)
- `CURRENCY` - waluta używana w systemie (domyślnie: `zł`)

### 10.7 Aktualizacje w Wersji 1.0.0

W wersji 1.0.0 interfejsu wprowadzono następujące zmiany:

1. Usunięto przykładowe dane we wszystkich modułach i zastąpiono je rzeczywistymi danymi z MT5
2. Dodano przyciski odświeżania dla każdego panelu
3. Poprawiono wyświetlanie danych w Live Monitor
4. Zaktualizowano wykresy w Performance Dashboard
5. Ulepszono wizualizację danych w AI Analytics
6. Rozbudowano monitoring zasobów systemowych
7. Dodano lepsze formatowanie alertów
8. Zwiększono interwał odświeżania do 10 sekund dla zmniejszenia obciążenia serwera
9. Dodano wskaźnik stanu połączenia z MT5 w pasku bocznym
10. Dodano możliwość dostosowania interwału odświeżania przez użytkownika
11. Dodano pasek postępu pokazujący czas do następnego odświeżenia
12. Dodano sekcję z aktualnymi pozycjami w zakładce Live Monitor
13. Dodano sekcję z aktualnymi sygnałami AI w zakładce AI Analytics
14. Dodano stopkę z informacjami o wersji i autorze 