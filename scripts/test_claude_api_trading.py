#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Test integracji API Claude (Anthropic) do zadań tradingowych.
Ten skrypt testuje działanie API Claude dla typowych zadań związanych z tradingiem,
takich jak analiza danych rynkowych i generowanie decyzji handlowych.
"""

import os
import sys
import time
import logging
import json
from datetime import datetime
from dotenv import load_dotenv

# Wczytanie zmiennych środowiskowych z pliku .env
load_dotenv()

# Sprawdzenie, czy klucz API jest dostępny
ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY')
if not ANTHROPIC_API_KEY:
    print("UWAGA: Nie znaleziono klucza API Claude (ANTHROPIC_API_KEY) w zmiennych środowiskowych")
    print("Wczytywanie klucza z pliku env.mdc...")
    
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
        print("Uruchom skrypt w środowisku, które ma dostęp do klucza API Claude")
        sys.exit(1)

# Dodajemy ścieżkę do src
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.ai_models.claude_api import ClaudeAPI, get_claude_api

# Konfiguracja logowania
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("ClaudeAPITest")

def test_api_initialization():
    """Test inicjalizacji API i wykrywania modelu."""
    logger.info("=== Test inicjalizacji API Claude ===")
    
    try:
        api = get_claude_api()
        logger.info(f"Zainicjalizowano API z modelem: {api.model}")
        logger.info(f"Parametry: max_tokens={api.max_tokens}, temperature={api.temperature}")
        
        # Przełączenie na mniejszy model dla szybszych testów
        logger.info("Przełączanie na mniejszy model (claude-3-haiku)...")
        api.set_model("claude-3-haiku-20240307")
        logger.info(f"Model ustawiony na: {api.model}")
        
        # Dostosowanie parametrów
        api.set_parameters(max_tokens=1000, temperature=0.5)
        logger.info(f"Parametry zaktualizowane: max_tokens={api.max_tokens}, temperature={api.temperature}")
        
        return api
    except Exception as e:
        logger.error(f"Błąd podczas inicjalizacji API: {str(e)}")
        return None

def test_simple_response(api):
    """Test prostej odpowiedzi z API."""
    logger.info("\n=== Test prostej odpowiedzi ===")
    prompt = "Napisz krótkie powitanie po polsku"
    
    start_time = time.time()
    response = api.generate_response(prompt)
    elapsed_time = time.time() - start_time
    
    logger.info(f"Czas odpowiedzi: {elapsed_time:.2f}s")
    logger.info(f"Odpowiedź: {response.get('text', '')}")
    logger.info(f"Tokeny: input={response.get('input_tokens', 0)}, output={response.get('output_tokens', 0)}, total={response.get('tokens_used', 0)}")
    
    return True if response.get('text') else False

def test_trading_decision(api):
    """Test generowania decyzji tradingowej."""
    logger.info("\n=== Test generowania decyzji tradingowej ===")
    
    # Przykładowe dane rynkowe
    market_data = {
        "symbol": "EURUSD",
        "current_price": 1.0935,
        "previous_close": 1.0920,
        "day_high": 1.0940,
        "day_low": 1.0905,
        "volume": 45670,
        "price_history": [
            {"time": "2023-07-01", "open": 1.0850, "high": 1.0875, "low": 1.0830, "close": 1.0870},
            {"time": "2023-07-02", "open": 1.0870, "high": 1.0890, "low": 1.0860, "close": 1.0880},
            {"time": "2023-07-03", "open": 1.0880, "high": 1.0910, "low": 1.0870, "close": 1.0905},
            {"time": "2023-07-04", "open": 1.0905, "high": 1.0925, "low": 1.0890, "close": 1.0920},
            {"time": "2023-07-05", "open": 1.0920, "high": 1.0940, "low": 1.0905, "close": 1.0935}
        ],
        "technical_indicators": {
            "RSI": 65.2,
            "MACD": {"value": 0.0012, "signal": 0.0008, "histogram": 0.0004},
            "MA_50": 1.0890,
            "MA_200": 1.0840,
            "Bollinger_Bands": {"upper": 1.0960, "middle": 1.0920, "lower": 1.0880}
        }
    }
    
    # Parametry ryzyka
    risk_parameters = {
        "max_risk_per_trade": 2.0,  # maksymalny % kapitału na transakcję
        "max_exposure_per_symbol": 5.0,  # maksymalny % kapitału na symbol
        "target_risk_reward": 2.0,  # Oczekiwany stosunek zysku do ryzyka
        "daily_loss_limit": 5.0,  # Dzienny limit straty (%)
        "daily_pnl": -1.2  # Aktualny dzienny wynik (%)
    }
    
    start_time = time.time()
    decision = api.generate_trading_decision(market_data, risk_parameters)
    elapsed_time = time.time() - start_time
    
    logger.info(f"Czas generowania decyzji: {elapsed_time:.2f}s")
    
    if isinstance(decision, dict) and "model" in decision:
        logger.info(f"Decyzja handlowa: {json.dumps(decision, indent=2)}")
        return True
    else:
        logger.error("Nieprawidłowy format decyzji")
        logger.error(f"Otrzymana odpowiedź: {decision}")
        return False

def test_market_analysis(api):
    """Test analizy rynkowej."""
    logger.info("\n=== Test analizy rynkowej ===")
    
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
    
    start_time = time.time()
    analysis = api.analyze_market_data(market_data, "trend")
    elapsed_time = time.time() - start_time
    
    logger.info(f"Czas analizy rynkowej: {elapsed_time:.2f}s")
    
    if isinstance(analysis, dict):
        logger.info(f"Analiza rynkowa: {json.dumps(analysis, indent=2)}")
        return True
    else:
        logger.error("Nieprawidłowy format analizy")
        logger.error(f"Otrzymana odpowiedź: {analysis}")
        return False

def main():
    """Główna funkcja testująca."""
    logger.info("=== Rozpoczęcie testów API Claude dla zadań tradingowych ===\n")
    
    # Test inicjalizacji
    api = test_api_initialization()
    if not api:
        logger.error("Nie udało się zainicjalizować API Claude")
        return 1
    
    # Test prostej odpowiedzi
    simple_test_success = test_simple_response(api)
    
    # Test analizy rynkowej
    analysis_test_success = test_market_analysis(api)
    
    # Test decyzji tradingowej
    trading_test_success = test_trading_decision(api)
    
    # Podsumowanie
    logger.info("\n=== Podsumowanie testów ===")
    logger.info(f"Test prostej odpowiedzi: {'SUKCES' if simple_test_success else 'NIEPOWODZENIE'}")
    logger.info(f"Test analizy rynkowej: {'SUKCES' if analysis_test_success else 'NIEPOWODZENIE'}")
    logger.info(f"Test decyzji tradingowej: {'SUKCES' if trading_test_success else 'NIEPOWODZENIE'}")
    
    # Status końcowy
    if simple_test_success and analysis_test_success and trading_test_success:
        logger.info("\n=== WSZYSTKIE TESTY ZAKOŃCZONE POMYŚLNIE ===")
        logger.info("API Claude działa poprawnie i może być używane do zadań tradingowych.")
        logger.info(f"Używany model: {api.model}")
        logger.info("\nZalecenia:")
        logger.info("1. W pliku src/ai_models/model_router.py skonfigurować Claude jako domyślny model dla zadań tradingowych")
        logger.info("2. Dostosować parametry (max_tokens, temperature) odpowiednio do potrzeb")
        return 0
    else:
        logger.error("\n=== NIEKTÓRE TESTY ZAKOŃCZYŁY SIĘ NIEPOWODZENIEM ===")
        logger.error("Sprawdź logi powyżej, aby zidentyfikować problem.")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 