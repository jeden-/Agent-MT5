# Dokumentacja Modułu Zarządzania Pozycjami

## Wprowadzenie

Moduł zarządzania pozycjami (`position_management`) jest odpowiedzialny za śledzenie, synchronizację i zarządzanie pozycjami handlowymi w systemie AgentMT5. Zapewnia spójność danych między platformą MetaTrader 5 a systemem, umożliwiając efektywne zarządzanie otwartymi i zamkniętymi pozycjami.

## Komponenty

Moduł składa się z trzech głównych komponentów:

1. **PositionManager**: Centralny menedżer pozycji, który zarządza wszystkimi aspektami cyklu życia pozycji.
2. **MT5ApiClient**: Klient API do komunikacji z platformą MetaTrader 5 poprzez protokół HTTP.
3. **DBManager**: Menedżer bazy danych do trwałego przechowywania i odzyskiwania danych pozycji.

### Position i PositionStatus

```python
class Position:
    """Klasa reprezentująca pozycję handlową."""
```

Klasa `Position` reprezentuje pojedynczą pozycję handlową w systemie. Przechowuje wszystkie istotne informacje o pozycji, takie jak ticket, symbol, typ, cena otwarcia, bieżący zysk, itp.

```python
class PositionStatus(Enum):
    """Status pozycji handlowej."""
    OPEN = auto()      # Pozycja otwarta
    CLOSED = auto()    # Pozycja zamknięta
    PENDING = auto()   # Pozycja oczekująca
    ERROR = auto()     # Pozycja z błędem
```

Enumeracja `PositionStatus` definiuje możliwe stany pozycji w systemie.

### PositionManager

```python
class PositionManager:
    """Menedżer pozycji handlowych."""
```

`PositionManager` jest głównym komponentem modułu, odpowiedzialnym za zarządzanie pozycjami. Oferuje następujące funkcjonalności:

- Dodawanie nowych pozycji
- Aktualizacja istniejących pozycji
- Zamykanie pozycji
- Pobieranie pozycji według różnych kryteriów
- Synchronizacja z MT5
- Odzyskiwanie pozycji po awarii

#### Inicjalizacja

```python
def __init__(self, db_connection=None, api_client=None):
    """
    Inicjalizacja menedżera pozycji.
    
    Args:
        db_connection: Połączenie z bazą danych
        api_client: Klient API do komunikacji z MT5
    """
```

PositionManager wymaga menedżera bazy danych i klienta API do pełnej funkcjonalności. Można go jednak zainicjować bez tych zależności w celach testowych.

#### Kluczowe metody

##### Dodanie pozycji

```python
def add_position(self, position_data: Dict[str, Any]) -> Position:
    """
    Dodaje nową pozycję do systemu.
    
    Args:
        position_data: Dane pozycji
        
    Returns:
        Utworzona pozycja
    """
```

##### Aktualizacja pozycji

```python
def update_position(self, ticket: int, update_data: Dict[str, Any]) -> Position:
    """
    Aktualizuje istniejącą pozycję.
    
    Args:
        ticket: Numer ticketu pozycji
        update_data: Dane do aktualizacji
        
    Returns:
        Zaktualizowana pozycja
        
    Raises:
        PositionError: Gdy pozycja o podanym tickecie nie istnieje
    """
```

##### Zamykanie pozycji

```python
def close_position(self, ticket: int, close_data: Dict[str, Any]) -> Position:
    """
    Zamyka istniejącą pozycję.
    
    Args:
        ticket: Numer ticketu pozycji
        close_data: Dane zamknięcia (close_price, close_time, profit)
        
    Returns:
        Zamknięta pozycja
        
    Raises:
        PositionError: Gdy pozycja o podanym tickecie nie istnieje
    """
```

##### Synchronizacja z MT5

```python
def sync_positions_with_mt5(self, ea_id: str) -> None:
    """
    Synchronizuje pozycje z MT5 dla danego EA.
    
    Args:
        ea_id: Identyfikator EA
    """
```

##### Odzyskiwanie pozycji

```python
def recover_positions(self, ea_id: str) -> None:
    """
    Odzyskuje stan pozycji w przypadku awarii.
    
    Args:
        ea_id: Identyfikator EA
    """
```

### MT5ApiClient

```python
class MT5ApiClient:
    """Klient API do komunikacji z MT5 poprzez HTTP."""
```

`MT5ApiClient` zapewnia interfejs do komunikacji z platformą MetaTrader 5 poprzez protokół HTTP. Obsługuje:

- Pobieranie aktywnych pozycji z MT5
- Pobieranie danych zamkniętych pozycji
- Otwieranie nowych pozycji
- Zamykanie pozycji
- Modyfikację parametrów pozycji (SL, TP)
- Pobieranie informacji o koncie
- Pobieranie danych rynkowych

### DBManager

```python
class DBManager:
    """Klasa do obsługi bazy danych dla zarządzania pozycjami."""
```

`DBManager` zapewnia funkcjonalność trwałego przechowywania pozycji w bazie danych PostgreSQL. Oferuje:

- Zapisywanie nowych pozycji
- Aktualizację istniejących pozycji
- Pobieranie pozycji według różnych kryteriów
- Śledzenie historii modyfikacji pozycji
- Obliczanie statystyk handlowych

## Schemat bazy danych

Moduł wykorzystuje dwie główne tabele w bazie danych:

1. `positions`: Przechowuje informacje o wszystkich pozycjach
2. `position_history`: Śledzi historię zmian pozycji

### Tabela positions

```sql
CREATE TABLE IF NOT EXISTS positions (
    id SERIAL PRIMARY KEY,
    ea_id VARCHAR(50) NOT NULL,
    ticket BIGINT NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    position_type VARCHAR(10) NOT NULL, -- BUY, SELL
    volume NUMERIC(10, 2) NOT NULL,
    open_price NUMERIC(15, 5) NOT NULL,
    current_price NUMERIC(15, 5),
    sl NUMERIC(15, 5) DEFAULT 0,
    tp NUMERIC(15, 5) DEFAULT 0,
    profit NUMERIC(15, 2),
    open_time TIMESTAMP NOT NULL,
    close_price NUMERIC(15, 5),
    close_time TIMESTAMP,
    status VARCHAR(20) NOT NULL, -- OPEN, CLOSED, PENDING, ERROR
    last_update TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    sync_status BOOLEAN DEFAULT TRUE,
    error_message TEXT,
    UNIQUE(ea_id, ticket)
);
```

### Tabela position_history

```sql
CREATE TABLE IF NOT EXISTS position_history (
    id SERIAL PRIMARY KEY,
    position_id INTEGER NOT NULL REFERENCES positions(id),
    modification_type VARCHAR(20) NOT NULL, -- UPDATE, CLOSE, SL_MODIFY, TP_MODIFY
    old_value TEXT, -- Przechowuje poprzedni stan pozycji jako JSON
    new_value TEXT, -- Przechowuje nowy stan pozycji jako JSON
    timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    user_id VARCHAR(50) -- ID użytkownika/systemu, który dokonał zmiany
);
```

## Przykłady użycia

### Inicjalizacja modułu

```python
from src.position_management import PositionManager, MT5ApiClient, DBManager

# Inicjalizacja klienta API
api_client = MT5ApiClient(server_url="http://127.0.0.1:5555")

# Inicjalizacja menedżera bazy danych
db_manager = DBManager(connection_string="postgresql://username:password@localhost/agentmt5")

# Inicjalizacja menedżera pozycji
position_manager = PositionManager(db_connection=db_manager, api_client=api_client)
```

### Śledzenie nowej pozycji

```python
# Dane pozycji otrzymane z MT5
position_data = {
    "ea_id": "EA_1741521231",
    "ticket": 89216817,
    "symbol": "GOLD.pro",
    "type": "BUY",
    "volume": 0.10,
    "open_price": 2917.28,
    "current_price": 2910.18,
    "sl": 0.0,
    "tp": 0.0,
    "profit": -274.52,
    "open_time": "2025.03.07 09:03"
}

# Dodanie pozycji do systemu
position = position_manager.add_position(position_data)
```

### Aktualizacja pozycji

```python
# Aktualizacja parametrów pozycji
update_data = {
    "current_price": 2920.50,
    "profit": 50.21,
    "sl": 2900.0,
    "tp": 2950.0
}

updated_position = position_manager.update_position(89216817, update_data)
```

### Zamykanie pozycji

```python
# Dane zamknięcia pozycji
close_data = {
    "close_price": 2925.0,
    "close_time": "2025.03.08 14:30",
    "profit": 85.5
}

closed_position = position_manager.close_position(89216817, close_data)
```

### Synchronizacja z MT5

```python
# Synchronizacja wszystkich pozycji dla danego EA
position_manager.sync_positions_with_mt5("EA_1741521231")
```

### Odzyskiwanie po awarii

```python
# Odzyskiwanie pozycji po awarii systemu
position_manager.recover_positions("EA_1741521231")
```

## Obsługa błędów

Moduł definiuje wyjątek `PositionError` dla specyficznych błędów związanych z zarządzaniem pozycjami:

```python
class PositionError(Exception):
    """Wyjątek związany z obsługą pozycji."""
    pass
```

Wyjątek ten jest używany w przypadkach takich jak:
- Próba dostępu do nieistniejącej pozycji
- Próba aktualizacji nieistniejącej pozycji
- Próba zamknięcia nieistniejącej pozycji
- Błędy synchronizacji z MT5

## Najlepsze praktyki

1. **Regularna synchronizacja z MT5**: Zaleca się regularne wywoływanie `sync_positions_with_mt5()` (np. co 1-5 minut) w celu zapewnienia spójności danych.

2. **Obsługa błędów**: Zawsze owijaj wywołania metod w bloki try-except, aby przechwytywać i obsługiwać potencjalne wyjątki.

3. **Zabezpieczenie przed awarią**: Implementuj procedury odzyskiwania pozycji (`recover_positions()`) po każdym ponownym uruchomieniu systemu.

4. **Logowanie**: Monitoruj i analizuj logi systemu, aby identyfikować i rozwiązywać problemy z zarządzaniem pozycjami.

5. **Kopie zapasowe**: Regularnie twórz kopie zapasowe bazy danych, aby zabezpieczyć dane pozycji przed utratą.

## Rozszerzenia

Moduł można rozszerzyć o dodatkowe funkcjonalności:

1. **Zaawansowane zarządzanie ryzykiem**: Automatyczne dostosowywanie poziomów SL/TP na podstawie warunków rynkowych.

2. **Partial close**: Implementacja częściowego zamykania pozycji.

3. **Trailing stop**: Automatyczne przesuwanie poziomu SL w miarę rozwoju pozycji.

4. **Batch orders**: Obsługa grupowego otwierania i zamykania pozycji.

5. **Statystyki i raportowanie**: Rozbudowane statystyki i raporty dotyczące wydajności handlowej. 