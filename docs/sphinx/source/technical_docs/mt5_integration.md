# Integracja z MetaTrader 5

## Wstęp

AgentMT5 wykorzystuje hybrydowy model komunikacji z platformą MetaTrader 5, co pozwala na efektywne działanie zarówno w zakresie odczytu danych rynkowych, jak i wykonywania operacji handlowych. Dokument ten opisuje szczegółowo metody integracji, przepływ danych oraz najczęstsze problemy i ich rozwiązania.

## Metody integracji z MT5

System AgentMT5 wykorzystuje dwa główne kanały komunikacji z platformą MetaTrader 5:

### Expert Advisor (EA) z komunikacją HTTP

Expert Advisor jest programem napisanym w języku MQL5, który działa bezpośrednio w terminalu MetaTrader 5. W naszym systemie EA jest odpowiedzialny za:

- Wykonywanie operacji handlowych (otwieranie i zamykanie pozycji)
- Wysyłanie danych o aktualnych cenach i tickach
- Informowanie o zmianach w otwartych pozycjach
- Pobieranie komend z serwera HTTP

Komunikacja między EA a serwerem HTTP odbywa się przy użyciu protokołu HTTP, z wykorzystaniem formatu JSON do wymiany danych.

### Bezpośrednia integracja przez Python API

Równolegle do komunikacji przez EA, system wykorzystuje bezpośrednią integrację z MT5 przez bibliotekę Python:

- Pobieranie historycznych danych rynkowych
- Odczytywanie stanu konta i otwartych pozycji
- Monitorowanie zdarzeń rynkowych
- Wykonywanie operacji handlowych w przypadku awarii EA

## Architektura komunikacji

```
+----------------+                  +----------------+
|                |  1. HTTP/JSON    |                |
|  MetaTrader 5  | <--------------> |   MT5 Bridge   |
|     (EA)       |                  |    (Server)    |
|                |                  |                |
+----------------+                  +----------------+
        ^                                   ^
        |                                   |
        | 2. Python API                     |
        |                                   |
        v                                   v
+----------------+                  +----------------+
|                |                  |                |
|  MetaTrader 5  | <--------------> |   MT5 Bridge   |
|   (Terminal)   |  3. Direct API   |    (Client)    |
|                |                  |                |
+----------------+                  +----------------+
```

## Przepływ danych

### Odczyt danych rynkowych

1. EA zbiera dane o aktualnych cenach i tickach
2. Dane są formatowane do JSON i wysyłane do serwera HTTP
3. Serwer przetwarza dane i zapisuje je w bazie danych
4. Równolegle, klient Python API pobiera historyczne dane bezpośrednio z terminala MT5
5. Dane są łączone i udostępniane dla modułów analitycznych

### Wykonywanie operacji handlowych

1. System generuje sygnał handlowy
2. Serwer HTTP przygotowuje komendę w formacie JSON
3. EA pobiera komendę podczas regularnego odpytywania serwera
4. EA wykonuje operację handlową w terminalu MT5
5. EA wysyła potwierdzenie wykonania operacji do serwera
6. W przypadku awarii EA, operacja jest wykonywana bezpośrednio przez Python API

## Implementacja MT5 Bridge

Moduł MT5 Bridge składa się z dwóch głównych komponentów:

### Serwer HTTP

Serwer HTTP jest implementowany przy użyciu FastAPI i udostępnia następujące endpointy:

- `/api/v1/mt5/data` - odbieranie danych rynkowych od EA
- `/api/v1/mt5/positions` - odbieranie informacji o pozycjach
- `/api/v1/mt5/account` - odbieranie informacji o koncie
- `/api/v1/mt5/commands` - udostępnianie komend dla EA
- `/api/v1/mt5/status` - sprawdzanie statusu połączenia

### Klient Python API

Klient Python API wykorzystuje bibliotekę `MetaTrader5` do bezpośredniej komunikacji z terminalem:

- `MT5Client.connect()` - nawiązywanie połączenia z terminalem
- `MT5Client.get_account_info()` - pobieranie informacji o koncie
- `MT5Client.get_positions()` - pobieranie informacji o otwartych pozycjach
- `MT5Client.get_history()` - pobieranie historii transakcji
- `MT5Client.place_order()` - składanie zlecenia
- `MT5Client.close_position()` - zamykanie pozycji

## Synchronizacja i obsługa błędów

System implementuje mechanizmy synchronizacji i obsługi błędów:

- Regularne sprawdzanie spójności danych między EA a bezpośrednim API
- Automatyczne przełączanie między kanałami komunikacji w przypadku awarii
- Buforowanie komend w przypadku problemów z komunikacją
- Mechanizm ponownych prób dla nieudanych operacji
- Logowanie wszystkich operacji i błędów

## Najczęstsze problemy i rozwiązania

### Problem: Brak połączenia z EA

**Rozwiązanie:**
1. Sprawdź, czy EA jest aktywny na wykresie
2. Zweryfikuj ustawienia serwera w EA
3. Sprawdź logi EA w terminalu MT5
4. Zrestartuj terminal MT5

### Problem: Opóźnienia w wykonywaniu operacji

**Rozwiązanie:**
1. Zoptymalizuj częstotliwość odpytywania serwera przez EA
2. Zwiększ priorytet EA w ustawieniach MT5
3. Sprawdź obciążenie serwera HTTP
4. Rozważ bezpośrednie wykonanie przez Python API

### Problem: Rozbieżności w danych

**Rozwiązanie:**
1. Uruchom procedurę synchronizacji danych
2. Sprawdź ustawienia czasowe na serwerze i terminalu
3. Zweryfikuj format danych w komunikacji JSON
4. Wyczyść cache danych w systemie 