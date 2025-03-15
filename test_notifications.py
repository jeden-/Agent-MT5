#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Skrypt testowy do sprawdzenia działania systemu powiadomień.
"""

import os
import sys
import logging
import yaml
import random
from datetime import datetime, timedelta

# Dodanie głównego katalogu projektu do PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

# Import i konfiguracja systemu logowania
from src.utils.logging_config import configure_logging

# Konfiguracja loggera z zapisem do pliku
configure_logging(log_level=logging.INFO)
logger = logging.getLogger(__name__)

# Import klas systemu powiadomień
from src.notifications.notification_manager import get_notification_manager, NotificationType
from src.notifications.email_notifier import EmailNotifier
from src.notifications.discord_notifier import DiscordNotifier
from src.notifications.init_notifications import init_notifications
from src.database.models import TradingSignal

def setup_test_environment():
    """Konfiguracja środowiska testowego"""
    logger.info("Konfiguracja środowiska testowego dla powiadomień")
    
    # Tworzymy tymczasowy plik konfiguracyjny
    config_dir = os.path.join(os.path.dirname(__file__), 'src', 'config')
    os.makedirs(config_dir, exist_ok=True)
    
    config_path = os.path.join(config_dir, 'notifications_config.yaml')
    
    # Konfiguracja testowa
    test_config = {
        'enabled_notification_types': [
            'new_signal',
            'signal_executed',
            'error',
            'warning'
        ],
        'email': {
            'enabled': False,  # W teście nie wysyłamy prawdziwych emaili
            'smtp_server': 'smtp.test.com',
            'smtp_port': 587,
            'username': 'test@example.com',
            'password': 'test-password',
            'sender_email': 'agentmt5@test.com',
            'recipient_emails': ['recipient@test.com'],
            'use_ssl': False,
            'use_tls': True
        },
        'discord': {
            'enabled': False,  # W teście nie wysyłamy prawdziwych powiadomień Discord
            'webhook_url': 'https://discord.com/api/webhooks/test',
            'username': 'AgentMT5-Test',
            'avatar_url': None
        },
        'general': {
            'include_ai_analysis': True,
            'max_analysis_length': 500,
            'include_charts': False
        }
    }
    
    with open(config_path, 'w', encoding='utf-8') as file:
        yaml.dump(test_config, file, default_flow_style=False)
    
    logger.info(f"Tymczasowy plik konfiguracyjny utworzony: {config_path}")
    
    # Inicjalizacja systemu powiadomień
    init_notifications()
    
    # Rejestracja testowego notyfikatora
    notification_manager = get_notification_manager()
    
    class TestNotifier:
        def send_notification(self, notification_type, subject, message, details=None):
            logger.info(f"TEST POWIADOMIENIA:")
            logger.info(f"Typ: {notification_type.value}")
            logger.info(f"Temat: {subject}")
            logger.info(f"Wiadomość: {message}")
            if details:
                logger.info(f"Szczegóły: {details}")
            return True
    
    notification_manager.register_notifier('test', TestNotifier())
    notification_manager.enable_notifier('test')
    
    # Włączenie wszystkich typów powiadomień
    for notification_type in NotificationType:
        notification_manager.enable_notification_type(notification_type)
    
    logger.info("Środowisko testowe skonfigurowane")

def create_test_signal():
    """Tworzy testowy sygnał handlowy"""
    symbols = ["EURUSD", "GBPUSD", "USDJPY", "GOLD", "SILVER"]
    timeframes = ["M1", "M5", "M15", "H1", "D1"]
    directions = ["BUY", "SELL"]
    
    current_price = 1.1 + random.random() * 0.1
    
    signal = TradingSignal(
        id=1,  # Testowy ID
        symbol=random.choice(symbols),
        timeframe=random.choice(timeframes),
        direction=random.choice(directions),
        entry_price=current_price,
        stop_loss=current_price * 0.95 if random.choice(directions) == "BUY" else current_price * 1.05,
        take_profit=current_price * 1.1 if random.choice(directions) == "BUY" else current_price * 0.9,
        confidence=0.3 + random.random() * 0.6,
        ai_analysis="Sygnał wygenerowany na podstawie analizy technicznej z wykorzystaniem sztucznej inteligencji. " +
                    "Wskaźniki RSI i MACD wskazują na silny trend, potwierdzony przez formację świecową. " +
                    "Analiza fal Elliotta sugeruje rozpoczęcie nowej fali wzrostowej. " +
                    "Rekomendowana pozycja z ryzykiem 2% kapitału.",
        created_at=datetime.now(),
        expired_at=datetime.now() + timedelta(hours=24),
        status="ACTIVE"
    )
    
    return signal

def test_notifications():
    """Testuje działanie systemu powiadomień"""
    setup_test_environment()
    
    # Pobierz menedżera powiadomień
    notification_manager = get_notification_manager()
    
    # 1. Test prostego powiadomienia
    logger.info("=== Test 1: Proste powiadomienie ===")
    notification_manager.send_notification(
        NotificationType.SYSTEM,
        "Test powiadomienia systemowego",
        "To jest testowe powiadomienie systemowe.",
        {"test_id": 1, "timestamp": datetime.now().isoformat()}
    )
    
    # 2. Test powiadomienia o błędzie
    logger.info("\n=== Test 2: Powiadomienie o błędzie ===")
    notification_manager.send_notification(
        NotificationType.ERROR,
        "Wykryto błąd w systemie",
        "Wystąpił błąd podczas przetwarzania danych.",
        {"error_code": "DB_CONNECTION_FAILED", "component": "database_connector"}
    )
    
    # 3. Test powiadomienia o nowym sygnale
    logger.info("\n=== Test 3: Powiadomienie o nowym sygnale ===")
    test_signal = create_test_signal()
    notification_manager.notify_new_signal(test_signal)
    
    logger.info("\nWszystkie testy powiadomień zakończone pomyślnie!")

if __name__ == "__main__":
    try:
        logger.info("Rozpoczęcie testów systemu powiadomień")
        test_notifications()
        logger.info("Testy systemu powiadomień zakończone pomyślnie")
    except Exception as e:
        logger.error(f"Błąd podczas testowania systemu powiadomień: {e}")
        import traceback
        logger.error(traceback.format_exc()) 