#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
NotificationManager - klasa odpowiedzialna za zarządzanie powiadomieniami w systemie AgentMT5.
Wspiera różne typy powiadomień i kanały komunikacji (email, Discord).
"""

import threading
import logging
from enum import Enum
from typing import Dict, List, Any, Optional, Callable, Union
from datetime import datetime

from src.database.models import TradingSignal

logger = logging.getLogger(__name__)

class NotificationType(Enum):
    """Typy powiadomień obsługiwane przez system."""
    NEW_SIGNAL = "new_signal"
    SIGNAL_EXPIRED = "signal_expired"
    SIGNAL_EXECUTED = "signal_executed"
    ERROR = "error"
    WARNING = "warning"
    SYSTEM = "system"
    BALANCE_CHANGE = "balance_change"
    POSITION_OPENED = "position_opened"
    POSITION_CLOSED = "position_closed"

class NotificationManager:
    """Zarządza powiadomieniami w systemie AgentMT5."""
    
    def __init__(self):
        """Inicjalizuje menedżera powiadomień."""
        self.notifiers = {}
        self.enabled_notifiers = set()
        self.enabled_types = set()
        self.lock = threading.Lock()
        logger.info("NotificationManager initialized")
    
    def register_notifier(self, notifier_id: str, notifier: Any) -> bool:
        """Rejestruje nowe narzędzie do wysyłania powiadomień.
        
        Args:
            notifier_id: Unikalny identyfikator narzędzia.
            notifier: Obiekt implementujący metodę send_notification.
            
        Returns:
            True jeśli rejestracja powiodła się, False w przeciwnym razie.
        """
        with self.lock:
            if notifier_id in self.notifiers:
                logger.warning(f"Notifier with ID {notifier_id} already registered")
                return False
            
            # Sprawdzanie, czy notifier ma wymaganą metodę
            if not hasattr(notifier, 'send_notification'):
                logger.error(f"Notifier {notifier_id} does not have send_notification method")
                return False
            
            self.notifiers[notifier_id] = notifier
            logger.info(f"Registered notifier: {notifier_id}")
            return True
    
    def enable_notifier(self, notifier_id: str) -> bool:
        """Włącza narzędzie do wysyłania powiadomień.
        
        Args:
            notifier_id: Identyfikator narzędzia.
            
        Returns:
            True jeśli operacja powiodła się, False w przeciwnym razie.
        """
        with self.lock:
            if notifier_id not in self.notifiers:
                logger.warning(f"Cannot enable unknown notifier: {notifier_id}")
                return False
            
            self.enabled_notifiers.add(notifier_id)
            logger.info(f"Enabled notifier: {notifier_id}")
            return True
    
    def disable_notifier(self, notifier_id: str) -> bool:
        """Wyłącza narzędzie do wysyłania powiadomień.
        
        Args:
            notifier_id: Identyfikator narzędzia.
            
        Returns:
            True jeśli operacja powiodła się, False w przeciwnym razie.
        """
        with self.lock:
            if notifier_id not in self.notifiers:
                logger.warning(f"Cannot disable unknown notifier: {notifier_id}")
                return False
            
            if notifier_id in self.enabled_notifiers:
                self.enabled_notifiers.remove(notifier_id)
                logger.info(f"Disabled notifier: {notifier_id}")
            return True
    
    def enable_notification_type(self, notification_type: NotificationType) -> None:
        """Włącza wysyłanie powiadomień określonego typu.
        
        Args:
            notification_type: Typ powiadomień do włączenia.
        """
        with self.lock:
            self.enabled_types.add(notification_type)
            logger.info(f"Enabled notification type: {notification_type.value}")
    
    def disable_notification_type(self, notification_type: NotificationType) -> None:
        """Wyłącza wysyłanie powiadomień określonego typu.
        
        Args:
            notification_type: Typ powiadomień do wyłączenia.
        """
        with self.lock:
            if notification_type in self.enabled_types:
                self.enabled_types.remove(notification_type)
                logger.info(f"Disabled notification type: {notification_type.value}")
    
    def send_notification(self, 
                          notification_type: NotificationType, 
                          subject: str, 
                          message: str, 
                          details: Optional[Dict[str, Any]] = None) -> bool:
        """Wysyła powiadomienie za pomocą wszystkich włączonych narzędzi.
        
        Args:
            notification_type: Typ powiadomienia.
            subject: Temat powiadomienia.
            message: Treść powiadomienia.
            details: Dodatkowe szczegóły (opcjonalne).
            
        Returns:
            True jeśli powiadomienie zostało wysłane przez co najmniej jedno narzędzie.
        """
        if not details:
            details = {}
            
        with self.lock:
            # Sprawdzenie, czy typ powiadomienia jest włączony
            if notification_type not in self.enabled_types:
                logger.debug(f"Notification type {notification_type.value} is disabled")
                return False
            
            if not self.enabled_notifiers:
                logger.warning("No enabled notifiers to send notification")
                return False
            
            success = False
            for notifier_id in self.enabled_notifiers:
                notifier = self.notifiers[notifier_id]
                try:
                    result = notifier.send_notification(notification_type, subject, message, details)
                    if result:
                        success = True
                        logger.debug(f"Notification sent via {notifier_id}")
                    else:
                        logger.warning(f"Failed to send notification via {notifier_id}")
                except Exception as e:
                    logger.error(f"Error sending notification via {notifier_id}: {str(e)}")
            
            return success
    
    def notify_new_signal(self, signal: TradingSignal) -> bool:
        """Wysyła powiadomienie o nowym sygnale handlowym.
        
        Args:
            signal: Obiekt TradingSignal reprezentujący nowy sygnał.
            
        Returns:
            True jeśli powiadomienie zostało wysłane pomyślnie.
        """
        direction = signal.direction.upper()
        symbol = signal.symbol
        timeframe = signal.timeframe
        confidence = signal.confidence
        
        subject = f"Nowy sygnał {direction} dla {symbol} ({timeframe})"
        message = (
            f"Wygenerowano nowy sygnał handlowy:\n"
            f"- Instrument: {symbol}\n"
            f"- Kierunek: {direction}\n"
            f"- Rama czasowa: {timeframe}\n"
            f"- Pewność: {confidence:.2f}\n"
            f"- Cena wejścia: {signal.entry_price:.5f}\n"
            f"- Stop Loss: {signal.stop_loss:.5f}\n"
            f"- Take Profit: {signal.take_profit:.5f}\n"
            f"- Czas wygenerowania: {signal.created_at}\n"
        )
        
        if signal.ai_analysis:
            message += f"\nAnaliza AI:\n{signal.ai_analysis}"
        
        return self.send_notification(
            NotificationType.NEW_SIGNAL,
            subject,
            message,
            {
                "signal_id": signal.id,
                "symbol": signal.symbol,
                "direction": signal.direction,
                "timeframe": signal.timeframe,
                "confidence": signal.confidence,
                "entry_price": signal.entry_price,
                "stop_loss": signal.stop_loss,
                "take_profit": signal.take_profit,
                "created_at": signal.created_at.isoformat() if signal.created_at else None
            }
        )

# Singleton instance
_instance = None
_instance_lock = threading.Lock()

def get_notification_manager() -> NotificationManager:
    """Zwraca singleton instancję NotificationManager."""
    global _instance
    if _instance is None:
        with _instance_lock:
            if _instance is None:
                _instance = NotificationManager()
    return _instance 