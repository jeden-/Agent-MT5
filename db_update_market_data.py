#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Skrypt do aktualizacji tabeli market_data w bazie danych.
Dodaje brakujące kolumny, w tym timeframe, jeśli nie istnieją.
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
logger = logging.getLogger("db_update")

# Dodanie głównego katalogu projektu do PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Ładowanie zmiennych środowiskowych
load_dotenv()
logger.info("Zmienne środowiskowe załadowane z pliku .env")

# Import komponentów
from src.database.db_manager import DatabaseManager

def check_column_exists(db_manager, table_name, column_name):
    """
    Sprawdza czy kolumna istnieje w tabeli.
    
    Args:
        db_manager: Instancja DatabaseManager
        table_name: Nazwa tabeli
        column_name: Nazwa kolumny
        
    Returns:
        bool: True jeśli kolumna istnieje, False w przeciwnym razie
    """
    query = """
        SELECT EXISTS (
            SELECT FROM information_schema.columns 
            WHERE table_schema = 'public'
            AND table_name = %s
            AND column_name = %s
        );
    """
    result = db_manager.execute_query(query, (table_name, column_name))
    return result[0]['exists'] if result else False

def update_market_data_table():
    """
    Aktualizuje tabelę market_data, dodając brakujące kolumny.
    """
    try:
        db_manager = DatabaseManager()
        
        # Sprawdzenie czy tabela istnieje
        query = """
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public'
                AND table_name = 'market_data'
            );
        """
        result = db_manager.execute_query(query)
        table_exists = result[0]['exists'] if result else False
        
        if not table_exists:
            logger.error("Tabela market_data nie istnieje w bazie danych.")
            return False
        
        # Lista kolumn do sprawdzenia i ewentualnego dodania
        columns_to_check = [
            {"name": "symbol", "type": "VARCHAR(20) NOT NULL DEFAULT ''"},
            {"name": "timeframe", "type": "VARCHAR(10) NOT NULL DEFAULT 'M5'"},
            {"name": "timestamp", "type": "TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP"},
            {"name": "open", "type": "FLOAT NOT NULL DEFAULT 0.0"},
            {"name": "high", "type": "FLOAT NOT NULL DEFAULT 0.0"},
            {"name": "low", "type": "FLOAT NOT NULL DEFAULT 0.0"},
            {"name": "close", "type": "FLOAT NOT NULL DEFAULT 0.0"},
            {"name": "tick_volume", "type": "INT NOT NULL DEFAULT 0"},
            {"name": "spread", "type": "INT DEFAULT 0"},
            {"name": "real_volume", "type": "FLOAT DEFAULT 0.0"},
            {"name": "volume", "type": "FLOAT DEFAULT 0.0"},
            {"name": "created_at", "type": "TIMESTAMP DEFAULT CURRENT_TIMESTAMP"}
        ]
        
        for column in columns_to_check:
            column_exists = check_column_exists(db_manager, 'market_data', column['name'])
            
            if not column_exists:
                # Dodanie kolumny
                logger.info(f"Dodawanie kolumny {column['name']} do tabeli market_data...")
                query = f"""
                    ALTER TABLE market_data 
                    ADD COLUMN {column['name']} {column['type']};
                """
                db_manager.execute_query(query, fetch=False)
                logger.info(f"Kolumna {column['name']} została dodana.")
            else:
                logger.info(f"Kolumna {column['name']} już istnieje w tabeli market_data.")
        
        # Sprawdzenie ograniczeń kolumn
        try:
            # Sprawdzenie, czy kolumna "volume" ma ograniczenie NOT NULL
            query = """
                SELECT is_nullable
                FROM information_schema.columns
                WHERE table_schema = 'public'
                AND table_name = 'market_data'
                AND column_name = 'volume';
            """
            result = db_manager.execute_query(query)
            
            if result and result[0]['is_nullable'] == 'NO':
                logger.info("Modyfikacja ograniczenia NOT NULL dla kolumny volume...")
                query = """
                    ALTER TABLE market_data
                    ALTER COLUMN volume DROP NOT NULL;
                """
                db_manager.execute_query(query, fetch=False)
                logger.info("Ograniczenie NOT NULL dla kolumny volume usunięte.")
                
                # Dodanie wartości domyślnej
                query = """
                    ALTER TABLE market_data
                    ALTER COLUMN volume SET DEFAULT 0.0;
                """
                db_manager.execute_query(query, fetch=False)
                logger.info("Wartość domyślna dla kolumny volume ustawiona na 0.0.")
        except Exception as e:
            logger.error(f"Błąd podczas modyfikacji ograniczeń kolumny volume: {e}")
        
        # Aktualizacja ograniczenia unikalności
        try:
            # Sprawdzenie, czy istnieje ograniczenie unikalności "market_data_symbol_timestamp_key"
            query = """
                SELECT con.conname
                FROM pg_constraint con
                JOIN pg_class rel ON rel.oid = con.conrelid
                JOIN pg_namespace nsp ON nsp.oid = rel.relnamespace
                WHERE nsp.nspname = 'public'
                AND rel.relname = 'market_data'
                AND con.conname = 'market_data_symbol_timestamp_key';
            """
            result = db_manager.execute_query(query)
            
            if result and len(result) > 0:
                logger.info("Usuwanie starego ograniczenia unikalności (symbol, timestamp)...")
                query = """
                    ALTER TABLE market_data
                    DROP CONSTRAINT market_data_symbol_timestamp_key;
                """
                db_manager.execute_query(query, fetch=False)
                logger.info("Stare ograniczenie unikalności usunięte.")
                
                # Dodanie nowego ograniczenia
                query = """
                    ALTER TABLE market_data
                    ADD CONSTRAINT market_data_symbol_timeframe_timestamp_key
                    UNIQUE (symbol, timeframe, timestamp);
                """
                db_manager.execute_query(query, fetch=False)
                logger.info("Dodano nowe ograniczenie unikalności (symbol, timeframe, timestamp).")
            else:
                # Sprawdzenie czy istnieje inne ograniczenie unikalności dla symbol i timestamp
                query = """
                    SELECT con.conname
                    FROM pg_constraint con
                    JOIN pg_class rel ON rel.oid = con.conrelid
                    JOIN pg_namespace nsp ON nsp.oid = rel.relnamespace
                    WHERE nsp.nspname = 'public'
                    AND rel.relname = 'market_data'
                    AND con.contype = 'u'
                    AND array_length(con.conkey, 1) = 2;
                """
                result = db_manager.execute_query(query)
                
                if result and len(result) > 0:
                    constraint_name = result[0]['conname']
                    logger.info(f"Usuwanie ograniczenia unikalności {constraint_name}...")
                    query = f"""
                        ALTER TABLE market_data
                        DROP CONSTRAINT {constraint_name};
                    """
                    db_manager.execute_query(query, fetch=False)
                    logger.info(f"Ograniczenie {constraint_name} usunięte.")
                
                # Sprawdzenie, czy już istnieje ograniczenie (symbol, timeframe, timestamp)
                query = """
                    SELECT EXISTS (
                        SELECT con.conname
                        FROM pg_constraint con
                        JOIN pg_class rel ON rel.oid = con.conrelid
                        JOIN pg_namespace nsp ON nsp.oid = rel.relnamespace
                        WHERE nsp.nspname = 'public'
                        AND rel.relname = 'market_data'
                        AND con.conname = 'market_data_symbol_timeframe_timestamp_key'
                    );
                """
                result = db_manager.execute_query(query)
                
                if not result or not result[0]['exists']:
                    # Dodanie nowego ograniczenia
                    query = """
                        ALTER TABLE market_data
                        ADD CONSTRAINT market_data_symbol_timeframe_timestamp_key
                        UNIQUE (symbol, timeframe, timestamp);
                    """
                    db_manager.execute_query(query, fetch=False)
                    logger.info("Dodano nowe ograniczenie unikalności (symbol, timeframe, timestamp).")
                else:
                    logger.info("Ograniczenie unikalności (symbol, timeframe, timestamp) już istnieje.")
        except Exception as e:
            logger.error(f"Błąd podczas aktualizacji ograniczenia unikalności: {e}")
        
        # Dodanie brakujących indeksów
        indexes_to_add = [
            {"name": "idx_market_data_timeframe", "columns": "timeframe"},
            {"name": "idx_market_data_symbol_timeframe", "columns": "symbol, timeframe"},
            {"name": "idx_market_data_symbol_timeframe_timestamp", "columns": "symbol, timeframe, timestamp"}
        ]
        
        for index in indexes_to_add:
            # Sprawdzenie czy indeks istnieje
            query = """
                SELECT EXISTS (
                    SELECT FROM pg_indexes
                    WHERE schemaname = 'public'
                    AND tablename = 'market_data'
                    AND indexname = %s
                );
            """
            result = db_manager.execute_query(query, (index['name'],))
            index_exists = result[0]['exists'] if result else False
            
            if not index_exists:
                # Dodanie indeksu
                logger.info(f"Dodawanie indeksu {index['name']} do tabeli market_data...")
                query = f"""
                    CREATE INDEX {index['name']} ON market_data({index['columns']});
                """
                db_manager.execute_query(query, fetch=False)
                logger.info(f"Indeks {index['name']} został dodany.")
            else:
                logger.info(f"Indeks {index['name']} już istnieje w tabeli market_data.")
        
        logger.info("Aktualizacja tabeli market_data zakończona pomyślnie.")
        return True
        
    except Exception as e:
        logger.error(f"Błąd podczas aktualizacji tabeli market_data: {e}")
        return False

def main():
    """
    Główna funkcja aktualizacji struktury bazy danych.
    """
    logger.info("Rozpoczęto aktualizację tabeli market_data...")
    success = update_market_data_table()
    
    if success:
        logger.info("Aktualizacja tabeli market_data zakończona pomyślnie.")
    else:
        logger.error("Aktualizacja tabeli market_data zakończona niepowodzeniem.")
        sys.exit(1)

if __name__ == "__main__":
    main() 