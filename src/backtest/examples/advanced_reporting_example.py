#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Przykład zaawansowanego raportowania i wizualizacji wyników backtestingu.
Ten moduł demonstruje rozszerzone metody raportowania i wizualizacji danych z backtestingu.
"""

import logging
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.express as px
from pathlib import Path
from datetime import datetime, timedelta
import json
import os
from typing import List, Dict, Any, Optional, Union, Tuple

from ..backtest_engine import BacktestEngine, BacktestConfig, BacktestResult
from ..backtest_metrics import calculate_metrics, generate_report
from ..strategy import TradingStrategy, StrategyConfig, SMAStrategy, RSIStrategy, BollingerBandsStrategy, MACDStrategy, CombinedIndicatorsStrategy
from ...utils.mt5_connector import get_mt5_connector
from ...utils.logger import setup_logger

# Konfiguracja logowania
logger = setup_logger(__name__)

def generate_interactive_equity_chart(result: BacktestResult, output_path: Optional[str] = None) -> str:
    """
    Generuje interaktywny wykres krzywej equity za pomocą Plotly.
    
    Args:
        result: Wyniki backtestingu
        output_path: Opcjonalna ścieżka do zapisu wykresu
        
    Returns:
        str: Ścieżka do wygenerowanego pliku HTML
    """
    if output_path is None:
        Path(result.config.output_dir).mkdir(parents=True, exist_ok=True)
        output_path = f"{result.config.output_dir}/{result.config.symbol}_{result.config.timeframe}_{result.config.test_id}_interactive_chart.html"
    
    # Tworzenie wykresu Plotly
    fig = make_subplots(
        rows=2, 
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.1,
        subplot_titles=("Krzywa equity", "Drawdown (%)")
    )
    
    # Dodanie krzywej equity
    fig.add_trace(
        go.Scatter(
            x=result.timestamps,
            y=result.equity_curve,
            mode='lines',
            name='Equity',
            line=dict(color='blue', width=2)
        ),
        row=1, col=1
    )
    
    # Dodanie drawdownu
    fig.add_trace(
        go.Scatter(
            x=result.timestamps,
            y=result.drawdowns,
            mode='lines',
            name='Drawdown (%)',
            line=dict(color='red', width=2),
            fill='tozeroy'
        ),
        row=2, col=1
    )
    
    # Oznaczenie transakcji na wykresie
    buy_entries = []
    buy_exits = []
    sell_entries = []
    sell_exits = []
    
    for trade in result.trades:
        if trade.status == "closed":
            if trade.direction.upper() == "BUY":
                buy_entries.append((trade.entry_time, trade.entry_price))
                buy_exits.append((trade.exit_time, trade.exit_price))
            else:
                sell_entries.append((trade.entry_time, trade.entry_price))
                sell_exits.append((trade.exit_time, trade.exit_price))
    
    # Dodanie znaczników transakcji BUY
    if buy_entries:
        entry_times, entry_prices = zip(*buy_entries)
        fig.add_trace(
            go.Scatter(
                x=entry_times,
                y=[result.equity_curve[result.timestamps.index(t)] if t in result.timestamps else None for t in entry_times],
                mode='markers',
                name='Buy Entry',
                marker=dict(color='green', size=8, symbol='triangle-up')
            ),
            row=1, col=1
        )
    
    if buy_exits:
        exit_times, exit_prices = zip(*buy_exits)
        fig.add_trace(
            go.Scatter(
                x=exit_times,
                y=[result.equity_curve[result.timestamps.index(t)] if t in result.timestamps else None for t in exit_times],
                mode='markers',
                name='Buy Exit',
                marker=dict(color='darkgreen', size=8, symbol='circle')
            ),
            row=1, col=1
        )
    
    # Dodanie znaczników transakcji SELL
    if sell_entries:
        entry_times, entry_prices = zip(*sell_entries)
        fig.add_trace(
            go.Scatter(
                x=entry_times,
                y=[result.equity_curve[result.timestamps.index(t)] if t in result.timestamps else None for t in entry_times],
                mode='markers',
                name='Sell Entry',
                marker=dict(color='red', size=8, symbol='triangle-down')
            ),
            row=1, col=1
        )
    
    if sell_exits:
        exit_times, exit_prices = zip(*sell_exits)
        fig.add_trace(
            go.Scatter(
                x=exit_times,
                y=[result.equity_curve[result.timestamps.index(t)] if t in result.timestamps else None for t in exit_times],
                mode='markers',
                name='Sell Exit',
                marker=dict(color='darkred', size=8, symbol='circle')
            ),
            row=1, col=1
        )
    
    # Dodanie informacji o profitach
    monthly_profits = {}
    for trade in result.trades:
        if trade.status == "closed" and trade.exit_time:
            month_key = trade.exit_time.strftime("%Y-%m")
            if month_key not in monthly_profits:
                monthly_profits[month_key] = 0
            monthly_profits[month_key] += trade.profit
    
    months = sorted(monthly_profits.keys())
    profits = [monthly_profits[m] for m in months]
    
    # Dodanie wykresu profitów miesięcznych
    fig2 = go.Figure()
    fig2.add_trace(
        go.Bar(
            x=months,
            y=profits,
            marker_color=['green' if p > 0 else 'red' for p in profits],
            name='Monthly Profit'
        )
    )
    
    fig2.update_layout(
        title="Miesięczne zyski/straty",
        xaxis_title="Miesiąc",
        yaxis_title="Zysk/Strata",
        barmode='group'
    )
    
    # Formatowanie głównego wykresu
    fig.update_layout(
        title=f"Wyniki backtestingu dla {result.config.symbol} {result.config.timeframe}",
        height=800,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )
    
    fig.update_xaxes(title_text="Data")
    fig.update_yaxes(title_text="Equity", row=1, col=1)
    fig.update_yaxes(title_text="Drawdown (%)", row=2, col=1)
    
    # Zapisanie wykresów
    fig.write_html(output_path)
    monthly_path = output_path.replace('_interactive_chart.html', '_monthly_profits.html')
    fig2.write_html(monthly_path)
    
    logger.info(f"Interaktywny wykres wygenerowany i zapisany do: {output_path}")
    logger.info(f"Wykres miesięcznych zysków zapisany do: {monthly_path}")
    
    return output_path


def generate_performance_dashboard(results: List[Dict[str, Any]], output_path: str) -> str:
    """
    Generuje dashboard porównawczy dla wielu backtestrów.
    
    Args:
        results: Lista wyników z różnych backtestrów
        output_path: Ścieżka do zapisu dashboardu
        
    Returns:
        str: Ścieżka do wygenerowanego dashboardu
    """
    # Upewnienie się, że katalog istnieje
    Path(os.path.dirname(output_path)).mkdir(parents=True, exist_ok=True)
    
    # Utworzenie dashboardu z Plotly
    fig = make_subplots(
        rows=3, 
        cols=2,
        specs=[
            [{"colspan": 2}, None],
            [{}, {}],
            [{}, {}]
        ],
        subplot_titles=(
            "Porównanie krzywych equity", 
            "Rozkład profitów", "Miesięczne stopy zwrotu",
            "Drawdown", "Czas trwania transakcji"
        )
    )
    
    # Dodanie porównania krzywych equity
    for result in results:
        # Normalizacja krzywej equity do początkowej wartości
        initial_equity = result['equity_curve'][0]
        normalized_equity = [e / initial_equity for e in result['equity_curve']]
        
        fig.add_trace(
            go.Scatter(
                x=result['timestamps'],
                y=normalized_equity,
                mode='lines',
                name=result['name']
            ),
            row=1, col=1
        )
    
    # Dodanie histogramu profitów
    for i, result in enumerate(results):
        if 'trade_profits' in result and result['trade_profits']:
            fig.add_trace(
                go.Histogram(
                    x=result['trade_profits'],
                    name=result['name'],
                    opacity=0.7,
                    nbinsx=20
                ),
                row=2, col=1
            )
    
    # Dodanie miesięcznych stóp zwrotu
    for i, result in enumerate(results):
        if 'monthly_returns' in result and result['monthly_returns']:
            months = list(result['monthly_returns'].keys())
            returns = list(result['monthly_returns'].values())
            
            fig.add_trace(
                go.Bar(
                    x=months,
                    y=returns,
                    name=result['name']
                ),
                row=2, col=2
            )
    
    # Dodanie drawdown
    for i, result in enumerate(results):
        fig.add_trace(
            go.Scatter(
                x=result['timestamps'],
                y=result['drawdowns'],
                mode='lines',
                name=result['name'],
                line=dict(width=1)
            ),
            row=3, col=1
        )
    
    # Dodanie czasu trwania transakcji
    for i, result in enumerate(results):
        if 'trade_durations' in result and result['trade_durations']:
            fig.add_trace(
                go.Box(
                    y=result['trade_durations'],
                    name=result['name']
                ),
                row=3, col=2
            )
    
    # Formatowanie dashboardu
    fig.update_layout(
        title_text="Dashboard porównania wyników backtestu",
        height=1000,
        template="plotly_white",
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )
    
    # Ustawienie tytułów osi
    fig.update_xaxes(title_text="Data", row=1, col=1)
    fig.update_yaxes(title_text="Znormalizowana wartość kapitału", row=1, col=1)
    
    fig.update_xaxes(title_text="Zysk/Strata", row=2, col=1)
    fig.update_yaxes(title_text="Liczba transakcji", row=2, col=1)
    
    fig.update_xaxes(title_text="Miesiąc", row=2, col=2)
    fig.update_yaxes(title_text="Stopa zwrotu (%)", row=2, col=2)
    
    fig.update_xaxes(title_text="Data", row=3, col=1)
    fig.update_yaxes(title_text="Drawdown (%)", row=3, col=1)
    
    fig.update_xaxes(title_text="Strategia", row=3, col=2)
    fig.update_yaxes(title_text="Czas trwania (godz.)", row=3, col=2)
    
    # Zapisanie dashboardu
    fig.write_html(output_path)
    
    logger.info(f"Dashboard porównawczy zapisany do: {output_path}")
    
    return output_path


def run_advanced_reporting_example():
    """
    Przykład generowania zaawansowanych raportów dla wyników backtestingu.
    """
    logger.info("Rozpoczynam przykład zaawansowanego raportowania backtestingu")
    
    # Inicjalizacja MT5
    mt5_connector = get_mt5_connector()
    
    # Parametry backtestingu
    symbol = "EURUSD"
    timeframe = "H1"
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)
    
    # Definicje strategii
    strategies = [
        {
            "name": "SMA CrossOver",
            "class": SMAStrategy,
            "config": {"fast_period": 10, "slow_period": 30}
        },
        {
            "name": "RSI Strategy",
            "class": RSIStrategy,
            "config": {"period": 14, "oversold": 30, "overbought": 70}
        },
        {
            "name": "MACD Strategy",
            "class": MACDStrategy,
            "config": {"fast_period": 12, "slow_period": 26, "signal_period": 9}
        },
        {
            "name": "Combined Strategy",
            "class": CombinedIndicatorsStrategy,
            "config": {
                "weights": {
                    "trend": 0.25,
                    "macd": 0.30, 
                    "rsi": 0.20,
                    "bb": 0.15,
                    "candle": 0.10
                },
                "thresholds": {
                    "signal_minimum": 0.2,
                    "signal_ratio": 1.2,
                    "rsi_overbought": 70,
                    "rsi_oversold": 30
                }
            }
        }
    ]
    
    # Przygotowanie katalogu na wyniki
    output_dir = Path("advanced_backtest_results")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Zbieranie rezultatów dla dashboard
    dashboard_results = []
    
    # Uruchomienie backtestingu dla każdej strategii
    for strategy_def in strategies:
        logger.info(f"Uruchamiam backtest dla strategii {strategy_def['name']}")
        
        # Konfiguracja strategii
        strategy_config = StrategyConfig(
            stop_loss_pips=50,
            take_profit_pips=100,
            position_size_pct=1.0,
            params=strategy_def["config"]
        )
        
        # Inicjalizacja strategii
        strategy = strategy_def["class"](config=strategy_config)
        
        # Konfiguracja backtestingu
        backtest_config = BacktestConfig(
            symbol=symbol,
            timeframe=timeframe,
            start_date=start_date,
            end_date=end_date,
            initial_balance=10000.0,
            position_size_pct=1.0,
            commission=0.0,
            slippage=2.0,
            use_spread=True,
            strategy_name=strategy_def["name"],
            output_dir=str(output_dir)
        )
        
        # Inicjalizacja silnika backtestingu
        engine = BacktestEngine(
            mt5_connector=mt5_connector,
            symbol=symbol,
            timeframe=timeframe,
            config=backtest_config,
            strategy=strategy
        )
        
        # Uruchomienie backtestingu
        try:
            result = engine.run()
            
            # Standardowy raport HTML
            report_path = generate_report(result)
            logger.info(f"Raport HTML wygenerowany: {report_path}")
            
            # Interaktywny wykres Plotly
            interactive_chart_path = generate_interactive_equity_chart(result)
            logger.info(f"Interaktywny wykres wygenerowany: {interactive_chart_path}")
            
            # Obliczenie miesięcznych stóp zwrotu
            monthly_returns = {}
            monthly_equity = {}
            
            for i, timestamp in enumerate(result.timestamps):
                month_key = timestamp.strftime("%Y-%m")
                if month_key not in monthly_equity:
                    monthly_equity[month_key] = result.equity_curve[i]
                else:
                    monthly_equity[month_key] = result.equity_curve[i]
            
            prev_month = None
            for month in sorted(monthly_equity.keys()):
                if prev_month:
                    monthly_return = ((monthly_equity[month] / monthly_equity[prev_month]) - 1) * 100
                    monthly_returns[month] = monthly_return
                prev_month = month
            
            # Obliczenie czasu trwania transakcji w godzinach
            trade_durations = []
            trade_profits = []
            
            for trade in result.trades:
                if trade.status == "closed" and trade.exit_time:
                    duration = (trade.exit_time - trade.entry_time).total_seconds() / 3600  # w godzinach
                    trade_durations.append(duration)
                    trade_profits.append(trade.profit)
            
            # Dodanie danych do wyników dashboard
            dashboard_results.append({
                "name": strategy_def["name"],
                "equity_curve": result.equity_curve,
                "timestamps": result.timestamps,
                "drawdowns": result.drawdowns,
                "trade_profits": trade_profits,
                "trade_durations": trade_durations,
                "monthly_returns": monthly_returns,
                "net_profit": result.metrics["net_profit"] if result.metrics else 0,
                "win_rate": result.metrics["win_rate"] if result.metrics else 0,
                "profit_factor": result.metrics["profit_factor"] if result.metrics else 0,
                "max_drawdown": result.metrics["max_drawdown"] if result.metrics else 0,
                "sharpe_ratio": result.metrics["sharpe_ratio"] if result.metrics else 0
            })
            
        except Exception as e:
            logger.error(f"Błąd podczas backtestingu strategii {strategy_def['name']}: {e}")
    
    # Generowanie dashboardu porównawczego
    if dashboard_results:
        dashboard_path = str(output_dir / f"{symbol}_{timeframe}_dashboard_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html")
        generate_performance_dashboard(dashboard_results, dashboard_path)
        
        # Generowanie tabeli porównawczej do CSV
        comparison_data = []
        for result in dashboard_results:
            comparison_data.append({
                "Strategia": result["name"],
                "Zysk netto": result["net_profit"],
                "Win Rate (%)": result["win_rate"],
                "Profit Factor": result["profit_factor"],
                "Max Drawdown (%)": result["max_drawdown"],
                "Sharpe Ratio": result["sharpe_ratio"],
                "Liczba transakcji": len(result["trade_profits"]) if "trade_profits" in result else 0
            })
        
        comparison_df = pd.DataFrame(comparison_data)
        csv_path = str(output_dir / f"{symbol}_{timeframe}_comparison_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
        comparison_df.to_csv(csv_path, index=False)
        
        logger.info(f"Tabela porównawcza zapisana do: {csv_path}")
        
        # Wyświetlenie tabeli porównawczej
        print("\n=== PORÓWNANIE STRATEGII ===")
        print(comparison_df.to_string(index=False))


if __name__ == "__main__":
    run_advanced_reporting_example() 