# Referencja API

## Przegląd API

AgentMT5 udostępnia REST API, które umożliwia integrację z zewnętrznymi systemami. API jest dostępne pod adresem `http://localhost:8000/api/v1/`.

## Autentykacja

Wszystkie zapytania do API wymagają autentykacji za pomocą tokenu API. Token należy przekazać w nagłówku `Authorization`:

```
Authorization: Bearer <token>
```

Token API można wygenerować w interfejsie użytkownika w sekcji "Ustawienia" -> "API".

## Endpointy

### Konto

#### Pobieranie informacji o koncie

```
GET /api/v1/account
```

Przykładowa odpowiedź:

```json
{
  "account_id": 62499981,
  "balance": 10000.0,
  "equity": 10050.0,
  "margin": 500.0,
  "free_margin": 9550.0,
  "margin_level": 2010.0,
  "leverage": 100,
  "currency": "USD"
}
```

### Pozycje

#### Pobieranie listy otwartych pozycji

```
GET /api/v1/positions
```

Przykładowa odpowiedź:

```json
{
  "positions": [
    {
      "position_id": 123456,
      "symbol": "EURUSD",
      "type": "buy",
      "volume": 0.1,
      "open_price": 1.1050,
      "current_price": 1.1070,
      "profit": 20.0,
      "swap": -1.2,
      "open_time": "2025-03-10T14:30:00Z",
      "stop_loss": 1.1000,
      "take_profit": 1.1100
    }
  ]
}
```

#### Otwieranie nowej pozycji

```
POST /api/v1/positions
```

Parametry zapytania:

```json
{
  "symbol": "EURUSD",
  "type": "buy",
  "volume": 0.1,
  "price": 0.0,
  "stop_loss": 1.1000,
  "take_profit": 1.1100,
  "comment": "API order"
}
```

Przykładowa odpowiedź:

```json
{
  "position_id": 123457,
  "symbol": "EURUSD",
  "type": "buy",
  "volume": 0.1,
  "open_price": 1.1055,
  "current_price": 1.1055,
  "profit": 0.0,
  "swap": 0.0,
  "open_time": "2025-03-11T10:15:00Z",
  "stop_loss": 1.1000,
  "take_profit": 1.1100
}
```

#### Modyfikacja pozycji

```
PUT /api/v1/positions/{position_id}
```

Parametry zapytania:

```json
{
  "stop_loss": 1.1010,
  "take_profit": 1.1110
}
```

Przykładowa odpowiedź:

```json
{
  "position_id": 123457,
  "symbol": "EURUSD",
  "type": "buy",
  "volume": 0.1,
  "open_price": 1.1055,
  "current_price": 1.1060,
  "profit": 5.0,
  "swap": 0.0,
  "open_time": "2025-03-11T10:15:00Z",
  "stop_loss": 1.1010,
  "take_profit": 1.1110
}
```

#### Zamykanie pozycji

```
DELETE /api/v1/positions/{position_id}
```

Przykładowa odpowiedź:

```json
{
  "position_id": 123457,
  "symbol": "EURUSD",
  "type": "buy",
  "volume": 0.1,
  "open_price": 1.1055,
  "close_price": 1.1065,
  "profit": 10.0,
  "swap": 0.0,
  "open_time": "2025-03-11T10:15:00Z",
  "close_time": "2025-03-11T11:30:00Z"
}
```

### Dane rynkowe

#### Pobieranie aktualnych cen

```
GET /api/v1/market/prices?symbols=EURUSD,GBPUSD
```

Przykładowa odpowiedź:

```json
{
  "prices": [
    {
      "symbol": "EURUSD",
      "bid": 1.1060,
      "ask": 1.1062,
      "time": "2025-03-11T11:35:00Z"
    },
    {
      "symbol": "GBPUSD",
      "bid": 1.3120,
      "ask": 1.3123,
      "time": "2025-03-11T11:35:00Z"
    }
  ]
}
```

#### Pobieranie danych historycznych

```
GET /api/v1/market/history?symbol=EURUSD&timeframe=H1&count=10
```

Przykładowa odpowiedź:

```json
{
  "symbol": "EURUSD",
  "timeframe": "H1",
  "data": [
    {
      "time": "2025-03-11T10:00:00Z",
      "open": 1.1050,
      "high": 1.1070,
      "low": 1.1045,
      "close": 1.1065,
      "volume": 1250
    },
    {
      "time": "2025-03-11T09:00:00Z",
      "open": 1.1040,
      "high": 1.1055,
      "low": 1.1035,
      "close": 1.1050,
      "volume": 1100
    }
  ]
}
```

### AI

#### Generowanie analizy rynku

```
POST /api/v1/ai/analyze
```

Parametry zapytania:

```json
{
  "symbol": "EURUSD",
  "timeframe": "H1",
  "model": "claude"
}
```

Przykładowa odpowiedź:

```json
{
  "analysis": {
    "trend": "bullish",
    "strength": 0.75,
    "support_levels": [1.1000, 1.0950],
    "resistance_levels": [1.1100, 1.1150],
    "recommendation": "buy",
    "confidence": 0.8,
    "reasoning": "Cena EURUSD pokazuje silny trend wzrostowy z formacją podwójnego dna na wykresie H1. Wskaźniki techniczne (RSI, MACD) potwierdzają sygnał kupna. Najbliższy poziom oporu znajduje się na 1.1100."
  }
}
```

#### Generowanie prognozy

```
POST /api/v1/ai/forecast
```

Parametry zapytania:

```json
{
  "symbol": "EURUSD",
  "timeframe": "H1",
  "model": "grok",
  "horizon": 24
}
```

Przykładowa odpowiedź:

```json
{
  "forecast": {
    "symbol": "EURUSD",
    "timeframe": "H1",
    "horizon": 24,
    "predictions": [
      {
        "time": "2025-03-11T12:00:00Z",
        "price": 1.1070,
        "confidence": 0.85
      },
      {
        "time": "2025-03-11T13:00:00Z",
        "price": 1.1080,
        "confidence": 0.80
      }
    ],
    "summary": "Prognoza wskazuje na kontynuację trendu wzrostowego w ciągu najbliższych 24 godzin, z potencjalnym osiągnięciem poziomu 1.1100 w ciągu 12 godzin."
  }
}
```

### System

#### Pobieranie statusu systemu

```
GET /api/v1/system/status
```

Przykładowa odpowiedź:

```json
{
  "status": "running",
  "uptime": 86400,
  "mt5_connected": true,
  "ai_models": {
    "claude": "available",
    "grok": "available",
    "deepseek": "unavailable"
  },
  "active_strategies": 2,
  "open_positions": 3,
  "cpu_usage": 25.5,
  "memory_usage": 512.3
}
```

#### Pobieranie logów

```
GET /api/v1/system/logs?level=error&count=10
```

Przykładowa odpowiedź:

```json
{
  "logs": [
    {
      "time": "2025-03-11T11:30:00Z",
      "level": "error",
      "component": "mt5_bridge",
      "message": "Failed to connect to MT5 terminal"
    },
    {
      "time": "2025-03-11T10:15:00Z",
      "level": "error",
      "component": "ai_controller",
      "message": "API rate limit exceeded for Claude API"
    }
  ]
}
```

## Kody błędów

| Kod | Opis |
|-----|------|
| 400 | Nieprawidłowe zapytanie |
| 401 | Brak autoryzacji |
| 403 | Brak uprawnień |
| 404 | Zasób nie znaleziony |
| 429 | Przekroczono limit zapytań |
| 500 | Błąd serwera |

## Limity API

- Maksymalnie 100 zapytań na minutę
- Maksymalnie 5000 zapytań na godzinę
- Maksymalnie 50000 zapytań na dzień

## Wersjonowanie

API jest wersjonowane w ścieżce URL. Aktualna wersja to `v1`. Przyszłe wersje będą dostępne pod ścieżkami `/api/v2/`, `/api/v3/` itd. 