#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import os
import logging

# Konfiguracja logowania
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("test_patch")

def test_mt5_connector_patch():
    """Testuje działanie łatki dla MT5Connector."""
    try:
        # Dodanie katalogu głównego projektu do ścieżki
        sys.path.append(os.path.dirname(os.path.abspath(__file__)))
        
        # Import potrzebnych modułów
        logger.info("Importowanie modułów...")
        from src.utils.patches import apply_patch_for_mt5_connector
        from src.mt5_bridge.mt5_connector import MT5Connector
        
        # Aplikowanie łatki
        logger.info("Aplikowanie łatki dla MT5Connector...")
        result = apply_patch_for_mt5_connector()
        logger.info(f"Wynik aplikowania łatki: {result}")
        
        # Sprawdzenie, czy alias open_position został dodany
        logger.info("Sprawdzanie aliasu open_position...")
        connector = MT5Connector()
        
        if hasattr(connector, 'open_position'):
            logger.info("Alias open_position został dodany do MT5Connector")
            logger.info(f"open_position jest aliasem dla: {connector.open_position}")
            
            # Sprawdzenie, czy open_position jest aliasem dla open_order
            if connector.open_position == connector.open_order:
                logger.info("open_position jest poprawnym aliasem dla open_order")
                return True
            else:
                logger.error("open_position NIE jest aliasem dla open_order")
                return False
        else:
            logger.error("Alias open_position NIE został dodany do MT5Connector")
            return False
            
    except Exception as e:
        logger.error(f"Błąd podczas testu: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return False

if __name__ == "__main__":
    result = test_mt5_connector_patch()
    print(f"Wynik testu: {'SUKCES' if result else 'PORAŻKA'}")
    sys.exit(0 if result else 1) 