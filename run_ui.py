#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Skrypt uruchamiający interfejs użytkownika AgentMT5 Trading Monitor.
Ten skrypt uruchamia interfejs Streamlit, który pobiera dane z API serwera MT5.
"""

import os
import sys
import subprocess
import logging
import traceback
from pathlib import Path

# Konfiguracja logowania
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("run_ui")

def check_server_running():
    """Sprawdza, czy serwer MT5 jest uruchomiony."""
    import requests
    try:
        # Próbujemy połączyć się z serwerem na porcie 5555
        response = requests.get("http://localhost:5555/ping", timeout=2)
        if response.status_code == 200:
            logger.info("Serwer MT5 jest już uruchomiony")
            return True
    except Exception:
        logger.warning("Serwer MT5 nie jest uruchomiony")
        return False

def start_server():
    """Uruchamia serwer MT5, jeśli nie jest jeszcze uruchomiony."""
    logger.info("Uruchamianie serwera MT5...")
    try:
        # Uruchom proces w tle
        process = subprocess.Popen(
            ["python", "start.py"],
            creationflags=subprocess.CREATE_NEW_CONSOLE,
            shell=True
        )
        logger.info(f"Uruchomiono serwer MT5 (PID: {process.pid})")
        return True
    except Exception as e:
        logger.error(f"Błąd podczas uruchamiania serwera MT5: {e}")
        return False

def run_ui():
    """Uruchamia interfejs użytkownika Streamlit."""
    logger.info("Uruchamianie interfejsu użytkownika...")
    
    # Sprawdź, czy katalog src/ui istnieje
    ui_dir = Path("src/ui")
    if not ui_dir.exists() or not ui_dir.is_dir():
        logger.error(f"Katalog {ui_dir} nie istnieje!")
        return False
    
    # Sprawdź, czy plik app.py istnieje
    app_path = ui_dir / "app.py"
    if not app_path.exists() or not app_path.is_file():
        logger.error(f"Plik {app_path} nie istnieje!")
        return False
    
    try:
        # Wydrukuj pełną ścieżkę do sprawdzenia
        print(f"Próba uruchomienia: {app_path.absolute()}")
        
        # Uruchom Streamlit używając modułu Pythona
        subprocess.run([
            "python", "-m", "streamlit", "run", str(app_path),
            "--server.port", "8501",
            "--server.address", "localhost"
        ], check=True)
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Błąd podczas uruchamiania interfejsu Streamlit: {e}")
        return False
    except FileNotFoundError as e:
        logger.error(f"Nie można znaleźć pliku: {e}")
        print(f"PATH: {os.environ.get('PATH')}")
        traceback.print_exc()
        return False
    except Exception as e:
        logger.error(f"Nieoczekiwany błąd: {e}")
        traceback.print_exc()
        return False

if __name__ == "__main__":
    # Upewnij się, że serwer MT5 jest uruchomiony
    if not check_server_running():
        start_server()
    
    # Uruchom interfejs użytkownika
    run_ui() 