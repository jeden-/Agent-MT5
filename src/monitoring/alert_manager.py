#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
AlertManager - klasa odpowiedzialna za zarządzanie alertami w systemie AgentMT5.
Umożliwia definiowanie reguł alertów, generowanie alertów oraz ich obsługę.
"""

import json
import threading
import time
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Any, Optional, Callable, Union

from src.monitoring.monitoring_logger import get_logger, LogEntry, LogLevel, OperationType, OperationStatus

class AlertLevel(Enum):
    """Poziomy alertów."""
    INFO = 0
    WARNING = 1
    ERROR = 2
    CRITICAL = 3

class AlertStatus(Enum):
    """Statusy alertów."""
    OPEN = "open"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    AUTO_RESOLVED = "auto_resolved"

class AlertCategory(Enum):
    """Kategorie alertów."""
    SYSTEM = "system"
    CONNECTION = "connection"
    TRADING = "trading"
    PERFORMANCE = "performance"
    SECURITY = "security"

class Alert:
    """Reprezentacja alertu w systemie."""
    
    def __init__(
        self,
        alert_id: int,
        timestamp: datetime,
        level: AlertLevel,
        category: AlertCategory,
        message: str,
        details: Dict[str, Any],
        ea_id: Optional[str] = None,
        source: Optional[str] = None,
        status: AlertStatus = AlertStatus.OPEN,
        auto_resolve_after: Optional[timedelta] = None
    ):
        """Inicjalizuje alert.
        
        Args:
            alert_id: Identyfikator alertu.
            timestamp: Czas wygenerowania alertu.
            level: Poziom alertu.
            category: Kategoria alertu.
            message: Wiadomość alertu.
            details: Szczegóły alertu.
            ea_id: Identyfikator EA, którego dotyczy alert.
            source: Źródło alertu.
            status: Status alertu.
            auto_resolve_after: Czas, po którym alert zostanie automatycznie rozwiązany.
        """
        self.alert_id = alert_id
        self.timestamp = timestamp
        self.level = level
        self.category = category
        self.message = message
        self.details = details
        self.ea_id = ea_id
        self.source = source or "system"
        self.status = status
        self.auto_resolve_after = auto_resolve_after
        self.auto_resolve_time = timestamp + auto_resolve_after if auto_resolve_after else None
        self.resolved_at = None
        self.acknowledged_at = None
        self.acknowledged_by = None
    
    def acknowledge(self, by: str = "system"):
        """Potwierdza alert.
        
        Args:
            by: Kto potwierdził alert.
        """
        self.status = AlertStatus.ACKNOWLEDGED
        self.acknowledged_at = datetime.now()
        self.acknowledged_by = by
    
    def resolve(self, by: str = "system", auto: bool = False):
        """Rozwiązuje alert.
        
        Args:
            by: Kto rozwiązał alert.
            auto: Czy alert został automatycznie rozwiązany.
        """
        self.status = AlertStatus.AUTO_RESOLVED if auto else AlertStatus.RESOLVED
        self.resolved_at = datetime.now()
    
    def should_auto_resolve(self) -> bool:
        """Sprawdza, czy alert powinien zostać automatycznie rozwiązany.
        
        Returns:
            True, jeśli alert powinien zostać automatycznie rozwiązany, False w przeciwnym razie.
        """
        if self.auto_resolve_time and self.status in [AlertStatus.OPEN, AlertStatus.ACKNOWLEDGED]:
            return datetime.now() >= self.auto_resolve_time
        return False
    
    def to_dict(self) -> Dict[str, Any]:
        """Konwertuje alert do słownika.
        
        Returns:
            Słownik z danymi alertu.
        """
        return {
            "alert_id": self.alert_id,
            "timestamp": self.timestamp.isoformat(),
            "level": self.level.name,
            "category": self.category.name,
            "message": self.message,
            "details": self.details,
            "ea_id": self.ea_id,
            "source": self.source,
            "status": self.status.value,
            "auto_resolve_after": str(self.auto_resolve_after) if self.auto_resolve_after else None,
            "auto_resolve_time": self.auto_resolve_time.isoformat() if self.auto_resolve_time else None,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "acknowledged_at": self.acknowledged_at.isoformat() if self.acknowledged_at else None,
            "acknowledged_by": self.acknowledged_by
        }
    
    def to_json(self) -> str:
        """Konwertuje alert do formatu JSON.
        
        Returns:
            Alert w formacie JSON.
        """
        return json.dumps(self.to_dict(), ensure_ascii=False)

class AlertRule:
    """Reguła alertu."""
    
    def __init__(
        self,
        rule_id: str,
        name: str,
        category: AlertCategory,
        level: AlertLevel,
        description: str,
        check_function: Callable[[Dict[str, Any]], bool],
        message_template: str,
        auto_resolve_after: Optional[timedelta] = None,
        parameters: Optional[Dict[str, Any]] = None
    ):
        """Inicjalizuje regułę alertu.
        
        Args:
            rule_id: Identyfikator reguły.
            name: Nazwa reguły.
            category: Kategoria alertu.
            level: Poziom alertu.
            description: Opis reguły.
            check_function: Funkcja sprawdzająca, czy należy wygenerować alert.
            message_template: Szablon wiadomości alertu.
            auto_resolve_after: Czas, po którym alert zostanie automatycznie rozwiązany.
            parameters: Parametry reguły.
        """
        self.rule_id = rule_id
        self.name = name
        self.category = category
        self.level = level
        self.description = description
        self.check_function = check_function
        self.message_template = message_template
        self.auto_resolve_after = auto_resolve_after
        self.parameters = parameters or {}
        self.enabled = True
    
    def check(self, context: Dict[str, Any]) -> bool:
        """Sprawdza, czy należy wygenerować alert.
        
        Args:
            context: Kontekst do sprawdzenia.
            
        Returns:
            True, jeśli należy wygenerować alert, False w przeciwnym razie.
        """
        if not self.enabled:
            return False
        
        try:
            return self.check_function(context, self.parameters)
        except Exception as e:
            # Logowanie błędu w check_function
            get_logger().error(
                "SYSTEM",
                OperationType.SYSTEM,
                OperationStatus.FAILED,
                {"error": str(e), "rule_id": self.rule_id},
                f"Error in alert rule check function: {e}"
            )
            return False
    
    def get_message(self, context: Dict[str, Any]) -> str:
        """Generuje wiadomość alertu na podstawie szablonu.
        
        Args:
            context: Kontekst alertu.
            
        Returns:
            Wiadomość alertu.
        """
        try:
            return self.message_template.format(**context)
        except Exception as e:
            # Logowanie błędu w formatowaniu wiadomości
            get_logger().error(
                "SYSTEM",
                OperationType.SYSTEM,
                OperationStatus.FAILED,
                {"error": str(e), "rule_id": self.rule_id, "template": self.message_template},
                f"Error in alert message formatting: {e}"
            )
            return f"Alert from rule {self.rule_id}: {self.name}"

class AlertManager:
    """Klasa do zarządzania alertami w systemie AgentMT5."""
    
    def __init__(self, check_interval: int = 30, max_alerts: int = 1000):
        """Inicjalizuje menedżera alertów.
        
        Args:
            check_interval: Interwał sprawdzania reguł alertów (w sekundach).
            max_alerts: Maksymalna liczba alertów w pamięci.
        """
        self.rules: Dict[str, AlertRule] = {}
        self.alerts: List[Alert] = []
        self.next_alert_id = 1
        self.check_interval = check_interval
        self.max_alerts = max_alerts
        
        self.rules_lock = threading.Lock()
        self.alerts_lock = threading.Lock()
        
        # Callbacks dla alertów
        self.alert_callbacks: List[Callable[[Alert], None]] = []
        
        # Logger
        self.logger = get_logger()
        
        # Uruchomienie wątku sprawdzającego auto-rozwiązywanie alertów
        self.auto_resolve_thread = threading.Thread(target=self._auto_resolve_checker, daemon=True)
        self.auto_resolve_thread.start()
    
    def add_rule(self, rule: AlertRule) -> str:
        """Dodaje nową regułę alertu.
        
        Args:
            rule: Reguła alertu.
            
        Returns:
            Identyfikator reguły.
        """
        with self.rules_lock:
            self.rules[rule.rule_id] = rule
        return rule.rule_id
    
    def remove_rule(self, rule_id: str) -> bool:
        """Usuwa regułę alertu.
        
        Args:
            rule_id: Identyfikator reguły.
            
        Returns:
            True, jeśli reguła została usunięta, False w przeciwnym razie.
        """
        with self.rules_lock:
            if rule_id in self.rules:
                del self.rules[rule_id]
                return True
        return False
    
    def enable_rule(self, rule_id: str, enabled: bool = True) -> bool:
        """Włącza lub wyłącza regułę alertu.
        
        Args:
            rule_id: Identyfikator reguły.
            enabled: Czy reguła ma być włączona.
            
        Returns:
            True, jeśli reguła została zmodyfikowana, False w przeciwnym razie.
        """
        with self.rules_lock:
            if rule_id in self.rules:
                self.rules[rule_id].enabled = enabled
                return True
        return False
    
    def create_alert(
        self,
        level: AlertLevel,
        category: AlertCategory,
        message: str,
        details: Dict[str, Any],
        ea_id: Optional[str] = None,
        source: Optional[str] = None,
        auto_resolve_after: Optional[timedelta] = None
    ) -> Alert:
        """Tworzy nowy alert.
        
        Args:
            level: Poziom alertu.
            category: Kategoria alertu.
            message: Wiadomość alertu.
            details: Szczegóły alertu.
            ea_id: Identyfikator EA, którego dotyczy alert.
            source: Źródło alertu.
            auto_resolve_after: Czas, po którym alert zostanie automatycznie rozwiązany.
            
        Returns:
            Utworzony alert.
        """
        with self.alerts_lock:
            alert_id = self.next_alert_id
            self.next_alert_id += 1
            
            alert = Alert(
                alert_id=alert_id,
                timestamp=datetime.now(),
                level=level,
                category=category,
                message=message,
                details=details,
                ea_id=ea_id,
                source=source,
                auto_resolve_after=auto_resolve_after
            )
            
            self.alerts.append(alert)
            
            # Ograniczenie liczby alertów w pamięci
            if len(self.alerts) > self.max_alerts:
                self.alerts = self.alerts[-self.max_alerts:]
        
        # Logowanie alertu
        log_level = LogLevel.INFO
        if level == AlertLevel.WARNING:
            log_level = LogLevel.WARNING
        elif level == AlertLevel.ERROR:
            log_level = LogLevel.ERROR
        elif level == AlertLevel.CRITICAL:
            log_level = LogLevel.CRITICAL
        
        self.logger.log(
            log_level,
            ea_id or "SYSTEM",
            OperationType.SYSTEM,
            OperationStatus.FAILED,
            {"alert_id": alert_id, "category": category.name, "details": details},
            message
        )
        
        # Wywołanie callbacków
        for callback in self.alert_callbacks:
            try:
                callback(alert)
            except Exception as e:
                self.logger.error(
                    "SYSTEM",
                    OperationType.SYSTEM,
                    OperationStatus.FAILED,
                    {"error": str(e), "alert_id": alert_id},
                    f"Error in alert callback: {e}"
                )
        
        return alert
    
    def acknowledge_alert(self, alert_id: int, by: str = "system") -> bool:
        """Potwierdza alert.
        
        Args:
            alert_id: Identyfikator alertu.
            by: Kto potwierdził alert.
            
        Returns:
            True, jeśli alert został potwierdzony, False w przeciwnym razie.
        """
        with self.alerts_lock:
            for alert in self.alerts:
                if alert.alert_id == alert_id and alert.status == AlertStatus.OPEN:
                    alert.acknowledge(by)
                    return True
        return False
    
    def resolve_alert(self, alert_id: int, by: str = "system") -> bool:
        """Rozwiązuje alert.
        
        Args:
            alert_id: Identyfikator alertu.
            by: Kto rozwiązał alert.
            
        Returns:
            True, jeśli alert został rozwiązany, False w przeciwnym razie.
        """
        with self.alerts_lock:
            for alert in self.alerts:
                if alert.alert_id == alert_id and alert.status in [AlertStatus.OPEN, AlertStatus.ACKNOWLEDGED]:
                    alert.resolve(by)
                    return True
        return False
    
    def get_alert(self, alert_id: int) -> Optional[Dict[str, Any]]:
        """Pobiera informacje o alercie.
        
        Args:
            alert_id: Identyfikator alertu.
            
        Returns:
            Słownik z danymi alertu lub None, jeśli alert nie istnieje.
        """
        with self.alerts_lock:
            for alert in self.alerts:
                if alert.alert_id == alert_id:
                    return alert.to_dict()
        return None
    
    def get_alerts(
        self,
        level: Optional[AlertLevel] = None,
        category: Optional[AlertCategory] = None,
        status: Optional[AlertStatus] = None,
        ea_id: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Pobiera informacje o alertach z możliwością filtrowania.
        
        Args:
            level: Filtrowanie po poziomie alertu.
            category: Filtrowanie po kategorii alertu.
            status: Filtrowanie po statusie alertu.
            ea_id: Filtrowanie po identyfikatorze EA.
            start_time: Początkowy timestamp.
            end_time: Końcowy timestamp.
            limit: Maksymalna liczba zwracanych alertów.
            
        Returns:
            Lista słowników z danymi alertów.
        """
        with self.alerts_lock:
            filtered_alerts = self.alerts.copy()
        
        # Filtrowanie
        if level:
            filtered_alerts = [a for a in filtered_alerts if a.level == level]
        if category:
            filtered_alerts = [a for a in filtered_alerts if a.category == category]
        if status:
            filtered_alerts = [a for a in filtered_alerts if a.status == status]
        if ea_id:
            filtered_alerts = [a for a in filtered_alerts if a.ea_id == ea_id]
        if start_time:
            filtered_alerts = [a for a in filtered_alerts if a.timestamp >= start_time]
        if end_time:
            filtered_alerts = [a for a in filtered_alerts if a.timestamp <= end_time]
        
        # Sortowanie od najnowszych do najstarszych
        filtered_alerts.sort(key=lambda a: a.timestamp, reverse=True)
        
        # Ograniczenie liczby alertów
        if limit and len(filtered_alerts) > limit:
            filtered_alerts = filtered_alerts[:limit]
        
        return [alert.to_dict() for alert in filtered_alerts]
    
    def add_alert_callback(self, callback: Callable[[Alert], None]):
        """Dodaje callback wywoływany, gdy zostanie wygenerowany nowy alert.
        
        Args:
            callback: Funkcja przyjmująca alert jako argument.
        """
        self.alert_callbacks.append(callback)
    
    def check_rules(self, context: Dict[str, Any], rule_ids: Optional[List[str]] = None):
        """Sprawdza reguły alertów.
        
        Args:
            context: Kontekst do sprawdzenia.
            rule_ids: Lista identyfikatorów reguł do sprawdzenia (None oznacza wszystkie).
        """
        rules_to_check = []
        
        with self.rules_lock:
            if rule_ids:
                rules_to_check = [self.rules[rule_id] for rule_id in rule_ids if rule_id in self.rules]
            else:
                rules_to_check = list(self.rules.values())
        
        for rule in rules_to_check:
            if rule.check(context):
                message = rule.get_message(context)
                self.create_alert(
                    level=rule.level,
                    category=rule.category,
                    message=message,
                    details=context,
                    ea_id=context.get("ea_id"),
                    source=f"rule:{rule.rule_id}",
                    auto_resolve_after=rule.auto_resolve_after
                )
    
    def _auto_resolve_checker(self):
        """Wątek sprawdzający auto-rozwiązywanie alertów."""
        while True:
            with self.alerts_lock:
                for alert in self.alerts:
                    if alert.should_auto_resolve():
                        alert.resolve(auto=True)
                        self.logger.info(
                            alert.ea_id or "SYSTEM",
                            OperationType.SYSTEM,
                            OperationStatus.SUCCESS,
                            {"alert_id": alert.alert_id},
                            f"Alert auto-resolved: {alert.message}"
                        )
            
            # Oczekiwanie na następne sprawdzenie
            time.sleep(self.check_interval)

# Singleton instance
_instance = None
_instance_lock = threading.Lock()

def get_alert_manager() -> AlertManager:
    """Zwraca singleton instancję AlertManager."""
    global _instance
    if _instance is None:
        with _instance_lock:
            if _instance is None:
                _instance = AlertManager()
    return _instance

# Wstępnie zdefiniowane reguły alertów

def create_inactive_connection_rule() -> AlertRule:
    """Tworzy regułę dla nieaktywnego połączenia."""
    
    def check_inactive_connection(context: Dict[str, Any], parameters: Dict[str, Any]) -> bool:
        if "status" not in context or "inactive_since" not in context:
            return False
        
        status = context["status"]
        inactive_str = context["inactive_since"]
        
        if status != "inactive":
            return False
        
        # Parsowanie inactive_since w formacie timedelta
        try:
            inactive_parts = inactive_str.split(":")
            if len(inactive_parts) >= 3:
                hours = int(inactive_parts[0])
                minutes = int(inactive_parts[1])
                seconds = float(inactive_parts[2])
                
                total_minutes = hours * 60 + minutes + seconds / 60
                threshold = parameters.get("threshold_minutes", 10)
                
                return total_minutes >= threshold
        except Exception:
            return False
        
        return False
    
    return AlertRule(
        rule_id="inactive_connection",
        name="Inactive Connection",
        category=AlertCategory.CONNECTION,
        level=AlertLevel.WARNING,
        description="Alert when connection is inactive for too long",
        check_function=check_inactive_connection,
        message_template="Connection with EA {ea_id} is inactive for {inactive_since}",
        auto_resolve_after=timedelta(minutes=30),
        parameters={"threshold_minutes": 10}
    )

def create_failed_operation_rule() -> AlertRule:
    """Tworzy regułę dla nieudanej operacji handlowej."""
    
    def check_failed_operation(context: Dict[str, Any], parameters: Dict[str, Any]) -> bool:
        if "status" not in context or "operation_type" not in context:
            return False
        
        status = context["status"]
        operation_type = context["operation_type"]
        
        if status != "FAILED":
            return False
        
        # Sprawdzenie typu operacji
        trading_operations = ["OPEN_POSITION", "CLOSE_POSITION", "MODIFY_POSITION"]
        return operation_type in trading_operations
    
    return AlertRule(
        rule_id="failed_operation",
        name="Failed Trading Operation",
        category=AlertCategory.TRADING,
        level=AlertLevel.ERROR,
        description="Alert when trading operation fails",
        check_function=check_failed_operation,
        message_template="Trading operation {operation_type} failed for EA {ea_id}",
        auto_resolve_after=timedelta(hours=1),
        parameters={}
    )

def initialize_default_rules():
    """Inicjalizuje domyślne reguły alertów."""
    manager = get_alert_manager()
    
    manager.add_rule(create_inactive_connection_rule())
    manager.add_rule(create_failed_operation_rule())
    
    return manager 