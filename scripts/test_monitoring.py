#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Test Monitoring - skrypt do testowania funkcjonalności monitorowania AgentMT5.
Generuje przykładowe logi, alerty i sprawdza status systemu.
"""

import sys
import os
import time
import json
import argparse
import random
from datetime import datetime, timedelta

# Dodanie ścieżki nadrzędnej, aby zaimportować moduły
sys.path.append(os.path.abspath(os.path.dirname(os.path.dirname(__file__))))

from src.monitoring.monitoring_logger import get_logger, OperationType, OperationStatus, LogLevel
from src.monitoring.connection_tracker import get_connection_tracker, ConnectionStatus
from src.monitoring.alert_manager import get_alert_manager, AlertLevel, AlertCategory, initialize_default_rules
from src.monitoring.status_reporter import get_status_reporter

def generate_sample_logs(count=10):
    """Generuje przykładowe logi."""
    print(f"Generowanie {count} przykładowych logów...")
    
    logger = get_logger()
    
    # Przykładowe EA IDs
    ea_ids = [f"EA_TEST_{i}" for i in range(1, 5)]
    
    # Przykładowe operacje
    operations = [
        OperationType.INIT,
        OperationType.OPEN_POSITION,
        OperationType.CLOSE_POSITION,
        OperationType.MODIFY_POSITION,
        OperationType.MARKET_DATA,
        OperationType.ACCOUNT_INFO,
        OperationType.CONNECTION,
        OperationType.SYSTEM
    ]
    
    # Przykładowe statusy
    statuses = [
        OperationStatus.SUCCESS,
        OperationStatus.FAILED,
        OperationStatus.PENDING,
        OperationStatus.REJECTED,
        OperationStatus.UNKNOWN
    ]
    
    # Przykładowe poziomy logowania
    levels = [
        LogLevel.DEBUG,
        LogLevel.INFO,
        LogLevel.WARNING,
        LogLevel.ERROR,
        LogLevel.CRITICAL
    ]
    
    for i in range(count):
        # Losowe dane
        ea_id = random.choice(ea_ids)
        operation = random.choice(operations)
        status = random.choice(statuses)
        level = random.choice(levels)
        
        # Przykładowe szczegóły
        details = {
            "timestamp": datetime.now().isoformat(),
            "sample_id": i,
            "random_value": random.random()
        }
        
        # Dodanie dodatkowych szczegółów w zależności od operacji
        if operation == OperationType.OPEN_POSITION:
            details["symbol"] = random.choice(["EURUSD", "GBPUSD", "USDJPY", "GOLD", "SILVER"])
            details["type"] = random.choice(["BUY", "SELL"])
            details["volume"] = round(random.uniform(0.01, 10.0), 2)
            details["price"] = round(random.uniform(1.0, 2000.0), 5)
            message = f"Open position {details['symbol']} {details['type']} {details['volume']} at {details['price']}"
        elif operation == OperationType.CLOSE_POSITION:
            details["ticket"] = random.randint(1000000, 9999999)
            details["profit"] = round(random.uniform(-1000.0, 1000.0), 2)
            message = f"Close position #{details['ticket']} with profit {details['profit']}"
        elif operation == OperationType.MODIFY_POSITION:
            details["ticket"] = random.randint(1000000, 9999999)
            details["sl"] = round(random.uniform(1.0, 2000.0), 5)
            details["tp"] = round(random.uniform(1.0, 2000.0), 5)
            message = f"Modify position #{details['ticket']} SL={details['sl']} TP={details['tp']}"
        else:
            message = f"Sample log message #{i}"
        
        # Logowanie
        logger.log(level, ea_id, operation, status, details, message)
        
        # Krótkie oczekiwanie
        time.sleep(0.1)
    
    print(f"Wygenerowano {count} logów.")

def generate_sample_connections(count=5):
    """Generuje przykładowe połączenia."""
    print(f"Generowanie {count} przykładowych połączeń...")
    
    connection_tracker = get_connection_tracker()
    
    # Przykładowe EA IDs
    ea_ids = [f"EA_TEST_{i}" for i in range(1, count + 1)]
    
    for ea_id in ea_ids:
        # Rejestracja połączenia
        connection_tracker.register_connection(ea_id)
        
        # Symulacja aktywności
        for _ in range(random.randint(1, 10)):
            connection_tracker.update_activity(ea_id, is_command=random.choice([True, False]))
    
    # Symulacja rozłączenia dla niektórych EA
    for ea_id in ea_ids[:2]:
        if random.choice([True, False]):
            connection_tracker.disconnect(ea_id)
    
    print(f"Wygenerowano {count} połączeń.")

def generate_sample_alerts(count=5):
    """Generuje przykładowe alerty."""
    print(f"Generowanie {count} przykładowych alertów...")
    
    alert_manager = get_alert_manager()
    
    # Przykładowe EA IDs
    ea_ids = [f"EA_TEST_{i}" for i in range(1, 5)]
    
    # Przykładowe kategorie
    categories = [
        AlertCategory.CONNECTION,
        AlertCategory.SYSTEM,
        AlertCategory.TRADING,
        AlertCategory.PERFORMANCE,
        AlertCategory.SECURITY
    ]
    
    # Przykładowe poziomy
    levels = [
        AlertLevel.INFO,
        AlertLevel.WARNING,
        AlertLevel.ERROR,
        AlertLevel.CRITICAL
    ]
    
    # Przykładowe źródła
    sources = ["test", "monitor", "system", "user"]
    
    for i in range(count):
        # Losowe dane
        ea_id = random.choice(ea_ids)
        category = random.choice(categories)
        level = random.choice(levels)
        source = random.choice(sources)
        message = f"Sample alert #{i} from {source} for {ea_id}"
        
        # Przykładowe szczegóły
        details = {
            "timestamp": datetime.now().isoformat(),
            "sample_id": i,
            "source": source,
            "category": category.name,
            "level": level.name
        }
        
        # Dodanie dodatkowych szczegółów w zależności od kategorii
        if category == AlertCategory.CONNECTION:
            details["status"] = random.choice(["active", "inactive", "disconnected"])
            details["inactive_since"] = str(timedelta(seconds=random.randint(60, 3600)))
        elif category == AlertCategory.TRADING:
            details["operation"] = random.choice(["open", "close", "modify"])
            details["error_code"] = random.randint(1000, 9999)
        elif category == AlertCategory.PERFORMANCE:
            details["cpu_usage"] = round(random.uniform(0.0, 100.0), 2)
            details["memory_usage"] = round(random.uniform(0.0, 100.0), 2)
            details["response_time"] = round(random.uniform(1.0, 1000.0), 2)
        
        # Tworzenie alertu
        alert = alert_manager.create_alert(
            level=level,
            category=category,
            message=message,
            details=details,
            ea_id=ea_id,
            source=source,
            auto_resolve_after=timedelta(minutes=random.randint(5, 60)) if random.choice([True, False]) else None
        )
        
        # Losowo potwierdzamy lub rozwiązujemy niektóre alerty
        if random.random() < 0.3:
            alert_manager.acknowledge_alert(alert.alert_id, by="test_script")
        elif random.random() < 0.2:
            alert_manager.resolve_alert(alert.alert_id, by="test_script")
    
    print(f"Wygenerowano {count} alertów.")

def update_performance_metrics(count=60):
    """Aktualizuje metryki wydajności."""
    print(f"Aktualizacja {count} metryk wydajności...")
    
    status_reporter = get_status_reporter()
    
    for i in range(count):
        # Symulacja żądań
        for _ in range(random.randint(1, 10)):
            status_reporter.increment_request_counter()
        
        # Symulacja poleceń
        for _ in range(random.randint(0, 3)):
            status_reporter.increment_command_counter()
        
        # Symulacja czasów odpowiedzi
        status_reporter.record_response_time(random.uniform(10.0, 500.0))
        
        # Symulacja wyników operacji
        status_reporter.record_operation_result(random.random() > 0.2)
        
        # Krótkie oczekiwanie
        time.sleep(0.05)
    
    print(f"Zaktualizowano {count} metryk wydajności.")

def print_basic_status():
    """Wyświetla podstawowy status systemu."""
    print("\n=== PODSTAWOWY STATUS SYSTEMU ===")
    
    status_reporter = get_status_reporter()
    status = status_reporter.get_basic_status()
    
    print(json.dumps(status, indent=2))

def print_detailed_status():
    """Wyświetla szczegółowy status systemu."""
    print("\n=== SZCZEGÓŁOWY STATUS SYSTEMU ===")
    
    status_reporter = get_status_reporter()
    status = status_reporter.get_detailed_status()
    
    print(json.dumps(status, indent=2))

def print_connection_info():
    """Wyświetla informacje o połączeniach."""
    print("\n=== INFORMACJE O POŁĄCZENIACH ===")
    
    connection_tracker = get_connection_tracker()
    connections = connection_tracker.get_all_connections()
    
    print(json.dumps(connections, indent=2))

def print_alerts():
    """Wyświetla informacje o alertach."""
    print("\n=== INFORMACJE O ALERTACH ===")
    
    alert_manager = get_alert_manager()
    alerts = alert_manager.get_alerts()
    
    print(json.dumps(alerts, indent=2))

def print_logs():
    """Wyświetla ostatnie logi."""
    print("\n=== OSTATNIE LOGI ===")
    
    logger = get_logger()
    logs = logger.get_logs(limit=10)
    
    for log in logs:
        print(f"{log.timestamp.strftime('%Y-%m-%d %H:%M:%S')} - {log.level.name} - {log.ea_id} - {log.operation_type.name} - {log.status.name} - {log.message}")

def main():
    """Główna funkcja."""
    parser = argparse.ArgumentParser(description='Test funkcjonalności monitorowania AgentMT5')
    parser.add_argument('--logs', type=int, default=10, help='Liczba przykładowych logów do wygenerowania')
    parser.add_argument('--connections', type=int, default=5, help='Liczba przykładowych połączeń do wygenerowania')
    parser.add_argument('--alerts', type=int, default=5, help='Liczba przykładowych alertów do wygenerowania')
    parser.add_argument('--metrics', type=int, default=60, help='Liczba aktualizacji metryk wydajności')
    parser.add_argument('--stats', action='store_true', help='Wyświetl statystyki po wygenerowaniu danych')
    parser.add_argument('--detailed', action='store_true', help='Wyświetl szczegółowe statystyki')
    args = parser.parse_args()
    
    print("=== TEST FUNKCJONALNOŚCI MONITOROWANIA ===")
    print(f"Data i czas: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Generowanie przykładowych danych
    generate_sample_logs(args.logs)
    generate_sample_connections(args.connections)
    generate_sample_alerts(args.alerts)
    update_performance_metrics(args.metrics)
    
    # Wyświetlanie statystyk
    if args.stats or args.detailed:
        if args.detailed:
            print_detailed_status()
            print_connection_info()
            print_alerts()
            print_logs()
        else:
            print_basic_status()
    
    print("\nTest zakończony pomyślnie.")

if __name__ == "__main__":
    main() 