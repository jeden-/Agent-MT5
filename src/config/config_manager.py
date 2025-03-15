#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Menedżer konfiguracji aplikacji.
"""

import os
import logging
import yaml
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class ConfigManager:
    """Menedżer konfiguracji aplikacji."""
    
    _instance = None
    
    def __new__(cls):
        """Implementacja wzorca Singleton."""
        if cls._instance is None:
            cls._instance = super(ConfigManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """Inicjalizacja menedżera konfiguracji."""
        if getattr(self, "_initialized", False):
            return
            
        self.config = {}
        self.config_file = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'config.yaml')
        
        # Domyślna konfiguracja
        self.default_config = {
            'indicators': {
                'RSI': True,
                'MACD': True,
                'MA': True,
                'Bollinger': True,
                'ATR': True
            },
            'trading': {
                'max_risk_per_trade': 0.02,
                'max_open_positions': 5,
                'default_lot_size': 0.01
            }
        }
        
        self.load_config()
        self._initialized = True
        
    def load_config(self) -> None:
        """Wczytuje konfigurację z pliku YAML."""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as file:
                    loaded_config = yaml.safe_load(file)
                    if loaded_config:
                        self.config = loaded_config
                        logger.info(f"Wczytano konfigurację z {self.config_file}")
                    else:
                        self.config = self.default_config
                        logger.warning(f"Plik konfiguracyjny {self.config_file} jest pusty, używam konfiguracji domyślnej")
            else:
                self.config = self.default_config
                logger.warning(f"Nie znaleziono pliku konfiguracyjnego {self.config_file}, używam konfiguracji domyślnej")
        except Exception as e:
            logger.error(f"Błąd podczas wczytywania konfiguracji: {e}")
            self.config = self.default_config
            
    def get_config(self) -> Dict[str, Any]:
        """Zwraca całą konfigurację."""
        return self.config
        
    def get_value(self, key: str, default: Any = None) -> Any:
        """Pobiera wartość z konfiguracji na podstawie klucza."""
        # Obsługa zagnieżdżonych kluczy (np. "trading.max_risk_per_trade")
        keys = key.split('.')
        config = self.config
        
        try:
            for k in keys:
                config = config[k]
            return config
        except (KeyError, TypeError):
            return default
            
    def save_config(self) -> bool:
        """Zapisuje konfigurację do pliku YAML."""
        try:
            with open(self.config_file, 'w') as file:
                yaml.dump(self.config, file, default_flow_style=False)
            logger.info(f"Zapisano konfigurację do {self.config_file}")
            return True
        except Exception as e:
            logger.error(f"Błąd podczas zapisywania konfiguracji: {e}")
            return False 