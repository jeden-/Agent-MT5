#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Skrypt testowy do sprawdzenia, czy patch dla TradingService działa poprawnie.
"""

import sys
import os
import logging
from datetime import datetime
import traceback

# Konfiguracja logowania
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("test_patch")

# Wyłączenie logowania dla niektórych modułów
logging.getLogger("MetaTrader5").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)

def test_patch():
    """Testuje działanie łatek."""
    try:
        # Dodanie katalogu głównego projektu do ścieżki
        sys.path.append(os.path.dirname(os.path.abspath(__file__)))
        
        # Import potrzebnych modułów
        logger.info("Importowanie modułów...")
        from src.utils.patches import patch_trading_signal, patch_trading_service, apply_patch_for_mt5_connector
        from src.database.models import TradingSignal
        from src.mt5_bridge.trading_service import TradingService
        from src.database.models import Transaction
        
        # Aplikowanie łatek
        logger.info("Aplikowanie łatek...")
        patch_trading_signal()
        patch_trading_service()
        apply_patch_for_mt5_connector()
        
        # Tworzenie testowego sygnału
        logger.info("Tworzenie testowego sygnału...")
        signal = TradingSignal(
            symbol="EURUSD",
            timeframe="H1",
            direction="buy",
            entry_price=1.1000,
            stop_loss=1.0950,
            take_profit=1.1100,
            id="test_signal_001"
        )
        
        # Testowanie metody get() na TradingSignal
        logger.info(f"Testowanie metody get() na TradingSignal: {signal.get('symbol', 'brak')}")
        
        # Inicjalizacja TradingService
        logger.info("Inicjalizacja TradingService...")
        ts = TradingService()
        logger.info(f"TradingService zainicjalizowany: {ts}")
        
        # Symulacja danych rynkowych
        logger.info("Przygotowanie danych rynkowych...")
        market_data = {
            'symbol': 'EURUSD',
            'bid': 1.1000,
            'ask': 1.1002,
            'spread': 2,
            'time': datetime.now(),
            'point': 0.00001  # Dodajemy wartość point, aby uniknąć błędu
        }
        logger.info(f"Dane rynkowe: {market_data}")
        
        # Nadpisanie metody get_market_data, aby zwracała nasze dane
        logger.info("Nadpisanie metody get_market_data...")
        original_get_market_data = ts.get_market_data
        ts.get_market_data = lambda symbol: market_data
        
        # Sprawdzenie, czy connector istnieje
        logger.info(f"Sprawdzanie connectora: {hasattr(ts, 'connector')}")
        if hasattr(ts, 'connector'):
            logger.info(f"Connector: {ts.connector}")
        
        # Nadpisanie metody open_order w MT5Connector, aby symulować sukces
        logger.info("Nadpisanie metody open_order...")
        if hasattr(ts.connector, 'open_order'):
            logger.info("Metoda open_order istnieje w MT5Connector")
            original_open_order = ts.connector.open_order
            ts.connector.open_order = lambda **kwargs: 12345  # Symulujemy sukces otwarcia pozycji
        else:
            logger.error("Metoda open_order NIE istnieje w MT5Connector")
            return False
        
        # Sprawdzenie, czy alias open_position został dodany
        logger.info("Sprawdzanie aliasu open_position...")
        if hasattr(ts.connector, 'open_position'):
            logger.info("Alias open_position został dodany do MT5Connector")
        else:
            logger.error("Alias open_position NIE został dodany do MT5Connector")
            return False
        
        # Testowanie wykonania sygnału
        logger.info("Wykonywanie sygnału...")
        try:
            # Sprawdzenie, czy metoda execute_signal istnieje
            if not hasattr(ts, 'execute_signal'):
                logger.error("Metoda execute_signal NIE istnieje w TradingService")
                return False
            
            # Sprawdzenie, czy metoda execute_signal jest callable
            if not callable(ts.execute_signal):
                logger.error("Metoda execute_signal NIE jest callable")
                return False
            
            # Wykonanie sygnału
            logger.info("Wywołanie metody execute_signal...")
            transaction = ts.execute_signal(signal)
            logger.info(f"Wynik wykonania sygnału: {transaction}")
            
            if transaction:
                logger.info(f"Test zakończony sukcesem! Transakcja: {transaction}")
                return True
            else:
                logger.error("Test nie powiódł się - nie udało się wykonać sygnału")
                return False
        except Exception as e:
            logger.error(f"Błąd podczas wykonywania sygnału: {e}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            return False
        finally:
            # Przywracanie oryginalnych metod
            logger.info("Przywracanie oryginalnych metod...")
            ts.get_market_data = original_get_market_data
            if hasattr(ts.connector, 'open_order'):
                ts.connector.open_order = original_open_order
            
    except Exception as e:
        logger.error(f"Błąd podczas testu: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return False

if __name__ == "__main__":
    result = test_patch()
    print(f"Wynik testu: {'SUKCES' if result else 'PORAŻKA'}")
    sys.exit(0 if result else 1) 