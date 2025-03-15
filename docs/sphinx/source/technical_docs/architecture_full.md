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
- `/market/data` - obsługa danych rynkowych
- `/position/update` - aktualizacja informacji o pozycjach
- `/account/info` - informacje o koncie
- `/commands` - pobieranie komend do wykonania przez EA
- `/agent/start`, `/agent/stop`, `/agent/status` - zarządzanie agentem
- `/monitoring/*` - endpointy monitoringu

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

## 7. Wdrażanie i testowanie

### 7.1 Instalacja i uruchomienie

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
python run.py
```

### 7.2 Testowanie

System obejmuje kompleksowe testy:
- Testy jednostkowe (pytest)
- Testy integracyjne
- Testy wydajnościowe
- Backtesty na danych historycznych

## 8. Bezpieczeństwo

System implementuje szereg mechanizmów bezpieczeństwa:
- Obsługa błędów i wyjątków
- Limity ekspozycji i ryzyka
- Walidacja zleceń przed wykonaniem
- Monitoring i alerty

## 9. Rozwój i rozszerzenia

Planowane rozszerzenia systemu:
- Integracja z dodatkowymi modelami AI
- Optymalizacja strategii zarządzania pozycjami
- Rozbudowa interfejsu użytkownika
- Zaawansowana analityka wyników

## 10. Słownik pojęć

- **EA (Expert Advisor)** - program automatycznego handlu w platformie MetaTrader 5
- **MT5** - MetaTrader 5, platforma handlowa
- **Setup** - potencjalna okazja handlowa
- **SL (Stop Loss)** - poziom ceny, przy którym pozycja jest automatycznie zamykana w celu ograniczenia strat
- **TP (Take Profit)** - poziom ceny, przy którym pozycja jest automatycznie zamykana w celu realizacji zysku
- **Break-even** - punkt, w którym transakcja nie przynosi ani zysku, ani straty

## 11. FAQ - Często zadawane pytania

### 11.1 Jak uruchomić system?
Aby uruchomić system, należy:
1. Aktywować środowisko wirtualne (venv)
2. Uruchomić terminal MT5
3. Uruchomić serwer HTTP (`python run.py`)
4. Załadować EA na wykres w MT5

### 11.2 Jak monitorować stan systemu?
Stan systemu można monitorować poprzez:
1. Interfejs użytkownika dostępny pod adresem http://localhost:8501
2. Logi systemowe w katalogu logs/
3. Endpointy monitorowania API

### 11.3 Jak zmienić tryb pracy agenta?
Tryb pracy agenta można zmienić poprzez:
1. Interfejs użytkownika
2. Wywołanie endpointu `/agent/start` z odpowiednim parametrem `mode` 