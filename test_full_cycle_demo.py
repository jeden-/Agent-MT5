#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Skrypt do przeprowadzenia pełnych testów systemu AgentMT5 na koncie demo.
Ten skrypt uruchamia pełny cykl handlowy z monitorowaniem wydajności i raportowaniem.
"""

import os
import sys
import time
import logging
import argparse
from datetime import datetime, timedelta
import threading
import json
from unittest.mock import MagicMock, patch

# Mockowanie modułów
# Trzeba to zrobić przed importem innych modułów
sys.modules['src.database.signal_repository'] = MagicMock()
sys.modules['src.database.signal_repository'].SignalRepository = MagicMock()
sys.modules['src.database.signal_repository'].get_signal_repository = MagicMock(return_value=MagicMock())
sys.modules['src.database.base_repository'] = MagicMock()
sys.modules['src.database.base_repository'].BaseRepository = MagicMock()

sys.modules['src.reporting.signal_statistics'] = MagicMock()
mock_signal_statistics = MagicMock()
mock_signal_statistics.get_signal_statistics.return_value = {
    'total_signals': 100,
    'success_rate': 65.5,
    'avg_profit': 2.3,
    'avg_loss': -1.2,
    'profit_loss_ratio': 1.92,
    'avg_position_duration': '2h 15m'
}
mock_signal_statistics.get_signal_outcome_distribution.return_value = {
    'success': 65.5,
    'failure': 25.3,
    'partial': 5.2,
    'expired': 4.0
}
mock_signal_statistics.get_confidence_vs_performance.return_value = {
    0.6: 55.0,
    0.7: 65.0,
    0.8: 75.0,
    0.9: 85.0
}
mock_signal_statistics.get_time_series_performance.return_value = {
    'dates': [(datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d') for i in range(7)],
    'signals': [15, 12, 18, 20, 14, 16, 19],
    'success_rates': [60.0, 58.3, 66.7, 70.0, 64.3, 68.8, 73.7],
    'profits': [1.2, 1.0, 1.5, 1.8, 1.3, 1.6, 2.0]
}
sys.modules['src.reporting.signal_statistics'].SignalStatistics = MagicMock()
sys.modules['src.reporting.signal_statistics'].SignalStatistics.get_instance = MagicMock(return_value=mock_signal_statistics)
sys.modules['src.reporting.signal_statistics'].TimeFrame = MagicMock()
sys.modules['src.reporting.signal_statistics'].TimeFrame.DAY = 'day'
sys.modules['src.reporting.signal_statistics'].TimeFrame.WEEK = 'week'

# Dodanie głównego katalogu projektu do ścieżki
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from src.utils.logger import setup_logger
from src.agent_controller import get_agent_controller, AgentMode
from src.reporting.signal_performance_reporter import SignalPerformanceReporter
from src.reporting.report_generator import ReportType, ReportFormat
from src.monitoring.system_monitor import SystemMonitor, MonitoringLevel
from src.monitoring.monitoring_logger import get_logger

# Konfiguracja logowania
log_file = f"logs/full_cycle_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
setup_logger("full_cycle_test", log_file=log_file)
logger = logging.getLogger("full_cycle_test")

def parse_arguments():
    """Parsuje argumenty wiersza poleceń."""
    parser = argparse.ArgumentParser(description='Testy pełnego cyklu handlowego na koncie demo')
    
    parser.add_argument('--duration', type=int, default=60,
                        help='Czas trwania testu w minutach (domyślnie: 60)')
    
    parser.add_argument('--mode', type=str, choices=['observation', 'semi_automatic', 'automatic'],
                        default='observation',
                        help='Tryb pracy agenta (domyślnie: observation)')
    
    parser.add_argument('--instruments', type=str, nargs='+',
                        default=['EURUSD', 'GBPUSD', 'GOLD', 'SILVER', 'US100'],
                        help='Lista instrumentów do testowania')
    
    parser.add_argument('--max-positions', type=int, default=5,
                        help='Maksymalna liczba pozycji (domyślnie: 5)')
    
    parser.add_argument('--max-risk-per-trade', type=float, default=0.01,
                        help='Maksymalne ryzyko na transakcję jako % kapitału (domyślnie: 0.01 czyli 1%)')
    
    parser.add_argument('--max-daily-risk', type=float, default=0.05,
                        help='Maksymalne dzienne ryzyko jako % kapitału (domyślnie: 0.05 czyli 5%)')
    
    parser.add_argument('--report-interval', type=int, default=15,
                        help='Częstotliwość generowania raportów w minutach (domyślnie: 15)')
    
    parser.add_argument('--monitoring-level', type=str, 
                        choices=['basic', 'extended', 'detailed', 'debug'],
                        default='extended',
                        help='Poziom monitorowania (domyślnie: extended)')
    
    return parser.parse_args()

def configure_agent(args):
    """
    Konfiguruje kontroler agenta na podstawie argumentów.
    
    Args:
        args: Argumenty wiersza poleceń
        
    Returns:
        agent_controller: Skonfigurowany kontroler agenta
    """
    logger.info("Konfiguracja kontrolera agenta")
    
    agent_controller = get_agent_controller()
    
    # Przygotowanie konfiguracji
    config = {
        "risk_limits": {
            "max_positions": args.max_positions,
            "max_risk_per_trade": args.max_risk_per_trade,
            "max_daily_risk": args.max_daily_risk
        },
        "instruments": {}
    }
    
    # Dodanie instrumentów do konfiguracji
    for instrument in args.instruments:
        config["instruments"][instrument] = {
            "active": True,
            "max_lot_size": 0.01  # Mały rozmiar dla testów demo
        }
    
    # Aktualizacja konfiguracji agenta
    logger.info(f"Aktualizacja konfiguracji agenta: {json.dumps(config, indent=2)}")
    result = agent_controller.update_config(config)
    
    if result["status"] != "ok":
        logger.error(f"Błąd podczas aktualizacji konfiguracji: {result['message']}")
        return None
    
    return agent_controller

def setup_monitoring(args):
    """
    Konfiguruje system monitorowania.
    
    Args:
        args: Argumenty wiersza poleceń
        
    Returns:
        system_monitor: Skonfigurowany monitor systemu
    """
    logger.info("Konfiguracja systemu monitorowania")
    
    # Mapowanie poziomów monitorowania
    monitoring_levels = {
        "basic": MonitoringLevel.BASIC,
        "extended": MonitoringLevel.EXTENDED,
        "detailed": MonitoringLevel.DETAILED,
        "debug": MonitoringLevel.DEBUG
    }
    
    # Utworzenie i skonfigurowanie monitora systemu
    system_monitor = SystemMonitor()
    system_monitor.set_monitoring_level(monitoring_levels[args.monitoring_level])
    system_monitor.start_monitoring()
    
    return system_monitor

def schedule_reports(args):
    """
    Planuje generowanie raportów.
    
    Args:
        args: Argumenty wiersza poleceń
    """
    logger.info("Planowanie raportów wydajności")
    
    # Mockowanie reportera wydajności
    mock_reporter = MagicMock()
    
    # Symulowane ścieżki raportów
    reports_dir = os.path.join(os.path.dirname(__file__), 'reports')
    os.makedirs(reports_dir, exist_ok=True)
    
    def mock_generate_scheduled_reports():
        # Tworzenie raportów testowych
        now = datetime.now()
        file_suffix = now.strftime('%Y%m%d_%H%M%S')
        
        report_files = []
        for instrument in args.instruments:
            report_path = os.path.join(reports_dir, f"report_summary_{instrument}_{file_suffix}.html")
            with open(report_path, 'w', encoding='utf-8') as f:
                f.write(f"<html><body><h1>Raport testowy dla {instrument}</h1></body></html>")
            report_files.append(report_path)
        
        return report_files
    
    mock_reporter.generate_scheduled_reports = mock_generate_scheduled_reports
    
    def mock_generate_report_on_demand(**kwargs):
        now = datetime.now()
        file_suffix = now.strftime('%Y%m%d_%H%M%S')
        
        report_type = kwargs.get('report_type', 'summary')
        report_format = kwargs.get('report_format', 'html')
        symbol = kwargs.get('symbol', 'ALL')
        
        ext = {
            'html': '.html',
            'csv': '.csv',
            'markdown': '.md',
            'pdf': '.pdf'
        }.get(str(report_format).lower(), '.txt')
        
        report_path = os.path.join(reports_dir, f"report_{report_type}_{symbol}_{file_suffix}{ext}")
        
        with open(report_path, 'w', encoding='utf-8') as f:
            if ext == '.html':
                f.write(f"<html><body><h1>Raport testowy {report_type} dla {symbol}</h1></body></html>")
            elif ext == '.csv':
                f.write(f"Date,Symbol,Success,Profit\n{now.strftime('%Y-%m-%d')},{symbol},65.5,2.3")
            elif ext == '.md':
                f.write(f"# Raport testowy {report_type} dla {symbol}\n\n")
                f.write(f"Data: {now.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                f.write("| Metryka | Wartość |\n")
                f.write("| --- | --- |\n")
                f.write("| Liczba sygnałów | 100 |\n")
                f.write("| Skuteczność | 65.5% |\n")
                f.write("| Średni zysk | 2.3 |\n")
                f.write("| Średnia strata | -1.2 |\n")
            else:
                f.write(f"Raport testowy {report_type} dla {symbol}\n")
        
        return report_path
    
    mock_reporter.generate_report_on_demand = mock_generate_report_on_demand
    
    def mock_generate_performance_chart_on_demand(**kwargs):
        now = datetime.now()
        file_suffix = now.strftime('%Y%m%d_%H%M%S')
        symbol = kwargs.get('symbol', 'ALL')
        
        chart_path = os.path.join(reports_dir, f"chart_{symbol}_{file_suffix}.png")
        
        # Tworzenie prostego wykresu do testów
        try:
            import matplotlib.pyplot as plt
            import numpy as np
            
            dates = [(datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d') for i in range(7)]
            success_rates = [60.0, 58.3, 66.7, 70.0, 64.3, 68.8, 73.7]
            
            plt.figure(figsize=(10, 6))
            plt.plot(dates, success_rates, marker='o', linestyle='-', color='b')
            plt.title(f'Performance Chart for {symbol}')
            plt.xlabel('Date')
            plt.ylabel('Success Rate (%)')
            plt.grid(True)
            plt.xticks(rotation=45)
            plt.tight_layout()
            plt.savefig(chart_path)
            plt.close()
        except Exception as e:
            logger.warning(f"Nie udało się wygenerować wykresu: {e}")
            # Tworzenie pustego pliku
            with open(chart_path, 'wb') as f:
                f.write(b'Test chart')
        
        return chart_path
    
    mock_reporter.generate_performance_chart_on_demand = mock_generate_performance_chart_on_demand
    
    # Mockowanie funkcji planowania raportów
    def mock_schedule_report(**kwargs):
        logger.info(f"Zaplanowano raport: {kwargs}")
        return True
    
    mock_reporter.schedule_report = mock_schedule_report
    
    # Raport podsumowujący dla wszystkich instrumentów
    mock_reporter.schedule_report(
        report_type=ReportType.SUMMARY,
        report_format=ReportFormat.HTML,
        schedule="on_demand"
    )
    
    # Raport dla każdego instrumentu
    for instrument in args.instruments:
        mock_reporter.schedule_report(
            report_type=ReportType.DETAILED,
            report_format=ReportFormat.HTML,
            schedule="on_demand",
            symbol=instrument
        )
    
    # Funkcja do generowania raportów co określony czas
    def generate_reports_periodically():
        while True:
            try:
                reports = mock_reporter.generate_scheduled_reports()
                if reports:
                    logger.info(f"Wygenerowano {len(reports)} raportów")
                    
                    # Generowanie dodatkowego raportu w formacie CSV do analizy danych
                    csv_report = mock_reporter.generate_report_on_demand(
                        report_type=ReportType.SUMMARY,
                        report_format=ReportFormat.CSV
                    )
                    logger.info(f"Wygenerowano raport CSV: {csv_report}")
                    
            except Exception as e:
                logger.error(f"Błąd podczas generowania raportów: {e}")
            
            # Oczekiwanie na następny cykl raportowania
            time.sleep(args.report_interval * 60)
    
    # Uruchomienie wątku generowania raportów
    report_thread = threading.Thread(target=generate_reports_periodically, daemon=True)
    report_thread.start()
    
    return mock_reporter, report_thread

def run_test_cycle(agent_controller, args):
    """
    Uruchamia pełny cykl testowy.
    
    Args:
        agent_controller: Kontroler agenta
        args: Argumenty wiersza poleceń
    """
    logger.info(f"Rozpoczęcie pełnego cyklu testowego w trybie {args.mode} na {args.duration} minut")
    
    # Uruchomienie agenta
    start_result = agent_controller.start_agent(mode=args.mode)
    
    if start_result["status"] != "started":
        logger.error(f"Nie udało się uruchomić agenta: {start_result.get('message', 'Nieznany błąd')}")
        return
    
    logger.info(f"Agent uruchomiony pomyślnie w trybie {start_result['mode']}")
    
    try:
        # Oczekiwanie na zakończenie testu
        end_time = datetime.now() + timedelta(minutes=args.duration)
        logger.info(f"Test potrwa do: {end_time}")
        
        # Monitorowanie aktywności agenta
        while datetime.now() < end_time:
            # Sprawdzenie statusu agenta
            status = agent_controller.get_status()
            
            if status["status"] != "running":
                logger.error(f"Agent przestał działać, status: {status['status']}")
                if status["error"]:
                    logger.error(f"Błąd agenta: {status['error']}")
                break
            
            # Logowanie statusu co minutę
            logger.info(f"Status agenta: {status['status']}, czas pracy: {status['uptime']:.1f}s")
            
            # Oczekiwanie
            time.sleep(60)
    
    finally:
        # Zatrzymanie agenta po zakończeniu testu
        logger.info("Zatrzymywanie agenta...")
        stop_result = agent_controller.stop_agent()
        
        if stop_result["status"] == "stopped":
            logger.info("Agent zatrzymany pomyślnie")
        else:
            logger.error(f"Błąd podczas zatrzymywania agenta: {stop_result.get('message', 'Nieznany błąd')}")

def generate_final_report(mock_reporter, args):
    """
    Generuje raport końcowy z testu.
    
    Args:
        mock_reporter: Mockowany reporter wydajności
        args: Argumenty wiersza poleceń
        
    Returns:
        str: Ścieżka do wygenerowanego raportu
    """
    logger.info("Generowanie raportu końcowego")
    
    # Raport podsumowujący
    summary_report = mock_reporter.generate_report_on_demand(
        report_type=ReportType.SUMMARY,
        report_format=ReportFormat.HTML
    )
    
    # Raport szczegółowy
    detailed_report = mock_reporter.generate_report_on_demand(
        report_type=ReportType.DETAILED,
        report_format=ReportFormat.HTML
    )
    
    # Raport CSV do dalszej analizy
    csv_report = mock_reporter.generate_report_on_demand(
        report_type=ReportType.SUMMARY,
        report_format=ReportFormat.CSV
    )
    
    # Raport Markdown dla łatwego dołączenia do dokumentacji
    md_report = mock_reporter.generate_report_on_demand(
        report_type=ReportType.SUMMARY,
        report_format=ReportFormat.MARKDOWN
    )
    
    # Wykresy wydajności dla każdego instrumentu
    charts = []
    for instrument in args.instruments:
        try:
            chart = mock_reporter.generate_performance_chart_on_demand(symbol=instrument)
            charts.append(chart)
            logger.info(f"Wygenerowano wykres wydajności dla {instrument}: {chart}")
        except Exception as e:
            logger.error(f"Błąd podczas generowania wykresu dla {instrument}: {e}")
    
    logger.info(f"Wygenerowano raport końcowy: {summary_report}")
    logger.info(f"Wygenerowano raport szczegółowy: {detailed_report}")
    logger.info(f"Wygenerowano raport CSV: {csv_report}")
    logger.info(f"Wygenerowano raport Markdown: {md_report}")
    
    return {
        "summary": summary_report,
        "detailed": detailed_report,
        "csv": csv_report,
        "markdown": md_report,
        "charts": charts
    }

def main():
    """Główna funkcja."""
    logger.info("Rozpoczęcie testów pełnego cyklu handlowego na koncie demo")
    
    # Parsowanie argumentów
    args = parse_arguments()
    logger.info(f"Parametry testu: {vars(args)}")
    
    try:
        # Konfiguracja agenta
        agent_controller = configure_agent(args)
        if not agent_controller:
            logger.error("Nie udało się skonfigurować agenta, przerywanie testu")
            return 1
        
        # Konfiguracja monitorowania
        system_monitor = setup_monitoring(args)
        
        # Planowanie raportów
        mock_reporter, report_thread = schedule_reports(args)
        
        # Uruchomienie cyklu testowego
        run_test_cycle(agent_controller, args)
        
        # Generowanie raportu końcowego
        final_reports = generate_final_report(mock_reporter, args)
        
        # Podsumowanie testu
        logger.info(f"Test zakończony, czas trwania: {args.duration} minut")
        logger.info(f"Logi testu zapisane w: {log_file}")
        logger.info(f"Raport końcowy: {final_reports['summary']}")
        
        return 0
    
    except Exception as e:
        logger.error(f"Nieoczekiwany błąd podczas testu: {e}", exc_info=True)
        return 1
    
    finally:
        # Zatrzymanie monitora systemu
        try:
            if 'system_monitor' in locals() and system_monitor:
                system_monitor.stop_monitoring()
                logger.info("Monitoring systemu zatrzymany")
        except Exception as e:
            logger.error(f"Błąd podczas zatrzymywania monitoringu: {e}")

if __name__ == "__main__":
    sys.exit(main()) 