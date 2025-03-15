# Aktualizacja dokumentacji technicznej AgentMT5 - Marzec 2025

## 1. Nowe endpointy API

### 1.1 Endpoint `/mt5/account`

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

**Odpowiedź (błąd):**
```json
{
  "status": "error",
  "error_code": 5001,
  "message": "Nie można połączyć się z MT5",
  "timestamp": "2025-03-12T03:00:00.000Z"
}
```

**Uwaga:** W przypadku błędu połączenia z MT5, system zwraca przykładowe dane o koncie z flagą `status: "ok"` dla zachowania kompatybilności z istniejącymi klientami.

## 2. Aktualizacje komponentów

### 2.1 Klasa `MT5ApiClient`

Dodano nowe metody:
- `get_account_info()` - pobiera informacje o koncie MT5
- `get_account_info_data()` - pobiera surowe dane o koncie (bez formatowania)

Zaktualizowano dokumentację metod:
- `send_request()` - dodano obsługę nowego endpointu
- `get_status()` - zaktualizowano format odpowiedzi

### 2.2 Klasa `MT5Server`

Dodano nowe endpointy:
- `/mt5/account` - endpoing zwracający informacje o koncie MT5

Zaktualizowano endpointy:
- `/account/info` - oznaczono jako przestarzały (deprecated)

## 3. Diagnostyka błędów połączenia

### 3.1 Błąd: 'NoneType' object has no attribute 'status_code'

Ten błąd występuje, gdy klient API próbuje połączyć się z nieistniejącym endpointem lub gdy serwer MT5 nie odpowiada. Komunikat wskazuje, że funkcja `send_request()` zwróciła `None` zamiast obiektu odpowiedzi HTTP.

**Rozwiązanie:**
1. Sprawdź czy endpoint jest poprawnie skonfigurowany w kliencie API
2. Upewnij się, że serwer HTTP działa na oczekiwanym porcie (np. 8000)
3. Sprawdź logi serwera pod kątem błędów
4. Zweryfikuj, czy zdefiniowano handler dla endpointu w klasie `MT5Server`

## 4. Porty używane przez system

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

## 5. Propozycja aktualizacji głównej dokumentacji technicznej

### 5.1 Sekcja do zaktualizowania: 3.1.2 Serwer HTTP (server.py)

Proponuję zaktualizować sekcję 3.1.2 w głównym pliku dokumentacji technicznej (DOKUMENTACJA_TECHNICZNA.md) w następujący sposób:

```markdown
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
```

### 5.2 Sekcja do dodania: 3.1.3 Endpointy API

Proponuję dodać nową sekcję 3.1.3 w głównym pliku dokumentacji technicznej (DOKUMENTACJA_TECHNICZNA.md):

```markdown
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
```

### 5.3 Sekcja do dodania: 9. Diagnostyka i rozwiązywanie problemów

Proponuję dodać nową sekcję 9 w głównym pliku dokumentacji technicznej (DOKUMENTACJA_TECHNICZNA.md):

```markdown
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
``` 