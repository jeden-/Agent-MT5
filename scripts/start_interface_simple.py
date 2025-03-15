#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Prosty skrypt uruchamiający interfejs użytkownika Streamlit bez prób komunikacji
bezpośrednio z MT5. Interfejs będzie korzystał z serwera HTTP jako pośrednika.
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

# Konfiguracja logowania
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("InterfaceSimple")

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

def run_ui(ui_port=8502):
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
        
        # Uruchom interfejs w nowym procesie bez przekierowywania stdout/stderr
        ui_process = subprocess.Popen(
            [
                "streamlit", "run", ui_script, 
                "--server.address", "127.0.0.1", 
                "--server.port", str(ui_port)
            ]
        )
        
        # Daj procesowi czas na uruchomienie
        time.sleep(2)
        
        # Sprawdź, czy proces został uruchomiony
        if ui_process.poll() is None:
            logger.info(f"Interfejs użytkownika uruchomiony pomyślnie na http://127.0.0.1:{ui_port}")
            return ui_process, ui_port
        else:
            logger.error(f"Nie można uruchomić interfejsu użytkownika, kod wyjścia: {ui_process.returncode}")
            return None, None
    except Exception as e:
        logger.error(f"Błąd podczas uruchamiania interfejsu użytkownika: {str(e)}")
        return None, None

def main():
    """Główna funkcja skryptu."""
    # Sprawdź, czy jesteśmy w środowisku wirtualnym
    if not hasattr(sys, 'real_prefix') and not hasattr(sys, 'base_prefix') != sys.prefix:
        logger.warning("Nie wykryto aktywnego środowiska wirtualnego! Zaleca się uruchamianie skryptu w środowisku wirtualnym.")
    
    # Uruchom interfejs użytkownika
    ui_process, ui_port = run_ui()
    if ui_process is None:
        logger.error("Nie można uruchomić interfejsu użytkownika")
        return 1
    
    logger.info(f"Interfejs użytkownika dostępny pod adresem http://127.0.0.1:{ui_port}")
    logger.info("WAŻNE: Upewnij się, że serwer HTTP jest uruchomiony w osobnym terminalu za pomocą komendy:")
    logger.info("python scripts/http_mt5_server.py --host 127.0.0.1 --port 5555")
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