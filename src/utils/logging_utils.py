#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Narzędzia do konfiguracji logowania w aplikacji.
"""

import os
import logging
import sys
from datetime import datetime
from logging.handlers import RotatingFileHandler

def setup_logging(log_level=None, log_file=None):
    """
    Konfiguracja systemu logowania.
    
    Args:
        log_level (str, optional): Poziom logowania (DEBUG, INFO, WARNING, ERROR, CRITICAL).
                                  Domyślnie pobierany z zmiennych środowiskowych lub ustawiony na INFO.
        log_file (str, optional): Ścieżka do pliku logów.
                                 Domyślnie pobierana z zmiennych środowiskowych lub ustawiona na logs/agent.log.
    
    Returns:
        logging.Logger: Skonfigurowany logger.
    """
    # Określenie poziomu logowania
    if log_level is None:
        log_level = os.getenv('LOG_LEVEL', 'INFO')
    
    numeric_level = getattr(logging, log_level.upper(), None)
    if not isinstance(numeric_level, int):
        print(f"Nieprawidłowy poziom logowania: {log_level}")
        numeric_level = logging.INFO
    
    # Określenie ścieżki do pliku logów
    if log_file is None:
        log_file = os.getenv('LOG_FILE_PATH', 'logs/agent.log')
    
    # Upewnienie się, że katalog logów istnieje
    log_dir = os.path.dirname(log_file)
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    # Konfiguracja podstawowego formatowania
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    date_format = '%Y-%m-%d %H:%M:%S'
    
    # Konfiguracja loggera
    logger = logging.getLogger('trading_agent')
    logger.setLevel(numeric_level)
    
    # Usunięcie istniejących handlerów, aby uniknąć duplikacji
    if logger.handlers:
        logger.handlers.clear()
    
    # Handler dla konsoli
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(numeric_level)
    console_formatter = logging.Formatter(log_format, date_format)
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    # Handler dla pliku z rotacją
    try:
        file_handler = RotatingFileHandler(
            log_file, maxBytes=10485760, backupCount=10, encoding='utf-8'
        )
        file_handler.setLevel(numeric_level)
        file_formatter = logging.Formatter(log_format, date_format)
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
    except Exception as e:
        logger.error(f"Nie można skonfigurować logowania do pliku: {e}")
    
    # Zapisanie informacji początkowej
    logger.info(f"Logowanie skonfigurowane na poziomie {log_level}")
    
    return logger 