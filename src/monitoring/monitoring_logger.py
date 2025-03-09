#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
MonitoringLogger - klasa odpowiedzialna za logowanie operacji w systemie AgentMT5.
Umożliwia logowanie z różnymi poziomami, zapisywanie do pliku oraz przesyłanie logów do innych komponentów.
"""

import os
import json
import logging
import threading
from datetime import datetime
from enum import Enum, auto
from typing import Dict, List, Any, Optional, Union

class LogLevel(Enum):
    """Poziomy logowania."""
    DEBUG = auto()
    INFO = auto()
    WARNING = auto()
    ERROR = auto()
    CRITICAL = auto()

class OperationType(Enum):
    """Typy operacji wykonywanych w systemie."""
    CONNECTION = auto()
    INIT = auto()
    OPEN_POSITION = auto()
    CLOSE_POSITION = auto()
    MODIFY_POSITION = auto()
    MARKET_DATA = auto()
    ACCOUNT_INFO = auto()
    COMMAND = auto()
    SYSTEM = auto()

class OperationStatus(Enum):
    """Statusy wykonania operacji."""
    SUCCESS = auto()
    FAILED = auto()
    PENDING = auto()
    REJECTED = auto()
    UNKNOWN = auto()

class LogEntry:
    """Reprezentacja wpisu w logu."""
    
    def __init__(
        self,
        timestamp: datetime,
        level: LogLevel,
        ea_id: str,
        operation_type: OperationType,
        status: OperationStatus,
        details: Dict[str, Any],
        message: Optional[str] = None
    ):
        self.timestamp = timestamp
        self.level = level
        self.ea_id = ea_id
        self.operation_type = operation_type
        self.status = status
        self.details = details
        self.message = message or ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Konwertuje wpis do słownika."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "level": self.level.name,
            "ea_id": self.ea_id,
            "operation_type": self.operation_type.name,
            "status": self.status.name,
            "details": self.details,
            "message": self.message
        }
    
    def to_json(self) -> str:
        """Konwertuje wpis do formatu JSON."""
        return json.dumps(self.to_dict(), ensure_ascii=False)
    
    def __str__(self) -> str:
        """Zwraca reprezentację tekstową wpisu."""
        return f"[{self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}] - {self.level.name} - {self.ea_id} - {self.operation_type.name} - {self.status.name} - {self.message}"

class MonitoringLogger:
    """Klasa do logowania operacji w systemie AgentMT5."""
    
    def __init__(
        self,
        log_to_file: bool = True,
        log_dir: Optional[str] = None,
        file_name_prefix: str = "agent_mt5_",
        max_file_size_mb: int = 10,
        max_files: int = 5,
        min_level: LogLevel = LogLevel.INFO
    ):
        """Inicjalizuje logger.
        
        Args:
            log_to_file: Czy zapisywać logi do pliku.
            log_dir: Katalog, w którym będą zapisywane pliki logów.
            file_name_prefix: Prefiks nazwy pliku logu.
            max_file_size_mb: Maksymalny rozmiar pliku logu w MB.
            max_files: Maksymalna liczba plików logów.
            min_level: Minimalny poziom logowania.
        """
        self.log_to_file = log_to_file
        self.log_dir = log_dir or os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'logs')
        self.file_name_prefix = file_name_prefix
        self.max_file_size_mb = max_file_size_mb
        self.max_files = max_files
        self.min_level = min_level
        
        # Tworzenie katalogu logów, jeśli nie istnieje
        if log_to_file and not os.path.exists(self.log_dir):
            os.makedirs(self.log_dir)
        
        # Inicjalizacja loggera standardowego
        self.logger = logging.getLogger('AgentMT5Monitor')
        self.logger.setLevel(logging.DEBUG)
        
        # Handler dla konsoli
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_formatter = logging.Formatter('[%(asctime)s] - %(levelname)s - %(message)s')
        console_handler.setFormatter(console_formatter)
        self.logger.addHandler(console_handler)
        
        # Handler dla pliku, jeśli wymagany
        if log_to_file:
            self.setup_file_handler()
        
        # Lista logów w pamięci
        self.logs: List[LogEntry] = []
        self.logs_lock = threading.Lock()
        
        # Callback dla alertów
        self.alert_callback = None
    
    def setup_file_handler(self):
        """Konfiguruje handler dla zapisywania logów do pliku."""
        now = datetime.now()
        log_file = os.path.join(
            self.log_dir,
            f"{self.file_name_prefix}{now.strftime('%Y%m%d')}.log"
        )
        
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter('[%(asctime)s] - %(levelname)s - %(message)s')
        file_handler.setFormatter(file_formatter)
        self.logger.addHandler(file_handler)
    
    def set_alert_callback(self, callback):
        """Ustawia callback dla alertów.
        
        Args:
            callback: Funkcja przyjmująca LogEntry jako argument.
        """
        self.alert_callback = callback
    
    def log(
        self,
        level: LogLevel,
        ea_id: str,
        operation_type: OperationType,
        status: OperationStatus,
        details: Dict[str, Any],
        message: Optional[str] = None
    ) -> LogEntry:
        """Loguje operację.
        
        Args:
            level: Poziom logowania.
            ea_id: Identyfikator EA.
            operation_type: Typ operacji.
            status: Status operacji.
            details: Szczegóły operacji.
            message: Dodatkowy komunikat.
            
        Returns:
            Utworzony wpis w logu.
        """
        # Pomiń jeśli poziom jest mniejszy niż minimalny
        if level.value < self.min_level.value:
            return None
        
        # Tworzenie wpisu
        entry = LogEntry(
            timestamp=datetime.now(),
            level=level,
            ea_id=ea_id,
            operation_type=operation_type,
            status=status,
            details=details,
            message=message
        )
        
        # Logowanie standardowe
        log_message = f"{ea_id} - {operation_type.name} - {status.name} - {message if message else json.dumps(details)}"
        if level == LogLevel.DEBUG:
            self.logger.debug(log_message)
        elif level == LogLevel.INFO:
            self.logger.info(log_message)
        elif level == LogLevel.WARNING:
            self.logger.warning(log_message)
        elif level == LogLevel.ERROR:
            self.logger.error(log_message)
        elif level == LogLevel.CRITICAL:
            self.logger.critical(log_message)
        
        # Zapisanie wpisu w pamięci
        with self.logs_lock:
            self.logs.append(entry)
            # Ograniczenie liczby wpisów w pamięci do 1000
            if len(self.logs) > 1000:
                self.logs = self.logs[-1000:]
        
        # Wywołanie callbacka jeśli istnieje i poziom jest wystarczający
        if self.alert_callback and level.value >= LogLevel.WARNING.value:
            self.alert_callback(entry)
        
        return entry
    
    def debug(self, ea_id: str, operation_type: OperationType, status: OperationStatus, details: Dict[str, Any], message: Optional[str] = None) -> LogEntry:
        """Loguje operację na poziomie DEBUG."""
        return self.log(LogLevel.DEBUG, ea_id, operation_type, status, details, message)
    
    def info(self, ea_id: str, operation_type: OperationType, status: OperationStatus, details: Dict[str, Any], message: Optional[str] = None) -> LogEntry:
        """Loguje operację na poziomie INFO."""
        return self.log(LogLevel.INFO, ea_id, operation_type, status, details, message)
    
    def warning(self, ea_id: str, operation_type: OperationType, status: OperationStatus, details: Dict[str, Any], message: Optional[str] = None) -> LogEntry:
        """Loguje operację na poziomie WARNING."""
        return self.log(LogLevel.WARNING, ea_id, operation_type, status, details, message)
    
    def error(self, ea_id: str, operation_type: OperationType, status: OperationStatus, details: Dict[str, Any], message: Optional[str] = None) -> LogEntry:
        """Loguje operację na poziomie ERROR."""
        return self.log(LogLevel.ERROR, ea_id, operation_type, status, details, message)
    
    def critical(self, ea_id: str, operation_type: OperationType, status: OperationStatus, details: Dict[str, Any], message: Optional[str] = None) -> LogEntry:
        """Loguje operację na poziomie CRITICAL."""
        return self.log(LogLevel.CRITICAL, ea_id, operation_type, status, details, message)
    
    def get_logs(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        level: Optional[LogLevel] = None,
        ea_id: Optional[str] = None,
        operation_type: Optional[OperationType] = None,
        status: Optional[OperationStatus] = None,
        limit: int = 100
    ) -> List[LogEntry]:
        """Pobiera logi z pamięci z możliwością filtrowania.
        
        Args:
            start_time: Początkowy timestamp.
            end_time: Końcowy timestamp.
            level: Filtrowanie po poziomie logowania.
            ea_id: Filtrowanie po identyfikatorze EA.
            operation_type: Filtrowanie po typie operacji.
            status: Filtrowanie po statusie operacji.
            limit: Maksymalna liczba zwracanych wpisów.
            
        Returns:
            Lista wpisów spełniających kryteria filtrowania.
        """
        with self.logs_lock:
            filtered_logs = self.logs.copy()
        
        # Filtrowanie
        if start_time:
            filtered_logs = [log for log in filtered_logs if log.timestamp >= start_time]
        if end_time:
            filtered_logs = [log for log in filtered_logs if log.timestamp <= end_time]
        if level:
            filtered_logs = [log for log in filtered_logs if log.level.value >= level.value]
        if ea_id:
            filtered_logs = [log for log in filtered_logs if log.ea_id == ea_id]
        if operation_type:
            filtered_logs = [log for log in filtered_logs if log.operation_type == operation_type]
        if status:
            filtered_logs = [log for log in filtered_logs if log.status == status]
        
        # Ograniczenie liczby wpisów
        if limit and len(filtered_logs) > limit:
            filtered_logs = filtered_logs[-limit:]
        
        return filtered_logs

# Singleton instance
_instance = None
_instance_lock = threading.Lock()

def get_logger() -> MonitoringLogger:
    """Zwraca singleton instancję MonitoringLogger."""
    global _instance
    if _instance is None:
        with _instance_lock:
            if _instance is None:
                _instance = MonitoringLogger()
    return _instance 