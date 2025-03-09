#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
ConnectionTracker - klasa odpowiedzialna za śledzenie stanu połączeń w systemie AgentMT5.
Monitoruje aktywne połączenia, wykrywa rozłączenia i zbiera statystyki.
"""

import threading
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable

from src.monitoring.monitoring_logger import get_logger, OperationType, OperationStatus, LogLevel

class ConnectionStatus:
    """Status połączenia z EA."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    DISCONNECTED = "disconnected"
    UNKNOWN = "unknown"

class ConnectionInfo:
    """Informacje o połączeniu z EA."""
    
    def __init__(self, ea_id: str):
        """Inicjalizuje informacje o połączeniu.
        
        Args:
            ea_id: Identyfikator EA.
        """
        self.ea_id = ea_id
        self.connected_since = datetime.now()
        self.last_active = datetime.now()
        self.total_requests = 0
        self.total_commands = 0
        self.last_request_time = None
        self.last_command_time = None
        self.disconnected_at = None
        self.reconnect_count = 0
        self.longest_inactivity = timedelta(seconds=0)
        self.status = ConnectionStatus.ACTIVE
        self.inactive_threshold = timedelta(minutes=5)  # Próg nieaktywności - 5 minut
        
    def update_activity(self, is_command: bool = False):
        """Aktualizuje czas ostatniej aktywności.
        
        Args:
            is_command: Czy aktualizacja dotyczy polecenia.
        """
        now = datetime.now()
        inactive_time = now - self.last_active
        
        if inactive_time > self.longest_inactivity:
            self.longest_inactivity = inactive_time
        
        self.last_active = now
        
        if is_command:
            self.total_commands += 1
            self.last_command_time = now
        else:
            self.total_requests += 1
            self.last_request_time = now
        
        if self.status != ConnectionStatus.ACTIVE:
            if self.status == ConnectionStatus.DISCONNECTED:
                self.reconnect_count += 1
            self.status = ConnectionStatus.ACTIVE
    
    def check_activity(self) -> bool:
        """Sprawdza, czy połączenie jest aktywne.
        
        Returns:
            True, jeśli połączenie jest aktywne, False w przeciwnym razie.
        """
        now = datetime.now()
        inactive_time = now - self.last_active
        
        if inactive_time > self.inactive_threshold:
            if self.status == ConnectionStatus.ACTIVE:
                self.status = ConnectionStatus.INACTIVE
            return False
        return True
    
    def disconnect(self):
        """Oznacza połączenie jako rozłączone."""
        self.disconnected_at = datetime.now()
        self.status = ConnectionStatus.DISCONNECTED
    
    def to_dict(self) -> Dict[str, Any]:
        """Konwertuje informacje o połączeniu do słownika.
        
        Returns:
            Słownik z informacjami o połączeniu.
        """
        return {
            "ea_id": self.ea_id,
            "connected_since": self.connected_since.isoformat(),
            "last_active": self.last_active.isoformat(),
            "total_requests": self.total_requests,
            "total_commands": self.total_commands,
            "last_request_time": self.last_request_time.isoformat() if self.last_request_time else None,
            "last_command_time": self.last_command_time.isoformat() if self.last_command_time else None,
            "disconnected_at": self.disconnected_at.isoformat() if self.disconnected_at else None,
            "reconnect_count": self.reconnect_count,
            "longest_inactivity": str(self.longest_inactivity),
            "status": self.status,
            "inactive_since": str(datetime.now() - self.last_active)
        }

class ConnectionTracker:
    """Klasa do śledzenia stanu połączeń w systemie AgentMT5."""
    
    def __init__(self, inactive_check_interval: int = 60):
        """Inicjalizuje tracker połączeń.
        
        Args:
            inactive_check_interval: Interwał sprawdzania nieaktywnych połączeń (w sekundach).
        """
        self.connections: Dict[str, ConnectionInfo] = {}
        self.connections_lock = threading.Lock()
        self.inactive_check_interval = inactive_check_interval
        self.inactivity_callbacks: List[Callable[[str], None]] = []
        
        # Uruchomienie wątku sprawdzającego nieaktywne połączenia
        self.checker_thread = threading.Thread(target=self._check_inactive_connections, daemon=True)
        self.checker_thread.start()
        
        # Logger
        self.logger = get_logger()
    
    def register_connection(self, ea_id: str) -> ConnectionInfo:
        """Rejestruje nowe połączenie lub aktualizuje istniejące.
        
        Args:
            ea_id: Identyfikator EA.
            
        Returns:
            Informacje o połączeniu.
        """
        with self.connections_lock:
            if ea_id in self.connections:
                connection = self.connections[ea_id]
                if connection.status == ConnectionStatus.DISCONNECTED:
                    # EA ponownie się połączył
                    connection.reconnect_count += 1
                    connection.status = ConnectionStatus.ACTIVE
                    connection.last_active = datetime.now()
                    
                    # Logowanie ponownego połączenia
                    self.logger.info(
                        ea_id, 
                        OperationType.CONNECTION, 
                        OperationStatus.SUCCESS, 
                        {"reconnect_count": connection.reconnect_count},
                        "EA reconnected"
                    )
            else:
                # Nowe połączenie
                connection = ConnectionInfo(ea_id)
                self.connections[ea_id] = connection
                
                # Logowanie nowego połączenia
                self.logger.info(
                    ea_id, 
                    OperationType.CONNECTION, 
                    OperationStatus.SUCCESS, 
                    {},
                    "New EA connection"
                )
            
            return connection
    
    def update_activity(self, ea_id: str, is_command: bool = False):
        """Aktualizuje czas ostatniej aktywności dla danego EA.
        
        Args:
            ea_id: Identyfikator EA.
            is_command: Czy aktualizacja dotyczy polecenia.
        """
        with self.connections_lock:
            if ea_id not in self.connections:
                self.register_connection(ea_id)
            
            self.connections[ea_id].update_activity(is_command)
    
    def disconnect(self, ea_id: str):
        """Oznacza połączenie jako rozłączone.
        
        Args:
            ea_id: Identyfikator EA.
        """
        with self.connections_lock:
            if ea_id in self.connections:
                self.connections[ea_id].disconnect()
                
                # Logowanie rozłączenia
                self.logger.info(
                    ea_id, 
                    OperationType.CONNECTION, 
                    OperationStatus.FAILED, 
                    {"disconnected_at": datetime.now().isoformat()},
                    "EA disconnected"
                )
    
    def get_connection_info(self, ea_id: str) -> Optional[Dict[str, Any]]:
        """Pobiera informacje o połączeniu dla danego EA.
        
        Args:
            ea_id: Identyfikator EA.
            
        Returns:
            Słownik z informacjami o połączeniu lub None, jeśli połączenie nie istnieje.
        """
        with self.connections_lock:
            if ea_id in self.connections:
                return self.connections[ea_id].to_dict()
            return None
    
    def get_all_connections(self) -> List[Dict[str, Any]]:
        """Pobiera informacje o wszystkich połączeniach.
        
        Returns:
            Lista słowników z informacjami o połączeniach.
        """
        with self.connections_lock:
            return [conn.to_dict() for conn in self.connections.values()]
    
    def add_inactivity_callback(self, callback: Callable[[str], None]):
        """Dodaje callback wywoływany, gdy połączenie zostanie oznaczone jako nieaktywne.
        
        Args:
            callback: Funkcja przyjmująca identyfikator EA jako argument.
        """
        self.inactivity_callbacks.append(callback)
    
    def _check_inactive_connections(self):
        """Wątek sprawdzający nieaktywne połączenia."""
        while True:
            inactive_ea_ids = []
            
            with self.connections_lock:
                for ea_id, connection in self.connections.items():
                    if not connection.check_activity() and connection.status == ConnectionStatus.ACTIVE:
                        inactive_ea_ids.append(ea_id)
                        
                        # Logowanie nieaktywnego połączenia
                        self.logger.warning(
                            ea_id, 
                            OperationType.CONNECTION, 
                            OperationStatus.FAILED, 
                            {"inactive_since": str(datetime.now() - connection.last_active)},
                            "EA connection inactive"
                        )
            
            # Wywołanie callbacków dla nieaktywnych połączeń
            for ea_id in inactive_ea_ids:
                for callback in self.inactivity_callbacks:
                    try:
                        callback(ea_id)
                    except Exception as e:
                        self.logger.error(
                            "SYSTEM", 
                            OperationType.SYSTEM, 
                            OperationStatus.FAILED, 
                            {"error": str(e)},
                            f"Error in inactivity callback for EA {ea_id}"
                        )
            
            # Oczekiwanie na następne sprawdzenie
            time.sleep(self.inactive_check_interval)

# Singleton instance
_instance = None
_instance_lock = threading.Lock()

def get_connection_tracker() -> ConnectionTracker:
    """Zwraca singleton instancję ConnectionTracker."""
    global _instance
    if _instance is None:
        with _instance_lock:
            if _instance is None:
                _instance = ConnectionTracker()
    return _instance 