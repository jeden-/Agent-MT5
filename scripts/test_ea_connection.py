#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Skrypt do testowania połączenia z Expert Advisor MT5.
"""

import os
import sys
import time
import logging
import threading
import requests
import json
from pathlib import Path

# Dodajemy katalog główny projektu do ścieżki, aby móc importować moduły
sys.path.append(str(Path(__file__).parent.parent))

# Konfiguracja logowania
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("EA_Connection_Test")

def test_server_connection(host='127.0.0.1', port=5556):
    """Testuje połączenie z serwerem HTTP."""
    server_url = f"http://{host}:{port}"
    
    # Sprawdź status serwera
    try:
        logger.info(f"Testowanie połączenia z serwerem HTTP na {server_url}...")
        response = requests.get(f"{server_url}/status", timeout=10)
        if response.status_code == 200:
            logger.info(f"Połączenie z serwerem HTTP nawiązane pomyślnie!")
            status_data = response.json()
            logger.info(f"Status serwera: {json.dumps(status_data, indent=2)}")
            return True
        else:
            logger.error(f"Błąd połączenia z serwerem HTTP: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        logger.error(f"Wyjątek podczas łączenia z serwerem HTTP: {str(e)}")
        return False

def send_test_command(host='127.0.0.1', port=5556):
    """Wysyła testowe polecenie do EA za pośrednictwem serwera HTTP."""
    server_url = f"http://{host}:{port}"
    
    # Polecenie testowe
    test_command = {
        "action": "test_connection",
        "timestamp": int(time.time())
    }
    
    # Znajdź aktywne EA, jeśli istnieją
    try:
        logger.info("Pobieranie listy aktywnych EA...")
        response = requests.get(f"{server_url}/status", timeout=10)
        if response.status_code == 200:
            status_data = response.json()
            
            # Sprawdź, czy są aktywne EA
            clients = status_data.get('clients', {})
            client_count = clients.get('count', 0)
            client_list = clients.get('list', [])
            
            logger.info(f"Znaleziono {client_count} aktywnych EA: {client_list}")
            
            if client_count > 0:
                # Wyślij polecenie do pierwszego EA
                ea_id = client_list[0]
                logger.info(f"Wysyłanie polecenia testowego do EA {ea_id}...")
                
                response = requests.post(
                    f"{server_url}/command", 
                    json={
                        "ea_id": ea_id,
                        "command": test_command
                    },
                    timeout=10
                )
                
                if response.status_code == 200:
                    logger.info(f"Polecenie wysłane pomyślnie: {response.json()}")
                    return True
                else:
                    logger.error(f"Błąd wysyłania polecenia: {response.status_code} - {response.text}")
                    return False
            else:
                logger.warning("Brak aktywnych EA - nie można wysłać polecenia")
                return False
        else:
            logger.error(f"Błąd pobierania statusu: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        logger.error(f"Wyjątek podczas wysyłania polecenia: {str(e)}")
        return False

def main():
    """Główna funkcja skryptu."""
    # Testowanie połączenia
    if not test_server_connection():
        logger.error("Test połączenia z serwerem HTTP nieudany!")
        return 1
    
    # Wysyłanie polecenia testowego
    if not send_test_command():
        logger.warning("Nie udało się wysłać polecenia testowego")
    
    logger.info("Test połączenia zakończony")
    return 0

if __name__ == "__main__":
    sys.exit(main()) 