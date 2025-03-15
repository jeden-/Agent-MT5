#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Skrypt do uruchomienia interfejsu użytkownika korzystającego z istniejącego połączenia na porcie 5555.
Ten skrypt nie uruchamia własnego serwera HTTP, ale korzysta z tego, który już działa w MT5.
"""

import os
import sys
import time
import logging
import subprocess
import socket
from pathlib import Path

# Dodajemy katalog główny projektu do ścieżki, aby móc importować moduły
sys.path.append(str(Path(__file__).parent.parent))

# Import naszego klienta API
from src.mt5_bridge.mt5_api_client import get_mt5_api_client

# Konfiguracja logowania
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/connect_to_mt5.log", mode='a'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("ConnectToMT5")

def is_port_in_use(port):
    """Sprawdza, czy port jest używany."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('127.0.0.1', port)) == 0

def find_free_port(start_port=8500, max_port=9000):
    """Znajduje wolny port TCP."""
    for port in range(start_port, max_port):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('127.0.0.1', port))
                return port
        except OSError:
            continue
    raise IOError("Nie można znaleźć wolnego portu w zakresie od {start_port} do {max_port}")

def test_mt5_connection(mt5_port=5555):
    """Testuje, czy MT5 jest dostępne na określonym porcie."""
    try:
        # Użyj naszego specjalnego klienta API
        client = get_mt5_api_client(port=mt5_port)
        if client.ping():
            logger.info(f"Połączenie z MT5 na porcie {mt5_port} działa poprawnie.")
            return True
        else:
            logger.error(f"Nie można połączyć się z MT5 na porcie {mt5_port}.")
            return False
    except Exception as e:
        logger.error(f"Błąd podczas testowania połączenia z MT5: {str(e)}")
        return False

def run_ui(mt5_port=5555, ui_port=8502):
    """Uruchamia interfejs użytkownika."""
    try:
        # Sprawdź, czy port jest wolny
        if is_port_in_use(ui_port):
            logger.warning(f"Port {ui_port} jest już używany. Szukam wolnego portu...")
            ui_port = find_free_port()
            logger.info(f"Znaleziono wolny port: {ui_port}")
        
        # Ścieżka do skryptu interfejsu
        ui_script = str(Path(__file__).parent.parent / "src" / "ui" / "app.py")
        
        # Sprawdź, czy plik istnieje
        if not os.path.exists(ui_script):
            logger.error(f"Plik interfejsu użytkownika nie istnieje: {ui_script}")
            return None
            
        logger.info(f"Uruchamianie interfejsu użytkownika na porcie {ui_port}...")
        
        # Utwórz zmienną środowiskową z adresem serwera MT5
        env = os.environ.copy()
        env["SERVER_URL"] = f"http://127.0.0.1:{mt5_port}"
        
        # Uruchom interfejs w nowym procesie
        ui_process = subprocess.Popen(
            [
                "streamlit", "run", ui_script, 
                "--server.address", "127.0.0.1", 
                "--server.port", str(ui_port)
            ],
            env=env
        )
        
        # Daj procesowi czas na uruchomienie
        time.sleep(2)
        
        # Sprawdź, czy proces został uruchomiony
        if ui_process.poll() is None:
            logger.info(f"Interfejs użytkownika uruchomiony pomyślnie na http://127.0.0.1:{ui_port}")
            return ui_process
        else:
            logger.error(f"Nie można uruchomić interfejsu użytkownika, kod wyjścia: {ui_process.returncode}")
            return None
    except Exception as e:
        logger.error(f"Błąd podczas uruchamiania interfejsu użytkownika: {str(e)}")
        return None

def main():
    """Główna funkcja skryptu."""
    # Konfiguracja
    mt5_port = 5555  # Port MT5
    ui_port = 8502   # Domyślny port interfejsu
    
    # Tworzymy katalog dla logów, jeśli nie istnieje
    os.makedirs("logs", exist_ok=True)
    
    # Sprawdź środowisko wirtualne
    if not hasattr(sys, 'real_prefix') and not hasattr(sys, 'base_prefix') != sys.prefix:
        logger.warning("Nie wykryto aktywnego środowiska wirtualnego! Zaleca się uruchamianie skryptu w środowisku wirtualnym.")
    
    # Sprawdź, czy port jest używany
    if not is_port_in_use(mt5_port):
        logger.warning(f"Port {mt5_port} nie jest używany! Upewnij się, że MT5 jest uruchomione i skonfigurowane poprawnie.")
        logger.info("Kontynuuję mimo to...")
    else:
        logger.info(f"Port {mt5_port} jest używany. Sprawdzanie połączenia MT5...")
        test_mt5_connection(mt5_port)
    
    # Uruchom interfejs użytkownika
    ui_process = run_ui(mt5_port, ui_port)
    if ui_process is None:
        logger.error("Nie można uruchomić interfejsu użytkownika")
        return 1
    
    logger.info(f"Interfejs został skonfigurowany do połączenia z MT5 na porcie {mt5_port}")
    logger.info(f"Interfejs użytkownika dostępny pod adresem http://127.0.0.1:{ui_port}")
    logger.info("Naciśnij Ctrl+C, aby zatrzymać interfejs...")
    
    try:
        while True:
            # Sprawdź, czy proces jest nadal uruchomiony
            if ui_process.poll() is not None:
                logger.error(f"Interfejs użytkownika został nieoczekiwanie zatrzymany z kodem wyjścia {ui_process.returncode}")
                return 1
            
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Zatrzymywanie procesów (Ctrl+C)...")
    finally:
        # Zatrzymaj proces
        logger.info("Zatrzymywanie interfejsu użytkownika...")
        ui_process.terminate()
        ui_process.wait(timeout=5)
        
        logger.info("Wszystkie procesy zatrzymane")
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 