#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Prosta bezpośrednia próba połączenia z API Ollama bez korzystania z klasy DeepSeekAPI.
"""

import requests
import json
import time
import sys

def get_available_models():
    """Pobiera listę wszystkich dostępnych modeli w Ollama."""
    print("Sprawdzam dostępne modele w Ollama...")
    
    try:
        url = "http://localhost:11434/api/tags"
        response = requests.get(url)
        
        if response.status_code == 200:
            models = response.json().get("models", [])
            model_names = [model.get("name") for model in models]
            
            print(f"Znaleziono {len(model_names)} modeli: {', '.join(model_names)}")
            return model_names
        else:
            print(f"Błąd podczas sprawdzania modeli: kod {response.status_code}")
            return []
    except Exception as e:
        print(f"Wyjątek podczas sprawdzania modeli: {e}")
        return []

def is_smaller_model(model_name):
    """Sprawdza czy model jest prawdopodobnie mniejszy i mniej zasobochłonny."""
    # Modele z mniejszą liczbą parametrów są zazwyczaj oznaczone mniejszymi liczbami
    smaller_indicators = ["tiny", "small", "mini", "3b", "1b", "7b"]
    # Modele quantized są zazwyczaj mniejsze
    quantized_indicators = ["q4", "q5", "q6", "q8", "int4", "int8"]
    
    model_lower = model_name.lower()
    
    # Sprawdź, czy jest to mały model lub model quantized
    for indicator in smaller_indicators + quantized_indicators:
        if indicator in model_lower:
            return True
            
    # Niektóre konkretne modele, które wiemy, że są mniejsze
    known_smaller_models = ["orca-mini", "tinyllama", "phi", "stablelm", "gemma:2b"]
    for model in known_smaller_models:
        if model in model_lower:
            return True
            
    return False

def test_ollama_api(model_name, timeout=30):
    """Test podstawowego zapytania do Ollama API."""
    
    # Endpoint API
    url = "http://localhost:11434/api/generate"
    
    # Dane zapytania
    data = {
        "model": model_name,
        "prompt": "Napisz krótko 'Działa poprawnie' po polsku",
        "stream": False,
        "options": {
            "num_predict": 20,  # Bardzo mała liczba tokenów
            "temperature": 0.7
        }
    }
    
    # Nagłówki
    headers = {"Content-Type": "application/json"}
    
    # Pomiar czasu
    start_time = time.time()
    
    # Wysłanie zapytania
    print(f"Wysyłanie zapytania do API Ollama dla modelu {model_name}...")
    print(f"Dane: {json.dumps(data, indent=2)}")
    
    try:
        response = requests.post(url, headers=headers, json=data, timeout=timeout)
        
        elapsed_time = time.time() - start_time
        print(f"Czas wykonania: {elapsed_time:.2f}s")
        
        # Sprawdzenie odpowiedzi
        if response.status_code == 200:
            print(f"Sukces! Kod odpowiedzi: {response.status_code}")
            try:
                response_data = response.json()
                print(f"Otrzymano odpowiedź o długości: {len(response_data.get('response', ''))}")
                print("\nOdpowiedź:")
                print(response_data.get('response', ''))
                print("\nTokeny: prompt={}, completion={}, total={}".format(
                    response_data.get('prompt_eval_count', 0),
                    response_data.get('eval_count', 0),
                    response_data.get('prompt_eval_count', 0) + response_data.get('eval_count', 0)
                ))
                return True, response_data.get('model_name', model_name)
            except json.JSONDecodeError as e:
                print(f"Błąd dekodowania JSON: {e}")
                print(f"Odpowiedź: {response.text}")
                return False, model_name
        else:
            print(f"Błąd! Kod odpowiedzi: {response.status_code}")
            print(f"Treść odpowiedzi: {response.text}")
            return False, model_name
    except requests.exceptions.Timeout:
        print(f"Timeout! Zapytanie przekroczyło limit czasu {timeout}s")
        return False, model_name
    except Exception as e:
        print(f"Wyjątek podczas wykonywania zapytania: {e}")
        return False, model_name

if __name__ == "__main__":
    print("Test bezpośredniego połączenia z API Ollama")
    
    # Pobieranie wszystkich dostępnych modeli
    all_models = get_available_models()
    
    if not all_models:
        print("Nie znaleziono żadnych modeli. Upewnij się, że Ollama jest uruchomiona.")
        sys.exit(1)
    
    # Najpierw próbujemy z małymi modelami
    print("\nTestowanie mniejszych modeli...")
    smaller_models = [model for model in all_models if is_smaller_model(model)]
    
    if smaller_models:
        print(f"Znaleziono {len(smaller_models)} mniejszych modeli: {', '.join(smaller_models)}")
        for model in smaller_models:
            print(f"\nTestuję mniejszy model: {model}")
            success, tested_model = test_ollama_api(model, timeout=20)
            print(f"Wynik testu dla {tested_model}: {'SUKCES' if success else 'PORAŻKA'}")
            
            if success:
                print(f"\nTest zakończony sukcesem dla mniejszego modelu {tested_model}")
                
                # Jeśli to był model DeepSeek, zaktualizuj plik konfiguracyjny
                if "deepseek" in tested_model.lower():
                    print(f"\nZnaleziono działający model DeepSeek: {tested_model}")
                    print("Zalecamy zaktualizowanie domyślnego modelu w pliku deepseek_api.py na ten model.")
                sys.exit(0)
    else:
        print("Nie znaleziono mniejszych modeli.")
    
    # Jeśli nie znaleźliśmy mniejszych modeli lub żaden z nich nie zadziałał,
    # spróbujmy z pozostałymi modelami
    print("\nTestowanie pozostałych modeli...")
    other_models = [model for model in all_models if model not in smaller_models]
    
    for model in other_models:
        print(f"\nTestuję model: {model}")
        success, tested_model = test_ollama_api(model, timeout=30)
        print(f"Wynik testu dla {tested_model}: {'SUKCES' if success else 'PORAŻKA'}")
        
        if success:
            print(f"\nTest zakończony sukcesem dla modelu {tested_model}")
            
            # Jeśli to był model DeepSeek, zaktualizuj plik konfiguracyjny
            if "deepseek" in tested_model.lower():
                print(f"\nZnaleziono działający model DeepSeek: {tested_model}")
                print("Zalecamy zaktualizowanie domyślnego modelu w pliku deepseek_api.py na ten model.")
            sys.exit(0)
    
    print("\nNie udało się przetestować żadnego modelu.")
    print("Zalecenia:")
    print("1. Sprawdź, czy Ollama jest uruchomiona i działa poprawnie.")
    print("2. Pobierz mniejszy model używając komendy 'ollama pull tinyllama' lub podobnej.")
    print("3. Zmniejsz wymagania pamięciowe dla Ollama lub zwiększ dostępną pamięć dla procesu.")
    sys.exit(1) 