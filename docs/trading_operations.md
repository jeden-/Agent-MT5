# Dokumentacja operacji handlowych

## Spis treści
1. [Wprowadzenie](#wprowadzenie)
2. [Endpointy REST API](#endpointy-rest-api)
   - [Otwieranie pozycji](#otwieranie-pozycji)
   - [Zamykanie pozycji](#zamykanie-pozycji)
   - [Modyfikacja pozycji](#modyfikacja-pozycji)
   - [Pobieranie informacji o koncie](#pobieranie-informacji-o-koncie)
3. [Przykłady użycia](#przykłady-użycia)
4. [Obsługa błędów](#obsługa-błędów)

## Wprowadzenie

Moduł operacji handlowych umożliwia zarządzanie pozycjami na platformie MetaTrader 5 poprzez REST API. System oparty jest na architekturze polling, gdzie Expert Advisor (EA) regularnie sprawdza czy są nowe polecenia do wykonania.

Komunikacja odbywa się poprzez dwa główne kanały:
1. **Polecenia od serwera do EA**: EA pobiera polecenia z serwera HTTP poprzez endpoint `/commands`
2. **Dane od EA do serwera**: EA wysyła dane o aktualnych pozycjach, stanie konta i cenach rynkowych

## Endpointy REST API

### Otwieranie pozycji

**Endpoint:** `POST /position/open`

**Opis:** Otwiera nową pozycję na wybranym instrumencie

**Parametry obowiązkowe:**
- `ea_id` (string): Identyfikator EA, który ma wykonać polecenie
- `symbol` (string): Symbol instrumentu (np. "EURUSD")
- `order_type` (string): Typ zlecenia ("BUY" lub "SELL")
- `volume` (double): Wolumen transakcji (np. 0.1)

**Parametry opcjonalne:**
- `price` (double): Cena otwarcia (jeśli nie podana, użyta zostanie aktualna cena rynkowa)
- `sl` (double): Stop Loss (cena)
- `tp` (double): Take Profit (cena)
- `comment` (string): Komentarz do zlecenia

**Przykładowe zapytanie:**
```json
{
  "ea_id": "EA_12345",
  "symbol": "EURUSD",
  "order_type": "BUY",
  "volume": 0.1,
  "sl": 1.09000,
  "tp": 1.12000,
  "comment": "API_ORDER"
}
```

**Przykładowa odpowiedź:**
```json
{
  "status": "ok",
  "message": "Position open command added to queue"
}
```

### Zamykanie pozycji

**Endpoint:** `POST /position/close`

**Opis:** Zamyka istniejącą pozycję

**Parametry obowiązkowe:**
- `ea_id` (string): Identyfikator EA, który ma wykonać polecenie
- `ticket` (long): Numer ticketu/identyfikator pozycji

**Parametry opcjonalne:**
- `volume` (double): Wolumen do zamknięcia (jeśli mniejszy niż całkowity wolumen pozycji, wykonywane jest częściowe zamknięcie)

**Przykładowe zapytanie:**
```json
{
  "ea_id": "EA_12345",
  "ticket": 123456789,
  "volume": 0.05
}
```

**Przykładowa odpowiedź:**
```json
{
  "status": "ok",
  "message": "Position close command added to queue"
}
```

### Modyfikacja pozycji

**Endpoint:** `POST /position/modify`

**Opis:** Modyfikuje parametry istniejącej pozycji (SL, TP)

**Parametry obowiązkowe:**
- `ea_id` (string): Identyfikator EA, który ma wykonać polecenie
- `ticket` (long): Numer ticketu/identyfikator pozycji

**Parametry opcjonalne (co najmniej jeden musi być podany):**
- `sl` (double): Nowa wartość Stop Loss
- `tp` (double): Nowa wartość Take Profit

**Przykładowe zapytanie:**
```json
{
  "ea_id": "EA_12345",
  "ticket": 123456789,
  "sl": 1.09500,
  "tp": 1.12500
}
```

**Przykładowa odpowiedź:**
```json
{
  "status": "ok",
  "message": "Position modification command added to queue"
}
```

### Pobieranie informacji o koncie

**Endpoint:** `GET /account_info/get`

**Opis:** Pobiera aktualne informacje o stanie konta, które zostały wcześniej wysłane przez Expert Advisor

**Parametry obowiązkowe:**
- `ea_id` (string): Identyfikator EA, którego informacje o koncie chcemy pobrać

**Przykładowe zapytanie:**
```
GET /account_info/get?ea_id=EA_12345 HTTP/1.1
Host: 127.0.0.1:5555
```

**Przykładowa odpowiedź (gdy dane są dostępne):**
```json
{
  "status": "ok",
  "account_info": {
    "account": 12345678,
    "balance": 10000.00,
    "equity": 10050.00,
    "margin": 200.00,
    "free_margin": 9850.00,
    "currency": "USD",
    "profit": 50.00,
    "name": "Test Account",
    "leverage": 100,
    "last_update": "2025-03-10 12:00:00"
  }
}
```

**Przykładowa odpowiedź (gdy dane nie są dostępne):**
```json
{
  "status": "warning",
  "message": "No account information for EA EA_12345",
  "account_info": {}
}
```

## Przykłady użycia

### Python - otwieranie pozycji

```python
import requests
import json

url = "http://127.0.0.1:5555/position/open"
headers = {"Content-Type": "application/json"}
data = {
    "ea_id": "EA_12345",
    "symbol": "EURUSD",
    "order_type": "BUY",
    "volume": 0.1,
    "sl": 1.09000,
    "tp": 1.12000
}

response = requests.post(url, headers=headers, data=json.dumps(data))
print(response.json())
```

### Python - zamykanie pozycji

```python
import requests
import json

url = "http://127.0.0.1:5555/position/close"
headers = {"Content-Type": "application/json"}
data = {
    "ea_id": "EA_12345",
    "ticket": 123456789
}

response = requests.post(url, headers=headers, data=json.dumps(data))
print(response.json())
```

### Python - pobieranie informacji o koncie

```python
import requests

url = "http://127.0.0.1:5555/account_info/get?ea_id=EA_12345"
response = requests.get(url)
print(response.json())

# Obsługa danych konta
account_data = response.json()
if account_data['status'] == 'ok':
    account_info = account_data['account_info']
    print(f"Stan konta: {account_info['balance']} {account_info['currency']}")
    print(f"Equity: {account_info['equity']} {account_info['currency']}")
    print(f"Aktualny zysk: {account_info['profit']} {account_info['currency']}")
else:
    print(f"Brak danych konta: {account_data['message']}")
```

## Obsługa błędów

Serwer zwraca odpowiedzi w formacie JSON z polami:
- `status`: "ok" lub "error"
- `message`: Komunikat tekstowy opisujący wynik operacji lub błąd

### Kody HTTP

- `200 OK`: Zapytanie zostało pomyślnie przetworzone
- `400 Bad Request`: Brakujące lub nieprawidłowe parametry
- `404 Not Found`: Nieznany endpoint
- `500 Internal Server Error`: Błąd po stronie serwera

### Typowe błędy

1. **Brak obowiązkowych parametrów**
```json
{
  "status": "error",
  "message": "Missing required fields. Required: ['ea_id', 'symbol', 'order_type', 'volume']"
}
```

2. **Nieznany endpoint**
```json
{
  "status": "error",
  "message": "Endpoint not found"
}
```

3. **Nieprawidłowy JSON**
```json
{
  "status": "error",
  "message": "Invalid JSON"
}
```

## Uwagi dotyczące obsługi EA

Expert Advisor musi być odpowiednio skonfigurowany, aby odczytywać i wykonywać polecenia z serwera:

1. Upewnij się, że EA ma ustawioną prawidłową wartość `ServerURL`
2. EA musi mieć włączone uprawnienia do WebRequest w MetaTrader 5
3. EA odczytuje polecenia co określony czas (domyślnie co 5 sekund)
4. Upewnij się, że EA ma włączone uprawnienia do handlu automatycznego (przycisk "Autotrading" w MT5) 