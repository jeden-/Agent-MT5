#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Testy jednostkowe dla repozytoriów bazy danych.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from src.database.models import Instrument, TradingSetup, TradingSignal
from src.database.repository import (
    Repository, InstrumentRepository, TradingSetupRepository,
    TradingSignalRepository
)
from src.database.db_manager import DatabaseManager


class TestRepository(unittest.TestCase):
    """Testy dla generycznego repozytorium."""
    
    def setUp(self):
        """Przygotowanie środowiska testowego."""
        # Mock dla DatabaseManager
        self.db_manager = Mock(spec=DatabaseManager)
        
        # Mock dla execute_query
        self.db_manager.execute_query = Mock()
        
        # Repozytorium
        self.repository = Repository(self.db_manager, 'test_table', Instrument)
    
    def test_create(self):
        """Test metody create."""
        # Przygotowanie
        entity = Instrument(symbol="EURUSD")
        self.db_manager.execute_query.return_value = [(1,)]
        
        # Wykonanie
        result = self.repository.create(entity)
        
        # Weryfikacja
        self.db_manager.execute_query.assert_called_once()
        self.assertEqual(result.symbol, "EURUSD")
        self.assertEqual(result.id, 1)
    
    def test_create_failure(self):
        """Test metody create - niepowodzenie."""
        # Przygotowanie
        entity = Instrument(symbol="EURUSD")
        self.db_manager.execute_query.return_value = None
        
        # Wykonanie
        result = self.repository.create(entity)
        
        # Weryfikacja
        self.db_manager.execute_query.assert_called_once()
        self.assertIsNone(result)
    
    def test_update(self):
        """Test metody update."""
        # Przygotowanie
        entity = Instrument(symbol="EURUSD", id=1)
        self.db_manager.execute_query.return_value = [(1,)]
        
        # Wykonanie
        result = self.repository.update(entity)
        
        # Weryfikacja
        self.db_manager.execute_query.assert_called_once()
        self.assertEqual(result.symbol, "EURUSD")
        self.assertEqual(result.id, 1)
    
    def test_update_no_id(self):
        """Test metody update - brak ID."""
        # Przygotowanie
        entity = Instrument(symbol="EURUSD")
        
        # Wykonanie
        result = self.repository.update(entity)
        
        # Weryfikacja
        self.db_manager.execute_query.assert_not_called()
        self.assertIsNone(result)
    
    def test_delete(self):
        """Test metody delete."""
        # Przygotowanie
        entity_id = 1
        self.db_manager.execute_query.return_value = [(1,)]
        
        # Wykonanie
        result = self.repository.delete(entity_id)
        
        # Weryfikacja
        self.db_manager.execute_query.assert_called_once()
        self.assertTrue(result)
    
    def test_delete_failure(self):
        """Test metody delete - niepowodzenie."""
        # Przygotowanie
        entity_id = 1
        self.db_manager.execute_query.return_value = None
        
        # Wykonanie
        result = self.repository.delete(entity_id)
        
        # Weryfikacja
        self.db_manager.execute_query.assert_called_once()
        self.assertFalse(result)
    
    def test_find_by_id(self):
        """Test metody find_by_id."""
        # Przygotowanie
        entity_id = 1
        mock_result = MagicMock()
        mock_result.keys.return_value = ['id', 'symbol', 'description']
        mock_result.__getitem__.side_effect = lambda key: {
            'id': 1,
            'symbol': 'EURUSD',
            'description': 'Euro vs US Dollar'
        }[key]
        
        self.db_manager.execute_query.return_value = [mock_result]
        
        # Wykonanie
        result = self.repository.find_by_id(entity_id)
        
        # Weryfikacja
        self.db_manager.execute_query.assert_called_once()
        self.assertIsNotNone(result)
        self.assertEqual(result.id, 1)
        self.assertEqual(result.symbol, 'EURUSD')
        self.assertEqual(result.description, 'Euro vs US Dollar')
    
    def test_find_by_id_not_found(self):
        """Test metody find_by_id - nie znaleziono."""
        # Przygotowanie
        entity_id = 1
        self.db_manager.execute_query.return_value = []
        
        # Wykonanie
        result = self.repository.find_by_id(entity_id)
        
        # Weryfikacja
        self.db_manager.execute_query.assert_called_once()
        self.assertIsNone(result)
    
    def test_find_all(self):
        """Test metody find_all."""
        # Przygotowanie
        mock_result1 = MagicMock()
        mock_result1.keys.return_value = ['id', 'symbol', 'description']
        mock_result1.__getitem__.side_effect = lambda key: {
            'id': 1,
            'symbol': 'EURUSD',
            'description': 'Euro vs US Dollar'
        }[key]
        
        mock_result2 = MagicMock()
        mock_result2.keys.return_value = ['id', 'symbol', 'description']
        mock_result2.__getitem__.side_effect = lambda key: {
            'id': 2,
            'symbol': 'GBPUSD',
            'description': 'Great Britain Pound vs US Dollar'
        }[key]
        
        self.db_manager.execute_query.return_value = [mock_result1, mock_result2]
        
        # Wykonanie
        result = self.repository.find_all(limit=10, offset=0)
        
        # Weryfikacja
        self.db_manager.execute_query.assert_called_once()
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0].id, 1)
        self.assertEqual(result[0].symbol, 'EURUSD')
        self.assertEqual(result[1].id, 2)
        self.assertEqual(result[1].symbol, 'GBPUSD')
    
    def test_find_all_empty(self):
        """Test metody find_all - brak wyników."""
        # Przygotowanie
        self.db_manager.execute_query.return_value = []
        
        # Wykonanie
        result = self.repository.find_all(limit=10, offset=0)
        
        # Weryfikacja
        self.db_manager.execute_query.assert_called_once()
        self.assertEqual(len(result), 0)
    
    def test_find_by_field(self):
        """Test metody find_by_field."""
        # Przygotowanie
        field_name = 'symbol'
        field_value = 'EURUSD'
        
        mock_result = MagicMock()
        mock_result.keys.return_value = ['id', 'symbol', 'description']
        mock_result.__getitem__.side_effect = lambda key: {
            'id': 1,
            'symbol': 'EURUSD',
            'description': 'Euro vs US Dollar'
        }[key]
        
        self.db_manager.execute_query.return_value = [mock_result]
        
        # Wykonanie
        result = self.repository.find_by_field(field_name, field_value)
        
        # Weryfikacja
        self.db_manager.execute_query.assert_called_once()
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].id, 1)
        self.assertEqual(result[0].symbol, 'EURUSD')
        self.assertEqual(result[0].description, 'Euro vs US Dollar')
    
    def test_find_by_field_not_found(self):
        """Test metody find_by_field - nie znaleziono."""
        # Przygotowanie
        field_name = 'symbol'
        field_value = 'EURUSD'
        self.db_manager.execute_query.return_value = []
        
        # Wykonanie
        result = self.repository.find_by_field(field_name, field_value)
        
        # Weryfikacja
        self.db_manager.execute_query.assert_called_once()
        self.assertEqual(len(result), 0)


class TestInstrumentRepository(unittest.TestCase):
    """Testy dla InstrumentRepository."""
    
    def setUp(self):
        """Przygotowanie środowiska testowego."""
        # Mock dla DatabaseManager
        self.db_manager = Mock(spec=DatabaseManager)
        
        # Mock dla execute_query
        self.db_manager.execute_query = Mock()
        
        # Repozytorium
        self.repository = InstrumentRepository(self.db_manager)
    
    def test_find_by_symbol(self):
        """Test metody find_by_symbol."""
        # Przygotowanie
        symbol = 'EURUSD'
        
        mock_result = MagicMock()
        mock_result.keys.return_value = ['id', 'symbol', 'description']
        mock_result.__getitem__.side_effect = lambda key: {
            'id': 1,
            'symbol': 'EURUSD',
            'description': 'Euro vs US Dollar'
        }[key]
        
        self.db_manager.execute_query.return_value = [mock_result]
        
        # Wykonanie
        result = self.repository.find_by_symbol(symbol)
        
        # Weryfikacja
        self.db_manager.execute_query.assert_called_once()
        self.assertIsNotNone(result)
        self.assertEqual(result.id, 1)
        self.assertEqual(result.symbol, 'EURUSD')
        self.assertEqual(result.description, 'Euro vs US Dollar')
    
    def test_find_by_symbol_not_found(self):
        """Test metody find_by_symbol - nie znaleziono."""
        # Przygotowanie
        symbol = 'EURUSD'
        self.db_manager.execute_query.return_value = []
        
        # Wykonanie
        result = self.repository.find_by_symbol(symbol)
        
        # Weryfikacja
        self.db_manager.execute_query.assert_called_once()
        self.assertIsNone(result)


class TestTradingSetupRepository(unittest.TestCase):
    """Testy dla TradingSetupRepository."""
    
    def setUp(self):
        """Przygotowanie środowiska testowego."""
        # Mock dla DatabaseManager
        self.db_manager = Mock(spec=DatabaseManager)
        
        # Mock dla execute_query
        self.db_manager.execute_query = Mock()
        
        # Repozytorium
        self.repository = TradingSetupRepository(self.db_manager)
    
    def test_find_by_symbol_and_timeframe(self):
        """Test metody find_by_symbol_and_timeframe."""
        # Przygotowanie
        symbol = 'EURUSD'
        timeframe = 'H1'
        
        mock_result = MagicMock()
        mock_result.keys.return_value = ['id', 'name', 'symbol', 'timeframe', 'setup_type', 'direction', 'entry_conditions']
        mock_result.__getitem__.side_effect = lambda key: {
            'id': 1,
            'name': 'EURUSD Breakout',
            'symbol': 'EURUSD',
            'timeframe': 'H1',
            'setup_type': 'breakout',
            'direction': 'buy',
            'entry_conditions': 'Breakout above resistance'
        }[key]
        
        self.db_manager.execute_query.return_value = [mock_result]
        
        # Wykonanie
        result = self.repository.find_by_symbol_and_timeframe(symbol, timeframe)
        
        # Weryfikacja
        self.db_manager.execute_query.assert_called_once()
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].id, 1)
        self.assertEqual(result[0].name, 'EURUSD Breakout')
        self.assertEqual(result[0].symbol, 'EURUSD')
        self.assertEqual(result[0].timeframe, 'H1')
        self.assertEqual(result[0].setup_type, 'breakout')
        self.assertEqual(result[0].direction, 'buy')
        self.assertEqual(result[0].entry_conditions, 'Breakout above resistance')
    
    def test_find_by_symbol_and_timeframe_not_found(self):
        """Test metody find_by_symbol_and_timeframe - nie znaleziono."""
        # Przygotowanie
        symbol = 'EURUSD'
        timeframe = 'H1'
        self.db_manager.execute_query.return_value = []
        
        # Wykonanie
        result = self.repository.find_by_symbol_and_timeframe(symbol, timeframe)
        
        # Weryfikacja
        self.db_manager.execute_query.assert_called_once()
        self.assertEqual(len(result), 0)


class TestTradingSignalRepository(unittest.TestCase):
    """Testy dla TradingSignalRepository."""
    
    def setUp(self):
        """Przygotowanie środowiska testowego."""
        # Mock dla DatabaseManager
        self.db_manager = Mock(spec=DatabaseManager)
        
        # Mock dla execute_query
        self.db_manager.execute_query = Mock()
        
        # Repozytorium
        self.repository = TradingSignalRepository(self.db_manager)
    
    def test_find_active_signals(self):
        """Test metody find_active_signals."""
        # Przygotowanie
        mock_result = MagicMock()
        mock_result.keys.return_value = ['id', 'symbol', 'timeframe', 'direction', 'entry_price', 'stop_loss', 'take_profit', 'status']
        mock_result.__getitem__.side_effect = lambda key: {
            'id': 1,
            'symbol': 'EURUSD',
            'timeframe': 'H1',
            'direction': 'buy',
            'entry_price': 1.1000,
            'stop_loss': 1.0950,
            'take_profit': 1.1100,
            'status': 'pending'
        }[key]
        
        self.db_manager.execute_query.return_value = [mock_result]
        
        # Wykonanie
        result = self.repository.find_active_signals()
        
        # Weryfikacja
        self.db_manager.execute_query.assert_called_once()
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].id, 1)
        self.assertEqual(result[0].symbol, 'EURUSD')
        self.assertEqual(result[0].timeframe, 'H1')
        self.assertEqual(result[0].direction, 'buy')
        self.assertEqual(result[0].entry_price, 1.1000)
        self.assertEqual(result[0].stop_loss, 1.0950)
        self.assertEqual(result[0].take_profit, 1.1100)
        self.assertEqual(result[0].status, 'pending')
    
    def test_find_active_signals_not_found(self):
        """Test metody find_active_signals - nie znaleziono."""
        # Przygotowanie
        self.db_manager.execute_query.return_value = []
        
        # Wykonanie
        result = self.repository.find_active_signals()
        
        # Weryfikacja
        self.db_manager.execute_query.assert_called_once()
        self.assertEqual(len(result), 0)


if __name__ == "__main__":
    unittest.main() 