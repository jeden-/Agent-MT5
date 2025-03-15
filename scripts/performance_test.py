#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Skrypt do testowania wydajności kluczowych komponentów systemu AgentMT5.
"""

import os
import sys
import time
import logging
import argparse
import random
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import statistics
import threading
import matplotlib.pyplot as plt

# Dodanie ścieżki głównej projektu do sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.mt5_bridge.trading_service import TradingService
from src.mt5_bridge.mt5_connector import MT5Connector
from src.monitoring.status_reporter import get_status_reporter

# Konfiguracja logowania
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("performance_test")

class PerformanceTest:
    """Klasa do przeprowadzania testów wydajnościowych."""
    
    def __init__(self, iterations: int = 10, symbols: List[str] = None):
        """
        Inicjalizacja testu wydajnościowego.
        
        Args:
            iterations: Liczba iteracji dla każdego testu
            symbols: Lista symboli do testowania (domyślnie: EURUSD, GBPUSD, USDJPY)
        """
        self.iterations = iterations
        self.symbols = symbols or ["EURUSD", "GBPUSD", "USDJPY"]
        self.results = {}
        self.trading_service = TradingService()
        
        # Połączenie z MT5
        if not self.trading_service.connect():
            logger.error("Nie można połączyć się z MT5. Przerywanie testów wydajnościowych.")
            sys.exit(1)
        
        logger.info(f"Rozpoczynam testy wydajnościowe na {len(self.symbols)} symbolach z {iterations} iteracjami.")
        
    def run_all_tests(self, with_caching: bool = True, with_batch_processing: bool = True):
        """
        Uruchamia wszystkie testy wydajnościowe.
        
        Args:
            with_caching: Czy używać buforowania danych
            with_batch_processing: Czy używać wsadowego przetwarzania danych
        """
        # Ustaw konfigurację testów
        self.with_caching = with_caching
        self.with_batch_processing = with_batch_processing
        
        logger.info(f"Konfiguracja testów: buforowanie={with_caching}, wsadowe przetwarzanie={with_batch_processing}")
        
        # Test 1: Pobieranie danych rynkowych
        self.test_get_market_data()
        
        # Test 2: Pobieranie otwartych pozycji
        self.test_get_open_positions()
        
        # Test 3: Aktualizacja trailing stop
        self.test_update_trailing_stops()
        
        # Test 4: Zarządzanie break-even stops
        self.test_manage_breakeven_stops()
        
        # Test 5: Zarządzanie częściowym zamykaniem pozycji
        self.test_manage_take_profits()
        
        # Test 6: Monitorowanie zleceń OCO
        self.test_monitor_oco_orders()
        
        # Wyświetl wyniki
        self.display_results()
        
    def test_get_market_data(self):
        """Test wydajności pobierania danych rynkowych."""
        logger.info("Test 1: Pobieranie danych rynkowych")
        
        times = []
        
        for _ in range(self.iterations):
            start_time = time.time()
            
            # Pobierz dane rynkowe dla wszystkich symboli
            for symbol in self.symbols:
                market_data = self.trading_service.get_market_data(symbol)
                
            elapsed_time = (time.time() - start_time) * 1000  # w milisekundach
            times.append(elapsed_time)
            
            # Jeśli używamy buforowania, wymuszamy odświeżenie bufora po każdej iteracji
            if self.with_caching and hasattr(self.trading_service.connector, 'invalidate_cache'):
                for symbol in self.symbols:
                    self.trading_service.connector.invalidate_cache('market_data', symbol)
        
        self.results['get_market_data'] = self._calc_statistics(times)
        logger.info(f"Wynik: {self.results['get_market_data']['mean']:.2f} ms średnio")
    
    def test_get_open_positions(self):
        """Test wydajności pobierania otwartych pozycji."""
        logger.info("Test 2: Pobieranie otwartych pozycji")
        
        times = []
        
        for _ in range(self.iterations):
            start_time = time.time()
            
            # Pobierz otwarte pozycje
            positions = self.trading_service.get_open_positions()
            
            elapsed_time = (time.time() - start_time) * 1000  # w milisekundach
            times.append(elapsed_time)
            
            # Jeśli używamy buforowania, wymuszamy odświeżenie bufora po każdej iteracji
            if self.with_caching and hasattr(self.trading_service.connector, 'invalidate_cache'):
                self.trading_service.connector.invalidate_cache('positions')
        
        self.results['get_open_positions'] = self._calc_statistics(times)
        logger.info(f"Wynik: {self.results['get_open_positions']['mean']:.2f} ms średnio")
    
    def test_update_trailing_stops(self):
        """Test wydajności aktualizacji trailing stop."""
        logger.info("Test 3: Aktualizacja trailing stop")
        
        times = []
        
        for _ in range(self.iterations):
            start_time = time.time()
            
            # Aktualizuj trailing stopy
            if self.with_batch_processing:
                self.trading_service.update_trailing_stops()
            else:
                # Ręczne przetwarzanie bez wsadowego
                positions = self.trading_service.get_open_positions()
                for position in positions or []:
                    ticket = position.get('ticket')
                    if ticket:
                        self.trading_service.apply_trailing_stop(ticket)
            
            elapsed_time = (time.time() - start_time) * 1000  # w milisekundach
            times.append(elapsed_time)
        
        self.results['update_trailing_stops'] = self._calc_statistics(times)
        logger.info(f"Wynik: {self.results['update_trailing_stops']['mean']:.2f} ms średnio")
    
    def test_manage_breakeven_stops(self):
        """Test wydajności zarządzania break-even stops."""
        logger.info("Test 4: Zarządzanie break-even stops")
        
        times = []
        
        for _ in range(self.iterations):
            start_time = time.time()
            
            # Zarządzaj break-even stops
            if self.with_batch_processing:
                self.trading_service.manage_breakeven_stops()
            else:
                # Ręczne przetwarzanie bez wsadowego
                positions = self.trading_service.get_open_positions()
                for position in positions or []:
                    ticket = position.get('ticket')
                    if ticket:
                        self.trading_service.advanced_breakeven_stop(ticket)
            
            elapsed_time = (time.time() - start_time) * 1000  # w milisekundach
            times.append(elapsed_time)
        
        self.results['manage_breakeven_stops'] = self._calc_statistics(times)
        logger.info(f"Wynik: {self.results['manage_breakeven_stops']['mean']:.2f} ms średnio")
    
    def test_manage_take_profits(self):
        """Test wydajności zarządzania częściowym zamykaniem pozycji."""
        logger.info("Test 5: Zarządzanie częściowym zamykaniem pozycji")
        
        times = []
        
        for _ in range(self.iterations):
            start_time = time.time()
            
            # Zarządzaj częściowym zamykaniem pozycji
            self.trading_service.manage_take_profits()
            
            elapsed_time = (time.time() - start_time) * 1000  # w milisekundach
            times.append(elapsed_time)
        
        self.results['manage_take_profits'] = self._calc_statistics(times)
        logger.info(f"Wynik: {self.results['manage_take_profits']['mean']:.2f} ms średnio")
    
    def test_monitor_oco_orders(self):
        """Test wydajności monitorowania zleceń OCO."""
        logger.info("Test 6: Monitorowanie zleceń OCO")
        
        times = []
        
        for _ in range(self.iterations):
            start_time = time.time()
            
            # Monitoruj zlecenia OCO
            self.trading_service.monitor_oco_orders()
            
            elapsed_time = (time.time() - start_time) * 1000  # w milisekundach
            times.append(elapsed_time)
        
        self.results['monitor_oco_orders'] = self._calc_statistics(times)
        logger.info(f"Wynik: {self.results['monitor_oco_orders']['mean']:.2f} ms średnio")
    
    def _calc_statistics(self, times: List[float]) -> Dict[str, float]:
        """
        Oblicza statystyki na podstawie wyników pomiarów.
        
        Args:
            times: Lista czasów wykonania w milisekundach
            
        Returns:
            Dict: Statystyki (min, max, mean, median, stdev)
        """
        return {
            'min': min(times),
            'max': max(times),
            'mean': statistics.mean(times),
            'median': statistics.median(times),
            'stdev': statistics.stdev(times) if len(times) > 1 else 0
        }
    
    def display_results(self):
        """Wyświetla wyniki testów wydajnościowych."""
        logger.info("\n=== WYNIKI TESTÓW WYDAJNOŚCIOWYCH ===")
        logger.info(f"Konfiguracja: buforowanie={self.with_caching}, wsadowe przetwarzanie={self.with_batch_processing}")
        logger.info(f"Liczba iteracji: {self.iterations}")
        
        for test_name, stats in self.results.items():
            logger.info(f"\n{test_name}:")
            logger.info(f"  Min: {stats['min']:.2f} ms")
            logger.info(f"  Max: {stats['max']:.2f} ms")
            logger.info(f"  Mean: {stats['mean']:.2f} ms")
            logger.info(f"  Median: {stats['median']:.2f} ms")
            logger.info(f"  Std dev: {stats['stdev']:.2f} ms")
    
    def plot_results(self, filename: str = "performance_results.png"):
        """
        Generuje wykres z wynikami testów wydajnościowych.
        
        Args:
            filename: Nazwa pliku do zapisania wykresu
        """
        test_names = list(self.results.keys())
        means = [stats['mean'] for stats in self.results.values()]
        
        plt.figure(figsize=(12, 8))
        plt.barh(test_names, means, color='skyblue')
        
        plt.title("Wyniki testów wydajnościowych (średni czas wykonania)", fontsize=14)
        plt.xlabel("Czas (ms)", fontsize=12)
        
        # Dodaj wartości przy słupkach
        for i, v in enumerate(means):
            plt.text(v + 1, i, f"{v:.2f} ms", va='center')
            
        plt.grid(axis='x', linestyle='--', alpha=0.7)
        plt.tight_layout()
        
        plt.savefig(filename)
        logger.info(f"Wykres zapisany do pliku: {filename}")
        
    def disconnect(self):
        """Zamyka połączenie z MT5."""
        self.trading_service.disconnect()
        logger.info("Testy wydajnościowe zakończone.")

def run_comparison_tests():
    """Uruchamia testy porównawcze dla różnych konfiguracji."""
    results = {}
    
    # Test 1: Bez buforowania i wsadowego przetwarzania
    logger.info("\n=== TEST 1: Bez buforowania i wsadowego przetwarzania ===")
    test1 = PerformanceTest(iterations=5)
    test1.run_all_tests(with_caching=False, with_batch_processing=False)
    results['standard'] = test1.results
    test1.disconnect()
    
    time.sleep(2)  # Pauza między testami
    
    # Test 2: Z buforowaniem, bez wsadowego przetwarzania
    logger.info("\n=== TEST 2: Z buforowaniem, bez wsadowego przetwarzania ===")
    test2 = PerformanceTest(iterations=5)
    test2.run_all_tests(with_caching=True, with_batch_processing=False)
    results['cached'] = test2.results
    test2.disconnect()
    
    time.sleep(2)  # Pauza między testami
    
    # Test 3: Z buforowaniem i wsadowym przetwarzaniem
    logger.info("\n=== TEST 3: Z buforowaniem i wsadowym przetwarzaniem ===")
    test3 = PerformanceTest(iterations=5)
    test3.run_all_tests(with_caching=True, with_batch_processing=True)
    results['optimized'] = test3.results
    test3.disconnect()
    
    # Generuj wykres porównawczy
    plot_comparison(results)

def plot_comparison(results: Dict[str, Dict[str, Dict[str, float]]]):
    """
    Generuje wykres porównawczy dla różnych konfiguracji.
    
    Args:
        results: Słownik wyników dla różnych konfiguracji
    """
    test_names = list(results['standard'].keys())
    
    # Przygotuj dane do wykresu
    data = {
        'Standard': [results['standard'][test]['mean'] for test in test_names],
        'Cached': [results['cached'][test]['mean'] for test in test_names],
        'Optimized': [results['optimized'][test]['mean'] for test in test_names]
    }
    
    # Oblicz przyspieszenie
    speedups = {
        'Cached vs Standard': [(results['standard'][test]['mean'] / results['cached'][test]['mean']) for test in test_names],
        'Optimized vs Standard': [(results['standard'][test]['mean'] / results['optimized'][test]['mean']) for test in test_names]
    }
    
    # Tworzenie wykresu
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 12), gridspec_kw={'height_ratios': [3, 1]})
    
    bar_width = 0.25
    x = range(len(test_names))
    
    # Wykres 1: Czasy wykonania
    ax1.bar([i - bar_width for i in x], data['Standard'], width=bar_width, label='Standard', color='lightblue')
    ax1.bar(x, data['Cached'], width=bar_width, label='Cached', color='skyblue')
    ax1.bar([i + bar_width for i in x], data['Optimized'], width=bar_width, label='Optimized', color='steelblue')
    
    ax1.set_title("Porównanie czasów wykonania dla różnych konfiguracji", fontsize=14)
    ax1.set_ylabel("Czas (ms)", fontsize=12)
    ax1.set_xticks(x)
    ax1.set_xticklabels([])
    ax1.legend()
    ax1.grid(axis='y', linestyle='--', alpha=0.7)
    
    # Wykres 2: Przyspieszenie
    ax2.bar([i - bar_width/2 for i in x], speedups['Cached vs Standard'], width=bar_width, label='Cached vs Standard', color='lightgreen')
    ax2.bar([i + bar_width/2 for i in x], speedups['Optimized vs Standard'], width=bar_width, label='Optimized vs Standard', color='forestgreen')
    
    ax2.set_title("Przyspieszenie względem konfiguracji standardowej", fontsize=14)
    ax2.set_ylabel("Przyspieszenie (x razy)", fontsize=12)
    ax2.set_xlabel("Test", fontsize=12)
    ax2.set_xticks(x)
    ax2.set_xticklabels(test_names, rotation=45, ha='right')
    ax2.legend()
    ax2.grid(axis='y', linestyle='--', alpha=0.7)
    
    # Dodaj wartości przy słupkach
    for i, v in enumerate(speedups['Optimized vs Standard']):
        ax2.text(i + bar_width/2, v + 0.1, f"{v:.2f}x", ha='center')
    
    plt.tight_layout()
    plt.savefig("performance_comparison.png")
    logger.info("Wykres porównawczy zapisany do pliku: performance_comparison.png")

def main():
    """Funkcja główna."""
    parser = argparse.ArgumentParser(description='Testy wydajnościowe dla AgentMT5')
    parser.add_argument('--iterations', type=int, default=5, help='Liczba iteracji dla każdego testu')
    parser.add_argument('--comparison', action='store_true', help='Uruchom testy porównawcze')
    parser.add_argument('--caching', action='store_true', help='Użyj buforowania danych')
    parser.add_argument('--batch', action='store_true', help='Użyj wsadowego przetwarzania')
    
    args = parser.parse_args()
    
    if args.comparison:
        run_comparison_tests()
    else:
        test = PerformanceTest(iterations=args.iterations)
        test.run_all_tests(with_caching=args.caching, with_batch_processing=args.batch)
        test.plot_results()
        test.disconnect()

if __name__ == "__main__":
    main() 