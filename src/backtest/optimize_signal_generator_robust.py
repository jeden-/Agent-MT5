#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Usprawniony skrypt do optymalizacji parametrów głównego generatora sygnałów.

Ta wersja skryptu zawiera ulepszenia:
- Generowanie syntetycznych danych testowych gdy rzeczywiste dane nie są dostępne
- Obsługa błędu pustych wyników
- Mechanizm wznowienia optymalizacji w przypadku awarii

Użycie:
    python optimize_signal_generator_robust.py --symbol EURUSD --timeframe H1 --method walk-forward

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
import pickle
from datetime import datetime, timedelta
from pathlib import Path
import random
import traceback

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
from src.backtest.historical_data_manager import HistoricalDataManager

# Konfiguracja logowania
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(os.path.join(current_dir, 'optimize_signal_generator_robust.log'))
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
    default_end_date = datetime.now() - timedelta(days=1)  # Dane z wczoraj jako bezpieczna opcja
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
    
    # Dodatkowe parametry
    parser.add_argument('--use-synthetic-data', action='store_true',
                       help='Użyj syntetycznych danych, gdy rzeczywiste dane są niedostępne')
    parser.add_argument('--resume', type=str, default=None,
                       help='Plik z zapisanym stanem do wznowienia optymalizacji')
    parser.add_argument('--max-combinations', type=int, default=None,
                       help='Maksymalna liczba kombinacji parametrów do sprawdzenia')
    parser.add_argument('--verbose', action='store_true',
                       help='Wyświetl szczegółowe informacje diagnostyczne')
    
    return parser.parse_args()

def create_param_grid(reduced=False):
    """
    Tworzy siatkę parametrów do optymalizacji dla strategii CombinedIndicatorsStrategy.
    
    Args:
        reduced (bool): Czy używać zredukowanej siatki parametrów
    
    Returns:
        dict: Siatka parametrów do optymalizacji
    """
    if reduced:
        # Bardzo ograniczona siatka parametrów do szybkich testów
        param_grid = {
            # Wagi dla wskaźników
            'weights_trend': [0.2, 0.3],
            'weights_macd': [0.2, 0.3],
            'weights_rsi': [0.15, 0.25],
            'weights_bb': [0.15, 0.25],
            'weights_candle': [0.1, 0.2],
            
            # Progi decyzyjne
            'thresholds_signal_minimum': [0.15, 0.25],
            'thresholds_signal_ratio': [1.3, 1.4],
            'thresholds_rsi_overbought': [70, 80],
            'thresholds_rsi_oversold': [20, 30],
            
            # Parametry techniczne wskaźników
            'technical_params_rsi_period': [14, 21],
            'technical_params_macd_fast': [12, 16],
            'technical_params_macd_slow': [26, 30],
            'technical_params_macd_signal': [9, 11],
            'technical_params_bb_period': [20, 26],
            'technical_params_bb_std': [2.0, 2.5],
            'technical_params_trend_period': [100, 200]
        }
    else:
        # Standardowa siatka parametrów
        param_grid = {
            # Wagi dla wskaźników
            'weights_trend': [0.1, 0.2, 0.3, 0.4],
            'weights_macd': [0.1, 0.2, 0.3, 0.4],
            'weights_rsi': [0.05, 0.15, 0.25, 0.35],
            'weights_bb': [0.05, 0.15, 0.25, 0.35],
            'weights_candle': [0.05, 0.1, 0.2, 0.3],
            
            # Progi decyzyjne
            'thresholds_signal_minimum': [0.1, 0.15, 0.2, 0.25],
            'thresholds_signal_ratio': [1.2, 1.3, 1.4, 1.5],
            'thresholds_rsi_overbought': [65, 70, 75, 80],
            'thresholds_rsi_oversold': [20, 25, 30, 35],
            
            # Parametry techniczne wskaźników
            'technical_params_rsi_period': [7, 14, 21, 28],
            'technical_params_macd_fast': [8, 12, 16, 20],
            'technical_params_macd_slow': [22, 26, 30, 34],
            'technical_params_macd_signal': [5, 9, 11, 13],
            'technical_params_bb_period': [14, 20, 26, 30],
            'technical_params_bb_std': [1.5, 2.0, 2.5, 3.0],
            'technical_params_trend_period': [50, 100, 150, 200]
        }
        
    return param_grid

def generate_synthetic_data(symbol, timeframe, start_date, end_date):
    """
    Generuje syntetyczne dane historyczne dla testów, gdy rzeczywiste dane są niedostępne.
    
    Args:
        symbol: Symbol instrumentu
        timeframe: Timeframe
        start_date: Data początkowa
        end_date: Data końcowa
        
    Returns:
        pd.DataFrame: Wygenerowane dane syntetyczne
    """
    logger.info(f"Generowanie syntetycznych danych dla {symbol} {timeframe} od {start_date} do {end_date}")
    
    # Określanie interwału czasowego na podstawie timeframe
    if timeframe == 'M1':
        interval = timedelta(minutes=1)
    elif timeframe == 'M5':
        interval = timedelta(minutes=5)
    elif timeframe == 'M15':
        interval = timedelta(minutes=15)
    elif timeframe == 'M30':
        interval = timedelta(minutes=30)
    elif timeframe == 'H1':
        interval = timedelta(hours=1)
    elif timeframe == 'H4':
        interval = timedelta(hours=4)
    elif timeframe == 'D1':
        interval = timedelta(days=1)
    else:
        interval = timedelta(hours=1)
    
    # Generowanie listy timestampów
    current_time = start_date
    timestamps = []
    
    while current_time <= end_date:
        # Pomijamy weekendy (prosta symulacja dni handlowych)
        if current_time.weekday() < 5:  # 0-4 to poniedziałek-piątek
            # Pomijamy godziny nocne (dla uproszczenia)
            if 8 <= current_time.hour <= 22:
                timestamps.append(current_time)
        current_time += interval
    
    # Jeśli nie mamy żadnych timestampów, generujemy przynajmniej kilka
    if not timestamps:
        logger.warning("Brak odpowiednich timestampów w zakresie dat. Generuję przykładowe dane.")
        for i in range(100):
            timestamps.append(start_date + i * interval)
    
    # Generowanie danych cenowych
    num_points = len(timestamps)
    logger.info(f"Generowanie {num_points} punktów danych syntetycznych")
    
    # Parametry generowania cen
    base_price = 1.1000  # Cena bazowa dla EUR/USD
    volatility = 0.002   # Zmienność dzienna
    trend = 0.0001       # Delikatny trend wzrostowy
    
    # Inicjalizacja tablicy cen
    closes = np.zeros(num_points)
    closes[0] = base_price
    
    # Generowanie losowych zmian cen
    np.random.seed(42)  # Dla powtarzalności
    
    for i in range(1, num_points):
        # Losowa zmiana z tendencją
        price_change = np.random.normal(trend, volatility)
        closes[i] = closes[i-1] * (1 + price_change)
    
    # Generowanie danych OHLC
    data = []
    for i in range(num_points):
        # Generowanie High/Low jako odchylenia od Close
        close = closes[i]
        high = close * (1 + np.random.uniform(0, 0.001))
        low = close * (1 - np.random.uniform(0, 0.001))
        open_price = closes[i-1] if i > 0 else close * (1 - np.random.uniform(-0.001, 0.001))
        
        # Wolumen losowo pomiędzy 100 a 1000
        volume = np.random.randint(100, 1000)
        
        data.append({
            'time': timestamps[i],
            'open': open_price,
            'high': high,
            'low': low,
            'close': close,
            'tick_volume': volume,
            'spread': 2,
            'real_volume': volume * 10
        })
    
    # Tworzenie DataFrame
    df = pd.DataFrame(data)
    
    # Upewniamy się, że kolumna 'time' jest dostępna zarówno jako indeks, jak i jako kolumna
    # To rozwiąże problem z KeyError: 'time'
    if 'time' not in df.columns:
        df['time'] = timestamps
    
    # Ustawiamy indeks, ale zachowujemy kolumnę 'time'
    df.set_index('time', inplace=True)
    df['time'] = df.index  # Dodajemy kolumnę 'time' z wartościami indeksu
    
    # Logujemy szczegóły danych
    logger.info(f"Wygenerowano syntetyczne dane: {len(df)} rekordów")
    logger.info(f"Zakres cen: {df['close'].min():.5f} - {df['close'].max():.5f}")
    logger.info(f"Pierwsze 5 dat: {', '.join([str(d) for d in df.index[:5]])}")
    
    return df

# Patching klasy HistoricalDataManager, aby obsługiwała dane syntetyczne
original_get_historical_data = HistoricalDataManager.get_historical_data

def patched_get_historical_data(self, symbol, timeframe, start_date, end_date, use_cache=True, update_cache=True, use_synthetic=False):
    """
    Poprawiona metoda pobierania danych historycznych, która obsługuje dane syntetyczne.
    """
    logger.info(f"Próba pobrania danych dla {symbol} {timeframe} od {start_date} do {end_date}")
    logger.info(f"Parametry: use_cache={use_cache}, update_cache={update_cache}, use_synthetic={use_synthetic}")
    
    data = original_get_historical_data(self, symbol, timeframe, start_date, end_date, use_cache, update_cache)
    
    if data is not None:
        logger.info(f"Pobrano rzeczywiste dane: {len(data)} rekordów")
        return data
    
    if use_synthetic:
        logger.warning(f"Nie udało się pobrać rzeczywistych danych. Generowanie danych syntetycznych.")
        data = generate_synthetic_data(symbol, timeframe, start_date, end_date)
        return data
    
    logger.error(f"Nie udało się pobrać danych i nie zezwolono na dane syntetyczne.")
    return None

# Zastępujemy oryginalną metodę naszą poprawioną wersją
HistoricalDataManager.get_historical_data = patched_get_historical_data

def run_grid_search_optimization(args, resume_state=None):
    """
    Przeprowadza optymalizację metodą grid search.
    
    Args:
        args: Argumenty wiersza poleceń
        resume_state: Stan wznowienia optymalizacji (opcjonalnie)
        
    Returns:
        list: Wyniki optymalizacji
    """
    logger.info("Rozpoczynam optymalizację metodą grid search")
    
    # Przygotowanie konfiguracji backtestingu
    param_grid = create_param_grid(reduced=(args.max_combinations is not None))
    
    # Inicjalizacja optymalizatora
    optimizer = ParameterOptimizer(
        strategy_class=CombinedIndicatorsStrategy,
        parameter_space=param_grid,
        evaluation_metric=args.metric,
        workers=os.cpu_count() or 4  # Używamy wszystkich dostępnych rdzeni
    )
    
    # Ustawiamy stan wznowienia, jeśli istnieje
    if resume_state:
        logger.info(f"Wznawiam optymalizację od {resume_state['progress']} z {resume_state['total']} kombinacji")
        optimizer.resume_from_state(resume_state)
    
    # Ograniczamy liczbę kombinacji, jeśli podano
    if args.max_combinations:
        optimizer.limit_combinations(args.max_combinations)
    
    # Uruchomienie grid search
    try:
        # Sprawdzamy, czy klasa grid_search obsługuje parametr use_synthetic_data
        # Jeśli nie, używamy bezpiecznego podejścia
        import inspect
        grid_search_params = inspect.signature(optimizer.grid_search).parameters
        
        # Budujemy słownik parametrów dla grid_search
        grid_search_kwargs = {
            'symbol': args.symbol,
            'timeframe': args.timeframe,
            'start_date': args.start_date,
            'end_date': args.end_date,
            'initial_balance': 10000,
            'position_size_pct': 0.01,
            'commission': 0.0002,  # 0.02% komisji
            'use_cache': True
        }
        
        # Dodajemy parametr use_synthetic_data tylko jeśli jest obsługiwany
        if 'use_synthetic_data' in grid_search_params:
            grid_search_kwargs['use_synthetic_data'] = args.use_synthetic_data
            logger.info(f"Dodano parametr use_synthetic_data={args.use_synthetic_data} do wywołania grid_search")
        else:
            logger.warning("Metoda grid_search nie obsługuje parametru use_synthetic_data. Używamy alternatywnego podejścia.")
            # Rozszerzamy funkcjonalność poprzez ustawienie zmiennej globalnej
            global USE_SYNTHETIC_DATA
            USE_SYNTHETIC_DATA = args.use_synthetic_data
            
        # Wywołujemy grid_search z odpowiednimi parametrami
        logger.info(f"Uruchamiam grid_search z parametrami: {grid_search_kwargs}")
        results = optimizer.grid_search(**grid_search_kwargs)
        
        # Zapisanie wyników
        if results and len(results) > 0:
            output_dir = save_results(results, args, method="grid_search")
            analyze_results(results, output_dir)
        else:
            logger.warning("Brak ważnych wyników optymalizacji")
            save_empty_results(args, method="grid_search")
            results = []
        
    except Exception as e:
        logger.error(f"Błąd podczas optymalizacji grid search: {str(e)}")
        logger.error(traceback.format_exc())
        results = []
    
    return results

def run_random_search_optimization(args, resume_state=None):
    """
    Przeprowadza optymalizację metodą random search.
    
    Args:
        args: Argumenty wiersza poleceń
        resume_state: Stan wznowienia optymalizacji (opcjonalnie)
        
    Returns:
        list: Wyniki optymalizacji
    """
    logger.info("Rozpoczynam optymalizację metodą random search")
    
    # Przygotowanie konfiguracji backtestingu
    param_grid = create_param_grid(reduced=False)
    
    # Dla random search, ograniczamy przestrzeń parametrów
    # wybierając losowo podzbiór wartości dla każdego parametru
    random_grid = {}
    iterations = args.max_combinations or 100  # Pożądana liczba iteracji

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
    
    logger.info(f"Wygenerowano losową siatkę parametrów")
    
    # Inicjalizacja optymalizatora
    optimizer = ParameterOptimizer(
        strategy_class=CombinedIndicatorsStrategy,
        parameter_space=random_grid,
        evaluation_metric=args.metric,
        workers=os.cpu_count() or 4  # Używamy wszystkich dostępnych rdzeni
    )
    
    # Ustawiamy stan wznowienia, jeśli istnieje
    if resume_state:
        logger.info(f"Wznawiam optymalizację od {resume_state['progress']} z {resume_state['total']} kombinacji")
        optimizer.resume_from_state(resume_state)
    
    # Uruchomienie random search
    try:
        results = optimizer.grid_search(
            symbol=args.symbol,
            timeframe=args.timeframe,
            start_date=args.start_date,
            end_date=args.end_date,
            initial_balance=10000,
            position_size_pct=0.01,
            commission=0.0002,  # 0.02% komisji
            use_cache=True,
            use_synthetic_data=args.use_synthetic_data
        )
        
        # Zapisanie wyników
        if results and len(results) > 0:
            output_dir = save_results(results, args, method="random_search")
            analyze_results(results, output_dir)
        else:
            logger.warning("Brak ważnych wyników optymalizacji")
            save_empty_results(args, method="random_search")
            results = []
        
    except Exception as e:
        logger.error(f"Błąd podczas optymalizacji random search: {str(e)}")
        logger.error(traceback.format_exc())
        results = []
    
    return results

def run_walk_forward_optimization(args, resume_state=None):
    """
    Przeprowadza optymalizację metodą walk-forward.
    
    Args:
        args: Argumenty wiersza poleceń
        resume_state: Stan wznowienia optymalizacji (opcjonalnie)
        
    Returns:
        list: Wyniki optymalizacji
    """
    logger.info("Rozpoczynam optymalizację metodą walk-forward")
    
    # Przygotowanie konfiguracji backtestingu
    param_grid = create_param_grid(reduced=True)  # Używamy zredukowanej siatki dla szybszego działania
    
    # Konfiguracja okresów
    total_days = (args.end_date - args.start_date).days
    train_days = total_days // 4  # 25% danych na trening
    test_days = total_days // 8   # 12.5% danych na test
    step_days = total_days // 16  # 6.25% danych jako krok
    
    # Inicjalizacja testera walk-forward
    wf_tester = WalkForwardTester(
        strategy_class=CombinedIndicatorsStrategy,
        parameter_space=param_grid,
        evaluation_metric=args.metric,
        train_period_days=train_days,
        test_period_days=test_days,
        step_days=step_days,
        workers=os.cpu_count() or 4
    )
    
    # Ustawiamy stan wznowienia, jeśli istnieje
    if resume_state:
        logger.info(f"Wznawiam optymalizację walk-forward od okna {resume_state['current_window']}")
        wf_tester.resume_from_state(resume_state)
    
    # Uruchomienie testu walk-forward
    try:
        results = wf_tester.run(
            symbol=args.symbol,
            timeframe=args.timeframe,
            start_date=args.start_date,
            end_date=args.end_date,
            initial_balance=10000,
            position_size_pct=0.01,
            commission=0.0002,  # 0.02% komisji
            use_cache=True,
            use_synthetic_data=args.use_synthetic_data
        )
        
        # Zapisanie wyników
        if results and len(results) > 0:
            output_dir = save_walk_forward_results(results, args)
            
            # Analiza wyników
            total_profit = sum(window['metrics']['net_profit'] for window in results)
            total_trades = sum(window['metrics']['total_trades'] for window in results)
            total_windows = len(results)
            
            logger.info(f"Walk-forward test zakończony")
            logger.info(f"Liczba okien: {total_windows}")
            logger.info(f"Łączny zysk: {total_profit:.2f}")
            logger.info(f"Łączna liczba transakcji: {total_trades}")
        else:
            logger.warning("Brak ważnych wyników optymalizacji walk-forward")
            save_empty_results(args, method="walk_forward")
            results = []
        
    except Exception as e:
        logger.error(f"Błąd podczas optymalizacji walk-forward: {str(e)}")
        logger.error(traceback.format_exc())
        results = []
    
    return results

def save_empty_results(args, method="grid_search"):
    """
    Zapisuje informację o braku wyników optymalizacji.
    
    Args:
        args: Argumenty wiersza poleceń
        method: Metoda optymalizacji
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = Path(args.output) / f"{args.symbol}_{args.timeframe}_{method}_{timestamp}_empty"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Zapisujemy informację o braku wyników
    info_file = output_dir / "info.json"
    with open(info_file, 'w') as f:
        json.dump({
            'status': 'empty',
            'symbol': args.symbol,
            'timeframe': args.timeframe,
            'start_date': args.start_date.isoformat(),
            'end_date': args.end_date.isoformat(),
            'method': method,
            'evaluation_metric': args.metric,
            'message': 'Brak ważnych wyników optymalizacji',
            'timestamp': datetime.now().isoformat()
        }, f, indent=4)
    
    logger.info(f"Zapisano informację o braku wyników do katalogu: {output_dir}")
    
    return output_dir

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
    
    # Sprawdzamy, czy mamy jakiekolwiek wyniki
    if not results or len(results) == 0:
        logger.warning("Brak wyników do zapisania")
        return save_empty_results(args, method)
    
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
    
    # Sprawdzamy, czy mamy jakiekolwiek wyniki
    if not results or len(results) == 0:
        logger.warning("Brak wyników walk-forward do zapisania")
        return save_empty_results(args, method="walk_forward")
    
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
        
        # Zapisujemy dane okna
        window_file = windows_dir / f"window_{i}.json"
        with open(window_file, 'w') as f:
            json.dump(window_data, f, indent=4)
    
    # Zapisujemy podsumowanie wyników walk-forward
    summary = {
        'symbol': args.symbol,
        'timeframe': args.timeframe,
        'start_date': args.start_date.isoformat(),
        'end_date': args.end_date.isoformat(),
        'method': 'walk_forward',
        'evaluation_metric': args.metric,
        'total_windows': len(results),
        'total_profit': sum(window['metrics']['net_profit'] for window in results),
        'total_trades': sum(window['metrics']['total_trades'] for window in results),
        'average_profit_per_window': sum(window['metrics']['net_profit'] for window in results) / len(results),
        'best_window': max(range(len(results)), key=lambda i: results[i]['metrics']['net_profit']),
        'worst_window': min(range(len(results)), key=lambda i: results[i]['metrics']['net_profit']),
        'timestamp': datetime.now().isoformat()
    }
    
    summary_file = output_dir / "summary.json"
    with open(summary_file, 'w') as f:
        json.dump(summary, f, indent=4)
    
    # Zapisujemy wszystkie okna do jednego pliku CSV
    results_df = pd.DataFrame([
        {
            'window': i,
            'train_start': window['train_period'][0].isoformat(),
            'train_end': window['train_period'][1].isoformat(),
            'test_start': window['test_period'][0].isoformat(),
            'test_end': window['test_period'][1].isoformat(),
            **{f"param_{k}": v for k, v in window['params'].items()},
            **{f"metric_{k}": v for k, v in window['metrics'].items()}
        }
        for i, window in enumerate(results)
    ])
    results_file = output_dir / "walk_forward_results.csv"
    results_df.to_csv(results_file, index=False)
    
    logger.info(f"Zapisano wyniki walk-forward do katalogu: {output_dir}")
    
    return output_dir

def analyze_results(results, output_dir):
    """
    Analizuje wyniki optymalizacji i generuje podsumowanie.
    
    Args:
        results: Wyniki optymalizacji
        output_dir: Katalog do zapisu wyników analizy
    """
    # Sprawdzamy, czy mamy jakiekolwiek wyniki
    if not results or len(results) == 0:
        logger.warning("Brak wyników do analizy")
        return
    
    try:
        # Konwertujemy wyniki do DataFrame dla łatwiejszej analizy
        results_df = pd.DataFrame([
            {
                **{f"param_{k}": v for k, v in result['params'].items()},
                **{f"metric_{k}": v for k, v in result['metrics'].items()}
            }
            for result in results
        ])
        
        # Podstawowe statystyki
        stats = results_df.describe()
        stats_file = Path(output_dir) / "statistics.csv"
        stats.to_csv(stats_file)
        
        # Analiza wpływu poszczególnych parametrów
        param_analysis = {}
        
        # Analizujemy wpływ każdego parametru na główną metrykę
        metric_cols = [col for col in results_df.columns if col.startswith('metric_')]
        param_cols = [col for col in results_df.columns if col.startswith('param_')]
        
        for metric_col in metric_cols:
            param_impact = {}
            for param_col in param_cols:
                # Dla każdej unikalnej wartości parametru, obliczamy średnią wartość metryki
                param_values = results_df[param_col].unique()
                param_impact[param_col] = {
                    str(value): results_df[results_df[param_col] == value][metric_col].mean()
                    for value in param_values
                }
            param_analysis[metric_col] = param_impact
        
        # Zapisanie analizy wpływu parametrów
        param_analysis_file = Path(output_dir) / "parameter_impact.json"
        with open(param_analysis_file, 'w') as f:
            json.dump(param_analysis, f, indent=4)
        
        logger.info(f"Zapisano analizę wyników do katalogu: {output_dir}")
        
    except Exception as e:
        logger.error(f"Błąd podczas analizy wyników: {str(e)}")
        logger.error(traceback.format_exc())

def load_resume_state(resume_file):
    """
    Wczytuje stan wznowienia optymalizacji z pliku.
    
    Args:
        resume_file: Ścieżka do pliku stanu
        
    Returns:
        dict: Wczytany stan lub None w przypadku błędu
    """
    try:
        with open(resume_file, 'rb') as f:
            state = pickle.load(f)
        return state
    except Exception as e:
        logger.error(f"Błąd podczas wczytywania stanu wznowienia: {str(e)}")
        return None

def save_checkpoint(state, args, iteration):
    """
    Zapisuje punkt kontrolny optymalizacji do pliku.
    
    Args:
        state: Stan optymalizacji
        args: Argumenty wiersza poleceń
        iteration: Numer iteracji
        
    Returns:
        str: Ścieżka do zapisanego pliku
    """
    # Tworzymy katalog checkpointów, jeśli nie istnieje
    checkpoint_dir = Path(args.output) / "checkpoints"
    checkpoint_dir.mkdir(parents=True, exist_ok=True)
    
    # Nazwa pliku punktu kontrolnego
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    method = args.method.replace('-', '_')
    checkpoint_file = checkpoint_dir / f"{args.symbol}_{args.timeframe}_{method}_checkpoint_{iteration}_{timestamp}.pkl"
    
    # Zapisujemy stan
    with open(checkpoint_file, 'wb') as f:
        pickle.dump(state, f)
    
    logger.info(f"Zapisano punkt kontrolny do pliku: {checkpoint_file}")
    
    return str(checkpoint_file)

def main():
    """Główna funkcja skryptu."""
    args = parse_arguments()
    
    # Konfiguracja logowania
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.setLevel(logging.DEBUG)
        logging.getLogger('src').setLevel(logging.DEBUG)
        
    # Wyświetl informacje o konfiguracji
    logger.info(f"Rozpoczynam optymalizację dla {args.symbol} {args.timeframe}")
    logger.info(f"Metoda optymalizacji: {args.method}")
    logger.info(f"Metryka: {args.metric}")
    logger.info(f"Zakres dat: {args.start_date} - {args.end_date}")
    logger.info(f"Użycie danych syntetycznych: {args.use_synthetic_data}")
    
    # Zapisanie katalogu wynikowego
    os.makedirs(args.output, exist_ok=True)
    logger.info(f"Katalog wynikowy: {args.output}")
    
    # Wczytanie stanu wznowienia, jeśli istnieje
    resume_state = None
    if args.resume:
        if os.path.exists(args.resume):
            try:
                with open(args.resume, 'rb') as f:
                    resume_state = pickle.load(f)
                logger.info(f"Wczytano stan wznowienia z pliku {args.resume}")
            except Exception as e:
                logger.error(f"Błąd podczas wczytywania stanu wznowienia: {str(e)}")
        else:
            logger.warning(f"Plik stanu wznowienia {args.resume} nie istnieje. Rozpoczynam od początku.")
    
    # Wybór odpowiedniej metody optymalizacji
    try:
        if args.method == 'grid':
            results = run_grid_search_optimization(args, resume_state)
        elif args.method == 'random':
            results = run_random_search_optimization(args, resume_state)
        elif args.method == 'walk-forward':
            results = run_walk_forward_optimization(args, resume_state)
        else:
            logger.error(f"Nieznana metoda optymalizacji: {args.method}")
            return
            
        # Wyświetlenie podsumowania
        if results and len(results) > 0:
            logger.info("Optymalizacja zakończona sukcesem.")
            if args.method == 'walk-forward':
                total_profit = sum(window['metrics']['net_profit'] for window in results)
                logger.info(f"Łączny zysk (walk-forward): {total_profit:.2f}")
            else:
                best_result = max(results, key=lambda x: x['metrics'][args.metric])
                logger.info(f"Najlepszy wynik ({args.metric}): {best_result['metrics'][args.metric]:.4f}")
                logger.info(f"Najlepsze parametry: {best_result['parameters']}")
        else:
            logger.warning("Optymalizacja nie znalazła żadnych ważnych wyników.")
            
    except Exception as e:
        logger.error(f"Błąd podczas optymalizacji: {str(e)}")
        logger.error(traceback.format_exc())

if __name__ == "__main__":
    # Zmienna globalna do śledzenia, czy używamy danych syntetycznych
    USE_SYNTHETIC_DATA = False
    
    try:
        start_time = datetime.now()
        main()
        end_time = datetime.now()
        logger.info(f"Całkowity czas wykonania: {end_time - start_time}")
    except KeyboardInterrupt:
        logger.info("Przerwano przez użytkownika. Zatrzymywanie...")
    except Exception as e:
        logger.error(f"Nieoczekiwany błąd: {str(e)}")
        logger.error(traceback.format_exc()) 