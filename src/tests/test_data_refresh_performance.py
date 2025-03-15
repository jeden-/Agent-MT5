#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Test wydajności mechanizmu regularnego odświeżania danych rynkowych.
Ten test weryfikuje wydajność pobierania danych historycznych i bieżących
z MT5 wykorzystując nowy mechanizm DataRefreshManager.
"""

import os
import sys
import time
import logging
import psutil
import threading
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
from typing import Dict, List, Any, Tuple, Optional
import multiprocessing
import traceback

# Dodanie ścieżki głównej projektu
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Import komponentów systemu
from src.mt5_bridge.mt5_connector import MT5Connector
from src.scheduler import DataRefreshManager, Scheduler
from src.utils.logger import setup_logger

# Konfiguracja logowania
import logging

# Upewnij się, że katalog logów istnieje
os.makedirs("logs", exist_ok=True)

# Konfiguracja loggera
logger = logging.getLogger("data_refresh_performance")
logger.setLevel(logging.INFO)

# Dodanie handlera pliku
file_handler = logging.FileHandler("logs/data_refresh_performance.log")
file_handler.setLevel(logging.INFO)

# Dodanie handlera konsoli
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)

# Dodanie formatera
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)
console_handler.setFormatter(formatter)

# Dodanie handlerów do loggera
logger.addHandler(file_handler)
logger.addHandler(console_handler)

class RefreshPerformanceTest:
    """Klasa testująca wydajność mechanizmu odświeżania danych."""
    
    def __init__(self):
        """Inicjalizacja testu wydajności."""
        self.mt5_connector = MT5Connector()
        if not self.mt5_connector.connect():
            logger.error("Nie można połączyć się z MT5!")
            raise ConnectionError("Nie można połączyć się z MT5")
            
        self.refresh_manager = DataRefreshManager(self.mt5_connector)
        
        # Metryki wydajności
        self.symbols = ["EURUSD", "GBPUSD", "USDJPY", "GOLD", "SILVER"]
        self.timeframes = ["M1", "M5", "M15", "H1", "D1"]
        
        # Wyniki testów
        self.results = {
            "single_refresh": {},
            "parallel_refresh": {},
            "sequential_refresh": {},
            "long_running": {}
        }
        
    def test_single_refresh(self, iterations: int = 5):
        """
        Test wydajności pojedynczego odświeżenia.
        
        Args:
            iterations: Liczba powtórzeń dla każdej kombinacji
        """
        logger.info("Rozpoczynam test pojedynczego odświeżenia...")
        
        for symbol in self.symbols:
            self.results["single_refresh"][symbol] = {}
            
            for timeframe in self.timeframes:
                metrics = []
                
                for i in range(iterations):
                    # Pomiar CPU i pamięci przed
                    cpu_before = psutil.cpu_percent()
                    process = psutil.Process(os.getpid())
                    memory_before = process.memory_info().rss / 1024 / 1024  # MB
                    
                    # Wykonanie testu
                    start_time = time.time()
                    result = self.refresh_manager.refresh_data(symbol, [timeframe])
                    elapsed = time.time() - start_time
                    
                    # Pomiar CPU i pamięci po
                    cpu_after = psutil.cpu_percent()
                    memory_after = process.memory_info().rss / 1024 / 1024  # MB
                    
                    # Pobranie statystyk wydajności
                    stats = self.refresh_manager.get_performance_stats()
                    
                    # Zebranie metryki
                    metrics.append({
                        "iteration": i + 1,
                        "elapsed_time": elapsed,
                        "cpu_usage": cpu_after - cpu_before,
                        "memory_delta": memory_after - memory_before,
                        "success": result["success"],
                        "data_points": stats.get("data_size", 0) / (i + 1)  # Przybliżona wielkość danych
                    })
                    
                    logger.info(f"Symbol: {symbol}, Timeframe: {timeframe}, Iteracja {i+1}: "
                                f"Czas: {elapsed:.4f}s, Zmiana CPU: {cpu_after - cpu_before:.2f}%, "
                                f"Zmiana pamięci: {memory_after - memory_before:.2f} MB")
                
                # Zapisanie wyników
                self.results["single_refresh"][symbol][timeframe] = metrics
                
        logger.info("Test pojedynczego odświeżenia zakończony")
        
    def test_parallel_refresh(self, max_workers: int = 3):
        """
        Test wydajności równoległego odświeżania danych.
        
        Args:
            max_workers: Maksymalna liczba równoległych procesów
        """
        logger.info(f"Rozpoczynam test równoległego odświeżania (max_workers={max_workers})...")
        
        # Przygotowanie argumentów dla procesów
        args_list = []
        for symbol in self.symbols:
            for timeframe in self.timeframes:
                args_list.append((symbol, timeframe))
        
        # Pomiar czasu przed
        start_time = time.time()
        cpu_before = psutil.cpu_percent()
        process = psutil.Process(os.getpid())
        memory_before = process.memory_info().rss / 1024 / 1024  # MB
        
        # Ze względu na problemy z pickle, użyjemy threadingu zamiast multiprocessing
        results = []
        threads = []
        
        # Semafor do ograniczenia liczby równoległych wątków
        semaphore = threading.Semaphore(max_workers)
        
        # Funkcja dla wątku
        def thread_task(symbol, timeframe):
            semaphore.acquire()
            try:
                result = self.refresh_manager.refresh_data(symbol, [timeframe])
                results.append({
                    "symbol": symbol,
                    "timeframe": timeframe,
                    "success": result["success"],
                    "errors": result.get("errors", {})
                })
            finally:
                semaphore.release()
        
        # Tworzenie i uruchamianie wątków
        for symbol, timeframe in args_list:
            thread = threading.Thread(target=thread_task, args=(symbol, timeframe))
            threads.append(thread)
            thread.start()
        
        # Czekanie na zakończenie wszystkich wątków
        for thread in threads:
            thread.join()
        
        # Pomiar po wykonaniu
        elapsed = time.time() - start_time
        cpu_after = psutil.cpu_percent()
        memory_after = process.memory_info().rss / 1024 / 1024  # MB
        
        # Zapisanie wyników
        self.results["parallel_refresh"] = {
            "elapsed_time": elapsed,
            "cpu_delta": cpu_after - cpu_before,
            "memory_delta": memory_after - memory_before,
            "num_tasks": len(args_list),
            "tasks_per_second": len(args_list) / elapsed if elapsed > 0 else 0,
            "individual_results": results
        }
        
        logger.info(f"Test równoległego odświeżania zakończony: "
                    f"Czas całkowity: {elapsed:.4f}s, "
                    f"Zadań na sekundę: {len(args_list) / elapsed if elapsed > 0 else 0:.2f}, "
                    f"Zmiana CPU: {cpu_after - cpu_before:.2f}%, "
                    f"Zmiana pamięci: {memory_after - memory_before:.2f} MB")
        
    def test_sequential_refresh(self):
        """Test wydajności sekwencyjnego odświeżania wszystkich danych."""
        logger.info("Rozpoczynam test sekwencyjnego odświeżania...")
        
        # Pomiar przed
        start_time = time.time()
        cpu_before = psutil.cpu_percent()
        process = psutil.Process(os.getpid())
        memory_before = process.memory_info().rss / 1024 / 1024  # MB
        
        # Wykonanie testu
        all_results = {}
        for symbol in self.symbols:
            all_results[symbol] = {}
            for timeframe in self.timeframes:
                result = self.refresh_manager.refresh_data(symbol, [timeframe])
                all_results[symbol][timeframe] = result
        
        # Pomiar po
        elapsed = time.time() - start_time
        cpu_after = psutil.cpu_percent()
        memory_after = process.memory_info().rss / 1024 / 1024  # MB
        
        # Obliczenie liczby udanych i nieudanych odświeżeń
        success_count = 0
        error_count = 0
        for symbol in all_results:
            for timeframe in all_results[symbol]:
                if all_results[symbol][timeframe]["success"]:
                    success_count += 1
                else:
                    error_count += 1
        
        # Zapisanie wyników
        self.results["sequential_refresh"] = {
            "elapsed_time": elapsed,
            "cpu_delta": cpu_after - cpu_before,
            "memory_delta": memory_after - memory_before,
            "total_tasks": len(self.symbols) * len(self.timeframes),
            "success_count": success_count,
            "error_count": error_count,
            "tasks_per_second": (len(self.symbols) * len(self.timeframes)) / elapsed if elapsed > 0 else 0,
            "individual_results": all_results
        }
        
        logger.info(f"Test sekwencyjnego odświeżania zakończony: "
                   f"Czas całkowity: {elapsed:.4f}s, "
                   f"Udanych: {success_count}, Błędów: {error_count}, "
                   f"Zadań na sekundę: {(len(self.symbols) * len(self.timeframes)) / elapsed if elapsed > 0 else 0:.2f}")
        
    def test_long_running_refresh(self, duration_seconds: int = 300, interval_seconds: int = 10):
        """
        Test długotrwałego odświeżania danych.
        
        Args:
            duration_seconds: Całkowity czas trwania testu w sekundach
            interval_seconds: Interwał odświeżania w sekundach
        """
        logger.info(f"Rozpoczynam test długotrwałego odświeżania (czas trwania: {duration_seconds}s)...")
        
        # Statystyki
        refresh_count = 0
        total_elapsed = 0
        start_memory = psutil.Process(os.getpid()).memory_info().rss / 1024 / 1024  # MB
        cpu_readings = []
        memory_readings = []
        time_readings = []
        
        # Czas rozpoczęcia
        start_time = time.time()
        end_time = start_time + duration_seconds
        
        try:
            while time.time() < end_time:
                # Wykonaj odświeżenie dla losowego symbolu i timeframe'u
                symbol = np.random.choice(self.symbols)
                timeframe = np.random.choice(self.timeframes)
                
                # Pomiar
                refresh_start = time.time()
                self.refresh_manager.refresh_data(symbol, [timeframe])
                elapsed = time.time() - refresh_start
                
                # Aktualizacja statystyk
                refresh_count += 1
                total_elapsed += elapsed
                
                # Pomiar zasobów
                cpu = psutil.cpu_percent()
                memory = psutil.Process(os.getpid()).memory_info().rss / 1024 / 1024  # MB
                
                cpu_readings.append(cpu)
                memory_readings.append(memory)
                time_readings.append(time.time() - start_time)
                
                # Logowanie co 10 odświeżeń
                if refresh_count % 10 == 0:
                    logger.info(f"Wykonano {refresh_count} odświeżeń, "
                               f"średni czas: {total_elapsed / refresh_count:.4f}s, "
                               f"CPU: {cpu:.2f}%, Pamięć: {memory:.2f} MB")
                
                # Poczekaj na kolejny interwał
                time.sleep(max(0, interval_seconds - elapsed))
                
        except KeyboardInterrupt:
            logger.info("Test przerwany przez użytkownika")
        
        # Obliczenie końcowych statystyk
        final_time = time.time()
        actual_duration = final_time - start_time
        final_memory = psutil.Process(os.getpid()).memory_info().rss / 1024 / 1024  # MB
        
        # Zapisanie wyników
        self.results["long_running"] = {
            "refresh_count": refresh_count,
            "actual_duration": actual_duration,
            "avg_time_per_refresh": total_elapsed / refresh_count if refresh_count > 0 else 0,
            "avg_cpu": np.mean(cpu_readings),
            "max_cpu": np.max(cpu_readings),
            "memory_growth": final_memory - start_memory,
            "refreshes_per_second": refresh_count / actual_duration,
            "cpu_readings": cpu_readings,
            "memory_readings": memory_readings,
            "time_readings": time_readings
        }
        
        logger.info(f"Test długotrwałego odświeżania zakończony: "
                   f"Wykonano {refresh_count} odświeżeń w czasie {actual_duration:.2f}s, "
                   f"Średni czas odświeżenia: {total_elapsed / refresh_count if refresh_count > 0 else 0:.4f}s, "
                   f"Średnie CPU: {np.mean(cpu_readings):.2f}%, "
                   f"Wzrost pamięci: {final_memory - start_memory:.2f} MB")
        
    def plot_performance_results(self, output_dir: str = "performance_results"):
        """
        Generuje wykresy wyników testów wydajności.
        
        Args:
            output_dir: Katalog do zapisania wykresów
        """
        # Tworzenie katalogu wynikowego, jeśli nie istnieje
        os.makedirs(output_dir, exist_ok=True)
        
        # 1. Wykres dla pojedynczego odświeżenia
        if self.results["single_refresh"]:
            plt.figure(figsize=(12, 8))
            symbols = list(self.results["single_refresh"].keys())
            timeframes = list(self.results["single_refresh"][symbols[0]].keys())
            
            avg_times = {}
            for tf in timeframes:
                avg_times[tf] = []
                for symbol in symbols:
                    metrics = self.results["single_refresh"][symbol][tf]
                    avg_time = np.mean([m["elapsed_time"] for m in metrics])
                    avg_times[tf].append(avg_time)
            
            x = np.arange(len(symbols))
            width = 0.8 / len(timeframes)
            
            for i, tf in enumerate(timeframes):
                plt.bar(x + i * width - 0.4 + width/2, avg_times[tf], width, label=tf)
            
            plt.xlabel('Symbol')
            plt.ylabel('Średni czas wykonania (s)')
            plt.title('Średni czas odświeżania danych według symbolu i timeframe\'u')
            plt.xticks(x, symbols)
            plt.legend(title="Timeframe")
            plt.grid(True, linestyle='--', alpha=0.7)
            plt.tight_layout()
            plt.savefig(f"{output_dir}/single_refresh_times.png")
            plt.close()
        
        # 2. Wykres porównawczy sekwencyjne vs równoległe
        if "sequential_refresh" in self.results and "parallel_refresh" in self.results:
            plt.figure(figsize=(10, 6))
            labels = ['Sekwencyjne', 'Równoległe']
            times = [
                self.results["sequential_refresh"]["elapsed_time"],
                self.results["parallel_refresh"]["elapsed_time"]
            ]
            tasks_per_second = [
                self.results["sequential_refresh"]["tasks_per_second"],
                self.results["parallel_refresh"]["tasks_per_second"]
            ]
            
            fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
            
            ax1.bar(labels, times, color=['blue', 'green'])
            ax1.set_ylabel('Czas wykonania (s)')
            ax1.set_title('Całkowity czas wykonania')
            ax1.grid(True, linestyle='--', alpha=0.7)
            
            ax2.bar(labels, tasks_per_second, color=['blue', 'green'])
            ax2.set_ylabel('Zadań na sekundę')
            ax2.set_title('Wydajność (zadań/s)')
            ax2.grid(True, linestyle='--', alpha=0.7)
            
            plt.tight_layout()
            plt.savefig(f"{output_dir}/sequential_vs_parallel.png")
            plt.close()
        
        # 3. Wykres użycia zasobów dla długotrwałego testu
        if "long_running" in self.results:
            lr_results = self.results["long_running"]
            
            if "time_readings" in lr_results and len(lr_results["time_readings"]) > 0:
                fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8), sharex=True)
                
                ax1.plot(lr_results["time_readings"], lr_results["cpu_readings"], 'b-', label='CPU')
                ax1.set_ylabel('Użycie CPU (%)')
                ax1.set_title('Użycie CPU podczas długotrwałego testu')
                ax1.grid(True, linestyle='--', alpha=0.7)
                ax1.legend()
                
                ax2.plot(lr_results["time_readings"], lr_results["memory_readings"], 'r-', label='Pamięć')
                ax2.set_xlabel('Czas (s)')
                ax2.set_ylabel('Użycie pamięci (MB)')
                ax2.set_title('Użycie pamięci podczas długotrwałego testu')
                ax2.grid(True, linestyle='--', alpha=0.7)
                ax2.legend()
                
                plt.tight_layout()
                plt.savefig(f"{output_dir}/long_running_resources.png")
                plt.close()
        
    def generate_report(self, output_file: str = "performance_report.md"):
        """
        Generuje raport w formacie Markdown z wynikami testów.
        
        Args:
            output_file: Ścieżka do pliku wynikowego
        """
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("# Raport wydajności mechanizmu regularnego odświeżania danych\n\n")
            f.write(f"Data: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            # 1. Informacje o środowisku
            f.write("## Informacje o środowisku\n\n")
            f.write(f"- System: {sys.platform}\n")
            f.write(f"- Python: {sys.version.split()[0]}\n")
            f.write(f"- Procesor: {psutil.cpu_count(logical=False)} rdzeni fizycznych, {psutil.cpu_count()} wątków\n")
            f.write(f"- Pamięć: {psutil.virtual_memory().total / (1024 ** 3):.2f} GB całkowita\n")
            f.write("\n")
            
            # 2. Podsumowanie testów pojedynczego odświeżenia
            f.write("## Test pojedynczego odświeżenia\n\n")
            if self.results["single_refresh"]:
                f.write("| Symbol | Timeframe | Średni czas (s) | Średnie CPU (%) | Średnia pamięć (MB) |\n")
                f.write("|--------|-----------|-----------------|-----------------|---------------------|\n")
                
                for symbol in self.results["single_refresh"]:
                    for tf in self.results["single_refresh"][symbol]:
                        metrics = self.results["single_refresh"][symbol][tf]
                        avg_time = np.mean([m["elapsed_time"] for m in metrics])
                        avg_cpu = np.mean([m["cpu_usage"] for m in metrics])
                        avg_mem = np.mean([m["memory_delta"] for m in metrics])
                        
                        f.write(f"| {symbol} | {tf} | {avg_time:.4f} | {avg_cpu:.2f} | {avg_mem:.2f} |\n")
            else:
                f.write("Brak danych\n")
            f.write("\n")
            
            # 3. Porównanie sekwencyjnego i równoległego odświeżania
            f.write("## Porównanie sekwencyjnego i równoległego odświeżania\n\n")
            if "sequential_refresh" in self.results and "parallel_refresh" in self.results:
                seq = self.results["sequential_refresh"]
                par = self.results["parallel_refresh"]
                
                f.write("| Metryka | Sekwencyjne | Równoległe | Stosunek |\n")
                f.write("|---------|-------------|------------|----------|\n")
                f.write(f"| Całkowity czas (s) | {seq['elapsed_time']:.4f} | {par['elapsed_time']:.4f} | {seq['elapsed_time']/par['elapsed_time']:.2f} |\n")
                f.write(f"| Zadań na sekundę | {seq['tasks_per_second']:.2f} | {par['tasks_per_second']:.2f} | {par['tasks_per_second']/seq['tasks_per_second']:.2f} |\n")
                f.write(f"| Zmiana CPU (%) | {seq['cpu_delta']:.2f} | {par['cpu_delta']:.2f} | - |\n")
                f.write(f"| Zmiana pamięci (MB) | {seq['memory_delta']:.2f} | {par['memory_delta']:.2f} | - |\n")
            else:
                f.write("Brak danych\n")
            f.write("\n")
            
            # 4. Wyniki testu długotrwałego
            f.write("## Wyniki testu długotrwałego\n\n")
            if "long_running" in self.results:
                lr = self.results["long_running"]
                
                f.write("| Metryka | Wartość |\n")
                f.write("|---------|--------|\n")
                f.write(f"| Liczba odświeżeń | {lr['refresh_count']} |\n")
                f.write(f"| Całkowity czas (s) | {lr['actual_duration']:.2f} |\n")
                f.write(f"| Średni czas odświeżenia (s) | {lr['avg_time_per_refresh']:.4f} |\n")
                f.write(f"| Odświeżeń na sekundę | {lr['refreshes_per_second']:.2f} |\n")
                f.write(f"| Średnie użycie CPU (%) | {lr['avg_cpu']:.2f} |\n")
                f.write(f"| Maksymalne użycie CPU (%) | {lr['max_cpu']:.2f} |\n")
                f.write(f"| Wzrost zużycia pamięci (MB) | {lr['memory_growth']:.2f} |\n")
            else:
                f.write("Brak danych\n")
            f.write("\n")
            
            # 5. Wnioski i rekomendacje
            f.write("## Wnioski i rekomendacje\n\n")
            
            if "long_running" in self.results and "single_refresh" in self.results:
                avg_refresh_time = self.results["long_running"]["avg_time_per_refresh"]
                recommended_intervals = {}
                
                for tf in self.timeframes:
                    # Rekomendowany interwał jako wielokrotność czasu odświeżania
                    if tf == "M1":
                        factor = 1  # Najczęstsze odświeżanie dla M1
                    elif tf == "M5":
                        factor = 3
                    elif tf == "M15":
                        factor = 6
                    elif tf == "H1":
                        factor = 12
                    else:  # D1 i wyżej
                        factor = 20
                        
                    recommended_interval = max(int(avg_refresh_time * factor), 5)  # Minimum 5 sekund
                    recommended_intervals[tf] = recommended_interval
                
                f.write("### Rekomendowane interwały odświeżania\n\n")
                f.write("| Timeframe | Rekomendowany interwał (s) |\n")
                f.write("|-----------|----------------------------|\n")
                
                for tf, interval in recommended_intervals.items():
                    f.write(f"| {tf} | {interval} |\n")
                
                f.write("\n### Ogólne wnioski\n\n")
                
                # Automatyczne generowanie wniosków
                if self.results["long_running"]["avg_cpu"] > 80:
                    f.write("- ⚠️ Wysokie obciążenie CPU podczas długotrwałego testu. Zaleca się zwiększenie interwałów odświeżania.\n")
                    
                if self.results["long_running"]["memory_growth"] > 100:
                    f.write("- ⚠️ Znaczący wzrost zużycia pamięci. Warto monitorować zużycie pamięci w czasie rzeczywistym.\n")
                
                if "sequential_refresh" in self.results and "parallel_refresh" in self.results:
                    ratio = self.results["sequential_refresh"]["elapsed_time"] / self.results["parallel_refresh"]["elapsed_time"]
                    if ratio > 1.5:
                        f.write(f"- ✅ Równoległe odświeżanie jest znacząco szybsze ({ratio:.2f}x) niż sekwencyjne. Zaleca się jego stosowanie.\n")
                    else:
                        f.write(f"- ℹ️ Równoległe odświeżanie daje umiarkowany zysk wydajności ({ratio:.2f}x). Zaleca się jego stosowanie dla większej liczby instrumentów.\n")
                
                refresh_rate = self.results["long_running"]["refreshes_per_second"]
                if refresh_rate < 0.2:  # Mniej niż jedno odświeżenie na 5 sekund
                    f.write("- ⚠️ Niska częstotliwość odświeżania. Warto rozważyć optymalizację kodu lub zwiększenie mocy obliczeniowej.\n")
                else:
                    f.write(f"- ✅ Dobra częstotliwość odświeżania ({refresh_rate:.2f} odświeżeń/s), co pozwala na płynne monitorowanie rynku.\n")
                
                f.write("\n")
            else:
                f.write("Niewystarczające dane do sformułowania wniosków\n")

def main():
    """Główna funkcja do uruchomienia testów wydajności."""
    try:
        print("Rozpoczynam testy wydajności mechanizmu regularnego odświeżania danych...")
        
        test = RefreshPerformanceTest()
        
        # Test pojedynczego odświeżenia
        test.test_single_refresh(iterations=3)
        
        # Test sekwencyjnego odświeżania
        test.test_sequential_refresh()
        
        # Test równoległego odświeżania (jeśli na systemie jest więcej niż 1 rdzeń)
        if psutil.cpu_count(logical=False) > 1:
            test.test_parallel_refresh(max_workers=min(3, psutil.cpu_count(logical=False)))
        
        # Test długotrwały (skrócony do 60 sekund na potrzeby tego testu)
        test.test_long_running_refresh(duration_seconds=60, interval_seconds=5)
        
        # Generowanie wykresów
        print("Generowanie wykresów...")
        test.plot_performance_results()
        
        # Generowanie raportu
        print("Generowanie raportu wydajności...")
        test.generate_report()
        
        print("Testy wydajności zakończone!")
        print("Wyniki dostępne w pliku: performance_report.md")
        print("Wykresy dostępne w katalogu: performance_results/")
        
    except Exception as e:
        logger.error(f"Błąd podczas testów wydajności: {str(e)}")
        logger.error(f"Szczegóły: {traceback.format_exc()}")
        print(f"Błąd podczas testów: {str(e)}")

if __name__ == "__main__":
    main() 