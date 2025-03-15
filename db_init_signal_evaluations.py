#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Skrypt do inicjalizacji tabeli signal_evaluations w bazie danych.
Tabela ta przechowuje wyniki oceny sygnałów tradingowych.
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

def create_signal_evaluations_table():
    """
    Tworzy tabelę signal_evaluations w bazie danych.
    """
    try:
        db_manager = DatabaseManager()
        
        # Sprawdzenie czy tabela już istnieje
        query = """
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public'
                AND table_name = 'signal_evaluations'
            );
        """
        result = db_manager.execute_query(query)
        table_exists = result[0]['exists'] if result else False
        
        if table_exists:
            logger.info("Tabela signal_evaluations już istnieje w bazie danych.")
            
            # Usunięcie istniejącej tabeli
            logger.info("Usuwanie istniejącej tabeli signal_evaluations...")
            drop_query = "DROP TABLE signal_evaluations CASCADE;"
            db_manager.execute_query(drop_query, fetch=False)
            logger.info("Tabela signal_evaluations została usunięta.")
        
        # Utworzenie tabeli signal_evaluations
        query = """
        CREATE TABLE signal_evaluations (
            id SERIAL PRIMARY KEY,
            signal_id VARCHAR(100) NOT NULL,
            symbol VARCHAR(20) NOT NULL,
            timeframe VARCHAR(10) NOT NULL,
            direction VARCHAR(10) NOT NULL,
            entry_price FLOAT NOT NULL,
            stop_loss FLOAT NOT NULL,
            take_profit FLOAT NOT NULL,
            max_profit FLOAT NOT NULL,
            max_loss FLOAT NOT NULL,
            exit_price FLOAT,
            actual_profit FLOAT,
            actual_loss FLOAT,
            realized_pips FLOAT,
            risk_reward_ratio FLOAT,
            hit_target BOOLEAN,
            hit_stop BOOLEAN,
            hit_neither BOOLEAN,
            time_to_target INTEGER,
            time_to_stop INTEGER,
            price_movement_percentage FLOAT,
            profit_loss_ratio FLOAT,
            entry_time TIMESTAMP NOT NULL,
            exit_time TIMESTAMP,
            evaluation_status VARCHAR(20) NOT NULL,
            metadata JSONB DEFAULT '{}',
            confidence FLOAT DEFAULT 0.0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        CREATE INDEX idx_signal_evaluations_signal_id ON signal_evaluations(signal_id);
        CREATE INDEX idx_signal_evaluations_symbol ON signal_evaluations(symbol);
        CREATE INDEX idx_signal_evaluations_timeframe ON signal_evaluations(timeframe);
        CREATE INDEX idx_signal_evaluations_direction ON signal_evaluations(direction);
        CREATE INDEX idx_signal_evaluations_evaluation_status ON signal_evaluations(evaluation_status);
        CREATE INDEX idx_signal_evaluations_entry_time ON signal_evaluations(entry_time);
        CREATE INDEX idx_signal_evaluations_updated_at ON signal_evaluations(updated_at);
        """
        
        db_manager.execute_query(query, fetch=False)
        logger.info("Tabela signal_evaluations została utworzona pomyślnie.")
        
        return True
        
    except Exception as e:
        logger.error(f"Błąd podczas tworzenia tabeli signal_evaluations: {e}")
        return False

def main():
    """
    Główna funkcja inicjalizacji bazy danych.
    """
    logger.info("Rozpoczęto inicjalizację tabeli signal_evaluations...")
    success = create_signal_evaluations_table()
    
    if success:
        logger.info("Inicjalizacja tabeli signal_evaluations zakończona pomyślnie.")
    else:
        logger.error("Inicjalizacja tabeli signal_evaluations zakończona niepowodzeniem.")
        sys.exit(1)

if __name__ == "__main__":
    main() 