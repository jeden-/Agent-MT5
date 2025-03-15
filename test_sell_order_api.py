import logging
import sys
import requests
import json
from datetime import datetime
import traceback

# Konfiguracja loggera
logging.basicConfig(
    level=logging.DEBUG,  # Zmieniam poziom logowania na DEBUG
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

def test_sell_order_api():
    """Test dla obsługi zleceń SELL poprzez API."""
    server_url = "http://127.0.0.1:5555"
    logger.debug(f"Używam adresu serwera: {server_url}")
    
    # Sprawdzenie, czy serwer działa
    try:
        logger.debug("Próba sprawdzenia, czy serwer działa...")
        response = requests.get(f"{server_url}/", timeout=5)
        logger.debug(f"Otrzymano odpowiedź: status={response.status_code}")
        logger.debug(f"Odpowiedź: {response.text}")
    except Exception as e:
        logger.error(f"Błąd podczas sprawdzania serwera: {e}")
        logger.error(traceback.format_exc())
    
    # Próba otwarcia pozycji SELL
    try:
        # Używamy stałych wartości zamiast pobierać dane rynkowe
        current_price = 33.08  # Przykładowa cena dla SILVER
        sl = current_price + 1.0  # 1 USD powyżej ceny rynkowej
        tp = current_price - 1.0  # 1 USD poniżej ceny rynkowej
        
        logger.info(f"Używam ceny SILVER: {current_price}, SL: {sl}, TP: {tp}")
        
        order_data = {
            "ea_id": "EA_1741779470",  # Używamy jednego z dostępnych EA_ID
            "symbol": "SILVER",
            "order_type": "SELL",  # Wielkie litery
            "volume": 0.1,
            "price": current_price,
            "sl": sl,
            "tp": tp,
            "comment": "Test SELL z wielkimi literami"
        }
        
        logger.info(f"Wysyłanie żądania otwarcia pozycji: {order_data}")
        logger.debug(f"URL: {server_url}/position/open")
        
        response = requests.post(
            f"{server_url}/position/open",
            json=order_data,
            timeout=10
        )
        
        logger.debug(f"Otrzymano odpowiedź: status={response.status_code}")
        
        if response.status_code != 200:
            logger.error(f"Nie można otworzyć pozycji SELL dla SILVER (kod: {response.status_code})")
            logger.error(f"Odpowiedź: {response.text}")
            return False
        
        result = response.json()
        logger.info(f"Odpowiedź serwera: {result}")
        
        if 'position' not in result or not result['position']:
            logger.error(f"Brak danych pozycji w odpowiedzi")
            return False
        
        logger.info(f"Pomyślnie otwarto pozycję SELL dla SILVER: {result['position']}")
        return True
    except Exception as e:
        logger.error(f"Błąd podczas otwierania pozycji: {e}")
        logger.error(traceback.format_exc())
        return False

if __name__ == "__main__":
    logger.info("Rozpoczęcie testu zlecenia SELL poprzez API...")
    result = test_sell_order_api()
    if result:
        logger.info("Test zakończony sukcesem!")
    else:
        logger.error("Test zakończony niepowodzeniem!") 