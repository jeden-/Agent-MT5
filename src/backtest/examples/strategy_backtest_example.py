#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Przykład wykorzystania nowego silnika backtestingu z interfejsem strategii.
"""

import sys
import os
import logging
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
from pathlib import Path

# Dodanie ścieżki do katalogu głównego projektu
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../')))

from src.backtest.backtest_engine import BacktestEngine, BacktestConfig
from src.backtest.strategy import (
    TradingStrategy, StrategyConfig, 
    SimpleMovingAverageStrategy, RSIStrategy, 
    BollingerBandsStrategy, MACDStrategy
)
from src.mt5_bridge.mt5_connector import get_mt5_connector
from src.config.config_manager import ConfigManager

# Konfiguracja logowania
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def run_strategy_backtest(
    symbol: str = "EURUSD",
    timeframe: str = "H1",
    days: int = 30,
    strategy_type: str = "SMA",
    strategy_params: dict = None
) -> None:
    """
    Uruchamia backtest dla wybranej strategii.
    
    Args:
        symbol: Symbol instrumentu.
        timeframe: Interwał czasowy.
        days: Liczba dni wstecz do backtestingu.
        strategy_type: Typ strategii (SMA, RSI, BB, MACD).
        strategy_params: Parametry strategii.
    """
    # Inicjalizacja konektora MT5
    mt5_connector = get_mt5_connector()
    
    # Ustawienie dat
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    
    # Konfiguracja backtestingu
    config = BacktestConfig(
        symbol=symbol,
        timeframe=timeframe,
        start_date=start_date,
        end_date=end_date,
        initial_balance=10000.0,
        position_size_pct=1.0,
        commission=0.0,
        slippage=0.0,
        use_spread=True,
        min_volume=0.01,
        max_volume=10.0,
        strategy_name=strategy_type,
        use_cache=True,
        update_cache=True,
        strategy_params=strategy_params or {}
    )
    
    # Wybór strategii
    strategy_config = StrategyConfig(
        stop_loss_pips=50,
        take_profit_pips=100,
        position_size_pct=1.0,
        params=strategy_params or {}
    )
    
    if strategy_type == "SMA":
        strategy = SimpleMovingAverageStrategy(
            config=strategy_config,
            fast_period=strategy_params.get("fast_period", 10) if strategy_params else 10,
            slow_period=strategy_params.get("slow_period", 30) if strategy_params else 30
        )
    elif strategy_type == "RSI":
        strategy = RSIStrategy(
            config=strategy_config,
            period=strategy_params.get("period", 14) if strategy_params else 14,
            oversold=strategy_params.get("oversold", 30) if strategy_params else 30,
            overbought=strategy_params.get("overbought", 70) if strategy_params else 70
        )
    elif strategy_type == "BB":
        strategy = BollingerBandsStrategy(
            config=strategy_config,
            period=strategy_params.get("period", 20) if strategy_params else 20,
            std_dev=strategy_params.get("std_dev", 2.0) if strategy_params else 2.0
        )
    elif strategy_type == "MACD":
        strategy = MACDStrategy(
            config=strategy_config,
            fast_period=strategy_params.get("fast_period", 12) if strategy_params else 12,
            slow_period=strategy_params.get("slow_period", 26) if strategy_params else 26,
            signal_period=strategy_params.get("signal_period", 9) if strategy_params else 9
        )
    else:
        logger.error(f"Nieznany typ strategii: {strategy_type}")
        return
    
    # Inicjalizacja silnika backtestingu
    engine = BacktestEngine(config=config, strategy=strategy)
    
    # Uruchomienie backtestingu
    logger.info(f"Uruchamianie backtestingu dla {symbol} na timeframe {timeframe} z strategią {strategy_type}")
    result = engine.run()
    
    # Zapisanie wyników
    result_file = result.save()
    logger.info(f"Wyniki zapisane do: {result_file}")
    
    # Wyświetlenie podstawowych metryk
    print("\n=== WYNIKI BACKTESTINGU ===")
    print(f"Symbol: {symbol}, Timeframe: {timeframe}, Strategia: {strategy_type}")
    print(f"Okres: {start_date.strftime('%Y-%m-%d')} - {end_date.strftime('%Y-%m-%d')}")
    print(f"Liczba transakcji: {len(result.trades)}")
    print(f"Zysk/strata: {result.balance - config.initial_balance:.2f}")
    
    if result.metrics:
        print("\n=== METRYKI ===")
        print(f"Całkowity zysk/strata: {result.metrics.get('net_profit', 0):.2f}")
        print(f"Win rate: {result.metrics.get('win_rate', 0):.2f}%")
        print(f"Średni zysk: {result.metrics.get('avg_profit', 0):.2f}")
        print(f"Średnia strata: {result.metrics.get('avg_loss', 0):.2f}")
        print(f"Profit factor: {result.metrics.get('profit_factor', 0):.2f}")
        print(f"Maksymalny drawdown: {result.metrics.get('max_drawdown', 0):.2f}%")
        print(f"Sharpe ratio: {result.metrics.get('sharpe_ratio', 0):.2f}")
    
    # Wykreślenie krzywej equity
    plt.figure(figsize=(12, 6))
    plt.plot(result.timestamps, result.equity_curve)
    plt.title(f"Krzywa equity dla {symbol} {timeframe} - {strategy_type}")
    plt.xlabel("Data")
    plt.ylabel("Equity")
    plt.grid(True)
    
    # Zapisanie wykresu
    output_dir = Path(config.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    chart_file = output_dir / f"{symbol}_{timeframe}_{strategy_type}_{config.test_id}_equity.png"
    plt.savefig(chart_file)
    logger.info(f"Wykres zapisany do: {chart_file}")
    
    # Wyświetlenie wykresu
    plt.show()


def run_strategy_comparison(
    symbol: str = "EURUSD",
    timeframe: str = "H1",
    days: int = 30
) -> None:
    """
    Porównuje różne strategie na tym samym instrumencie i timeframe.
    
    Args:
        symbol: Symbol instrumentu.
        timeframe: Interwał czasowy.
        days: Liczba dni wstecz do backtestingu.
    """
    # Definicje strategii do porównania
    strategies = [
        {"type": "SMA", "params": {"fast_period": 10, "slow_period": 30}},
        {"type": "RSI", "params": {"period": 14, "oversold": 30, "overbought": 70}},
        {"type": "BB", "params": {"period": 20, "std_dev": 2.0}},
        {"type": "MACD", "params": {"fast_period": 12, "slow_period": 26, "signal_period": 9}}
    ]
    
    # Inicjalizacja konektora MT5
    mt5_connector = get_mt5_connector()
    
    # Ustawienie dat
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    
    # Przygotowanie do wykresu porównawczego
    plt.figure(figsize=(12, 6))
    
    # Uruchomienie backtestingu dla każdej strategii
    results = []
    
    for strategy_def in strategies:
        strategy_type = strategy_def["type"]
        strategy_params = strategy_def["params"]
        
        # Konfiguracja backtestingu
        config = BacktestConfig(
            symbol=symbol,
            timeframe=timeframe,
            start_date=start_date,
            end_date=end_date,
            initial_balance=10000.0,
            position_size_pct=1.0,
            strategy_name=strategy_type,
            use_cache=True,
            update_cache=True,
            strategy_params=strategy_params
        )
        
        # Wybór strategii
        strategy_config = StrategyConfig(
            stop_loss_pips=50,
            take_profit_pips=100,
            position_size_pct=1.0,
            params=strategy_params
        )
        
        if strategy_type == "SMA":
            strategy = SimpleMovingAverageStrategy(
                config=strategy_config,
                fast_period=strategy_params.get("fast_period", 10),
                slow_period=strategy_params.get("slow_period", 30)
            )
        elif strategy_type == "RSI":
            strategy = RSIStrategy(
                config=strategy_config,
                period=strategy_params.get("period", 14),
                oversold=strategy_params.get("oversold", 30),
                overbought=strategy_params.get("overbought", 70)
            )
        elif strategy_type == "BB":
            strategy = BollingerBandsStrategy(
                config=strategy_config,
                period=strategy_params.get("period", 20),
                std_dev=strategy_params.get("std_dev", 2.0)
            )
        elif strategy_type == "MACD":
            strategy = MACDStrategy(
                config=strategy_config,
                fast_period=strategy_params.get("fast_period", 12),
                slow_period=strategy_params.get("slow_period", 26),
                signal_period=strategy_params.get("signal_period", 9)
            )
        else:
            logger.error(f"Nieznany typ strategii: {strategy_type}")
            continue
        
        # Inicjalizacja silnika backtestingu
        engine = BacktestEngine(config=config, strategy=strategy)
        
        # Uruchomienie backtestingu
        logger.info(f"Uruchamianie backtestingu dla {symbol} na timeframe {timeframe} z strategią {strategy_type}")
        result = engine.run()
        
        # Zapisanie wyników
        result_file = result.save()
        logger.info(f"Wyniki zapisane do: {result_file}")
        
        # Dodanie do listy wyników
        results.append({
            "type": strategy_type,
            "result": result
        })
        
        # Dodanie krzywej equity do wykresu
        plt.plot(result.timestamps, result.equity_curve, label=f"{strategy_type}")
    
    # Finalizacja wykresu
    plt.title(f"Porównanie strategii dla {symbol} {timeframe}")
    plt.xlabel("Data")
    plt.ylabel("Equity")
    plt.legend()
    plt.grid(True)
    
    # Zapisanie wykresu
    output_dir = Path("backtest_results")
    output_dir.mkdir(parents=True, exist_ok=True)
    chart_file = output_dir / f"{symbol}_{timeframe}_strategy_comparison_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
    plt.savefig(chart_file)
    logger.info(f"Wykres porównawczy zapisany do: {chart_file}")
    
    # Wyświetlenie wykresu
    plt.show()
    
    # Wyświetlenie tabeli porównawczej
    print("\n=== PORÓWNANIE STRATEGII ===")
    print(f"Symbol: {symbol}, Timeframe: {timeframe}")
    print(f"Okres: {start_date.strftime('%Y-%m-%d')} - {end_date.strftime('%Y-%m-%d')}")
    print("\n{:<10} {:<15} {:<10} {:<10} {:<15} {:<15} {:<15}".format(
        "Strategia", "Zysk/Strata", "Win Rate", "Transakcje", "Profit Factor", "Max Drawdown", "Sharpe Ratio"
    ))
    print("-" * 90)
    
    for result_item in results:
        strategy_type = result_item["type"]
        result = result_item["result"]
        metrics = result.metrics
        
        print("{:<10} {:<15.2f} {:<10.2f} {:<10} {:<15.2f} {:<15.2f} {:<15.2f}".format(
            strategy_type,
            metrics.get("net_profit", 0),
            metrics.get("win_rate", 0),
            len(result.trades),
            metrics.get("profit_factor", 0),
            metrics.get("max_drawdown", 0),
            metrics.get("sharpe_ratio", 0)
        ))


def run_parameter_optimization(
    symbol: str = "EURUSD",
    timeframe: str = "H1",
    days: int = 30,
    strategy_type: str = "SMA"
) -> None:
    """
    Przeprowadza prostą optymalizację parametrów dla wybranej strategii.
    
    Args:
        symbol: Symbol instrumentu.
        timeframe: Interwał czasowy.
        days: Liczba dni wstecz do backtestingu.
        strategy_type: Typ strategii (SMA, RSI, BB, MACD).
    """
    # Inicjalizacja konektora MT5
    mt5_connector = get_mt5_connector()
    
    # Ustawienie dat
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    
    # Definicje parametrów do optymalizacji
    if strategy_type == "SMA":
        param_grid = {
            "fast_period": [5, 10, 15, 20],
            "slow_period": [20, 30, 40, 50]
        }
    elif strategy_type == "RSI":
        param_grid = {
            "period": [7, 14, 21],
            "oversold": [20, 30],
            "overbought": [70, 80]
        }
    elif strategy_type == "BB":
        param_grid = {
            "period": [10, 20, 30],
            "std_dev": [1.5, 2.0, 2.5]
        }
    elif strategy_type == "MACD":
        param_grid = {
            "fast_period": [8, 12, 16],
            "slow_period": [21, 26, 34],
            "signal_period": [5, 9, 13]
        }
    else:
        logger.error(f"Nieznany typ strategii: {strategy_type}")
        return
    
    # Generowanie wszystkich kombinacji parametrów
    import itertools
    param_keys = list(param_grid.keys())
    param_values = list(param_grid.values())
    param_combinations = list(itertools.product(*param_values))
    
    # Przygotowanie do zapisania wyników
    optimization_results = []
    
    # Uruchomienie backtestingu dla każdej kombinacji parametrów
    for combination in param_combinations:
        # Tworzenie słownika parametrów
        params = {param_keys[i]: combination[i] for i in range(len(param_keys))}
        
        # Konfiguracja backtestingu
        config = BacktestConfig(
            symbol=symbol,
            timeframe=timeframe,
            start_date=start_date,
            end_date=end_date,
            initial_balance=10000.0,
            position_size_pct=1.0,
            strategy_name=f"{strategy_type}_{str(params)}",
            use_cache=True,
            update_cache=True,
            strategy_params=params
        )
        
        # Wybór strategii
        strategy_config = StrategyConfig(
            stop_loss_pips=50,
            take_profit_pips=100,
            position_size_pct=1.0,
            params=params
        )
        
        if strategy_type == "SMA":
            strategy = SimpleMovingAverageStrategy(
                config=strategy_config,
                fast_period=params.get("fast_period"),
                slow_period=params.get("slow_period")
            )
        elif strategy_type == "RSI":
            strategy = RSIStrategy(
                config=strategy_config,
                period=params.get("period"),
                oversold=params.get("oversold"),
                overbought=params.get("overbought")
            )
        elif strategy_type == "BB":
            strategy = BollingerBandsStrategy(
                config=strategy_config,
                period=params.get("period"),
                std_dev=params.get("std_dev")
            )
        elif strategy_type == "MACD":
            strategy = MACDStrategy(
                config=strategy_config,
                fast_period=params.get("fast_period"),
                slow_period=params.get("slow_period"),
                signal_period=params.get("signal_period")
            )
        
        # Inicjalizacja silnika backtestingu
        engine = BacktestEngine(config=config, strategy=strategy)
        
        # Uruchomienie backtestingu
        logger.info(f"Uruchamianie backtestingu dla {symbol} na timeframe {timeframe} z parametrami {params}")
        result = engine.run()
        
        # Zapisanie wyników
        result_file = result.save()
        
        # Dodanie do listy wyników optymalizacji
        optimization_results.append({
            "params": params,
            "net_profit": result.metrics.get("net_profit", 0),
            "win_rate": result.metrics.get("win_rate", 0),
            "trades": len(result.trades),
            "profit_factor": result.metrics.get("profit_factor", 0),
            "max_drawdown": result.metrics.get("max_drawdown", 0),
            "sharpe_ratio": result.metrics.get("sharpe_ratio", 0)
        })
    
    # Sortowanie wyników według zysku
    optimization_results.sort(key=lambda x: x["net_profit"], reverse=True)
    
    # Wyświetlenie najlepszych wyników
    print("\n=== WYNIKI OPTYMALIZACJI ===")
    print(f"Strategia: {strategy_type}, Symbol: {symbol}, Timeframe: {timeframe}")
    print(f"Okres: {start_date.strftime('%Y-%m-%d')} - {end_date.strftime('%Y-%m-%d')}")
    print("\nNajlepsze 5 kombinacji parametrów:")
    
    for i, result in enumerate(optimization_results[:5]):
        print(f"\n{i+1}. Parametry: {result['params']}")
        print(f"   Zysk/Strata: {result['net_profit']:.2f}")
        print(f"   Win Rate: {result['win_rate']:.2f}%")
        print(f"   Liczba transakcji: {result['trades']}")
        print(f"   Profit Factor: {result['profit_factor']:.2f}")
        print(f"   Max Drawdown: {result['max_drawdown']:.2f}%")
        print(f"   Sharpe Ratio: {result['sharpe_ratio']:.2f}")
    
    # Zapisanie wszystkich wyników do CSV
    import csv
    output_dir = Path("backtest_results")
    output_dir.mkdir(parents=True, exist_ok=True)
    csv_file = output_dir / f"{symbol}_{timeframe}_{strategy_type}_optimization_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    
    with open(csv_file, 'w', newline='') as file:
        writer = csv.writer(file)
        
        # Nagłówki
        headers = ["Rank"] + list(param_keys) + ["Net Profit", "Win Rate", "Trades", "Profit Factor", "Max Drawdown", "Sharpe Ratio"]
        writer.writerow(headers)
        
        # Dane
        for i, result in enumerate(optimization_results):
            row = [i+1]
            for key in param_keys:
                row.append(result["params"][key])
            row.extend([
                result["net_profit"],
                result["win_rate"],
                result["trades"],
                result["profit_factor"],
                result["max_drawdown"],
                result["sharpe_ratio"]
            ])
            writer.writerow(row)
    
    logger.info(f"Wyniki optymalizacji zapisane do: {csv_file}")


if __name__ == "__main__":
    # Przykład użycia
    # run_strategy_backtest(symbol="EURUSD", timeframe="H1", days=30, strategy_type="SMA")
    # run_strategy_comparison(symbol="EURUSD", timeframe="H1", days=30)
    # run_parameter_optimization(symbol="EURUSD", timeframe="H1", days=30, strategy_type="SMA")
    
    import argparse
    
    parser = argparse.ArgumentParser(description="Narzędzie do backtestingu strategii tradingowych")
    parser.add_argument("--mode", choices=["single", "compare", "optimize"], default="single", help="Tryb działania")
    parser.add_argument("--symbol", default="EURUSD", help="Symbol instrumentu")
    parser.add_argument("--timeframe", default="H1", help="Interwał czasowy")
    parser.add_argument("--days", type=int, default=30, help="Liczba dni wstecz")
    parser.add_argument("--strategy", default="SMA", help="Typ strategii (SMA, RSI, BB, MACD)")
    
    args = parser.parse_args()
    
    if args.mode == "single":
        run_strategy_backtest(symbol=args.symbol, timeframe=args.timeframe, days=args.days, strategy_type=args.strategy)
    elif args.mode == "compare":
        run_strategy_comparison(symbol=args.symbol, timeframe=args.timeframe, days=args.days)
    elif args.mode == "optimize":
        run_parameter_optimization(symbol=args.symbol, timeframe=args.timeframe, days=args.days, strategy_type=args.strategy) 