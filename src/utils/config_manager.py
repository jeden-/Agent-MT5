#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Moduł zarządzania konfiguracją.
"""

import os
import json
import yaml
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class ConfigManager:
    """
    Klasa zarządzająca konfiguracją aplikacji.
    
    Ta klasa jest odpowiedzialna za wczytywanie, zapisywanie i zarządzanie
    konfiguracją aplikacji.
    """
    
    _instance = None
    
    @classmethod
    def get_instance(cls) -> 'ConfigManager':
        """
        Pobiera instancję managera konfiguracji w trybie singletonu.
        
        Returns:
            ConfigManager: Instancja managera konfiguracji
        """
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Inicjalizacja managera konfiguracji.
        
        Args:
            config_path: Ścieżka do pliku konfiguracyjnego (opcjonalnie)
        """
        self.config_path = config_path or os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            'config',
            'config.yaml'
        )
        self.config = {}
        self.load_config()
        logger.info("ConfigManager zainicjalizowany")
    
    def load_config(self) -> Dict[str, Any]:
        """
        Wczytuje konfigurację z pliku.
        
        Returns:
            Dict[str, Any]: Wczytana konfiguracja
        """
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    if self.config_path.endswith('.yaml') or self.config_path.endswith('.yml'):
                        self.config = yaml.safe_load(f) or {}
                    elif self.config_path.endswith('.json'):
                        self.config = json.load(f)
                    else:
                        logger.warning(f"Nieobsługiwany format pliku konfiguracyjnego: {self.config_path}")
                logger.info(f"Wczytano konfigurację z {self.config_path}")
            else:
                logger.warning(f"Plik konfiguracyjny nie istnieje: {self.config_path}")
                self.config = {}
        except Exception as e:
            logger.error(f"Błąd podczas wczytywania konfiguracji: {e}")
            self.config = {}
        
        return self.config
    
    def save_config(self) -> bool:
        """
        Zapisuje konfigurację do pliku.
        
        Returns:
            bool: True jeśli zapisano pomyślnie
        """
        try:
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
            
            with open(self.config_path, 'w', encoding='utf-8') as f:
                if self.config_path.endswith('.yaml') or self.config_path.endswith('.yml'):
                    yaml.dump(self.config, f, default_flow_style=False)
                elif self.config_path.endswith('.json'):
                    json.dump(self.config, f, indent=2)
                else:
                    logger.warning(f"Nieobsługiwany format pliku konfiguracyjnego: {self.config_path}")
                    return False
            
            logger.info(f"Zapisano konfigurację do {self.config_path}")
            return True
        except Exception as e:
            logger.error(f"Błąd podczas zapisywania konfiguracji: {e}")
            return False
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Pobiera wartość z konfiguracji.
        
        Args:
            key: Klucz konfiguracji
            default: Domyślna wartość, jeśli klucz nie istnieje
            
        Returns:
            Any: Wartość konfiguracji lub domyślna wartość
        """
        return self.config.get(key, default)
    
    def set(self, key: str, value: Any) -> None:
        """
        Ustawia wartość w konfiguracji.
        
        Args:
            key: Klucz konfiguracji
            value: Wartość konfiguracji
        """
        self.config[key] = value
    
    def update(self, config: Dict[str, Any]) -> None:
        """
        Aktualizuje konfigurację.
        
        Args:
            config: Nowa konfiguracja
        """
        self.config.update(config)
        self.save_config()
        
    def get_config_section(self, section: str) -> Dict[str, Any]:
        """
        Pobiera określoną sekcję konfiguracji.
        
        Args:
            section: Nazwa sekcji konfiguracji
            
        Returns:
            Dict[str, Any]: Konfiguracja dla danej sekcji lub pusty słownik, jeśli sekcja nie istnieje
        """
        return self.config.get(section, {})


def get_config_manager() -> ConfigManager:
    """
    Funkcja pomocnicza do pobierania instancji managera konfiguracji.
    
    Returns:
        ConfigManager: Instancja managera konfiguracji
    """
    return ConfigManager.get_instance()

def get_config() -> Dict[str, Any]:
    """
    Funkcja pomocnicza do pobierania słownika konfiguracji.
    
    Returns:
        Dict[str, Any]: Słownik z konfiguracją
    """
    return get_config_manager().config 