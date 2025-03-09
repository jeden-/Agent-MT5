#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Narzędzie wiersza poleceń do zarządzania bazą danych.
Pozwala na inicjalizację, czyszczenie i zapytania do bazy danych.
"""

import os
import sys
import argparse
import logging
from tabulate import tabulate

# Dodanie głównego katalogu projektu do PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.database import DatabaseManager
from src.database.models import (
    Instrument, TradingSetup, TradingSignal, Transaction,
    OrderModification, AccountSnapshot, SystemLog,
    AIStats, PerformanceMetric
)
from src.utils import setup_logging
from scripts.init_database import init_database

def parse_args():
    """Parsuje argumenty wiersza poleceń."""
    parser = argparse.ArgumentParser(description='Narzędzie wiersza poleceń do zarządzania bazą danych')
    
    subparsers = parser.add_subparsers(dest='command', help='Komenda do wykonania')
    
    # Inicjalizacja bazy danych
    init_parser = subparsers.add_parser('init', help='Inicjalizacja bazy danych')
    
    # Czyszczenie bazy danych
    clear_parser = subparsers.add_parser('clear', help='Czyszczenie bazy danych')
    clear_parser.add_argument('--table', help='Nazwa tabeli do wyczyszczenia (jeśli nie podano, czyści wszystkie)')
    clear_parser.add_argument('--confirm', action='store_true', help='Potwierdź czyszczenie bez dodatkowego pytania')
    
    # Zapytanie do bazy danych
    query_parser = subparsers.add_parser('query', help='Wykonanie zapytania SQL')
    query_parser.add_argument('--table', required=True, help='Nazwa tabeli')
    query_parser.add_argument('--where', help='Warunek WHERE (opcjonalnie)')
    query_parser.add_argument('--limit', type=int, default=10, help='Limit wyników (domyślnie 10)')
    
    # Status bazy danych
    status_parser = subparsers.add_parser('status', help='Sprawdzenie statusu bazy danych')
    
    # Wykonanie niestandardowego zapytania SQL
    sql_parser = subparsers.add_parser('sql', help='Wykonanie niestandardowego zapytania SQL')
    sql_parser.add_argument('--query', required=True, help='Zapytanie SQL')
    
    return parser.parse_args()

def clear_database(db, table=None, confirm=False):
    """Czyści bazę danych lub określoną tabelę."""
    logger = logging.getLogger('trading_agent.db_cli')
    
    if table:
        tables = [table]
        message = f"Czy na pewno chcesz wyczyścić tabelę '{table}'? [t/N]: "
    else:
        tables = [
            "performance_metrics", "ai_stats", "system_logs", "account_snapshots",
            "order_modifications", "transactions", "trading_signals", "trading_setups",
            "instruments"
        ]
        message = "Czy na pewno chcesz wyczyścić WSZYSTKIE tabele w bazie danych? [t/N]: "
    
    if not confirm:
        confirmation = input(message)
        if confirmation.lower() != 't':
            logger.info("Operacja anulowana przez użytkownika")
            return
    
    for table_name in tables:
        try:
            db.execute_query(f"DELETE FROM {table_name}", fetch=False)
            logger.info(f"Tabela '{table_name}' została wyczyszczona")
        except Exception as e:
            logger.error(f"Błąd podczas czyszczenia tabeli '{table_name}': {e}")

def query_database(db, table, where=None, limit=10):
    """Wykonuje zapytanie do bazy danych."""
    logger = logging.getLogger('trading_agent.db_cli')
    
    try:
        sql = f"SELECT * FROM {table}"
        if where:
            sql += f" WHERE {where}"
        sql += f" LIMIT {limit}"
        
        results = db.execute_query(sql)
        
        if not results:
            logger.info(f"Brak wyników dla zapytania: {sql}")
            return
        
        # Przygotowanie danych do wyświetlenia w tabeli
        headers = results[0].keys()
        rows = [list(row.values()) for row in results]
        
        print(tabulate(rows, headers=headers, tablefmt="grid"))
        logger.info(f"Znaleziono {len(results)} wyników")
    except Exception as e:
        logger.error(f"Błąd podczas wykonywania zapytania: {e}")

def execute_custom_sql(db, query):
    """Wykonuje niestandardowe zapytanie SQL."""
    logger = logging.getLogger('trading_agent.db_cli')
    
    try:
        results = db.execute_query(query)
        
        if not results:
            logger.info("Zapytanie wykonane, brak wyników do wyświetlenia")
            return
        
        # Przygotowanie danych do wyświetlenia w tabeli
        headers = results[0].keys()
        rows = [list(row.values()) for row in results]
        
        print(tabulate(rows, headers=headers, tablefmt="grid"))
        logger.info(f"Znaleziono {len(results)} wyników")
    except Exception as e:
        logger.error(f"Błąd podczas wykonywania zapytania: {e}")

def show_database_status(db):
    """Pokazuje status bazy danych."""
    logger = logging.getLogger('trading_agent.db_cli')
    
    try:
        # Liczba wierszy w każdej tabeli
        tables = [
            "instruments", "trading_setups", "trading_signals", "transactions",
            "order_modifications", "account_snapshots", "system_logs",
            "ai_stats", "performance_metrics"
        ]
        
        table_stats = []
        for table_name in tables:
            try:
                count = db.execute_query(f"SELECT COUNT(*) as count FROM {table_name}")[0]['count']
                table_stats.append([table_name, count])
            except Exception as e:
                logger.error(f"Błąd podczas pobierania statystyk tabeli '{table_name}': {e}")
                table_stats.append([table_name, "ERROR"])
        
        print("\nStatystyki tabel:")
        print(tabulate(table_stats, headers=["Tabela", "Liczba wierszy"], tablefmt="grid"))
        
        # Informacje o bazie danych
        version = db.execute_query("SHOW server_version")[0]['server_version']
        size = db.execute_query("""
            SELECT pg_size_pretty(pg_database_size(current_database())) as db_size
        """)[0]['db_size']
        
        print("\nInformacje o bazie danych:")
        print(f"Wersja PostgreSQL: {version}")
        print(f"Rozmiar bazy danych: {size}")
        
    except Exception as e:
        logger.error(f"Błąd podczas pobierania statusu bazy danych: {e}")

def main():
    """Główna funkcja programu."""
    args = parse_args()
    logger = setup_logging(log_name='trading_agent.db_cli')
    
    # Inicjalizacja menedżera bazy danych
    db = DatabaseManager()
    
    try:
        db.connect()
        
        if args.command == 'init':
            logger.info("Inicjalizacja bazy danych...")
            init_database()
            logger.info("Inicjalizacja bazy danych zakończona")
        
        elif args.command == 'clear':
            clear_database(db, args.table, args.confirm)
        
        elif args.command == 'query':
            query_database(db, args.table, args.where, args.limit)
        
        elif args.command == 'status':
            show_database_status(db)
        
        elif args.command == 'sql':
            execute_custom_sql(db, args.query)
        
        else:
            logger.error("Nie podano komendy. Użyj --help, aby zobaczyć dostępne opcje.")
    
    except Exception as e:
        logger.error(f"Błąd podczas wykonywania operacji na bazie danych: {e}", exc_info=True)
    
    finally:
        db.close()

if __name__ == "__main__":
    main() 