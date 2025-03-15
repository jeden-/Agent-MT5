# Integracja z MetaTrader 5

## 1. Wstęp

AgentMT5 wykorzystuje hybrydowy model komunikacji z platformą MetaTrader 5, co pozwala na efektywne działanie zarówno w zakresie odczytu danych rynkowych, jak i wykonywania operacji handlowych. Dokument ten opisuje szczegółowo metody integracji, przepływ danych oraz najczęstsze problemy i ich rozwiązania.

## 2. Metody integracji z MT5

System AgentMT5 wykorzystuje dwa główne kanały komunikacji z platformą MetaTrader 5:

### 2.1 Expert Advisor (EA) z komunikacją HTTP

Expert Advisor jest programem napisanym w języku MQL5, który działa bezpośrednio w terminalu MetaTrader 5. W naszym systemie EA jest odpowiedzialny za:

- Wykonywanie operacji handlowych (otwieranie i zamykanie pozycji)
- Wysyłanie danych o aktualnych cenach i tickach
- Informowanie o zmianach w otwartych pozycjach
- Pobieranie komend z serwera HTTP

Komunikacja między EA a serwerem HTTP odbywa się przy użyciu protokołu HTTP, z wykorzystaniem formatu JSON do wymiany danych.

```
┌───────────────────┐     HTTP/JSON     ┌───────────────────┐
│   EA (MQL5)       │ ────────────────> │   Serwer HTTP     │
│   MetaTrader 5    │ <──────────────── │   (Python)        │
└───────────────────┘                   └───────────────────┘
```

### 2.2 Bezpośrednia integracja przez bibliotekę MetaTrader5 w Pythonie

Równolegle do komunikacji przez EA, system wykorzystuje bezpośrednią integrację z MT5 za pomocą oficjalnej biblioteki Python `MetaTrader5`. Ta metoda pozwala na:

- Bezpośrednie pobieranie danych historycznych
- Dostęp do informacji o koncie
- Pobieranie listy otwartych pozycji
- Pobieranie historii transakcji
- Monitorowanie stanu terminal MT5

```
┌───────────────────┐     Natywne API   ┌───────────────────┐
│   Terminal        │ <──────────────── │   MT5Server       │
│   MetaTrader 5    │ ────────────────> │   (Python)        │
└───────────────────┘                   └───────────────────┘
```

## 3. Konfiguracja i inicjalizacja

### 3.1 Instalacja biblioteki MetaTrader5

```bash
pip install MetaTrader5
```

### 3.2 Inicjalizacja połączenia w kodzie

```python
import MetaTrader5 as mt5

# Inicjalizacja połączenia z terminalem
if not mt5.initialize():
    print(f"Inicjalizacja MT5 nie powiodła się, kod błędu: {mt5.last_error()}")
    # Obsługa błędu inicjalizacji
else:
    print(f"Wersja biblioteki MT5: {mt5.version()}")
    # Dalsze operacje
```

### 3.3 Parametry EA w MetaTrader 5

Expert Advisor wymaga skonfigurowania następujących parametrów:

- **Server URL** - adres serwera HTTP (domyślnie: http://127.0.0.1:5555)
- **Update Interval** - częstotliwość wysyłania danych (w milisekundach)
- **EA ID** - unikalny identyfikator EA
- **Symbols to Monitor** - lista instrumentów do monitorowania

## 4. Przepływ danych

### 4.1 Pobieranie danych rynkowych

#### 4.1.1 Przez API Python

```python
# Pobieranie danych historycznych
def get_market_data(symbol, timeframe, count=100):
    # Mapowanie timeframe'ów
    timeframe_map = {
        "M1": mt5.TIMEFRAME_M1,
        "M5": mt5.TIMEFRAME_M5,
        "M15": mt5.TIMEFRAME_M15,
        "H1": mt5.TIMEFRAME_H1,
        "D1": mt5.TIMEFRAME_D1
    }
    
    # Pobieranie danych
    if timeframe in timeframe_map:
        rates = mt5.copy_rates_from_pos(symbol, timeframe_map[timeframe], 0, count)
        return rates
    else:
        return None
```

#### 4.1.2 Przez EA (otrzymywane na endpoint `/market/data`)

```json
{
  "symbol": "EURUSD",
  "timeframe": "M15",
  "data": {
    "open": 1.0850,
    "high": 1.0855,
    "low": 1.0845,
    "close": 1.0852,
    "volume": 2450,
    "time": "2023-03-10T15:45:00"
  }
}
```

### 4.2 Zarządzanie pozycjami

#### 4.2.1 Otwieranie pozycji

```python
def open_position(symbol, order_type, volume, price=0.0, sl=0.0, tp=0.0, comment=""):
    # Ustalenie typu zlecenia
    if order_type.upper() == "BUY":
        order_type_mt5 = mt5.ORDER_TYPE_BUY
    elif order_type.upper() == "SELL":
        order_type_mt5 = mt5.ORDER_TYPE_SELL
    else:
        return {"status": "error", "message": "Nieznany typ zlecenia"}
    
    # Przygotowanie zlecenia
    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": float(volume),
        "type": order_type_mt5,
        "price": price,
        "sl": sl,
        "tp": tp,
        "comment": comment,
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }
    
    # Wysłanie zlecenia
    result = mt5.order_send(request)
    
    # Obsługa wyniku
    if result.retcode == mt5.TRADE_RETCODE_DONE:
        return {
            "status": "success",
            "ticket": result.order,
            "message": "Pozycja otwarta"
        }
    else:
        return {
            "status": "error",
            "code": result.retcode,
            "message": f"Błąd otwarcia pozycji: {result.comment}"
        }
```

#### 4.2.2 Zamykanie pozycji

```python
def close_position(ticket):
    # Pobieranie informacji o pozycji
    positions = mt5.positions_get(ticket=ticket)
    if positions:
        position = positions[0]
    else:
        return {"status": "error", "message": "Nie znaleziono pozycji"}
    
    # Odwrócenie kierunku dla zamknięcia
    if position.type == mt5.POSITION_TYPE_BUY:
        order_type = mt5.ORDER_TYPE_SELL
        price = mt5.symbol_info_tick(position.symbol).bid
    else:
        order_type = mt5.ORDER_TYPE_BUY
        price = mt5.symbol_info_tick(position.symbol).ask
    
    # Przygotowanie zlecenia zamknięcia
    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": position.symbol,
        "volume": position.volume,
        "type": order_type,
        "position": position.ticket,
        "price": price,
        "comment": "Zamknięcie pozycji",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }
    
    # Wysłanie zlecenia
    result = mt5.order_send(request)
    
    # Obsługa wyniku
    if result.retcode == mt5.TRADE_RETCODE_DONE:
        return {"status": "success", "message": "Pozycja zamknięta"}
    else:
        return {
            "status": "error",
            "code": result.retcode,
            "message": f"Błąd zamknięcia pozycji: {result.comment}"
        }
```

#### 4.2.3 Modyfikacja pozycji

```python
def modify_position(ticket, sl=None, tp=None):
    # Aktualizacja tylko podanych parametrów
    request = {
        "action": mt5.TRADE_ACTION_SLTP,
        "position": ticket
    }
    
    # Dodanie SL/TP tylko jeśli są określone
    if sl is not None:
        request["sl"] = sl
    if tp is not None:
        request["tp"] = tp
    
    # Wysłanie zlecenia
    result = mt5.order_send(request)
    
    # Obsługa wyniku
    if result.retcode == mt5.TRADE_RETCODE_DONE:
        return {"status": "success", "message": "Pozycja zmodyfikowana"}
    else:
        return {
            "status": "error",
            "code": result.retcode,
            "message": f"Błąd modyfikacji pozycji: {result.comment}"
        }
```

### 4.3 Pobieranie informacji o koncie

```python
def get_account_info():
    # Pobieranie informacji o koncie
    account_info = mt5.account_info()
    if account_info:
        return {
            "balance": account_info.balance,
            "equity": account_info.equity,
            "margin": account_info.margin,
            "free_margin": account_info.margin_free,
            "margin_level": account_info.margin_level,
            "positions": mt5.positions_total()
        }
    else:
        return {}
```

## 5. Endpointy API

Serwer HTTP udostępnia następujące endpointy dla komunikacji z EA:

| Endpoint | Metoda | Opis |
|----------|--------|------|
| `/ping` | GET/POST | Sprawdzenie połączenia |
| `/market/data` | POST | Odbieranie danych rynkowych od EA |
| `/position/update` | POST | Aktualizacja informacji o pozycjach |
| `/account/info` | GET | Pobieranie informacji o koncie |
| `/commands` | GET | Pobieranie komend do wykonania przez EA |
| `/agent/start` | POST | Uruchomienie agenta |
| `/agent/stop` | POST | Zatrzymanie agenta |
| `/agent/status` | GET | Sprawdzenie statusu agenta |

## 6. Rozwiązywanie problemów

### 6.1 Typowe problemy z połączeniem

#### Problem: Nie można zainicjalizować MT5
Rozwiązanie:
1. Sprawdź, czy terminal MT5 jest uruchomiony
2. Upewnij się, że korzystasz z tej samej bitowości (32/64-bit) Pythona co MT5
3. Sprawdź uprawnienia do folderu MT5

#### Problem: Błędy HTTP w EA
Rozwiązanie:
1. Sprawdź, czy serwer HTTP jest uruchomiony
2. Zweryfikuj adres IP i port w ustawieniach EA
3. Sprawdź, czy firewall nie blokuje połączeń

#### Problem: Zlecenia nie są wykonywane
Rozwiązanie:
1. Sprawdź, czy konto ma wystarczające środki
2. Zweryfikuj, czy symbol jest dostępny do handlu w obecnych godzinach
3. Sprawdź logi błędów w MT5 (F12)

### 6.2 Monitorowanie i debugowanie

#### Logi z MT5

Terminal MT5 pozwala na przeglądanie logów EA poprzez naciśnięcie F12 lub Menu > Tools > MetaQuotes Language Editor > Tools > Journal.

#### Logi z serwera HTTP

Serwer HTTP zapisuje logi w katalogu `logs/`. Można je przeglądać w celu diagnozowania problemów z komunikacją.

## 7. Zabezpieczenia i dobre praktyki

### 7.1 Bezpieczeństwo

1. Używaj tylko lokalnego połączenia HTTP (127.0.0.1) dla komunikacji EA z serwerem
2. Nie przechowuj poświadczeń MT5 w kodzie (używaj zmiennych środowiskowych)
3. Zabezpiecz komunikację HTTPS, jeśli serwer ma być dostępny z zewnątrz
4. Implementuj limity częstotliwości zapytań dla ochrony przed DoS

### 7.2 Optymalizacja wydajności

1. Ograniczaj częstotliwość zapytań do MT5 (nie częściej niż 10 razy na sekundę)
2. Implementuj buforowanie dla często używanych danych
3. Używaj asynchronicznej komunikacji dla operacji niekrytycznych
4. Monitoruj i optymalizuj czas odpowiedzi serwera HTTP

## 8. Dalsza rozbudowa integracji

### 8.1 Możliwe rozszerzenia

1. Integracja z dodatkowymi danymi ekonomicznymi
2. Implementacja automatycznego backupu i przywracania konfiguracji EA
3. Rozszerzenie o wsparcie dla wielu terminali MT5 jednocześnie
4. Dodanie WebSocket dla komunikacji w czasie rzeczywistym

### 8.2 Znane ograniczenia

1. Biblioteka MetaTrader5 dla Pythona ma ograniczoną funkcjonalność w porównaniu z MQL5
2. Niektóre operacje (np. otwieranie/zamykanie pozycji) mogą być blokowane przez brokerów
3. Terminal MT5 musi być uruchomiony dla działania integracji
4. Między EA a serwerem HTTP mogą występować opóźnienia w komunikacji 