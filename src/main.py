#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Trading Agent MT5 - Main Application

Ten plik zawiera główną logikę aplikacji Trading Agent MT5.
"""

import os
import sys
import logging
import time
from datetime import datetime
import yaml
import asyncio
from dotenv import load_dotenv

# Dodanie głównego katalogu projektu do PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import i konfiguracja systemu logowania
from src.utils.logging_config import configure_logging, get_current_log_path

# Konfiguracja loggera z zapisem do pliku
configure_logging(log_level=logging.INFO)
log_path = get_current_log_path()

logger = logging.getLogger(__name__)
logger.info(f"Logowanie skonfigurowane. Ścieżka do pliku logów: {log_path}")

def load_config():
    """Wczytaj konfigurację z pliku YAML."""
    config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config', 'config.yaml')
    try:
        with open(config_path, 'r', encoding='utf-8') as config_file:
            return yaml.safe_load(config_file)
    except Exception as e:
        logging.error(f"Błąd podczas wczytywania konfiguracji: {e}")
        sys.exit(1)

async def main():
    """Główna funkcja aplikacji."""
    try:
        # Wczytanie zmiennych środowiskowych
        load_dotenv()
        
        # Wczytanie konfiguracji
        config = load_config()
        
        # Aplikowanie łatek
        from src.utils.patches import apply_all_patches
        patch_results = apply_all_patches()
        if not all(patch_results.values()):
            logger.warning("Nie wszystkie łatki zostały pomyślnie zaaplikowane!")
        
        # Inicjalizacja systemu powiadomień
        from src.notifications.init_notifications import init_notifications
        if init_notifications():
            logger.info("System powiadomień zainicjalizowany pomyślnie")
        else:
            logger.warning("Inicjalizacja systemu powiadomień zakończona z ostrzeżeniami")
        
        # Import modułów systemu
        # Ważne: Kolejność importów ma znaczenie, aby uniknąć cyklicznego importu
        from src.mt5_bridge import start_server
        from src.agent_controller import get_agent_controller
        from src.scheduler import get_scheduler
        
        # Uruchomienie serwera HTTP
        host = config.get('server', {}).get('host', '127.0.0.1')
        port = config.get('server', {}).get('port', 5555)
        
        logger.info(f"Uruchamianie serwera na {host}:{port}")
        server = await start_server(host, port)
        
        # Inicjalizacja kontrolera agenta
        logger.info("Inicjalizacja kontrolera agenta")
        agent_controller = get_agent_controller()
        
        # Ustawienie kontrolera agenta w serwerze
        logger.info("Konfiguracja kontrolera agenta w serwerze")
        server.set_agent_controller(agent_controller)
        
        # Inicjalizacja i uruchomienie harmonogramu zadań
        logger.info("Inicjalizacja harmonogramu zadań")
        scheduler = get_scheduler()
        scheduler.initialize_default_tasks()
        logger.info("Uruchamianie harmonogramu zadań")
        scheduler.start()
        
        # Uruchomienie agenta w trybie obserwacyjnym
        if config.get('agent', {}).get('auto_start', False):
            mode = config.get('agent', {}).get('mode', 'observation')
            logger.info(f"Automatyczne uruchomienie agenta w trybie: {mode}")
            agent_controller.start_agent(mode=mode)
        
        # Utrzymanie działania aplikacji
        logger.info("Aplikacja uruchomiona. Naciśnij Ctrl+C, aby zakończyć.")
        while True:
            await asyncio.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("Zatrzymywanie aplikacji przez użytkownika...")
    except Exception as e:
        logger.error(f"Nieoczekiwany błąd: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Czyszczenie zasobów
        logger.info("Czyszczenie zasobów...")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        logger.error(f"Błąd podczas uruchamiania aplikacji: {e}")
        import traceback
        traceback.print_exc() 