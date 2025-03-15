#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Moduł notifications - zawiera klasy i funkcje odpowiedzialne za wysyłanie powiadomień
o nowych sygnałach handlowych i innych ważnych wydarzeniach w systemie AgentMT5.
"""

from src.notifications.email_notifier import EmailNotifier
from src.notifications.discord_notifier import DiscordNotifier
from src.notifications.notification_manager import NotificationManager, NotificationType

__all__ = [
    'EmailNotifier',
    'DiscordNotifier',
    'NotificationManager',
    'NotificationType'
] 