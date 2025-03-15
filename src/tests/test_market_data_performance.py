#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Test wydajności pobierania danych rynkowych z MT5.
"""

import os
import sys
import time
import logging
import psutil
import threading
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
from typing import Dict, List, Any, Tuple, Optional

# Dodanie ścieżki głównej projektu
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Import komponentów systemu
from src.mt5_bridge.mt5_connector import MT5Connector
from src.analysis.market_data_processor import MarketDataProcessor
from src.utils.logger import setup_logger

# Konfiguracja logowania
logger = setup_logger("market_data_performance", "logs/market_data_performance.log")

class PerformanceMetrics:
    """Klasa przechowująca metryki wydajności."""
    
    def __init__(self):
        self.cpu_usage = []
        self.memory_usage = []
        self.times = []
        self.data_points = []
        
    def add_metrics(self, cpu: float, memory: float, execution_time: float, data_points: int):
        """Dodaje metryki do historii."""
        self.cpu_usage.append(cpu)
        self.memory_usage.append(memory)
        self.times.append(execution_time)
        self.data_points.append(data_points)
        
    def get_summary(self) -> Dict[str, Any]:
        """Zwraca podsumowanie metryk."""
        return {
            "avg_cpu_usage": np.mean(self.cpu_usage) if self.cpu_usage else 0,
            "max_cpu_usage": np.max(self.cpu_usage) if self.cpu_usage else 0,
            "avg_memory_usage_mb": np.mean(self.memory_usage) / (1024 * 1024) if self.memory_usage else 0,
            "max_memory_usage_mb": np.max(self.memory_usage) / (1024 * 1024) if self.memory_usage else 0,
            "avg_execution_time_ms": np.mean(self.times) * 1000 if self.times else 0,
            "max_execution_time_ms": np.max(self.times) * 1000 if self.times else 0,
            "min_execution_time_ms": np.min(self.times) * 1000 if self.times else 0,
            "total_tests": len(self.times),
            "total_data_points": sum(self.data_points)
        }
        
    def plot_results(self, title: str = "Wydajność pobierania danych", output_file: Optional[str] = None):
        """Rysuje wykresy wydajności."""
        plt.figure(figsize=(12, 10))
        
        # Wykres czasu wykonania
        plt.subplot(3, 1, 1)
        plt.plot(self.times, 'r-')
        plt.title(f"{title} - Czas wykonania (s)")
        plt.xlabel("Próba")
        plt.ylabel("Czas (s)")
        plt.grid(True)
        
        # Wykres użycia CPU
        plt.subplot(3, 1, 2)
        plt.plot(self.cpu_usage, 'g-')
        plt.title("Użycie CPU (%)")
        plt.xlabel("Próba")
        plt.ylabel("CPU (%)")
        plt.grid(True)
        
        # Wykres użycia pamięci
        plt.subplot(3, 1, 3)
        plt.plot([m / (1024 * 1024) for m in self.memory_usage], 'b-')
        plt.title("Użycie pamięci (MB)")
        plt.xlabel("Próba")
        plt.ylabel("Pamięć (MB)")
        plt.grid(True)
        
        plt.tight_layout()
        
        if output_file:
            plt.savefig(output_file)
        else:
            plt.show()


def test_historical_data_performance(
    connector: MT5Connector,
    symbols: List[str],
    timeframes: List[str],
    num_bars: List[int],
    num_iterations: int = 5
) -> Dict[str, PerformanceMetrics]:
    """
    Testuje wydajność pobierania danych historycznych.
    
    Args:
        connector: Połączenie z MT5
        symbols: Lista symboli do testowania
        timeframes: Lista timeframe'ów do testowania
        num_bars: Lista liczby świec do pobrania
        num_iterations: Liczba powtórzeń testu
        
    Returns:
        Dict[str, PerformanceMetrics]: Słownik z metrykami wydajności
    """
    process = psutil.Process(os.getpid())
    results = {}
    
    for symbol in symbols:
        for timeframe in timeframes:
            for bars in num_bars:
                test_name = f"{symbol}_{timeframe}_{bars}_bars"
                logger.info(f"Rozpoczynam test: {test_name}")
                
                metrics = PerformanceMetrics()
                
                for i in range(num_iterations):
                    # Pomiar przed rozpoczęciem
                    cpu_before = psutil.cpu_percent(interval=None)
                    memory_before = process.memory_info().rss
                    
                    # Pobranie danych
                    start_time = time.time()
                    data = connector.get_historical_data(symbol, timeframe, count=bars)
                    execution_time = time.time() - start_time
                    
                    # Pomiar po zakończeniu
                    cpu_after = psutil.cpu_percent(interval=0.1)
                    memory_after = process.memory_info().rss
                    
                    # Dodanie metryk
                    data_points = len(data) if data is not None else 0
                    metrics.add_metrics(
                        cpu=cpu_after - cpu_before,
                        memory=memory_after - memory_before,
                        execution_time=execution_time,
                        data_points=data_points
                    )
                    
                    logger.info(f"Iteracja {i+1}/{num_iterations}: {data_points} punktów danych, "
                              f"czas: {execution_time*1000:.2f}ms, CPU: {cpu_after-cpu_before:.2f}%, "
                              f"Pamięć: {(memory_after-memory_before)/(1024*1024):.2f}MB")
                    
                    # Krótkie oczekiwanie między iteracjami
                    time.sleep(0.5)
                
                # Zapisz wyniki
                results[test_name] = metrics
                summary = metrics.summary = metrics.get_summary()
                
                logger.info(f"Podsumowanie testu {test_name}:")
                logger.info(f"  Średni czas wykonania: {summary['avg_execution_time_ms']:.2f}ms")
                logger.info(f"  Maksymalny czas wykonania: {summary['max_execution_time_ms']:.2f}ms")
                logger.info(f"  Minimalny czas wykonania: {summary['min_execution_time_ms']:.2f}ms")
                logger.info(f"  Średnie użycie CPU: {summary['avg_cpu_usage']:.2f}%")
                logger.info(f"  Średnie użycie pamięci: {summary['avg_memory_usage_mb']:.2f}MB")
                logger.info(f"  Łącznie pobrano {summary['total_data_points']} punktów danych")
                
                # Generowanie wykresu
                output_dir = "logs/performance_tests"
                os.makedirs(output_dir, exist_ok=True)
                metrics.plot_results(
                    title=f"Wydajność pobierania danych - {symbol} {timeframe} ({bars} świec)",
                    output_file=f"{output_dir}/{test_name}.png"
                )
    
    return results


def test_market_data_processor_performance(
    processor: MarketDataProcessor,
    symbols: List[str],
    timeframes: List[str],
    num_bars: List[int],
    num_iterations: int = 5
) -> Dict[str, PerformanceMetrics]:
    """
    Testuje wydajność procesora danych rynkowych.
    
    Args:
        processor: Procesor danych rynkowych
        symbols: Lista symboli do testowania
        timeframes: Lista timeframe'ów do testowania
        num_bars: Lista liczby świec do pobrania
        num_iterations: Liczba powtórzeń testu
        
    Returns:
        Dict[str, PerformanceMetrics]: Słownik z metrykami wydajności
    """
    process = psutil.Process(os.getpid())
    results = {}
    
    for symbol in symbols:
        for timeframe in timeframes:
            for bars in num_bars:
                test_name = f"processor_{symbol}_{timeframe}_{bars}_bars"
                logger.info(f"Rozpoczynam test procesora: {test_name}")
                
                metrics = PerformanceMetrics()
                
                for i in range(num_iterations):
                    # Pomiar przed rozpoczęciem
                    cpu_before = psutil.cpu_percent(interval=None)
                    memory_before = process.memory_info().rss
                    
                    # Pobranie i przetworzenie danych
                    start_time = time.time()
                    market_data = processor.get_market_data(symbol, timeframe, num_bars=bars)
                    execution_time = time.time() - start_time
                    
                    # Pomiar po zakończeniu
                    cpu_after = psutil.cpu_percent(interval=0.1)
                    memory_after = process.memory_info().rss
                    
                    # Dodanie metryk
                    data_points = len(market_data.get('data', [])) if market_data and 'data' in market_data else 0
                    metrics.add_metrics(
                        cpu=cpu_after - cpu_before,
                        memory=memory_after - memory_before,
                        execution_time=execution_time,
                        data_points=data_points
                    )
                    
                    logger.info(f"Iteracja {i+1}/{num_iterations}: {data_points} punktów danych, "
                              f"czas: {execution_time*1000:.2f}ms, CPU: {cpu_after-cpu_before:.2f}%, "
                              f"Pamięć: {(memory_after-memory_before)/(1024*1024):.2f}MB")
                    
                    # Czyszczenie cache'a między iteracjami
                    processor._clear_cache(symbol, timeframe)
                    
                    # Krótkie oczekiwanie między iteracjami
                    time.sleep(0.5)
                
                # Zapisz wyniki
                results[test_name] = metrics
                summary = metrics.summary = metrics.get_summary()
                
                logger.info(f"Podsumowanie testu procesora {test_name}:")
                logger.info(f"  Średni czas wykonania: {summary['avg_execution_time_ms']:.2f}ms")
                logger.info(f"  Maksymalny czas wykonania: {summary['max_execution_time_ms']:.2f}ms")
                logger.info(f"  Minimalny czas wykonania: {summary['min_execution_time_ms']:.2f}ms")
                logger.info(f"  Średnie użycie CPU: {summary['avg_cpu_usage']:.2f}%")
                logger.info(f"  Średnie użycie pamięci: {summary['avg_memory_usage_mb']:.2f}MB")
                logger.info(f"  Łącznie pobrano {summary['total_data_points']} punktów danych")
                
                # Generowanie wykresu
                output_dir = "logs/performance_tests"
                os.makedirs(output_dir, exist_ok=True)
                metrics.plot_results(
                    title=f"Wydajność procesora danych - {symbol} {timeframe} ({bars} świec)",
                    output_file=f"{output_dir}/{test_name}.png"
                )
    
    return results


def generate_report(
    raw_results: Dict[str, PerformanceMetrics],
    processor_results: Dict[str, PerformanceMetrics]
) -> None:
    """
    Generuje raport HTML z wynikami testów.
    
    Args:
        raw_results: Wyniki dla pobierania surowych danych
        processor_results: Wyniki dla procesora danych
    """
    output_dir = "logs/performance_tests"
    os.makedirs(output_dir, exist_ok=True)
    
    # Tworzenie ramki danych z wynikami
    results_data = []
    
    for test_name, metrics in raw_results.items():
        summary = metrics.get_summary()
        parts = test_name.split('_')
        symbol = parts[0]
        timeframe = parts[1]
        bars = parts[2]
        
        results_data.append({
            'Typ testu': 'Surowe dane',
            'Symbol': symbol,
            'Timeframe': timeframe,
            'Liczba świec': bars,
            'Średni czas (ms)': round(summary['avg_execution_time_ms'], 2),
            'Max czas (ms)': round(summary['max_execution_time_ms'], 2),
            'Min czas (ms)': round(summary['min_execution_time_ms'], 2),
            'Średnie CPU (%)': round(summary['avg_cpu_usage'], 2),
            'Średnia pamięć (MB)': round(summary['avg_memory_usage_mb'], 2),
            'Punkty danych': summary['total_data_points']
        })
    
    for test_name, metrics in processor_results.items():
        summary = metrics.get_summary()
        parts = test_name.split('_')
        symbol = parts[1]
        timeframe = parts[2]
        bars = parts[3]
        
        results_data.append({
            'Typ testu': 'Procesor danych',
            'Symbol': symbol,
            'Timeframe': timeframe,
            'Liczba świec': bars,
            'Średni czas (ms)': round(summary['avg_execution_time_ms'], 2),
            'Max czas (ms)': round(summary['max_execution_time_ms'], 2),
            'Min czas (ms)': round(summary['min_execution_time_ms'], 2),
            'Średnie CPU (%)': round(summary['avg_cpu_usage'], 2),
            'Średnia pamięć (MB)': round(summary['avg_memory_usage_mb'], 2),
            'Punkty danych': summary['total_data_points']
        })
    
    df = pd.DataFrame(results_data)
    
    # Generowanie HTML
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Raport wydajności pobierania danych - {datetime.now().strftime('%Y-%m-%d %H:%M')}</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; }}
            h1, h2 {{ color: #333366; }}
            table {{ border-collapse: collapse; width: 100%; margin-top: 20px; }}
            th, td {{ border: 1px solid #dddddd; text-align: left; padding: 8px; }}
            th {{ background-color: #f2f2f2; }}
            tr:nth-child(even) {{ background-color: #f9f9f9; }}
            .summary {{ background-color: #e6f7ff; font-weight: bold; }}
            .chart-container {{ margin-top: 30px; }}
            img {{ max-width: 100%; border: 1px solid #ddd; }}
        </style>
    </head>
    <body>
        <h1>Raport wydajności pobierania danych rynkowych</h1>
        <p>Wygenerowano: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        
        <h2>Podsumowanie wyników</h2>
        {df.to_html(index=False)}
        
        <h2>Wykresy wydajności</h2>
        <div class="chart-container">
    """
    
    # Dodanie wykresów
    for test_name in raw_results.keys():
        html_content += f"""
            <h3>Surowe dane: {test_name}</h3>
            <img src="{test_name}.png" alt="Wykres wydajności {test_name}">
        """
    
    for test_name in processor_results.keys():
        html_content += f"""
            <h3>Procesor danych: {test_name}</h3>
            <img src="{test_name}.png" alt="Wykres wydajności {test_name}">
        """
    
    html_content += """
        </div>
    </body>
    </html>
    """
    
    # Zapis raportu do pliku
    report_path = f"{output_dir}/performance_report_{datetime.now().strftime('%Y%m%d_%H%M')}.html"
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    logger.info(f"Raport wygenerowany: {report_path}")


def main():
    """Główna funkcja testująca."""
    try:
        logger.info("Rozpoczynam test wydajności pobierania danych rynkowych")
        
        # Inicjalizacja komponentów
        mt5_connector = MT5Connector()
        data_processor = MarketDataProcessor()
        
        # Parametry testów
        symbols = ["EURUSD", "GBPUSD", "USDJPY", "XAUUSD", "BTCUSD"]
        timeframes = ["M1", "M5", "M15", "H1", "D1"]
        bar_counts = [100, 500, 1000]
        iterations = 3
        
        # Testowanie połączenia
        if not mt5_connector.connect():
            logger.error("Nie można połączyć się z MT5. Przerywam test.")
            return
            
        logger.info("Połączono z MT5 pomyślnie")
        
        # Testowanie wydajności pobierania surowych danych
        raw_results = test_historical_data_performance(
            connector=mt5_connector,
            symbols=symbols,
            timeframes=timeframes,
            num_bars=bar_counts,
            num_iterations=iterations
        )
        
        # Testowanie wydajności procesora danych
        processor_results = test_market_data_processor_performance(
            processor=data_processor,
            symbols=symbols,
            timeframes=timeframes,
            num_bars=bar_counts,
            num_iterations=iterations
        )
        
        # Generowanie raportu
        generate_report(raw_results, processor_results)
        
        logger.info("Test wydajności zakończony pomyślnie")
        
    except Exception as e:
        logger.exception(f"Błąd podczas testu wydajności: {str(e)}")


if __name__ == "__main__":
    main() 