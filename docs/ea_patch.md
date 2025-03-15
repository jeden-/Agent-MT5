# Dokumentacja łatki dla komunikacji z Expert Advisor (EA)

## Problem

TMS OANDA zablokowała możliwość bezpośredniego otwierania i zamykania pozycji przez API MT5. W związku z tym tradycyjny mechanizm korzystający z `MT5Connector` i metod `open_position` oraz `close_position` nie działa. W logach widoczny jest błąd:

```
Unsupported filling mode (kod 10030)
```

Ten błąd występuje, ponieważ broker nie obsługuje trybów wypełnienia zleceń wymaganych przez API MetaTrader 5.

## Rozwiązanie

Jako rozwiązanie problemu stworzono serwer HTTP i skrypt Expert Advisor (EA) o nazwie `simple_http_AgentMT5_EA.mq5`, który jest dodawany do każdego instrumentu w platformie MT5. EA pośredniczy między naszym systemem a platformą MT5, wykonując zlecenia handlowe na podstawie komunikatów przesyłanych przez HTTP.

Zastosowano dwie łatki:
1. `apply_patch_for_ea_communication` - modyfikuje metodę `execute_signal` w klasie `TradingService`, aby używała `MT5ApiClient` do komunikacji z EA przy otwieraniu pozycji.
2. `patch_mt5_connector` z funkcją `patched_close_position` - modyfikuje metodę `close_position` w klasie `MT5Connector`, aby używała `MT5ApiClient` do komunikacji z EA przy zamykaniu pozycji.

## Schemat działania

### Otwieranie pozycji
1. `TradingService` analizuje sygnał handlowy i przygotowuje dane dla EA
2. Dane są wysyłane przez `MT5ApiClient` do endpointu `/position/open` na serwerze HTTP
3. Serwer przekazuje polecenie do EA działającego na platformie MT5
4. EA wykonuje operację otwierania pozycji i zwraca rezultat
5. Rezultat jest przekazywany z powrotem do `TradingService`, który tworzy odpowiednią transakcję

### Zamykanie pozycji
1. `MT5Connector` otrzymuje polecenie zamknięcia pozycji z określonym numerem ticketu
2. Funkcja `patched_close_position` tworzy instancję `MT5ApiClient` i przekazuje polecenie do EA
3. Dane są wysyłane do endpointu `/position/close` na serwerze HTTP
4. Serwer przekazuje polecenie do EA działającego na platformie MT5
5. EA wykonuje operację zamykania pozycji i zwraca rezultat
6. Wynik operacji jest przekazywany z powrotem do wywołującego kod

## Implementacja

### Łatka dla otwierania pozycji

Łatka dodaje nową metodę `patched_execute_signal` do klasy `TradingService`, która:

1. Sprawdza poprawność sygnału handlowego
2. Pobiera aktualne dane rynkowe dla instrumentu
3. Wylicza cenę wejścia dla zlecenia
4. Przygotowuje dane dla EA zgodnie z dokumentacją API
5. Wybiera odpowiedni EA ID do komunikacji
6. Wywołuje metodę `open_position` z klasy `MT5ApiClient`
7. Tworzy obiekt transakcji na podstawie wyniku działania EA

### Łatka dla zamykania pozycji

Łatka tworzy funkcję `patched_close_position`, która:

1. Pobiera informacje o pozycji o danym numerze ticketu
2. Tworzy instancję `MT5ApiClient` i wybiera odpowiedni EA ID
3. Wywołuje metodę `close_position` z klasy `MT5ApiClient`
4. Zwraca wynik operacji (True/False)

## Aktywacja łatek

Łatki są aktywowane automatycznie podczas uruchomienia systemu w funkcji `apply_all_patches()` w module `src.utils.patches`.

## Identyfikatory EA

System korzysta z następujących identyfikatorów EA:
- EA_1741779470
- EA_1741780868

## Format danych dla EA

### Otwieranie pozycji
```json
{
  "ea_id": "EA_1741779470",
  "symbol": "EURUSD",
  "order_type": "BUY",
  "volume": 0.1,
  "price": 1.12345,
  "sl": 1.10000,
  "tp": 1.15000,
  "comment": "Signal ID: 12345"
}
```

### Zamykanie pozycji
```json
{
  "ea_id": "EA_1741779470",
  "ticket": 89216817,
  "volume": null  // null oznacza zamknięcie całej pozycji
}
```

## Testowanie

Łatki zostały przetestowane za pomocą testów jednostkowych i integracyjnych, które weryfikują poprawność ich działania, oraz skryptu `close_excess_positions.py`, który wykorzystuje funkcję `patched_close_position`.

## Uwagi

- EA musi być poprawnie zainstalowany na platformie MT5 dla wszystkich instrumentów
- Serwer HTTP musi być uruchomiony i działać na porcie 5555
- W przypadku problemów z komunikacją należy sprawdzić logi serwera HTTP i EA
- Broker może czasowo blokować zbyt częste żądania - należy zadbać o odpowiednie odstępy między operacjami 