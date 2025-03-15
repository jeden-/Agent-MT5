#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Przykład użycia zaawansowanych funkcji zarządzania pozycjami w backtestingu.
Demonstruje wykorzystanie trailing stop, breakeven i częściowego zamykania pozycji.
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
from backtest.strategy import RSIStrategy, StrategyConfig
from mt5.mt5_connector import MT5Connector
from utils.logger import setup_logger

# Konfiguracja logowania
setup_logger()
logger = logging.getLogger(__name__)

def run_backtest_with_position_management(symbol="EURUSD", timeframe="M15", days=30,
                                        use_trailing_stop=True, use_breakeven=True, use_partial_close=True):
    """
    Uruchamia backtest z zaawansowanym zarządzaniem pozycjami.
    
    Args:
        symbol: Symbol instrumentu (default: "EURUSD")
        timeframe: Interwał czasowy (default: "M15")
        days: Liczba dni danych historycznych (default: 30)
        use_trailing_stop: Czy używać trailing stop (default: True)
        use_breakeven: Czy używać breakeven (default: True)
        use_partial_close: Czy używać częściowego zamykania (default: True)
    """
    # Inicjalizacja łącznika MT5
    mt5_connector = MT5Connector()
    mt5_connector.initialize()
    
    # Ustawienie dat dla backtestingu
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    
    logger.info(f"Rozpoczynam backtest z zarządzaniem pozycjami dla {symbol} na timeframe {timeframe}")
    logger.info(f"Okres: {start_date.date()} - {end_date.date()}")
    logger.info(f"Trailing stop: {'Włączony' if use_trailing_stop else 'Wyłączony'}")
    logger.info(f"Breakeven: {'Włączony' if use_breakeven else 'Wyłączony'}")
    logger.info(f"Częściowe zamykanie: {'Włączone' if use_partial_close else 'Wyłączone'}")
    
    # Konfiguracja częściowego zamykania, jeśli jest włączone
    partial_close_levels = []
    if use_partial_close:
        # Format: (poziom w pipsach, procent do zamknięcia)
        partial_close_levels = [
            (15, 25),  # Zamknij 25% pozycji przy 15 pipsach zysku
            (30, 25),  # Zamknij kolejne 25% przy 30 pipsach zysku
            (50, 50)   # Zamknij pozostałe 50% przy 50 pipsach zysku
        ]
    
    # Konfiguracja backtestingu
    config = BacktestConfig(
        symbol=symbol,
        timeframe=timeframe,
        start_date=start_date,
        end_date=end_date,
        initial_balance=10000.0,
        position_size_pct=2.0,
        use_cache=True,
        
        # Parametry zarządzania pozycjami
        use_trailing_stop=use_trailing_stop,
        trailing_stop_pips=20.0,
        use_breakeven=use_breakeven,
        breakeven_trigger_pips=15.0,
        breakeven_plus_pips=2.0,
        use_partial_close=use_partial_close,
        partial_close_levels=partial_close_levels
    )
    
    # Konfiguracja strategii (używamy prostej strategii RSI dla przykładu)
    strategy_config = StrategyConfig(
        stop_loss_pips=25,
        take_profit_pips=50,
        position_size_pct=2.0,
        params={
            'rsi_period': 14,
            'overbought_level': 70,
            'oversold_level': 30
        }
    )
    
    # Inicjalizacja strategii
    strategy = RSIStrategy(config=strategy_config)
    
    # Inicjalizacja silnika backtestingu
    backtest_engine = BacktestEngine(
        config=config,
        strategy=strategy
    )
    
    # Uruchomienie backtestingu
    result = backtest_engine.run()
    
    # Wyświetlenie wyników
    logger.info(f"Wyniki backtestingu:")
    logger.info(f"Liczba transakcji: {len(result.trades)}")
    logger.info(f"Zysk netto: {result.metrics.get('net_profit', 0):.2f}")
    logger.info(f"Odsetek wygranych: {result.metrics.get('win_rate', 0):.2f}%")
    logger.info(f"Współczynnik zysku: {result.metrics.get('profit_factor', 0):.2f}")
    logger.info(f"Maksymalny drawdown: {result.metrics.get('max_drawdown', 0):.2f}%")
    
    # Generowanie wykresów
    plt.figure(figsize=(12, 6))
    plt.subplot(2, 1, 1)
    plt.plot(result.timestamps, result.equity_curve)
    plt.title(f"Krzywa kapitału - {symbol}:{timeframe}")
    plt.grid(True)
    
    plt.subplot(2, 1, 2)
    plt.plot(result.timestamps, result.drawdowns)
    plt.title("Drawdown (%)")
    plt.grid(True)
    
    # Utworzenie katalogu na wyniki, jeśli nie istnieje
    results_dir = Path("results")
    results_dir.mkdir(parents=True, exist_ok=True)
    
    # Zapisanie wykresu
    plt.tight_layout()
    plt.savefig(results_dir / f"{symbol}_{timeframe}_position_management.png")
    
    # Zapisanie raportu
    result_file = result.save(str(results_dir / f"{symbol}_{timeframe}_position_management.json"))
    
    logger.info(f"Wykresy i raport zapisane w katalogu: {results_dir}")
    
    mt5_connector.shutdown()

def compare_position_management_strategies(symbol="EURUSD", timeframe="M15", days=30):
    """
    Porównuje wyniki backtestingu z różnymi strategiami zarządzania pozycjami.
    
    Args:
        symbol: Symbol instrumentu (default: "EURUSD")
        timeframe: Interwał czasowy (default: "M15")
        days: Liczba dni danych historycznych (default: 30)
    """
    logger.info("Rozpoczynam porównanie strategii zarządzania pozycjami")
    
    # Definicje strategii zarządzania pozycjami do porównania
    strategies = [
        {"name": "Podstawowa (bez zarządzania)", "ts": False, "be": False, "pc": False},
        {"name": "Tylko Trailing Stop", "ts": True, "be": False, "pc": False},
        {"name": "Tylko Breakeven", "ts": False, "be": True, "pc": False},
        {"name": "Tylko Częściowe Zamykanie", "ts": False, "be": False, "pc": True},
        {"name": "Pełne Zarządzanie", "ts": True, "be": True, "pc": True},
    ]
    
    results = []
    
    # Inicjalizacja łącznika MT5
    mt5_connector = MT5Connector()
    mt5_connector.initialize()
    
    # Ustawienie dat dla backtestingu
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    
    for strategy in strategies:
        logger.info(f"Testowanie strategii: {strategy['name']}")
        
        # Konfiguracja częściowego zamykania, jeśli jest włączone
        partial_close_levels = []
        if strategy["pc"]:
            partial_close_levels = [
                (15, 25),  # Zamknij 25% pozycji przy 15 pipsach zysku
                (30, 25),  # Zamknij kolejne 25% przy 30 pipsach zysku
                (50, 50)   # Zamknij pozostałe 50% przy 50 pipsach zysku
            ]
        
        # Konfiguracja backtestingu
        config = BacktestConfig(
            symbol=symbol,
            timeframe=timeframe,
            start_date=start_date,
            end_date=end_date,
            initial_balance=10000.0,
            position_size_pct=2.0,
            use_cache=True,
            
            # Parametry zarządzania pozycjami
            use_trailing_stop=strategy["ts"],
            trailing_stop_pips=20.0,
            use_breakeven=strategy["be"],
            breakeven_trigger_pips=15.0,
            breakeven_plus_pips=2.0,
            use_partial_close=strategy["pc"],
            partial_close_levels=partial_close_levels
        )
        
        # Konfiguracja strategii (używamy prostej strategii RSI dla przykładu)
        strategy_config = StrategyConfig(
            stop_loss_pips=25,
            take_profit_pips=50,
            position_size_pct=2.0,
            params={
                'rsi_period': 14,
                'overbought_level': 70,
                'oversold_level': 30
            }
        )
        
        # Inicjalizacja strategii
        rsi_strategy = RSIStrategy(config=strategy_config)
        
        # Inicjalizacja silnika backtestingu
        backtest_engine = BacktestEngine(
            config=config,
            strategy=rsi_strategy
        )
        
        # Uruchomienie backtestingu
        result = backtest_engine.run()
        
        # Zbieranie wyników
        results.append({
            "name": strategy["name"],
            "equity_curve": result.equity_curve,
            "timestamps": result.timestamps,
            "net_profit": result.metrics.get("net_profit", 0),
            "win_rate": result.metrics.get("win_rate", 0),
            "profit_factor": result.metrics.get("profit_factor", 0),
            "max_drawdown": result.metrics.get("max_drawdown", 0),
            "trades": len(result.trades)
        })
        
        logger.info(f"Strategia {strategy['name']}: Zysk netto = {result.metrics.get('net_profit', 0):.2f}, Win Rate = {result.metrics.get('win_rate', 0):.2f}%")
    
    # Generowanie wykresu porównawczego
    plt.figure(figsize=(15, 10))
    
    # Wykres krzywych equity
    plt.subplot(2, 1, 1)
    for result in results:
        # Normalizacja krzywej equity do początkowego kapitału
        normalized_equity = [e / results[0]["equity_curve"][0] for e in result["equity_curve"]]
        plt.plot(result["timestamps"], normalized_equity, label=result["name"])
    
    plt.title("Porównanie strategii zarządzania pozycjami - Znormalizowana krzywa kapitału")
    plt.grid(True)
    plt.legend()
    
    # Tabela wyników
    plt.subplot(2, 1, 2)
    plt.axis('off')
    table_data = [
        ["Strategia", "Zysk netto", "Win Rate", "Profit Factor", "Max DD", "Liczba transakcji"]
    ]
    
    for result in results:
        table_data.append([
            result["name"],
            f"{result['net_profit']:.2f}",
            f"{result['win_rate']:.2f}%",
            f"{result['profit_factor']:.2f}",
            f"{result['max_drawdown']:.2f}%",
            str(result["trades"])
        ])
    
    table = plt.table(
        cellText=table_data,
        loc='center',
        cellLoc='center',
        colWidths=[0.2, 0.1, 0.1, 0.1, 0.1, 0.1]
    )
    table.auto_set_font_size(False)
    table.set_fontsize(10)
    table.scale(1, 2)
    
    # Utworzenie katalogu na wyniki, jeśli nie istnieje
    results_dir = Path("results")
    results_dir.mkdir(parents=True, exist_ok=True)
    
    # Zapisanie wykresu
    plt.tight_layout()
    plt.savefig(results_dir / f"{symbol}_{timeframe}_position_management_comparison.png")
    
    logger.info(f"Wykres porównawczy zapisany w: {results_dir}")
    
    mt5_connector.shutdown()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Przykład backtestingu z zaawansowanym zarządzaniem pozycjami")
    parser.add_argument('--symbol', type=str, default="EURUSD", help="Symbol instrumentu")
    parser.add_argument('--timeframe', type=str, default="M15", help="Interwał czasowy")
    parser.add_argument('--days', type=int, default=30, help="Liczba dni danych historycznych")
    parser.add_argument('--mode', type=str, choices=['single', 'compare'], default='single',
                        help="Tryb backtestingu: 'single' dla pojedynczego testu lub 'compare' dla porównania strategii")
    parser.add_argument('--no-trailing', action='store_true', help="Wyłącz trailing stop")
    parser.add_argument('--no-breakeven', action='store_true', help="Wyłącz breakeven")
    parser.add_argument('--no-partial', action='store_true', help="Wyłącz częściowe zamykanie")
    
    args = parser.parse_args()
    
    if args.mode == 'single':
        run_backtest_with_position_management(
            symbol=args.symbol,
            timeframe=args.timeframe,
            days=args.days,
            use_trailing_stop=not args.no_trailing,
            use_breakeven=not args.no_breakeven,
            use_partial_close=not args.no_partial
        )
    else:
        compare_position_management_strategies(
            symbol=args.symbol,
            timeframe=args.timeframe,
            days=args.days
        ) 