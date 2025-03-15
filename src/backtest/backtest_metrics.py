#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Moduł do obliczania metryk backtestingu i generowania raportów.
"""

import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Any, Optional
from datetime import datetime
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import json

from .backtest_engine import BacktestResult

logger = logging.getLogger(__name__)


def calculate_metrics(result: BacktestResult) -> Dict[str, Any]:
    """
    Oblicza metryki wydajności na podstawie wyników backtestingu.
    
    Args:
        result: Wyniki backtestingu
        
    Returns:
        Dict[str, Any]: Słownik zawierający obliczone metryki
    """
    metrics = {}
    
    # Podstawowe metryki
    initial_balance = result.config.initial_balance
    final_balance = result.balance
    
    # Zyski i straty
    metrics["net_profit"] = final_balance - initial_balance
    metrics["net_profit_percent"] = (metrics["net_profit"] / initial_balance) * 100 if initial_balance > 0 else 0
    
    # Metryki transakcji
    total_trades = len([t for t in result.trades if t.status == "closed"])
    metrics["total_trades"] = total_trades
    
    if total_trades > 0:
        winning_trades = len([t for t in result.trades if t.status == "closed" and t.profit > 0])
        losing_trades = len([t for t in result.trades if t.status == "closed" and t.profit <= 0])
        
        metrics["winning_trades"] = winning_trades
        metrics["losing_trades"] = losing_trades
        metrics["win_rate"] = (winning_trades / total_trades) * 100 if total_trades > 0 else 0
        
        # Średnie zyski i straty
        profit_trades = [t.profit for t in result.trades if t.status == "closed" and t.profit > 0]
        loss_trades = [t.profit for t in result.trades if t.status == "closed" and t.profit <= 0]
        
        metrics["avg_profit"] = np.mean(profit_trades) if profit_trades else 0
        metrics["avg_loss"] = np.mean(loss_trades) if loss_trades else 0
        metrics["largest_profit"] = max(profit_trades) if profit_trades else 0
        metrics["largest_loss"] = min(loss_trades) if loss_trades else 0
        
        # Współczynnik zysku do straty
        metrics["profit_factor"] = abs(sum(profit_trades) / sum(loss_trades)) if sum(loss_trades) != 0 else float('inf')
        
        # Stosunek średniego zysku do średniej straty
        metrics["reward_risk_ratio"] = abs(metrics["avg_profit"] / metrics["avg_loss"]) if metrics["avg_loss"] != 0 else float('inf')
        
        # Analiza kierunkowa
        buy_trades = [t for t in result.trades if t.status == "closed" and t.direction.upper() == "BUY"]
        sell_trades = [t for t in result.trades if t.status == "closed" and t.direction.upper() == "SELL"]
        
        metrics["buy_trades"] = len(buy_trades)
        metrics["sell_trades"] = len(sell_trades)
        
        if buy_trades:
            metrics["buy_win_rate"] = (len([t for t in buy_trades if t.profit > 0]) / len(buy_trades)) * 100
        else:
            metrics["buy_win_rate"] = 0
            
        if sell_trades:
            metrics["sell_win_rate"] = (len([t for t in sell_trades if t.profit > 0]) / len(sell_trades)) * 100
        else:
            metrics["sell_win_rate"] = 0
    else:
        # Domyślne wartości, gdy brak transakcji
        metrics["winning_trades"] = 0
        metrics["losing_trades"] = 0
        metrics["win_rate"] = 0
        metrics["avg_profit"] = 0
        metrics["avg_loss"] = 0
        metrics["largest_profit"] = 0
        metrics["largest_loss"] = 0
        metrics["profit_factor"] = 0
        metrics["reward_risk_ratio"] = 0
        metrics["buy_trades"] = 0
        metrics["sell_trades"] = 0
        metrics["buy_win_rate"] = 0
        metrics["sell_win_rate"] = 0
    
    # Analiza drawdown
    drawdowns = np.array(result.drawdowns)
    metrics["max_drawdown"] = np.max(drawdowns) if len(drawdowns) > 0 else 0
    metrics["avg_drawdown"] = np.mean(drawdowns) if len(drawdowns) > 0 else 0
    
    # Oblicz Sharpe Ratio, jeśli mamy co najmniej 2 punkty na krzywej equity
    if len(result.equity_curve) >= 2:
        equity_returns = np.diff(result.equity_curve) / result.equity_curve[:-1]
        metrics["sharpe_ratio"] = np.mean(equity_returns) / np.std(equity_returns) * np.sqrt(252) if np.std(equity_returns) > 0 else 0
        metrics["volatility"] = np.std(equity_returns) * 100  # Wyrażone w procentach
    else:
        metrics["sharpe_ratio"] = 0
        metrics["volatility"] = 0
    
    # Dodatkowe metryki
    if total_trades > 0:
        # Średni czas trwania transakcji
        trade_durations = [(t.exit_time - t.entry_time).total_seconds() / 3600 for t in result.trades if t.status == "closed" and t.exit_time]
        metrics["avg_trade_duration_hours"] = np.mean(trade_durations) if trade_durations else 0
        
        # Oczekiwana wartość
        metrics["expected_value"] = (metrics["win_rate"] / 100 * metrics["avg_profit"]) + ((100 - metrics["win_rate"]) / 100 * metrics["avg_loss"])
    else:
        metrics["avg_trade_duration_hours"] = 0
        metrics["expected_value"] = 0
    
    return metrics


def generate_report(result: BacktestResult, output_path: Optional[str] = None) -> str:
    """
    Generuje raport z wynikami backtestingu.
    
    Args:
        result: Wyniki backtestingu
        output_path: Opcjonalna ścieżka do zapisu raportu
        
    Returns:
        str: Ścieżka do wygenerowanego raportu
    """
    if output_path is None:
        Path(result.config.output_dir).mkdir(parents=True, exist_ok=True)
        output_path = f"{result.config.output_dir}/{result.config.symbol}_{result.config.timeframe}_{result.config.test_id}_report.html"
    
    # Oblicz metryki, jeśli nie zostały jeszcze obliczone
    if not result.metrics:
        result.metrics = calculate_metrics(result)
    
    # Generuj wykresy
    fig = plt.figure(figsize=(15, 10))
    fig.suptitle(f"Raport backtestingu: {result.config.symbol} {result.config.timeframe}", fontsize=16)
    
    # Wykres krzywej equity
    ax1 = plt.subplot(2, 2, 1)
    ax1.plot(result.timestamps, result.equity_curve)
    ax1.set_title("Krzywa equity")
    ax1.set_xlabel("Czas")
    ax1.set_ylabel("Equity")
    plt.xticks(rotation=45)
    
    # Wykres drawdownu
    ax2 = plt.subplot(2, 2, 2)
    ax2.plot(result.timestamps, result.drawdowns)
    ax2.set_title("Drawdown (%)")
    ax2.set_xlabel("Czas")
    ax2.set_ylabel("Drawdown (%)")
    plt.xticks(rotation=45)
    
    # Rozkład zysków i strat
    if result.trades:
        profits = [t.profit for t in result.trades if t.status == "closed"]
        ax3 = plt.subplot(2, 2, 3)
        sns.histplot(profits, kde=True, ax=ax3)
        ax3.set_title("Rozkład zysków i strat")
        ax3.set_xlabel("Zysk/strata")
        ax3.set_ylabel("Liczba transakcji")
        
        # Wykres skumulowanego P&L
        ax4 = plt.subplot(2, 2, 4)
        cumulative_pnl = np.cumsum([t.profit for t in sorted(result.trades, key=lambda x: x.entry_time) if t.status == "closed"])
        ax4.plot(cumulative_pnl)
        ax4.set_title("Skumulowany P&L")
        ax4.set_xlabel("Liczba transakcji")
        ax4.set_ylabel("P&L")
    
    plt.tight_layout(rect=[0, 0, 1, 0.95])
    
    # Zapisz wykresy
    charts_path = f"{result.config.output_dir}/{result.config.symbol}_{result.config.timeframe}_{result.config.test_id}_charts.png"
    plt.savefig(charts_path)
    plt.close()
    
    # Generuj raport HTML
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Raport backtestingu: {result.config.symbol} {result.config.timeframe}</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; }}
            h1, h2 {{ color: #333; }}
            table {{ border-collapse: collapse; width: 100%; margin-bottom: 20px; }}
            th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
            th {{ background-color: #f2f2f2; }}
            tr:nth-child(even) {{ background-color: #f9f9f9; }}
            .chart-container {{ margin: 20px 0; }}
            .section {{ margin-bottom: 30px; }}
        </style>
    </head>
    <body>
        <h1>Raport backtestingu: {result.config.symbol} {result.config.timeframe}</h1>
        
        <div class="section">
            <h2>Konfiguracja</h2>
            <table>
                <tr><th>Parametr</th><th>Wartość</th></tr>
                <tr><td>Symbol</td><td>{result.config.symbol}</td></tr>
                <tr><td>Timeframe</td><td>{result.config.timeframe}</td></tr>
                <tr><td>Okres</td><td>{result.config.start_date.strftime('%Y-%m-%d')} do {result.config.end_date.strftime('%Y-%m-%d')}</td></tr>
                <tr><td>Saldo początkowe</td><td>{result.config.initial_balance:.2f}</td></tr>
                <tr><td>Rozmiar pozycji (%)</td><td>{result.config.position_size_pct:.2f}%</td></tr>
                <tr><td>Prowizja</td><td>{result.config.commission} punktów</td></tr>
                <tr><td>Poślizg</td><td>{result.config.slippage} punktów</td></tr>
                <tr><td>Uwzględnienie spreadu</td><td>{'Tak' if result.config.use_spread else 'Nie'}</td></tr>
            </table>
        </div>
        
        <div class="section">
            <h2>Podsumowanie wyników</h2>
            <table>
                <tr><th>Metryka</th><th>Wartość</th></tr>
                <tr><td>Zysk netto</td><td>{result.metrics["net_profit"]:.2f} ({result.metrics["net_profit_percent"]:.2f}%)</td></tr>
                <tr><td>Liczba transakcji</td><td>{result.metrics["total_trades"]}</td></tr>
                <tr><td>Transakcje zyskowne</td><td>{result.metrics["winning_trades"]} ({result.metrics["win_rate"]:.2f}%)</td></tr>
                <tr><td>Transakcje stratne</td><td>{result.metrics["losing_trades"]}</td></tr>
                <tr><td>Średni zysk</td><td>{result.metrics["avg_profit"]:.2f}</td></tr>
                <tr><td>Średnia strata</td><td>{result.metrics["avg_loss"]:.2f}</td></tr>
                <tr><td>Największy zysk</td><td>{result.metrics["largest_profit"]:.2f}</td></tr>
                <tr><td>Największa strata</td><td>{result.metrics["largest_loss"]:.2f}</td></tr>
                <tr><td>Współczynnik zysku</td><td>{result.metrics["profit_factor"]:.2f}</td></tr>
                <tr><td>Stosunek zysku do ryzyka</td><td>{result.metrics["reward_risk_ratio"]:.2f}</td></tr>
                <tr><td>Maksymalny drawdown</td><td>{result.metrics["max_drawdown"]:.2f}%</td></tr>
                <tr><td>Sharpe Ratio</td><td>{result.metrics["sharpe_ratio"]:.2f}</td></tr>
                <tr><td>Zmienność</td><td>{result.metrics["volatility"]:.2f}%</td></tr>
                <tr><td>Średni czas trwania transakcji</td><td>{result.metrics["avg_trade_duration_hours"]:.2f} godz.</td></tr>
                <tr><td>Oczekiwana wartość</td><td>{result.metrics["expected_value"]:.2f}</td></tr>
            </table>
        </div>
        
        <div class="section">
            <h2>Analiza kierunkowa</h2>
            <table>
                <tr><th>Metryka</th><th>Wartość</th></tr>
                <tr><td>Liczba transakcji BUY</td><td>{result.metrics["buy_trades"]}</td></tr>
                <tr><td>Liczba transakcji SELL</td><td>{result.metrics["sell_trades"]}</td></tr>
                <tr><td>Skuteczność BUY</td><td>{result.metrics["buy_win_rate"]:.2f}%</td></tr>
                <tr><td>Skuteczność SELL</td><td>{result.metrics["sell_win_rate"]:.2f}%</td></tr>
            </table>
        </div>
        
        <div class="chart-container">
            <h2>Wykresy</h2>
            <img src="{charts_path}" alt="Wykresy backtestingu" style="width: 100%;">
        </div>
        
        <div class="section">
            <h2>Informacje o transakcjach</h2>
            <table>
                <tr>
                    <th>ID</th>
                    <th>Symbol</th>
                    <th>Kierunek</th>
                    <th>Wejście</th>
                    <th>Wyjście</th>
                    <th>Cena wejścia</th>
                    <th>Cena wyjścia</th>
                    <th>SL</th>
                    <th>TP</th>
                    <th>Wolumen</th>
                    <th>Zysk/Strata</th>
                    <th>Pipsy</th>
                    <th>Powód zamknięcia</th>
                </tr>
    """
    
    # Dodaj informacje o transakcjach
    for trade in sorted(result.trades, key=lambda x: x.entry_time):
        if trade.status == "closed":
            profit_color = "green" if trade.profit > 0 else "red"
            entry_time = trade.entry_time.strftime("%Y-%m-%d %H:%M")
            exit_time = trade.exit_time.strftime("%Y-%m-%d %H:%M") if trade.exit_time else "-"
            
            html_content += f"""
                <tr>
                    <td>{trade.signal_id}</td>
                    <td>{trade.symbol}</td>
                    <td>{trade.direction}</td>
                    <td>{entry_time}</td>
                    <td>{exit_time}</td>
                    <td>{trade.entry_price:.5f}</td>
                    <td>{trade.exit_price:.5f if trade.exit_price else '-'}</td>
                    <td>{trade.stop_loss:.5f}</td>
                    <td>{trade.take_profit:.5f}</td>
                    <td>{trade.volume:.2f}</td>
                    <td style="color: {profit_color}">{trade.profit:.2f}</td>
                    <td style="color: {profit_color}">{trade.pips:.1f}</td>
                    <td>{trade.reason}</td>
                </tr>
            """
    
    html_content += """
            </table>
        </div>
    </body>
    </html>
    """
    
    # Zapisz raport HTML
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    
    logger.info(f"Raport wygenerowany i zapisany do: {output_path}")
    return output_path 