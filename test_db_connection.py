#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Test połączenia z bazą danych.
"""

import os
import sys
import logging
from pathlib import Path
import traceback

# Dodaj ścieżkę projektu do PYTHONPATH
project_root = Path(__file__).parent
sys.path.append(str(project_root))

# Konfiguracja logowania
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_db_connection():
    """Test połączenia z bazą danych."""
    try:
        from src.database.db_manager import get_db_manager
        
        # Pobierz instancję menedżera bazy danych
        db_manager = get_db_manager()
        
        # Testuj połączenie
        connection_status = db_manager.test_connection()
        
        if connection_status:
            print("✅ Połączenie z bazą danych działa poprawnie.")
            
            # Spróbuj wykonać proste zapytanie
            try:
                result = db_manager.execute_query("SELECT current_database(), current_user, version();")
                print(f"Baza danych: {result[0][0]}")
                print(f"Użytkownik: {result[0][1]}")
                print(f"Wersja PostgreSQL: {result[0][2]}")
                
                # Sprawdź czy tabele istnieją
                tables_result = db_manager.execute_query("""
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_schema = 'public'
                    ORDER BY table_name;
                """)
                
                if tables_result:
                    print("\nDostępne tabele:")
                    for table in tables_result:
                        print(f"- {table[0]}")
                else:
                    print("\nBrak dostępnych tabel w schemacie 'public'")
                    
                    # Oferujemy możliwość utworzenia tabel
                    print("\nCzy chcesz utworzyć tabele? (tak/nie)")
                    answer = input()
                    if answer.lower() in ['tak', 't', 'yes', 'y']:
                        db_manager.create_tables()
                        print("Tabele zostały utworzone.")
                
            except Exception as e:
                print(f"❌ Błąd podczas wykonywania zapytania: {e}")
                traceback.print_exc()
        else:
            print("❌ Nie można połączyć się z bazą danych.")
            print("Sprawdź ustawienia połączenia w pliku .env:")
            
            # Wyświetl ustawienia (bez hasła)
            from dotenv import load_dotenv
            load_dotenv()
            print(f"DB_HOST: {os.getenv('DB_HOST', 'nie ustawiono')}")
            print(f"DB_PORT: {os.getenv('DB_PORT', 'nie ustawiono')}")
            print(f"DB_NAME: {os.getenv('DB_NAME', 'nie ustawiono')}")
            print(f"DB_USER: {os.getenv('DB_USER', 'nie ustawiono')}")
            
    except Exception as e:
        print(f"❌ Błąd podczas testu połączenia z bazą danych: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    test_db_connection() 