#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Testy jednostkowe dla modułu monitorowania AI.
"""

import unittest
import os
import sys
import logging
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock, call
import threading

# Konfiguracja logowania
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Importy testowanych modułów
from src.monitoring.ai_monitor import AIMonitor, AIModelUsage, get_ai_monitor, AlertType, AlertPriority


class TestAIMonitor(unittest.TestCase):
    """Testy jednostkowe dla modułu monitorowania AI."""
    
    def setUp(self):
        """Przygotowanie środowiska testowego."""
        # Mockowanie repozytorium i menedżera alertów
        self.mock_repository = Mock()
        self.mock_alert_manager = Mock()
        
        # Patchowanie inicjalizacji AIMonitor
        self.init_patch = patch.object(AIMonitor, '__init__', return_value=None)
        self.mock_init = self.init_patch.start()
        
        # Patchowanie wątku analizy
        self.thread_patch = patch('threading.Thread')
        self.mock_thread = self.thread_patch.start()
        
        # Tworzenie instancji AIMonitor
        self.ai_monitor = AIMonitor()
        
        # Ręczna inicjalizacja pól
        self.ai_monitor._initialized = True
        self.ai_monitor._running = False
        self.ai_monitor.logger = logging.getLogger('test')
        self.ai_monitor.ai_usage_repository = self.mock_repository
        self.ai_monitor.alert_manager = self.mock_alert_manager
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
        
        # Implementacja metody _create_alert
        def _create_alert(message, alert_type, priority):
            self.mock_alert_manager.create_alert(
                message=message,
                alert_type=alert_type,
                priority=priority,
                source="AI Monitor"
            )
        
        self.ai_monitor._create_alert = _create_alert
        
    def tearDown(self):
        """Czyszczenie po testach."""
        self.init_patch.stop()
        self.thread_patch.stop()
        
        # Reset singletona
        AIMonitor._instance = None
    
    def test_singleton_pattern(self):
        """Test wzorca Singleton."""
        # Patchowanie __new__ aby zwracał nową instancję
        with patch.object(AIMonitor, '__new__', return_value=AIMonitor()):
            monitor1 = get_ai_monitor()
            monitor2 = get_ai_monitor()
            
            self.assertIs(monitor1, monitor2)
    
    def test_record_usage(self):
        """Test rejestrowania użycia modelu AI."""
        # Tworzenie przykładowego użycia
        usage = AIModelUsage(
            model_name="claude",
            timestamp=datetime.now(),
            request_type="market_analysis",
            tokens_input=500,
            tokens_output=200,
            duration_ms=1500,
            success=True,
            cost=0.05,
            signal_generated=True,
            decision_quality=0.85
        )
        
        # Patchowanie metod wywoływanych przez record_usage
        with patch.object(self.ai_monitor, '_update_performance_stats') as mock_update:
            with patch.object(self.ai_monitor, '_check_for_anomalies') as mock_check_anomalies:
                with patch.object(self.ai_monitor, '_check_cost_thresholds') as mock_check_costs:
                    # Wywołanie testowanej metody
                    self.ai_monitor.record_usage(usage)
                    
                    # Sprawdzenie, czy użycie zostało dodane do bufora
                    self.assertEqual(len(self.ai_monitor.usage_buffer), 1)
                    self.assertEqual(self.ai_monitor.usage_buffer[0], usage)
                    
                    # Sprawdzenie, czy metody zostały wywołane
                    mock_update.assert_called_once_with(usage)
                    mock_check_anomalies.assert_called_once_with(usage)
                    mock_check_costs.assert_called_once_with(usage.model_name)
    
    def test_flush_buffer(self):
        """Test zapisywania bufora do bazy danych."""
        # Dodanie kilku przykładowych użyć do bufora
        for i in range(3):
            usage = AIModelUsage(
                model_name=f"model{i}",
                timestamp=datetime.now(),
                request_type="test",
                tokens_input=100,
                tokens_output=50,
                duration_ms=1000,
                success=True,
                cost=0.01,
                signal_generated=False
            )
            self.ai_monitor.usage_buffer.append(usage)
        
        # Wywołanie testowanej metody
        self.ai_monitor._flush_buffer()
        
        # Sprawdzenie, czy repozytorium zostało wywołane
        self.assertEqual(self.mock_repository.insert_usage.call_count, 3)
        
        # Sprawdzenie, czy bufor został wyczyszczony
        self.assertEqual(len(self.ai_monitor.usage_buffer), 0)
    
    def test_check_for_anomalies(self):
        """Test wykrywania anomalii w użyciu modelu AI."""
        # Przypadek 1: Błąd modelu
        error_usage = AIModelUsage(
            model_name="model1",
            timestamp=datetime.now(),
            request_type="test",
            tokens_input=100,
            tokens_output=0,
            duration_ms=500,
            success=False,
            error_message="API Error",
            cost=0.0,
            signal_generated=False
        )
        
        self.ai_monitor._check_for_anomalies(error_usage)
        
        # Sprawdzenie, czy alert został utworzony
        self.mock_alert_manager.create_alert.assert_called_with(
            message="Błąd modelu model1: API Error",
            alert_type=AlertType.AI_ERROR,
            priority=AlertPriority.HIGH,
            source="AI Monitor"
        )
        
        # Reset mocka
        self.mock_alert_manager.create_alert.reset_mock()
        
        # Przypadek 2: Długi czas odpowiedzi
        slow_usage = AIModelUsage(
            model_name="model2",
            timestamp=datetime.now(),
            request_type="test",
            tokens_input=100,
            tokens_output=50,
            duration_ms=15000,  # 15 sekund
            success=True,
            cost=0.01,
            signal_generated=False
        )
        
        self.ai_monitor._check_for_anomalies(slow_usage)
        
        # Sprawdzenie, czy alert został utworzony
        self.mock_alert_manager.create_alert.assert_called_with(
            message="Bardzo długi czas odpowiedzi modelu model2: 15000ms",
            alert_type=AlertType.AI_PERFORMANCE,
            priority=AlertPriority.MEDIUM,
            source="AI Monitor"
        )
    
    def test_check_cost_thresholds(self):
        """Test sprawdzania progów kosztów."""
        # Mockowanie metody get_daily_cost
        self.mock_repository.get_daily_cost.return_value = 4.5  # 90% limitu dla Claude (5.0)
        
        # Wywołanie testowanej metody
        self.ai_monitor._check_cost_thresholds("claude")
        
        # Sprawdzenie, czy alert został utworzony
        self.mock_alert_manager.create_alert.assert_called_with(
            message="Zbliżamy się do dziennego limitu kosztów dla modelu claude: $4.50 / $5.00",
            alert_type=AlertType.AI_COST,
            priority=AlertPriority.MEDIUM,
            source="AI Monitor"
        )
        
        # Reset mocka
        self.mock_alert_manager.create_alert.reset_mock()
        
        # Przypadek przekroczenia limitu
        self.mock_repository.get_daily_cost.return_value = 5.5  # 110% limitu
        
        self.ai_monitor._check_cost_thresholds("claude")
        
        # Sprawdzenie, czy alert został utworzony
        self.mock_alert_manager.create_alert.assert_called_with(
            message="Przekroczono dzienny limit kosztów dla modelu claude: $5.50 / $5.00",
            alert_type=AlertType.AI_COST,
            priority=AlertPriority.HIGH,
            source="AI Monitor"
        )
    
    def test_update_performance_stats(self):
        """Test aktualizacji statystyk wydajności."""
        # Pierwszy zapis
        usage1 = AIModelUsage(
            model_name="test_model",
            timestamp=datetime.now(),
            request_type="analysis",
            tokens_input=1000,
            tokens_output=500,
            duration_ms=2000,
            success=True,
            cost=0.1,
            signal_generated=True,
            decision_quality=0.7
        )
        
        self.ai_monitor._update_performance_stats(usage1)
        
        # Sprawdzenie statystyk po pierwszym zapisie
        stats = self.ai_monitor.model_performance["test_model"]
        self.assertEqual(stats["requests_count"], 1)
        self.assertEqual(stats["success_rate"], 1.0)
        self.assertEqual(stats["avg_tokens_input"], 1000)
        self.assertEqual(stats["avg_tokens_output"], 500)
        self.assertEqual(stats["avg_duration_ms"], 2000)
        self.assertAlmostEqual(stats["total_cost"], 0.1, places=2)
        self.assertEqual(stats["signal_rate"], 1.0)
        
        # Inicjalizacja avg_decision_quality
        stats["avg_decision_quality"] = 0.7
        
        # Drugi zapis
        usage2 = AIModelUsage(
            model_name="test_model",
            timestamp=datetime.now(),
            request_type="analysis",
            tokens_input=2000,
            tokens_output=1000,
            duration_ms=3000,
            success=False,
            cost=0.2,
            signal_generated=False,
            decision_quality=None
        )
        
        self.ai_monitor._update_performance_stats(usage2)
        
        # Sprawdzenie statystyk po drugim zapisie
        stats = self.ai_monitor.model_performance["test_model"]
        self.assertEqual(stats["requests_count"], 2)
        self.assertEqual(stats["success_rate"], 0.5)  # (1 + 0) / 2
        self.assertEqual(stats["avg_tokens_input"], 1500)  # (1000 + 2000) / 2
        self.assertEqual(stats["avg_tokens_output"], 750)  # (500 + 1000) / 2
        self.assertEqual(stats["avg_duration_ms"], 2500)  # (2000 + 3000) / 2
        self.assertAlmostEqual(stats["total_cost"], 0.3, places=2)  # 0.1 + 0.2
        self.assertEqual(stats["signal_rate"], 0.5)  # (1 + 0) / 2
        self.assertEqual(stats["avg_decision_quality"], 0.7)  # Nie zmienia się, bo drugi zapis nie ma jakości
    
    def test_get_performance_summary(self):
        """Test pobierania podsumowania wydajności."""
        # Dodanie przykładowych danych wydajności
        self.ai_monitor.model_performance = {
            "model1": {"requests_count": 10, "success_rate": 0.9},
            "model2": {"requests_count": 5, "success_rate": 0.8}
        }
        
        self.ai_monitor.performance_history = [
            {"model": "model1", "timestamp": datetime.now(), "success_rate": 90.0},
            {"model": "model2", "timestamp": datetime.now(), "success_rate": 80.0}
        ]
        
        # Wywołanie testowanej metody
        summary = self.ai_monitor.get_performance_summary()
        
        # Sprawdzenie wyników
        self.assertEqual(len(summary["current_stats"]), 2)
        self.assertEqual(len(summary["history"]), 2)
        self.assertIn("model1", summary["current_stats"])
        self.assertIn("model2", summary["current_stats"])
        self.assertEqual(summary["current_stats"]["model1"]["requests_count"], 10)
        self.assertEqual(summary["current_stats"]["model2"]["success_rate"], 0.8)


if __name__ == '__main__':
    unittest.main() 