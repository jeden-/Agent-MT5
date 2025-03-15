#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Skrypt do uruchamiania wszystkich testów agenta handlowego.

Ten skrypt uruchamia wszystkie testy agenta handlowego:
1. test_agent_modes.py - testy trybów pracy agenta
2. test_agent_full_cycle.py - test pełnego cyklu pracy agenta
3. test_llm_integration.py - testy integracji z modelami LLM
4. test_agent_longterm.py - testy długoterminowej stabilności agenta
"""

import sys
import os
import asyncio
import logging
import subprocess
import argparse
import time
from datetime import datetime

# Konfiguracja loggera
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("test_run.log")
    ]
)

logger = logging.getLogger("test_runner")

def run_test(test_file, timeout=300):
    """
    Uruchamia pojedynczy test i zwraca wynik.
    
    Args:
        test_file: Ścieżka do pliku testu
        timeout: Limit czasu wykonania testu w sekundach
        
    Returns:
        dict: Wynik testu zawierający status, czas wykonania i komunikaty
    """
    logger.info(f"Uruchamianie testu: {test_file}")
    start_time = time.time()
    
    try:
        # Uruchomienie testu jako podproces
        process = subprocess.Popen(
            [sys.executable, test_file],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Oczekiwanie na zakończenie testu z limitem czasu
        stdout, stderr = process.communicate(timeout=timeout)
        
        # Sprawdzenie kodu wyjścia
        if process.returncode == 0:
            status = "SUCCESS"
        else:
            status = "FAILURE"
        
        # Obliczenie czasu wykonania
        execution_time = time.time() - start_time
        
        logger.info(f"Test {test_file} zakończony ze statusem: {status} (czas: {execution_time:.2f}s)")
        
        return {
            "test_file": test_file,
            "status": status,
            "execution_time": execution_time,
            "stdout": stdout,
            "stderr": stderr,
            "return_code": process.returncode
        }
    
    except subprocess.TimeoutExpired:
        # Przerwanie testu po przekroczeniu limitu czasu
        process.kill()
        logger.error(f"Test {test_file} przerwany po przekroczeniu limitu czasu ({timeout}s)")
        
        return {
            "test_file": test_file,
            "status": "TIMEOUT",
            "execution_time": timeout,
            "stdout": "",
            "stderr": f"Test przerwany po przekroczeniu limitu czasu ({timeout}s)",
            "return_code": -1
        }
    
    except Exception as e:
        # Obsługa innych błędów
        logger.error(f"Błąd podczas uruchamiania testu {test_file}: {e}")
        
        return {
            "test_file": test_file,
            "status": "ERROR",
            "execution_time": time.time() - start_time,
            "stdout": "",
            "stderr": str(e),
            "return_code": -1
        }

def generate_report(results):
    """
    Generuje raport z wyników testów.
    
    Args:
        results: Lista wyników testów
        
    Returns:
        str: Raport w formacie tekstowym
    """
    report = []
    report.append("=" * 80)
    report.append(f"RAPORT Z TESTÓW - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append("=" * 80)
    report.append("")
    
    # Podsumowanie
    total = len(results)
    success = sum(1 for r in results if r["status"] == "SUCCESS")
    failure = sum(1 for r in results if r["status"] == "FAILURE")
    timeout = sum(1 for r in results if r["status"] == "TIMEOUT")
    error = sum(1 for r in results if r["status"] == "ERROR")
    
    report.append(f"Łącznie testów: {total}")
    report.append(f"Sukces: {success}")
    report.append(f"Porażka: {failure}")
    report.append(f"Timeout: {timeout}")
    report.append(f"Błąd: {error}")
    report.append("")
    
    # Szczegóły testów
    report.append("SZCZEGÓŁY TESTÓW:")
    report.append("-" * 80)
    
    for result in results:
        report.append(f"Test: {result['test_file']}")
        report.append(f"Status: {result['status']}")
        report.append(f"Czas wykonania: {result['execution_time']:.2f}s")
        
        if result["status"] != "SUCCESS":
            report.append("Błędy:")
            for line in result["stderr"].split("\n"):
                if line.strip():
                    report.append(f"  {line}")
        
        report.append("-" * 80)
    
    return "\n".join(report)

def main():
    """Główna funkcja skryptu."""
    parser = argparse.ArgumentParser(description="Uruchamianie testów agenta handlowego")
    parser.add_argument("--timeout", type=int, default=300, help="Limit czasu wykonania testu w sekundach")
    parser.add_argument("--tests", nargs="+", help="Lista testów do uruchomienia (domyślnie wszystkie)")
    args = parser.parse_args()
    
    # Lista wszystkich testów
    all_tests = [
        "test_agent_modes.py",
        "test_agent_full_cycle.py",
        "test_llm_integration.py",
        "test_agent_longterm.py"
    ]
    
    # Wybór testów do uruchomienia
    tests_to_run = args.tests if args.tests else all_tests
    
    logger.info(f"Rozpoczynanie uruchamiania testów: {', '.join(tests_to_run)}")
    
    # Uruchomienie testów
    results = []
    for test in tests_to_run:
        result = run_test(test, timeout=args.timeout)
        results.append(result)
    
    # Generowanie raportu
    report = generate_report(results)
    logger.info("Generowanie raportu z testów")
    
    # Zapisanie raportu do pliku
    report_file = f"test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    with open(report_file, "w") as f:
        f.write(report)
    
    logger.info(f"Raport zapisany do pliku: {report_file}")
    
    # Wyświetlenie raportu
    print("\n" + report)
    
    # Zwrócenie kodu wyjścia
    if all(r["status"] == "SUCCESS" for r in results):
        return 0
    else:
        return 1

if __name__ == "__main__":
    sys.exit(main()) 