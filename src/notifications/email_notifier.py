#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
EmailNotifier - klasa odpowiedzialna za wysyłanie powiadomień email w systemie AgentMT5.
"""

import logging
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, List, Any, Optional, Union
from datetime import datetime

from src.notifications.notification_manager import NotificationType

logger = logging.getLogger(__name__)

class EmailNotifier:
    """Klasa odpowiedzialna za wysyłanie powiadomień email."""
    
    def __init__(
        self,
        smtp_server: str,
        smtp_port: int,
        username: str,
        password: str,
        sender_email: str,
        recipient_emails: List[str],
        use_ssl: bool = True,
        use_tls: bool = False
    ):
        """Inicjalizuje narzędzie do wysyłania powiadomień email.
        
        Args:
            smtp_server: Adres serwera SMTP.
            smtp_port: Port serwera SMTP.
            username: Nazwa użytkownika do logowania na serwer SMTP.
            password: Hasło do logowania na serwer SMTP.
            sender_email: Adres email nadawcy.
            recipient_emails: Lista adresów email odbiorców.
            use_ssl: Czy używać SSL do połączenia z serwerem SMTP.
            use_tls: Czy używać TLS do połączenia z serwerem SMTP.
        """
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.username = username
        self.password = password
        self.sender_email = sender_email
        self.recipient_emails = recipient_emails
        self.use_ssl = use_ssl
        self.use_tls = use_tls
        
        logger.info(f"EmailNotifier initialized with SMTP server {smtp_server}:{smtp_port}")
    
    def send_notification(
        self,
        notification_type: NotificationType,
        subject: str,
        message: str,
        details: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Wysyła powiadomienie email.
        
        Args:
            notification_type: Typ powiadomienia.
            subject: Temat wiadomości.
            message: Treść wiadomości.
            details: Dodatkowe szczegóły (opcjonalne).
            
        Returns:
            True jeśli powiadomienie zostało wysłane pomyślnie.
        """
        if not self.recipient_emails:
            logger.warning("No recipients specified for email notification")
            return False
        
        # Dodanie prefiksu do tematu zależnie od typu powiadomienia
        prefix = self._get_subject_prefix(notification_type)
        if prefix:
            subject = f"{prefix} {subject}"
        
        # Utworzenie wiadomości email
        email_message = MIMEMultipart()
        email_message["Subject"] = subject
        email_message["From"] = self.sender_email
        email_message["To"] = ", ".join(self.recipient_emails)
        
        # Dodanie treści wiadomości
        email_message.attach(MIMEText(message, "plain"))
        
        try:
            # Połączenie z serwerem SMTP
            if self.use_ssl:
                context = ssl.create_default_context()
                server = smtplib.SMTP_SSL(self.smtp_server, self.smtp_port, context=context)
            else:
                server = smtplib.SMTP(self.smtp_server, self.smtp_port)
                if self.use_tls:
                    server.starttls()
            
            # Logowanie do serwera SMTP
            server.login(self.username, self.password)
            
            # Wysłanie wiadomości
            server.sendmail(self.sender_email, self.recipient_emails, email_message.as_string())
            
            # Zamknięcie połączenia
            server.quit()
            
            logger.info(f"Email notification sent to {len(self.recipient_emails)} recipients")
            return True
        except Exception as e:
            logger.error(f"Error sending email notification: {str(e)}")
            return False
    
    def _get_subject_prefix(self, notification_type: NotificationType) -> str:
        """Zwraca prefiks tematu wiadomości zależnie od typu powiadomienia.
        
        Args:
            notification_type: Typ powiadomienia.
            
        Returns:
            Prefiks tematu wiadomości.
        """
        prefixes = {
            NotificationType.NEW_SIGNAL: "🔔 [AgentMT5]",
            NotificationType.SIGNAL_EXPIRED: "⌛ [AgentMT5]",
            NotificationType.SIGNAL_EXECUTED: "✅ [AgentMT5]",
            NotificationType.ERROR: "❌ [AgentMT5]",
            NotificationType.WARNING: "⚠️ [AgentMT5]",
            NotificationType.SYSTEM: "🔧 [AgentMT5]",
            NotificationType.BALANCE_CHANGE: "💰 [AgentMT5]",
            NotificationType.POSITION_OPENED: "📈 [AgentMT5]",
            NotificationType.POSITION_CLOSED: "📉 [AgentMT5]"
        }
        return prefixes.get(notification_type, "[AgentMT5]")
    
    @classmethod
    def from_config(cls, config: Dict[str, Any]) -> 'EmailNotifier':
        """Tworzy instancję EmailNotifier na podstawie konfiguracji.
        
        Args:
            config: Słownik z konfiguracją.
            
        Returns:
            Instancja EmailNotifier.
            
        Raises:
            ValueError: Gdy brakuje wymaganych pól konfiguracji.
        """
        required_fields = [
            'smtp_server', 'smtp_port', 'username', 
            'password', 'sender_email', 'recipient_emails'
        ]
        
        for field in required_fields:
            if field not in config:
                raise ValueError(f"Missing required field in email configuration: {field}")
        
        return cls(
            smtp_server=config['smtp_server'],
            smtp_port=config['smtp_port'],
            username=config['username'],
            password=config['password'],
            sender_email=config['sender_email'],
            recipient_emails=config['recipient_emails'],
            use_ssl=config.get('use_ssl', True),
            use_tls=config.get('use_tls', False)
        ) 