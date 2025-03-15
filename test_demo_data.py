#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Test generowania danych demonstracyjnych dla AI Analytics.
"""

import sys
import json
from pathlib import Path

# Dodaj ścieżkę projektu do PYTHONPATH
project_root = Path(__file__).parent
sys.path.append(str(project_root))

def test_demo_data():
    """Test generowania danych demonstracyjnych."""
    try:
        from src.analysis.demo_data import get_demo_data_provider
        
        # Pobierz instancję generatora danych
        demo = get_demo_data_provider()
        
        # Testuj generowanie sygnałów
        print("=== Testowanie najnowszych sygnałów ===")
        latest_signals = demo.get_latest_signals(limit=2)
        print(f"Liczba wygenerowanych sygnałów: {latest_signals['count']}")
        if latest_signals['signals']:
            print("Przykładowy sygnał:")
            print(json.dumps(latest_signals['signals'][0], indent=2))
        else:
            print("Brak wygenerowanych sygnałów!")
        
        # Testuj generowanie danych modeli
        print("\n=== Testowanie danych modeli AI ===")
        models_data = demo.get_ai_models_data()
        print(f"Status: {models_data['status']}")
        print(f"Liczba modeli: {len(models_data['models'])}")
        if models_data['models']:
            print("Przykładowy model:")
            print(json.dumps(models_data['models'][0], indent=2))
        else:
            print("Brak danych o modelach!")
        
        # Testuj generowanie danych sygnałów dla analizy
        print("\n=== Testowanie analizy sygnałów AI ===")
        signals_analysis = demo.get_ai_signals_data()
        print(f"Liczba sygnałów do analizy: {signals_analysis['count']}")
        if signals_analysis['signals']:
            print("Przykładowy sygnał do analizy:")
            print(json.dumps(signals_analysis['signals'][0], indent=2))
        else:
            print("Brak danych o sygnałach do analizy!")
            
    except Exception as e:
        print(f"Błąd podczas testowania danych demonstracyjnych: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_demo_data() 