#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
StatusReporter - klasa odpowiedzialna za raportowanie statusu systemu AgentMT5.
Generuje raporty statusu oraz udostępnia dane o stanie systemu.
"""

import threading
import time
import json
import psutil
import os
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Union, Tuple

from src.monitoring.monitoring_logger import get_logger, OperationType, OperationStatus, LogLevel
from src.monitoring.connection_tracker import get_connection_tracker, ConnectionStatus
from src.monitoring.alert_manager import get_alert_manager, AlertLevel, AlertCategory, AlertStatus

class SystemStatus:
    """Status systemu."""
    OK = "ok"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

class StatusReporter:
    """Klasa do raportowania statusu systemu AgentMT5."""
    
    def __init__(
        self,
        basic_interval: int = 60,
        detailed_interval: int = 3600,
        full_interval: int = 86400,
        performance_samples: int = 60
    ):
        """Inicjalizuje reporter statusu.
        
        Args:
            basic_interval: Interwał generowania podstawowych raportów (w sekundach).
            detailed_interval: Interwał generowania szczegółowych raportów (w sekundach).
            full_interval: Interwał generowania pełnych raportów (w sekundach).
            performance_samples: Liczba próbek do śledzenia wydajności.
        """
        self.basic_interval = basic_interval
        self.detailed_interval = detailed_interval
        self.full_interval = full_interval
        self.performance_samples = performance_samples
        
        self.start_time = datetime.now()
        self.system_status = SystemStatus.OK
        
        # Dane wydajności
        self.performance_data = {
            "cpu_usage": [],
            "memory_usage": [],
            "requests_per_minute": [],
            "commands_per_minute": [],
            "response_times": []
        }
        
        # Liczniki
        self.request_counter = 0
        self.command_counter = 0
        self.last_minute_requests = 0
        self.last_minute_commands = 0
        self.last_counter_reset = datetime.now()
        
        # Statystyki
        self.total_requests = 0
        self.total_commands = 0
        self.total_successful_operations = 0
        self.total_failed_operations = 0
        
        # Zamki dla bezpiecznego dostępu
        self.performance_lock = threading.Lock()
        self.counters_lock = threading.Lock()
        self.stats_lock = threading.Lock()
        
        # Logger
        self.logger = get_logger()
        
        # Uruchomienie wątków raportowania
        self._start_reporting_threads()
    
    def _start_reporting_threads(self):
        """Uruchamia wątki raportowania."""
        # Wątek zbierający dane wydajności
        self.performance_thread = threading.Thread(target=self._collect_performance_data, daemon=True)
        self.performance_thread.start()
        
        # Wątek generujący podstawowe raporty
        self.basic_report_thread = threading.Thread(target=self._generate_basic_reports, daemon=True)
        self.basic_report_thread.start()
        
        # Wątek generujący szczegółowe raporty
        self.detailed_report_thread = threading.Thread(target=self._generate_detailed_reports, daemon=True)
        self.detailed_report_thread.start()
        
        # Wątek generujący pełne raporty
        self.full_report_thread = threading.Thread(target=self._generate_full_reports, daemon=True)
        self.full_report_thread.start()
    
    def increment_request_counter(self):
        """Inkrementuje licznik żądań."""
        with self.counters_lock:
            self.request_counter += 1
            self.total_requests += 1
    
    def increment_command_counter(self):
        """Inkrementuje licznik poleceń."""
        with self.counters_lock:
            self.command_counter += 1
            self.total_commands += 1
    
    def record_response_time(self, response_time: float):
        """Zapisuje czas odpowiedzi.
        
        Args:
            response_time: Czas odpowiedzi w milisekundach.
        """
        with self.performance_lock:
            self.performance_data["response_times"].append(response_time)
            
            # Ograniczenie liczby próbek
            if len(self.performance_data["response_times"]) > self.performance_samples:
                self.performance_data["response_times"] = self.performance_data["response_times"][-self.performance_samples:]
    
    def record_operation_result(self, success: bool):
        """Zapisuje wynik operacji.
        
        Args:
            success: Czy operacja zakończyła się sukcesem.
        """
        with self.stats_lock:
            if success:
                self.total_successful_operations += 1
            else:
                self.total_failed_operations += 1
    
    def get_basic_status(self) -> Dict[str, Any]:
        """Pobiera podstawowy status systemu.
        
        Returns:
            Słownik z podstawowym statusem systemu.
        """
        # Pobieranie danych o połączeniach
        connection_tracker = get_connection_tracker()
        connections = connection_tracker.get_all_connections()
        active_connections = [c for c in connections if c["status"] == ConnectionStatus.ACTIVE]
        
        # Obliczanie uptime
        uptime = datetime.now() - self.start_time
        uptime_str = self._format_timedelta(uptime)
        
        # Obliczanie średniego czasu odpowiedzi
        avg_response_time = self._calculate_avg_response_time()
        
        # Obliczanie obciążenia
        cpu_usage = self._get_current_cpu_usage()
        memory_usage = self._get_current_memory_usage()
        
        # Pobieranie danych o alertach
        alert_manager = get_alert_manager()
        alerts = alert_manager.get_alerts(status=AlertStatus.OPEN)
        
        # Liczba alertów według poziomów
        info_alerts = len([a for a in alerts if a["level"] == AlertLevel.INFO.name])
        warning_alerts = len([a for a in alerts if a["level"] == AlertLevel.WARNING.name])
        error_alerts = len([a for a in alerts if a["level"] == AlertLevel.ERROR.name])
        critical_alerts = len([a for a in alerts if a["level"] == AlertLevel.CRITICAL.name])
        
        # Określanie ogólnego statusu systemu
        system_status = SystemStatus.OK
        if critical_alerts > 0:
            system_status = SystemStatus.CRITICAL
        elif error_alerts > 0:
            system_status = SystemStatus.ERROR
        elif warning_alerts > 0:
            system_status = SystemStatus.WARNING
        
        # Aktualizacja statusu systemu
        self.system_status = system_status
        
        return {
            "status": system_status,
            "uptime": uptime_str,
            "active_eas": len(active_connections),
            "cpu_usage": cpu_usage,
            "memory_usage": memory_usage,
            "avg_response_time": avg_response_time,
            "last_minute_requests": self.last_minute_requests,
            "last_minute_commands": self.last_minute_commands,
            "alerts": {
                "info": info_alerts,
                "warning": warning_alerts,
                "error": error_alerts,
                "critical": critical_alerts
            }
        }
    
    def get_detailed_status(self) -> Dict[str, Any]:
        """Pobiera szczegółowy status systemu.
        
        Returns:
            Słownik ze szczegółowym statusem systemu.
        """
        basic_status = self.get_basic_status()
        
        # Pobieranie danych o połączeniach
        connection_tracker = get_connection_tracker()
        connections = connection_tracker.get_all_connections()
        
        # Pobieranie danych o alertach
        alert_manager = get_alert_manager()
        alerts = alert_manager.get_alerts(limit=20)
        
        # Obliczanie statystyk operacji
        total_operations = self.total_successful_operations + self.total_failed_operations
        success_rate = 100.0 if total_operations == 0 else (self.total_successful_operations / total_operations) * 100.0
        
        with self.performance_lock:
            # Obliczanie średnich wydajności
            avg_cpu_usage = sum(self.performance_data["cpu_usage"]) / max(1, len(self.performance_data["cpu_usage"]))
            avg_memory_usage = sum(self.performance_data["memory_usage"]) / max(1, len(self.performance_data["memory_usage"]))
            avg_requests_per_minute = sum(self.performance_data["requests_per_minute"]) / max(1, len(self.performance_data["requests_per_minute"]))
            avg_commands_per_minute = sum(self.performance_data["commands_per_minute"]) / max(1, len(self.performance_data["commands_per_minute"]))
        
        return {
            **basic_status,
            "connections": connections[:10],  # Ograniczenie do 10 połączeń
            "recent_alerts": alerts,
            "statistics": {
                "total_requests": self.total_requests,
                "total_commands": self.total_commands,
                "total_operations": total_operations,
                "success_rate": success_rate,
                "avg_cpu_usage": avg_cpu_usage,
                "avg_memory_usage": avg_memory_usage,
                "avg_requests_per_minute": avg_requests_per_minute,
                "avg_commands_per_minute": avg_commands_per_minute
            }
        }
    
    def get_full_status(self) -> Dict[str, Any]:
        """Pobiera pełny status systemu.
        
        Returns:
            Słownik z pełnym statusem systemu.
        """
        detailed_status = self.get_detailed_status()
        
        # Pobieranie wszystkich połączeń
        connection_tracker = get_connection_tracker()
        connections = connection_tracker.get_all_connections()
        
        # Pobieranie wszystkich alertów
        alert_manager = get_alert_manager()
        alerts = alert_manager.get_alerts(limit=100)
        
        # Pobieranie danych o wydajności
        with self.performance_lock:
            performance_data = {
                "cpu_usage": self.performance_data["cpu_usage"][-self.performance_samples:],
                "memory_usage": self.performance_data["memory_usage"][-self.performance_samples:],
                "requests_per_minute": self.performance_data["requests_per_minute"][-self.performance_samples:],
                "commands_per_minute": self.performance_data["commands_per_minute"][-self.performance_samples:],
                "response_times": self.performance_data["response_times"][-self.performance_samples:]
            }
        
        # Dane o systemie
        system_info = {
            "platform": os.name,
            "cpu_count": psutil.cpu_count(),
            "memory_total": psutil.virtual_memory().total,
            "memory_available": psutil.virtual_memory().available,
            "disk_usage": psutil.disk_usage('/').percent
        }
        
        return {
            **detailed_status,
            "connections": connections,
            "alerts": alerts,
            "performance": performance_data,
            "system_info": system_info
        }
    
    def _collect_performance_data(self):
        """Wątek zbierający dane wydajności."""
        while True:
            # Zbieranie danych CPU i pamięci
            cpu_usage = self._get_current_cpu_usage()
            memory_usage = self._get_current_memory_usage()
            
            with self.performance_lock:
                self.performance_data["cpu_usage"].append(cpu_usage)
                self.performance_data["memory_usage"].append(memory_usage)
                
                # Ograniczenie liczby próbek
                if len(self.performance_data["cpu_usage"]) > self.performance_samples:
                    self.performance_data["cpu_usage"] = self.performance_data["cpu_usage"][-self.performance_samples:]
                if len(self.performance_data["memory_usage"]) > self.performance_samples:
                    self.performance_data["memory_usage"] = self.performance_data["memory_usage"][-self.performance_samples:]
            
            # Aktualizacja liczników żądań i poleceń
            now = datetime.now()
            if (now - self.last_counter_reset).total_seconds() >= 60:
                with self.counters_lock:
                    self.last_minute_requests = self.request_counter
                    self.last_minute_commands = self.command_counter
                    
                    with self.performance_lock:
                        self.performance_data["requests_per_minute"].append(self.last_minute_requests)
                        self.performance_data["commands_per_minute"].append(self.last_minute_commands)
                        
                        # Ograniczenie liczby próbek
                        if len(self.performance_data["requests_per_minute"]) > self.performance_samples:
                            self.performance_data["requests_per_minute"] = self.performance_data["requests_per_minute"][-self.performance_samples:]
                        if len(self.performance_data["commands_per_minute"]) > self.performance_samples:
                            self.performance_data["commands_per_minute"] = self.performance_data["commands_per_minute"][-self.performance_samples:]
                    
                    self.request_counter = 0
                    self.command_counter = 0
                    self.last_counter_reset = now
            
            # Oczekiwanie przed następnym zbieraniem danych
            time.sleep(10)
    
    def _generate_basic_reports(self):
        """Wątek generujący podstawowe raporty."""
        while True:
            status = self.get_basic_status()
            
            # Logowanie podstawowego statusu
            self.logger.info(
                "SYSTEM",
                OperationType.SYSTEM,
                OperationStatus.SUCCESS,
                status,
                f"System status: {status['status']} - Active EAs: {status['active_eas']} - Alerts: {sum(status['alerts'].values())}"
            )
            
            # Oczekiwanie przed następnym raportem
            time.sleep(self.basic_interval)
    
    def _generate_detailed_reports(self):
        """Wątek generujący szczegółowe raporty."""
        # Oczekiwanie przed pierwszym raportem
        time.sleep(self.basic_interval * 3)
        
        while True:
            status = self.get_detailed_status()
            
            # Logowanie szczegółowego statusu
            self.logger.info(
                "SYSTEM",
                OperationType.SYSTEM,
                OperationStatus.SUCCESS,
                status,
                f"Detailed system status - Success rate: {status['statistics']['success_rate']:.2f}% - Avg response time: {status['avg_response_time']:.2f}ms"
            )
            
            # Oczekiwanie przed następnym raportem
            time.sleep(self.detailed_interval)
    
    def _generate_full_reports(self):
        """Wątek generujący pełne raporty."""
        # Oczekiwanie przed pierwszym raportem
        time.sleep(self.basic_interval * 5)
        
        while True:
            status = self.get_full_status()
            
            # Logowanie pełnego statusu
            self.logger.info(
                "SYSTEM",
                OperationType.SYSTEM,
                OperationStatus.SUCCESS,
                {"report_type": "full_status"},
                f"Full system status report generated"
            )
            
            # Zapisanie raportu do pliku
            self._save_full_report(status)
            
            # Oczekiwanie przed następnym raportem
            time.sleep(self.full_interval)
    
    def _save_full_report(self, status: Dict[str, Any]):
        """Zapisuje pełny raport do pliku.
        
        Args:
            status: Status systemu.
        """
        try:
            # Tworzenie katalogu raportów, jeśli nie istnieje
            reports_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'reports')
            if not os.path.exists(reports_dir):
                os.makedirs(reports_dir)
            
            # Tworzenie nazwy pliku z datą i czasem
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = os.path.join(reports_dir, f"system_report_{timestamp}.json")
            
            # Zapisanie raportu do pliku
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(status, f, ensure_ascii=False, indent=4)
            
            self.logger.info(
                "SYSTEM",
                OperationType.SYSTEM,
                OperationStatus.SUCCESS,
                {"filename": filename},
                f"Full system status report saved to {filename}"
            )
        except Exception as e:
            self.logger.error(
                "SYSTEM",
                OperationType.SYSTEM,
                OperationStatus.FAILED,
                {"error": str(e)},
                f"Error saving full system status report: {e}"
            )
    
    def _get_current_cpu_usage(self) -> float:
        """Pobiera aktualne zużycie CPU.
        
        Returns:
            Zużycie CPU w procentach.
        """
        try:
            return psutil.cpu_percent(interval=0.1)
        except Exception:
            return 0.0
    
    def _get_current_memory_usage(self) -> float:
        """Pobiera aktualne zużycie pamięci.
        
        Returns:
            Zużycie pamięci w procentach.
        """
        try:
            return psutil.virtual_memory().percent
        except Exception:
            return 0.0
    
    def _calculate_avg_response_time(self) -> float:
        """Oblicza średni czas odpowiedzi.
        
        Returns:
            Średni czas odpowiedzi w milisekundach.
        """
        with self.performance_lock:
            if not self.performance_data["response_times"]:
                return 0.0
            return sum(self.performance_data["response_times"]) / len(self.performance_data["response_times"])
    
    def _format_timedelta(self, delta: timedelta) -> str:
        """Formatuje timedelta do postaci czytelnej dla człowieka.
        
        Args:
            delta: Obiekt timedelta.
            
        Returns:
            Sformatowany string.
        """
        total_seconds = int(delta.total_seconds())
        days, remainder = divmod(total_seconds, 86400)
        hours, remainder = divmod(remainder, 3600)
        minutes, seconds = divmod(remainder, 60)
        
        if days > 0:
            return f"{days}d {hours}h {minutes}m {seconds}s"
        elif hours > 0:
            return f"{hours}h {minutes}m {seconds}s"
        elif minutes > 0:
            return f"{minutes}m {seconds}s"
        else:
            return f"{seconds}s"

# Singleton instance
_instance = None
_instance_lock = threading.Lock()

def get_status_reporter() -> StatusReporter:
    """Zwraca singleton instancję StatusReporter."""
    global _instance
    if _instance is None:
        with _instance_lock:
            if _instance is None:
                _instance = StatusReporter()
    return _instance 