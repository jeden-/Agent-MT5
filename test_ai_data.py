#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Test dostępności danych AI Analytics.
"""

import os
import sys
import logging
from pathlib import Path
import traceback
from datetime import datetime

# Dodaj ścieżkę projektu do PYTHONPATH
project_root = Path(__file__).parent
sys.path.append(str(project_root))

# Konfiguracja logowania
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def check_ai_data():
    """Sprawdza dostępność danych AI w bazie danych."""
    try:
        from src.database.db_manager import get_db_manager
        
        # Pobierz instancję menedżera bazy danych
        db_manager = get_db_manager()
        
        # Sprawdź tabele związane z AI
        relevant_tables = [
            'trading_signals',
            'ai_stats',
            'signal_evaluations'
        ]
        
        print("Sprawdzanie danych AI Analytics...")
        
        for table in relevant_tables:
            try:
                # Sprawdź liczbę rekordów w tabeli
                count_query = f"SELECT COUNT(*) FROM {table}"
                count_result = db_manager.execute_query(count_query)
                record_count = count_result[0][0] if count_result else 0
                
                print(f"\nTabela {table}: {record_count} rekordów")
                
                # Jeśli są jakieś rekordy, pobierz przykładowe dane
                if record_count > 0:
                    # Najpierw pobierz informacje o kolumnach
                    column_query = f"""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name = '{table}'
                    ORDER BY ordinal_position
                    """
                    column_result = db_manager.execute_query(column_query)
                    columns = [col[0] for col in column_result]
                    
                    print(f"Kolumny: {', '.join(columns)}")
                    
                    # Teraz pobierz przykładowe dane
                    sample_query = f"SELECT * FROM {table} LIMIT 3"
                    sample_data = db_manager.execute_query(sample_query)
                    
                    # Wyświetl przykładowe dane
                    print("Przykładowe dane:")
                    for row in sample_data:
                        # Konwertuj row na słownik dla czytelności
                        row_dict = {columns[i]: str(value)[:50] + ('...' if len(str(value)) > 50 else '') 
                                   for i, value in enumerate(row) if i < len(columns)}
                        print(row_dict)
            except Exception as e:
                print(f"❌ Błąd podczas sprawdzania tabeli {table}: {e}")
                traceback.print_exc()
        
        # Sprawdź sygnały handlowe
        print("\n--- Szczegóły sygnałów handlowych ---")
        try:
            # Policz sygnały według modelu AI
            model_query = """
            SELECT model_name, COUNT(*) as signal_count 
            FROM trading_signals 
            WHERE model_name IS NOT NULL
            GROUP BY model_name 
            ORDER BY signal_count DESC
            """
            model_result = db_manager.execute_query(model_query)
            
            if model_result:
                print("\nLiczba sygnałów według modelu AI:")
                for row in model_result:
                    print(f"- {row[0]}: {row[1]} sygnałów")
            else:
                print("\nBrak danych o modelach AI w sygnałach.")
            
            # Policz sygnały według instrumentu
            symbol_query = """
            SELECT symbol, COUNT(*) as signal_count 
            FROM trading_signals 
            GROUP BY symbol 
            ORDER BY signal_count DESC
            """
            symbol_result = db_manager.execute_query(symbol_query)
            
            if symbol_result:
                print("\nLiczba sygnałów według instrumentu:")
                for row in symbol_result:
                    print(f"- {row[0]}: {row[1]} sygnałów")
            else:
                print("\nBrak danych o sygnałach dla instrumentów.")
                    
            # Policz sygnały według kierunku
            direction_query = """
            SELECT direction, COUNT(*) as signal_count 
            FROM trading_signals 
            GROUP BY direction
            """
            direction_result = db_manager.execute_query(direction_query)
            
            if direction_result:
                print("\nLiczba sygnałów według kierunku:")
                for row in direction_result:
                    print(f"- {row[0]}: {row[1]} sygnałów")
            else:
                print("\nBrak danych o kierunkach sygnałów.")
                    
            # Sprawdź najnowsze sygnały
            latest_query = """
            SELECT id, symbol, direction, confidence, created_at 
            FROM trading_signals 
            ORDER BY created_at DESC 
            LIMIT 5
            """
            latest_result = db_manager.execute_query(latest_query)
            
            if latest_result:
                print("\nNajnowsze sygnały:")
                for row in latest_result:
                    print(f"- ID: {row[0]}, Symbol: {row[1]}, Kierunek: {row[2]}, Pewność: {row[3]}, Data: {row[4]}")
            else:
                print("\nBrak najnowszych sygnałów.")
            
        except Exception as e:
            print(f"❌ Błąd podczas analizy sygnałów handlowych: {e}")
            traceback.print_exc()
        
        
    except Exception as e:
        print(f"❌ Błąd podczas sprawdzania danych AI: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    check_ai_data() 