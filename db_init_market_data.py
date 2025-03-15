#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Skrypt do inicjalizacji tabeli market_data w bazie danych.
Tabela ta przechowuje dane historyczne rynku.
"""

import os
import sys
import logging
from dotenv import load_dotenv

# Konfiguracja loggera
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("db_init")

# Dodanie głównego katalogu projektu do PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Ładowanie zmiennych środowiskowych
load_dotenv()
logger.info("Zmienne środowiskowe załadowane z pliku .env")

# Import komponentów
from src.database.db_manager import DatabaseManager

def create_market_data_table():
    """
    Tworzy tabelę market_data w bazie danych.
    """
    try:
        db_manager = DatabaseManager()
        
        # Sprawdzenie czy tabela już istnieje
        query = """
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public'
                AND table_name = 'market_data'
            );
        """
        result = db_manager.execute_query(query)
        table_exists = result[0]['exists'] if result else False
        
        if table_exists:
            logger.info("Tabela market_data już istnieje w bazie danych.")
            return True
        
        # Utworzenie tabeli market_data
        query = """
        CREATE TABLE market_data (
            id SERIAL PRIMARY KEY,
            symbol VARCHAR(20) NOT NULL,
            timeframe VARCHAR(10) NOT NULL,
            timestamp TIMESTAMP NOT NULL,
            open FLOAT NOT NULL,
            high FLOAT NOT NULL,
            low FLOAT NOT NULL,
            close FLOAT NOT NULL,
            tick_volume INT NOT NULL,
            spread INT DEFAULT 0,
            real_volume FLOAT DEFAULT 0.0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(symbol, timeframe, timestamp)
        );
        
        CREATE INDEX idx_market_data_symbol ON market_data(symbol);
        CREATE INDEX idx_market_data_timeframe ON market_data(timeframe);
        CREATE INDEX idx_market_data_timestamp ON market_data(timestamp);
        CREATE INDEX idx_market_data_symbol_timeframe ON market_data(symbol, timeframe);
        CREATE INDEX idx_market_data_symbol_timeframe_timestamp ON market_data(symbol, timeframe, timestamp);
        """
        
        db_manager.execute_query(query, fetch=False)
        logger.info("Tabela market_data została utworzona pomyślnie.")
        
        return True
        
    except Exception as e:
        logger.error(f"Błąd podczas tworzenia tabeli market_data: {e}")
        return False

def main():
    """
    Główna funkcja inicjalizacji bazy danych.
    """
    logger.info("Rozpoczęto inicjalizację tabeli market_data...")
    success = create_market_data_table()
    
    if success:
        logger.info("Inicjalizacja tabeli market_data zakończona pomyślnie.")
    else:
        logger.error("Inicjalizacja tabeli market_data zakończona niepowodzeniem.")
        sys.exit(1)

if __name__ == "__main__":
    main() 