import threading
import time

# Symulacja zmiennych i obiektów z serwera
command_queue = {}
commands_lock = threading.Lock()

def add_command(ea_id, command):
    """Dodaje komendę do kolejki."""
    with commands_lock:
        if ea_id not in command_queue:
            command_queue[ea_id] = []
        command_queue[ea_id].append(command)
        print(f"Dodano komendę dla {ea_id}: {command}")
        print(f"Stan kolejki po dodaniu: {command_queue}")

def get_commands(ea_id):
    """Pobiera komendy z kolejki dla określonego ea_id."""
    print(f"Otrzymano żądanie pobrania komend dla {ea_id}")
    print(f"Stan kolejki przed pobraniem: {command_queue}")
    
    # Pobieramy komendy z kolejki dla danego EA i czyścimy kolejkę
    commands = []
    with commands_lock:
        if ea_id in command_queue and command_queue[ea_id]:
            commands = command_queue[ea_id].copy()
            command_queue[ea_id] = []  # Czyszczenie kolejki po pobraniu
            print(f"Pobrano {len(commands)} komend dla EA {ea_id}")
    
    print(f"Stan kolejki po pobraniu: {command_queue}")
    print(f"Zwracam komendy: {commands}")
    return {"commands": commands}

# Test dodawania i pobierania komend
print("\n=== TEST 1: Dodawanie i pobieranie komendy ===")
ea_id = "TEST_EA_123"
command = {"action": "OPEN_POSITION", "symbol": "EURUSD", "type": "BUY", "volume": 0.01}

print("1. Dodaję komendę")
add_command(ea_id, command)

print("\n2. Pobieram komendy")
result = get_commands(ea_id)
print(f"Wynik: {result}")

print("\n3. Sprawdzam czy kolejka jest pusta po pobraniu")
result = get_commands(ea_id)
print(f"Wynik: {result}")

# Test dla więcej niż jednej komendy
print("\n=== TEST 2: Więcej niż jedna komenda ===")
ea_id = "TEST_EA_456"
command1 = {"action": "OPEN_POSITION", "symbol": "EURUSD", "type": "BUY", "volume": 0.01}
command2 = {"action": "OPEN_POSITION", "symbol": "GBPUSD", "type": "SELL", "volume": 0.02}

print("1. Dodaję komendę 1")
add_command(ea_id, command1)

print("\n2. Dodaję komendę 2")
add_command(ea_id, command2)

print("\n3. Pobieram komendy")
result = get_commands(ea_id)
print(f"Wynik: {result}")

# Test dla komend dla różnych EA
print("\n=== TEST 3: Komendy dla różnych EA ===")
ea_id1 = "TEST_EA_789"
ea_id2 = "TEST_EA_012"
command1 = {"action": "OPEN_POSITION", "symbol": "EURUSD", "type": "BUY", "volume": 0.01}
command2 = {"action": "OPEN_POSITION", "symbol": "GBPUSD", "type": "SELL", "volume": 0.02}

print("1. Dodaję komendę dla EA1")
add_command(ea_id1, command1)

print("\n2. Dodaję komendę dla EA2")
add_command(ea_id2, command2)

print("\n3. Pobieram komendy dla EA1")
result = get_commands(ea_id1)
print(f"Wynik dla EA1: {result}")

print("\n4. Pobieram komendy dla EA2")
result = get_commands(ea_id2)
print(f"Wynik dla EA2: {result}")

print("\n5. Sprawdzam czy kolejki są puste po pobraniu")
result1 = get_commands(ea_id1)
result2 = get_commands(ea_id2)
print(f"Wynik dla EA1: {result1}")
print(f"Wynik dla EA2: {result2}") 