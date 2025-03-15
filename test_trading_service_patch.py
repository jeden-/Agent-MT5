#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import os
import logging
from datetime import datetime
import traceback

# Konfiguracja logowania
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("test_patch")

def test_trading_service_patch():
    """Testuje działanie łatki dla TradingService."""
    try:
        # Dodanie katalogu głównego projektu do ścieżki
        sys.path.append(os.path.dirname(os.path.abspath(__file__)))
        
        # Import potrzebnych modułów
        logger.info("Importowanie modułów...")
        from src.utils.patches import patch_trading_service
        from src.mt5_bridge.trading_service import TradingService
        
        # Aplikowanie łatki
        logger.info("Aplikowanie łatki dla TradingService...")
        result = patch_trading_service()
        logger.info(f"Wynik aplikowania łatki: {result}")
        
        # Inicjalizacja TradingService
        logger.info("Inicjalizacja TradingService...")
        ts = TradingService()
        
        # Testowanie metody get_market_data
        logger.info("Testowanie metody get_market_data...")
        
        # Nadpisanie metody get_symbol_info w connector, aby symulować sukces
        original_get_symbol_info = ts.connector.get_symbol_info
        ts.connector.get_symbol_info = lambda symbol: {
            'symbol': symbol,
            'bid': 1.1000,
            'ask': 1.1002,
            'point': 0.00001,
            'digits': 5,
            'volume_min': 0.01,
            'volume_max': 100.0,
            'volume_step': 0.01
        }
        
        # Wywołanie metody get_market_data
        market_data = ts.get_market_data("EURUSD")
        logger.info(f"Wynik get_market_data: {market_data}")
        
        # Sprawdzenie, czy klucz 'point' istnieje w market_data
        if 'point' in market_data:
            logger.info(f"Klucz 'point' istnieje w market_data: {market_data['point']}")
            # Przywracanie oryginalnej metody
            ts.connector.get_symbol_info = original_get_symbol_info
            return True
        else:
            logger.error("Klucz 'point' NIE istnieje w market_data")
            # Przywracanie oryginalnej metody
            ts.connector.get_symbol_info = original_get_symbol_info
            return False
            
    except Exception as e:
        logger.error(f"Błąd podczas testu: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return False

if __name__ == "__main__":
    result = test_trading_service_patch()
    print(f"Wynik testu: {'SUKCES' if result else 'PORAŻKA'}")
    sys.exit(0 if result else 1) 