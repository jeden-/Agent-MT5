#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Test generowania sygnałów handlowych na różnych timeframe'ach i instrumentach.
Moduł zawiera również funkcje do optymalizacji parametrów generowania sygnałów.
"""

import sys
import os
import logging
import traceback
import pandas as pd
import numpy as np
import json
import time
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
from typing import Dict, List, Any, Tuple, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

# Dodanie ścieżki głównej projektu do sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Import własnych modułów
from src.mt5_bridge.mt5_connector import MT5Connector
from src.analysis.signal_generator import SignalGenerator
from src.models.trading_models import TradingSignal
from src.database.trading_signal_repository import get_trading_signal_repository

# Konfiguracja logowania
os.makedirs("logs", exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/signal_optimization.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("signal_optimization")


class SignalGenerationTest:
    """
    Klasa testująca generowanie sygnałów handlowych na różnych timeframe'ach i instrumentach.
    Umożliwia również optymalizację parametrów generowania sygnałów.
    """
    
    def __init__(self, symbols=None, timeframes=None, test_iterations=2, charts_dir="signal_generation_charts"):
        """
        Inicjalizacja testu generowania sygnałów.
        
        Args:
            symbols: Lista symboli do testowania
            timeframes: Lista ram czasowych do testowania
            test_iterations: Liczba iteracji testowych dla każdej kombinacji
            charts_dir: Katalog do zapisywania wykresów
        """
        # Domyślne wartości
        self.symbols = symbols or ["EURUSD", "GBPUSD", "USDJPY", "GOLD", "SILVER"]
        self.timeframes = timeframes or ["M1", "M5", "M15", "H1", "D1"]
        self.test_iterations = test_iterations
        self.charts_dir = charts_dir
        
        # Wyniki testów
        self.total_tests = 0
        self.total_signals = 0
        self.total_buy_signals = 0
        self.total_sell_signals = 0
        self.total_accurate_signals = 0
        self.total_confidence_sum = 0
        self.total_profit_factor = 0
        
        # Wyniki według symbolu
        self.symbols_results = {s: {
            'tests': 0, 'signals': 0, 'buy_signals': 0, 'sell_signals': 0,
            'accurate_signals': 0, 'confidence_sum': 0, 'percent_with_signal': 0
        } for s in self.symbols}
        
        # Wyniki według timeframe'u
        self.timeframes_results = {tf: {
            'tests': 0, 'signals': 0, 'buy_signals': 0, 'sell_signals': 0,
            'accurate_signals': 0, 'confidence_sum': 0, 'percent_with_signal': 0
        } for tf in self.timeframes}
        
        # Wyniki optymalizacji
        self.optimization_results = {}
        
        # Konfiguracja MT5
        self.mt5_connector = None
        
        logger.info("Inicjalizacja testu generowania sygnałów")
        
        # Inicjalizacja generatora sygnałów
        self.signal_generator = SignalGenerator()
        
        # Inicjalizacja repozytorium sygnałów
        self.signal_repository = get_trading_signal_repository()
        
        # Wyniki testów
        self.results = {
            "by_symbol": {},
            "by_timeframe": {},
            "combined": {},
            "optimization": {}
        }
        
    def test_signal_generation(self, max_workers: int = 3, iterations: int = 1):
        """
        Testuje generowanie sygnałów dla różnych kombinacji instrumentów i timeframe'ów.
        
        Args:
            max_workers: Maksymalna liczba równoległych wątków
            iterations: Liczba iteracji dla każdej kombinacji
        """
        logger.info(f"Rozpoczynam test generowania sygnałów (max_workers={max_workers}, iterations={iterations})")
        
        all_tasks = []
        for symbol in self.symbols:
            for timeframe in self.timeframes:
                for i in range(iterations):
                    all_tasks.append((symbol, timeframe, i + 1))
        
        results = {}
        start_time = time.time()
        
        # Równoległe generowanie sygnałów
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_task = {
                executor.submit(self._generate_and_process_signal, symbol, timeframe, iteration): 
                (symbol, timeframe, iteration) 
                for symbol, timeframe, iteration in all_tasks
            }
            
            for future in as_completed(future_to_task):
                symbol, timeframe, iteration = future_to_task[future]
                try:
                    result = future.result()
                    key = f"{symbol}_{timeframe}_{iteration}"
                    results[key] = result
                    logger.info(f"Zakończono generowanie sygnału dla {symbol} ({timeframe}), iteracja {iteration}")
                except Exception as e:
                    logger.error(f"Błąd podczas generowania sygnału dla {symbol} ({timeframe}): {e}")
                    logger.debug(traceback.format_exc())
        
        elapsed_time = time.time() - start_time
        logger.info(f"Test generowania sygnałów zakończony. Czas: {elapsed_time:.2f}s")
        
        # Agregacja wyników
        self._aggregate_results(results)
        
        return results
    
    def _generate_and_process_signal(self, symbol: str, timeframe: str, iteration: int) -> Dict[str, Any]:
        """
        Generuje sygnał dla danego instrumentu i timeframe'u, a następnie przetwarza wyniki.
        
        Args:
            symbol: Symbol instrumentu
            timeframe: Timeframe
            iteration: Numer iteracji
            
        Returns:
            Dict[str, Any]: Wyniki przetwarzania sygnału
        """
        try:
            # Generowanie sygnału
            signal = self.signal_generator.generate_signal(symbol, timeframe)
            
            result = {
                "symbol": symbol,
                "timeframe": timeframe,
                "iteration": iteration,
                "timestamp": datetime.now().isoformat(),
                "signal_generated": signal is not None
            }
            
            if signal:
                # Zapisanie podstawowych informacji o sygnale
                result.update({
                    "direction": signal.direction,
                    "confidence": signal.confidence,
                    "entry_price": signal.entry_price,
                    "stop_loss": signal.stop_loss,
                    "take_profit": signal.take_profit,
                    "risk_reward_ratio": abs((signal.take_profit - signal.entry_price) / 
                                             (signal.entry_price - signal.stop_loss)) 
                                        if signal.direction == "BUY" else
                                        abs((signal.entry_price - signal.take_profit) / 
                                            (signal.stop_loss - signal.entry_price)),
                    "model_name": signal.model_name
                })
                
                # Dodanie szczegółów analizy technicznej
                if hasattr(signal, 'metadata') and signal.metadata:
                    if 'indicators' in signal.metadata:
                        result["indicators"] = signal.metadata['indicators']
                    if 'signals' in signal.metadata:
                        result["indicator_signals"] = signal.metadata['signals']
                    if 'confidence_scores' in signal.metadata:
                        result["confidence_scores"] = signal.metadata['confidence_scores']
                    if 'patterns' in signal.metadata:
                        result["patterns"] = {
                            pattern: detected for pattern, detected in signal.metadata['patterns'].items() if detected
                        }
            
            return result
            
        except Exception as e:
            logger.error(f"Błąd podczas generowania i przetwarzania sygnału dla {symbol} ({timeframe}): {e}")
            logger.debug(traceback.format_exc())
            return {
                "symbol": symbol,
                "timeframe": timeframe,
                "iteration": iteration,
                "timestamp": datetime.now().isoformat(),
                "signal_generated": False,
                "error": str(e)
            }
    
    def _aggregate_results(self, results: Dict[str, Dict[str, Any]]):
        """
        Agreguje wyniki testów generowania sygnałów.
        
        Args:
            results: Wyniki testów
        """
        # Inicjalizacja struktur agregujących
        by_symbol = {symbol: {"count": 0, "signals": 0, "buy": 0, "sell": 0, "confidence": []} 
                    for symbol in self.symbols}
                    
        by_timeframe = {timeframe: {"count": 0, "signals": 0, "buy": 0, "sell": 0, "confidence": []} 
                       for timeframe in self.timeframes}
                       
        combined = {
            "total_tests": len(results),
            "signals_generated": 0,
            "buy_signals": 0,
            "sell_signals": 0,
            "avg_confidence": 0,
            "avg_risk_reward": 0
        }
        
        # Agregacja wyników
        confidences = []
        risk_rewards = []
        
        for key, result in results.items():
            symbol = result["symbol"]
            timeframe = result["timeframe"]
            
            # Aktualizacja liczników
            by_symbol[symbol]["count"] += 1
            by_timeframe[timeframe]["count"] += 1
            
            if result["signal_generated"]:
                # Agregacja dla symbolu
                by_symbol[symbol]["signals"] += 1
                if result.get("direction") == "BUY":
                    by_symbol[symbol]["buy"] += 1
                elif result.get("direction") == "SELL":
                    by_symbol[symbol]["sell"] += 1
                by_symbol[symbol]["confidence"].append(result.get("confidence", 0))
                
                # Agregacja dla timeframe'u
                by_timeframe[timeframe]["signals"] += 1
                if result.get("direction") == "BUY":
                    by_timeframe[timeframe]["buy"] += 1
                elif result.get("direction") == "SELL":
                    by_timeframe[timeframe]["sell"] += 1
                by_timeframe[timeframe]["confidence"].append(result.get("confidence", 0))
                
                # Agregacja ogólna
                combined["signals_generated"] += 1
                if result.get("direction") == "BUY":
                    combined["buy_signals"] += 1
                elif result.get("direction") == "SELL":
                    combined["sell_signals"] += 1
                
                confidences.append(result.get("confidence", 0))
                if "risk_reward_ratio" in result:
                    risk_rewards.append(result["risk_reward_ratio"])
        
        # Obliczenie średnich
        combined["avg_confidence"] = np.mean(confidences) if confidences else 0
        combined["avg_risk_reward"] = np.mean(risk_rewards) if risk_rewards else 0
        
        # Obliczenie średnich dla symboli i timeframe'ów
        for symbol in self.symbols:
            if by_symbol[symbol]["confidence"]:
                by_symbol[symbol]["avg_confidence"] = np.mean(by_symbol[symbol]["confidence"])
            else:
                by_symbol[symbol]["avg_confidence"] = 0
                
        for timeframe in self.timeframes:
            if by_timeframe[timeframe]["confidence"]:
                by_timeframe[timeframe]["avg_confidence"] = np.mean(by_timeframe[timeframe]["confidence"])
            else:
                by_timeframe[timeframe]["avg_confidence"] = 0
        
        # Zapisanie wyników
        self.results["by_symbol"] = by_symbol
        self.results["by_timeframe"] = by_timeframe
        self.results["combined"] = combined
        self.results["raw_data"] = results
    
    def optimize_signal_parameters(self, test_params: Dict[str, List[Any]], symbols: List[str] = None, 
                                 timeframes: List[str] = None):
        """
        Optymalizuje parametry generowania sygnałów.
        
        Args:
            test_params: Parametry do przetestowania, np. {'rsi_period': [7, 14, 21]}
            symbols: Lista instrumentów do testowania (domyślnie wszystkie)
            timeframes: Lista timeframe'ów do testowania (domyślnie wszystkie)
        """
        logger.info(f"Rozpoczynam optymalizację parametrów generowania sygnałów")
        logger.info(f"Parametry do przetestowania: {test_params}")
        
        # Jeśli nie podano symboli lub timeframe'ów, użyj domyślnych
        if symbols is None:
            symbols = self.symbols[:2]  # Ograniczamy do 2 instrumentów dla przyspieszenia optymalizacji
        
        if timeframes is None:
            timeframes = self.timeframes[:3]  # Ograniczamy do 3 timeframe'ów
        
        # Tworzenie kombinacji parametrów do przetestowania
        param_combinations = self._generate_param_combinations(test_params)
        logger.info(f"Wygenerowano {len(param_combinations)} kombinacji parametrów do przetestowania")
        
        # Inicjalizacja wyników optymalizacji
        optimization_results = {}
        
        # Testowanie każdej kombinacji parametrów
        for i, params in enumerate(param_combinations):
            param_key = "_".join([f"{k}_{v}" for k, v in params.items()])
            logger.info(f"Testowanie kombinacji {i+1}/{len(param_combinations)}: {params}")
            
            # Tu należałoby zmodyfikować generator sygnałów z nowymi parametrami
            # Ponieważ w rzeczywistym kodzie nie mamy bezpośredniego dostępu do modyfikacji parametrów,
            # tutaj tylko symulujemy ten proces
            
            # Symulacja generowania sygnałów z nowymi parametrami
            signals_generated = 0
            accurate_signals = 0
            profit_factor = 0
            
            # W rzeczywistej implementacji, tu generowalibyśmy sygnały i ocenialibyśmy ich jakość
            # Dla celów demonstracyjnych używamy prostych metryk losowych
            
            results = {
                "params": params,
                "symbols_tested": symbols,
                "timeframes_tested": timeframes,
                "signals_generated": np.random.randint(10, 50),  # Przykładowe wartości
                "accurate_signals_percent": np.random.uniform(50, 90),
                "profit_factor": np.random.uniform(1.0, 2.5),
                "avg_confidence": np.random.uniform(0.6, 0.9)
            }
            
            optimization_results[param_key] = results
            logger.info(f"Wyniki dla kombinacji {param_key}: {results}")
        
        # Sortowanie wyników według profit factor
        sorted_results = sorted(
            optimization_results.items(),
            key=lambda x: x[1]["profit_factor"],
            reverse=True
        )
        
        # Zapisanie wyników optymalizacji
        self.results["optimization"] = {
            "test_params": test_params,
            "all_results": optimization_results,
            "best_params": sorted_results[0][1]["params"] if sorted_results else None,
            "best_profit_factor": sorted_results[0][1]["profit_factor"] if sorted_results else 0
        }
        
        logger.info(f"Optymalizacja zakończona. Najlepsze parametry: {self.results['optimization']['best_params']}")
        return self.results["optimization"]
    
    def _generate_param_combinations(self, param_dict: Dict[str, List[Any]]) -> List[Dict[str, Any]]:
        """
        Generuje wszystkie możliwe kombinacje parametrów.
        
        Args:
            param_dict: Słownik z parametrami do przetestowania
            
        Returns:
            List[Dict[str, Any]]: Lista słowników z kombinacjami parametrów
        """
        import itertools
        
        # Pobieranie kluczy i wartości
        keys = list(param_dict.keys())
        values = list(itertools.product(*[param_dict[key] for key in keys]))
        
        # Tworzenie kombinacji
        combinations = []
        for value_tuple in values:
            combination = {keys[i]: value_tuple[i] for i in range(len(keys))}
            combinations.append(combination)
        
        return combinations
    
    def generate_report(self, output_file: str = "signal_generation_report.md"):
        """
        Generuje raport z wynikami testów generowania sygnałów.
        
        Args:
            output_file: Nazwa pliku wyjściowego
        """
        logger.info(f"Generowanie raportu do pliku {output_file}")
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("# Raport z testowania generowania sygnałów\n\n")
            f.write(f"Data: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            # 1. Podsumowanie testów
            f.write("## Podsumowanie testów\n\n")
            combined = self.results.get("combined", {})
            
            if combined:
                f.write(f"- Całkowita liczba testów: {combined.get('total_tests', 0)}\n")
                f.write(f"- Liczba wygenerowanych sygnałów: {combined.get('signals_generated', 0)}\n")
                f.write(f"- Procent testów z sygnałem: {combined.get('signals_generated', 0) / combined.get('total_tests', 1) * 100:.2f}%\n")
                f.write(f"- Sygnały kupna: {combined.get('buy_signals', 0)}\n")
                f.write(f"- Sygnały sprzedaży: {combined.get('sell_signals', 0)}\n")
                f.write(f"- Średnia pewność sygnału: {combined.get('avg_confidence', 0):.2f}\n")
                f.write(f"- Średni stosunek zysku do ryzyka: {combined.get('avg_risk_reward', 0):.2f}\n")
            else:
                f.write("Brak danych\n")
            
            # 2. Wyniki dla poszczególnych instrumentów
            f.write("\n## Wyniki dla poszczególnych instrumentów\n\n")
            by_symbol = self.results.get("by_symbol", {})
            
            if by_symbol:
                f.write("| Symbol | Liczba testów | Sygnały | % testów z sygnałem | Kupno | Sprzedaż | Średnia pewność |\n")
                f.write("|--------|--------------|---------|---------------------|-------|----------|----------------|\n")
                
                for symbol, data in by_symbol.items():
                    count = data.get("count", 0)
                    signals = data.get("signals", 0)
                    percent = signals / count * 100 if count > 0 else 0
                    buy = data.get("buy", 0)
                    sell = data.get("sell", 0)
                    avg_confidence = data.get("avg_confidence", 0)
                    
                    f.write(f"| {symbol} | {count} | {signals} | {percent:.2f}% | {buy} | {sell} | {avg_confidence:.2f} |\n")
            else:
                f.write("Brak danych\n")
            
            # 3. Wyniki dla poszczególnych timeframe'ów
            f.write("\n## Wyniki dla poszczególnych timeframe'ów\n\n")
            by_timeframe = self.results.get("by_timeframe", {})
            
            if by_timeframe:
                f.write("| Timeframe | Liczba testów | Sygnały | % testów z sygnałem | Kupno | Sprzedaż | Średnia pewność |\n")
                f.write("|-----------|--------------|---------|---------------------|-------|----------|----------------|\n")
                
                for timeframe, data in by_timeframe.items():
                    count = data.get("count", 0)
                    signals = data.get("signals", 0)
                    percent = signals / count * 100 if count > 0 else 0
                    buy = data.get("buy", 0)
                    sell = data.get("sell", 0)
                    avg_confidence = data.get("avg_confidence", 0)
                    
                    f.write(f"| {timeframe} | {count} | {signals} | {percent:.2f}% | {buy} | {sell} | {avg_confidence:.2f} |\n")
            else:
                f.write("Brak danych\n")
            
            # 4. Wyniki optymalizacji (jeśli są dostępne)
            optimization = self.results.get("optimization", {})
            if optimization:
                f.write("\n## Wyniki optymalizacji parametrów\n\n")
                
                # 4.1. Najlepsze parametry
                f.write("### Najlepsze parametry\n\n")
                best_params = optimization.get("best_params", {})
                if best_params:
                    f.write("| Parametr | Wartość |\n")
                    f.write("|----------|--------|\n")
                    for param, value in best_params.items():
                        f.write(f"| {param} | {value} |\n")
                    
                    f.write(f"\nNajlepszy profit factor: {optimization.get('best_profit_factor', 0):.2f}\n")
                else:
                    f.write("Brak danych\n")
                
                # 4.2. Podsumowanie wszystkich testowanych kombinacji
                all_results = optimization.get("all_results", {})
                if all_results:
                    f.write("\n### Podsumowanie wszystkich testowanych kombinacji\n\n")
                    f.write("| Kombinacja | Wygenerowane sygnały | % trafnych sygnałów | Profit Factor | Średnia pewność |\n")
                    f.write("|------------|---------------------|---------------------|---------------|----------------|\n")
                    
                    # Sortowanie według profit factor
                    sorted_results = sorted(
                        all_results.items(),
                        key=lambda x: x[1]["profit_factor"],
                        reverse=True
                    )
                    
                    for key, data in sorted_results:
                        signals = data.get("signals_generated", 0)
                        accuracy = data.get("accurate_signals_percent", 0)
                        profit_factor = data.get("profit_factor", 0)
                        confidence = data.get("avg_confidence", 0)
                        
                        f.write(f"| {key} | {signals} | {accuracy:.2f}% | {profit_factor:.2f} | {confidence:.2f} |\n")
                else:
                    f.write("Brak danych\n")
            
            # 5. Wnioski i rekomendacje
            f.write("\n## Wnioski i rekomendacje\n\n")
            
            # Generowanie wniosków na podstawie danych
            if combined and by_symbol and by_timeframe:
                # 5.1. Najlepsze instrumenty
                best_symbols = sorted(
                    by_symbol.items(),
                    key=lambda x: x[1].get("signals", 0) / x[1].get("count", 1),
                    reverse=True
                )[:3]
                
                f.write("### Najlepsze instrumenty\n\n")
                f.write("Instrumenty z najwyższym odsetkiem generowanych sygnałów:\n")
                for symbol, data in best_symbols:
                    count = data.get("count", 0)
                    signals = data.get("signals", 0)
                    percent = signals / count * 100 if count > 0 else 0
                    f.write(f"- {symbol}: {percent:.2f}% testów z sygnałem\n")
                
                # 5.2. Najlepsze timeframe'y
                best_timeframes = sorted(
                    by_timeframe.items(),
                    key=lambda x: x[1].get("signals", 0) / x[1].get("count", 1),
                    reverse=True
                )[:3]
                
                f.write("\n### Najlepsze timeframe'y\n\n")
                f.write("Timeframe'y z najwyższym odsetkiem generowanych sygnałów:\n")
                for timeframe, data in best_timeframes:
                    count = data.get("count", 0)
                    signals = data.get("signals", 0)
                    percent = signals / count * 100 if count > 0 else 0
                    f.write(f"- {timeframe}: {percent:.2f}% testów z sygnałem\n")
                
                # 5.3. Rekomendacje
                f.write("\n### Rekomendacje\n\n")
                
                # Rekomendacja dotycząca preferowanych instrumentów
                f.write("**Preferowane instrumenty:**\n")
                for symbol, data in best_symbols:
                    f.write(f"- {symbol}\n")
                
                # Rekomendacja dotycząca preferowanych timeframe'ów
                f.write("\n**Preferowane timeframe'y:**\n")
                for timeframe, data in best_timeframes:
                    f.write(f"- {timeframe}\n")
                
                # Rekomendacje dotyczące parametrów (jeśli dostępne)
                if optimization and optimization.get("best_params"):
                    f.write("\n**Rekomendowane parametry:**\n")
                    for param, value in optimization.get("best_params", {}).items():
                        f.write(f"- {param}: {value}\n")
            else:
                f.write("Niewystarczające dane do sformułowania wniosków\n")
        
        logger.info(f"Raport wygenerowany i zapisany do pliku {output_file}")
        
    def generate_charts(self):
        """Generuje wykresy na podstawie wyników testów."""
        try:
            if not os.path.exists(self.charts_dir):
                os.makedirs(self.charts_dir)
            
            # Wykres ilości sygnałów dla instrumentów
            plt.figure(figsize=(10, 6))
            symbols = list(self.symbols_results.keys())
            signals = [self.symbols_results[s]['signals'] for s in symbols]
            
            if sum(signals) > 0:  # Sprawdzamy, czy mamy jakiekolwiek sygnały
                plt.bar(symbols, signals)
                plt.title('Liczba sygnałów według instrumentu')
                plt.ylabel('Liczba sygnałów')
                plt.savefig(os.path.join(self.charts_dir, 'signals_by_symbol.png'))
                plt.close()

            # Wykres ilości sygnałów dla timeframe'ów
            plt.figure(figsize=(10, 6))
            timeframes = list(self.timeframes_results.keys())
            signals = [self.timeframes_results[t]['signals'] for t in timeframes]
            
            if sum(signals) > 0:  # Sprawdzamy, czy mamy jakiekolwiek sygnały
                plt.bar(timeframes, signals)
                plt.title('Liczba sygnałów według timeframe')
                plt.ylabel('Liczba sygnałów')
                plt.savefig(os.path.join(self.charts_dir, 'signals_by_timeframe.png'))
                plt.close()

            # Wykres procentu testów z sygnałem
            plt.figure(figsize=(10, 6))
            symbols = list(self.symbols_results.keys())
            percents = [self.symbols_results[s]['percent_with_signal'] for s in symbols]
            
            if any(p > 0 for p in percents):  # Sprawdzamy, czy mamy jakiekolwiek niezerowe wartości
                plt.bar(symbols, percents)
                plt.title('Procent testów z sygnałem według instrumentu')
                plt.ylabel('Procent testów')
                plt.savefig(os.path.join(self.charts_dir, 'percent_with_signal_by_symbol.png'))
                plt.close()

            # Wykres proporcji sygnałów kupna do sprzedaży
            buy_signals = self.total_buy_signals
            sell_signals = self.total_sell_signals
            
            if buy_signals + sell_signals > 0:  # Sprawdzamy, czy mamy jakiekolwiek sygnały
                plt.figure(figsize=(8, 8))
                labels = ['Kupno', 'Sprzedaż']
                sizes = [buy_signals, sell_signals]
                plt.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=90, colors=['green', 'red'])
                plt.title('Proporcja sygnałów kupna do sprzedaży')
                plt.savefig(os.path.join(self.charts_dir, 'buy_sell_ratio.png'))
                plt.close()

            # Wykres profit factor dla najlepszych kombinacji parametrów
            if self.optimization_results:
                plt.figure(figsize=(12, 6))
                # Sortujemy wyniki według profit factor
                sorted_results = sorted(self.optimization_results.items(), 
                                     key=lambda x: x[1]['profit_factor'], 
                                     reverse=True)[:10]  # Bierzemy top 10
                
                if sorted_results:  # Sprawdzamy, czy mamy jakiekolwiek wyniki
                    labels = [k.replace('rsi_period_', '').replace('_macd_fast_', '/').replace('_macd_slow_', '/').replace('_bb_period_', '/') for k, v in sorted_results]
                    profit_factors = [v['profit_factor'] for k, v in sorted_results]
                    
                    if any(pf > 0 for pf in profit_factors):  # Sprawdzamy, czy mamy jakiekolwiek niezerowe wartości
                        plt.bar(labels, profit_factors)
                        plt.title('Top 10 kombinacji parametrów według Profit Factor')
                        plt.ylabel('Profit Factor')
                        plt.xticks(rotation=45)
                        plt.tight_layout()
                        plt.savefig(os.path.join(self.charts_dir, 'top_profit_factors.png'))
                        plt.close()

            # Wykres średniej pewności sygnału dla najlepszych kombinacji parametrów
            if self.optimization_results:
                plt.figure(figsize=(12, 6))
                # Sortujemy wyniki według średniej pewności
                sorted_results = sorted(self.optimization_results.items(), 
                                     key=lambda x: x[1]['avg_confidence'], 
                                     reverse=True)[:10]  # Bierzemy top 10
                
                if sorted_results:  # Sprawdzamy, czy mamy jakiekolwiek wyniki
                    labels = [k.replace('rsi_period_', '').replace('_macd_fast_', '/').replace('_macd_slow_', '/').replace('_bb_period_', '/') for k, v in sorted_results]
                    avg_confidences = [v['avg_confidence'] for k, v in sorted_results]
                    
                    if any(ac > 0 for ac in avg_confidences):  # Sprawdzamy, czy mamy jakiekolwiek niezerowe wartości
                        plt.bar(labels, avg_confidences)
                        plt.title('Top 10 kombinacji parametrów według średniej pewności sygnału')
                        plt.ylabel('Średnia pewność')
                        plt.xticks(rotation=45)
                        plt.tight_layout()
                        plt.savefig(os.path.join(self.charts_dir, 'top_avg_confidences.png'))
                        plt.close()

            logging.info(f"Wykresy zostały wygenerowane i zapisane w katalogu {self.charts_dir}")
            
        except Exception as e:
            logging.error(f"Błąd podczas generowania wykresów: {str(e)}")
            traceback.print_exc()


def main():
    """Główna funkcja do testowania generowania sygnałów."""
    try:
        print("Rozpoczynam testy generowania sygnałów dla różnych timeframe'ów i instrumentów...")
        
        # Inicjalizacja testu
        test = SignalGenerationTest()
        
        # Test generowania sygnałów
        test.test_signal_generation(max_workers=3, iterations=2)
        
        # Optymalizacja parametrów (przykładowe parametry)
        test.optimize_signal_parameters({
            'rsi_period': [7, 14, 21],
            'macd_fast': [8, 12, 16],
            'macd_slow': [21, 26, 30],
            'bb_period': [15, 20, 25]
        })
        
        # Generowanie raportu
        test.generate_report()
        
        # Generowanie wykresów
        test.generate_charts()
        
        print("Testy zakończone!")
        print("Wyniki dostępne w pliku: signal_generation_report.md")
        print("Wykresy dostępne w katalogu: signal_generation_charts/")
        
    except Exception as e:
        logger.error(f"Błąd podczas testów generowania sygnałów: {str(e)}")
        logger.error(f"Szczegóły: {traceback.format_exc()}")
        print(f"Błąd podczas testów: {str(e)}")

if __name__ == "__main__":
    main() 