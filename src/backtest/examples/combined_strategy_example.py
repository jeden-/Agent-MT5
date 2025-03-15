#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Przykład użycia CombinedIndicatorsStrategy w backtestingu.
Ta strategia odwzorowuje działanie głównego generatora sygnałów systemu.
"""

import os
import sys
import logging
import argparse
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
from pathlib import Path

# Dodanie ścieżki projektu do sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from backtest.backtest_engine import BacktestEngine, BacktestConfig
from backtest.strategy import CombinedIndicatorsStrategy, StrategyConfig
from mt5.mt5_connector import MT5Connector
from utils.logger import setup_logging

# Konfiguracja logowania
setup_logging()
logger = logging.getLogger(__name__)

def run_combined_strategy_backtest(symbol="EURUSD", timeframe="M15", days=30, optimize=False):
    """
    Uruchamia backtest strategii CombinedIndicatorsStrategy dla podanego instrumentu i timeframe'u.
    
    Args:
        symbol: Symbol instrumentu (default: "EURUSD")
        timeframe: Interwał czasowy (default: "M15")
        days: Liczba dni danych historycznych (default: 30)
        optimize: Czy przeprowadzić optymalizację parametrów (default: False)
    """
    # Inicjalizacja łącznika MT5
    mt5_connector = MT5Connector()
    mt5_connector.initialize()
    
    # Ustawienie dat dla backtestingu
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    
    logger.info(f"Rozpoczynam backtest dla {symbol} na timeframe {timeframe}, okres: {start_date.date()} - {end_date.date()}")
    
    if optimize:
        # Jeśli wybrano optymalizację, uruchom proces optymalizacji parametrów
        optimize_combined_strategy(mt5_connector, symbol, timeframe, start_date, end_date)
    else:
        # Standardowy backtest z domyślnymi parametrami
        run_default_backtest(mt5_connector, symbol, timeframe, start_date, end_date)
    
    mt5_connector.shutdown()

def run_default_backtest(mt5_connector, symbol, timeframe, start_date, end_date):
    """
    Uruchamia standardowy backtest z domyślnymi parametrami.
    
    Args:
        mt5_connector: Instancja łącznika MT5
        symbol: Symbol instrumentu
        timeframe: Interwał czasowy
        start_date: Data początkowa backtestingu
        end_date: Data końcowa backtestingu
    """
    # Konfiguracja backtestingu
    config = BacktestConfig(
        initial_balance=10000.0,
        use_cache=True,
        commission=0.0,
        slippage=0.0,
        spread_points=0,
        date_from=start_date,
        date_to=end_date
    )
    
    # Konfiguracja strategii
    strategy_config = StrategyConfig(
        stop_loss_pips=20,   # Stop Loss w pipach
        take_profit_pips=30, # Take Profit w pipach
        position_size_pct=2.0,    # Procent kapitału na transakcję
        params={
            # Domyślne wagi wskaźników
            'weights': {
                'trend': 0.25,  # Waga trendu
                'macd': 0.30,   # Waga MACD
                'rsi': 0.20,    # Waga RSI
                'bb': 0.15,     # Waga Bollinger Bands
                'candle': 0.10  # Waga formacji świecowych
            },
            # Progi decyzyjne
            'thresholds': {
                'signal_minimum': 0.2,  # Minimalny próg pewności do wygenerowania sygnału
                'signal_ratio': 1.2,    # Wymagany stosunek pewności między BUY i SELL
                'rsi_overbought': 65,   # Próg wyprzedania dla RSI
                'rsi_oversold': 35      # Próg wykupienia dla RSI
            },
            # Parametry wskaźników
            'rsi_period': 7,           # Okres RSI
            'trend_fast_period': 12,   # Szybki EMA dla trendu
            'trend_slow_period': 26,   # Wolny EMA dla trendu
            'macd_fast': 12,           # Szybki EMA dla MACD
            'macd_slow': 26,           # Wolny EMA dla MACD
            'macd_signal': 9,          # Sygnał dla MACD
            'bb_period': 15,           # Okres Bollinger Bands
            'bb_std_dev': 2.0          # Odchylenie standardowe dla Bollinger Bands
        }
    )
    
    # Inicjalizacja strategii
    strategy = CombinedIndicatorsStrategy(config=strategy_config)
    
    # Inicjalizacja silnika backtestingu
    backtest_engine = BacktestEngine(
        mt5_connector=mt5_connector,
        symbol=symbol,
        timeframe=timeframe,
        config=config,
        strategy=strategy
    )
    
    # Uruchomienie backtestingu
    result = backtest_engine.run()
    
    # Wyświetlenie wyników
    logger.info(f"Wyniki backtestingu dla {symbol}:{timeframe} ze strategią {strategy.name}:")
    logger.info(f"Liczba transakcji: {result.total_trades}")
    logger.info(f"Zysk netto: {result.net_profit:.2f}")
    logger.info(f"Odsetek wygranych: {result.win_rate:.2f}%")
    logger.info(f"Współczynnik zysku: {result.profit_factor:.2f}")
    logger.info(f"Maksymalny drawdown: {result.max_drawdown:.2f}%")
    logger.info(f"Współczynnik Sharpe'a: {result.sharpe_ratio:.2f}")
    
    # Generowanie wykresu equity
    plt.figure(figsize=(12, 6))
    plt.plot(result.equity_curve)
    plt.title(f"Krzywa kapitału - {symbol}:{timeframe} - {strategy.name}")
    plt.xlabel("Transakcje")
    plt.ylabel("Kapitał")
    plt.grid(True)
    
    # Utworzenie katalogu na wyniki, jeśli nie istnieje
    results_dir = Path("results")
    results_dir.mkdir(parents=True, exist_ok=True)
    
    # Zapisanie wykresu
    plt.savefig(results_dir / f"{symbol}_{timeframe}_{strategy.name}_equity.png")
    plt.close()
    
    # Zapisanie raportu HTML
    report_path = backtest_engine.generate_html_report(
        output_path=str(results_dir / f"{symbol}_{timeframe}_{strategy.name}_report.html")
    )
    logger.info(f"Raport HTML zapisany w: {report_path}")

def optimize_combined_strategy(mt5_connector, symbol, timeframe, start_date, end_date):
    """
    Przeprowadza optymalizację parametrów dla CombinedIndicatorsStrategy.
    
    Args:
        mt5_connector: Instancja łącznika MT5
        symbol: Symbol instrumentu
        timeframe: Interwał czasowy
        start_date: Data początkowa backtestingu
        end_date: Data końcowa backtestingu
    """
    logger.info(f"Rozpoczynam optymalizację parametrów dla {symbol} na timeframe {timeframe}")
    
    # Konfiguracja backtestingu
    config = BacktestConfig(
        initial_balance=10000.0,
        use_cache=True,
        commission=0.0,
        slippage=0.0,
        spread_points=0,
        date_from=start_date,
        date_to=end_date
    )
    
    # Parametry do optymalizacji
    rsi_periods = [5, 7, 9, 14]
    trend_fast_periods = [8, 12, 16]
    trend_slow_periods = [21, 26, 30]
    signal_minimums = [0.15, 0.2, 0.25]
    rsi_overbought_values = [60, 65, 70]
    rsi_oversold_values = [30, 35, 40]
    
    results = []
    
    # Pętla optymalizacyjna
    for rsi_period in rsi_periods:
        for trend_fast in trend_fast_periods:
            for trend_slow in trend_slow_periods:
                if trend_fast >= trend_slow:
                    continue  # Pomijamy nieprawidłowe kombinacje
                
                for signal_min in signal_minimums:
                    for rsi_ob in rsi_overbought_values:
                        for rsi_os in rsi_oversold_values:
                            if rsi_os >= rsi_ob:
                                continue  # Pomijamy nieprawidłowe kombinacje
                            
                            # Konfiguracja strategii z bieżącymi parametrami
                            strategy_config = StrategyConfig(
                                stop_loss_pips=20,
                                take_profit_pips=30,
                                position_size_pct=2.0,
                                params={
                                    'weights': {
                                        'trend': 0.25,
                                        'macd': 0.30,
                                        'rsi': 0.20,
                                        'bb': 0.15,
                                        'candle': 0.10
                                    },
                                    'thresholds': {
                                        'signal_minimum': signal_min,
                                        'signal_ratio': 1.2,
                                        'rsi_overbought': rsi_ob,
                                        'rsi_oversold': rsi_os
                                    },
                                    'rsi_period': rsi_period,
                                    'trend_fast_period': trend_fast,
                                    'trend_slow_period': trend_slow,
                                    'macd_fast': 12,
                                    'macd_slow': 26,
                                    'macd_signal': 9,
                                    'bb_period': 15,
                                    'bb_std_dev': 2.0
                                }
                            )
                            
                            # Inicjalizacja strategii
                            strategy = CombinedIndicatorsStrategy(config=strategy_config)
                            
                            # Parametry do wyświetlenia w wynikach
                            param_string = (f"RSI:{rsi_period} Fast:{trend_fast} Slow:{trend_slow} "
                                           f"Min:{signal_min} RSI_OB:{rsi_ob} RSI_OS:{rsi_os}")
                            
                            logger.info(f"Testowanie parametrów: {param_string}")
                            
                            # Inicjalizacja silnika backtestingu
                            backtest_engine = BacktestEngine(
                                mt5_connector=mt5_connector,
                                symbol=symbol,
                                timeframe=timeframe,
                                config=config,
                                strategy=strategy
                            )
                            
                            # Uruchomienie backtestingu
                            try:
                                result = backtest_engine.run()
                                
                                # Zapisanie wyników
                                results.append({
                                    'parameters': param_string,
                                    'net_profit': result.net_profit,
                                    'win_rate': result.win_rate,
                                    'profit_factor': result.profit_factor,
                                    'max_drawdown': result.max_drawdown,
                                    'sharpe_ratio': result.sharpe_ratio,
                                    'trades': result.total_trades,
                                    'rsi_period': rsi_period,
                                    'trend_fast': trend_fast,
                                    'trend_slow': trend_slow,
                                    'signal_min': signal_min,
                                    'rsi_overbought': rsi_ob,
                                    'rsi_oversold': rsi_os
                                })
                            except Exception as e:
                                logger.error(f"Błąd podczas testowania parametrów {param_string}: {e}")
    
    # Utworzenie ramki danych z wynikami
    if results:
        results_df = pd.DataFrame(results)
        
        # Sortowanie wyników według zysku netto
        results_df = results_df.sort_values('net_profit', ascending=False)
        
        # Zapisanie wyników do CSV
        results_dir = Path("results")
        results_dir.mkdir(parents=True, exist_ok=True)
        csv_path = results_dir / f"{symbol}_{timeframe}_optimization_results.csv"
        results_df.to_csv(csv_path, index=False)
        
        # Wyświetlenie najlepszych 5 zestawów parametrów
        logger.info("Najlepsze 5 zestawów parametrów:")
        for i, row in results_df.head(5).iterrows():
            logger.info(f"Rank {i+1}: {row['parameters']}")
            logger.info(f"  Zysk netto: {row['net_profit']:.2f}, Win Rate: {row['win_rate']:.2f}%, " 
                       f"Profit Factor: {row['profit_factor']:.2f}, Max DD: {row['max_drawdown']:.2f}%")
        
        # Uruchomienie backtestingu dla najlepszego zestawu parametrów
        best_params = results_df.iloc[0]
        logger.info(f"Uruchamiam backtest dla najlepszego zestawu parametrów: {best_params['parameters']}")
        
        # Utworzenie konfiguracji dla najlepszego zestawu
        best_strategy_config = StrategyConfig(
            stop_loss_pips=20,
            take_profit_pips=30,
            position_size_pct=2.0,
            params={
                'weights': {
                    'trend': 0.25,
                    'macd': 0.30,
                    'rsi': 0.20,
                    'bb': 0.15,
                    'candle': 0.10
                },
                'thresholds': {
                    'signal_minimum': best_params['signal_min'],
                    'signal_ratio': 1.2,
                    'rsi_overbought': best_params['rsi_overbought'],
                    'rsi_oversold': best_params['rsi_oversold']
                },
                'rsi_period': best_params['rsi_period'],
                'trend_fast_period': best_params['trend_fast'],
                'trend_slow_period': best_params['trend_slow'],
                'macd_fast': 12,
                'macd_slow': 26,
                'macd_signal': 9,
                'bb_period': 15,
                'bb_std_dev': 2.0
            }
        )
        
        # Inicjalizacja strategii z najlepszymi parametrami
        best_strategy = CombinedIndicatorsStrategy(config=best_strategy_config)
        
        # Inicjalizacja silnika backtestingu
        backtest_engine = BacktestEngine(
            mt5_connector=mt5_connector,
            symbol=symbol,
            timeframe=timeframe,
            config=config,
            strategy=best_strategy
        )
        
        # Uruchomienie backtestingu
        result = backtest_engine.run()
        
        # Generowanie wykresu equity
        plt.figure(figsize=(12, 6))
        plt.plot(result.equity_curve)
        plt.title(f"Krzywa kapitału - {symbol}:{timeframe} - Najlepsze parametry")
        plt.xlabel("Transakcje")
        plt.ylabel("Kapitał")
        plt.grid(True)
        
        # Zapisanie wykresu
        plt.savefig(results_dir / f"{symbol}_{timeframe}_best_params_equity.png")
        plt.close()
        
        # Zapisanie raportu HTML
        report_path = backtest_engine.generate_html_report(
            output_path=str(results_dir / f"{symbol}_{timeframe}_best_params_report.html")
        )
        logger.info(f"Raport HTML zapisany w: {report_path}")
    else:
        logger.warning("Nie znaleziono żadnych wyników optymalizacji.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Backtest strategii CombinedIndicatorsStrategy")
    parser.add_argument('--symbol', type=str, default="EURUSD", help="Symbol instrumentu")
    parser.add_argument('--timeframe', type=str, default="M15", help="Interwał czasowy")
    parser.add_argument('--days', type=int, default=30, help="Liczba dni danych historycznych")
    parser.add_argument('--optimize', action='store_true', help="Przeprowadź optymalizację parametrów")
    
    args = parser.parse_args()
    
    run_combined_strategy_backtest(
        symbol=args.symbol,
        timeframe=args.timeframe,
        days=args.days,
        optimize=args.optimize
    ) 