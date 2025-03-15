# Konfiguracja systemu

## Plik konfiguracyjny .env

Główna konfiguracja systemu AgentMT5 znajduje się w pliku `.env`. Poniżej opisano najważniejsze parametry konfiguracyjne:

### Konfiguracja bazy danych

```
# Konfiguracja bazy danych
DB_HOST=localhost
DB_PORT=5432
DB_NAME=mt5remotetest
DB_USER=mt5remote
DB_PASSWORD=mt5remote

# Parametry połączenia z bazą
DB_POOL_MIN_SIZE=5
DB_POOL_MAX_SIZE=20
DB_COMMAND_TIMEOUT=60
DB_CONNECT_TIMEOUT=30
DB_MAX_RETRIES=3
DB_RETRY_INTERVAL=5
```

### Konfiguracja MetaTrader 5

```
# Konfiguracja MT5
MT5_LOGIN=62499981
MT5_PASSWORD=*********
MT5_SERVER=OANDATMS-MT5
```

### Konfiguracja API

```
# Konfiguracja API
API_HOST=0.0.0.0
API_PORT=8000
API_DEBUG=True
```

### Konfiguracja logowania

```
# Konfiguracja logowania
LOG_LEVEL=INFO
LOG_FILE=mt5remoteai.log
```

### Konfiguracja modeli AI

```
# Konfiguracja RAG
RAG_MODEL=all-MiniLM-L6-v2
RAG_PERSIST_DIR=market_memory

# Konfiguracja Claude API
ANTHROPIC_API_KEY=sk-ant-api03-*****

# Konfiguracja Grok API
XAI_API_KEY=xai-*****
```

## Konfiguracja strategii handlowych

Strategie handlowe są konfigurowane w bazie danych i mogą być modyfikowane przez interfejs użytkownika. Główne parametry strategii to:

### Parametry ogólne

- **Nazwa strategii** - unikalna nazwa strategii
- **Opis** - krótki opis działania strategii
- **Aktywna** - czy strategia jest aktywna
- **Model AI** - model AI używany przez strategię (Claude, Grok, DeepSeek)
- **Tryb pracy** - tryb pracy strategii (obserwacja, półautomatyczny, automatyczny)

### Parametry zarządzania ryzykiem

- **Maksymalna wielkość pozycji** - maksymalna wielkość pojedynczej pozycji (w lotach)
- **Maksymalna ekspozycja** - maksymalna łączna ekspozycja na rynku (% kapitału)
- **Maksymalna strata dzienna** - maksymalna dopuszczalna strata dzienna (% kapitału)
- **Maksymalna strata na pozycję** - maksymalna dopuszczalna strata na pojedynczą pozycję (% kapitału)
- **Domyślny Stop Loss** - domyślny poziom Stop Loss (w punktach)
- **Domyślny Take Profit** - domyślny poziom Take Profit (w punktach)
- **Trailing Stop** - czy używać Trailing Stop
- **Poziom aktywacji Trailing Stop** - poziom aktywacji Trailing Stop (w punktach)

### Parametry czasowe

- **Godziny handlu** - godziny, w których strategia może handlować
- **Dni handlu** - dni tygodnia, w których strategia może handlować
- **Czas ważności sygnału** - czas ważności sygnału handlowego (w minutach)

### Parametry instrumentów

- **Lista instrumentów** - lista instrumentów, na których strategia może handlować
- **Maksymalna liczba pozycji na instrument** - maksymalna liczba otwartych pozycji na jeden instrument
- **Minimalny spread** - minimalny spread, przy którym strategia może handlować

## Konfiguracja Expert Advisor

Expert Advisor (EA) dla MetaTrader 5 jest konfigurowany w pliku `AgentMT5.mq5`. Główne parametry EA to:

### Parametry połączenia

```
// Parametry połączenia z serwerem
input string ServerURL = "http://localhost:8000";
input int UpdateInterval = 1000; // Interwał aktualizacji w milisekundach
```

### Parametry logowania

```
// Parametry logowania
input bool EnableLogging = true;
input bool VerboseLogging = false;
```

### Parametry handlowe

```
// Parametry handlowe
input bool AllowTrading = true;
input double MaxSlippage = 3.0; // Maksymalny poślizg w punktach
```

## Konfiguracja monitoringu

System monitoringu jest konfigurowany w pliku `config/monitoring.json`. Główne parametry to:

### Alerty

```json
{
  "alerts": {
    "email": {
      "enabled": true,
      "recipients": ["user@example.com"],
      "server": "smtp.example.com",
      "port": 587,
      "username": "alerts@example.com",
      "password": "*****"
    },
    "telegram": {
      "enabled": false,
      "bot_token": "",
      "chat_id": ""
    }
  }
}
```

### Metryki

```json
{
  "metrics": {
    "performance": {
      "track_daily_pnl": true,
      "track_drawdown": true,
      "track_win_rate": true
    },
    "system": {
      "track_cpu_usage": true,
      "track_memory_usage": true,
      "track_api_latency": true
    }
  }
}
```

## Konfiguracja interfejsu użytkownika

Interfejs użytkownika jest konfigurowany w pliku `config/ui.json`. Główne parametry to:

```json
{
  "ui": {
    "theme": "dark",
    "language": "pl",
    "refresh_interval": 5,
    "default_view": "dashboard",
    "charts": {
      "default_timeframe": "H1",
      "default_indicators": ["MA", "RSI", "MACD"]
    }
  }
}
``` 