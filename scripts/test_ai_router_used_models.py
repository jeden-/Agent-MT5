#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Test routera AI do sprawdzenia, jakie modele są używane podczas analizy rynku.
"""

import os
import sys
import logging
import json
from dotenv import load_dotenv

# Wczytanie zmiennych środowiskowych
load_dotenv()

# Sprawdzenie, czy klucz API Claude jest dostępny
ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY')
if not ANTHROPIC_API_KEY:
    try:
        env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'env.mdc')
        with open(env_path, 'r') as f:
            for line in f:
                if line.strip().startswith('ANTHROPIC_API_KEY='):
                    api_key = line.strip().split('=', 1)[1]
                    os.environ['ANTHROPIC_API_KEY'] = api_key
                    print(f"Klucz API Claude został wczytany z pliku env.mdc")
                    break
    except Exception as e:
        print(f"Błąd podczas wczytywania klucza API z pliku env.mdc: {str(e)}")
        sys.exit(1)

# Dodajemy ścieżkę do src
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.ai_models.ai_router import get_ai_router

# Konfiguracja logowania
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("AIRouterUsageTest")

def test_market_analysis_by_router():
    """Test analizy rynku przez router AI."""
    logger.info("=== Test analizy rynku przez router AI ===")
    
    # Inicjalizacja routera AI
    router = get_ai_router()
    
    # Przykładowe dane rynkowe
    market_data = {
        "symbol": "EURUSD",
        "current_price": 1.0935,
        "open": 1.0920,
        "high": 1.0940,
        "low": 1.0905,
        "close_previous": 1.0920,
        "volume": 45670,
        "technical_indicators": {
            "RSI": 65.2,
            "MACD": {"value": 0.0012, "signal": 0.0008, "histogram": 0.0004},
            "MA_50": 1.0890,
            "MA_200": 1.0840
        }
    }
    
    # Wykonanie analizy
    logger.info("Wykonywanie analizy rynku...")
    analysis_result = router.analyze_market_data(market_data, "trend")
    
    # Sprawdzenie, które modele zostały użyte
    models_used = analysis_result.get('models_used', [])
    logger.info(f"Modele użyte podczas analizy: {', '.join(models_used)}")
    
    # Sprawdzenie, czy DeepSeek nie został użyty
    if 'deepseek' not in models_used:
        logger.info("✅ DeepSeek nie został użyty w analizie")
    else:
        logger.warning("❌ DeepSeek został użyty pomimo wyłączenia")
    
    # Sprawdzenie, czy Claude został użyty
    if 'claude' in models_used:
        logger.info("✅ Claude został użyty w analizie")
    else:
        logger.warning("❌ Claude nie został użyty pomimo włączenia")
    
    # Wyświetlenie wyników analizy
    logger.info("\nWyniki analizy:")
    for key, value in analysis_result.items():
        if key != 'models_used':
            logger.info(f"- {key}: {value}")
    
    return 'claude' in models_used and 'deepseek' not in models_used

def main():
    """Główna funkcja testująca."""
    logger.info("=== Rozpoczęcie testu użycia modeli przez router AI ===\n")
    
    # Test analizy rynku
    models_usage_ok = test_market_analysis_by_router()
    
    # Podsumowanie
    logger.info("\n=== Podsumowanie testu ===")
    logger.info(f"Użycie modeli przez router AI: {'✅ OK' if models_usage_ok else '❌ BŁĄD'}")
    
    if models_usage_ok:
        logger.info("\n=== TEST ZAKOŃCZONY POMYŚLNIE ===")
        logger.info("Router AI prawidłowo używa Claude jako domyślnego modelu i nie korzysta z DeepSeek.")
        return 0
    else:
        logger.error("\n=== TEST ZAKOŃCZONY NIEPOWODZENIEM ===")
        logger.error("Router AI nie używa właściwych modeli. Sprawdź konfigurację.")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 