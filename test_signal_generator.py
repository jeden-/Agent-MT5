#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Test generatora sygnałów handlowych z wykorzystaniem analizy technicznej.
"""

import sys
import os
import logging
import traceback
from datetime import datetime

# Dodanie ścieżki głównej projektu do sys.path
root_dir = os.path.dirname(os.path.abspath(__file__))
if root_dir not in sys.path:
    sys.path.append(root_dir)

# Konfiguracja logowania
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('test_signal_generator')

from src.mt5_bridge.mt5_connector import MT5Connector
from src.analysis.signal_generator import SignalGenerator
from src.models.trading_models import TradingSignal

def test_signal_generator():
    """
    Testuje generator sygnałów handlowych dla różnych instrumentów i ram czasowych.
    Wyświetla szczegółowe informacje o wygenerowanych sygnałach.
    """
    try:
        # Inicjalizacja konektora MT5
        logger.info("Inicjalizacja konektora MT5")
        mt5_connector = MT5Connector()
        connected = mt5_connector.connect()
        
        # Sprawdzenie połączenia
        if not connected:
            logger.error("Nie udało się połączyć z MetaTrader 5")
            return
        
        logger.info("Połączono z MetaTrader 5")
        account_info = mt5_connector.get_account_info()
        logger.info(f"Informacje o koncie: {account_info}")
        
        # Inicjalizacja generatora sygnałów
        logger.info("Inicjalizacja generatora sygnałów")
        signal_generator = SignalGenerator()
        
        # Lista instrumentów do testowania
        instruments = ["EURUSD"]  # Ograniczamy do jednego instrumentu dla szybszego testowania
        
        # Ramy czasowe do testowania
        timeframes = ["M15"]  # Ograniczamy do jednego timeframe dla szybszego testowania
        
        # Test generowania sygnałów
        for symbol in instruments:
            logger.info(f"\n=== Testowanie sygnałów dla {symbol} ===")
            
            for timeframe in timeframes:
                logger.info(f"\n--- Ramy czasowe: {timeframe} ---")
                
                # Generowanie sygnału
                logger.info(f"Generowanie sygnału dla {symbol} na ramach czasowych {timeframe}")
                try:
                    signal = signal_generator.generate_signal(symbol, timeframe)
                    
                    if signal:
                        # Wyświetlenie szczegółów sygnału
                        logger.info(f"Wygenerowany sygnał dla {symbol}:")
                        logger.info(f"Kierunek: {signal.direction}")
                        logger.info(f"Pewność: {signal.confidence:.2f}")
                        logger.info(f"Cena wejścia: {signal.entry_price:.5f}")
                        logger.info(f"Stop Loss: {signal.stop_loss:.5f}")
                        logger.info(f"Take Profit: {signal.take_profit:.5f}")
                        logger.info(f"Model: {signal.model_name}")
                        logger.info(f"Czas wygenerowania: {signal.timestamp}")
                        
                        # Wyświetlenie szczegółów analizy technicznej
                        if hasattr(signal, 'metadata') and signal.metadata:
                            logger.info("\nSzczegóły analizy technicznej:")
                            
                            # Wskaźniki
                            if 'indicators' in signal.metadata:
                                logger.info("Wartości wskaźników:")
                                for indicator, value in signal.metadata['indicators'].items():
                                    if value is not None:
                                        logger.info(f"  {indicator}: {value:.5f}" if isinstance(value, float) else f"  {indicator}: {value}")
                            
                            # Sygnały z poszczególnych wskaźników
                            if 'signals' in signal.metadata:
                                logger.info("Sygnały z poszczególnych wskaźników:")
                                for indicator, signal_value in signal.metadata['signals'].items():
                                    logger.info(f"  {indicator}: {signal_value}")
                            
                            # Poziomy pewności
                            if 'confidence_scores' in signal.metadata:
                                logger.info("Poziomy pewności:")
                                for indicator, confidence in signal.metadata['confidence_scores'].items():
                                    logger.info(f"  {indicator}: {confidence:.2f}")
                            
                            # Formacje świecowe
                            if 'patterns' in signal.metadata:
                                logger.info("Wykryte formacje świecowe:")
                                detected_patterns = [pattern for pattern, detected in signal.metadata['patterns'].items() if detected]
                                if detected_patterns:
                                    for pattern in detected_patterns:
                                        logger.info(f"  {pattern}")
                                else:
                                    logger.info("  Nie wykryto formacji świecowych")
                        
                        # Analiza AI
                        logger.info(f"\nAnaliza AI:")
                        logger.info(f"{signal.analysis}")
                    else:
                        logger.info(f"Nie wygenerowano sygnału dla {symbol} na ramach czasowych {timeframe}")
                except Exception as e:
                    logger.error(f"Błąd podczas generowania sygnału: {e}")
                    logger.error(f"Pełny ślad stosu błędu:\n{traceback.format_exc()}")
        
        # Zamykanie połączenia z MT5
        logger.info("\nZamykanie połączenia z MetaTrader 5")
        mt5_connector.disconnect()
        
    except Exception as e:
        logger.error(f"Błąd podczas testowania generatora sygnałów: {e}")
        logger.error(f"Pełny ślad stosu błędu:\n{traceback.format_exc()}")
        
if __name__ == "__main__":
    logger.info("Rozpoczynanie testu generatora sygnałów")
    test_signal_generator()
    logger.info("Test zakończony") 