#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Testy integracyjne dla bazy danych.
"""

import unittest
import os
import sys
import logging
from dotenv import load_dotenv

# Dodanie głównego katalogu projektu do PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from src.database import (
    DatabaseManager, Instrument, InstrumentRepository
)


class TestDatabaseIntegration(unittest.TestCase):
    """Testy integracyjne dla bazy danych."""
    
    @classmethod
    def setUpClass(cls):
        """Przygotowanie środowiska testowego przed wszystkimi testami."""
        # Konfiguracja logowania
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        
        # Wczytanie zmiennych środowiskowych
        load_dotenv()
        
        # Utworzenie połączenia z bazą danych
        cls.db_manager = DatabaseManager()
        
        try:
            # Próba połączenia z bazą danych
            cls.db_manager.connect()
        except Exception as e:
            logging.error(f"Nie można połączyć się z bazą danych: {e}")
            cls.skipTest(cls, "Baza danych niedostępna")
    
    @classmethod
    def tearDownClass(cls):
        """Czyszczenie po wszystkich testach."""
        if hasattr(cls, 'db_manager'):
            cls.db_manager.close()
    
    def test_connection(self):
        """Test połączenia z bazą danych."""
        with self.db_manager.get_connection() as conn:
            self.assertIsNotNone(conn)
    
    def test_execute_query(self):
        """Test wykonywania zapytania SQL."""
        result = self.db_manager.execute_query("SELECT version();")
        self.assertIsNotNone(result)
        self.assertGreaterEqual(len(result), 1)
    
    def test_create_tables(self):
        """Test tworzenia tabel."""
        # Ten test może być pusty, jeśli tabele już istnieją
        # lub można dodać logikę sprawdzającą istnienie tabel
        try:
            self.db_manager.create_tables()
            # Sprawdzenie czy tabela instruments istnieje
            result = self.db_manager.execute_query(
                "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'instruments');"
            )
            self.assertTrue(result[0][0])
        except Exception as e:
            self.fail(f"Tworzenie tabel nie powiodło się: {e}")
    
    def test_crud_operations(self):
        """Test operacji CRUD na repozytorium."""
        # Utworzenie repozytorium
        repository = InstrumentRepository(self.db_manager)
        
        # Utworzenie nowego instrumentu
        test_symbol = "TESTEUR"
        instrument = Instrument(
            symbol=test_symbol,
            description="Test Euro",
            pip_value=0.0001,
            min_lot=0.01,
            max_lot=100.00,
            lot_step=0.01
        )
        
        # Sprawdzenie, czy instrument już istnieje i usunięcie go
        existing = repository.find_by_symbol(test_symbol)
        if existing:
            repository.delete(existing.id)
        
        # Dodanie instrumentu
        created = repository.create(instrument)
        self.assertIsNotNone(created)
        self.assertEqual(created.symbol, test_symbol)
        self.assertIsNotNone(created.id)
        
        # Pobranie instrumentu
        fetched = repository.find_by_symbol(test_symbol)
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched.symbol, test_symbol)
        
        # Aktualizacja instrumentu
        fetched.description = "Updated Test Euro"
        updated = repository.update(fetched)
        self.assertIsNotNone(updated)
        self.assertEqual(updated.description, "Updated Test Euro")
        
        # Usunięcie instrumentu
        deleted = repository.delete(fetched.id)
        self.assertTrue(deleted)
        
        # Sprawdzenie, czy instrument został usunięty
        fetched_after_delete = repository.find_by_symbol(test_symbol)
        self.assertIsNone(fetched_after_delete)


if __name__ == "__main__":
    unittest.main() 