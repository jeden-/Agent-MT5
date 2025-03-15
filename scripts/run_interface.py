#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Skrypt do jednoczesnego uruchomienia serwera HTTP i interfejsu użytkownika.
"""

import os
import sys
import time
import argparse
import logging
import threading
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
        logging.FileHandler("logs/interface.log", mode='a'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("InterfaceScript")

def find_free_port(start_port=5000, max_port=9000):
    """Znajduje wolny port TCP."""
    for port in range(start_port, max_port):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('127.0.0.1', port))
                return port
        except OSError:
            continue
    raise IOError("Nie można znaleźć wolnego portu w zakresie od {start_port} do {max_port}")

def is_port_in_use(port):
    """Sprawdza, czy port jest używany."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('127.0.0.1', port)) == 0

def run_http_server(host='127.0.0.1', port=5555):
    """Uruchamia serwer HTTP."""
    try:
        # Sprawdź, czy port jest wolny
        if is_port_in_use(port):
            logger.warning(f"Port {port} jest już używany. Szukam wolnego portu...")
            port = find_free_port(start_port=5556)
            logger.info(f"Znaleziono wolny port: {port}")
        
        # Ścieżka do skryptu serwera HTTP - używamy nowego serwera
        server_script = str(Path(__file__).parent.parent / "src" / "mt5_bridge" / "mt5_server.py")
        
        # Sprawdź, czy plik istnieje
        if not os.path.exists(server_script):
            logger.error(f"Plik serwera HTTP nie istnieje: {server_script}")
            return None, None
            
        logger.info(f"Uruchamianie serwera HTTP na {host}:{port} z: {server_script}")
        
        # Uruchom serwer HTTP w nowym procesie bez przekierowywania stdout/stderr
        server_process = subprocess.Popen(
            [sys.executable, server_script, "--host", host, "--port", str(port)]
        )
        
        # Daj procesowi czas na uruchomienie
        time.sleep(2)
        
        # Sprawdź, czy proces został uruchomiony
        if server_process.poll() is None:
            logger.info("Serwer HTTP uruchomiony pomyślnie")
            return server_process, port
        else:
            logger.error(f"Nie można uruchomić serwera HTTP, kod wyjścia: {server_process.returncode}")
            return None, None
    except Exception as e:
        logger.error(f"Błąd podczas uruchamiania serwera HTTP: {str(e)}")
        return None, None

def run_ui(host='127.0.0.1', port=8501, server_port=5555):
    """Uruchamia interfejs użytkownika."""
    try:
        # Sprawdź, czy port jest wolny
        if is_port_in_use(port):
            logger.warning(f"Port {port} jest już używany. Szukam wolnego portu...")
            port = find_free_port(start_port=8502)
            logger.info(f"Znaleziono wolny port: {port}")
        
        # Ścieżka do skryptu interfejsu
        ui_script = str(Path(__file__).parent.parent / "src" / "ui" / "app.py")
        
        # Tworzymy tymczasowy plik konfiguracyjny dla Streamlit
        config_dir = os.path.join(os.path.expanduser("~"), ".streamlit")
        os.makedirs(config_dir, exist_ok=True)
        config_path = os.path.join(config_dir, "config.toml")
        
        with open(config_path, "w") as f:
            f.write(f"""
[server]
port = {port}
address = "{host}"

[browser]
serverAddress = "{host}"
serverPort = {port}

[theme]
base = "dark"
primaryColor = "#7792E3"
backgroundColor = "#0E1117"
secondaryBackgroundColor = "#262730"
textColor = "#FAFAFA"
            """)
            
        # Utwórz zmienną środowiskową z adresem serwera HTTP
        env = os.environ.copy()
        env["SERVER_URL"] = f"http://{host}:{server_port}"
        
        # Sprawdź, czy plik istnieje
        if not os.path.exists(ui_script):
            logger.error(f"Plik interfejsu użytkownika nie istnieje: {ui_script}")
            return None, None
            
        logger.info(f"Uruchamianie interfejsu użytkownika na {host}:{port} z: {ui_script}")
        
        # Uruchom interfejs w nowym procesie bez przekierowywania stdout/stderr
        ui_process = subprocess.Popen(
            [
                "streamlit", "run", ui_script, 
                "--server.address", host, 
                "--server.port", str(port),
                "--theme.base", "dark"
            ],
            env=env
        )
        
        # Daj procesowi czas na uruchomienie
        time.sleep(2)
        
        # Sprawdź, czy proces został uruchomiony
        if ui_process.poll() is None:
            logger.info("Interfejs użytkownika uruchomiony pomyślnie")
            return ui_process, port
        else:
            logger.error(f"Nie można uruchomić interfejsu użytkownika, kod wyjścia: {ui_process.returncode}")
            return None, None
    except Exception as e:
        logger.error(f"Błąd podczas uruchamiania interfejsu użytkownika: {str(e)}")
        return None, None

def main():
    """Główna funkcja skryptu."""
    # Parsowanie argumentów wiersza poleceń
    parser = argparse.ArgumentParser(description='Uruchamia serwer HTTP i interfejs użytkownika.')
    parser.add_argument('--server-host', type=str, default='127.0.0.1',
                        help='Adres hosta dla serwera HTTP (domyślnie: 127.0.0.1)')
    parser.add_argument('--server-port', type=int, default=5555,
                        help='Port dla serwera HTTP (domyślnie: 5555)')
    parser.add_argument('--ui-host', type=str, default='127.0.0.1',
                        help='Adres hosta dla interfejsu użytkownika (domyślnie: 127.0.0.1)')
    parser.add_argument('--ui-port', type=int, default=8501,
                        help='Port dla interfejsu użytkownika (domyślnie: 8501)')
    
    args = parser.parse_args()
    
    # Tworzymy katalog dla logów, jeśli nie istnieje
    os.makedirs("logs", exist_ok=True)
    
    # Sprawdź środowisko wirtualne
    if not hasattr(sys, 'real_prefix') and not hasattr(sys, 'base_prefix'):
        logger.warning("Nie wykryto aktywnego środowiska wirtualnego! Zaleca się uruchamianie skryptu w środowisku wirtualnym.")
    
    # Uruchom serwer HTTP
    server_process, actual_server_port = run_http_server(args.server_host, args.server_port)
    if server_process is None:
        logger.error("Nie można uruchomić serwera HTTP")
        return 1
    
    # Uruchom interfejs użytkownika
    ui_process, actual_ui_port = run_ui(args.ui_host, args.ui_port, actual_server_port)
    if ui_process is None:
        logger.error("Nie można uruchomić interfejsu użytkownika")
        server_process.terminate()
        return 1
    
    logger.info(f"Serwer HTTP działa na http://{args.server_host}:{actual_server_port}")
    logger.info(f"Interfejs użytkownika dostępny pod adresem http://{args.ui_host}:{actual_ui_port}")
    logger.info("Naciśnij Ctrl+C, aby zatrzymać oba procesy...")
    
    try:
        while True:
            # Sprawdź, czy procesy są nadal uruchomione
            if server_process.poll() is not None:
                logger.error(f"Serwer HTTP został nieoczekiwanie zatrzymany z kodem wyjścia {server_process.returncode}")
                ui_process.terminate()
                return 1
            
            if ui_process.poll() is not None:
                logger.error(f"Interfejs użytkownika został nieoczekiwanie zatrzymany z kodem wyjścia {ui_process.returncode}")
                server_process.terminate()
                return 1
            
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Zatrzymywanie procesów (Ctrl+C)...")
    finally:
        # Zatrzymaj procesy
        logger.info("Zatrzymywanie interfejsu użytkownika...")
        ui_process.terminate()
        ui_process.wait(timeout=5)
        
        logger.info("Zatrzymywanie serwera HTTP...")
        server_process.terminate()
        server_process.wait(timeout=5)
        
        logger.info("Wszystkie procesy zatrzymane")
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 