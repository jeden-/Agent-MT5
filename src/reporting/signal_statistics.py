#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
SignalStatistics - klasa odpowiedzialna za zbieranie i analizowanie statystyk 
dotyczących sygnałów handlowych w systemie AgentMT5.
"""

import logging
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple, Union
import pandas as pd
import numpy as np
from enum import Enum

from src.database.signal_evaluation_repository import get_signal_evaluation_repository
from src.database.signal_repository import get_signal_repository
from src.database.models import TradingSignal, SignalEvaluation

logger = logging.getLogger(__name__)

class TimeFrame(Enum):
    """Przedziały czasowe dla statystyk."""
    DAY = "day"
    WEEK = "week"
    MONTH = "month"
    QUARTER = "quarter"
    YEAR = "year"
    ALL = "all"

class SignalOutcome(Enum):
    """Możliwe wyniki sygnału."""
    SUCCESS = "success"  # Sygnał osiągnął take_profit
    FAILURE = "failure"  # Sygnał osiągnął stop_loss
    PARTIAL = "partial"  # Sygnał zamknięty manualnie z zyskiem
    LOSS = "loss"       # Sygnał zamknięty manualnie ze stratą
    EXPIRED = "expired"  # Sygnał wygasł bez realizacji
    PENDING = "pending"  # Sygnał oczekuje na realizację

class SignalStatistics:
    """
    Klasa do zbierania i analizowania statystyk dotyczących sygnałów handlowych.
    """
    
    _instance = None
    _lock = threading.Lock()
    
    @classmethod
    def get_instance(cls) -> 'SignalStatistics':
        """
        Pobiera instancję klasy (singleton).
        
        Returns:
            SignalStatistics: Instancja klasy SignalStatistics
        """
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance
    
    def __init__(self):
        """
        Inicjalizuje obiekt statystyk sygnałów.
        """
        self.signal_repository = get_signal_repository()
        self.evaluation_repository = get_signal_evaluation_repository()
        self.logger = logging.getLogger(__name__)
        
        # Cache dla statystyk
        self.statistics_cache = {}
        self.cache_timestamp = {}
        self.cache_valid_time = 300  # 5 minut ważności cache
    
    def get_signal_success_rate(self, 
                               symbol: Optional[str] = None, 
                               timeframe: Optional[str] = None,
                               start_date: Optional[datetime] = None,
                               end_date: Optional[datetime] = None) -> float:
        """
        Oblicza procentowy wskaźnik skuteczności sygnałów.
        
        Args:
            symbol: Symbol instrumentu (opcjonalnie)
            timeframe: Rama czasowa (opcjonalnie)
            start_date: Data początkowa (opcjonalnie)
            end_date: Data końcowa (opcjonalnie)
            
        Returns:
            float: Procentowy wskaźnik skuteczności (0-100)
        """
        stats = self.get_signal_statistics(symbol, timeframe, start_date, end_date)
        
        total_completed = stats.get('total_completed', 0)
        if total_completed == 0:
            return 0.0
            
        successes = stats.get('total_success', 0) + stats.get('total_partial', 0)
        return (successes / total_completed) * 100
    
    def get_signal_statistics(self,
                             symbol: Optional[str] = None,
                             timeframe: Optional[str] = None,
                             start_date: Optional[datetime] = None,
                             end_date: Optional[datetime] = None) -> Dict[str, Any]:
        """
        Pobiera statystyki sygnałów.
        
        Args:
            symbol: Symbol instrumentu (opcjonalnie)
            timeframe: Rama czasowa (opcjonalnie)
            start_date: Data początkowa (opcjonalnie)
            end_date: Data końcowa (opcjonalnie)
            
        Returns:
            Dict[str, Any]: Słownik statystyk sygnałów
        """
        # Sprawdzenie, czy dane są w cache
        cache_key = f"{symbol}_{timeframe}_{start_date}_{end_date}"
        if cache_key in self.statistics_cache:
            if datetime.now().timestamp() - self.cache_timestamp.get(cache_key, 0) < self.cache_valid_time:
                self.logger.debug(f"Używam cache dla statystyk: {cache_key}")
                return self.statistics_cache[cache_key]
        
        # Pobranie ewaluacji sygnałów
        evaluations = self.evaluation_repository.get_evaluations_by_date_range(start_date, end_date)
        
        # Filtrowanie po symbolu i timeframe
        if symbol:
            evaluations = [e for e in evaluations if e['symbol'] == symbol]
        if timeframe:
            evaluations = [e for e in evaluations if e['timeframe'] == timeframe]
        
        # Inicjalizacja statystyk
        stats = {
            'total_signals': len(evaluations),
            'total_completed': 0,
            'total_pending': 0,
            'total_success': 0,
            'total_failure': 0,
            'total_partial': 0,
            'total_loss': 0,
            'total_expired': 0,
            'avg_profit': 0.0,
            'avg_loss': 0.0,
            'profit_loss_ratio': 0.0,
            'max_profit': 0.0,
            'max_loss': 0.0,
            'avg_time_to_profit': 0.0,
            'avg_time_to_loss': 0.0,
            'avg_risk_reward': 0.0,
            'buy_signals': 0,
            'sell_signals': 0,
            'buy_success_rate': 0.0,
            'sell_success_rate': 0.0,
            'most_successful_symbol': None,
            'most_successful_timeframe': None,
            'most_successful_signal_details': None,
            'symbols_data': {},
            'timeframes_data': {},
            'confidence_performance': {}
        }
        
        # Jeśli brak sygnałów, zwróć puste statystyki
        if not evaluations:
            self.statistics_cache[cache_key] = stats
            self.cache_timestamp[cache_key] = datetime.now().timestamp()
            return stats
        
        # Zliczenia i sumy
        total_profit = 0.0
        total_loss = 0.0
        profitable_signals = []
        loss_signals = []
        total_time_to_profit = 0
        total_time_to_loss = 0
        profits_by_symbol = {}
        profits_by_timeframe = {}
        buy_success = 0
        buy_total = 0
        sell_success = 0
        sell_total = 0
        confidence_bins = {}
        
        # Przetwarzanie ewaluacji
        for eval_data in evaluations:
            symbol = eval_data.get('symbol', '')
            tf = eval_data.get('timeframe', '')
            direction = eval_data.get('direction', '')
            status = eval_data.get('evaluation_status', '')
            confidence = eval_data.get('confidence', 0.0)
            
            # Inicjalizacja danych dla symbolu i timeframe
            if symbol not in stats['symbols_data']:
                stats['symbols_data'][symbol] = {'total': 0, 'success': 0, 'failure': 0, 'profit': 0.0, 'loss': 0.0}
            if tf not in stats['timeframes_data']:
                stats['timeframes_data'][tf] = {'total': 0, 'success': 0, 'failure': 0, 'profit': 0.0, 'loss': 0.0}
            
            # Zwiększenie liczników dla kierunku
            if direction == 'BUY':
                stats['buy_signals'] += 1
                buy_total += 1
            elif direction == 'SELL':
                stats['sell_signals'] += 1
                sell_total += 1
            
            # Zwiększenie liczników dla symbolu i timeframe
            stats['symbols_data'][symbol]['total'] += 1
            stats['timeframes_data'][tf]['total'] += 1
            
            # Grupowanie wg. przedziałów pewności
            confidence_bin = int(confidence * 10) / 10
            if confidence_bin not in confidence_bins:
                confidence_bins[confidence_bin] = {'total': 0, 'success': 0, 'failure': 0}
            confidence_bins[confidence_bin]['total'] += 1
            
            # Analiza statusu
            if status == 'closed':
                stats['total_completed'] += 1
                
                hit_target = eval_data.get('hit_target', False)
                hit_stop = eval_data.get('hit_stop', False)
                actual_profit = eval_data.get('actual_profit', 0.0)
                actual_loss = eval_data.get('actual_loss', 0.0)
                time_to_target = eval_data.get('time_to_target', 0)
                time_to_stop = eval_data.get('time_to_stop', 0)
                
                if hit_target:
                    stats['total_success'] += 1
                    total_profit += actual_profit
                    profitable_signals.append(actual_profit)
                    total_time_to_profit += time_to_target
                    
                    if direction == 'BUY':
                        buy_success += 1
                    elif direction == 'SELL':
                        sell_success += 1
                    
                    stats['symbols_data'][symbol]['success'] += 1
                    stats['symbols_data'][symbol]['profit'] += actual_profit
                    stats['timeframes_data'][tf]['success'] += 1
                    stats['timeframes_data'][tf]['profit'] += actual_profit
                    confidence_bins[confidence_bin]['success'] += 1
                    
                    if actual_profit > stats['max_profit']:
                        stats['max_profit'] = actual_profit
                        stats['most_successful_signal_details'] = eval_data
                
                elif hit_stop:
                    stats['total_failure'] += 1
                    total_loss += actual_loss
                    loss_signals.append(actual_loss)
                    total_time_to_loss += time_to_stop
                    
                    stats['symbols_data'][symbol]['failure'] += 1
                    stats['symbols_data'][symbol]['loss'] += actual_loss
                    stats['timeframes_data'][tf]['failure'] += 1
                    stats['timeframes_data'][tf]['loss'] += actual_loss
                    confidence_bins[confidence_bin]['failure'] += 1
                    
                    if actual_loss > stats['max_loss']:
                        stats['max_loss'] = actual_loss
                
                elif actual_profit > 0:
                    stats['total_partial'] += 1
                    total_profit += actual_profit
                    profitable_signals.append(actual_profit)
                    
                    stats['symbols_data'][symbol]['success'] += 1
                    stats['symbols_data'][symbol]['profit'] += actual_profit
                    stats['timeframes_data'][tf]['success'] += 1
                    stats['timeframes_data'][tf]['profit'] += actual_profit
                    confidence_bins[confidence_bin]['success'] += 1
                
                elif actual_loss > 0:
                    stats['total_loss'] += 1
                    total_loss += actual_loss
                    loss_signals.append(actual_loss)
                    
                    stats['symbols_data'][symbol]['failure'] += 1
                    stats['symbols_data'][symbol]['loss'] += actual_loss
                    stats['timeframes_data'][tf]['failure'] += 1
                    stats['timeframes_data'][tf]['loss'] += actual_loss
                    confidence_bins[confidence_bin]['failure'] += 1
            
            elif status == 'expired':
                stats['total_expired'] += 1
                stats['total_completed'] += 1
            
            elif status == 'open':
                stats['total_pending'] += 1
        
        # Obliczanie statystyk
        if profitable_signals:
            stats['avg_profit'] = total_profit / len(profitable_signals)
        if loss_signals:
            stats['avg_loss'] = total_loss / len(loss_signals)
        if stats['avg_loss'] > 0:
            stats['profit_loss_ratio'] = stats['avg_profit'] / stats['avg_loss'] if stats['avg_loss'] > 0 else 0
        
        if stats['total_success'] > 0:
            stats['avg_time_to_profit'] = total_time_to_profit / stats['total_success']
        if stats['total_failure'] > 0:
            stats['avg_time_to_loss'] = total_time_to_loss / stats['total_failure']
        
        # Obliczanie średniego stosunku zysku do ryzyka
        risk_reward_sum = 0.0
        for eval_data in evaluations:
            risk_reward = eval_data.get('risk_reward_ratio', 0.0)
            if risk_reward > 0:
                risk_reward_sum += risk_reward
        stats['avg_risk_reward'] = risk_reward_sum / len(evaluations) if evaluations else 0.0
        
        # Obliczanie skuteczności według kierunku
        stats['buy_success_rate'] = (buy_success / buy_total) * 100 if buy_total > 0 else 0
        stats['sell_success_rate'] = (sell_success / sell_total) * 100 if sell_total > 0 else 0
        
        # Znalezienie najbardziej udanego symbolu i timeframe
        best_symbol = None
        best_symbol_rate = 0
        for sym, data in stats['symbols_data'].items():
            if data['total'] > 0:
                success_rate = (data['success'] / data['total']) * 100
                if success_rate > best_symbol_rate:
                    best_symbol_rate = success_rate
                    best_symbol = sym
        stats['most_successful_symbol'] = best_symbol
        
        best_tf = None
        best_tf_rate = 0
        for tf, data in stats['timeframes_data'].items():
            if data['total'] > 0:
                success_rate = (data['success'] / data['total']) * 100
                if success_rate > best_tf_rate:
                    best_tf_rate = success_rate
                    best_tf = tf
        stats['most_successful_timeframe'] = best_tf
        
        # Konwersja danych o pewności
        for conf, data in confidence_bins.items():
            success_rate = (data['success'] / data['total']) * 100 if data['total'] > 0 else 0
            stats['confidence_performance'][conf] = {
                'total': data['total'],
                'success': data['success'],
                'failure': data['failure'],
                'success_rate': success_rate
            }
        
        # Zapisanie do cache
        self.statistics_cache[cache_key] = stats
        self.cache_timestamp[cache_key] = datetime.now().timestamp()
        
        return stats
    
    def get_signals_by_timeframe(self, timeframe: TimeFrame = TimeFrame.WEEK) -> List[Dict[str, Any]]:
        """
        Pobiera sygnały z określonego przedziału czasowego.
        
        Args:
            timeframe: Przedział czasowy
            
        Returns:
            List[Dict[str, Any]]: Lista sygnałów
        """
        # Określenie dat na podstawie timeframe
        end_date = datetime.now()
        if timeframe == TimeFrame.DAY:
            start_date = end_date - timedelta(days=1)
        elif timeframe == TimeFrame.WEEK:
            start_date = end_date - timedelta(days=7)
        elif timeframe == TimeFrame.MONTH:
            start_date = end_date - timedelta(days=30)
        elif timeframe == TimeFrame.QUARTER:
            start_date = end_date - timedelta(days=90)
        elif timeframe == TimeFrame.YEAR:
            start_date = end_date - timedelta(days=365)
        else:  # ALL
            start_date = None
        
        # Pobranie ewaluacji z repozytorium
        evaluations = self.evaluation_repository.get_evaluations_by_date_range(start_date, end_date)
        return evaluations
    
    def get_signal_outcome_distribution(self, 
                                      symbol: Optional[str] = None,
                                      timeframe: Optional[str] = None,
                                      start_date: Optional[datetime] = None,
                                      end_date: Optional[datetime] = None) -> Dict[str, float]:
        """
        Pobiera rozkład wyników sygnałów.
        
        Args:
            symbol: Symbol instrumentu (opcjonalnie)
            timeframe: Rama czasowa (opcjonalnie)
            start_date: Data początkowa (opcjonalnie)
            end_date: Data końcowa (opcjonalnie)
            
        Returns:
            Dict[str, float]: Rozkład wyników sygnałów (jako procenty)
        """
        stats = self.get_signal_statistics(symbol, timeframe, start_date, end_date)
        
        total = stats['total_completed']
        if total == 0:
            return {
                'success': 0.0,
                'failure': 0.0,
                'partial': 0.0,
                'loss': 0.0,
                'expired': 0.0
            }
        
        return {
            'success': (stats['total_success'] / total) * 100,
            'failure': (stats['total_failure'] / total) * 100,
            'partial': (stats['total_partial'] / total) * 100,
            'loss': (stats['total_loss'] / total) * 100,
            'expired': (stats['total_expired'] / total) * 100
        }
    
    def get_confidence_vs_performance(self,
                                    symbol: Optional[str] = None,
                                    timeframe: Optional[str] = None,
                                    start_date: Optional[datetime] = None,
                                    end_date: Optional[datetime] = None) -> Dict[float, float]:
        """
        Analizuje korelację między poziomem pewności sygnału a jego skutecznością.
        
        Args:
            symbol: Symbol instrumentu (opcjonalnie)
            timeframe: Rama czasowa (opcjonalnie)
            start_date: Data początkowa (opcjonalnie)
            end_date: Data końcowa (opcjonalnie)
            
        Returns:
            Dict[float, float]: Słownik, gdzie kluczem jest poziom pewności, a wartością procent sukcesu
        """
        stats = self.get_signal_statistics(symbol, timeframe, start_date, end_date)
        return {float(k): v['success_rate'] for k, v in stats['confidence_performance'].items()}
    
    def get_time_series_performance(self,
                                  symbol: Optional[str] = None,
                                  timeframe: Optional[str] = None,
                                  period: TimeFrame = TimeFrame.MONTH) -> Dict[str, List[Any]]:
        """
        Generuje szereg czasowy skuteczności sygnałów w okresie.
        
        Args:
            symbol: Symbol instrumentu (opcjonalnie)
            timeframe: Rama czasowa (opcjonalnie)
            period: Okres analizy
            
        Returns:
            Dict[str, List[Any]]: Dane szeregu czasowego
        """
        # Określenie przedziału czasowego
        end_date = datetime.now()
        if period == TimeFrame.WEEK:
            start_date = end_date - timedelta(days=7)
            interval = timedelta(days=1)
            format_str = "%Y-%m-%d"
        elif period == TimeFrame.MONTH:
            start_date = end_date - timedelta(days=30)
            interval = timedelta(days=1)
            format_str = "%Y-%m-%d"
        elif period == TimeFrame.QUARTER:
            start_date = end_date - timedelta(days=90)
            interval = timedelta(days=7)
            format_str = "%Y-%m-%d"
        elif period == TimeFrame.YEAR:
            start_date = end_date - timedelta(days=365)
            interval = timedelta(days=30)
            format_str = "%Y-%m"
        else:
            start_date = end_date - timedelta(days=7)
            interval = timedelta(days=1)
            format_str = "%Y-%m-%d"
        
        # Pobranie wszystkich ewaluacji
        evaluations = self.evaluation_repository.get_evaluations_by_date_range(start_date, end_date)
        
        # Filtrowanie po symbolu i timeframe
        if symbol:
            evaluations = [e for e in evaluations if e['symbol'] == symbol]
        if timeframe:
            evaluations = [e for e in evaluations if e['timeframe'] == timeframe]
        
        # Sortowanie po dacie
        evaluations.sort(key=lambda x: x.get('created_at', datetime.now()))
        
        # Konwersja do DataFrame dla łatwiejszej analizy czasowej
        if not evaluations:
            return {'dates': [], 'success_rates': [], 'total_signals': []}
        
        df = pd.DataFrame(evaluations)
        if 'created_at' not in df.columns:
            return {'dates': [], 'success_rates': [], 'total_signals': []}
        
        # Przekształcenie kolumny datetime na datę
        df['date'] = df['created_at'].dt.date
        
        # Grupowanie po datach
        grouped = df.groupby('date').apply(lambda x: {
            'total': len(x),
            'success': sum(1 for i, row in x.iterrows() if row.get('hit_target', False) or 
                          (row.get('actual_profit', 0) > 0 and not row.get('hit_stop', False))),
            'success_rate': sum(1 for i, row in x.iterrows() if row.get('hit_target', False) or 
                               (row.get('actual_profit', 0) > 0 and not row.get('hit_stop', False))) / len(x) * 100 if len(x) > 0 else 0
        }).reset_index()
        
        # Konwersja do list
        dates = [d.strftime(format_str) for d in grouped['date']]
        success_rates = [d['success_rate'] for d in grouped[0]]
        total_signals = [d['total'] for d in grouped[0]]
        
        return {
            'dates': dates,
            'success_rates': success_rates,
            'total_signals': total_signals
        }
    
    def clear_cache(self):
        """
        Czyści cache statystyk.
        """
        self.statistics_cache = {}
        self.cache_timestamp = {}
        self.logger.debug("Cache statystyk wyczyszczony")

# Singleton getter
def get_signal_statistics() -> SignalStatistics:
    """
    Pobiera instancję SignalStatistics.
    
    Returns:
        SignalStatistics: Instancja klasy SignalStatistics
    """
    return SignalStatistics.get_instance() 