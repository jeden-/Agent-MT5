#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Skrypt diagnostyczny do debugowania błędu w generowaniu sygnałów.
"""

import sys
import os
import logging
import traceback
from typing import Dict, Any, Optional
from datetime import datetime

# Dodanie ścieżki projektu do PYTHONPATH
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Konfiguracja logowania
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('diagnose_error.log')
    ]
)

logger = logging.getLogger(__name__)

def diagnose_signal_generation():
    """
    Diagnozuje problem z generowaniem sygnałów handlowych.
    """
    logger.info("Rozpoczynam diagnostykę problemu z generowaniem sygnałów")
    
    try:
        # Najpierw aplikujemy łatki systemowe
        from src.utils.patches import apply_all_patches
        logger.info("Aplikowanie łatek systemowych...")
        patch_results = apply_all_patches()
        if all(patch_results.values()):
            logger.info(f"Pomyślnie zaaplikowano {sum(patch_results.values())}/{len(patch_results)} łatek")
        else:
            logger.warning("Nie wszystkie łatki zostały pomyślnie zaaplikowane!")
        
        # Importujemy potrzebne moduły
        from src.database.models import TradingSignal
        
        # 1. Sprawdź sygnaturę konstruktora TradingSignal
        logger.info("Sprawdzam sygnaturę konstruktora TradingSignal")
        import inspect
        sig = inspect.signature(TradingSignal.__init__)
        logger.info(f"Sygnatura konstruktora TradingSignal: {sig}")
        
        # 2. Próba utworzenia instancji TradingSignal
        logger.info("Próba utworzenia instancji TradingSignal")
        signal = TradingSignal(
            symbol="EURUSD",
            timeframe="H1",
            direction="buy",
            entry_price=1.1000,
            stop_loss=1.0950,
            take_profit=1.1050
        )
        logger.info(f"Utworzono instancję TradingSignal: {signal}")
        
        # 3. Sprawdź implementację SignalGenerator
        logger.info("Sprawdzam implementację SignalGenerator")
        from src.analysis.signal_generator import SignalGenerator
        
        # 4. Sprawdź, gdzie w kodzie może być tworzony obiekt wymagający config
        logger.info("Sprawdzam inne klasy zaimportowane w SignalGenerator")
        
        # 5. Sprawdź czy używany jest SignalValidator
        try:
            logger.info("Próbuję utworzyć instancję SignalValidator")
            from src.analysis.signal_validator import SignalValidator
            validator = SignalValidator({})  # Przekazujemy pusty słownik jako config
            logger.info("Pomyślnie utworzono instancję SignalValidator")
        except Exception as e:
            logger.error(f"Błąd podczas tworzenia instancji SignalValidator: {e}")
            logger.error(traceback.format_exc())
        
        # 6. Sprawdź, jakie obiekty są tworzone w metodzie generate_signal
        logger.info("Sprawdzam kod metody generate_signal")
        source_code = inspect.getsource(SignalGenerator.generate_signal)
        logger.info(f"Kod metody generate_signal:\n{source_code}")
        
    except Exception as e:
        logger.error(f"Błąd podczas diagnostyki: {e}")
        logger.error(traceback.format_exc())

if __name__ == "__main__":
    diagnose_signal_generation() 