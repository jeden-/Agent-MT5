#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Skrypt do inicjalizacji bazy danych i wypełnienia jej początkowymi danymi.
"""

import os
import sys
import logging
from datetime import datetime

# Dodanie głównego katalogu projektu do PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.database import DatabaseManager
from src.utils import setup_logging

def init_database():
    """Inicjalizacja bazy danych i utworzenie tabel."""
    logger = setup_logging()
    logger.info("Rozpoczęcie inicjalizacji bazy danych...")
    
    db = DatabaseManager()
    try:
        # Utworzenie tabel
        db.create_tables()
        logger.info("Tabele zostały utworzone pomyślnie")
        
        # Wypełnienie tabel początkowymi danymi
        populate_initial_data(db)
        logger.info("Baza danych została zainicjalizowana pomyślnie")
    except Exception as e:
        logger.error(f"Błąd podczas inicjalizacji bazy danych: {e}", exc_info=True)
        sys.exit(1)
    finally:
        db.close()

def populate_initial_data(db):
    """Wypełnienie tabel początkowymi danymi."""
    logger = logging.getLogger('trading_agent.database')
    
    # Dodanie instrumentów
    instruments = [
        ('EURUSD', 'Euro vs US Dollar', 0.0001, 0.01, 100.00, 0.01),
        ('GBPUSD', 'Great Britain Pound vs US Dollar', 0.0001, 0.01, 100.00, 0.01),
        ('USDJPY', 'US Dollar vs Japanese Yen', 0.01, 0.01, 100.00, 0.01),
        ('AUDUSD', 'Australian Dollar vs US Dollar', 0.0001, 0.01, 100.00, 0.01),
        ('USDCHF', 'US Dollar vs Swiss Franc', 0.0001, 0.01, 100.00, 0.01),
        ('USDCAD', 'US Dollar vs Canadian Dollar', 0.0001, 0.01, 100.00, 0.01)
    ]
    
    logger.info("Dodawanie instrumentów...")
    for instrument in instruments:
        try:
            db.execute_query(
                """
                INSERT INTO instruments 
                    (symbol, description, pip_value, min_lot, max_lot, lot_step)
                VALUES 
                    (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (symbol) DO UPDATE SET
                    description = EXCLUDED.description,
                    pip_value = EXCLUDED.pip_value,
                    min_lot = EXCLUDED.min_lot,
                    max_lot = EXCLUDED.max_lot,
                    lot_step = EXCLUDED.lot_step,
                    updated_at = CURRENT_TIMESTAMP
                """,
                instrument,
                fetch=False
            )
        except Exception as e:
            logger.error(f"Błąd podczas dodawania instrumentu {instrument[0]}: {e}")
    
    # Dodanie przykładowych setupów
    setups = [
        (
            'EURUSD Breakout', 
            'Wybicie z konsolidacji na EURUSD', 
            'EURUSD', 
            'H1', 
            'breakout', 
            'buy', 
            'Wybicie powyżej resistance po min. 3h konsolidacji', 
            'Osiągnięcie TP lub hit SL',
            2.5,
            0.65
        ),
        (
            'GBPUSD Pullback', 
            'Korekta trendu wzrostowego na GBPUSD', 
            'GBPUSD', 
            'H4', 
            'pullback', 
            'buy', 
            'Korekta do MA20 w trendzie wzrostowym', 
            'Osiągnięcie TP lub hit SL',
            2.0,
            0.70
        )
    ]
    
    logger.info("Dodawanie przykładowych setupów...")
    for setup in setups:
        try:
            db.execute_query(
                """
                INSERT INTO trading_setups
                    (name, description, symbol, timeframe, setup_type, direction,
                     entry_conditions, exit_conditions, risk_reward_ratio, success_rate)
                VALUES
                    (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT DO NOTHING
                """,
                setup,
                fetch=False
            )
        except Exception as e:
            logger.error(f"Błąd podczas dodawania setupu {setup[0]}: {e}")

if __name__ == "__main__":
    init_database() 