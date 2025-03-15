#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Prosty test sprawdzający, czy DeepSeek jest wyłączony w routerze AI.
"""

import os
import sys
import logging
import time
from dotenv import load_dotenv

# Wczytanie zmiennych środowiskowych
load_dotenv()

# Dodajemy ścieżkę do src
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Konfiguracja logowania - zapisujemy wszystko do pliku logs/ai_router_test.log
log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs')
os.makedirs(log_dir, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(log_dir, 'ai_router_test.log')),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("AIRouterTest")

def main():
    """
    Główna funkcja testująca.
    
    Sprawdza, czy DeepSeek jest wyłączony w routerze AI poprzez przeglądanie logów.
    """
    logger.info("=== Rozpoczęcie testu wyłączenia DeepSeek ===\n")
    
    from src.ai_models.ai_router import get_ai_router
    
    # Inicjalizacja routera AI
    router = get_ai_router()
    
    # Sprawdzenie konfiguracji modeli
    logger.info("Konfiguracja modeli:")
    for model_name, config in router.models_config.items():
        enabled = "WŁĄCZONY" if config.get('enabled', False) else "WYŁĄCZONY"
        weight = config.get('weight', 0.0)
        logger.info(f"- {model_name}: {enabled}, waga: {weight}")
    
    # Weryfikacja, czy Claude jest włączony i ma najwyższą wagę
    claude_enabled = router.models_config.get('claude', {}).get('enabled', False)
    claude_weight = router.models_config.get('claude', {}).get('weight', 0.0)
    
    # Weryfikacja, czy DeepSeek jest wyłączony
    deepseek_enabled = router.models_config.get('deepseek', {}).get('enabled', True)
    
    if claude_enabled and claude_weight > 0.5 and not deepseek_enabled:
        logger.info("\n=== TEST ZAKOŃCZONY POMYŚLNIE ===")
        logger.info("Router AI jest poprawnie skonfigurowany do korzystania z Claude jako domyślnego modelu.")
        logger.info("DeepSeek jest poprawnie wyłączony w konfiguracji.")
        return 0
    else:
        logger.error("\n=== TEST ZAKOŃCZONY NIEPOWODZENIEM ===")
        if not claude_enabled or claude_weight <= 0.5:
            logger.error("Claude nie jest włączony lub ma zbyt niską wagę.")
        if deepseek_enabled:
            logger.error("DeepSeek jest nadal włączony w konfiguracji.")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 