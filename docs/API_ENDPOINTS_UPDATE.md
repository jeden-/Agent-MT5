# Aktualizacja Dokumentacji API - Marzec 2025

## Dodane endpointy

### Endpoint /mt5/account

Endpoint służy do pobierania informacji o koncie MetaTrader 5.

#### Metoda
`GET`

#### URL
```
http://localhost:8000/mt5/account
```

#### Parametry
Brak

#### Odpowiedź

Powodzenie:
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

Błąd (gdy serwer MT5 jest niedostępny):
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

Uwaga: W przypadku błędu połączenia z MT5, system zwraca przykładowe dane o koncie z flagą `status: "ok"` dla zachowania kompatybilności z istniejącymi klientami.

## Zaktualizowane komponenty

### MT5ApiClient

Dokonano aktualizacji metody `get_account_info()` w klasie `MT5ApiClient`. Metoda ta teraz łączy się z poprawnym endpointem `/mt5/account` zamiast poprzedniego (`account_info/get`).

```python
def get_account_info(self) -> Dict[str, Any]:
    """
    Pobiera informacje o koncie MT5.
    
    Returns:
        Słownik z informacjami o koncie lub pusty słownik w przypadku błędu.
    """
    result = self.send_request("mt5/account")
    return result or {}
```

## Diagnostyka błędów połączenia

### Problem: 'NoneType' object has no attribute 'status_code'

Ten błąd występuje, gdy klient API próbuje połączyć się z nieistniejącym endpointem lub gdy serwer MT5 nie odpowiada. Komunikat wskazuje, że funkcja `send_request()` zwróciła `None` zamiast obiektu odpowiedzi HTTP.

#### Rozwiązanie:

1. Sprawdź czy endpoint jest poprawnie skonfigurowany w kliencie API
2. Upewnij się, że serwer HTTP działa na oczekiwanym porcie (np. 8000)
3. Sprawdź logi serwera pod kątem błędów
4. Zweryfikuj, czy zdefiniowano handler dla endpointu w klasie `MT5Server`

## Porty używane przez system

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

## Dodane endpointy AI

### Endpoint /ai/signals/latest

Endpoint służy do pobierania najnowszych sygnałów generowanych przez modele AI.

#### Metoda
`GET`

#### URL
```
http://localhost:8000/ai/signals/latest
```

#### Parametry
Brak

#### Odpowiedź

Powodzenie:
```json
{
  "status": "ok",
  "signals": [
    {
      "id": "sig004",
      "model": "Claude",
      "symbol": "US100",
      "type": "BUY",
      "confidence": 0.85,
      "timestamp": "2025-03-12T09:35:26.316Z",
      "executed": false,
      "profit": null
    },
    {
      "id": "sig005",
      "model": "Grok",
      "symbol": "SILVER",
      "type": "SELL",
      "confidence": 0.78,
      "timestamp": "2025-03-12T09:35:26.316Z",
      "executed": false,
      "profit": null
    }
  ]
}
```

Błąd:
```json
{
  "status": "error",
  "message": "Błąd podczas pobierania najnowszych sygnałów: [opis błędu]",
  "signals": []
}
``` 