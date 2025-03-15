#!/usr/bin/env python
"""
Skrypt testowy do sprawdzenia endpointów AI.

Testuje:
1. Generowanie sygnału przez /ai/generate_signal
2. Pobieranie najnowszych sygnałów przez /ai/signals/latest
3. Sprawdzenie wydajności modeli przez /ai/performance
"""

import os
import sys
import time
import logging
import requests
import json
from datetime import datetime
from dotenv import load_dotenv

# Dodanie ścieżki głównej projektu
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Konfiguracja logowania
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Ładowanie zmiennych środowiskowych
load_dotenv()

# Adres serwera MT5
SERVER_URL = os.getenv('MT5_SERVER_URL', 'http://127.0.0.1:8000')

def test_generate_signal():
    """Test endpointu /ai/generate_signal"""
    logger.info("Test 1: Generowanie sygnału przez /ai/generate_signal")
    
    # Lista instrumentów do przetestowania
    instruments = ["EURUSD", "USDJPY", "GOLD"]
    
    for instrument in instruments:
        try:
            # Przygotowanie danych
            payload = {
                "symbol": instrument,
                "timeframe": "M15"
            }
            
            # Wysłanie żądania
            logger.info(f"Wysyłam żądanie generowania sygnału dla {instrument}")
            response = requests.post(f"{SERVER_URL}/ai/generate_signal", json=payload)
            
            # Sprawdzenie odpowiedzi
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "ok":
                    signal = data.get("signal", {})
                    logger.info(f"Wygenerowano sygnał dla {instrument}: {signal.get('direction')} z pewnością {signal.get('confidence')}")
                    logger.info(f"Model: {signal.get('model_name')}")
                    logger.info(f"Analiza: {signal.get('analysis')[:100]}...")
                else:
                    logger.warning(f"Błąd w odpowiedzi: {data.get('message')}")
            else:
                logger.error(f"Błąd HTTP {response.status_code}: {response.text}")
        
        except Exception as e:
            logger.error(f"Błąd podczas testu dla {instrument}: {str(e)}")
        
        # Krótka przerwa między żądaniami
        time.sleep(1)

def test_latest_signals():
    """Test endpointu /ai/signals/latest"""
    logger.info("\nTest 2: Pobieranie najnowszych sygnałów przez /ai/signals/latest")
    
    try:
        # Wysłanie żądania
        logger.info("Wysyłam żądanie o najnowsze sygnały")
        response = requests.get(f"{SERVER_URL}/ai/signals/latest?limit=5")
        
        # Sprawdzenie odpowiedzi
        if response.status_code == 200:
            data = response.json()
            if data.get("status") == "ok":
                signals = data.get("signals", [])
                logger.info(f"Pobrano {len(signals)} najnowszych sygnałów")
                
                for i, signal in enumerate(signals):
                    logger.info(f"Sygnał {i+1}: {signal.get('symbol')} {signal.get('direction')} ({signal.get('model_name')})")
            else:
                logger.warning(f"Błąd w odpowiedzi: {data.get('message')}")
        else:
            logger.error(f"Błąd HTTP {response.status_code}: {response.text}")
    
    except Exception as e:
        logger.error(f"Błąd podczas testu najnowszych sygnałów: {str(e)}")

def test_ai_performance():
    """Test endpointu /ai/performance"""
    logger.info("\nTest 3: Sprawdzenie wydajności modeli przez /ai/performance")
    
    try:
        # Wysłanie żądania
        logger.info("Wysyłam żądanie o statystyki wydajności modeli AI")
        response = requests.get(f"{SERVER_URL}/ai/performance")
        
        # Sprawdzenie odpowiedzi
        if response.status_code == 200:
            data = response.json()
            if data.get("status") == "ok":
                models = data.get("models_performance", [])
                logger.info(f"Pobrano statystyki dla {len(models)} modeli AI")
                logger.info(f"Całkowita liczba przeanalizowanych sygnałów: {data.get('total_signals_analyzed', 0)}")
                logger.info(f"Średnia globalna pewność: {data.get('avg_global_confidence', 0)}")
                
                for model in models:
                    logger.info(f"Model: {model.get('model')}")
                    logger.info(f"  Liczba sygnałów: {model.get('total_signals')}")
                    logger.info(f"  Sygnały kupna: {model.get('buy_signals')} ({model.get('buy_percentage')}%)")
                    logger.info(f"  Sygnały sprzedaży: {model.get('sell_signals')} ({model.get('sell_percentage')}%)")
                    logger.info(f"  Średnia pewność: {model.get('avg_confidence')}")
            else:
                logger.warning(f"Błąd w odpowiedzi: {data.get('message')}")
        else:
            logger.error(f"Błąd HTTP {response.status_code}: {response.text}")
    
    except Exception as e:
        logger.error(f"Błąd podczas testu wydajności AI: {str(e)}")

def main():
    """Główna funkcja uruchamiająca testy."""
    logger.info("Rozpoczynam testy endpointów AI")
    
    # Test 1: Generowanie sygnału
    test_generate_signal()
    
    # Test 2: Pobieranie najnowszych sygnałów
    test_latest_signals()
    
    # Test 3: Sprawdzenie wydajności modeli
    test_ai_performance()
    
    logger.info("Testy zakończone")

if __name__ == "__main__":
    main() 