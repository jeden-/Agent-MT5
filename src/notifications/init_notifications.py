#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Inicjalizacja systemu powiadomień dla AgentMT5.
Ten moduł odpowiada za wczytanie konfiguracji i inicjalizację systemu powiadomień.
"""

import os
import yaml
import logging
from typing import Dict, Any, Optional

from src.notifications.notification_manager import get_notification_manager, NotificationType
from src.notifications.email_notifier import EmailNotifier
from src.notifications.discord_notifier import DiscordNotifier

logger = logging.getLogger(__name__)

def load_notifications_config() -> Dict[str, Any]:
    """
    Wczytuje konfigurację powiadomień z pliku YAML.
    
    Returns:
        Dict[str, Any]: Konfiguracja powiadomień
    """
    config_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        'src',
        'config',
        'notifications_config.yaml'
    )
    
    # Sprawdzenie, czy plik konfiguracyjny istnieje
    if not os.path.exists(config_path):
        logger.warning(f"Plik konfiguracyjny powiadomień nie istnieje: {config_path}")
        return {}
    
    try:
        with open(config_path, 'r', encoding='utf-8') as file:
            config = yaml.safe_load(file)
        logger.info("Konfiguracja powiadomień wczytana pomyślnie")
        return config
    except Exception as e:
        logger.error(f"Błąd podczas wczytywania konfiguracji powiadomień: {e}")
        return {}

def init_notifications() -> bool:
    """
    Inicjalizuje system powiadomień na podstawie konfiguracji.
    
    Returns:
        bool: True jeśli inicjalizacja powiodła się, False w przeciwnym razie
    """
    config = load_notifications_config()
    if not config:
        logger.warning("Nie udało się zainicjalizować systemu powiadomień z powodu braku konfiguracji")
        return False
    
    notification_manager = get_notification_manager()
    success = True
    
    # Włączanie typów powiadomień
    enabled_types = config.get('enabled_notification_types', [])
    for notification_type_name in enabled_types:
        try:
            notification_type = NotificationType(notification_type_name)
            notification_manager.enable_notification_type(notification_type)
            logger.info(f"Włączono typ powiadomień: {notification_type_name}")
        except ValueError:
            logger.warning(f"Nieznany typ powiadomień: {notification_type_name}")
    
    # Inicjalizacja powiadomień email
    email_config = config.get('email', {})
    if email_config.get('enabled', False):
        try:
            email_notifier = EmailNotifier.from_config(email_config)
            if notification_manager.register_notifier('email', email_notifier):
                notification_manager.enable_notifier('email')
                logger.info("Włączono powiadomienia email")
        except Exception as e:
            logger.error(f"Błąd podczas inicjalizacji powiadomień email: {e}")
            success = False
    
    # Inicjalizacja powiadomień Discord
    discord_config = config.get('discord', {})
    if discord_config.get('enabled', False):
        try:
            discord_notifier = DiscordNotifier.from_config(discord_config)
            if notification_manager.register_notifier('discord', discord_notifier):
                notification_manager.enable_notifier('discord')
                logger.info("Włączono powiadomienia Discord")
        except Exception as e:
            logger.error(f"Błąd podczas inicjalizacji powiadomień Discord: {e}")
            success = False
    
    return success 