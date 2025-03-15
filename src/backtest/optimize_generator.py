#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Optymalizacja parametrów głównego generatora sygnałów.

Ten moduł implementuje funkcje do optymalizacji parametrów generatora sygnałów
korzystając ze strategii CombinedIndicatorsStrategy. Optymalizacji poddawane są:
- Wagi wskaźników technicznych
- Progi decyzyjne
- Parametry techniczne (okresy wskaźników)
"""

import os
import sys
import logging
import argparse
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from typing import Dict, List, Tuple, Optional, Any
from datetime import datetime, timedelta
from pathlib import Path
import itertools
import multiprocessing
import json

# Dodanie ścieżki projektu do sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from src.backtest.backtest_engine import BacktestEngine, BacktestConfig
from src.backtest.strategy import CombinedIndicatorsStrategy, StrategyConfig
from src.backtest.parameter_optimizer import ParameterOptimizer
from src.mt5_bridge.mt5_connector import MT5Connector
from src.utils.logger import setup_logging

# Konfiguracja logowania
setup_logging()
logger = logging.getLogger(__name__)

class SignalGeneratorOptimizer:
    """
    Klasa do optymalizacji parametrów generatora sygnałów.
    Implementuje metody do optymalizacji poszczególnych grup parametrów.
    """
    
    def __init__(self, mt5_connector=None, 
                 symbols: List[str] = None, 
                 timeframes: List[str] = None,
                 optimization_days: int = 90,
                 evaluation_metric: str = "sharpe_ratio",
                 num_workers: int = None,
                 output_dir: str = "optimization_results"):
        """
        Inicjalizacja optymalizatora.
        
        Args:
            mt5_connector: Opcjonalny łącznik MT5. Jeśli None, zostanie utworzony nowy.
            symbols: Lista symboli do optymalizacji. Jeśli None, używane są domyślne.
            timeframes: Lista timeframe'ów do optymalizacji. Jeśli None, używane są domyślne.
            optimization_days: Liczba dni danych historycznych do optymalizacji.
            evaluation_metric: Metryka używana do oceny strategii: 
                               "net_profit", "profit_factor", "sharpe_ratio", "calmar_ratio"
            num_workers: Liczba procesów roboczych. Jeśli None, używana jest liczba dostępnych rdzeni.
            output_dir: Katalog wyjściowy dla wyników optymalizacji.
        """
        self.mt5_connector = mt5_connector or MT5Connector()
        self.symbols = symbols or ["EURUSD", "GBPUSD", "USDJPY", "USDCHF", "AUDUSD"]
        self.timeframes = timeframes or ["M15", "H1", "H4", "D1"]
        self.optimization_days = optimization_days
        self.evaluation_metric = evaluation_metric
        self.num_workers = num_workers or multiprocessing.cpu_count()
        self.output_dir = Path(output_dir)
        
        # Upewnij się, że katalog wyjściowy istnieje
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Inicjalizacja łącznika MT5, jeśli potrzeba
        if not self.mt5_connector.initialized:
            self.mt5_connector.initialize()
        
        logger.info(f"Inicjalizacja SignalGeneratorOptimizer zakończona.")
        logger.info(f"Symbole: {self.symbols}")
        logger.info(f"Timeframe'y: {self.timeframes}")
        logger.info(f"Optymalizacja na: {self.optimization_days} dni, metryka: {self.evaluation_metric}")
    
    def optimize_weights(self, symbol: str, timeframe: str,
                         start_date: datetime, end_date: datetime,
                         base_config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Optymalizuje wagi dla poszczególnych wskaźników.
        
        Args:
            symbol: Symbol instrumentu
            timeframe: Interwał czasowy
            start_date: Data początkowa danych
            end_date: Data końcowa danych
            base_config: Bazowa konfiguracja parametrów (używana jako punkt startowy)
            
        Returns:
            Dict zawierający optymalne wagi i wyniki
        """
        logger.info(f"Rozpoczynam optymalizację wag dla {symbol}:{timeframe}")
        
        # Przygotowanie przestrzeni parametrów dla wag
        param_grid = {
            'weights.trend': [0.10, 0.15, 0.20, 0.25, 0.30],
            'weights.macd': [0.20, 0.25, 0.30, 0.35, 0.40],
            'weights.rsi': [0.15, 0.20, 0.25, 0.30],
            'weights.bb': [0.10, 0.15, 0.20, 0.25],
            'weights.candle': [0.05, 0.10, 0.15]
        }
        
        # Parametry bazowe (używamy domyślnych, jeśli nie podano innych)
        base_params = base_config or {}
        
        # Inicjalizacja parametrów z base_params
        strategy_params = {
            'weights': {
                'trend': base_params.get('weights', {}).get('trend', 0.25),
                'macd': base_params.get('weights', {}).get('macd', 0.30),
                'rsi': base_params.get('weights', {}).get('rsi', 0.20),
                'bb': base_params.get('weights', {}).get('bb', 0.15),
                'candle': base_params.get('weights', {}).get('candle', 0.10)
            },
            'thresholds': base_params.get('thresholds', {
                'signal_minimum': 0.2,
                'signal_ratio': 1.2,
                'rsi_overbought': 65, 
                'rsi_oversold': 35
            }),
            'rsi_period': base_params.get('rsi_period', 7),
            'trend_fast_period': base_params.get('trend_fast_period', 12),
            'trend_slow_period': base_params.get('trend_slow_period', 26),
            'macd_fast': base_params.get('macd_fast', 12),
            'macd_slow': base_params.get('macd_slow', 26),
            'macd_signal': base_params.get('macd_signal', 9),
            'bb_period': base_params.get('bb_period', 15),
            'bb_std_dev': base_params.get('bb_std_dev', 2.0)
        }
        
        # Konfiguracja optymalizatora parametrów
        optimizer = self._create_optimizer(symbol, timeframe, start_date, end_date, 
                                          param_grid, strategy_params)
        
        # Przeprowadzenie optymalizacji
        results = optimizer.grid_search()
        
        # Zapisanie wyników
        self._save_optimization_results(results, f"weights_{symbol}_{timeframe}")
        
        # Zwrócenie najlepszych wag
        best_result = results[0]
        best_params = best_result['params']
        
        # Konwersja z formatu parametrów na format używany przez strategię
        optimized_weights = {
            'trend': best_params.get('weights.trend', strategy_params['weights']['trend']),
            'macd': best_params.get('weights.macd', strategy_params['weights']['macd']),
            'rsi': best_params.get('weights.rsi', strategy_params['weights']['rsi']),
            'bb': best_params.get('weights.bb', strategy_params['weights']['bb']),
            'candle': best_params.get('weights.candle', strategy_params['weights']['candle'])
        }
        
        # Normalizacja wag, aby sumowały się do 1.0
        sum_weights = sum(optimized_weights.values())
        optimized_weights = {k: v/sum_weights for k, v in optimized_weights.items()}
        
        logger.info(f"Optymalizacja wag zakończona. Najlepsze wagi: {optimized_weights}")
        logger.info(f"Metryka {self.evaluation_metric}: {best_result['metrics'][self.evaluation_metric]}")
        
        return {
            'weights': optimized_weights,
            'metrics': best_result['metrics']
        }
    
    def optimize_thresholds(self, symbol: str, timeframe: str,
                           start_date: datetime, end_date: datetime,
                           base_config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Optymalizuje progi decyzyjne dla generatora sygnałów.
        
        Args:
            symbol: Symbol instrumentu
            timeframe: Interwał czasowy
            start_date: Data początkowa danych
            end_date: Data końcowa danych
            base_config: Bazowa konfiguracja parametrów (używana jako punkt startowy)
            
        Returns:
            Dict zawierający optymalne progi i wyniki
        """
        logger.info(f"Rozpoczynam optymalizację progów dla {symbol}:{timeframe}")
        
        # Przygotowanie przestrzeni parametrów dla progów
        param_grid = {
            'thresholds.signal_minimum': [0.15, 0.2, 0.25, 0.3],
            'thresholds.signal_ratio': [1.0, 1.1, 1.2, 1.3, 1.4],
            'thresholds.rsi_overbought': [60, 65, 70, 75],
            'thresholds.rsi_oversold': [25, 30, 35, 40]
        }
        
        # Parametry bazowe (używamy domyślnych, jeśli nie podano innych)
        base_params = base_config or {}
        
        # Inicjalizacja parametrów z base_params
        strategy_params = {
            'weights': base_params.get('weights', {
                'trend': 0.25,
                'macd': 0.30,
                'rsi': 0.20,
                'bb': 0.15,
                'candle': 0.10
            }),
            'thresholds': {
                'signal_minimum': base_params.get('thresholds', {}).get('signal_minimum', 0.2),
                'signal_ratio': base_params.get('thresholds', {}).get('signal_ratio', 1.2),
                'rsi_overbought': base_params.get('thresholds', {}).get('rsi_overbought', 65),
                'rsi_oversold': base_params.get('thresholds', {}).get('rsi_oversold', 35)
            },
            'rsi_period': base_params.get('rsi_period', 7),
            'trend_fast_period': base_params.get('trend_fast_period', 12),
            'trend_slow_period': base_params.get('trend_slow_period', 26),
            'macd_fast': base_params.get('macd_fast', 12),
            'macd_slow': base_params.get('macd_slow', 26),
            'macd_signal': base_params.get('macd_signal', 9),
            'bb_period': base_params.get('bb_period', 15),
            'bb_std_dev': base_params.get('bb_std_dev', 2.0)
        }
        
        # Konfiguracja optymalizatora parametrów
        optimizer = self._create_optimizer(symbol, timeframe, start_date, end_date, 
                                          param_grid, strategy_params)
        
        # Przeprowadzenie optymalizacji
        results = optimizer.grid_search()
        
        # Zapisanie wyników
        self._save_optimization_results(results, f"thresholds_{symbol}_{timeframe}")
        
        # Zwrócenie najlepszych progów
        best_result = results[0]
        best_params = best_result['params']
        
        # Konwersja z formatu parametrów na format używany przez strategię
        optimized_thresholds = {
            'signal_minimum': best_params.get('thresholds.signal_minimum', 
                                            strategy_params['thresholds']['signal_minimum']),
            'signal_ratio': best_params.get('thresholds.signal_ratio', 
                                          strategy_params['thresholds']['signal_ratio']),
            'rsi_overbought': best_params.get('thresholds.rsi_overbought', 
                                            strategy_params['thresholds']['rsi_overbought']),
            'rsi_oversold': best_params.get('thresholds.rsi_oversold', 
                                          strategy_params['thresholds']['rsi_oversold'])
        }
        
        logger.info(f"Optymalizacja progów zakończona. Najlepsze progi: {optimized_thresholds}")
        logger.info(f"Metryka {self.evaluation_metric}: {best_result['metrics'][self.evaluation_metric]}")
        
        return {
            'thresholds': optimized_thresholds,
            'metrics': best_result['metrics']
        }
    
    def optimize_technical_params(self, symbol: str, timeframe: str,
                                 start_date: datetime, end_date: datetime,
                                 base_config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Optymalizuje parametry techniczne wskaźników.
        
        Args:
            symbol: Symbol instrumentu
            timeframe: Interwał czasowy
            start_date: Data początkowa danych
            end_date: Data końcowa danych
            base_config: Bazowa konfiguracja parametrów (używana jako punkt startowy)
            
        Returns:
            Dict zawierający optymalne parametry techniczne i wyniki
        """
        logger.info(f"Rozpoczynam optymalizację parametrów technicznych dla {symbol}:{timeframe}")
        
        # Przygotowanie przestrzeni parametrów dla parametrów technicznych
        param_grid = {
            'rsi_period': [5, 7, 9, 14, 21],
            'trend_fast_period': [8, 10, 12, 16],
            'trend_slow_period': [21, 26, 30, 34],
            'macd_fast': [8, 10, 12, 16],
            'macd_slow': [21, 26, 30, 34],
            'macd_signal': [7, 9, 11, 13],
            'bb_period': [10, 15, 20, 25],
            'bb_std_dev': [1.5, 2.0, 2.5, 3.0]
        }
        
        # Parametry bazowe (używamy domyślnych, jeśli nie podano innych)
        base_params = base_config or {}
        
        # Inicjalizacja parametrów z base_params
        strategy_params = {
            'weights': base_params.get('weights', {
                'trend': 0.25,
                'macd': 0.30,
                'rsi': 0.20,
                'bb': 0.15,
                'candle': 0.10
            }),
            'thresholds': base_params.get('thresholds', {
                'signal_minimum': 0.2,
                'signal_ratio': 1.2,
                'rsi_overbought': 65,
                'rsi_oversold': 35
            }),
            'rsi_period': base_params.get('rsi_period', 7),
            'trend_fast_period': base_params.get('trend_fast_period', 12),
            'trend_slow_period': base_params.get('trend_slow_period', 26),
            'macd_fast': base_params.get('macd_fast', 12),
            'macd_slow': base_params.get('macd_slow', 26),
            'macd_signal': base_params.get('macd_signal', 9),
            'bb_period': base_params.get('bb_period', 15),
            'bb_std_dev': base_params.get('bb_std_dev', 2.0)
        }
        
        # Konfiguracja optymalizatora parametrów
        optimizer = self._create_optimizer(symbol, timeframe, start_date, end_date, 
                                          param_grid, strategy_params)
        
        # Dodanie ograniczenia, aby trend_fast_period < trend_slow_period i macd_fast < macd_slow
        def param_constraint(params):
            valid = True
            if 'trend_fast_period' in params and 'trend_slow_period' in params:
                valid = valid and (params['trend_fast_period'] < params['trend_slow_period'])
            if 'macd_fast' in params and 'macd_slow' in params:
                valid = valid and (params['macd_fast'] < params['macd_slow'])
            return valid
        
        optimizer.set_parameter_constraint(param_constraint)
        
        # Przeprowadzenie optymalizacji
        results = optimizer.grid_search()
        
        # Zapisanie wyników
        self._save_optimization_results(results, f"technical_params_{symbol}_{timeframe}")
        
        # Zwrócenie najlepszych parametrów technicznych
        best_result = results[0]
        best_params = best_result['params']
        
        # Konwersja z formatu parametrów na format używany przez strategię
        optimized_tech_params = {
            'rsi_period': best_params.get('rsi_period', strategy_params['rsi_period']),
            'trend_fast_period': best_params.get('trend_fast_period', strategy_params['trend_fast_period']),
            'trend_slow_period': best_params.get('trend_slow_period', strategy_params['trend_slow_period']),
            'macd_fast': best_params.get('macd_fast', strategy_params['macd_fast']),
            'macd_slow': best_params.get('macd_slow', strategy_params['macd_slow']),
            'macd_signal': best_params.get('macd_signal', strategy_params['macd_signal']),
            'bb_period': best_params.get('bb_period', strategy_params['bb_period']),
            'bb_std_dev': best_params.get('bb_std_dev', strategy_params['bb_std_dev'])
        }
        
        logger.info(f"Optymalizacja parametrów technicznych zakończona. Najlepsze parametry: {optimized_tech_params}")
        logger.info(f"Metryka {self.evaluation_metric}: {best_result['metrics'][self.evaluation_metric]}")
        
        return {
            'technical_params': optimized_tech_params,
            'metrics': best_result['metrics']
        }
    
    def run_all_optimizations(self, symbol: str, timeframe: str) -> Dict[str, Any]:
        """
        Przeprowadza pełną optymalizację (wagi, progi, parametry techniczne) dla podanego symbolu i timeframe'u.
        
        Args:
            symbol: Symbol instrumentu
            timeframe: Interwał czasowy
            
        Returns:
            Dict zawierający wszystkie optymalne parametry i wyniki
        """
        # Ustalenie dat dla optymalizacji
        end_date = datetime.now()
        start_date = end_date - timedelta(days=self.optimization_days)
        
        logger.info(f"Rozpoczynam pełną optymalizację dla {symbol}:{timeframe}")
        logger.info(f"Okres: {start_date.date()} - {end_date.date()}")
        
        # 1. Optymalizacja wag wskaźników
        weights_result = self.optimize_weights(symbol, timeframe, start_date, end_date)
        
        # 2. Optymalizacja progów decyzyjnych z użyciem zoptymalizowanych wag
        base_config = {'weights': weights_result['weights']}
        thresholds_result = self.optimize_thresholds(symbol, timeframe, start_date, end_date, base_config)
        
        # 3. Optymalizacja parametrów technicznych z użyciem zoptymalizowanych wag i progów
        base_config = {
            'weights': weights_result['weights'],
            'thresholds': thresholds_result['thresholds']
        }
        tech_params_result = self.optimize_technical_params(symbol, timeframe, start_date, end_date, base_config)
        
        # Połączenie wszystkich wyników
        final_params = {
            'weights': weights_result['weights'],
            'thresholds': thresholds_result['thresholds'],
            'rsi_period': tech_params_result['technical_params']['rsi_period'],
            'trend_fast_period': tech_params_result['technical_params']['trend_fast_period'],
            'trend_slow_period': tech_params_result['technical_params']['trend_slow_period'],
            'macd_fast': tech_params_result['technical_params']['macd_fast'],
            'macd_slow': tech_params_result['technical_params']['macd_slow'],
            'macd_signal': tech_params_result['technical_params']['macd_signal'],
            'bb_period': tech_params_result['technical_params']['bb_period'],
            'bb_std_dev': tech_params_result['technical_params']['bb_std_dev']
        }
        
        # Zapisanie końcowych parametrów
        self._save_final_params(symbol, timeframe, final_params)
        
        # Przeprowadzenie testu z końcowymi parametrami
        final_metrics = self._test_final_params(symbol, timeframe, start_date, end_date, final_params)
        
        logger.info(f"Pełna optymalizacja zakończona dla {symbol}:{timeframe}")
        logger.info(f"Końcowe parametry: {final_params}")
        logger.info(f"Końcowe metryki: {final_metrics}")
        
        return {
            'params': final_params,
            'metrics': final_metrics
        }
    
    def run_all_combinations(self) -> Dict[str, Any]:
        """
        Przeprowadza optymalizację dla wszystkich kombinacji symbolów i timeframe'ów.
        
        Returns:
            Dict z wynikami dla wszystkich kombinacji
        """
        logger.info(f"Rozpoczynam optymalizację dla wszystkich kombinacji: {len(self.symbols)} symboli x {len(self.timeframes)} timeframe'ów")
        
        all_results = {}
        
        for symbol in self.symbols:
            all_results[symbol] = {}
            for timeframe in self.timeframes:
                logger.info(f"Przetwarzanie kombinacji: {symbol} - {timeframe}")
                try:
                    result = self.run_all_optimizations(symbol, timeframe)
                    all_results[symbol][timeframe] = result
                except Exception as e:
                    logger.error(f"Błąd podczas optymalizacji {symbol}:{timeframe}: {e}")
                    import traceback
                    logger.error(traceback.format_exc())
        
        # Zapisanie zbiorczego raportu
        self._save_summary_report(all_results)
        
        logger.info("Optymalizacja dla wszystkich kombinacji zakończona")
        return all_results
    
    def _create_optimizer(self, symbol: str, timeframe: str, 
                        start_date: datetime, end_date: datetime,
                        param_grid: Dict[str, List], 
                        base_params: Dict[str, Any]) -> ParameterOptimizer:
        """
        Tworzy instancję optymalizatora parametrów.
        
        Args:
            symbol: Symbol instrumentu
            timeframe: Interwał czasowy
            start_date: Data początkowa danych
            end_date: Data końcowa danych
            param_grid: Siatka parametrów do optymalizacji
            base_params: Bazowa konfiguracja parametrów
            
        Returns:
            Instancja ParameterOptimizer
        """
        # Tworzenie funkcji do tworzenia strategii z danymi parametrami
        def create_strategy(params):
            # Słownik do odwzorowania nazw parametrów na strukturę słownika dla strategii
            strategy_params = base_params.copy()
            
            # Uzupełnianie parametrów z siatki
            for param_name, param_value in params.items():
                if '.' in param_name:
                    # Parametr zagnieżdżony (np. weights.trend)
                    group, key = param_name.split('.', 1)
                    if group not in strategy_params:
                        strategy_params[group] = {}
                    strategy_params[group][key] = param_value
                else:
                    # Parametr główny
                    strategy_params[param_name] = param_value
            
            # Tworzenie konfiguracji strategii
            strategy_config = StrategyConfig(
                stop_loss_pips=20,   # domyślna wartość
                take_profit_pips=30, # domyślna wartość
                position_size_pct=2.0,    # domyślna wartość
                params=strategy_params
            )
            
            # Tworzenie strategii
            return CombinedIndicatorsStrategy(config=strategy_config)
        
        # Tworzenie konfiguracji backtestingu
        backtest_config = BacktestConfig(
            symbol=symbol,
            timeframe=timeframe,
            start_date=start_date,
            end_date=end_date,
            initial_balance=10000,
            position_size_pct=0.02,  # 2% kapitału na transakcję
            commission=0.0,
            use_cache=True
        )
        
        # Tworzenie optymalizatora
        optimizer = ParameterOptimizer(
            strategy_class=None,  # Nie używamy klasy, tylko funkcji
            parameter_space=param_grid,
            evaluation_metric=self.evaluation_metric,
            workers=self.num_workers,
            create_strategy=create_strategy
        )
        
        # Konfiguracja backtestingu
        optimizer.set_backtest_config(backtest_config)
        
        return optimizer
    
    def _save_optimization_results(self, results: List[Dict], prefix: str) -> None:
        """
        Zapisuje wyniki optymalizacji do pliku.
        
        Args:
            results: Lista wyników optymalizacji
            prefix: Prefiks nazwy pliku
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = self.output_dir / f"{prefix}_{timestamp}.json"
        
        # Zapisujemy tylko 10 najlepszych wyników
        top_results = results[:10]
        
        # Konwertowanie datetime na string przed zapisem do JSON
        serializable_results = []
        for result in top_results:
            serializable_result = result.copy()
            if 'metrics' in serializable_result:
                metrics = serializable_result['metrics'].copy()
                if 'dates' in metrics:
                    if isinstance(metrics['dates']['start'], datetime):
                        metrics['dates']['start'] = metrics['dates']['start'].isoformat()
                    if isinstance(metrics['dates']['end'], datetime):
                        metrics['dates']['end'] = metrics['dates']['end'].isoformat()
                serializable_result['metrics'] = metrics
            serializable_results.append(serializable_result)
        
        with open(filename, 'w') as f:
            json.dump(serializable_results, f, indent=2)
        
        logger.info(f"Wyniki optymalizacji zapisane w: {filename}")
    
    def _save_final_params(self, symbol: str, timeframe: str, params: Dict[str, Any]) -> None:
        """
        Zapisuje końcowe parametry do pliku.
        
        Args:
            symbol: Symbol instrumentu
            timeframe: Interwał czasowy
            params: Optymalne parametry
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = self.output_dir / f"final_params_{symbol}_{timeframe}_{timestamp}.json"
        
        with open(filename, 'w') as f:
            json.dump(params, f, indent=2)
        
        logger.info(f"Końcowe parametry zapisane w: {filename}")
    
    def _test_final_params(self, symbol: str, timeframe: str, 
                         start_date: datetime, end_date: datetime, 
                         params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Testuje końcowe parametry na danych historycznych.
        
        Args:
            symbol: Symbol instrumentu
            timeframe: Interwał czasowy
            start_date: Data początkowa danych
            end_date: Data końcowa danych
            params: Parametry do testowania
            
        Returns:
            Dict z metrykami wyników
        """
        # Konfiguracja backtestingu
        config = BacktestConfig(
            symbol=symbol,
            timeframe=timeframe,
            start_date=start_date,
            end_date=end_date,
            initial_balance=10000,
            position_size_pct=0.02,
            commission=0.0,
            use_cache=True
        )
        
        # Konfiguracja strategii
        strategy_config = StrategyConfig(
            stop_loss_pips=20,
            take_profit_pips=30,
            position_size_pct=2.0,
            params=params
        )
        
        # Inicjalizacja strategii
        strategy = CombinedIndicatorsStrategy(config=strategy_config)
        
        # Inicjalizacja silnika backtestingu
        backtest_engine = BacktestEngine(
            config=config,
            strategy=strategy
        )
        
        # Uruchomienie backtestingu
        result = backtest_engine.run()
        
        return result.metrics
    
    def _save_summary_report(self, all_results: Dict[str, Dict[str, Dict]]) -> None:
        """
        Zapisuje zbiorczy raport z optymalizacji.
        
        Args:
            all_results: Wyniki dla wszystkich kombinacji
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = self.output_dir / f"optimization_summary_{timestamp}.md"
        
        with open(filename, 'w') as f:
            f.write("# Raport z optymalizacji parametrów generatora sygnałów\n\n")
            f.write(f"Data: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write(f"Metryka optymalizacji: {self.evaluation_metric}\n")
            f.write(f"Okres optymalizacji: {self.optimization_days} dni\n\n")
            
            # Tabela z najlepszymi wynikami
            f.write("## Podsumowanie najlepszych wyników\n\n")
            f.write("| Symbol | Timeframe | Net Profit | Win Rate | Profit Factor | Sharpe Ratio | Max Drawdown |\n")
            f.write("|--------|-----------|------------|----------|---------------|--------------|-------------|\n")
            
            for symbol in all_results:
                for timeframe in all_results[symbol]:
                    metrics = all_results[symbol][timeframe]['metrics']
                    f.write(f"| {symbol} | {timeframe} | {metrics.get('net_profit', 0):.2f} | "
                            f"{metrics.get('win_rate', 0)*100:.2f}% | {metrics.get('profit_factor', 0):.2f} | "
                            f"{metrics.get('sharpe_ratio', 0):.2f} | {metrics.get('max_drawdown', 0)*100:.2f}% |\n")
            
            f.write("\n## Szczegółowe wyniki\n\n")
            
            for symbol in all_results:
                f.write(f"### {symbol}\n\n")
                
                for timeframe in all_results[symbol]:
                    f.write(f"#### {timeframe}\n\n")
                    
                    # Parametry
                    params = all_results[symbol][timeframe]['params']
                    f.write("**Optymalne parametry:**\n\n")
                    f.write("```json\n")
                    f.write(json.dumps(params, indent=2))
                    f.write("\n```\n\n")
                    
                    # Metryki
                    metrics = all_results[symbol][timeframe]['metrics']
                    f.write("**Metryki:**\n\n")
                    f.write("```json\n")
                    # Filtrujemy metryki, które są trudne do serializacji
                    filtered_metrics = {k: v for k, v in metrics.items() 
                                      if not isinstance(v, (datetime, pd.DataFrame, np.ndarray))}
                    f.write(json.dumps(filtered_metrics, indent=2))
                    f.write("\n```\n\n")
            
            f.write("\n## Wnioski i rekomendacje\n\n")
            f.write("Na podstawie przeprowadzonej optymalizacji można sformułować następujące rekomendacje:\n\n")
            
            # Tu można by automatycznie generować rekomendacje, ale to zadanie wymaga
            # bardziej zaawansowanej analizy wyników, więc zostawiamy to jako miejsce na ręczne wypełnienie
            f.write("1. [Miejsce na ręczne wypełnienie rekomendacji]\n")
            f.write("2. [Miejsce na ręczne wypełnienie rekomendacji]\n")
            f.write("3. [Miejsce na ręczne wypełnienie rekomendacji]\n")
        
        logger.info(f"Raport zbiorczy zapisany w: {filename}")

def main():
    """
    Główna funkcja uruchamiająca optymalizację.
    """
    parser = argparse.ArgumentParser(description="Optymalizacja parametrów generatora sygnałów")
    parser.add_argument("--symbols", nargs="+", default=["EURUSD", "GBPUSD"],
                        help="Symbole do optymalizacji")
    parser.add_argument("--timeframes", nargs="+", default=["H1"],
                        help="Interwały czasowe do optymalizacji")
    parser.add_argument("--days", type=int, default=90,
                        help="Liczba dni danych historycznych do optymalizacji")
    parser.add_argument("--metric", type=str, default="sharpe_ratio",
                        choices=["net_profit", "win_rate", "profit_factor", "sharpe_ratio", "calmar_ratio"],
                        help="Metryka używana do oceny strategii")
    parser.add_argument("--workers", type=int, default=None,
                        help="Liczba procesów roboczych")
    parser.add_argument("--output", type=str, default="optimization_results",
                        help="Katalog wyjściowy dla wyników optymalizacji")
    
    args = parser.parse_args()
    
    # Inicjalizacja optymalizatora
    optimizer = SignalGeneratorOptimizer(
        symbols=args.symbols,
        timeframes=args.timeframes,
        optimization_days=args.days,
        evaluation_metric=args.metric,
        num_workers=args.workers,
        output_dir=args.output
    )
    
    # Uruchomienie optymalizacji
    optimizer.run_all_combinations()

if __name__ == "__main__":
    main() 