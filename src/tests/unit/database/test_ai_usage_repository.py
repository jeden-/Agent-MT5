#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Testy jednostkowe dla repozytorium danych o użyciu AI.
"""

import unittest
import os
import sys
import logging
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock

# Konfiguracja logowania
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Importy testowanych modułów
from src.database.ai_usage_repository import AIUsageRepository, get_ai_usage_repository


class TestAIUsageRepository(unittest.TestCase):
    """Testy jednostkowe dla repozytorium danych o użyciu AI."""
    
    def setUp(self):
        """Przygotowanie środowiska testowego."""
        # Mockowanie menedżera bazy danych
        self.mock_db_manager = Mock()
        
        # Patchowanie inicjalizacji AIUsageRepository
        self.init_patch = patch.object(AIUsageRepository, '__init__', return_value=None)
        self.mock_init = self.init_patch.start()
        
        # Tworzenie instancji AIUsageRepository
        self.repository = AIUsageRepository()
        
        # Ręczna inicjalizacja pól
        self.repository._initialized = True
        self.repository.logger = logging.getLogger('test')
        self.repository.db_manager = self.mock_db_manager
        
    def tearDown(self):
        """Czyszczenie po testach."""
        self.init_patch.stop()
        
        # Reset singletona
        AIUsageRepository._instance = None
    
    def test_singleton_pattern(self):
        """Test wzorca Singleton."""
        repo1 = get_ai_usage_repository()
        repo2 = get_ai_usage_repository()
        
        self.assertIs(repo1, repo2)
    
    def test_create_tables(self):
        """Test tworzenia tabel."""
        # Wywołanie testowanej metody
        self.repository._create_tables()
        
        # Sprawdzenie, czy execute_query zostało wywołane
        self.mock_db_manager.execute_query.assert_called_once()
        
        # Sprawdzenie, czy zapytanie zawiera CREATE TABLE
        query = self.mock_db_manager.execute_query.call_args[0][0]
        self.assertIn("CREATE TABLE IF NOT EXISTS ai_usage", query)
        self.assertIn("CREATE INDEX IF NOT EXISTS", query)
    
    def test_insert_usage(self):
        """Test zapisywania danych o użyciu AI."""
        # Mockowanie wyniku zapytania
        self.mock_db_manager.execute_query.return_value = [(123,)]
        
        # Dane testowe
        usage_data = {
            'model_name': 'test_model',
            'timestamp': datetime.now(),
            'request_type': 'test',
            'tokens_input': 100,
            'tokens_output': 50,
            'duration_ms': 1000,
            'success': True,
            'error_message': None,
            'cost': 0.01,
            'signal_generated': False,
            'decision_quality': None
        }
        
        # Wywołanie testowanej metody
        record_id = self.repository.insert_usage(usage_data)
        
        # Sprawdzenie wyniku
        self.assertEqual(record_id, 123)
        
        # Sprawdzenie, czy execute_query zostało wywołane z odpowiednimi parametrami
        self.mock_db_manager.execute_query.assert_called_once()
        query, params = self.mock_db_manager.execute_query.call_args[0]
        self.assertIn("INSERT INTO ai_usage", query)
        self.assertEqual(params['model_name'], 'test_model')
        self.assertEqual(params['tokens_input'], 100)
    
    def test_insert_usage_with_iso_timestamp(self):
        """Test zapisywania danych z timestamp w formacie ISO."""
        # Mockowanie wyniku zapytania
        self.mock_db_manager.execute_query.return_value = [(123,)]
        
        # Dane testowe z timestamp jako string
        usage_data = {
            'model_name': 'test_model',
            'timestamp': datetime.now().isoformat(),
            'request_type': 'test',
            'tokens_input': 100,
            'tokens_output': 50,
            'duration_ms': 1000,
            'success': True,
            'error_message': None,
            'cost': 0.01,
            'signal_generated': False,
            'decision_quality': None
        }
        
        # Wywołanie testowanej metody
        record_id = self.repository.insert_usage(usage_data)
        
        # Sprawdzenie wyniku
        self.assertEqual(record_id, 123)
        
        # Sprawdzenie, czy timestamp został przekonwertowany na datetime
        query, params = self.mock_db_manager.execute_query.call_args[0]
        self.assertIsInstance(params['timestamp'], datetime)
    
    def test_get_usage_in_timeframe(self):
        """Test pobierania danych o użyciu w przedziale czasowym."""
        # Mockowanie wyniku zapytania
        mock_result = [
            (1, 'model1', datetime.now(), 'test', 100, 50, 1000, True, None, 0.01, False, None),
            (2, 'model2', datetime.now(), 'test', 200, 100, 2000, True, None, 0.02, True, 0.8)
        ]
        self.mock_db_manager.execute_query.return_value = mock_result
        
        # Parametry zapytania
        start_time = datetime.now() - timedelta(days=1)
        end_time = datetime.now()
        
        # Wywołanie testowanej metody
        results = self.repository.get_usage_in_timeframe(start_time, end_time)
        
        # Sprawdzenie wyniku
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]['id'], 1)
        self.assertEqual(results[0]['model_name'], 'model1')
        self.assertEqual(results[1]['id'], 2)
        self.assertEqual(results[1]['model_name'], 'model2')
        self.assertEqual(results[1]['decision_quality'], 0.8)
        
        # Sprawdzenie, czy execute_query zostało wywołane z odpowiednimi parametrami
        self.mock_db_manager.execute_query.assert_called_once()
        query, params = self.mock_db_manager.execute_query.call_args[0]
        self.assertIn("SELECT * FROM ai_usage", query)
        self.assertEqual(params[0], start_time)
        self.assertEqual(params[1], end_time)
    
    def test_get_daily_cost(self):
        """Test pobierania dziennego kosztu."""
        # Mockowanie wyniku zapytania
        self.mock_db_manager.execute_query.return_value = [(0.5,)]
        
        # Parametry zapytania
        model_name = 'test_model'
        day = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Wywołanie testowanej metody
        cost = self.repository.get_daily_cost(model_name, day)
        
        # Sprawdzenie wyniku
        self.assertEqual(cost, 0.5)
        
        # Sprawdzenie, czy execute_query zostało wywołane z odpowiednimi parametrami
        self.mock_db_manager.execute_query.assert_called_once()
        query, params = self.mock_db_manager.execute_query.call_args[0]
        self.assertIn("SELECT SUM(cost) FROM ai_usage", query)
        self.assertEqual(params[0], model_name)
        self.assertEqual(params[1], day)
        self.assertEqual(params[2], day + timedelta(days=1))
    
    def test_get_model_performance(self):
        """Test pobierania statystyk wydajności modelu."""
        # Mockowanie wyniku zapytania
        mock_result = [(
            100,  # total_requests
            95.0,  # success_rate
            500.0,  # avg_tokens_input
            200.0,  # avg_tokens_output
            1500.0,  # avg_duration_ms
            5.0,  # total_cost
            60.0,  # signal_rate
            0.75  # avg_decision_quality
        )]
        self.mock_db_manager.execute_query.return_value = mock_result
        
        # Parametry zapytania
        model_name = 'test_model'
        days = 7
        
        # Wywołanie testowanej metody
        stats = self.repository.get_model_performance(model_name, days)
        
        # Sprawdzenie wyniku
        self.assertEqual(stats['total_requests'], 100)
        self.assertEqual(stats['success_rate'], 95.0)
        self.assertEqual(stats['avg_tokens_input'], 500.0)
        self.assertEqual(stats['avg_tokens_output'], 200.0)
        self.assertEqual(stats['avg_duration_ms'], 1500.0)
        self.assertEqual(stats['total_cost'], 5.0)
        self.assertEqual(stats['signal_rate'], 60.0)
        self.assertEqual(stats['avg_decision_quality'], 0.75)
        self.assertEqual(stats['days'], 7)
        
        # Sprawdzenie, czy execute_query zostało wywołane z odpowiednimi parametrami
        self.mock_db_manager.execute_query.assert_called_once()
        query, params = self.mock_db_manager.execute_query.call_args[0]
        self.assertIn("SELECT", query)
        self.assertEqual(params[0], model_name)
    
    def test_get_daily_usage_stats(self):
        """Test pobierania dziennych statystyk użycia."""
        # Mockowanie wyniku zapytania
        today = datetime.now().date()
        yesterday = (datetime.now() - timedelta(days=1)).date()
        
        mock_result = [
            (today, 'model1', 50, 2.5, 98.0),
            (today, 'model2', 30, 1.5, 95.0),
            (yesterday, 'model1', 40, 2.0, 97.0)
        ]
        self.mock_db_manager.execute_query.return_value = mock_result
        
        # Parametry zapytania
        days = 30
        
        # Wywołanie testowanej metody
        stats = self.repository.get_daily_usage_stats(days)
        
        # Sprawdzenie wyniku
        self.assertEqual(len(stats), 3)
        self.assertEqual(stats[0]['day'], today)
        self.assertEqual(stats[0]['model_name'], 'model1')
        self.assertEqual(stats[0]['requests'], 50)
        self.assertEqual(stats[0]['daily_cost'], 2.5)
        self.assertEqual(stats[0]['success_rate'], 98.0)
        
        self.assertEqual(stats[2]['day'], yesterday)
        self.assertEqual(stats[2]['model_name'], 'model1')
        
        # Sprawdzenie, czy execute_query zostało wywołane z odpowiednimi parametrami
        self.mock_db_manager.execute_query.assert_called_once()
        query, params = self.mock_db_manager.execute_query.call_args[0]
        self.assertIn("SELECT", query)
        self.assertIn("GROUP BY DATE(timestamp), model_name", query)


if __name__ == '__main__':
    unittest.main() 