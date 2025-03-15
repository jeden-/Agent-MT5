#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Test do identyfikacji problemu z obiektami Position.
"""

import sys
import logging
import traceback
from datetime import datetime

from src.position_management.position_manager import Position, PositionStatus
from src.database.models import TradingSignal

# Konfiguracja logowania
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_position_access():
    """
    Test sprawdzający dostęp do atrybutów obiektu Position.
    """
    try:
        # Utwórz przykładowy obiekt Position
        position = Position(
            ea_id="test_ea",
            ticket=12345,
            symbol="EURUSD",
            type="BUY",
            volume=0.1,
            open_price=1.1234,
            current_price=1.1245,
            sl=1.1200,
            tp=1.1300,
            profit=0.0,
            open_time=datetime.now(),
            status=PositionStatus.OPEN
        )
        
        # Utwórz przykładowy sygnał
        signal = TradingSignal(
            symbol="EURUSD",
            timeframe="M15",
            direction="BUY",
            entry_price=1.1234,
            stop_loss=1.1200,
            take_profit=1.1300,
            confidence=0.75,
            status="pending",
            ai_analysis="Test analysis"
        )
        
        # Test dostępu do atrybutu symbol
        logger.info(f"Position symbol: {position.symbol}")
        logger.info(f"Signal symbol: {signal.symbol}")
        
        # Test porównania
        if position.symbol == signal.symbol:
            logger.info("Symbole są identyczne")
        else:
            logger.info(f"Symbole różnią się: {position.symbol} vs {signal.symbol}")
        
        # Spróbuj obu metod (jako atrybut i jako get)
        try:
            logger.info(f"Position.symbol (jako atrybut): {position.symbol}")
        except Exception as e:
            logger.error(f"Błąd przy dostępie do atrybutu: {e}")
            
        try:
            logger.info(f"Position.get('symbol') (jako metoda): {position.get('symbol')}")
        except Exception as e:
            logger.error(f"Błąd przy dostępie przez get(): {e}")
        
        return True
    except Exception as e:
        logger.error(f"Błąd podczas testu: {e}")
        logger.error(traceback.format_exc())
        return False

if __name__ == "__main__":
    logger.info("Rozpoczęcie testu Position")
    result = test_position_access()
    logger.info(f"Test zakończony {'pomyślnie' if result else 'niepowodzeniem'}")
    sys.exit(0 if result else 1) 