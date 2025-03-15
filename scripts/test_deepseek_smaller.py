#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Test połączenia z mniejszym modelem DeepSeek (deepseek-r1:1.5b) przez API Ollama.
"""

import requests
import json
import time
import sys

def test_smaller_deepseek():
    """Test podstawowego zapytania do mniejszego modelu DeepSeek."""
    
    # Parametry testu
    model_name = "deepseek-r1:1.5b"
    timeout = 30
    
    # Endpoint API
    url = "http://localhost:11434/api/generate"
    
    # Dane zapytania
    data = {
        "model": model_name,
        "prompt": "Napisz krótko 'Działa poprawnie' po polsku",
        "stream": False,
        "options": {
            "num_predict": 50,
            "temperature": 0.7
        }
    }
    
    # Nagłówki
    headers = {"Content-Type": "application/json"}
    
    # Sprawdzenie, czy model jest dostępny
    print(f"Sprawdzanie, czy model {model_name} jest dostępny...")
    try:
        response = requests.get("http://localhost:11434/api/tags")
        if response.status_code == 200:
            models = [model.get("name") for model in response.json().get("models", [])]
            if model_name in models:
                print(f"Model {model_name} jest dostępny!")
            else:
                print(f"Model {model_name} nie jest dostępny. Dostępne modele: {', '.join(models)}")
                print(f"Zainstaluj model używając komendy: ollama pull {model_name}")
                return False
        else:
            print(f"Błąd sprawdzania dostępności modeli: {response.status_code}")
            return False
    except Exception as e:
        print(f"Błąd podczas sprawdzania dostępności modeli: {str(e)}")
        return False
    
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
                
                # Test analityczny dla zadania finansowego
                print("\nTestowanie zadania analitycznego...")
                success = test_financial_task(model_name)
                
                return True
            except json.JSONDecodeError as e:
                print(f"Błąd dekodowania JSON: {e}")
                print(f"Odpowiedź: {response.text}")
                return False
        else:
            print(f"Błąd! Kod odpowiedzi: {response.status_code}")
            print(f"Treść odpowiedzi: {response.text}")
            return False
    except requests.exceptions.Timeout:
        print(f"Timeout! Zapytanie przekroczyło limit czasu {timeout}s")
        return False
    except Exception as e:
        print(f"Wyjątek podczas wykonywania zapytania: {e}")
        return False

def test_financial_task(model_name):
    """Test zadania analitycznego związanego z finansami."""
    
    # Endpoint API
    url = "http://localhost:11434/api/generate"
    
    # Dane zapytania - proste zadanie analityczne
    data = {
        "model": model_name,
        "prompt": """Przeanalizuj poniższe dane cenowe EURUSD i określ, czy trend jest zwyżkowy, spadkowy, czy boczny.
        Podaj również potencjalne poziomy wsparcia i oporu w formacie JSON.
        
        Dane cenowe (ostatnie 5 dni):
        - Dzień 1: Open 1.0850, High 1.0875, Low 1.0830, Close 1.0870
        - Dzień 2: Open 1.0870, High 1.0890, Low 1.0860, Close 1.0880
        - Dzień 3: Open 1.0880, High 1.0910, Low 1.0870, Close 1.0905
        - Dzień 4: Open 1.0905, High 1.0925, Low 1.0890, Close 1.0920
        - Dzień 5: Open 1.0920, High 1.0940, Low 1.0905, Close 1.0935""",
        "stream": False,
        "options": {
            "num_predict": 200,
            "temperature": 0.2
        }
    }
    
    # Nagłówki
    headers = {"Content-Type": "application/json"}
    
    # Pomiar czasu
    start_time = time.time()
    
    # Wysłanie zapytania
    print(f"Wysyłanie zapytania analitycznego dla rynku FOREX...")
    
    try:
        response = requests.post(url, headers=headers, json=data, timeout=60)
        
        elapsed_time = time.time() - start_time
        print(f"Czas wykonania analizy: {elapsed_time:.2f}s")
        
        # Sprawdzenie odpowiedzi
        if response.status_code == 200:
            print(f"Sukces! Kod odpowiedzi: {response.status_code}")
            try:
                response_data = response.json()
                print(f"Otrzymano odpowiedź o długości: {len(response_data.get('response', ''))}")
                print("\nOdpowiedź na zadanie analityczne:")
                print(response_data.get('response', ''))
                
                # Sprawdź, czy odpowiedź zawiera JSON
                if "```json" in response_data.get('response', '') or "{" in response_data.get('response', ''):
                    print("\nModel odpowiedział w oczekiwanym formacie! Można go używać do zadań analitycznych.")
                    return True
                else:
                    print("\nModel odpowiedział, ale nie w oczekiwanym formacie JSON. Może wymagać dodatkowych wytycznych.")
                    return False
                
            except json.JSONDecodeError as e:
                print(f"Błąd dekodowania JSON: {e}")
                print(f"Odpowiedź: {response.text}")
                return False
        else:
            print(f"Błąd! Kod odpowiedzi: {response.status_code}")
            print(f"Treść odpowiedzi: {response.text}")
            return False
    except requests.exceptions.Timeout:
        print(f"Timeout! Zapytanie przekroczyło limit czasu 60s")
        return False
    except Exception as e:
        print(f"Wyjątek podczas wykonywania zapytania: {e}")
        return False

if __name__ == "__main__":
    print("=== Test mniejszego modelu DeepSeek (deepseek-r1:1.5b) ===\n")
    success = test_smaller_deepseek()
    
    if success:
        print("\n=== TEST ZAKOŃCZONY POMYŚLNIE ===")
        print("Model deepseek-r1:1.5b działa poprawnie i może być używany w projekcie.")
        print("Zalecana aktualizacja w pliku src/ai_models/deepseek_api.py:")
        print("- Zmiana domyślnego modelu na deepseek-r1:1.5b")
        print("- Dostosowanie parametrów (max_tokens, temperature) pod kątem mniejszego modelu")
    else:
        print("\n=== TEST ZAKOŃCZONY NIEPOWODZENIEM ===")
        print("Model deepseek-r1:1.5b nie działa prawidłowo.")
        print("Zalecenia:")
        print("1. Sprawdź, czy model został poprawnie zainstalowany (ollama list)")
        print("2. Spróbuj zainstalować model ponownie (ollama pull deepseek-r1:1.5b)")
        print("3. Sprawdź, czy Ollama jest uruchomiona i działa poprawnie")
    
    sys.exit(0 if success else 1) 