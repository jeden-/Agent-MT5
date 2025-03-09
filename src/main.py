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
from dotenv import load_dotenv

# Dodanie głównego katalogu projektu do PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Moduły aplikacji
from src.database import DatabaseManager
from src.mt5_bridge import TradingService
from src.position_management import PositionManager
from src.risk_management import RiskManager
from src.analysis import SignalGenerator, SignalValidator, FeedbackLoop
from src.trading_integration import TradingIntegration
from src.utils import setup_logging

def load_config():
    """Wczytaj konfigurację z pliku YAML."""
    config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config', 'config.yaml')
    try:
        with open(config_path, 'r', encoding='utf-8') as config_file:
            return yaml.safe_load(config_file)
    except Exception as e:
        logging.error(f"Błąd podczas wczytywania konfiguracji: {e}")
        sys.exit(1)

class TradingAgent:
    """Główna klasa agenta handlującego."""
    
    def __init__(self):
        """Inicjalizacja agenta."""
        # Wczytanie zmiennych środowiskowych
        load_dotenv()
        
        # Wczytanie konfiguracji
        self.config = load_config()
        
        # Konfiguracja logowania
        self.logger = setup_logging()
        self.logger.info("Inicjalizacja Trading Agent MT5")
        
        # Status agenta
        self.is_running = False
        
        # Komponenty
        self.db_manager = None
        self.trading_integration = None
    
    def initialize_components(self):
        """Inicjalizacja wszystkich komponentów systemu."""
        self.logger.info("Inicjalizacja komponentów systemu...")
        
        # Inicjalizacja bazy danych
        self.logger.info("Inicjalizacja połączenia z bazą danych...")
        self.db_manager = DatabaseManager()
        self.db_manager.connect()
        
        # Sprawdzenie struktury bazy danych
        self.logger.info("Sprawdzanie struktury bazy danych...")
        try:
            self.db_manager.create_tables()
            self.logger.info("Struktura bazy danych zweryfikowana")
        except Exception as e:
            self.logger.error(f"Błąd podczas weryfikacji struktury bazy danych: {e}", exc_info=True)
            raise
        
        # Inicjalizacja integracji handlowej
        self.logger.info("Inicjalizacja integracji handlowej...")
        self.trading_integration = TradingIntegration()
        
        self.logger.info("Inicjalizacja komponentów zakończona")
    
    def start(self):
        """Uruchomienie agenta."""
        self.logger.info("Uruchamianie Trading Agent MT5...")
        
        try:
            self.initialize_components()
            self.is_running = True
            
            # Uruchomienie integracji handlowej
            if not self.trading_integration.start():
                self.logger.error("Nie udało się uruchomić integracji handlowej")
                raise RuntimeError("Błąd uruchamiania integracji handlowej")
            
            # Włączenie/wyłączenie automatycznego handlu na podstawie konfiguracji
            auto_trading_enabled = self.config.get('auto_trading_enabled', False)
            self.trading_integration.enable_trading(auto_trading_enabled)
            
            self.logger.info(f"Trading Agent MT5 uruchomiony (auto-trading: {'włączony' if auto_trading_enabled else 'wyłączony'})")
            
            # Główna pętla aplikacji
            while self.is_running:
                time.sleep(1)  # Czekamy na przerwanie przez użytkownika
                
        except KeyboardInterrupt:
            self.logger.info("Otrzymano sygnał przerwania, zatrzymywanie agenta...")
            self.stop()
        except Exception as e:
            self.logger.error(f"Błąd podczas działania agenta: {e}", exc_info=True)
            self.stop()
            raise
    
    def stop(self):
        """Zatrzymanie agenta."""
        self.logger.info("Zatrzymywanie Trading Agent MT5...")
        
        try:
            # Zatrzymanie integracji handlowej
            if self.trading_integration:
                self.trading_integration.stop()
            
            # Zamknięcie połączenia z bazą danych
            if self.db_manager:
                self.db_manager.disconnect()
            
            self.is_running = False
            self.logger.info("Trading Agent MT5 zatrzymany")
            
        except Exception as e:
            self.logger.error(f"Błąd podczas zatrzymywania agenta: {e}", exc_info=True)


if __name__ == "__main__":
    agent = TradingAgent()
    agent.start() 