#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Test integracji API DeepSeek po zmianie domyślnego modelu na deepseek-r1:1.5b.
"""

import os
import sys
import time
import logging
import json
from datetime import datetime

# Dodajemy ścieżkę do src
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.ai_models.deepseek_api import DeepSeekAPI

# Konfiguracja logowania
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("DeepSeekAPITest")

def test_api_initialization():
    """Test inicjalizacji API i wykrywania modelu."""
    logger.info("=== Test inicjalizacji API DeepSeek ===")
    api = DeepSeekAPI()
    logger.info(f"Zainicjalizowano API z modelem: {api.model}")
    logger.info(f"Parametry: max_tokens={api.max_tokens}, temperature={api.temperature}")
    return api

def test_simple_response(api):
    """Test prostej odpowiedzi z API."""
    logger.info("\n=== Test prostej odpowiedzi ===")
    prompt = "Napisz krótkie powitanie po polsku"
    
    start_time = time.time()
    response = api.generate_response(prompt)
    elapsed_time = time.time() - start_time
    
    logger.info(f"Czas odpowiedzi: {elapsed_time:.2f}s")
    
    if response["success"]:
        logger.info(f"Odpowiedź: {response['response']}")
        logger.info(f"Tokeny: {response['tokens_used']}")
        return True
    else:
        logger.error(f"Błąd: {response.get('error', 'Nieznany błąd')}")
        return False

def test_trading_decision(api):
    """Test generowania decyzji tradingowej."""
    logger.info("\n=== Test generowania decyzji tradingowej ===")
    
    # Przykładowe dane rynkowe
    market_data = {
        "instrument": "EURUSD",
        "current_price": 1.0935,
        "previous_close": 1.0920,
        "daily_high": 1.0940,
        "daily_low": 1.0905,
        "daily_volume": 45670,
        "price_history": [
            {"time": "2023-07-01", "open": 1.0850, "high": 1.0875, "low": 1.0830, "close": 1.0870},
            {"time": "2023-07-02", "open": 1.0870, "high": 1.0890, "low": 1.0860, "close": 1.0880},
            {"time": "2023-07-03", "open": 1.0880, "high": 1.0910, "low": 1.0870, "close": 1.0905},
            {"time": "2023-07-04", "open": 1.0905, "high": 1.0925, "low": 1.0890, "close": 1.0920},
            {"time": "2023-07-05", "open": 1.0920, "high": 1.0940, "low": 1.0905, "close": 1.0935}
        ]
    }
    
    prompt = f"""Przeanalizuj poniższe dane rynkowe dla instrumentu EURUSD i podaj rekomendację tradingową 
    (BUY, SELL lub HOLD) wraz z krótkim uzasadnieniem. Odpowiedź sformatuj jako proste zdanie.
    
    Dane rynkowe:
    {json.dumps(market_data, indent=2)}
    """
    
    system_prompt = "Jesteś doświadczonym analitykiem rynków finansowych. Twoje odpowiedzi są zwięzłe i precyzyjne."
    
    start_time = time.time()
    response = api.generate_response(prompt, system_prompt, max_tokens=200)
    elapsed_time = time.time() - start_time
    
    logger.info(f"Czas odpowiedzi: {elapsed_time:.2f}s")
    
    if response["success"]:
        logger.info(f"Rekomendacja tradingowa: {response['response']}")
        logger.info(f"Tokeny: {response['tokens_used']}")
        return True
    else:
        logger.error(f"Błąd: {response.get('error', 'Nieznany błąd')}")
        return False

def main():
    """Główna funkcja testująca."""
    logger.info("Rozpoczęcie testów integracji API DeepSeek")
    
    # Test inicjalizacji
    api = test_api_initialization()
    
    # Test prostej odpowiedzi
    simple_test_success = test_simple_response(api)
    
    # Test decyzji tradingowej
    trading_test_success = test_trading_decision(api)
    
    # Podsumowanie
    logger.info("\n=== Podsumowanie testów ===")
    logger.info(f"Test prostej odpowiedzi: {'SUKCES' if simple_test_success else 'NIEPOWODZENIE'}")
    logger.info(f"Test decyzji tradingowej: {'SUKCES' if trading_test_success else 'NIEPOWODZENIE'}")
    
    # Status końcowy
    if simple_test_success and trading_test_success:
        logger.info("\nWszystkie testy zakończone pomyślnie!")
        logger.info("API DeepSeek z modelem deepseek-r1:1.5b działa poprawnie.")
        return 0
    else:
        logger.error("\nNiektóre testy zakończyły się niepowodzeniem.")
        logger.error("Sprawdź logi powyżej, aby zidentyfikować problem.")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 