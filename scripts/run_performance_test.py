#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Skrypt do uruchamiania testów wydajności pobierania danych rynkowych.
"""

import os
import sys
import time
import argparse
from datetime import datetime

# Dodanie głównego katalogu projektu do ścieżki
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def main():
    """Główna funkcja uruchamiająca testy wydajności."""
    parser = argparse.ArgumentParser(description='Test wydajności pobierania danych rynkowych z MT5')
    parser.add_argument('--symbols', type=str, nargs='+', default=["EURUSD", "GBPUSD", "USDJPY", "XAUUSD"],
                        help='Lista symboli do testowania (domyślnie: EURUSD GBPUSD USDJPY XAUUSD)')
    parser.add_argument('--timeframes', type=str, nargs='+', default=["M1", "M5", "M15", "H1", "D1"],
                        help='Lista timeframe\'ów do testowania (domyślnie: M1 M5 M15 H1 D1)')
    parser.add_argument('--bars', type=int, nargs='+', default=[100, 500, 1000],
                        help='Lista liczby świec do pobrania (domyślnie: 100 500 1000)')
    parser.add_argument('--iterations', type=int, default=3,
                        help='Liczba powtórzeń testu (domyślnie: 3)')
    parser.add_argument('--quick', action='store_true',
                        help='Szybki test tylko dla jednego symbolu i timeframe\'u')
    parser.add_argument('--no-plots', action='store_true',
                        help='Nie generuj wykresów')
    
    args = parser.parse_args()
    
    # Jeśli wybrano szybki test, zredukuj liczbę symboli i timeframe'ów
    if args.quick:
        args.symbols = [args.symbols[0]]
        args.timeframes = [args.timeframes[0]]
        args.bars = [args.bars[0]]
        args.iterations = 1
        print(f"Uruchamiam szybki test dla symbolu {args.symbols[0]}, timeframe {args.timeframes[0]}, {args.bars[0]} świec")
    
    # Utwórz katalog dla wyników, jeśli nie istnieje
    os.makedirs("logs/performance_tests", exist_ok=True)
    
    print(f"Uruchamiam test wydajności pobierania danych rynkowych z MT5")
    print(f"Symbole: {args.symbols}")
    print(f"Timeframe'y: {args.timeframes}")
    print(f"Liczba świec: {args.bars}")
    print(f"Liczba powtórzeń: {args.iterations}")
    print(f"Generowanie wykresów: {'Nie' if args.no_plots else 'Tak'}")
    print("-" * 80)
    
    start_time = time.time()
    
    # Importuj testy (tu, aby uniknąć importów podczas analizy argumentów)
    from src.tests.test_market_data_performance import (
        test_historical_data_performance,
        test_market_data_processor_performance,
        generate_report,
        MT5Connector,
        MarketDataProcessor
    )
    
    try:
        # Inicjalizacja komponentów
        mt5_connector = MT5Connector()
        data_processor = MarketDataProcessor()
        
        # Testowanie połączenia
        if not mt5_connector.connect():
            print("Błąd: Nie można połączyć się z MT5. Przerywam test.")
            return 1
            
        print(f"Połączono z MT5 pomyślnie")
        
        # Testowanie wydajności pobierania surowych danych
        raw_results = test_historical_data_performance(
            connector=mt5_connector,
            symbols=args.symbols,
            timeframes=args.timeframes,
            num_bars=args.bars,
            num_iterations=args.iterations
        )
        
        # Testowanie wydajności procesora danych
        processor_results = test_market_data_processor_performance(
            processor=data_processor,
            symbols=args.symbols,
            timeframes=args.timeframes,
            num_bars=args.bars,
            num_iterations=args.iterations
        )
        
        # Generowanie raportu
        generate_report(raw_results, processor_results)
        
        end_time = time.time()
        print(f"Test wydajności zakończony pomyślnie")
        print(f"Czas wykonania: {end_time - start_time:.2f} sekund")
        print(f"Wyniki dostępne w katalogu logs/performance_tests")
        
        return 0
        
    except Exception as e:
        print(f"Błąd podczas testu wydajności: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main()) 