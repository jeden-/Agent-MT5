#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Skrypt do optymalizacji parametrów głównego generatora sygnałów.

Ten skrypt przeprowadza optymalizację parametrów dla strategii CombinedIndicatorsStrategy,
która odwzorowuje działanie głównego generatora sygnałów. Optymalizowane są wagi wskaźników,
progi decyzyjne oraz parametry techniczne poszczególnych wskaźników.

Użycie:
    python optimize_signal_generator.py --symbol EURUSD --timeframe H1 --method walk-forward

Autor: AgentMT5
Data: 14.03.2025
"""

import os
import sys
import pandas as pd
import numpy as np
import logging
import json
import argparse
from datetime import datetime, timedelta
from pathlib import Path
import random

# Dodajemy ścieżkę głównego katalogu projektu
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, '../..'))
sys.path.insert(0, project_root)

# Importy z modułu backtest
from src.backtest.backtest_engine import BacktestEngine, BacktestConfig
from src.backtest.strategy import CombinedIndicatorsStrategy
from src.backtest.parameter_optimizer import ParameterOptimizer
from src.backtest.walk_forward_tester import WalkForwardTester
from src.backtest.backtest_metrics import calculate_metrics

# Konfiguracja logowania
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(os.path.join(current_dir, 'optimize_signal_generator.log'))
    ]
)
logger = logging.getLogger(__name__)

def parse_arguments():
    """Parsowanie argumentów wiersza poleceń."""
    parser = argparse.ArgumentParser(description='Optymalizacja parametrów generatora sygnałów')
    
    # Parametry rynkowe
    parser.add_argument('--symbol', type=str, default='EURUSD', help='Symbol instrumentu')
    parser.add_argument('--timeframe', type=str, default='M15', help='Timeframe (np. M5, M15, H1, H4, D1)')
    
    # Zakres dat
    default_end_date = datetime.now()
    default_start_date = default_end_date - timedelta(days=180)
    parser.add_argument('--start-date', type=lambda s: datetime.strptime(s, '%Y-%m-%d'),
                       default=default_start_date, help='Data początkowa w formacie YYYY-MM-DD')
    parser.add_argument('--end-date', type=lambda s: datetime.strptime(s, '%Y-%m-%d'),
                       default=default_end_date, help='Data końcowa w formacie YYYY-MM-DD')
    
    # Metoda optymalizacji
    parser.add_argument('--method', choices=['grid', 'random', 'walk-forward'], default='walk-forward',
                       help='Metoda optymalizacji: grid search, random search lub walk-forward testing')
    
    # Metryka optymalizacji
    parser.add_argument('--metric', type=str, default='sharpe_ratio',
                       help='Metryka do optymalizacji (np. net_profit, sharpe_ratio, profit_factor)')
    
    # Katalog wyjściowy
    parser.add_argument('--output', type=str, default=os.path.join(current_dir, 'optimization_results'),
                       help='Katalog do zapisania wyników optymalizacji')
    
    return parser.parse_args()

def create_param_grid():
    """
    Tworzy sietkę parametrów do optymalizacji dla strategii CombinedIndicatorsStrategy.
    
    Uwaga: Funkcja dostarcza mocno ograniczoną siatkę parametrów, aby zapobiec
    błędom pamięci. W rzeczywistym zastosowaniu należy użyć większej liczby
    parametrów i ich wartości, ale trzeba to zrobić stopniowo lub wykorzystać
    inne techniki optymalizacji.
    
    Returns:
        dict: Siatka parametrów do optymalizacji
    """
    # Bardzo ograniczona siatka parametrów, aby zapobiec błędom pamięci
    param_grid = {
        # Wagi dla wskaźników - tylko 2 wartości dla każdego parametru
        'weights': {
            'trend': [0.2, 0.3],
            'macd': [0.2, 0.3],
            'rsi': [0.15, 0.25],
            'bb': [0.15, 0.25],
            'candle': [0.1, 0.2]
        },
        
        # Progi decyzyjne - tylko 2 wartości dla każdego parametru
        'thresholds': {
            'signal_minimum': [0.15, 0.25],
            'signal_ratio': [1.2, 1.4],
            'rsi_overbought': [70, 80],
            'rsi_oversold': [20, 30]
        },
        
        # Parametry techniczne - tylko 2 wartości dla każdego parametru
        'technical_params': {
            'rsi_period': [14, 21],
            'macd_fast': [12, 16],
            'macd_slow': [26, 30],
            'macd_signal': [9, 11],
            'bb_period': [20, 26],
            'bb_std': [2.0, 2.5],
            'trend_period': [100, 200]
        }
    }
    
    # Spłaszczamy słownik parametrów, łącząc kategorie
    flat_params = {}
    for category, params in param_grid.items():
        for param_name, param_values in params.items():
            flat_params[f"{category}_{param_name}"] = param_values
    
    logger.info(f"Wygenerowano siatkę parametrów z {len(flat_params)} parametrami")
    
    # Oszacowanie liczby kombinacji
    num_combinations = 1
    for param_values in flat_params.values():
        num_combinations *= len(param_values)
    logger.info(f"Łączna liczba kombinacji parametrów: {num_combinations}")
    
    return flat_params

def run_grid_search_optimization(args):
    """
    Przeprowadza optymalizację metodą grid search.
    
    Args:
        args: Argumenty wiersza poleceń
        
    Returns:
        list: Wyniki optymalizacji
    """
    logger.info("Rozpoczynam optymalizację metodą grid search")
    
    # Przygotowanie konfiguracji backtestingu
    param_grid = create_param_grid()
    
    # Inicjalizacja optymalizatora
    optimizer = ParameterOptimizer(
        strategy_class=CombinedIndicatorsStrategy,
        parameter_space=param_grid,
        evaluation_metric=args.metric,
        workers=os.cpu_count() or 4  # Używamy wszystkich dostępnych rdzeni
    )
    
    # Uruchomienie grid search
    results = optimizer.grid_search(
        symbol=args.symbol,
        timeframe=args.timeframe,
        start_date=args.start_date,
        end_date=args.end_date,
        initial_balance=10000,
        position_size_pct=0.01,
        commission=0.0002,  # 0.02% komisji
        use_cache=True
    )
    
    # Zapisanie wyników
    output_dir = save_results(results, args, method="grid_search")
    
    # Analiza wyników
    analyze_results(results, output_dir)
    
    return results

def run_random_search_optimization(args):
    """
    Przeprowadza optymalizację metodą random search.
    
    Ponieważ klasa ParameterOptimizer nie posiada natywnej funkcji random_search,
    symulujemy ją poprzez wybranie losowego podzbioru parametrów i użycie grid_search.
    
    Args:
        args: Argumenty wiersza poleceń
        
    Returns:
        list: Wyniki optymalizacji
    """
    logger.info("Rozpoczynam optymalizację metodą random search")
    
    # Przygotowanie konfiguracji backtestingu
    param_grid = create_param_grid()
    
    # Dla random search, ograniczamy przestrzeń parametrów
    # wybierając losowo podzbiór wartości dla każdego parametru
    random_grid = {}
    iterations = 100  # Pożądana liczba iteracji

    # Oszacuj, ile wartości wybrać dla każdego parametru, aby uzyskać około iterations kombinacji
    total_params = len(param_grid)
    # Każdy parametr powinien mieć approx_values wartości, aby uzyskać około iterations kombinacji
    # param_count * approx_values^param_count ≈ iterations
    approx_values = int(np.power(iterations, 1/total_params)) or 1
    
    logger.info(f"Przygotowanie losowej siatki parametrów (około {iterations} kombinacji)")
    
    for param_name, param_values in param_grid.items():
        # Wybierz losowy podzbiór wartości (minimum 2 wartości lub wszystkie jeśli jest ich mniej)
        num_values = min(len(param_values), max(2, approx_values))
        random_grid[param_name] = random.sample(param_values, num_values)
    
    logger.info(f"Wygenerowano losową siatkę parametrów: {random_grid}")
    
    # Inicjalizacja optymalizatora
    optimizer = ParameterOptimizer(
        strategy_class=CombinedIndicatorsStrategy,
        parameter_space=random_grid,
        evaluation_metric=args.metric,
        workers=os.cpu_count() or 4  # Używamy wszystkich dostępnych rdzeni
    )
    
    # Uruchomienie grid search na losowej siatce parametrów
    results = optimizer.grid_search(
        symbol=args.symbol,
        timeframe=args.timeframe,
        start_date=args.start_date,
        end_date=args.end_date,
        initial_balance=10000,
        position_size_pct=0.01,
        commission=0.0002,  # 0.02% komisji
        use_cache=True
    )
    
    # Zapisanie wyników
    output_dir = save_results(results, args, method="random_search")
    
    # Analiza wyników
    analyze_results(results, output_dir)
    
    return results

def run_walk_forward_optimization(args):
    """
    Przeprowadza optymalizację metodą walk-forward testing.
    
    Args:
        args: Argumenty wiersza poleceń
        
    Returns:
        list: Wyniki optymalizacji
    """
    logger.info("Rozpoczynam optymalizację metodą walk-forward testing")
    
    # Przygotowanie konfiguracji walk-forward
    param_grid = create_param_grid()
    
    # Konfiguracja walk-forward
    config = {
        'train_days': 60,  # 60 dni treningu
        'test_days': 30,   # 30 dni testowania
        'step_days': 30,   # Przesuwamy okno o 30 dni
        'symbol': args.symbol,
        'timeframe': args.timeframe,
        'initial_balance': 10000,
        'position_size_pct': 0.01,
        'commission': 0.0002,  # 0.02% komisji
        'evaluation_metric': args.metric
    }
    
    # Inicjalizacja testera walk-forward
    wf_tester = WalkForwardTester(
        strategy_class=CombinedIndicatorsStrategy,
        parameter_space=param_grid,
        train_days=config['train_days'],
        test_days=config['test_days'],
        step_days=config['step_days'],
        evaluation_metric=config['evaluation_metric'],
        workers=os.cpu_count() or 4
    )
    
    # Uruchomienie testu walk-forward
    results = wf_tester.run(
        start_date=args.start_date,
        end_date=args.end_date,
        symbol=config['symbol'],
        timeframe=config['timeframe'],
        initial_balance=config['initial_balance'],
        position_size_pct=config['position_size_pct'],
        commission=config['commission'],
        use_cache=True
    )
    
    # Zapisanie wyników
    output_dir = save_walk_forward_results(results, args)
    
    # Analiza wyników
    total_profit = sum(window['metrics']['net_profit'] for window in results)
    total_trades = sum(window['metrics']['total_trades'] for window in results)
    total_windows = len(results)
    
    logger.info(f"Walk-forward test zakończony")
    logger.info(f"Liczba okien: {total_windows}")
    logger.info(f"Łączny zysk: {total_profit:.2f}")
    logger.info(f"Łączna liczba transakcji: {total_trades}")
    
    return results

def save_results(results, args, method="grid_search"):
    """
    Zapisuje wyniki optymalizacji do plików.
    
    Args:
        results: Wyniki optymalizacji
        args: Argumenty wiersza poleceń
        method: Metoda optymalizacji
        
    Returns:
        str: Ścieżka do katalogu z wynikami
    """
    # Tworzymy katalog wyjściowy, jeśli nie istnieje
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = Path(args.output) / f"{args.symbol}_{args.timeframe}_{method}_{timestamp}"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Zapisujemy najlepsze parametry do pliku JSON
    best_params = results[0]['params']
    best_metrics = results[0]['metrics']
    best_params_file = output_dir / "best_params.json"
    with open(best_params_file, 'w') as f:
        json.dump({
            'params': best_params,
            'metrics': best_metrics,
            'symbol': args.symbol,
            'timeframe': args.timeframe,
            'start_date': args.start_date.isoformat(),
            'end_date': args.end_date.isoformat(),
            'method': method,
            'evaluation_metric': args.metric
        }, f, indent=4)
    
    # Zapisujemy wszystkie wyniki do pliku CSV
    results_df = pd.DataFrame([
        {
            **{f"param_{k}": v for k, v in result['params'].items()},
            **{f"metric_{k}": v for k, v in result['metrics'].items()}
        }
        for result in results
    ])
    results_file = output_dir / "results.csv"
    results_df.to_csv(results_file, index=False)
    
    logger.info(f"Zapisano wyniki optymalizacji do katalogu: {output_dir}")
    
    return output_dir

def save_walk_forward_results(results, args):
    """
    Zapisuje wyniki testu walk-forward do plików.
    
    Args:
        results: Wyniki testu walk-forward
        args: Argumenty wiersza poleceń
        
    Returns:
        str: Ścieżka do katalogu z wynikami
    """
    # Tworzymy katalog wyjściowy, jeśli nie istnieje
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = Path(args.output) / f"{args.symbol}_{args.timeframe}_walk_forward_{timestamp}"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Zapisujemy wyniki każdego okna do osobnego pliku JSON
    windows_dir = output_dir / "windows"
    windows_dir.mkdir(exist_ok=True)
    
    all_windows_data = []
    for i, window in enumerate(results):
        window_data = {
            'window_index': i,
            'train_period': {
                'start': window['train_period'][0].isoformat(),
                'end': window['train_period'][1].isoformat()
            },
            'test_period': {
                'start': window['test_period'][0].isoformat(),
                'end': window['test_period'][1].isoformat()
            },
            'params': window['params'],
            'metrics': window['metrics']
        }
        all_windows_data.append(window_data)
        
        window_file = windows_dir / f"window_{i+1}.json"
        with open(window_file, 'w') as f:
            json.dump(window_data, f, indent=4)
    
    # Zapisujemy podsumowanie wszystkich okien
    summary_file = output_dir / "summary.json"
    with open(summary_file, 'w') as f:
        json.dump({
            'symbol': args.symbol,
            'timeframe': args.timeframe,
            'start_date': args.start_date.isoformat(),
            'end_date': args.end_date.isoformat(),
            'method': 'walk_forward',
            'evaluation_metric': args.metric,
            'windows': all_windows_data
        }, f, indent=4)
    
    # Zapisujemy podsumowanie do pliku CSV
    results_df = pd.DataFrame([
        {
            'window': i+1,
            'train_start': window['train_period'][0].isoformat(),
            'train_end': window['train_period'][1].isoformat(),
            'test_start': window['test_period'][0].isoformat(),
            'test_end': window['test_period'][1].isoformat(),
            **{f"param_{k}": v for k, v in window['params'].items()},
            **{f"metric_{k}": v for k, v in window['metrics'].items()}
        }
        for i, window in enumerate(results)
    ])
    results_file = output_dir / "results.csv"
    results_df.to_csv(results_file, index=False)
    
    logger.info(f"Zapisano wyniki testu walk-forward do katalogu: {output_dir}")
    
    return output_dir

def analyze_results(results, output_dir):
    """
    Analizuje wyniki optymalizacji i generuje rekomendacje.
    
    Args:
        results: Wyniki optymalizacji
        output_dir: Katalog z wynikami
    """
    logger.info("Analiza wyników optymalizacji")
    
    # Najlepsze parametry
    best_params = results[0]['params']
    best_metrics = results[0]['metrics']
    
    logger.info(f"Najlepsze parametry: {best_params}")
    logger.info(f"Najlepsze metryki: {best_metrics}")
    
    # Sprawdzamy, które parametry mają największy wpływ
    # Zamiana wyników na DataFrame
    df = pd.DataFrame([
        {
            **{k: v for k, v in result['params'].items()},
            **{f"metric_{k}": v for k, v in result['metrics'].items()}
        }
        for result in results
    ])
    
    # Analiza wpływu parametrów
    analysis = {}
    global args  # Aby mieć dostęp do args.metric w tej funkcji
    target_metric = f"metric_{args.metric}"
    
    for param in df.columns:
        if param.startswith('metric_'):
            continue
            
        # Sprawdzamy korelację parametru z metryką docelową
        try:
            correlation = df[[param, target_metric]].corr().iloc[0, 1]
            if pd.isna(correlation):
                correlation = 0
            analysis[param] = correlation
        except (ValueError, IndexError) as e:
            logger.warning(f"Nie można obliczyć korelacji dla {param}: {e}")
            analysis[param] = 0
    
    # Sortujemy parametry według wpływu (wartość bezwzględna korelacji)
    top_params = sorted(analysis.items(), key=lambda x: abs(x[1]), reverse=True)
    
    # Zapisujemy analizę do pliku
    analysis_file = Path(output_dir) / "parameter_impact.csv"
    pd.DataFrame(top_params, columns=['Parameter', 'Correlation']).to_csv(analysis_file, index=False)
    
    # Generujemy rekomendacje
    recommendations = []
    
    # Na podstawie top 3 najbardziej wpływowych parametrów (lub mniej, jeśli mamy mniej parametrów)
    top_n = min(3, len(top_params))
    for param, corr in top_params[:top_n]:
        if corr > 0:
            recommendations.append(f"Parameter {param} ma pozytywny wpływ ({corr:.2f}) - zalecane wyższe wartości")
        else:
            recommendations.append(f"Parameter {param} ma negatywny wpływ ({corr:.2f}) - zalecane niższe wartości")
    
    # Zapisujemy rekomendacje do pliku
    recommendations_file = Path(output_dir) / "recommendations.txt"
    with open(recommendations_file, 'w') as f:
        f.write("Rekomendacje na podstawie analizy wyników optymalizacji:\n\n")
        for rec in recommendations:
            f.write(f"- {rec}\n")
        
        f.write("\nNajlepsze znalezione parametry:\n")
        for param, value in best_params.items():
            f.write(f"- {param}: {value}\n")
        
        f.write("\nOsiągnięte metryki:\n")
        for metric, value in best_metrics.items():
            f.write(f"- {metric}: {value}\n")
    
    logger.info("Analiza została zapisana do pliku")

def main():
    """Główna funkcja skryptu."""
    global args
    args = parse_arguments()
    
    logger.info(f"Rozpoczynam optymalizację parametrów dla {args.symbol} na timeframe {args.timeframe}")
    logger.info(f"Okres: {args.start_date.date()} - {args.end_date.date()}")
    logger.info(f"Metoda: {args.method}")
    logger.info(f"Metryka: {args.metric}")
    
    try:
        if args.method == 'grid':
            results = run_grid_search_optimization(args)
        elif args.method == 'random':
            results = run_random_search_optimization(args)
        elif args.method == 'walk-forward':
            results = run_walk_forward_optimization(args)
        else:
            logger.error(f"Nieznana metoda optymalizacji: {args.method}")
            return
        
        logger.info("Optymalizacja zakończona pomyślnie")
    except Exception as e:
        logger.exception(f"Błąd podczas optymalizacji: {e}")

if __name__ == "__main__":
    main() 