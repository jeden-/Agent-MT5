#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Skrypt testowy do sprawdzenia połączenia z Expert Advisorem MT5
"""

import sys
import time
from pathlib import Path
import logging

# Dodajemy katalog główny projektu do ścieżki, aby móc importować moduły
sys.path.append(str(Path(__file__).parent.parent))

from src.mt5_bridge import MT5Server

# Konfiguracja logowania
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("MT5ConnectionTest")

def main():
    """Testuje połączenie z EA MT5."""
    logger.info("Rozpoczynam test połączenia z EA MT5")
    
    # Tworzymy instancję serwera (ale nie uruchamiamy nowego serwera, używamy już działającego)
    server = MT5Server(host='127.0.0.1', port=5555)
    
    # Rejestrujemy callbacki
    def on_market_data(data):
        logger.info(f"Otrzymano dane rynkowe: {data}")
        
    def on_positions_update(data):
        logger.info(f"Otrzymano aktualizację pozycji: {data}")
        
    def on_account_info(data):
        logger.info(f"Otrzymano informacje o koncie: {data}")
        
    server.register_callback("MARKET_DATA", on_market_data)
    server.register_callback("POSITIONS_UPDATE", on_positions_update)
    server.register_callback("ACCOUNT_INFO", on_account_info)
    
    # Sprawdzamy czy EA jest podłączony
    if server.is_connected():
        logger.info("EA jest podłączony!")
        
        # Testujemy wysyłanie komend
        logger.info("Wysyłam zapytanie o informacje o koncie...")
        server.request_account_info()
        
        logger.info("Wysyłam zapytanie o dane rynkowe dla EURUSD...")
        server.request_market_data("EURUSD")
        
        # Czekamy na odpowiedzi (callback zostanie wywołany automatycznie)
        logger.info("Czekam na odpowiedzi...")
        time.sleep(5)
        
        # Sprawdzamy dane (bez wysyłania zapytań, tylko pobieramy to co już mamy w serwrze)
        account_info = server.get_account_info()
        market_data = server.get_market_data("EURUSD")
        positions = server.get_positions_data()
        
        logger.info(f"Dane konta: {account_info}")
        logger.info(f"Dane rynkowe EURUSD: {market_data}")
        logger.info(f"Otwarte pozycje: {positions}")
    else:
        logger.error("EA nie jest podłączony. Upewnij się, że EA jest uruchomiony w MT5!")
    
    logger.info("Test połączenia zakończony")
    
if __name__ == "__main__":
    main() 