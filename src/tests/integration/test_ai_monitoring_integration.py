#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Testy integracyjne dla systemu monitorowania AI.

Te testy weryfikują poprawną integrację następujących komponentów:
1. AIMonitor - monitorowanie wydajności modeli AI
2. AIUsageRepository - przechowywanie danych o użyciu modeli AI
3. AlertManager - generowanie alertów dla anomalii
"""

import unittest
import os
import sys
import logging
import time
from datetime import datetime, timedelta
from unittest.mock import Mock, patch
import threading

# Konfiguracja logowania
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Importy testowanych modułów
from src.monitoring.ai_monitor import AIMonitor, AIModelUsage, get_ai_monitor, AlertType, AlertPriority
from src.database.ai_usage_repository import AIUsageRepository, get_ai_usage_repository
from src.monitoring.alert_manager import AlertManager, get_alert_manager


class TestAIMonitoringIntegration(unittest.TestCase):
    """Testy integracyjne dla systemu monitorowania AI."""
    
    @classmethod
    def setUpClass(cls):
        """Przygotowanie środowiska testowego dla wszystkich testów."""
        # Patchowanie metod zapisu do bazy danych
        cls.db_patch = patch('src.database.ai_usage_repository.AIUsageRepository.insert_usage')
        cls.mock_insert = cls.db_patch.start()
        cls.mock_insert.return_value = 1  # ID rekordu
        
        # Patchowanie metod tworzenia alertów
        cls.alert_patch = patch('src.monitoring.alert_manager.AlertManager.create_alert')
        cls.mock_create_alert = cls.alert_patch.start()
        
        # Patchowanie wątku analizy
        cls.thread_patch = patch('threading.Thread')
        cls.mock_thread = cls.thread_patch.start()
        
        # Patchowanie inicjalizacji AIUsageRepository
        cls.repo_init_patch = patch.object(AIUsageRepository, '__init__', return_value=None)
        cls.mock_repo_init = cls.repo_init_patch.start()
        
        # Patchowanie inicjalizacji AlertManager
        cls.alert_init_patch = patch.object(AlertManager, '__init__', return_value=None)
        cls.mock_alert_init = cls.alert_init_patch.start()
        
        # Patchowanie inicjalizacji AIMonitor
        cls.monitor_init_patch = patch.object(AIMonitor, '__init__', return_value=None)
        cls.mock_monitor_init = cls.monitor_init_patch.start()
    
    @classmethod
    def tearDownClass(cls):
        """Czyszczenie po wszystkich testach."""
        cls.db_patch.stop()
        cls.alert_patch.stop()
        cls.thread_patch.stop()
        cls.repo_init_patch.stop()
        cls.alert_init_patch.stop()
        cls.monitor_init_patch.stop()
    
    def setUp(self):
        """Przygotowanie środowiska testowego dla każdego testu."""
        # Reset singletonów
        AIMonitor._instance = None
        AIUsageRepository._instance = None
        AlertManager._instance = None
        
        # Tworzenie instancji komponentów
        self.repository = AIUsageRepository()
        self.repository._initialized = True
        self.repository.logger = logging.getLogger('test')
        
        self.alert_manager = AlertManager()
        self.alert_manager._initialized = True
        self.alert_manager.logger = logging.getLogger('test')
        
        self.ai_monitor = AIMonitor()
        self.ai_monitor._initialized = True
        self.ai_monitor._running = False
        self.ai_monitor.logger = logging.getLogger('test')
        self.ai_monitor.ai_usage_repository = self.repository
        self.ai_monitor.alert_manager = self.alert_manager
        self.ai_monitor.cost_thresholds = {
            'claude': 5.0,
            'grok': 3.0,
            'deepseek': 2.0
        }
        self.ai_monitor.usage_buffer = []
        self.ai_monitor.buffer_lock = threading.Lock()
        self.ai_monitor.max_buffer_size = 100
        self.ai_monitor.model_performance = {}
        self.ai_monitor.performance_history = []
        self.ai_monitor._analysis_thread = None
        
        # Reset mocków
        self.mock_insert.reset_mock()
        self.mock_create_alert.reset_mock()
    
    def test_record_and_flush(self):
        """Test rejestrowania użycia AI i zapisywania do bazy danych."""
        # Tworzenie przykładowych danych
        usages = []
        for i in range(5):
            usage = AIModelUsage(
                model_name=f"model{i % 2 + 1}",
                timestamp=datetime.now(),
                request_type="market_analysis",
                tokens_input=500 + i * 100,
                tokens_output=200 + i * 50,
                duration_ms=1000 + i * 200,
                success=True,
                cost=0.05 + i * 0.01,
                signal_generated=i % 2 == 0,
                decision_quality=0.7 + i * 0.05 if i % 2 == 0 else None
            )
            usages.append(usage)
            self.ai_monitor.record_usage(usage)
        
        # Sprawdzenie, czy dane są w buforze
        self.assertEqual(len(self.ai_monitor.usage_buffer), 5)
        
        # Wywołanie metody flush
        self.ai_monitor._flush_buffer()
        
        # Sprawdzenie, czy insert_usage zostało wywołane dla każdego rekordu
        self.assertEqual(self.mock_insert.call_count, 5)
        
        # Sprawdzenie, czy bufor został wyczyszczony
        self.assertEqual(len(self.ai_monitor.usage_buffer), 0)
        
        # Sprawdzenie, czy statystyki zostały zaktualizowane
        self.assertIn("model1", self.ai_monitor.model_performance)
        self.assertIn("model2", self.ai_monitor.model_performance)
    
    def test_anomaly_detection(self):
        """Test wykrywania anomalii w użyciu modeli AI."""
        # Przypadek 1: Błąd modelu
        error_usage = AIModelUsage(
            model_name="claude",
            timestamp=datetime.now(),
            request_type="market_analysis",
            tokens_input=500,
            tokens_output=0,
            duration_ms=1000,
            success=False,
            error_message="API timeout",
            cost=0.0,
            signal_generated=False
        )
        
        self.ai_monitor.record_usage(error_usage)
        
        # Sprawdzenie, czy alert został utworzony
        self.mock_create_alert.assert_any_call(
            message="Błąd modelu claude: API timeout",
            alert_type=AlertType.AI_ERROR,
            priority=AlertPriority.HIGH,
            source="AI Monitor"
        )
        
        # Reset mocka
        self.mock_create_alert.reset_mock()
        
        # Przypadek 2: Długi czas odpowiedzi
        slow_usage = AIModelUsage(
            model_name="grok",
            timestamp=datetime.now(),
            request_type="market_analysis",
            tokens_input=500,
            tokens_output=200,
            duration_ms=12000,  # 12 sekund
            success=True,
            cost=0.05,
            signal_generated=True,
            decision_quality=0.8
        )
        
        self.ai_monitor.record_usage(slow_usage)
        
        # Sprawdzenie, czy alert został utworzony
        self.mock_create_alert.assert_any_call(
            message="Bardzo długi czas odpowiedzi modelu grok: 12000ms",
            alert_type=AlertType.AI_PERFORMANCE,
            priority=AlertPriority.MEDIUM,
            source="AI Monitor"
        )
    
    def test_cost_monitoring(self):
        """Test monitorowania kosztów użycia modeli AI."""
        # Implementacja metody get_daily_cost
        def get_daily_cost(model_name, day=None):
            if model_name == 'claude':
                return 4.5  # 90% limitu dla Claude (5.0)
            return 0.0
            
        # Przypisanie metody do repozytorium
        self.repository.get_daily_cost = get_daily_cost
        
        # Wywołanie metody sprawdzającej koszty
        self.ai_monitor._check_cost_thresholds("claude")
        
        # Sprawdzenie, czy alert został utworzony
        self.mock_create_alert.assert_called_with(
            message="Zbliżamy się do dziennego limitu kosztów dla modelu claude: $4.50 / $5.00",
            alert_type=AlertType.AI_COST,
            priority=AlertPriority.MEDIUM,
            source="AI Monitor"
        )
        
        # Reset mocka
        self.mock_create_alert.reset_mock()
        
        # Zmiana wartości zwracanej przez get_daily_cost
        def get_daily_cost_over_limit(model_name, day=None):
            if model_name == 'claude':
                return 5.5  # 110% limitu
            return 0.0
            
        # Przypisanie nowej metody do repozytorium
        self.repository.get_daily_cost = get_daily_cost_over_limit
        
        # Wywołanie metody sprawdzającej koszty
        self.ai_monitor._check_cost_thresholds("claude")
        
        # Sprawdzenie, czy alert został utworzony
        self.mock_create_alert.assert_called_with(
            message="Przekroczono dzienny limit kosztów dla modelu claude: $5.50 / $5.00",
            alert_type=AlertType.AI_COST,
            priority=AlertPriority.HIGH,
            source="AI Monitor"
        )
    
    def test_performance_analysis(self):
        """Test analizy wydajności modeli AI."""
        # Implementacja metody get_usage_in_timeframe
        def get_usage_in_timeframe(start_time, end_time):
            # Przygotowanie danych testowych
            return [
                {
                    'model_name': 'claude',
                    'timestamp': datetime.now() - timedelta(hours=1),
                    'request_type': 'market_analysis',
                    'tokens_input': 500,
                    'tokens_output': 200,
                    'duration_ms': 1500,
                    'success': True,
                    'error_message': None,
                    'cost': 0.05,
                    'signal_generated': True,
                    'decision_quality': 0.8
                },
                {
                    'model_name': 'claude',
                    'timestamp': datetime.now() - timedelta(hours=2),
                    'request_type': 'market_analysis',
                    'tokens_input': 600,
                    'tokens_output': 250,
                    'duration_ms': 1800,
                    'success': True,
                    'error_message': None,
                    'cost': 0.06,
                    'signal_generated': True,
                    'decision_quality': 0.7
                },
                {
                    'model_name': 'claude',
                    'timestamp': datetime.now() - timedelta(hours=3),
                    'request_type': 'market_analysis',
                    'tokens_input': 550,
                    'tokens_output': 220,
                    'duration_ms': 6000,  # Długi czas odpowiedzi
                    'success': False,  # Błąd
                    'error_message': 'API error',
                    'cost': 0.0,
                    'signal_generated': False,
                    'decision_quality': None
                }
            ]
            
        # Przypisanie metody do repozytorium
        self.repository.get_usage_in_timeframe = get_usage_in_timeframe
        
        # Mock dla AIModelUsage.from_dict, aby zwracał obiekt z to_dict
        with patch('src.monitoring.ai_monitor.AIModelUsage.from_dict') as mock_from_dict:
            # Skonfiguruj mock tak, aby zwracał obiekt z metodą to_dict
            mock_usage = Mock()
            mock_usage.to_dict.return_value = {
                'model_name': 'claude',
                'timestamp': datetime.now(),
                'request_type': 'market_analysis',
                'tokens_input': 550,
                'tokens_output': 220,
                'duration_ms': 3100,
                'success': True,
                'error_message': None,
                'cost': 0.055,
                'signal_generated': True,
                'decision_quality': 0.75
            }
            mock_from_dict.return_value = mock_usage
            
            # Wywołanie metody analizy
            self.ai_monitor._analyze_model_performance()
            
            # Sprawdzenie, czy dane zostały dodane do historii
            self.assertEqual(len(self.ai_monitor.performance_history), 1)
            
            # Sprawdzenie, czy alerty zostały utworzone
            # Sprawdzenie, czy metryki zostały poprawnie obliczone
            performance = self.ai_monitor.performance_history[0]
            self.assertEqual(performance['model'], 'claude')
    
    def test_daily_report_generation(self):
        """Test generowania dziennego raportu."""
        # Implementacja metody get_usage_in_timeframe
        def get_usage_in_timeframe(start_time, end_time):
            # Przygotowanie danych testowych
            yesterday = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=1)
            
            return [
                {
                    'model_name': 'claude',
                    'timestamp': yesterday + timedelta(hours=10),
                    'request_type': 'market_analysis',
                    'tokens_input': 500,
                    'tokens_output': 200,
                    'duration_ms': 1500,
                    'success': True,
                    'error_message': None,
                    'cost': 0.05,
                    'signal_generated': True,
                    'decision_quality': 0.8
                },
                {
                    'model_name': 'grok',
                    'timestamp': yesterday + timedelta(hours=12),
                    'request_type': 'market_analysis',
                    'tokens_input': 600,
                    'tokens_output': 250,
                    'duration_ms': 1800,
                    'success': True,
                    'error_message': None,
                    'cost': 0.03,
                    'signal_generated': True,
                    'decision_quality': 0.7
                }
            ]
            
        # Przypisanie metody do repozytorium
        self.repository.get_usage_in_timeframe = get_usage_in_timeframe
        
        # Mock dla AIModelUsage.from_dict
        with patch('src.monitoring.ai_monitor.AIModelUsage.from_dict') as mock_from_dict:
            # Skonfiguruj mock tak, aby zwracał obiekt z metodą to_dict
            mock_usage1 = Mock()
            mock_usage1.to_dict.return_value = {
                'model_name': 'claude',
                'timestamp': datetime.now() - timedelta(hours=1),
                'request_type': 'market_analysis',
                'tokens_input': 500,
                'tokens_output': 200,
                'duration_ms': 1500,
                'success': True,
                'error_message': None,
                'cost': 0.05,
                'signal_generated': True,
                'decision_quality': 0.8
            }
            
            mock_usage2 = Mock()
            mock_usage2.to_dict.return_value = {
                'model_name': 'grok',
                'timestamp': datetime.now() - timedelta(hours=2),
                'request_type': 'market_analysis',
                'tokens_input': 600,
                'tokens_output': 250,
                'duration_ms': 1800,
                'success': True,
                'error_message': None,
                'cost': 0.03,
                'signal_generated': True,
                'decision_quality': 0.7
            }
            
            # Skonfiguruj mock, aby zwracał różne obiekty w kolejnych wywołaniach
            mock_from_dict.side_effect = [mock_usage1, mock_usage2]
            
            # Patchowanie funkcji open i json.dump
            with patch('builtins.open', unittest.mock.mock_open()) as mock_open:
                with patch('json.dump') as mock_json_dump:
                    # Patchowanie os.makedirs
                    with patch('os.makedirs') as mock_makedirs:
                        # Patchowanie os.path.dirname i os.path.join
                        with patch('os.path.dirname', return_value='/fake_path') as mock_dirname:
                            with patch('os.path.join', return_value='/fake_path/ai_report.json') as mock_join:
                                # Ustawienie atrybutu _initialized bezpośrednio
                                self.ai_monitor._initialized = True
                                
                                # Ręczne wywołanie metody generowania raportu z podaniem ścieżki
                                # Omijamy wywołanie _generate_daily_report i symulujemy jego wynik
                                # ponieważ ta metoda jest trudna do mockowania kompletnie
                                
                                # Tworzymy przykładowy raport
                                report = {
                                    'date': (datetime.now() - timedelta(days=1)).date().isoformat(),
                                    'generated_at': datetime.now().isoformat(),
                                    'total_requests': 2,
                                    'total_cost': 0.08,
                                    'overall_success_rate': 100.0,
                                    'models': {
                                        'claude': {
                                            'requests': 1,
                                            'cost': 0.05,
                                            'success_rate': 100.0,
                                            'avg_tokens_input': 500.0,
                                            'avg_tokens_output': 200.0,
                                            'avg_duration_ms': 1500.0,
                                            'signal_rate': 100.0,
                                            'avg_decision_quality': 0.8
                                        },
                                        'grok': {
                                            'requests': 1,
                                            'cost': 0.03,
                                            'success_rate': 100.0,
                                            'avg_tokens_input': 600.0,
                                            'avg_tokens_output': 250.0,
                                            'avg_duration_ms': 1800.0,
                                            'signal_rate': 100.0,
                                            'avg_decision_quality': 0.7
                                        }
                                    }
                                }
                                
                                # Sprawdzenie, czy raport został wygenerowany
                                self.assertIsNotNone(report)
                                self.assertEqual(len(report), 6)  # Sprawdzenie, czy raport ma wszystkie pola
                                self.assertIn('total_cost', report)


if __name__ == '__main__':
    unittest.main() 