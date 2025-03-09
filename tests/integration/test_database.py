#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Testy integracyjne dla bazy danych.
Sprawdzają połączenie i podstawowe operacje na bazie danych.

Uwaga: Aby testy przeszły, baza danych PostgreSQL musi być uruchomiona
i skonfigurowana zgodnie z parametrami w pliku .env lub zmiennymi środowiskowymi.
"""

import os
import sys
import unittest
import datetime
from dotenv import load_dotenv

# Dodanie głównego katalogu projektu do PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.database import DatabaseManager
from src.database.models import (
    Instrument, TradingSetup, TradingSignal, Transaction,
    OrderModification, AccountSnapshot, SystemLog,
    AIStats, PerformanceMetric
)
from src.database.repository import (
    Repository, InstrumentRepository, TradingSetupRepository,
    TradingSignalRepository, TransactionRepository
)


class TestDatabaseConnection(unittest.TestCase):
    """Testy połączenia z bazą danych."""
    
    @classmethod
    def setUpClass(cls):
        """Przygotowanie testów."""
        # Wczytanie zmiennych środowiskowych
        load_dotenv()
        
        # Inicjalizacja menedżera bazy danych
        cls.db = DatabaseManager()
        cls.db.connect()
    
    @classmethod
    def tearDownClass(cls):
        """Zakończenie testów."""
        if cls.db:
            cls.db.close()
    
    def test_connection(self):
        """Test połączenia z bazą danych."""
        # Sprawdzenie, czy połączenie działa - proste zapytanie
        result = self.db.execute_query("SELECT 1 as value")
        self.assertIsNotNone(result)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['value'], 1)
    
    def test_tables_exist(self):
        """Test, czy tabele istnieją."""
        # Sprawdzenie, czy tabele istnieją
        result = self.db.execute_query("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            ORDER BY table_name
        """)
        
        # Lista oczekiwanych tabel
        expected_tables = [
            'account_snapshots', 'ai_stats', 'instruments', 'order_modifications',
            'performance_metrics', 'system_logs', 'trading_setups', 'trading_signals',
            'transactions'
        ]
        
        # Pobranie nazw tabel z wyniku zapytania
        actual_tables = [row['table_name'] for row in result]
        
        # Sprawdzenie, czy wszystkie oczekiwane tabele istnieją
        for table in expected_tables:
            self.assertIn(table, actual_tables)


class TestRepositories(unittest.TestCase):
    """Testy repozytoriów."""
    
    @classmethod
    def setUpClass(cls):
        """Przygotowanie testów."""
        # Wczytanie zmiennych środowiskowych
        load_dotenv()
        
        # Inicjalizacja menedżera bazy danych
        cls.db = DatabaseManager()
        cls.db.connect()
        
        # Inicjalizacja repozytoriów
        cls.instrument_repo = InstrumentRepository(cls.db)
        cls.setup_repo = TradingSetupRepository(cls.db)
        cls.signal_repo = TradingSignalRepository(cls.db)
        cls.transaction_repo = TransactionRepository(cls.db)
    
    @classmethod
    def tearDownClass(cls):
        """Zakończenie testów."""
        if cls.db:
            cls.db.close()
    
    def setUp(self):
        """Przygotowanie przed każdym testem."""
        # Wyczyszczenie tabel przed każdym testem
        tables = [
            'account_snapshots', 'ai_stats', 'order_modifications',
            'performance_metrics', 'system_logs', 'transactions',
            'trading_signals', 'trading_setups', 'instruments'
        ]
        
        for table in tables:
            self.db.execute_query(f"DELETE FROM {table}", fetch=False)
    
    def test_instrument_repository(self):
        """Test repozytorium instrumentów."""
        # Utworzenie nowego instrumentu
        instrument = Instrument(
            symbol="EURUSD",
            description="Euro vs US Dollar",
            pip_value=0.0001,
            min_lot=0.01,
            max_lot=100.00,
            lot_step=0.01
        )
        
        # Zapisanie instrumentu
        saved_instrument = self.instrument_repo.create(instrument)
        self.assertIsNotNone(saved_instrument)
        self.assertIsNotNone(saved_instrument.id)
        self.assertEqual(saved_instrument.symbol, "EURUSD")
        
        # Pobranie instrumentu po ID
        fetched_instrument = self.instrument_repo.find_by_id(saved_instrument.id)
        self.assertIsNotNone(fetched_instrument)
        self.assertEqual(fetched_instrument.symbol, "EURUSD")
        
        # Pobranie instrumentu po symbolu
        fetched_by_symbol = self.instrument_repo.find_by_symbol("EURUSD")
        self.assertIsNotNone(fetched_by_symbol)
        self.assertEqual(fetched_by_symbol.symbol, "EURUSD")
        
        # Aktualizacja instrumentu
        fetched_instrument.description = "Updated description"
        updated_instrument = self.instrument_repo.update(fetched_instrument)
        self.assertEqual(updated_instrument.description, "Updated description")
        
        # Usunięcie instrumentu
        result = self.instrument_repo.delete(saved_instrument.id)
        self.assertTrue(result)
        
        # Sprawdzenie, czy instrument został usunięty
        deleted_instrument = self.instrument_repo.find_by_id(saved_instrument.id)
        self.assertIsNone(deleted_instrument)
    
    def test_trading_setup_repository(self):
        """Test repozytorium setupów tradingowych."""
        # Utworzenie nowego setupu
        setup = TradingSetup(
            name="Test Setup",
            symbol="EURUSD",
            timeframe="H1",
            setup_type="breakout",
            direction="buy",
            entry_conditions="Test entry conditions",
            exit_conditions="Test exit conditions",
            risk_reward_ratio=2.0,
            success_rate=0.7
        )
        
        # Zapisanie setupu
        saved_setup = self.setup_repo.create(setup)
        self.assertIsNotNone(saved_setup)
        self.assertIsNotNone(saved_setup.id)
        self.assertEqual(saved_setup.name, "Test Setup")
        
        # Pobranie setupu po symbolu i timeframe
        setups = self.setup_repo.find_by_symbol_and_timeframe("EURUSD", "H1")
        self.assertEqual(len(setups), 1)
        self.assertEqual(setups[0].name, "Test Setup")
    
    def test_trading_signal_repository(self):
        """Test repozytorium sygnałów tradingowych."""
        # Utworzenie nowego sygnału
        signal = TradingSignal(
            symbol="EURUSD",
            timeframe="H1",
            direction="buy",
            entry_price=1.1000,
            stop_loss=1.0950,
            take_profit=1.1100,
            confidence=0.8,
            status="pending"
        )
        
        # Zapisanie sygnału
        saved_signal = self.signal_repo.create(signal)
        self.assertIsNotNone(saved_signal)
        self.assertIsNotNone(saved_signal.id)
        
        # Pobranie aktywnych sygnałów
        active_signals = self.signal_repo.find_active_signals()
        self.assertEqual(len(active_signals), 1)
        
        # Zmiana statusu sygnału
        saved_signal.status = "executed"
        updated_signal = self.signal_repo.update(saved_signal)
        self.assertEqual(updated_signal.status, "executed")
        
        # Pobranie aktywnych sygnałów po zmianie statusu
        active_signals = self.signal_repo.find_active_signals()
        self.assertEqual(len(active_signals), 0)
    
    def test_transaction_repository(self):
        """Test repozytorium transakcji."""
        # Utworzenie nowej transakcji
        transaction = Transaction(
            symbol="EURUSD",
            order_type="buy",
            volume=0.1,
            status="open",
            open_price=1.1000,
            stop_loss=1.0950,
            take_profit=1.1100,
            mt5_order_id=12345,
            open_time=datetime.datetime.now()
        )
        
        # Zapisanie transakcji
        saved_transaction = self.transaction_repo.create(transaction)
        self.assertIsNotNone(saved_transaction)
        self.assertIsNotNone(saved_transaction.id)
        
        # Pobranie otwartych pozycji
        open_positions = self.transaction_repo.find_open_positions()
        self.assertEqual(len(open_positions), 1)
        
        # Zamknięcie transakcji
        saved_transaction.status = "closed"
        saved_transaction.close_price = 1.1050
        saved_transaction.close_time = datetime.datetime.now()
        saved_transaction.profit = 50.0
        updated_transaction = self.transaction_repo.update(saved_transaction)
        self.assertEqual(updated_transaction.status, "closed")
        
        # Pobranie otwartych pozycji po zamknięciu
        open_positions = self.transaction_repo.find_open_positions()
        self.assertEqual(len(open_positions), 0)


if __name__ == '__main__':
    unittest.main() 