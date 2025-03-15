#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
DiscordNotifier - klasa odpowiedzialna za wysyłanie powiadomień na Discord w systemie AgentMT5.
"""

import json
import logging
import requests
from typing import Dict, List, Any, Optional, Union
from datetime import datetime

from src.notifications.notification_manager import NotificationType

logger = logging.getLogger(__name__)

class DiscordNotifier:
    """Klasa odpowiedzialna za wysyłanie powiadomień na Discord."""
    
    def __init__(
        self,
        webhook_url: str,
        username: str = "AgentMT5",
        avatar_url: Optional[str] = None
    ):
        """Inicjalizuje narzędzie do wysyłania powiadomień na Discord.
        
        Args:
            webhook_url: URL webhooka Discord.
            username: Nazwa użytkownika wyświetlana na Discord.
            avatar_url: URL do avatara użytkownika (opcjonalne).
        """
        self.webhook_url = webhook_url
        self.username = username
        self.avatar_url = avatar_url
        
        logger.info(f"DiscordNotifier initialized with webhook URL")
    
    def send_notification(
        self,
        notification_type: NotificationType,
        subject: str,
        message: str,
        details: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Wysyła powiadomienie na Discord.
        
        Args:
            notification_type: Typ powiadomienia.
            subject: Temat wiadomości.
            message: Treść wiadomości.
            details: Dodatkowe szczegóły (opcjonalne).
            
        Returns:
            True jeśli powiadomienie zostało wysłane pomyślnie.
        """
        # Przygotowanie danych do wysłania
        color = self._get_color_for_type(notification_type)
        emoji = self._get_emoji_for_type(notification_type)
        
        # Przygotowanie pełnego tytułu wiadomości z emoji
        title = f"{emoji} {subject}"
        
        # Przygotowanie pól do embedu
        fields = self._prepare_fields(details) if details else []
        
        # Przygotowanie wiadomości Discord
        payload = {
            "username": self.username,
            "embeds": [
                {
                    "title": title,
                    "description": message,
                    "color": color,
                    "fields": fields,
                    "footer": {
                        "text": f"AgentMT5 | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                    }
                }
            ]
        }
        
        # Dodanie avatara, jeśli podany
        if self.avatar_url:
            payload["avatar_url"] = self.avatar_url
        
        try:
            # Wysłanie żądania do webhooka Discord
            response = requests.post(
                self.webhook_url,
                data=json.dumps(payload),
                headers={"Content-Type": "application/json"}
            )
            
            # Sprawdzenie odpowiedzi
            if response.status_code == 204:
                logger.info("Discord notification sent successfully")
                return True
            else:
                logger.error(f"Failed to send Discord notification. Status code: {response.status_code}, Response: {response.text}")
                return False
        except Exception as e:
            logger.error(f"Error sending Discord notification: {str(e)}")
            return False
    
    def _prepare_fields(self, details: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Przygotowuje pola do embedu Discord.
        
        Args:
            details: Szczegóły do przetworzenia na pola.
            
        Returns:
            Lista pól do embedu.
        """
        fields = []
        
        # Konwersja szczegółów na pola embedu
        for key, value in details.items():
            # Pomijanie niektórych detali, które nie są przydatne w polach
            if key in ['created_at', 'id', 'signal_id']:
                continue
                
            # Formatowanie wartości
            if isinstance(value, float):
                value = f"{value:.5f}"
            elif value is None:
                value = "N/A"
            else:
                value = str(value)
            
            # Dodanie pola
            fields.append({
                "name": key.replace('_', ' ').title(),
                "value": value,
                "inline": True
            })
        
        return fields
    
    def _get_emoji_for_type(self, notification_type: NotificationType) -> str:
        """Zwraca emoji dla typu powiadomienia.
        
        Args:
            notification_type: Typ powiadomienia.
            
        Returns:
            Emoji odpowiadające typowi powiadomienia.
        """
        emojis = {
            NotificationType.NEW_SIGNAL: "🔔",
            NotificationType.SIGNAL_EXPIRED: "⌛",
            NotificationType.SIGNAL_EXECUTED: "✅",
            NotificationType.ERROR: "❌",
            NotificationType.WARNING: "⚠️",
            NotificationType.SYSTEM: "🔧",
            NotificationType.BALANCE_CHANGE: "💰",
            NotificationType.POSITION_OPENED: "📈",
            NotificationType.POSITION_CLOSED: "📉"
        }
        return emojis.get(notification_type, "🤖")
    
    def _get_color_for_type(self, notification_type: NotificationType) -> int:
        """Zwraca kolor dla typu powiadomienia.
        
        Args:
            notification_type: Typ powiadomienia.
            
        Returns:
            Kod koloru w formacie Discord.
        """
        colors = {
            NotificationType.NEW_SIGNAL: 0x3498DB,  # Niebieski
            NotificationType.SIGNAL_EXPIRED: 0x95A5A6,  # Szary
            NotificationType.SIGNAL_EXECUTED: 0x2ECC71,  # Zielony
            NotificationType.ERROR: 0xE74C3C,  # Czerwony
            NotificationType.WARNING: 0xF39C12,  # Pomarańczowy
            NotificationType.SYSTEM: 0x9B59B6,  # Fioletowy
            NotificationType.BALANCE_CHANGE: 0xF1C40F,  # Żółty
            NotificationType.POSITION_OPENED: 0x2ECC71,  # Zielony
            NotificationType.POSITION_CLOSED: 0x3498DB  # Niebieski
        }
        return colors.get(notification_type, 0x7289DA)  # Domyślny kolor Discord
    
    @classmethod
    def from_config(cls, config: Dict[str, Any]) -> 'DiscordNotifier':
        """Tworzy instancję DiscordNotifier na podstawie konfiguracji.
        
        Args:
            config: Słownik z konfiguracją.
            
        Returns:
            Instancja DiscordNotifier.
            
        Raises:
            ValueError: Gdy brakuje wymaganych pól konfiguracji.
        """
        if 'webhook_url' not in config:
            raise ValueError("Missing required field in Discord configuration: webhook_url")
        
        return cls(
            webhook_url=config['webhook_url'],
            username=config.get('username', 'AgentMT5'),
            avatar_url=config.get('avatar_url')
        ) 