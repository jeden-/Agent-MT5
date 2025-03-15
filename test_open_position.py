#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Skrypt testowy do generowania sygnału i otwierania pozycji w MT5.
"""

import logging
import sys
import os
from datetime import datetime
from typing import Dict, Any, Optional
import MetaTrader5 as mt5

# Dodanie głównego katalogu projektu do PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Import komponentów
from src.analysis.signal_generator import SignalGenerator
from src.mt5_bridge.trading_service import TradingService
from src.trading_integration import TradingIntegration
from src.position_management.position_manager import PositionManager
from src.risk_management.risk_manager import RiskManager
from src.database.models import TradingSignal

# Konfiguracja loggera
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("test_open_position")

def main():
    """
    Główna funkcja testowa.
    """
    try:
        logger.info("Rozpoczynam test otwierania pozycji na podstawie sygnału")
        
        # Inicjalizacja komponentów
        logger.info("Inicjalizacja komponentów...")
        
        # Inicjalizacja serwisu handlowego
        trading_service = TradingService()
        if not trading_service.connect():
            logger.error("Nie udało się połączyć z MT5")
            return
        logger.info("Połączono z MT5")
        
        # Konfiguracja dla managera pozycji
        position_config = {
            "risk_limits": {
                "max_positions": 5,
                "max_risk_per_trade": 0.02,
                "max_daily_risk": 0.05
            },
            "instruments": {
                "EURUSD.pro": {
                    "active": True,
                    "max_lot_size": 0.1
                },
                "GBPUSD.pro": {
                    "active": True,
                    "max_lot_size": 0.1
                },
                "GOLD.pro": {
                    "active": True,
                    "max_lot_size": 0.05
                },
                "US100.pro": {
                    "active": True,
                    "max_lot_size": 0.05
                },
                "SILVER.pro": {
                    "active": True,
                    "max_lot_size": 0.05
                }
            }
        }
        
        # Inicjalizacja managera pozycji
        position_manager = PositionManager(config=position_config)
        
        # Inicjalizacja managera ryzyka
        risk_manager = RiskManager()
        
        # Inicjalizacja integratora handlowego
        trading_integration = TradingIntegration(
            trading_service=trading_service,
            position_manager=position_manager,
            risk_manager=risk_manager
        )
        
        # Rejestracja instrumentów
        instruments = ["EURUSD.pro", "GBPUSD.pro", "GOLD.pro", "US100.pro", "SILVER.pro"]
        for instrument in instruments:
            trading_integration.register_instrument(instrument, max_lot_size=0.1)
        logger.info(f"Zarejestrowano instrumenty: {instruments}")
        
        # Inicjalizacja generatora sygnałów
        signal_generator = SignalGenerator()
        
        # Wybór instrumentu do testu
        test_instrument = "EURUSD.pro"
        logger.info(f"Generowanie sygnału dla {test_instrument}...")
        
        # Generowanie sygnału
        try:
            # Sprawdźmy, czy możemy pobrać dane historyczne
            logger.info(f"Próba pobrania danych historycznych dla {test_instrument}...")
            tf_map = {
                "M1": mt5.TIMEFRAME_M1,
                "M5": mt5.TIMEFRAME_M5,
                "M15": mt5.TIMEFRAME_M15,
                "M30": mt5.TIMEFRAME_M30,
                "H1": mt5.TIMEFRAME_H1,
                "H4": mt5.TIMEFRAME_H4,
                "D1": mt5.TIMEFRAME_D1
            }
            
            mt5_timeframe = tf_map.get("M15", mt5.TIMEFRAME_M15)
            
            # Pobieranie danych historycznych
            rates = mt5.copy_rates_from_pos(test_instrument, mt5_timeframe, 0, 100)
            if rates is None or len(rates) < 50:
                logger.error(f"Nie udało się pobrać wystarczającej ilości danych dla {test_instrument}")
                logger.error(f"MT5 error: {mt5.last_error()}")
                return
            
            logger.info(f"Pobrano {len(rates)} świec dla {test_instrument}")
            
            # Teraz spróbujmy wygenerować sygnał
            try:
                trading_signal = signal_generator.generate_signal(test_instrument, "M15")
                if not trading_signal:
                    logger.error(f"Nie udało się wygenerować sygnału dla {test_instrument}")
                    return
            except Exception as e:
                logger.error(f"Błąd podczas generowania sygnału: {e}", exc_info=True)
                return
        except Exception as e:
            logger.error(f"Błąd podczas generowania sygnału: {e}", exc_info=True)
            return
        
        # Wyświetlenie szczegółów sygnału
        logger.info(f"Wygenerowano sygnał: {trading_signal.direction} dla {trading_signal.symbol}")
        logger.info(f"Cena wejścia: {trading_signal.entry_price}, SL: {trading_signal.stop_loss}, TP: {trading_signal.take_profit}")
        logger.info(f"Pewność: {trading_signal.confidence}")
        logger.info(f"Analiza AI: {trading_signal.ai_analysis}")
        
        # Wykonanie sygnału - bezpośrednio używamy obiektu TradingSignal
        logger.info("Wykonywanie sygnału...")
        result = trading_integration.execute_signal(trading_signal)
        
        if result:
            logger.info(f"Pozycja otwarta pomyślnie: {result}")
            
            # Pobieranie otwartych pozycji
            logger.info("Pobieranie otwartych pozycji...")
            positions = trading_service.get_open_positions()
            logger.info(f"Otwarte pozycje: {positions}")
            
            # Wyświetlenie szczegółów ostatnio otwartej pozycji
            last_position = None
            for position in positions:
                if position['magic'] == 12345:  # Nasz magiczny numer
                    if last_position is None or position['open_time'] > last_position['open_time']:
                        last_position = position
            
            if last_position:
                logger.info(f"Szczegóły ostatnio otwartej pozycji:")
                logger.info(f"  Symbol: {last_position['symbol']}")
                logger.info(f"  Typ: {last_position['type']}")
                logger.info(f"  Wielkość: {last_position['volume']}")
                logger.info(f"  Cena otwarcia: {last_position['open_price']}")
                logger.info(f"  Stop Loss: {last_position['sl']}")
                logger.info(f"  Take Profit: {last_position['tp']}")
                logger.info(f"  Zysk/Strata: {last_position['profit']}")
                logger.info(f"  Magic: {last_position['magic']}")
        else:
            logger.error("Nie udało się otworzyć pozycji")
        
        logger.info("Test zakończony")
        
    except Exception as e:
        logger.error(f"Błąd podczas testu: {e}", exc_info=True)
    finally:
        # Zamknięcie połączenia z MT5
        if 'trading_service' in locals() and trading_service:
            trading_service.disconnect()
            logger.info("Rozłączono z MT5")

if __name__ == "__main__":
    main() 