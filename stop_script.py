#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Skrypt zatrzymujący system AgentMT5 po określonym czasie.
"""

import os
import sys
import time
import signal
import logging
import psutil
import subprocess
from datetime import datetime

# Konfiguracja logowania
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/stop_script.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("stop_script")

def find_process_by_command(command_part):
    """Znajdź proces na podstawie fragmentu komendy."""
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            cmdline = proc.info['cmdline']
            if cmdline and any(command_part in cmd for cmd in cmdline):
                return proc
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    return None

def stop_system(timeout_minutes=10):
    """Zatrzymaj system po określonym czasie."""
    start_time = datetime.now()
    logger.info(f"Skrypt zatrzymujący uruchomiony: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"System zostanie zatrzymany po {timeout_minutes} minutach")
    
    # Czekaj przez określony czas
    time.sleep(timeout_minutes * 60)
    
    end_time = datetime.now()
    elapsed_time = (end_time - start_time).total_seconds() / 60
    logger.info(f"Upłynęło {elapsed_time:.2f} minut. Zatrzymywanie systemu...")
    
    # Znajdź i zatrzymaj proces start.py
    process = find_process_by_command('start.py')
    
    if process:
        pid = process.pid
        logger.info(f"Znaleziono proces start.py (PID: {pid}). Zatrzymywanie...")
        
        try:
            # Zatrzymaj proces
            process.terminate()
            logger.info(f"Wysłano sygnał zakończenia do procesu {pid}")
            
            # Poczekaj na zakończenie procesu (max 10 sekund)
            process.wait(timeout=10)
            logger.info(f"Proces {pid} zakończony pomyślnie")
        except psutil.NoSuchProcess:
            logger.warning(f"Proces {pid} już nie istnieje")
        except psutil.TimeoutExpired:
            logger.warning(f"Proces {pid} nie zakończył się po 10 sekundach. Wymuszanie zakończenia...")
            process.kill()
            logger.info(f"Proces {pid} zakończony przymusowo")
        except Exception as e:
            logger.error(f"Błąd podczas zatrzymywania procesu {pid}: {e}")
    else:
        logger.warning("Nie znaleziono procesu start.py")
    
    logger.info("Próba uruchomienia klienta HTTP do zatrzymania systemu...")
    try:
        # Alternatywne zatrzymanie przez API
        import requests
        response = requests.post("http://localhost:8000/api/agent/stop")
        logger.info(f"Wysłano żądanie zatrzymania przez API: {response.status_code} {response.text}")
    except Exception as e:
        logger.error(f"Błąd podczas zatrzymywania przez API: {e}")
    
    logger.info("Skrypt zatrzymujący zakończył pracę")

if __name__ == "__main__":
    minutes = 10  # Domyślny czas działania
    
    # Sprawdź, czy podano argument z czasem
    if len(sys.argv) > 1:
        try:
            minutes = int(sys.argv[1])
        except ValueError:
            logger.error(f"Nieprawidłowy argument: {sys.argv[1]}. Używam domyślnej wartości {minutes} minut.")
    
    stop_system(minutes) 