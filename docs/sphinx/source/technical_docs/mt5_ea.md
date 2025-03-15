# Dokumentacja Expert Advisor MT5 i systemu komunikacji

## Wprowadzenie

Ten dokument opisuje działanie Expert Advisora (EA) dla platformy MetaTrader 5 oraz systemu komunikacji między EA a aplikacją Python. Celem tego systemu jest umożliwienie automatycznego handlu na platformie MT5 sterowanego przez kod Python, który może wykorzystywać zaawansowane algorytmy AI.

## Struktura systemu

System składa się z dwóch głównych komponentów:

1. **Expert Advisor** - skrypt w języku MQL5 działający na platformie MT5
2. **Serwer MT5** - aplikacja Python obsługująca komunikację z EA

Komponenty te komunikują się ze sobą poprzez protokół TCP/IP, wymieniając komunikaty tekstowe o określonym formacie.

## Expert Advisor (EA)

### Pliki EA

- `AgentMT5_EA.mq5` - główny plik EA
- `Logger.mqh` - moduł logowania
- `ErrorHandler.mqh` - moduł obsługi błędów
- `Communication.mqh` - moduł komunikacji

### Instalacja EA

Aby zainstalować EA, należy:

1. Uruchomić platformę MetaTrader 5
2. Otworzyć MetaEditor (Narzędzia > MetaEditor lub F4)
3. Utworzyć nowy projekt Expert Advisor
4. Skopiować zawartość plików do odpowiednich plików w projekcie
5. Skompilować projekt (F7)
6. Zrestartować MT5 (jeśli było uruchomione)
7. Przeciągnąć skompilowany EA na wykres

### Konfiguracja EA

Expert Advisor posiada następujące parametry wejściowe:

- `ServerAddress` - adres serwera Python (domyślnie: 127.0.0.1)
- `ServerPort` - port serwera Python (domyślnie: 5555)
- `ConnectionTimeout` - timeout połączenia w milisekundach (domyślnie: 5000)
- `CommandCheckInterval` - częstotliwość sprawdzania komend w milisekundach (domyślnie: 1000)
- `EnableLogging` - włączenie logowania (domyślnie: true)
- `LogLevel` - poziom logowania (domyślnie: INFO, dostępne: DEBUG, INFO, WARNING, ERROR)

## Serwer MT5 (Python)

### Pliki serwera

- `mt5_server.py` - implementacja serwera
- `scripts/run_mt5_server.py` - skrypt do uruchomienia serwera

### Uruchomienie serwera

Aby uruchomić serwer, należy wykonać:

```bash
python scripts/run_mt5_server.py
```

Dostępne opcje:

- `--host` - adres hosta do nasłuchiwania (domyślnie: 127.0.0.1)
- `--port` - port do nasłuchiwania (domyślnie: 5555)
- `--ping-interval` - interwał pingowania EA w sekundach (domyślnie: 5)

### Korzystanie z MT5Server w kodzie

```python
from src.mt5_bridge import MT5Server

# Tworzenie i uruchomienie serwera
server = MT5Server(host='127.0.0.1', port=5555)
server.start()

# Rejestracja callbacków dla wydarzeń
def on_market_data(data):
    print(f"Otrzymano dane rynkowe: {data}")

server.register_callback("MARKET_DATA", on_market_data)

# Wysyłanie komend
server.open_position("EURUSD", "BUY", 0.1, sl=1.09, tp=1.12)
server.close_position(12345)
server.modify_position(12345, sl=1.08, tp=1.13)

# Pobieranie danych
market_data = server.get_market_data("EURUSD")
positions = server.get_positions_data()
account_info = server.get_account_info()

# Zatrzymanie serwera
server.stop()
```

## Protokół komunikacji

Komunikacja między EA a serwerem opiera się na prostym protokole tekstowym:

### Format wiadomości

```
MESSAGE_TYPE:MESSAGE_DATA
```

Gdzie:
- `MESSAGE_TYPE` - typ wiadomości (np. MARKET_DATA, OPEN_POSITION)
- `MESSAGE_DATA` - dane wiadomości w formacie `KEY:VALUE;KEY:VALUE;...`

### Typy wiadomości od EA do serwera

- `INIT` - informacja o inicjalizacji EA
- `DEINIT` - informacja o zatrzymaniu EA
- `MARKET_DATA` - dane rynkowe
- `POSITIONS_UPDATE` - aktualizacja pozycji
- `ACCOUNT_INFO` - informacje o koncie
- `SUCCESS` - potwierdzenie wykonania operacji
- `ERROR` - informacja o błędzie
- `PONG` - odpowiedź na ping

### Typy komend od serwera do EA

- `OPEN_POSITION` - otwarcie pozycji
- `CLOSE_POSITION` - zamknięcie pozycji
- `MODIFY_POSITION` - modyfikacja pozycji
- `GET_ACCOUNT_INFO` - żądanie informacji o koncie
- `GET_MARKET_DATA` - żądanie danych rynkowych
- `PING` - sprawdzenie połączenia

### Przykłady wiadomości

**Otwarcie pozycji:**
```
OPEN_POSITION:SYMBOL:EURUSD;TYPE:BUY;VOLUME:0.1;SL:1.1;TP:1.2
```

**Aktualizacja pozycji:**
```
POSITIONS_UPDATE:TICKET:12345;SYMBOL:EURUSD;TYPE:BUY;VOLUME:0.1;OPEN_PRICE:1.1;CURRENT_PRICE:1.15;SL:1.09;TP:1.2;PROFIT:50
```

**Dane rynkowe:**
```
MARKET_DATA:SYMBOL:EURUSD;BID:1.1;ASK:1.11;SPREAD:10;TIME:2023.01.01 12:00:00;VOLUME:100;HIGH:1.12;LOW:1.09
```

## Logowanie

### Logowanie w EA

EA zapisuje logi w pliku `AgentMT5_EA_YYMMDD.log` w katalogu dzienników MT5. Poziom logowania można ustawić za pomocą parametru `LogLevel`.

### Logowanie w serwerze

Serwer zapisuje logi w pliku `logs/mt5_server.log`. Poziom logowania jest domyślnie ustawiony na INFO.

## Obsługa błędów

System zawiera rozbudowaną obsługę błędów:

- EA zawiera moduł `ErrorHandler` do obsługi błędów MT5
- Serwer loguje wszystkie błędy i próbuje automatycznie się odzyskać
- W przypadku utraty połączenia, EA automatycznie próbuje się ponownie połączyć
- Serwer monitoruje stan połączenia za pomocą pingów

## Bezpieczeństwo

Zalecenia bezpieczeństwa:

1. System domyślnie nasłuchuje tylko na lokalnym interfejsie (127.0.0.1)
2. Nie należy otwierać portu komunikacji na zaporze bez dodatkowego zabezpieczenia
3. Komunikacja nie jest szyfrowana, więc nie powinna odbywać się przez niezabezpieczone sieci
4. Zaleca się dodatkowe zabezpieczenie kluczami API w przyszłych wersjach

## Rozszerzanie systemu

System można rozszerzyć o nowe funkcje:

1. Dodanie nowych typów komend
2. Implementacja zaawansowanych strategii handlowych
3. Integracja z systemami AI
4. Dodanie dodatkowych zabezpieczeń
5. Implementacja bardziej zaawansowanych metod zarządzania ryzykiem

## Rozwiązywanie problemów

### EA nie może się połączyć z serwerem

1. Sprawdź czy serwer jest uruchomiony
2. Sprawdź czy adresy i porty są zgodne
3. Sprawdź czy zapora nie blokuje połączenia
4. Sprawdź logi EA i serwera

### Brak danych z MT5

1. Sprawdź czy EA jest uruchomiony na wykresie
2. Sprawdź czy symbol jest poprawny
3. Sprawdź logi pod kątem błędów

### Problemy z wykonywaniem zleceń

1. Sprawdź czy konto ma wystarczające środki
2. Sprawdź czy handel jest włączony dla danego symbolu
3. Sprawdź logi pod kątem błędów handlowych 