import requests
import json
import logging
import time

# Konfiguracja logowania
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Konfiguracja serwera
server_url = "http://127.0.0.1:5555"

def send_buy_stop_order():
    """Wysyła zlecenie BUY_STOP bezpośrednio do MT5 EA."""
    try:
        url = f"{server_url}/position/open"
        headers = {"Content-Type": "application/json"}
        data = {
            "ea_id": "EA_1234",
            "symbol": "EURUSD",
            "order_type": "BUY_STOP",
            "volume": 0.01,
            "price": 1.25,
            "comment": "Test BUY_STOP order"
        }
        
        logger.info(f"Wysyłanie zlecenia: {data}")
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        
        result = response.json()
        logger.info(f"Odpowiedź serwera: {result}")
        
        return True
    except Exception as e:
        logger.error(f"Błąd podczas wysyłania zlecenia: {str(e)}")
        return False

def check_command_queue():
    """Sprawdza zawartość kolejki komend."""
    try:
        url = f"{server_url}/commands?ea_id=EA_1234"
        response = requests.get(url)
        response.raise_for_status()
        
        result = response.json()
        logger.info(f"Stan kolejki komend: {result}")
        
        return result
    except Exception as e:
        logger.error(f"Błąd podczas sprawdzania kolejki komend: {str(e)}")
        return None

def ping_server():
    """Sprawdza czy serwer jest dostępny."""
    try:
        url = f"{server_url}/ping"
        response = requests.get(url)
        response.raise_for_status()
        
        logger.info(f"Serwer jest dostępny. Odpowiedź: {response.text}")
        return True
    except Exception as e:
        logger.error(f"Serwer jest niedostępny: {str(e)}")
        return False

if __name__ == "__main__":
    # Sprawdź czy serwer jest dostępny
    if not ping_server():
        logger.error("Nie można połączyć się z serwerem. Upewnij się, że serwer jest uruchomiony.")
        exit(1)
    
    # Wyślij zlecenie BUY_STOP
    if send_buy_stop_order():
        logger.info("Zlecenie zostało wysłane pomyślnie")
    else:
        logger.error("Nie udało się wysłać zlecenia")
        exit(1)
    
    # Sprawdź kolejkę komend
    logger.info("Sprawdzanie kolejki komend...")
    result = check_command_queue()
    
    if result and "commands" in result and len(result["commands"]) > 0:
        logger.info(f"Kolejka zawiera {len(result['commands'])} komend")
    else:
        logger.warning("Kolejka jest pusta lub nie można jej sprawdzić")
    
    # Daj czas EA na pobranie i przetworzenie komendy
    logger.info("Czekam 5 sekund na przetworzenie komendy przez EA...")
    time.sleep(5)
    
    # Sprawdź ponownie kolejkę komend
    logger.info("Ponowne sprawdzanie kolejki komend...")
    result = check_command_queue()
    
    if result and "commands" in result and len(result["commands"]) > 0:
        logger.info(f"Kolejka zawiera {len(result['commands'])} komend")
    else:
        logger.info("Kolejka jest pusta - komendy zostały pobrane lub nie dodano ich prawidłowo") 