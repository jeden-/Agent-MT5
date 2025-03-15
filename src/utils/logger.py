"""
Moduł konfiguracji logowania dla systemu AgentMT5.
"""

import os
import logging
from logging.handlers import RotatingFileHandler
from typing import Optional

def setup_logger(name: str, level: int = logging.INFO, 
                log_file: Optional[str] = None) -> logging.Logger:
    """
    Konfiguruje i zwraca logger.
    
    Args:
        name (str): Nazwa loggera
        level (int): Poziom logowania
        log_file (str, optional): Ścieżka do pliku logów
    
    Returns:
        logging.Logger: Skonfigurowany logger
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Formatowanie logów
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Handler konsolowy
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # Handler plikowy (jeśli podano ścieżkę)
    if log_file:
        # Upewnij się, że katalog istnieje
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        
        # Dodaj handler plikowy z rotacją
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger 

def setup_logging(level: int = logging.INFO, log_file: Optional[str] = None):
    """
    Konfiguruje główny logger aplikacji.
    
    Args:
        level (int): Poziom logowania
        log_file (str, optional): Ścieżka do pliku logów
    """
    # Konfiguracja głównego loggera
    root_logger = logging.getLogger()
    
    # Usuń wszystkie istniejące handlery, aby uniknąć duplikacji
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Ustawienie poziomu logowania
    root_logger.setLevel(level)
    
    # Formatowanie logów
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Handler konsolowy
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # Handler plikowy (jeśli podano ścieżkę)
    if log_file:
        # Upewnij się, że katalog istnieje
        log_dir = os.path.dirname(log_file)
        if log_dir:
            os.makedirs(log_dir, exist_ok=True)
        
        # Dodaj handler plikowy z rotacją
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5
        )
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
        
    logging.info("Skonfigurowano logowanie aplikacji") 