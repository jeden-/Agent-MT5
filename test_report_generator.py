#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Skrypt testowy dla modułu raportowania w systemie AgentMT5.
"""

import os
import sys
import logging
import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta

# Dodanie katalogu głównego projektu do ścieżki Pythona
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from src.utils.logger import setup_logger

# Konfiguracja logowania
setup_logger("test_report_generator")
logger = logging.getLogger(__name__)

# Mockowanie repozytoriów
class MockSignalStatistics:
    @classmethod
    def get_instance(cls):
        return cls()
    
    def get_signal_statistics(self, **kwargs):
        return {
            'total_signals': 100,
            'success_rate': 65.5,
            'avg_profit': 2.3,
            'avg_loss': -1.2,
            'profit_loss_ratio': 1.92,
            'avg_position_duration': '2h 15m'
        }
    
    def get_signal_outcome_distribution(self, **kwargs):
        return {
            'success': 65.5,
            'failure': 25.3,
            'partial': 5.2,
            'expired': 4.0
        }
    
    def get_confidence_vs_performance(self, **kwargs):
        return {
            0.6: 55.0,
            0.7: 65.0,
            0.8: 75.0,
            0.9: 85.0
        }
    
    def get_time_series_performance(self, **kwargs):
        dates = [(datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d') for i in range(7)]
        return {
            'dates': dates,
            'signals': [15, 12, 18, 20, 14, 16, 19],
            'success_rates': [60.0, 58.3, 66.7, 70.0, 64.3, 68.8, 73.7],
            'profits': [1.2, 1.0, 1.5, 1.8, 1.3, 1.6, 2.0]
        }

# Mockowanie modułów
sys.modules['src.reporting.signal_statistics'] = MagicMock()
sys.modules['src.reporting.signal_statistics'].SignalStatistics = MockSignalStatistics
sys.modules['src.reporting.signal_statistics'].TimeFrame = MagicMock()
sys.modules['src.reporting.signal_statistics'].TimeFrame.DAY = 'day'
sys.modules['src.reporting.signal_statistics'].TimeFrame.WEEK = 'week'

sys.modules['src.utils.config_manager'] = MagicMock()
sys.modules['src.utils.config_manager'].get_config = MagicMock(return_value={})

sys.modules['src.utils.path_utils'] = MagicMock()
sys.modules['src.utils.path_utils'].get_project_root = MagicMock(return_value=os.path.dirname(__file__))

# Teraz importujemy moduły raportowania
from src.reporting.report_generator import ReportGenerator, ReportType, ReportFormat
from src.reporting.signal_performance_reporter import SignalPerformanceReporter

def test_report_generator():
    """
    Test generowania raportów w różnych formatach.
    """
    logger.info("Rozpoczęcie testu ReportGenerator...")
    
    # Inicjalizacja generatora raportów
    report_generator = ReportGenerator.get_instance()
    
    # Utworzenie katalogów dla raportów i szablonów
    os.makedirs(os.path.join(os.path.dirname(__file__), 'reports'), exist_ok=True)
    os.makedirs(os.path.join(os.path.dirname(__file__), 'templates', 'reports'), exist_ok=True)
    
    # Utworzenie domyślnego szablonu HTML
    default_template_path = os.path.join(os.path.dirname(__file__), 'templates', 'reports', 'default_template.html')
    if not os.path.exists(default_template_path):
        with open(default_template_path, 'w', encoding='utf-8') as f:
            f.write('<html><body><h1>Raport {{ report_type }}</h1></body></html>')
    
    # Test generowania raportu HTML
    logger.info("Generowanie raportu HTML...")
    html_path = report_generator.generate_report(
        report_type=ReportType.SUMMARY,
        report_format=ReportFormat.HTML,
        symbol="EURUSD"
    )
    logger.info(f"Wygenerowano raport HTML: {html_path}")
    
    # Test generowania raportu Markdown
    logger.info("Generowanie raportu Markdown...")
    md_path = report_generator.generate_report(
        report_type=ReportType.SUMMARY,
        report_format=ReportFormat.MARKDOWN,
        symbol="EURUSD"
    )
    logger.info(f"Wygenerowano raport Markdown: {md_path}")
    
    # Test generowania raportu CSV
    logger.info("Generowanie raportu CSV...")
    csv_path = report_generator.generate_report(
        report_type=ReportType.SUMMARY,
        report_format=ReportFormat.CSV,
        symbol="EURUSD"
    )
    logger.info(f"Wygenerowano raport CSV: {csv_path}")
    
    logger.info("Test ReportGenerator zakończony pomyślnie!")

def test_performance_reporter():
    """
    Test reportera wydajności sygnałów.
    """
    logger.info("Rozpoczęcie testu SignalPerformanceReporter...")
    
    # Inicjalizacja reportera wydajności
    performance_reporter = SignalPerformanceReporter()
    
    # Test planowania raportu
    logger.info("Planowanie raportu tygodniowego...")
    scheduled = performance_reporter.schedule_report(
        report_type=ReportType.WEEKLY,
        report_format=ReportFormat.HTML,
        symbol="EURUSD"
    )
    logger.info(f"Zaplanowano raport: {scheduled}")
    
    # Test generowania raportu na żądanie
    logger.info("Generowanie raportu na żądanie...")
    now = datetime.now()
    report_path = performance_reporter.generate_report_on_demand(
        report_type=ReportType.DETAILED,
        report_format=ReportFormat.HTML,
        symbol="EURUSD",
        start_date=now - timedelta(days=7),
        end_date=now
    )
    logger.info(f"Wygenerowano raport na żądanie: {report_path}")
    
    logger.info("Test SignalPerformanceReporter zakończony pomyślnie!")

def main():
    """
    Główna funkcja testowa.
    """
    logger.info("Rozpoczęcie testów modułu raportowania...")
    
    test_report_generator()
    test_performance_reporter()
    
    logger.info("Wszystkie testy modułu raportowania zakończone pomyślnie!")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.error(f"Wystąpił błąd podczas testów: {e}", exc_info=True)
        sys.exit(1)
    
    sys.exit(0) 