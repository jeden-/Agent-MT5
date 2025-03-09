#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Skrypt do uruchomienia serwera MT5.
"""

import os
import sys
import time
import argparse
import logging
from pathlib import Path

# Dodajemy katalog główny projektu do ścieżki, aby móc importować moduły
sys.path.append(str(Path(__file__).parent.parent))

from src.mt5_bridge import MT5Server

# Konfiguracja logowania
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/mt5_server.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("MT5ServerScript")

def main():
    """Główna funkcja skryptu."""
    # Parsowanie argumentów wiersza poleceń
    parser = argparse.ArgumentParser(description='Uruchamia serwer MT5 do komunikacji z Expert Advisorem.')
    parser.add_argument('--host', type=str, default='127.0.0.1',
                        help='Adres hosta do nasłuchiwania (domyślnie: 127.0.0.1)')
    parser.add_argument('--port', type=int, default=5555,
                        help='Port do nasłuchiwania (domyślnie: 5555)')
    parser.add_argument('--ping-interval', type=int, default=5,
                        help='Interwał pingowania EA w sekundach (domyślnie: 5)')
    
    args = parser.parse_args()
    
    # Tworzymy katalog dla logów, jeśli nie istnieje
    os.makedirs("logs", exist_ok=True)
    
    logger.info(f"Uruchamianie serwera MT5 na {args.host}:{args.port}")
    
    # Tworzymy i uruchamiamy serwer
    server = MT5Server(host=args.host, port=args.port)
    
    try:
        if server.start():
            logger.info(f"Serwer MT5 uruchomiony pomyślnie na {args.host}:{args.port}")
            print(f"Serwer MT5 uruchomiony na {args.host}:{args.port}")
            print("Naciśnij Ctrl+C aby zatrzymać serwer...")
            
            # Rejestrujemy callbacki
            def on_market_data(data):
                logger.debug(f"Nowe dane rynkowe: {data}")
            
            def on_positions_update(data):
                logger.debug(f"Aktualizacja pozycji: {data}")
            
            def on_account_info(data):
                logger.debug(f"Informacje o koncie: {data}")
            
            server.register_callback("MARKET_DATA", on_market_data)
            server.register_callback("POSITIONS_UPDATE", on_positions_update)
            server.register_callback("ACCOUNT_INFO", on_account_info)
            
            # Utrzymujemy serwer uruchomiony
            last_ping_time = 0
            while True:
                # Co określony interwał wysyłamy ping, jeśli jesteśmy połączeni
                current_time = time.time()
                if current_time - last_ping_time > args.ping_interval:
                    if server.is_connected():
                        server.ping()
                    last_ping_time = current_time
                
                # Krótka pauza, aby nie obciążać CPU
                time.sleep(0.1)
        else:
            logger.error("Nie można uruchomić serwera MT5")
            print("Nie można uruchomić serwera MT5")
            return 1
    except KeyboardInterrupt:
        logger.info("Zatrzymywanie serwera MT5 (Ctrl+C)")
        print("Zatrzymywanie serwera MT5...")
    except Exception as e:
        logger.error(f"Błąd podczas działania serwera MT5: {str(e)}")
        print(f"Błąd: {str(e)}")
        return 1
    finally:
        server.stop()
        logger.info("Serwer MT5 zatrzymany")
        print("Serwer MT5 zatrzymany")
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 