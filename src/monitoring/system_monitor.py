#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Moduł zawierający implementację monitora systemu do monitorowania wydajności 
i zachowania systemu podczas testów i pracy produkcyjnej.
"""

import os
import sys
import time
import logging
import threading
import json
import platform
import psutil
from datetime import datetime
from enum import Enum, auto
from typing import Dict, Any, List, Optional

# Dodanie głównego katalogu projektu do ścieżki
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from src.utils.logger import setup_logger
from src.utils.path_utils import get_project_root

# Konfiguracja logowania
logger = logging.getLogger(__name__)

class MonitoringLevel(Enum):
    """Poziomy monitorowania systemu."""
    BASIC = auto()       # Podstawowe informacje: CPU, RAM, liczba operacji
    EXTENDED = auto()    # Rozszerzone: + czasy odpowiedzi, wydajność API
    DETAILED = auto()    # Szczegółowe: + śledzenie operacji, statystyki per instrument
    DEBUG = auto()       # Debugowanie: + zapisy wszystkich operacji, pełne ślady

class SystemMonitor:
    """
    Klasa monitora systemu odpowiedzialna za monitorowanie wydajności
    i zachowania systemu podczas testów i pracy produkcyjnej.
    
    Monitorowane są:
    - Zużycie zasobów (CPU, RAM)
    - Czasy odpowiedzi API
    - Statystyki operacji (liczba, rodzaj)
    - Wydajność poszczególnych komponentów
    - Anomalie w działaniu systemu
    """
    
    _instance = None
    
    @classmethod
    def get_instance(cls) -> 'SystemMonitor':
        """
        Pobiera instancję monitora systemu w trybie singletonu.
        
        Returns:
            SystemMonitor: Instancja monitora systemu
        """
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def __init__(self):
        """Inicjalizacja monitora systemu."""
        # Zabezpieczenie przed wielokrotną inicjalizacją singletonu
        if SystemMonitor._instance is not None:
            return
        
        self.monitoring_level = MonitoringLevel.BASIC
        self.sampling_interval = 10  # sekundy
        self.report_interval = 300   # sekundy (5 minut)
        
        # Ścieżka do katalogu z danymi monitoringu
        self.monitoring_dir = os.path.join(get_project_root(), 'logs', 'monitoring')
        os.makedirs(self.monitoring_dir, exist_ok=True)
        
        # Ścieżka do pliku z danymi monitoringu
        self.monitoring_file = os.path.join(
            self.monitoring_dir, 
            f"monitoring_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )
        
        # Dane monitoringu
        self.monitoring_data = {
            "system": self._get_system_info(),
            "start_time": datetime.now().isoformat(),
            "samples": [],
            "alerts": [],
            "operations": [],
            "performance": {}
        }
        
        # Flagi kontrolne
        self.is_monitoring = False
        self.stop_event = threading.Event()
        
        # Wątki monitorowania
        self.monitoring_thread = None
        self.reporting_thread = None
        
        SystemMonitor._instance = self
        logger.info("SystemMonitor zainicjalizowany")
    
    def _get_system_info(self) -> Dict[str, Any]:
        """
        Pobiera informacje o systemie.
        
        Returns:
            Dict[str, Any]: Informacje o systemie
        """
        return {
            "platform": platform.platform(),
            "python": platform.python_version(),
            "cpu_count": psutil.cpu_count(logical=True),
            "memory_total": psutil.virtual_memory().total,
            "hostname": platform.node(),
            "timezone": time.tzname
        }
    
    def _get_current_stats(self) -> Dict[str, Any]:
        """
        Pobiera bieżące statystyki systemu.
        
        Returns:
            Dict[str, Any]: Bieżące statystyki systemu
        """
        # Statystyki podstawowe
        stats = {
            "timestamp": datetime.now().isoformat(),
            "cpu_percent": psutil.cpu_percent(interval=0.1),
            "memory_percent": psutil.virtual_memory().percent,
            "disk_usage_percent": psutil.disk_usage('/').percent,
            "process_count": len(psutil.pids()),
            "operations_count": len(self.monitoring_data["operations"])
        }
        
        # Statystyki rozszerzone
        if self.monitoring_level.value >= MonitoringLevel.EXTENDED.value:
            stats.update({
                "network_io": {
                    "bytes_sent": psutil.net_io_counters().bytes_sent,
                    "bytes_recv": psutil.net_io_counters().bytes_recv
                },
                "disk_io": {
                    "read_bytes": psutil.disk_io_counters().read_bytes,
                    "write_bytes": psutil.disk_io_counters().write_bytes
                },
                "process_memory": psutil.Process().memory_info().rss
            })
            
            # Dodanie statystyk per instrument jeśli dostępne
            if "performance" in self.monitoring_data and self.monitoring_data["performance"]:
                stats["instruments_performance"] = self.monitoring_data["performance"]
        
        # Statystyki szczegółowe
        if self.monitoring_level.value >= MonitoringLevel.DETAILED.value:
            # Ostatnie operacje
            last_operations = self.monitoring_data["operations"][-10:] if self.monitoring_data["operations"] else []
            stats["last_operations"] = last_operations
            
            # Dodanie statystyk logów
            try:
                log_dir = os.path.join(get_project_root(), 'logs')
                log_files = [f for f in os.listdir(log_dir) if f.endswith('.log')]
                latest_log = max(log_files, key=lambda x: os.path.getmtime(os.path.join(log_dir, x)), default=None)
                
                if latest_log:
                    log_path = os.path.join(log_dir, latest_log)
                    log_size = os.path.getsize(log_path)
                    stats["latest_log"] = {
                        "name": latest_log,
                        "size": log_size,
                        "last_modified": datetime.fromtimestamp(os.path.getmtime(log_path)).isoformat()
                    }
            except Exception as e:
                logger.warning(f"Nie udało się pobrać statystyk logów: {e}")
        
        return stats
    
    def set_monitoring_level(self, level: MonitoringLevel) -> None:
        """
        Ustawia poziom monitorowania.
        
        Args:
            level: Poziom monitorowania
        """
        self.monitoring_level = level
        logger.info(f"Ustawiono poziom monitorowania: {level.name}")
    
    def set_sampling_interval(self, interval: int) -> None:
        """
        Ustawia interwał próbkowania.
        
        Args:
            interval: Interwał próbkowania w sekundach
        """
        if interval < 1:
            logger.warning("Interwał próbkowania musi być większy niż 0, ustawiam na 1")
            interval = 1
        
        self.sampling_interval = interval
        logger.info(f"Ustawiono interwał próbkowania: {interval}s")
    
    def set_report_interval(self, interval: int) -> None:
        """
        Ustawia interwał raportowania.
        
        Args:
            interval: Interwał raportowania w sekundach
        """
        if interval < 10:
            logger.warning("Interwał raportowania musi być większy niż 10, ustawiam na 10")
            interval = 10
        
        self.report_interval = interval
        logger.info(f"Ustawiono interwał raportowania: {interval}s")
    
    def start_monitoring(self) -> bool:
        """
        Rozpoczyna monitorowanie systemu.
        
        Returns:
            bool: True jeśli monitoring został uruchomiony pomyślnie
        """
        if self.is_monitoring:
            logger.warning("Monitoring jest już uruchomiony")
            return False
        
        try:
            # Resetowanie danych
            self.monitoring_data["start_time"] = datetime.now().isoformat()
            self.monitoring_data["samples"] = []
            self.monitoring_data["alerts"] = []
            self.monitoring_data["operations"] = []
            self.monitoring_data["performance"] = {}
            
            # Resetowanie flagi zatrzymania
            self.stop_event.clear()
            self.is_monitoring = True
            
            # Wątek monitorowania
            self.monitoring_thread = threading.Thread(target=self._monitoring_loop)
            self.monitoring_thread.daemon = True
            self.monitoring_thread.start()
            
            # Wątek raportowania
            self.reporting_thread = threading.Thread(target=self._reporting_loop)
            self.reporting_thread.daemon = True
            self.reporting_thread.start()
            
            logger.info("Monitoring systemu uruchomiony")
            return True
        
        except Exception as e:
            logger.error(f"Błąd podczas uruchamiania monitoringu: {e}")
            self.is_monitoring = False
            return False
    
    def stop_monitoring(self) -> None:
        """Zatrzymuje monitorowanie systemu."""
        if not self.is_monitoring:
            logger.warning("Monitoring nie jest uruchomiony")
            return
        
        try:
            # Ustawienie flagi zatrzymania
            self.stop_event.set()
            
            # Oczekiwanie na zakończenie wątków
            if self.monitoring_thread and self.monitoring_thread.is_alive():
                self.monitoring_thread.join(timeout=5)
            
            if self.reporting_thread and self.reporting_thread.is_alive():
                self.reporting_thread.join(timeout=5)
            
            # Zapisanie danych monitoringu
            self._save_monitoring_data()
            
            self.is_monitoring = False
            logger.info("Monitoring systemu zatrzymany")
        
        except Exception as e:
            logger.error(f"Błąd podczas zatrzymywania monitoringu: {e}")
    
    def record_operation(self, operation_type: str, details: Dict[str, Any]) -> None:
        """
        Rejestruje operację.
        
        Args:
            operation_type: Typ operacji
            details: Szczegóły operacji
        """
        if not self.is_monitoring:
            return
        
        # Bazowy poziom monitorowania rejestruje tylko podstawowe operacje
        if self.monitoring_level == MonitoringLevel.BASIC and operation_type not in [
            "signal_generated", "position_opened", "position_closed", "error"
        ]:
            return
        
        operation = {
            "timestamp": datetime.now().isoformat(),
            "type": operation_type,
            "details": details
        }
        
        self.monitoring_data["operations"].append(operation)
        
        # Dla poziomu DEBUG, od razu zapisujemy operację do pliku
        if self.monitoring_level == MonitoringLevel.DEBUG:
            self._save_monitoring_data()
    
    def record_performance(self, component: str, metric: str, value: float) -> None:
        """
        Rejestruje metrykę wydajności.
        
        Args:
            component: Nazwa komponentu
            metric: Nazwa metryki
            value: Wartość metryki
        """
        if not self.is_monitoring:
            return
        
        if component not in self.monitoring_data["performance"]:
            self.monitoring_data["performance"][component] = {}
        
        if metric not in self.monitoring_data["performance"][component]:
            self.monitoring_data["performance"][component][metric] = []
        
        self.monitoring_data["performance"][component][metric].append({
            "timestamp": datetime.now().isoformat(),
            "value": value
        })
    
    def record_alert(self, severity: str, message: str, details: Optional[Dict[str, Any]] = None) -> None:
        """
        Rejestruje alert.
        
        Args:
            severity: Poziom ważności alertu (low, medium, high, critical)
            message: Komunikat alertu
            details: Szczegóły alertu (opcjonalnie)
        """
        if not self.is_monitoring:
            return
        
        alert = {
            "timestamp": datetime.now().isoformat(),
            "severity": severity,
            "message": message,
            "details": details or {}
        }
        
        self.monitoring_data["alerts"].append(alert)
        
        # Dla alertów o wysokiej ważności lub krytycznych, od razu zapisujemy dane
        if severity in ["high", "critical"]:
            self._save_monitoring_data()
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """
        Pobiera podsumowanie wydajności.
        
        Returns:
            Dict[str, Any]: Podsumowanie wydajności
        """
        summary = {
            "monitoring_level": self.monitoring_level.name,
            "samples_count": len(self.monitoring_data["samples"]),
            "operations_count": len(self.monitoring_data["operations"]),
            "alerts_count": len(self.monitoring_data["alerts"]),
            "components": {}
        }
        
        # Obliczanie średnich wartości dla metryk wydajności
        for component, metrics in self.monitoring_data["performance"].items():
            summary["components"][component] = {}
            
            for metric, values in metrics.items():
                if values:
                    avg_value = sum(item["value"] for item in values) / len(values)
                    summary["components"][component][metric] = {
                        "avg": avg_value,
                        "min": min(item["value"] for item in values),
                        "max": max(item["value"] for item in values),
                        "count": len(values)
                    }
        
        return summary
    
    def _monitoring_loop(self) -> None:
        """Główna pętla monitorowania."""
        try:
            while not self.stop_event.is_set():
                # Pobieranie bieżących statystyk
                stats = self._get_current_stats()
                
                # Dodawanie do danych monitoringu
                self.monitoring_data["samples"].append(stats)
                
                # Wykrywanie anomalii (tylko dla poziomów wyższych niż BASIC)
                if self.monitoring_level.value > MonitoringLevel.BASIC.value:
                    self._detect_anomalies(stats)
                
                # Oczekiwanie na następny cykl próbkowania
                self.stop_event.wait(self.sampling_interval)
        
        except Exception as e:
            logger.error(f"Błąd w pętli monitorowania: {e}")
            self.is_monitoring = False
    
    def _reporting_loop(self) -> None:
        """Pętla raportowania danych monitoringu."""
        try:
            while not self.stop_event.is_set():
                # Zapisanie danych monitoringu
                self._save_monitoring_data()
                
                # Oczekiwanie na następny cykl raportowania
                self.stop_event.wait(self.report_interval)
        
        except Exception as e:
            logger.error(f"Błąd w pętli raportowania: {e}")
    
    def _detect_anomalies(self, stats: Dict[str, Any]) -> None:
        """
        Wykrywa anomalie w statystykach systemu.
        
        Args:
            stats: Bieżące statystyki systemu
        """
        # Wysokie zużycie CPU
        if stats["cpu_percent"] > 90:
            self.record_alert(
                severity="high" if stats["cpu_percent"] > 95 else "medium",
                message=f"Wysokie zużycie CPU: {stats['cpu_percent']}%"
            )
        
        # Wysokie zużycie pamięci
        if stats["memory_percent"] > 90:
            self.record_alert(
                severity="high" if stats["memory_percent"] > 95 else "medium",
                message=f"Wysokie zużycie pamięci: {stats['memory_percent']}%"
            )
        
        # Wysokie zużycie dysku
        if stats["disk_usage_percent"] > 90:
            self.record_alert(
                severity="medium",
                message=f"Wysokie zużycie dysku: {stats['disk_usage_percent']}%"
            )
        
        # Analiza wzrostu liczby operacji
        if len(self.monitoring_data["samples"]) > 1:
            prev_samples = self.monitoring_data["samples"][-2]
            curr_operations = stats.get("operations_count", 0)
            prev_operations = prev_samples.get("operations_count", 0)
            
            # Jeśli liczba operacji znacząco wzrosła
            if curr_operations > prev_operations + 100:
                self.record_alert(
                    severity="medium",
                    message=f"Gwałtowny wzrost liczby operacji: {prev_operations} -> {curr_operations}"
                )
    
    def _save_monitoring_data(self) -> None:
        """Zapisuje dane monitoringu do pliku."""
        try:
            with open(self.monitoring_file, 'w', encoding='utf-8') as f:
                json.dump(self.monitoring_data, f, indent=2)
            
            logger.debug(f"Zapisano dane monitoringu do {self.monitoring_file}")
        
        except Exception as e:
            logger.error(f"Błąd podczas zapisywania danych monitoringu: {e}")

# Funkcja pomocnicza do pobierania instancji monitora systemu
def get_system_monitor() -> SystemMonitor:
    """
    Pobiera instancję monitora systemu.
    
    Returns:
        SystemMonitor: Instancja monitora systemu
    """
    return SystemMonitor.get_instance() 