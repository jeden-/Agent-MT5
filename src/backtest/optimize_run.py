#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Skrypt do uruchamiania optymalizacji parametrów generatora sygnałów.
"""

import os
import sys
import logging
import argparse
from datetime import datetime, timedelta
from pathlib import Path

# Dodanie ścieżki projektu do sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from src.backtest.optimize_generator import SignalGeneratorOptimizer
from src.utils.logger import setup_logging

# Konfiguracja logowania
setup_logging()
logger = logging.getLogger(__name__)

def parse_arguments():
    """
    Parsowanie argumentów linii komend.
    
    Returns:
        Sparsowane argumenty
    """
    parser = argparse.ArgumentParser(description="Optymalizacja parametrów generatora sygnałów")
    
    # Podstawowe parametry
    parser.add_argument("--symbols", nargs="+", default=["EURUSD", "GBPUSD"],
                        help="Symbole do optymalizacji")
    parser.add_argument("--timeframes", nargs="+", default=["H1"],
                        help="Interwały czasowe do optymalizacji")
    parser.add_argument("--days", type=int, default=90,
                        help="Liczba dni danych historycznych do optymalizacji")
    parser.add_argument("--metric", type=str, default="sharpe_ratio",
                        choices=["net_profit", "win_rate", "profit_factor", "sharpe_ratio", "calmar_ratio"],
                        help="Metryka używana do oceny strategii")
    
    # Parametry zaawansowane
    parser.add_argument("--workers", type=int, default=None,
                        help="Liczba procesów roboczych (domyślnie: liczba rdzeni)")
    parser.add_argument("--output", type=str, default="optimization_results",
                        help="Katalog wyjściowy dla wyników optymalizacji")
    
    # Tryby optymalizacji
    optimization_group = parser.add_mutually_exclusive_group()
    optimization_group.add_argument("--all", action="store_true",
                                   help="Optymalizuj wszystkie parametry (domyślne)")
    optimization_group.add_argument("--weights", action="store_true",
                                   help="Optymalizuj tylko wagi wskaźników")
    optimization_group.add_argument("--thresholds", action="store_true",
                                   help="Optymalizuj tylko progi")
    optimization_group.add_argument("--technical", action="store_true",
                                   help="Optymalizuj tylko parametry techniczne")
    optimization_group.add_argument("--single", type=str, 
                                   help="Optymalizuj pojedynczą parę symbol:timeframe (np. EURUSD:H1)")
    
    args = parser.parse_args()
    return args

def run_optimization(args):
    """
    Uruchamia optymalizację zgodnie z podanymi argumentami.
    
    Args:
        args: Argumenty linii komend
    """
    logger.info("Uruchamianie optymalizacji parametrów generatora sygnałów")
    
    # Inicjalizacja optymalizatora
    optimizer = SignalGeneratorOptimizer(
        symbols=args.symbols,
        timeframes=args.timeframes,
        optimization_days=args.days,
        evaluation_metric=args.metric,
        num_workers=args.workers,
        output_dir=args.output
    )
    
    # Ustalenie dat dla optymalizacji
    end_date = datetime.now()
    start_date = end_date - timedelta(days=args.days)
    
    logger.info(f"Okres optymalizacji: {start_date.date()} - {end_date.date()}")
    
    try:
        # Wybór trybu optymalizacji
        if args.weights:
            # Optymalizacja tylko wag
            for symbol in args.symbols:
                for timeframe in args.timeframes:
                    logger.info(f"Rozpoczynam optymalizację wag dla {symbol}:{timeframe}")
                    results = optimizer.optimize_weights(symbol, timeframe, start_date, end_date)
                    logger.info(f"Zakończono optymalizację wag dla {symbol}:{timeframe}")
                    logger.info(f"Najlepsze wagi: {results['weights']}")
                    logger.info(f"Metryka {args.metric}: {results['metrics'].get(args.metric, 0)}")
        
        elif args.thresholds:
            # Optymalizacja tylko progów
            for symbol in args.symbols:
                for timeframe in args.timeframes:
                    logger.info(f"Rozpoczynam optymalizację progów dla {symbol}:{timeframe}")
                    results = optimizer.optimize_thresholds(symbol, timeframe, start_date, end_date)
                    logger.info(f"Zakończono optymalizację progów dla {symbol}:{timeframe}")
                    logger.info(f"Najlepsze progi: {results['thresholds']}")
                    logger.info(f"Metryka {args.metric}: {results['metrics'].get(args.metric, 0)}")
        
        elif args.technical:
            # Optymalizacja tylko parametrów technicznych
            for symbol in args.symbols:
                for timeframe in args.timeframes:
                    logger.info(f"Rozpoczynam optymalizację parametrów technicznych dla {symbol}:{timeframe}")
                    results = optimizer.optimize_technical_params(symbol, timeframe, start_date, end_date)
                    logger.info(f"Zakończono optymalizację parametrów technicznych dla {symbol}:{timeframe}")
                    logger.info(f"Najlepsze parametry: {results['technical_params']}")
                    logger.info(f"Metryka {args.metric}: {results['metrics'].get(args.metric, 0)}")
        
        elif args.single:
            # Optymalizacja pojedynczej pary symbol:timeframe
            try:
                symbol, timeframe = args.single.split(":")
                logger.info(f"Rozpoczynam pełną optymalizację dla {symbol}:{timeframe}")
                results = optimizer.run_all_optimizations(symbol, timeframe)
                logger.info(f"Zakończono pełną optymalizację dla {symbol}:{timeframe}")
                logger.info(f"Najlepsze parametry: {results['params']}")
                logger.info(f"Końcowe metryki: {results['metrics']}")
            except ValueError:
                logger.error(f"Niepoprawny format dla opcji --single: {args.single}")
                logger.error("Poprawny format to symbol:timeframe, np. EURUSD:H1")
                sys.exit(1)
        
        else:
            # Domyślnie - pełna optymalizacja dla wszystkich kombinacji
            logger.info("Rozpoczynam pełną optymalizację dla wszystkich kombinacji")
            results = optimizer.run_all_combinations()
            logger.info("Zakończono pełną optymalizację")
            
    except Exception as e:
        logger.error(f"Wystąpił błąd podczas optymalizacji: {e}")
        import traceback
        logger.error(traceback.format_exc())
        sys.exit(1)
    
    logger.info("Optymalizacja zakończona pomyślnie")

def main():
    """
    Funkcja główna.
    """
    args = parse_arguments()
    run_optimization(args)

if __name__ == "__main__":
    main() 