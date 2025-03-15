#!/usr/bin/env python
"""
Skrypt sprawdza dostępność serwera Ollama i modeli DeepSeek.
Umożliwia także pobieranie modeli, jeśli nie są zainstalowane.
"""

import sys
import time
import requests
import argparse
import subprocess
from typing import List, Dict, Any, Tuple, Optional
import os
import logging

# Konfiguracja logowania
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("check_ollama")

# Parametry połączenia z Ollama
OLLAMA_API_URL = "http://localhost:11434/api"
OLLAMA_TAGS_URL = f"{OLLAMA_API_URL}/tags"
OLLAMA_VERSION_URL = f"{OLLAMA_API_URL}/version"
OLLAMA_PULL_URL = f"{OLLAMA_API_URL}/pull"

# Lista obsługiwanych modeli DeepSeek
SUPPORTED_MODELS = [
    "deepseek-r1:8b",      # Model podstawowy do pracy z kodem
    "deepseek-instruct",   # Model do zadań ogólnych
    "deepseek-llm"         # Podstawowy model językowy
]

RECOMMENDED_MODEL = "deepseek-r1:8b"

def check_ollama_running() -> Tuple[bool, Optional[str]]:
    """
    Sprawdza, czy serwer Ollama jest uruchomiony.
    
    Returns:
        Tuple[bool, Optional[str]]: (czy_dziala, wersja)
    """
    try:
        response = requests.get(OLLAMA_VERSION_URL, timeout=5)
        if response.status_code == 200:
            version_data = response.json()
            version = version_data.get('version', 'unknown')
            logger.info(f"Ollama jest uruchomiona (wersja {version})")
            return True, version
        else:
            logger.error(f"Nie można połączyć się z Ollama API (kod: {response.status_code})")
            return False, None
    except requests.RequestException as e:
        logger.error(f"Błąd podczas próby połączenia z Ollama: {str(e)}")
        return False, None

def get_available_models() -> List[Dict[str, Any]]:
    """
    Pobiera listę modeli dostępnych w Ollama.
    
    Returns:
        List[Dict[str, Any]]: Lista modeli
    """
    try:
        response = requests.get(OLLAMA_TAGS_URL, timeout=10)
        if response.status_code == 200:
            return response.json().get('models', [])
        else:
            logger.error(f"Nie można pobrać listy modeli (kod: {response.status_code})")
            return []
    except requests.RequestException as e:
        logger.error(f"Błąd podczas pobierania listy modeli: {str(e)}")
        return []

def check_deepseek_models() -> List[str]:
    """
    Sprawdza dostępność modeli DeepSeek.
    
    Returns:
        List[str]: Lista nazw dostępnych modeli DeepSeek
    """
    models = get_available_models()
    deepseek_models = []
    
    for model in models:
        name = model.get('name', '')
        if 'deepseek' in name.lower():
            deepseek_models.append(name)
            logger.info(f"Znaleziono model DeepSeek: {name}")
    
    if not deepseek_models:
        logger.warning("Nie znaleziono żadnych modeli DeepSeek")
    
    return deepseek_models

def pull_model(model_name: str) -> bool:
    """
    Pobiera model z repozytorium Ollama.
    
    Args:
        model_name: Nazwa modelu do pobrania
        
    Returns:
        bool: Czy operacja się powiodła
    """
    logger.info(f"Rozpoczęcie pobierania modelu {model_name}...")
    
    try:
        # Użycie komendy systemowej ollama pull
        # Jest to bardziej niezawodne niż API dla dużych modeli
        result = subprocess.run(
            ["ollama", "pull", model_name],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            logger.info(f"Model {model_name} został pomyślnie pobrany")
            return True
        else:
            logger.error(f"Błąd podczas pobierania modelu {model_name}: {result.stderr}")
            return False
            
    except subprocess.SubprocessError as e:
        logger.error(f"Błąd podczas uruchamiania komendy ollama pull: {str(e)}")
        return False

def start_ollama() -> bool:
    """
    Próbuje uruchomić Ollama.
    
    Returns:
        bool: Czy uruchomienie się powiodło
    """
    try:
        # Różne komendy dla różnych systemów operacyjnych
        if sys.platform.startswith('win'):
            # Windows - uruchomienie Ollama z menu start
            logger.info("Próba uruchomienia Ollama na Windows...")
            subprocess.Popen(["start", "Ollama"], shell=True)
        elif sys.platform == 'darwin':
            # MacOS
            logger.info("Próba uruchomienia Ollama na macOS...")
            subprocess.Popen(["open", "-a", "Ollama"])
        else:
            # Linux
            logger.info("Próba uruchomienia Ollama na Linux...")
            subprocess.Popen(["ollama", "serve"], start_new_session=True)
        
        # Czekamy kilka sekund na uruchomienie
        time.sleep(5)
        
        # Sprawdzamy, czy Ollama została uruchomiona
        is_running, _ = check_ollama_running()
        return is_running
        
    except Exception as e:
        logger.error(f"Błąd podczas uruchamiania Ollama: {str(e)}")
        return False

def main():
    """Główna funkcja programu."""
    parser = argparse.ArgumentParser(description="Sprawdza dostępność serwera Ollama i modeli DeepSeek")
    parser.add_argument("--install", action="store_true", help="Automatycznie instaluje Ollama i modele, jeśli ich brak")
    parser.add_argument("--model", type=str, default=RECOMMENDED_MODEL, help=f"Model DeepSeek do sprawdzenia/instalacji (domyślnie: {RECOMMENDED_MODEL})")
    
    args = parser.parse_args()
    
    logger.info("Sprawdzanie dostępności Ollama...")
    is_running, version = check_ollama_running()
    
    if not is_running:
        logger.warning("Ollama nie jest uruchomiona!")
        
        if args.install:
            logger.info("Próba uruchomienia Ollama...")
            if start_ollama():
                logger.info("Ollama została pomyślnie uruchomiona")
            else:
                logger.error("Nie udało się uruchomić Ollama. Proszę zainstalować i uruchomić Ollama ręcznie.")
                logger.info("Instrukcje instalacji: https://ollama.com/download")
                return 1
        else:
            logger.error("Ollama nie jest uruchomiona. Uruchom Ollama lub użyj flagi --install.")
            return 1
    
    logger.info("Sprawdzanie dostępności modeli DeepSeek...")
    available_deepseek_models = check_deepseek_models()
    
    if args.model not in available_deepseek_models:
        logger.warning(f"Model {args.model} nie jest dostępny")
        
        if args.install:
            logger.info(f"Próba pobrania modelu {args.model}...")
            if pull_model(args.model):
                logger.info(f"Model {args.model} został pomyślnie pobrany")
            else:
                logger.error(f"Nie udało się pobrać modelu {args.model}")
                return 1
        else:
            logger.error(f"Model {args.model} nie jest dostępny. Uruchom z flagą --install, aby go pobrać.")
            logger.info(f"Komenda: ollama pull {args.model}")
            return 1
    else:
        logger.info(f"Model {args.model} jest dostępny i gotowy do użycia")
    
    logger.info("Sprawdzanie zakończone pomyślnie - system jest gotowy do pracy z modelami DeepSeek")
    return 0

if __name__ == "__main__":
    sys.exit(main()) 