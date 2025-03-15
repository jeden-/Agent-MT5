#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Testy dla modułu optymalizacji parametrów.
"""

import unittest
import logging
import sys
import os
from datetime import datetime, timedelta
from pathlib import Path

# Dodanie ścieżki projektu do sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))

from src.backtest.parameter_optimizer import ParameterOptimizer
from src.backtest.strategy import CombinedIndicatorsStrategy, StrategyConfig
from src.backtest.backtest_engine import BacktestConfig
from src.utils.logger import setup_logging

# Konfiguracja logowania
setup_logging()
logger = logging.getLogger(__name__)

class TestParameterOptimizer(unittest.TestCase):
    """
    Testy dla klasy ParameterOptimizer.
    """
    
    def setUp(self):
        """
        Przygotowanie środowiska testowego.
        """
        # Mała przestrzeń parametrów do szybkich testów
        self.parameter_space = {
            'weights.trend': [0.2, 0.3],
            'weights.macd': [0.2, 0.3],
            'weights.rsi': [0.2, 0.3],
            'rsi_period': [7, 14]
        }
        
        # Funkcja tworząca strategię
        def create_strategy(params):
            # Przetworzenie parametrów z notacji płaskiej na zagnieżdżoną
            strategy_params = {}
            weights = {}
            
            for key, value in params.items():
                if '.' in key:
                    group, param = key.split('.', 1)
                    if group == 'weights':
                        weights[param] = value
                else:
                    strategy_params[key] = value
            
            # Dodanie domyślnych wartości wag, jeśli nie zostały podane
            if 'trend' not in weights:
                weights['trend'] = 0.25
            if 'macd' not in weights:
                weights['macd'] = 0.25
            if 'rsi' not in weights:
                weights['rsi'] = 0.2
            if 'bb' not in weights:
                weights['bb'] = 0.15
            if 'candle' not in weights:
                weights['candle'] = 0.15
                
            # Normalizacja wag
            total = sum(weights.values())
            weights = {k: v/total for k, v in weights.items()}
            
            strategy_params['weights'] = weights
            
            # Domyślne progi decyzyjne
            strategy_params['thresholds'] = {
                'signal_minimum': 0.2,
                'signal_ratio': 1.2,
                'rsi_overbought': 70,
                'rsi_oversold': 30
            }
            
            # Konfiguracja strategii
            config = StrategyConfig(
                stop_loss_pips=20,
                take_profit_pips=30,
                position_size_pct=2.0,
                params=strategy_params
            )
            
            return CombinedIndicatorsStrategy(config=config)
        
        self.create_strategy = create_strategy
        
        # Konfiguracja backtestingu
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)  # 30 dni danych do testów
        
        self.backtest_config = BacktestConfig(
            symbol="EURUSD",
            timeframe="H1",
            start_date=start_date,
            end_date=end_date,
            initial_balance=10000,
            position_size_pct=0.02,
            commission=0.0,
            use_cache=True
        )
    
    def test_small_grid_search(self):
        """
        Test przeszukiwania siatki parametrów na małej przestrzeni parametrów.
        """
        # Inicjalizacja optymalizatora
        optimizer = ParameterOptimizer(
            strategy_class=None,  # Nie używamy klasy bezpośrednio
            parameter_space=self.parameter_space,
            evaluation_metric="sharpe_ratio",
            workers=1,  # Jeden wątek dla stabilności testów
            create_strategy=self.create_strategy
        )
        
        # Ustawienie konfiguracji backtestingu
        optimizer.set_backtest_config(self.backtest_config)
        
        # Dodanie ograniczenia (tylko do testów - zawsze prawdziwe)
        def dummy_constraint(params):
            return True
        
        optimizer.set_parameter_constraint(dummy_constraint)
        
        # Uruchomienie optymalizacji
        try:
            results = optimizer.grid_search()
            
            # Sprawdzenie, czy mamy jakieś wyniki
            self.assertIsNotNone(results)
            self.assertGreater(len(results), 0)
            
            # Sprawdzenie, czy wyniki są posortowane od najlepszych do najgorszych
            if len(results) > 1:
                self.assertGreaterEqual(
                    results[0]['metrics'].get('sharpe_ratio', 0),
                    results[-1]['metrics'].get('sharpe_ratio', 0)
                )
            
            # Wyświetlenie najlepszych parametrów
            logger.info(f"Najlepsze parametry: {results[0]['params']}")
            logger.info(f"Najlepszy Sharpe Ratio: {results[0]['metrics'].get('sharpe_ratio', 0)}")
            
        except Exception as e:
            self.fail(f"Grid search powinien zakończyć się powodzeniem, ale wystąpił błąd: {e}")
    
    def test_parameter_constraint(self):
        """
        Test ograniczeń dla parametrów.
        """
        # Przestrzeń parametrów z potencjalnie niewłaściwymi kombinacjami
        param_space = {
            'trend_fast_period': [8, 12, 16],
            'trend_slow_period': [21, 26, 30]
        }
        
        # Inicjalizacja optymalizatora
        optimizer = ParameterOptimizer(
            strategy_class=None,
            parameter_space=param_space,
            evaluation_metric="net_profit",
            workers=1,
            create_strategy=self.create_strategy
        )
        
        # Ustawienie konfiguracji backtestingu
        optimizer.set_backtest_config(self.backtest_config)
        
        # Dodanie ograniczenia - szybki okres musi być mniejszy niż wolny
        def period_constraint(params):
            if 'trend_fast_period' in params and 'trend_slow_period' in params:
                return params['trend_fast_period'] < params['trend_slow_period']
            return True
        
        optimizer.set_parameter_constraint(period_constraint)
        
        # Sprawdzenie, czy wszystkie kombinacje parametrów spełniają ograniczenie
        param_names = list(param_space.keys())
        param_values = list(param_space.values())
        
        import itertools
        combinations = list(itertools.product(*param_values))
        param_dicts = []
        
        for combo in combinations:
            param_dict = {param_names[i]: combo[i] for i in range(len(param_names))}
            
            # Sprawdzenie ograniczeń parametrów
            if period_constraint(param_dict):
                param_dicts.append(param_dict)
        
        # Ręczne sprawdzenie ile kombinacji powinno zostać
        expected_valid_combinations = 0
        for fast in param_space['trend_fast_period']:
            for slow in param_space['trend_slow_period']:
                if fast < slow:
                    expected_valid_combinations += 1
        
        self.assertEqual(len(param_dicts), expected_valid_combinations)
        logger.info(f"Ograniczenie parametrów: {len(param_dicts)} ważnych kombinacji z {len(combinations)} możliwych")

if __name__ == '__main__':
    unittest.main() 