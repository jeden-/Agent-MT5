#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Moduł mechanizmu uczenia się systemu (feedback loop).

Ten moduł zawiera funkcje i klasy do analizy historycznych decyzji handlowych,
ich wyników, oraz optymalizacji parametrów strategii handlowych na podstawie
zebranych danych.
"""

import os
import json
import logging
import threading
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Union, Tuple
from enum import Enum, auto

# Importy wewnętrzne
try:
    # Próbujemy importu z przedrostkiem src (dla testów z katalogu głównego)
    from src.analysis.signal_generator import SignalType, SignalStrength, SignalSource
    from src.analysis.signal_validator import ValidationResult
    from src.database.signal_repository import SignalRepository, get_signal_repository
    from src.database.trade_repository import TradeRepository, get_trade_repository
    from src.position_management.position_manager import PositionManager, get_position_manager
    from src.utils.config_manager import ConfigManager
except ImportError:
    # Próbujemy importu względnego (dla uruchamiania z katalogu src)
    from .signal_generator import SignalType, SignalStrength, SignalSource
    from .signal_validator import ValidationResult
    from ..database.signal_repository import SignalRepository, get_signal_repository
    from ..database.trade_repository import TradeRepository, get_trade_repository
    from ..position_management.position_manager import PositionManager, get_position_manager
    from ..utils.config_manager import ConfigManager

# Konfiguracja loggera
logger = logging.getLogger('trading_agent.analysis.feedback_loop')


class LearningStrategy(Enum):
    """Strategia uczenia się systemu."""
    BAYESIAN = auto()           # Optymalizacja bayesowska parametrów
    REINFORCEMENT = auto()      # Uczenie ze wzmocnieniem
    STATISTICAL = auto()        # Analiza statystyczna skuteczności
    ADAPTIVE = auto()           # Adaptacyjne dostosowanie parametrów
    HYBRID = auto()             # Podejście hybrydowe


class FeedbackLoop:
    """
    Klasa implementująca mechanizm uczenia się systemu na podstawie
    historycznych decyzji i ich wyników.
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        """Implementacja wzorca Singleton."""
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(FeedbackLoop, cls).__new__(cls)
                cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """Inicjalizacja mechanizmu feedback loop."""
        if self._initialized:
            return
            
        self.logger = logging.getLogger('trading_agent.analysis.feedback_loop')
        self.logger.info("Inicjalizacja FeedbackLoop")
        
        # Inicjalizacja zależności
        self.signal_repository = get_signal_repository()
        self.trade_repository = get_trade_repository()
        self.position_manager = get_position_manager()
        
        # Parametry konfiguracyjne
        self.config_manager = ConfigManager()
        self.config = self._load_config()
        
        # Statystyki i dane historyczne
        self.strategy_performance = {}
        self.signal_quality_metrics = {}
        self.model_performance = {}
        self.parameter_history = {}
        
        # Ostatnia optymalizacja
        self.last_optimization = datetime.now() - timedelta(days=1)
        self.optimization_interval = timedelta(hours=self.config.get('optimization_interval_hours', 4))
        
        self._initialized = True
    
    def _load_config(self) -> Dict[str, Any]:
        """
        Wczytuje konfigurację z pliku config.yaml.
        
        Returns:
            Dict zawierający konfigurację
        """
        try:
            config = self.config_manager.get_config_section('feedback_loop')
            if not config:
                self.logger.warning("Brak sekcji 'feedback_loop' w konfiguracji, używam wartości domyślnych")
                config = self._get_default_config()
            return config
        except Exception as e:
            self.logger.error(f"Błąd wczytywania konfiguracji: {str(e)}")
            return self._get_default_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """
        Zwraca domyślną konfigurację.
        
        Returns:
            Dict zawierający domyślną konfigurację
        """
        return {
            'learning_strategy': 'HYBRID',
            'optimization_interval_hours': 4,
            'min_data_points': 50,
            'performance_metrics': ['profit_factor', 'win_rate', 'avg_profit', 'max_drawdown'],
            'learning_rate': 0.05,
            'signal_history_days': 30,
            'weight_recent_trades': True,
            'recency_half_life_days': 5,
            'parameter_bounds': {
                'rsi_oversold': [20, 40],
                'rsi_overbought': [60, 80],
                'macd_signal_period': [5, 15],
                'bollinger_std': [1.5, 3.0],
                'risk_reward_min': [1.5, 3.0],
                'stop_loss_atr_multiplier': [1.0, 4.0]
            }
        }
    
    def analyze_performance(self, symbol: Optional[str] = None, 
                           days: int = 30) -> Dict[str, Any]:
        """
        Analizuje historyczną skuteczność sygnałów tradingowych dla danego symbolu.
        
        Args:
            symbol: Symbol instrumentu (jeśli None, analizuje wszystkie instrumenty)
            days: Liczba dni historii do analizy
            
        Returns:
            Dict zawierający metryki wydajności dla różnych strategii i źródeł sygnałów
        """
        self.logger.info(f"Analizuję historyczną skuteczność sygnałów dla {symbol or 'wszystkich symboli'}")
        
        # Pobierz historyczne sygnały i transakcje
        from_date = datetime.now() - timedelta(days=days)
        signals = self._get_historical_signals(symbol, from_date)
        trades = self._get_historical_trades(symbol, from_date)
        
        if not signals or not trades:
            self.logger.warning(f"Brak wystarczających danych historycznych dla {symbol or 'wszystkich symboli'}")
            return {}
        
        # Przekształć dane do postaci DataFrame
        signals_df = pd.DataFrame(signals)
        trades_df = pd.DataFrame(trades)
        
        # Połącz sygnały z transakcjami
        merged_data = self._merge_signals_with_trades(signals_df, trades_df)
        
        # Oblicz metryki wydajności dla różnych kategorii
        performance_metrics = self._calculate_performance_metrics(merged_data)
        
        # Zapisz wyniki do pamięci podręcznej
        if symbol:
            self.strategy_performance[symbol] = performance_metrics
        else:
            self.strategy_performance['all'] = performance_metrics
        
        return performance_metrics
    
    def _get_historical_signals(self, symbol: Optional[str], 
                               from_date: datetime) -> List[Dict[str, Any]]:
        """
        Pobiera historyczne sygnały tradingowe.
        
        Args:
            symbol: Symbol instrumentu (jeśli None, pobiera dla wszystkich instrumentów)
            from_date: Data, od której pobierać dane
            
        Returns:
            Lista sygnałów tradingowych
        """
        try:
            if symbol:
                return self.signal_repository.get_signals_by_symbol(symbol, from_date)
            else:
                return self.signal_repository.get_signals_after_date(from_date)
        except Exception as e:
            self.logger.error(f"Błąd pobierania historycznych sygnałów: {str(e)}")
            return []
    
    def _get_historical_trades(self, symbol: Optional[str], 
                              from_date: datetime) -> List[Dict[str, Any]]:
        """
        Pobiera historyczne transakcje.
        
        Args:
            symbol: Symbol instrumentu (jeśli None, pobiera dla wszystkich instrumentów)
            from_date: Data, od której pobierać dane
            
        Returns:
            Lista transakcji
        """
        try:
            if symbol:
                return self.trade_repository.get_trades_by_symbol(symbol, from_date)
            else:
                return self.trade_repository.get_trades_after_date(from_date)
        except Exception as e:
            self.logger.error(f"Błąd pobierania historycznych transakcji: {str(e)}")
            return []
    
    def _merge_signals_with_trades(self, signals_df: pd.DataFrame, 
                                  trades_df: pd.DataFrame) -> pd.DataFrame:
        """
        Łączy dane o sygnałach i transakcjach.
        
        Args:
            signals_df: DataFrame z sygnałami
            trades_df: DataFrame z transakcjami
            
        Returns:
            DataFrame z połączonymi danymi
        """
        # Implementacja połączenia danych
        # W rzeczywistej implementacji tutaj należałoby dopasować sygnały do powiązanych transakcji
        # na podstawie timestampów, symboli i typów sygnałów
        
        # Uproszczona implementacja na potrzeby prototypu
        merged_data = signals_df.copy()
        
        # Dodaj kolumny z informacjami o wyniku transakcji
        merged_data['profit'] = None
        merged_data['success'] = None
        
        # Dla każdego sygnału znajdź powiązaną transakcję
        for idx, signal in merged_data.iterrows():
            related_trades = trades_df[
                (trades_df['symbol'] == signal['symbol']) & 
                (trades_df['signal_id'] == signal['id'])
            ]
            
            if not related_trades.empty:
                # Jeśli znaleziono powiązane transakcje, zapisz wynik
                merged_data.at[idx, 'profit'] = related_trades['profit'].sum()
                merged_data.at[idx, 'success'] = related_trades['profit'].sum() > 0
        
        # Usuń wpisy bez powiązanych transakcji
        return merged_data.dropna(subset=['profit'])
    
    def _calculate_performance_metrics(self, data: pd.DataFrame) -> Dict[str, Any]:
        """
        Oblicza metryki wydajności dla różnych strategii i źródeł sygnałów.
        
        Args:
            data: DataFrame z połączonymi danymi o sygnałach i transakcjach
            
        Returns:
            Dict zawierający metryki wydajności
        """
        results = {
            'overall': self._calculate_metrics(data),
            'by_source': {},
            'by_strength': {},
            'by_model': {},
            'by_timeframe': {}
        }
        
        # Metryki według źródła sygnału
        for source in data['source'].unique():
            source_data = data[data['source'] == source]
            results['by_source'][source] = self._calculate_metrics(source_data)
        
        # Metryki według siły sygnału
        for strength in data['strength'].unique():
            strength_data = data[data['strength'] == strength]
            results['by_strength'][strength] = self._calculate_metrics(strength_data)
        
        # Metryki według modelu AI (jeśli dostępne)
        if 'ai_model' in data.columns:
            for model in data['ai_model'].unique():
                if pd.notna(model):
                    model_data = data[data['ai_model'] == model]
                    results['by_model'][model] = self._calculate_metrics(model_data)
        
        # Metryki według timeframe'u
        if 'timeframe' in data.columns:
            for timeframe in data['timeframe'].unique():
                tf_data = data[data['timeframe'] == timeframe]
                results['by_timeframe'][timeframe] = self._calculate_metrics(tf_data)
        
        return results
    
    def _calculate_metrics(self, data: pd.DataFrame) -> Dict[str, float]:
        """
        Oblicza podstawowe metryki wydajności.
        
        Args:
            data: DataFrame z danymi o transakcjach
            
        Returns:
            Dict zawierający metryki wydajności
        """
        if data.empty:
            return {
                'count': 0,
                'win_rate': 0.0,
                'profit_factor': 0.0,
                'avg_profit': 0.0,
                'total_profit': 0.0,
                'max_drawdown': 0.0
            }
        
        # Podstawowe metryki
        wins = data[data['profit'] > 0]
        losses = data[data['profit'] < 0]
        
        win_count = len(wins)
        loss_count = len(losses)
        total_count = len(data)
        
        win_rate = win_count / total_count if total_count > 0 else 0
        
        gross_profit = wins['profit'].sum() if not wins.empty else 0
        gross_loss = abs(losses['profit'].sum()) if not losses.empty else 0
        
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
        avg_profit = data['profit'].mean()
        total_profit = data['profit'].sum()
        
        # Obliczenie maksymalnej drawdown (spadku kapitału)
        cumulative = data['profit'].cumsum()
        max_drawdown = 0
        peak = 0
        
        for value in cumulative:
            if value > peak:
                peak = value
            drawdown = peak - value
            if drawdown > max_drawdown:
                max_drawdown = drawdown
        
        return {
            'count': total_count,
            'win_rate': win_rate,
            'profit_factor': profit_factor,
            'avg_profit': avg_profit,
            'total_profit': total_profit,
            'max_drawdown': max_drawdown
        }
    
    def optimize_parameters(self, symbol: Optional[str] = None) -> Dict[str, Any]:
        """
        Optymalizuje parametry strategii handlowych na podstawie historycznych danych.
        
        Args:
            symbol: Symbol instrumentu (jeśli None, optymalizuje dla wszystkich instrumentów)
            
        Returns:
            Dict zawierający zoptymalizowane parametry
        """
        self.logger.info(f"Optymalizuję parametry strategii dla {symbol or 'wszystkich symboli'}")
        
        # Sprawdź, czy minął odpowiedni czas od ostatniej optymalizacji
        current_time = datetime.now()
        if current_time - self.last_optimization < self.optimization_interval:
            self.logger.info("Zbyt wcześnie na kolejną optymalizację parametrów")
            return {}
        
        # Analizuj wydajność historyczną
        performance = self.analyze_performance(symbol, self.config.get('signal_history_days', 30))
        if not performance:
            self.logger.warning("Brak wystarczających danych do optymalizacji parametrów")
            return {}
        
        # Implementacja optymalizacji parametrów w zależności od wybranej strategii uczenia
        strategy = LearningStrategy[self.config.get('learning_strategy', 'HYBRID')]
        
        if strategy == LearningStrategy.BAYESIAN:
            optimized_params = self._optimize_bayesian(performance, symbol)
        elif strategy == LearningStrategy.REINFORCEMENT:
            optimized_params = self._optimize_reinforcement(performance, symbol)
        elif strategy == LearningStrategy.STATISTICAL:
            optimized_params = self._optimize_statistical(performance, symbol)
        elif strategy == LearningStrategy.ADAPTIVE:
            optimized_params = self._optimize_adaptive(performance, symbol)
        else:  # HYBRID
            optimized_params = self._optimize_hybrid(performance, symbol)
        
        # Zapisz datę ostatniej optymalizacji
        self.last_optimization = current_time
        
        # Zapisz historię parametrów
        if symbol not in self.parameter_history:
            self.parameter_history[symbol] = []
        
        self.parameter_history[symbol].append({
            'timestamp': current_time,
            'parameters': optimized_params,
            'performance': performance['overall']
        })
        
        return optimized_params
    
    def _optimize_bayesian(self, performance: Dict[str, Any], 
                          symbol: Optional[str]) -> Dict[str, Any]:
        """
        Optymalizacja bayesowska parametrów.
        
        Args:
            performance: Wyniki analizy wydajności
            symbol: Symbol instrumentu
            
        Returns:
            Dict zawierający zoptymalizowane parametry
        """
        self.logger.info("Używam optymalizacji bayesowskiej dla parametrów")
        
        # W rzeczywistej implementacji tutaj należałoby użyć biblioteki do optymalizacji bayesowskiej
        # np. skopt, bayesian-optimization lub podobnej
        
        # Uproszczona implementacja na potrzeby prototypu
        return {
            'rsi_oversold': 30,
            'rsi_overbought': 70,
            'macd_signal_period': 9,
            'bollinger_std': 2.0,
            'risk_reward_min': 2.0,
            'stop_loss_atr_multiplier': 2.0
        }
    
    def _optimize_reinforcement(self, performance: Dict[str, Any], 
                               symbol: Optional[str]) -> Dict[str, Any]:
        """
        Optymalizacja parametrów za pomocą uczenia ze wzmocnieniem.
        
        Args:
            performance: Wyniki analizy wydajności
            symbol: Symbol instrumentu
            
        Returns:
            Dict zawierający zoptymalizowane parametry
        """
        self.logger.info("Używam uczenia ze wzmocnieniem dla parametrów")
        
        # Uproszczona implementacja na potrzeby prototypu
        return {
            'rsi_oversold': 30,
            'rsi_overbought': 70,
            'macd_signal_period': 9,
            'bollinger_std': 2.0,
            'risk_reward_min': 2.0,
            'stop_loss_atr_multiplier': 2.0
        }
    
    def _optimize_statistical(self, performance: Dict[str, Any], 
                             symbol: Optional[str]) -> Dict[str, Any]:
        """
        Optymalizacja parametrów za pomocą analizy statystycznej.
        
        Args:
            performance: Wyniki analizy wydajności
            symbol: Symbol instrumentu
            
        Returns:
            Dict zawierający zoptymalizowane parametry
        """
        self.logger.info("Używam analizy statystycznej dla parametrów")
        
        # Uproszczona implementacja na potrzeby prototypu
        return {
            'rsi_oversold': 30,
            'rsi_overbought': 70,
            'macd_signal_period': 9,
            'bollinger_std': 2.0,
            'risk_reward_min': 2.0,
            'stop_loss_atr_multiplier': 2.0
        }
    
    def _optimize_adaptive(self, performance: Dict[str, Any], 
                          symbol: Optional[str]) -> Dict[str, Any]:
        """
        Adaptacyjna optymalizacja parametrów.
        
        Args:
            performance: Wyniki analizy wydajności
            symbol: Symbol instrumentu
            
        Returns:
            Dict zawierający zoptymalizowane parametry
        """
        self.logger.info("Używam adaptacyjnej optymalizacji parametrów")
        
        # Uproszczona implementacja na potrzeby prototypu
        return {
            'rsi_oversold': 30,
            'rsi_overbought': 70,
            'macd_signal_period': 9,
            'bollinger_std': 2.0,
            'risk_reward_min': 2.0,
            'stop_loss_atr_multiplier': 2.0
        }
    
    def _optimize_hybrid(self, performance: Dict[str, Any], 
                        symbol: Optional[str]) -> Dict[str, Any]:
        """
        Hybrydowa optymalizacja parametrów.
        
        Args:
            performance: Wyniki analizy wydajności
            symbol: Symbol instrumentu
            
        Returns:
            Dict zawierający zoptymalizowane parametry
        """
        self.logger.info("Używam hybrydowej optymalizacji parametrów")
        
        # Uproszczona implementacja na potrzeby prototypu
        return {
            'rsi_oversold': 30,
            'rsi_overbought': 70,
            'macd_signal_period': 9,
            'bollinger_std': 2.0,
            'risk_reward_min': 2.0,
            'stop_loss_atr_multiplier': 2.0
        }
    
    def get_signal_quality(self, signal: Dict[str, Any]) -> float:
        """
        Ocenia jakość sygnału tradingowego na podstawie historycznych danych.
        
        Args:
            signal: Sygnał tradingowy do oceny
            
        Returns:
            Wartość 0-1 określająca jakość sygnału
        """
        self.logger.debug(f"Oceniam jakość sygnału dla {signal.get('symbol')}")
        
        # Pobierz odpowiednie metryki wydajności
        symbol = signal.get('symbol')
        source = signal.get('source')
        strength = signal.get('strength')
        
        if symbol not in self.strategy_performance:
            # Jeśli nie mamy jeszcze danych dla tego symbolu, analizujemy je teraz
            self.analyze_performance(symbol)
        
        if symbol not in self.strategy_performance:
            # Jeśli nadal nie mamy danych, użyj ogólnych metryk
            performance = self.strategy_performance.get('all', {})
        else:
            performance = self.strategy_performance[symbol]
        
        # Pobierz odpowiednie metryki na podstawie źródła i siły sygnału
        source_metrics = performance.get('by_source', {}).get(source, {})
        strength_metrics = performance.get('by_strength', {}).get(strength, {})
        
        # Jeśli jest dostępny model AI, uwzględnij również jego metryki
        model_metrics = {}
        if 'ai_model' in signal and signal['ai_model']:
            model = signal['ai_model']
            model_metrics = performance.get('by_model', {}).get(model, {})
        
        # Połącz metryki z różnych źródeł, nadając im wagi
        win_rate = self._weighted_average([
            (performance.get('overall', {}).get('win_rate', 0.5), 0.4),
            (source_metrics.get('win_rate', 0.5), 0.3),
            (strength_metrics.get('win_rate', 0.5), 0.2),
            (model_metrics.get('win_rate', 0.5), 0.1)
        ])
        
        profit_factor = self._weighted_average([
            (performance.get('overall', {}).get('profit_factor', 1.0), 0.4),
            (source_metrics.get('profit_factor', 1.0), 0.3),
            (strength_metrics.get('profit_factor', 1.0), 0.2),
            (model_metrics.get('profit_factor', 1.0), 0.1)
        ])
        
        # Uwzględnij aktualne warunki rynkowe
        market_condition_factor = self._evaluate_market_conditions(signal)
        
        # Oblicz końcowy wynik jakości
        quality = (win_rate * 0.4 + min(profit_factor / 3, 1.0) * 0.4 + market_condition_factor * 0.2)
        
        # Normalizuj do zakresu 0-1
        return max(0.0, min(1.0, quality))
    
    def _weighted_average(self, value_weight_pairs: List[Tuple[float, float]]) -> float:
        """
        Oblicza średnią ważoną.
        
        Args:
            value_weight_pairs: Lista par (wartość, waga)
            
        Returns:
            Średnia ważona
        """
        total_weight = sum(weight for _, weight in value_weight_pairs)
        if total_weight == 0:
            return 0
        
        weighted_sum = sum(value * weight for value, weight in value_weight_pairs)
        return weighted_sum / total_weight
    
    def _evaluate_market_conditions(self, signal: Dict[str, Any]) -> float:
        """
        Ocenia aktualne warunki rynkowe dla danego sygnału.
        
        Args:
            signal: Sygnał tradingowy
            
        Returns:
            Wartość 0-1 określająca sprzyjające warunki rynkowe
        """
        # W rzeczywistej implementacji tutaj należałoby analizować aktualne
        # warunki rynkowe, trendy, zmienność, korelacje itp.
        
        # Uproszczona implementacja na potrzeby prototypu
        return 0.7
    
    def update_model_weights(self) -> Dict[str, float]:
        """
        Aktualizuje wagi modeli AI na podstawie ich historycznej wydajności.
        
        Returns:
            Dict zawierający zaktualizowane wagi modeli
        """
        self.logger.info("Aktualizuję wagi modeli AI")
        
        # Analizuj wydajność wszystkich modeli
        performance = self.analyze_performance(days=self.config.get('signal_history_days', 30))
        
        if not performance or 'by_model' not in performance:
            self.logger.warning("Brak danych o wydajności modeli")
            return {
                'claude': 0.33,
                'grok': 0.33,
                'deepseek': 0.33
            }
        
        model_metrics = performance.get('by_model', {})
        
        # Oblicz wagi na podstawie win_rate i profit_factor
        weights = {}
        total_score = 0
        
        for model, metrics in model_metrics.items():
            win_rate = metrics.get('win_rate', 0.5)
            profit_factor = metrics.get('profit_factor', 1.0)
            
            # Oblicz wynik dla modelu (kombinacja win_rate i profit_factor)
            score = win_rate * 0.5 + min(profit_factor / 3, 1.0) * 0.5
            weights[model] = score
            total_score += score
        
        # Normalizuj wagi
        if total_score > 0:
            for model in weights:
                weights[model] /= total_score
        else:
            # Jeśli brak danych, ustaw równe wagi
            models = list(weights.keys())
            equal_weight = 1.0 / len(models) if models else 0
            weights = {model: equal_weight for model in models}
        
        # Upewnij się, że mamy wagi dla wszystkich modeli
        default_models = ['claude', 'grok', 'deepseek']
        for model in default_models:
            if model not in weights:
                weights[model] = 0.1  # Minimalna waga dla modeli bez danych
        
        # Renormalizuj wagi
        total_weight = sum(weights.values())
        if total_weight > 0:
            for model in weights:
                weights[model] /= total_weight
        
        # Zapisz zaktualizowane wagi w pamięci podręcznej
        self.model_performance = {
            'weights': weights,
            'updated_at': datetime.now()
        }
        
        return weights
    
    def get_feedback_stats(self) -> Dict[str, Any]:
        """
        Zwraca statystyki mechanizmu feedback loop.
        
        Returns:
            Dict zawierający statystyki
        """
        return {
            'strategy_performance': self.strategy_performance,
            'model_performance': self.model_performance,
            'parameter_history': {k: v[-1] if v else None for k, v in self.parameter_history.items()},
            'last_optimization': self.last_optimization.isoformat(),
            'learning_strategy': self.config.get('learning_strategy', 'HYBRID')
        }


def get_feedback_loop() -> FeedbackLoop:
    """
    Zwraca instancję FeedbackLoop (Singleton).
    
    Returns:
        Instancja FeedbackLoop
    """
    return FeedbackLoop() 