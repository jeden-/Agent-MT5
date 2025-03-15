#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Moduł walk-forward testingu dla strategii tradingowych.

Ten moduł zawiera implementację procedury walk-forward testingu, która łączy
optymalizację parametrów na danych historycznych z testem na nowych danych w celu
oceny skuteczności strategii tradingowych w różnych warunkach rynkowych.
"""

import os
import logging
import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional, Tuple, Union
from datetime import datetime, timedelta
from pathlib import Path
import json
import time
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.gridspec import GridSpec
import seaborn as sns

from src.backtest.backtest_engine import BacktestEngine, BacktestConfig, BacktestResult
from src.backtest.strategy import TradingStrategy, StrategyConfig
from src.backtest.parameter_optimizer import ParameterOptimizer

logger = logging.getLogger(__name__)


class WalkForwardTester:
    """
    Klasa do przeprowadzania walk-forward testingu strategii tradingowych.
    
    Attributes:
        strategy_class: Klasa strategii do testowania
        parameter_space: Słownik zawierający zakresy parametrów do przeszukania
        train_days: Liczba dni w okresie treningowym
        test_days: Liczba dni w okresie testowym
        step_days: Liczba dni przesunięcia okna
        anchor_mode: Tryb przesuwania okna (rolling lub anchored)
        evaluation_metric: Metryka używana do oceny wyników
        workers: Liczba równoległych procesów
        output_dir: Katalog do zapisywania wyników
        results: Lista wyników testu walk-forward
    """
    
    def __init__(self, 
                strategy_class: type, 
                parameter_space: Dict[str, List[Any]],
                train_days: int = 60,
                test_days: int = 30, 
                step_days: int = 30,
                anchor_mode: str = "rolling",
                evaluation_metric: str = "net_profit",
                workers: int = None,
                output_dir: str = "walkforward_results"):
        """
        Inicjalizacja testera walk-forward.
        
        Args:
            strategy_class: Klasa strategii do testowania
            parameter_space: Słownik zawierający zakresy parametrów do przeszukania
            train_days: Liczba dni w okresie treningowym
            test_days: Liczba dni w okresie testowym
            step_days: Liczba dni przesunięcia okna
            anchor_mode: Tryb przesuwania okna ('rolling' lub 'anchored')
            evaluation_metric: Metryka używana do oceny wyników
            workers: Liczba równoległych procesów
            output_dir: Katalog do zapisywania wyników
        """
        self.strategy_class = strategy_class
        self.parameter_space = parameter_space
        self.train_days = train_days
        self.test_days = test_days
        self.step_days = step_days
        self.anchor_mode = anchor_mode.lower()
        self.evaluation_metric = evaluation_metric
        self.workers = workers
        self.output_dir = output_dir
        self.results = []
        
        # Walidacja parametrów
        if self.anchor_mode not in ["rolling", "anchored"]:
            logger.warning(f"Nieznany tryb przesuwania okna: {anchor_mode}. Używanie 'rolling'.")
            self.anchor_mode = "rolling"
        
        # Utwórz katalog wynikowy, jeśli nie istnieje
        Path(self.output_dir).mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Inicjalizacja WalkForwardTester dla {strategy_class.__name__}")
        logger.info(f"Okres treningowy: {train_days} dni, okres testowy: {test_days} dni")
        logger.info(f"Krok przesunięcia: {step_days} dni, tryb: {self.anchor_mode}")
        logger.info(f"Przestrzeń parametrów: {parameter_space}")
        logger.info(f"Metryka oceny: {evaluation_metric}")
    
    def run(self, 
           symbol: str, 
           timeframe: str, 
           start_date: datetime, 
           end_date: datetime,
           initial_balance: float = 10000.0,
           position_size_pct: float = 1.0,
           commission: float = 0.0001,
           use_cache: bool = True) -> List[Dict[str, Any]]:
        """
        Przeprowadza test walk-forward dla strategii.
        
        Args:
            symbol: Symbol instrumentu
            timeframe: Timeframe danych
            start_date: Data początkowa całego okresu
            end_date: Data końcowa całego okresu
            initial_balance: Początkowe saldo
            position_size_pct: Procent salda na pozycję
            commission: Prowizja w punktach
            use_cache: Czy używać cache dla danych historycznych
            
        Returns:
            Lista wyników testu walk-forward
        """
        logger.info(f"Rozpoczęcie walk-forward testingu dla {symbol} {timeframe} od {start_date} do {end_date}")
        
        # Sprawdź czy okres jest wystarczająco długi
        min_required_days = self.train_days + self.test_days
        if (end_date - start_date).days < min_required_days:
            logger.error(f"Za krótki okres: {(end_date - start_date).days} dni. "
                        f"Wymagane minimum: {min_required_days} dni.")
            return []
        
        # Reset wyników
        self.results = []
        start_time = time.time()
        
        # Przygotuj optymalizator parametrów
        optimizer = ParameterOptimizer(
            strategy_class=self.strategy_class,
            parameter_space=self.parameter_space,
            evaluation_metric=self.evaluation_metric,
            workers=self.workers,
            output_dir=os.path.join(self.output_dir, "optimizations")
        )
        
        # Ustal pierwszy okres treningowy
        current_date = start_date
        anchor_date = start_date  # Punkt zakotwiczenia dla trybu 'anchored'
        window_number = 1
        
        while current_date + timedelta(days=self.train_days + self.test_days) <= end_date:
            # Ustal okresy treningowe i testowe
            if self.anchor_mode == "anchored":
                # W trybie "anchored" początek okresu treningowego jest zawsze ten sam
                train_start = anchor_date
            else:
                # W trybie "rolling" przesuwamy całe okno
                train_start = current_date
                
            train_end = train_start + timedelta(days=self.train_days)
            test_start = train_end
            test_end = test_start + timedelta(days=self.test_days)
            
            logger.info(f"Okno {window_number}: Trening {train_start} - {train_end}, Test {test_start} - {test_end}")
            
            try:
                # Optymalizacja na danych treningowych
                logger.info(f"Rozpoczęcie optymalizacji dla okna {window_number}...")
                optimization_results = optimizer.grid_search(
                    symbol=symbol,
                    timeframe=timeframe,
                    start_date=train_start,
                    end_date=train_end,
                    initial_balance=initial_balance,
                    position_size_pct=position_size_pct,
                    commission=commission,
                    use_cache=use_cache
                )
                
                if not optimization_results:
                    logger.warning(f"Brak wyników optymalizacji dla okna {window_number}. Pomijanie.")
                    current_date += timedelta(days=self.step_days)
                    window_number += 1
                    continue
                
                # Wybierz najlepszy zestaw parametrów
                best_params = optimization_results[0]['params']
                
                logger.info(f"Najlepsze parametry dla okna {window_number}: {best_params}")
                
                # Test na danych testowych z najlepszymi parametrami
                strategy_config = StrategyConfig(
                    stop_loss_pips=best_params.get('stop_loss_pips', 50),
                    take_profit_pips=best_params.get('take_profit_pips', 100),
                    position_size_pct=position_size_pct,
                    params=best_params
                )
                
                strategy = self.strategy_class(config=strategy_config)
                
                backtest_config = BacktestConfig(
                    symbol=symbol,
                    timeframe=timeframe,
                    start_date=test_start,
                    end_date=test_end,
                    initial_balance=initial_balance,
                    position_size_pct=position_size_pct,
                    commission=commission,
                    use_cache=use_cache,
                    update_cache=False,
                    strategy_name=f"WF_{window_number}_{self.strategy_class.__name__}"
                )
                
                # Uruchom backtest na okresie testowym
                logger.info(f"Rozpoczęcie backtestingu na okresie testowym dla okna {window_number}...")
                engine = BacktestEngine(config=backtest_config, strategy=strategy)
                result = engine.run()
                
                # Jeśli backtest zakończył się sukcesem
                if result and hasattr(result, 'metrics') and result.metrics:
                    # Zapisz wyniki testu
                    window_result = {
                        'window': window_number,
                        'train_period': (train_start, train_end),
                        'test_period': (test_start, test_end),
                        'best_params': best_params,
                        'train_metric': optimization_results[0]['metrics'][self.evaluation_metric],
                        'test_metrics': {
                            'net_profit': result.metrics['net_profit'],
                            'net_profit_percent': result.metrics['net_profit_percent'],
                            'win_rate': result.metrics['win_rate'],
                            'profit_factor': result.metrics['profit_factor'],
                            'max_drawdown_pct': result.metrics['max_drawdown_pct'],
                            'total_trades': result.metrics['total_trades']
                        },
                        'equity_curve': result.equity_curve,
                        'trades': [
                            {
                                'entry_time': trade.entry_time.isoformat() if hasattr(trade, 'entry_time') else None,
                                'exit_time': trade.exit_time.isoformat() if hasattr(trade, 'exit_time') else None,
                                'direction': trade.direction,
                                'profit': trade.profit,
                                'pips': trade.pips,
                                'status': trade.status
                            }
                            for trade in result.trades
                        ]
                    }
                    
                    self.results.append(window_result)
                    logger.info(f"Wyniki dla okna {window_number}: "
                               f"Zysk: {result.metrics['net_profit']:.2f}, "
                               f"Win rate: {result.metrics['win_rate']*100:.2f}%")
                else:
                    logger.warning(f"Backtest dla okna {window_number} nie zwrócił ważnych wyników")
                
            except Exception as e:
                logger.error(f"Błąd podczas walk-forward testingu dla okna {window_number}: {e}")
                import traceback
                logger.error(traceback.format_exc())
            
            # Przesuń okno
            current_date += timedelta(days=self.step_days)
            window_number += 1
        
        # Po zakończeniu wszystkich okien
        if self.results:
            # Zapisz wyniki
            self._save_results(symbol, timeframe)
            
            # Wygeneruj raport
            self.generate_report(symbol, timeframe)
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        logger.info(f"Walk-forward testing zakończony. Przetestowano {len(self.results)} okien.")
        logger.info(f"Czas wykonania: {timedelta(seconds=int(execution_time))}")
        
        return self.results
    
    def _save_results(self, symbol: str, timeframe: str) -> str:
        """
        Zapisuje wyniki testu walk-forward do pliku.
        
        Args:
            symbol: Symbol instrumentu
            timeframe: Timeframe danych
            
        Returns:
            Ścieżka do zapisanego pliku
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"wf_{self.strategy_class.__name__}_{symbol}_{timeframe}_{timestamp}.json"
        filepath = os.path.join(self.output_dir, filename)
        
        # Przygotuj dane do zapisu
        results_to_save = {
            'strategy': self.strategy_class.__name__,
            'symbol': symbol,
            'timeframe': timeframe,
            'train_days': self.train_days,
            'test_days': self.test_days,
            'step_days': self.step_days,
            'anchor_mode': self.anchor_mode,
            'evaluation_metric': self.evaluation_metric,
            'timestamp': timestamp,
            'parameter_space': self.parameter_space,
            'results': self.results
        }
        
        # Zapisz do pliku JSON
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(results_to_save, f, indent=2, default=str)
        
        logger.info(f"Wyniki walk-forward testingu zapisane do: {filepath}")
        return filepath
    
    def load_results(self, filepath: str) -> bool:
        """
        Ładuje wyniki testu walk-forward z pliku.
        
        Args:
            filepath: Ścieżka do pliku z wynikami
            
        Returns:
            True jeśli załadowano pomyślnie, False w przeciwnym razie
        """
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Zaktualizuj atrybuty klasy
            self.strategy_class = data.get('strategy')
            self.train_days = data.get('train_days', self.train_days)
            self.test_days = data.get('test_days', self.test_days)
            self.step_days = data.get('step_days', self.step_days)
            self.anchor_mode = data.get('anchor_mode', self.anchor_mode)
            self.evaluation_metric = data.get('evaluation_metric', self.evaluation_metric)
            self.parameter_space = data.get('parameter_space', self.parameter_space)
            self.results = data.get('results', [])
            
            logger.info(f"Załadowano wyniki walk-forward testingu z: {filepath}")
            return True
        except Exception as e:
            logger.error(f"Błąd podczas ładowania wyników walk-forward testingu: {e}")
            return False
    
    def generate_report(self, symbol: str, timeframe: str) -> str:
        """
        Generuje raport z wynikami testu walk-forward.
        
        Args:
            symbol: Symbol instrumentu
            timeframe: Timeframe danych
            
        Returns:
            Ścieżka do wygenerowanego raportu
        """
        if not self.results:
            logger.warning("Brak wyników testu walk-forward do wygenerowania raportu")
            return ""
        
        try:
            # Konfiguracja wykresu
            plt.style.use('seaborn-darkgrid')
            fig = plt.figure(figsize=(15, 12))
            gs = GridSpec(4, 2, figure=fig)
            
            # Tytuł
            strategy_name = self.strategy_class.__name__ if isinstance(self.strategy_class, type) else self.strategy_class
            plt.suptitle(f"Raport Walk-Forward Testingu: {strategy_name} na {symbol} {timeframe}", fontsize=16)
            
            # 1. Wykres krzywej kapitału dla wszystkich okien
            ax1 = fig.add_subplot(gs[0, :])
            
            # Połączona krzywa kapitału
            all_equity = []
            for result in self.results:
                if result.get('equity_curve'):
                    all_equity.extend(result['equity_curve'])
            
            if all_equity:
                ax1.plot(list(range(len(all_equity))), all_equity)
                ax1.set_title("Połączona krzywa kapitału (wszystkie okna testowe)")
                ax1.set_xlabel("Liczba transakcji")
                ax1.set_ylabel("Kapitał")
                ax1.grid(True)
            
            # 2. Porównanie metryk treningowych i testowych
            ax2 = fig.add_subplot(gs[1, 0])
            
            window_numbers = [result['window'] for result in self.results]
            train_metrics = [result['train_metric'] for result in self.results]
            test_metrics = [result['test_metrics'].get('net_profit_percent', 0) for result in self.results]
            
            bar_width = 0.35
            x = range(len(window_numbers))
            
            ax2.bar([i - bar_width/2 for i in x], train_metrics, bar_width, label='Trening')
            ax2.bar([i + bar_width/2 for i in x], test_metrics, bar_width, label='Test')
            
            ax2.set_title(f"Porównanie wydajności ({self.evaluation_metric})")
            ax2.set_xlabel("Numer okna")
            ax2.set_ylabel("Wartość metryki")
            ax2.set_xticks(x)
            ax2.set_xticklabels(window_numbers)
            ax2.legend()
            ax2.grid(True)
            
            # 3. Win rate dla każdego okna
            ax3 = fig.add_subplot(gs[1, 1])
            
            win_rates = [result['test_metrics'].get('win_rate', 0) * 100 for result in self.results]
            
            ax3.bar(x, win_rates, color='green', alpha=0.7)
            ax3.set_title("Win Rate dla każdego okna testowego")
            ax3.set_xlabel("Numer okna")
            ax3.set_ylabel("Win Rate (%)")
            ax3.set_xticks(x)
            ax3.set_xticklabels(window_numbers)
            ax3.grid(True)
            
            # 4. Ewolucja parametrów w czasie
            ax4 = fig.add_subplot(gs[2, :])
            
            # Wybierz kilka najważniejszych parametrów do pokazania
            if self.results and 'best_params' in self.results[0]:
                param_keys = list(self.results[0]['best_params'].keys())
                selected_params = param_keys[:min(len(param_keys), 4)]  # Pokaż maksymalnie 4 parametry
                
                for param in selected_params:
                    param_values = [result['best_params'].get(param, 0) for result in self.results]
                    ax4.plot(window_numbers, param_values, 'o-', label=param)
                
                ax4.set_title("Ewolucja parametrów")
                ax4.set_xlabel("Numer okna")
                ax4.set_ylabel("Wartości parametrów")
                ax4.legend()
                ax4.grid(True)
            
            # 5. Statystyki zbiorcze
            ax5 = fig.add_subplot(gs[3, :])
            ax5.axis('off')
            
            # Oblicz statystyki zbiorcze
            total_trades = sum(result['test_metrics'].get('total_trades', 0) for result in self.results)
            avg_win_rate = sum(result['test_metrics'].get('win_rate', 0) * result['test_metrics'].get('total_trades', 0) 
                             for result in self.results) / max(total_trades, 1) * 100
            total_profit = sum(result['test_metrics'].get('net_profit', 0) for result in self.results)
            total_profit_percent = sum(result['test_metrics'].get('net_profit_percent', 0) for result in self.results)
            avg_drawdown = sum(result['test_metrics'].get('max_drawdown_pct', 0) for result in self.results) / max(len(self.results), 1)
            
            # In-sample vs. Out-of-sample performance
            train_avg = sum(result['train_metric'] for result in self.results) / len(self.results)
            test_avg = sum(result['test_metrics'].get('net_profit_percent', 0) for result in self.results) / len(self.results)
            overfitting_ratio = abs(train_avg / max(test_avg, 0.0001))
            
            summary_text = (
                f"PODSUMOWANIE WALK-FORWARD TESTINGU\n\n"
                f"Liczba okien testowych: {len(self.results)}\n"
                f"Całkowita liczba transakcji: {total_trades}\n"
                f"Średni Win Rate: {avg_win_rate:.2f}%\n"
                f"Całkowity zysk: {total_profit:.2f} ({total_profit_percent:.2f}%)\n"
                f"Średni maksymalny drawdown: {avg_drawdown:.2f}%\n\n"
                f"Średnia wydajność na treningowych: {train_avg:.2f}\n"
                f"Średnia wydajność na testowych: {test_avg:.2f}\n"
                f"Współczynnik przetrenowania: {overfitting_ratio:.2f}\n"
            )
            
            ax5.text(0.5, 0.5, summary_text, horizontalalignment='center', verticalalignment='center', 
                   transform=ax5.transAxes, fontsize=12)
            
            # Zapisz raport
            plt.tight_layout(rect=[0, 0, 1, 0.97])
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            report_path = os.path.join(self.output_dir, 
                                     f"wf_report_{self.strategy_class.__name__}_{symbol}_{timeframe}_{timestamp}.png")
            
            plt.savefig(report_path, dpi=150)
            plt.close()
            
            logger.info(f"Raport walk-forward testingu zapisany do: {report_path}")
            return report_path
            
        except Exception as e:
            logger.error(f"Błąd podczas generowania raportu walk-forward testingu: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return ""


# Funkcja pomocnicza do walk-forward testingu
def run_walk_forward_test(strategy_class: type,
                         parameter_space: Dict[str, List[Any]],
                         symbol: str,
                         timeframe: str,
                         start_date: datetime,
                         end_date: datetime,
                         train_days: int = 60,
                         test_days: int = 30,
                         step_days: int = 30,
                         anchor_mode: str = "rolling",
                         evaluation_metric: str = "net_profit",
                         workers: int = None) -> List[Dict[str, Any]]:
    """
    Funkcja pomocnicza do szybkiego przeprowadzenia testu walk-forward.
    
    Args:
        strategy_class: Klasa strategii do testowania
        parameter_space: Słownik zawierający zakresy parametrów do przeszukania
        symbol: Symbol instrumentu
        timeframe: Timeframe danych
        start_date: Data początkowa całego okresu
        end_date: Data końcowa całego okresu
        train_days: Liczba dni w okresie treningowym
        test_days: Liczba dni w okresie testowym
        step_days: Liczba dni przesunięcia okna
        anchor_mode: Tryb przesuwania okna ('rolling' lub 'anchored')
        evaluation_metric: Metryka używana do oceny wyników
        workers: Liczba równoległych procesów
        
    Returns:
        Lista wyników testu walk-forward
    """
    tester = WalkForwardTester(
        strategy_class=strategy_class,
        parameter_space=parameter_space,
        train_days=train_days,
        test_days=test_days,
        step_days=step_days,
        anchor_mode=anchor_mode,
        evaluation_metric=evaluation_metric,
        workers=workers
    )
    
    return tester.run(
        symbol=symbol,
        timeframe=timeframe,
        start_date=start_date,
        end_date=end_date
    ) 