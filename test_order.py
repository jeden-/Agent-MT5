import requests
import json
import time

# Unikalne ID dla zlecenia
import random
ea_id = f"TEST_EA_{random.randint(1000, 9999)}"

print(f"Używam EA_ID: {ea_id}")

url = "http://127.0.0.1:5555/position/open"
headers = {"Content-Type": "application/json"}
data = {
    "ea_id": ea_id,
    "symbol": "EURUSD",
    "order_type": "BUY_STOP",
    "volume": 0.01,
    "price": 1.25,
    "comment": f"Test zlecenia {random.randint(1000, 9999)}"
}

response = requests.post(url, headers=headers, json=data)
print(f"Status code: {response.status_code}")
print(f"Response: {response.text}")

# Poczekaj chwilę, aby serwer miał czas na przetworzenie
time.sleep(1)

# Sprawdź czy komenda pojawiła się w kolejce
check_url = f"http://127.0.0.1:5555/commands?ea_id={ea_id}"
check_response = requests.get(check_url)
print(f"\nStatus kolejki komend: {check_response.status_code}")
print(f"Kolejka komend: {check_response.text}")

# Sprawdź kolejkę dla domyślnego EA_ID = TEST_EA
default_check_url = "http://127.0.0.1:5555/commands?ea_id=TEST_EA"
default_check_response = requests.get(default_check_url)
print(f"\nStatus kolejki domyślnej: {default_check_response.status_code}")
print(f"Kolejka domyślna: {default_check_response.text}") 