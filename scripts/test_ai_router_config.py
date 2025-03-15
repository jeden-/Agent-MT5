#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Test konfiguracji routera AI po modyfikacjach.
Sprawdza, czy router AI poprawnie używa Claude jako domyślnego modelu
i czy DeepSeek jest wyłączony.
"""

import os
import sys
import logging
from dotenv import load_dotenv

# Wczytanie zmiennych środowiskowych
load_dotenv()

# Sprawdzenie, czy klucz API Claude jest dostępny
ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY')
if not ANTHROPIC_API_KEY:
    try:
        env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'env.mdc')
        with open(env_path, 'r') as f:
            for line in f:
                if line.strip().startswith('ANTHROPIC_API_KEY='):
                    api_key = line.strip().split('=', 1)[1]
                    os.environ['ANTHROPIC_API_KEY'] = api_key
                    print(f"Klucz API Claude został wczytany z pliku env.mdc")
                    break
    except Exception as e:
        print(f"Błąd podczas wczytywania klucza API z pliku env.mdc: {str(e)}")
        sys.exit(1)

# Dodajemy ścieżkę do src
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.ai_models.ai_router import AIRouter, get_ai_router
from src.analysis.signal_generator import SignalGenerator

# Konfiguracja logowania
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("AIRouterTest")

def test_ai_router_config():
    """Test konfiguracji routera AI."""
    logger.info("=== Test konfiguracji routera AI ===")
    
    # Inicjalizacja routera AI
    router = get_ai_router()
    
    # Sprawdzenie konfiguracji modeli
    logger.info("Konfiguracja modeli:")
    for model_name, config in router.models_config.items():
        enabled = "WŁĄCZONY" if config.get('enabled', False) else "WYŁĄCZONY"
        weight = config.get('weight', 0.0)
        logger.info(f"- {model_name}: {enabled}, waga: {weight}")
    
    # Weryfikacja, czy Claude jest włączony i ma najwyższą wagę
    claude_enabled = router.models_config.get('claude', {}).get('enabled', False)
    claude_weight = router.models_config.get('claude', {}).get('weight', 0.0)
    
    if claude_enabled and claude_weight > 0.5:
        logger.info("✅ Claude jest włączony i ma wysoką wagę")
    else:
        logger.warning("❌ Claude nie jest ustawiony jako preferowany model")
    
    # Weryfikacja, czy DeepSeek jest wyłączony
    deepseek_enabled = router.models_config.get('deepseek', {}).get('enabled', True)
    
    if not deepseek_enabled:
        logger.info("✅ DeepSeek jest wyłączony")
    else:
        logger.warning("❌ DeepSeek jest nadal włączony")
        
    return claude_enabled and claude_weight > 0.5 and not deepseek_enabled

def test_signal_generator_model_selection():
    """Test wyboru modelu przez generator sygnałów."""
    logger.info("\n=== Test wyboru modelu przez generator sygnałów ===")
    
    # Inicjalizacja generatora sygnałów
    generator = SignalGenerator()
    
    # Testowanie wyboru modelu dla różnych poziomów pewności
    confidences = [0.9, 0.8, 0.6]
    claude_count = 0
    total_tests = len(confidences) * 10  # 10 testów dla każdego poziomu pewności
    
    for confidence in confidences:
        logger.info(f"Testowanie wyboru modelu dla pewności {confidence}:")
        models_selected = {}
        
        # Wykonanie 10 testów dla danego poziomu pewności
        for _ in range(10):
            model = generator._select_model_name(confidence)
            models_selected[model] = models_selected.get(model, 0) + 1
            if model == "Claude":
                claude_count += 1
        
        # Wyświetlenie wyników
        for model, count in models_selected.items():
            logger.info(f"- {model}: {count} razy")
    
    # Sprawdzenie, czy Claude jest najczęściej wybierany
    claude_percentage = (claude_count / total_tests) * 100
    logger.info(f"\nClaude został wybrany w {claude_percentage:.1f}% przypadków")
    
    if claude_percentage > 40:
        logger.info("✅ Claude jest preferowanym modelem w generatorze sygnałów")
        return True
    else:
        logger.warning("❌ Claude nie jest preferowanym modelem w generatorze sygnałów")
        return False

def main():
    """Główna funkcja testująca."""
    logger.info("=== Rozpoczęcie testów konfiguracji AI ===\n")
    
    # Test konfiguracji routera AI
    router_config_ok = test_ai_router_config()
    
    # Test wyboru modelu przez generator sygnałów
    generator_model_ok = test_signal_generator_model_selection()
    
    # Podsumowanie
    logger.info("\n=== Podsumowanie testów ===")
    logger.info(f"Konfiguracja routera AI: {'✅ OK' if router_config_ok else '❌ BŁĄD'}")
    logger.info(f"Wybór modelu w generatorze sygnałów: {'✅ OK' if generator_model_ok else '❌ BŁĄD'}")
    
    if router_config_ok and generator_model_ok:
        logger.info("\n=== WSZYSTKIE TESTY ZAKOŃCZONE POMYŚLNIE ===")
        logger.info("System jest poprawnie skonfigurowany do korzystania z Claude jako domyślnego modelu.")
        return 0
    else:
        logger.error("\n=== NIEKTÓRE TESTY ZAKOŃCZYŁY SIĘ NIEPOWODZENIEM ===")
        logger.error("Sprawdź logi powyżej, aby zidentyfikować problem.")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 