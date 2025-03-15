#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Przykład użycia systemu backtestingu.
"""

import sys
import os
import logging
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import pandas as pd

# Dodaj katalog główny projektu do ścieżki
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))

from src.backtest import BacktestEngine, BacktestConfig, BacktestResult
from src.backtest.backtest_metrics import calculate_metrics, generate_report

# Konfiguracja logowania
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def run_example_backtest():
    """
    Uruchamia przykładowy backtest.
    """
    logger.info("Rozpoczynam przykładowy backtest")
    
    # Utwórz konfigurację backtestingu
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)  # Testuj na danych z ostatnich 30 dni
    
    config = BacktestConfig(
        symbol="EURUSD",
        timeframe="H1",
        start_date=start_date,
        end_date=end_date,
        initial_balance=10000.0,
        position_size_pct=1.0,
        commission=0.0,
        slippage=2.0,
        use_spread=True,
        min_volume=0.01,
        max_volume=1.0,
        strategy_name="example_strategy",
        output_dir="backtest_results"
    )
    
    # Utwórz silnik backtestingu i uruchom test
    engine = BacktestEngine(config)
    result = engine.run()
    
    # Wygeneruj raport
    report_path = generate_report(result)
    
    logger.info(f"Backtest zakończony, wyniki zapisane do {report_path}")
    
    # Wyświetl podsumowanie wyników
    print("\n============ PODSUMOWANIE WYNIKÓW BACKTESTINGU ============")
    print(f"Symbol: {config.symbol}, Timeframe: {config.timeframe}")
    print(f"Okres: {config.start_date.strftime('%Y-%m-%d')} - {config.end_date.strftime('%Y-%m-%d')}")
    print(f"Liczba transakcji: {result.metrics['total_trades']}")
    print(f"Zysk netto: {result.metrics['net_profit']:.2f} USD ({result.metrics['net_profit_percent']:.2f}%)")
    print(f"Win rate: {result.metrics['win_rate']:.2f}%")
    print(f"Średni zysk: {result.metrics['avg_profit']:.2f} USD")
    print(f"Średnia strata: {result.metrics['avg_loss']:.2f} USD")
    print(f"Współczynnik zysku: {result.metrics['profit_factor']:.2f}")
    print(f"Maksymalny drawdown: {result.metrics['max_drawdown']:.2f}%")
    print(f"Sharpe Ratio: {result.metrics['sharpe_ratio']:.2f}")
    print("============================================================\n")
    
    # Wyświetl wykres equity
    plt.figure(figsize=(12, 6))
    plt.plot(result.timestamps, result.equity_curve)
    plt.title(f"Krzywa equity - {config.symbol} {config.timeframe}")
    plt.xlabel("Czas")
    plt.ylabel("Equity (USD)")
    plt.grid(True)
    plt.tight_layout()
    plt.show()
    
    return result


def run_multiple_symbol_backtest(symbols: list):
    """
    Uruchamia backtest dla wielu symboli i porównuje wyniki.
    
    Args:
        symbols: Lista symboli do przetestowania
    """
    logger.info(f"Rozpoczynam backtest dla symboli: {symbols}")
    
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)
    
    results = {}
    summary_data = []
    
    for symbol in symbols:
        config = BacktestConfig(
            symbol=symbol,
            timeframe="H1",
            start_date=start_date,
            end_date=end_date,
            initial_balance=10000.0,
            position_size_pct=1.0,
            commission=0.0,
            slippage=2.0,
            use_spread=True,
            min_volume=0.01,
            max_volume=1.0,
            strategy_name="multi_symbol_test",
            output_dir="backtest_results/multi_symbol"
        )
        
        engine = BacktestEngine(config)
        result = engine.run()
        
        results[symbol] = result
        
        # Zbierz dane do porównania
        summary_data.append({
            "Symbol": symbol,
            "Zysk netto (%)": result.metrics["net_profit_percent"],
            "Liczba transakcji": result.metrics["total_trades"],
            "Win rate (%)": result.metrics["win_rate"],
            "Drawdown (%)": result.metrics["max_drawdown"],
            "Sharpe Ratio": result.metrics["sharpe_ratio"]
        })
        
        # Wygeneruj raport dla każdego symbolu
        generate_report(result)
    
    # Utwórz tabelę porównawczą
    summary_df = pd.DataFrame(summary_data)
    print("\n================ PORÓWNANIE WYNIKÓW ================")
    print(summary_df.to_string(index=False))
    print("=====================================================\n")
    
    # Wykreśl porównanie wyników
    plt.figure(figsize=(12, 8))
    
    # Wykres zysku netto
    plt.subplot(2, 2, 1)
    plt.bar(summary_df["Symbol"], summary_df["Zysk netto (%)"])
    plt.title("Zysk netto (%)")
    plt.grid(True, axis='y')
    
    # Wykres win rate
    plt.subplot(2, 2, 2)
    plt.bar(summary_df["Symbol"], summary_df["Win rate (%)"])
    plt.title("Win rate (%)")
    plt.grid(True, axis='y')
    
    # Wykres drawdown
    plt.subplot(2, 2, 3)
    plt.bar(summary_df["Symbol"], summary_df["Drawdown (%)"])
    plt.title("Maksymalny drawdown (%)")
    plt.grid(True, axis='y')
    
    # Wykres Sharpe Ratio
    plt.subplot(2, 2, 4)
    plt.bar(summary_df["Symbol"], summary_df["Sharpe Ratio"])
    plt.title("Sharpe Ratio")
    plt.grid(True, axis='y')
    
    plt.tight_layout()
    plt.show()
    
    return results


def run_timeframe_comparison(symbol: str, timeframes: list):
    """
    Uruchamia backtest dla jednego symbolu na różnych timeframe'ach.
    
    Args:
        symbol: Symbol do przetestowania
        timeframes: Lista timeframe'ów do przetestowania
    """
    logger.info(f"Rozpoczynam porównanie timeframe'ów dla {symbol}: {timeframes}")
    
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)
    
    results = {}
    summary_data = []
    
    for tf in timeframes:
        config = BacktestConfig(
            symbol=symbol,
            timeframe=tf,
            start_date=start_date,
            end_date=end_date,
            initial_balance=10000.0,
            position_size_pct=1.0,
            commission=0.0,
            slippage=2.0,
            use_spread=True,
            min_volume=0.01,
            max_volume=1.0,
            strategy_name="timeframe_comparison",
            output_dir="backtest_results/timeframe_comparison"
        )
        
        engine = BacktestEngine(config)
        result = engine.run()
        
        results[tf] = result
        
        # Zbierz dane do porównania
        summary_data.append({
            "Timeframe": tf,
            "Zysk netto (%)": result.metrics["net_profit_percent"],
            "Liczba transakcji": result.metrics["total_trades"],
            "Win rate (%)": result.metrics["win_rate"],
            "Drawdown (%)": result.metrics["max_drawdown"],
            "Sharpe Ratio": result.metrics["sharpe_ratio"]
        })
        
        # Wygeneruj raport dla każdego timeframe'u
        generate_report(result)
    
    # Utwórz tabelę porównawczą
    summary_df = pd.DataFrame(summary_data)
    print(f"\n================ PORÓWNANIE TIMEFRAME'ÓW DLA {symbol} ================")
    print(summary_df.to_string(index=False))
    print("======================================================================\n")
    
    # Wykreśl porównanie wyników
    plt.figure(figsize=(12, 8))
    
    # Wykres zysku netto
    plt.subplot(2, 2, 1)
    plt.bar(summary_df["Timeframe"], summary_df["Zysk netto (%)"])
    plt.title("Zysk netto (%)")
    plt.grid(True, axis='y')
    
    # Wykres win rate
    plt.subplot(2, 2, 2)
    plt.bar(summary_df["Timeframe"], summary_df["Win rate (%)"])
    plt.title("Win rate (%)")
    plt.grid(True, axis='y')
    
    # Wykres drawdown
    plt.subplot(2, 2, 3)
    plt.bar(summary_df["Timeframe"], summary_df["Drawdown (%)"])
    plt.title("Maksymalny drawdown (%)")
    plt.grid(True, axis='y')
    
    # Wykres liczby transakcji
    plt.subplot(2, 2, 4)
    plt.bar(summary_df["Timeframe"], summary_df["Liczba transakcji"])
    plt.title("Liczba transakcji")
    plt.grid(True, axis='y')
    
    plt.suptitle(f"Porównanie timeframe'ów dla {symbol}")
    plt.tight_layout()
    plt.show()
    
    return results


if __name__ == "__main__":
    # Przykład pojedynczego backtestu
    result = run_example_backtest()
    
    # Przykład porównania wielu symboli
    # multi_symbol_results = run_multiple_symbol_backtest(["EURUSD", "GBPUSD", "USDJPY", "AUDUSD"])
    
    # Przykład porównania różnych timeframe'ów
    # timeframe_results = run_timeframe_comparison("EURUSD", ["M15", "H1", "H4", "D1"]) 