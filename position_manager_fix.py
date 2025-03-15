#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Plik naprawiający problem z PositionManager.
"""

import logging
import sys
import os
from typing import Dict, Any

# Dodanie ścieżki projektu do PYTHONPATH
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

logger = logging.getLogger(__name__)

def patch_position_manager():
    """
    Funkcja aplikująca łatkę na klasę PositionManager i funkcję get_position_manager.
    """
    logger.info("Aplikuję łatkę na PositionManager i get_position_manager")
    
    try:
        # Importujemy oryginalną klasę i funkcję
        from src.position_management.position_manager import PositionManager, get_position_manager as original_get_position_manager
        
        # Tworzymy nową wersję funkcji get_position_manager
        def patched_get_position_manager() -> PositionManager:
            """
            Patched version of get_position_manager that provides an empty config.
            
            Returns:
                PositionManager: Instance of position manager
            """
            # Przekazujemy pusty słownik jako konfigurację
            empty_config = {}
            if hasattr(PositionManager, "get_instance"):
                return PositionManager.get_instance()
            else:
                return PositionManager(config=empty_config)
        
        # Podmieniamy oryginalną funkcję na naszą wersję
        import src.position_management.position_manager
        setattr(src.position_management.position_manager, "get_position_manager", patched_get_position_manager)
        
        logger.info("Łatka została pomyślnie zaaplikowana")
        
        # Testujemy, czy poprawka działa
        pm = patched_get_position_manager()
        logger.info(f"Pomyślnie utworzono instancję PositionManager: {pm}")
        
        return True
    except Exception as e:
        logger.error(f"Błąd podczas aplikowania łatki: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

if __name__ == "__main__":
    # Konfiguracja logowania
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    success = patch_position_manager()
    print(f"Łatka zaaplikowana {'pomyślnie' if success else 'niepomyślnie'}") 