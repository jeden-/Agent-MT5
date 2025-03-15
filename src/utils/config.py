"""
Moduł konfiguracyjny dla systemu AgentMT5.
"""

import os
import yaml
from typing import Dict, Any

def load_config(config_path: str = None) -> Dict[str, Any]:
    """
    Ładuje konfigurację z pliku YAML.
    
    Args:
        config_path (str, optional): Ścieżka do pliku konfiguracyjnego.
            Jeśli nie podano, używa domyślnej ścieżki.
    
    Returns:
        Dict[str, Any]: Słownik z konfiguracją
    """
    if config_path is None:
        config_path = os.getenv("CONFIG_PATH", "config/config.yml")
    
    # Jeśli plik nie istnieje, zwróć domyślną konfigurację
    if not os.path.exists(config_path):
        return {
            "http_server": {
                "host": "localhost",
                "port": 8080
            },
            "trading": {
                "max_positions": 100,
                "default_volume": 0.01,
                "risk_percent": 1.0
            },
            "monitoring": {
                "log_level": "INFO",
                "performance_metrics": True
            }
        }
    
    with open(config_path, "r") as f:
        return yaml.safe_load(f) 