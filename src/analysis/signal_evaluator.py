#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
System oceny jakości sygnałów handlowych.
"""

import logging
import time
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

from src.database.models import TradingSignal, SignalEvaluation
from src.database.trading_signal_repository import get_trading_signal_repository
from src.database.signal_evaluation_repository import get_signal_evaluation_repository
from src.mt5_bridge.mt5_connector import get_mt5_connector
from src.config.config_manager import ConfigManager

logger = logging.getLogger(__name__)


class SignalEvaluator:
    """
    System oceny jakości sygnałów handlowych.
    Monitoruje sygnały, ocenia ich skuteczność i dostarcza metryki wydajności.
    """
    
    _instance = None
    
    @classmethod
    def get_instance(cls) -> 'SignalEvaluator':
        """
        Pobiera instancję ewaluatora sygnałów w trybie singletonu.
        
        Returns:
            SignalEvaluator: Instancja ewaluatora sygnałów
        """
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def __init__(self):
        """
        Inicjalizacja systemu oceny sygnałów handlowych.
        """
        self.signal_repository = get_trading_signal_repository()
        self.evaluation_repository = get_signal_evaluation_repository()
        self.mt5_connector = get_mt5_connector()
        self.config = ConfigManager().get_config().get('signal_evaluation', {})
        self.logger = logging.getLogger(__name__)
        self.logger.info("SignalEvaluator zainicjalizowany")
        
        # Domyślne ustawienia
        self.default_config = {
            'evaluation_period_days': 30,
            'check_interval_seconds': 300,  # 5 minut
            'max_evaluation_time_hours': 168,  # 7 dni
            'success_threshold_percentage': 0.8,  # 80%
            'failure_threshold_percentage': 0.8,  # 80%
            'update_price_percentage': 0.5  # 0.5%
        }
        
        # Łączenie domyślnych ustawień z konfiguracją z pliku
        self.config = {**self.default_config, **self.config}
    
    def register_new_signal(self, signal: TradingSignal) -> Optional[SignalEvaluation]:
        """
        Rejestruje nowy sygnał handlowy do oceny.
        
        Args:
            signal: Sygnał handlowy do oceny
            
        Returns:
            Optional[SignalEvaluation]: Obiekt oceny sygnału lub None w przypadku błędu
        """
        try:
            self.logger.info(f"Rejestrowanie nowego sygnału {signal.direction} dla {signal.symbol} do oceny")
            
            # Obliczenie potencjalnego zysku i straty
            max_profit = abs(signal.take_profit - signal.entry_price)
            max_loss = abs(signal.stop_loss - signal.entry_price)
            
            # Obliczenie stosunku zysku do ryzyka
            risk_reward_ratio = max_profit / max_loss if max_loss > 0 else 0
            
            # Utworzenie obiektu oceny sygnału
            evaluation = SignalEvaluation(
                signal_id=signal.id,
                symbol=signal.symbol,
                timeframe=signal.timeframe,
                direction=signal.direction,
                entry_price=signal.entry_price,
                stop_loss=signal.stop_loss,
                take_profit=signal.take_profit,
                max_profit=max_profit,
                max_loss=max_loss,
                risk_reward_ratio=risk_reward_ratio,
                entry_time=signal.created_at,
                confidence=signal.confidence,
                evaluation_status="open",
                metadata={
                    "signal_metadata": signal.metadata if hasattr(signal, "metadata") else {},
                    "ai_analysis": signal.ai_analysis
                }
            )
            
            # Zapisanie oceny sygnału
            evaluation_id = self.evaluation_repository.save_evaluation(evaluation)
            
            if evaluation_id > 0:
                evaluation.id = evaluation_id
                self.logger.info(f"Zarejestrowano sygnał {signal.direction} dla {signal.symbol} do oceny (ID: {evaluation.id})")
                return evaluation
            else:
                self.logger.error(f"Nie udało się zarejestrować sygnału {signal.direction} dla {signal.symbol} do oceny")
                return None
        except Exception as e:
            self.logger.error(f"Błąd podczas rejestracji sygnału: {e}")
            return None
    
    def update_evaluation(self, evaluation_id: int, current_price: float) -> Optional[SignalEvaluation]:
        """
        Aktualizuje ocenę sygnału handlowego na podstawie aktualnej ceny.
        
        Args:
            evaluation_id: ID oceny sygnału handlowego do aktualizacji
            current_price: Aktualna cena instrumentu
            
        Returns:
            SignalEvaluation: Zaktualizowana ocena sygnału handlowego lub None w przypadku błędu
        """
        try:
            self.logger.debug(f"Aktualizacja oceny sygnału ID: {evaluation_id}")
            
            # Pobierz ocenę z repozytorium
            evaluation = self.evaluation_repository.get_by_id(evaluation_id)
            if not evaluation:
                self.logger.error(f"Nie znaleziono oceny o ID: {evaluation_id}")
                return None
                
            # Sprawdzenie czy sygnał już jest zamknięty
            if evaluation.evaluation_status != "open":
                return evaluation
            
            # Obliczenie różnicy ceny
            price_diff = abs(current_price - evaluation.entry_price)
            price_movement_percentage = (price_diff / evaluation.entry_price) * 100
            
            # Aktualizacja procentowej zmiany ceny
            evaluation.price_movement_percentage = price_movement_percentage
            
            # Sprawdzenie czy osiągnięto poziom Take Profit
            hit_target = False
            if evaluation.direction == "BUY" and current_price >= evaluation.take_profit:
                hit_target = True
            elif evaluation.direction == "SELL" and current_price <= evaluation.take_profit:
                hit_target = True
            
            # Sprawdzenie czy osiągnięto poziom Stop Loss
            hit_stop = False
            if evaluation.direction == "BUY" and current_price <= evaluation.stop_loss:
                hit_stop = True
            elif evaluation.direction == "SELL" and current_price >= evaluation.stop_loss:
                hit_stop = True
            
            # Aktualizacja statusu oceny sygnału
            if hit_target or hit_stop:
                # Zamknięcie oceny sygnału
                evaluation.exit_price = current_price
                evaluation.exit_time = datetime.now()
                evaluation.evaluation_status = "closed"
                
                # Obliczenie czasu do osiągnięcia celu/stop
                time_diff = (evaluation.exit_time - evaluation.entry_time).total_seconds()
                
                if hit_target:
                    evaluation.hit_target = True
                    evaluation.hit_stop = False
                    evaluation.hit_neither = False
                    evaluation.time_to_target = time_diff
                else:
                    evaluation.hit_target = False
                    evaluation.hit_stop = True
                    evaluation.hit_neither = False
                    evaluation.time_to_stop = time_diff
                
                # Obliczenie rzeczywistego zysku/straty
                if evaluation.direction == "BUY":
                    actual_pips = (evaluation.exit_price - evaluation.entry_price)
                else:  # SELL
                    actual_pips = (evaluation.entry_price - evaluation.exit_price)
                    
                if actual_pips > 0:
                    evaluation.actual_profit = actual_pips
                    evaluation.actual_loss = 0
                else:
                    evaluation.actual_profit = 0
                    evaluation.actual_loss = abs(actual_pips)
                
                # Obliczenie stosunku zysku do straty
                if evaluation.actual_loss > 0:
                    evaluation.profit_loss_ratio = evaluation.actual_profit / evaluation.actual_loss
                elif evaluation.actual_profit > 0:
                    evaluation.profit_loss_ratio = float('inf')  # Nieskończony stosunek zysku do straty
                else:
                    evaluation.profit_loss_ratio = 0
                
                self.logger.info(
                    f"Sygnał {evaluation.direction} dla {evaluation.symbol} zakończony: "
                    f"{'Cel osiągnięty' if hit_target else 'Stop Loss aktywowany'}"
                )
            
            # Sprawdzenie czy upłynął maksymalny czas oceny
            max_time = self.config['max_evaluation_time_hours']
            if (datetime.now() - evaluation.entry_time).total_seconds() > max_time * 3600:
                if evaluation.evaluation_status == "open":
                    evaluation.evaluation_status = "expired"
                    evaluation.exit_time = datetime.now()
                    evaluation.exit_price = current_price
                    evaluation.hit_target = False
                    evaluation.hit_stop = False
                    evaluation.hit_neither = True
                    
                    # Obliczenie rzeczywistego zysku/straty
                    if evaluation.direction == "BUY":
                        actual_pips = (evaluation.exit_price - evaluation.entry_price)
                    else:  # SELL
                        actual_pips = (evaluation.entry_price - evaluation.exit_price)
                        
                    if actual_pips > 0:
                        evaluation.actual_profit = actual_pips
                        evaluation.actual_loss = 0
                    else:
                        evaluation.actual_profit = 0
                        evaluation.actual_loss = abs(actual_pips)
                    
                    # Obliczenie stosunku zysku do straty
                    if evaluation.actual_loss > 0:
                        evaluation.profit_loss_ratio = evaluation.actual_profit / evaluation.actual_loss
                    elif evaluation.actual_profit > 0:
                        evaluation.profit_loss_ratio = float('inf')
                    else:
                        evaluation.profit_loss_ratio = 0
                    
                    self.logger.info(
                        f"Sygnał {evaluation.direction} dla {evaluation.symbol} wygasł po {max_time} godzinach"
                    )
            
            # Aktualizacja czasowa
            evaluation.updated_at = datetime.now()
            
            # Zapisanie aktualizacji
            self.evaluation_repository.save_evaluation(evaluation)
            
            return evaluation
            
        except Exception as e:
            self.logger.error(f"Błąd podczas aktualizacji oceny sygnału: {e}")
            return None
    
    def check_open_evaluations(self) -> int:
        """
        Sprawdza wszystkie otwarte oceny sygnałów i aktualizuje ich status.
        
        Returns:
            int: Liczba zaktualizowanych ocen
        """
        try:
            self.logger.info("Sprawdzanie otwartych ocen sygnałów")
            
            # Pobranie wszystkich otwartych ocen
            open_evaluations = self.evaluation_repository.get_open_evaluations()
            
            if not open_evaluations:
                self.logger.info("Brak otwartych ocen sygnałów")
                return 0
            
            self.logger.info(f"Znaleziono {len(open_evaluations)} otwartych ocen sygnałów")
            
            # Grupowanie ocen według symbolu
            evaluations_by_symbol = {}
            for evaluation in open_evaluations:
                if evaluation.symbol not in evaluations_by_symbol:
                    evaluations_by_symbol[evaluation.symbol] = []
                evaluations_by_symbol[evaluation.symbol].append(evaluation)
            
            updated_count = 0
            
            # Aktualizacja ocen dla każdego symbolu
            for symbol, evaluations in evaluations_by_symbol.items():
                try:
                    # Pobieranie aktualnej ceny
                    price_info = self.mt5_connector.get_current_price(symbol)
                    
                    if not price_info or 'bid' not in price_info or 'ask' not in price_info:
                        self.logger.warning(f"Nie udało się pobrać aktualnej ceny dla {symbol}")
                        continue
                    
                    # Aktualizacja ocen dla danego symbolu
                    for evaluation in evaluations:
                        # Wybór odpowiedniej ceny w zależności od kierunku
                        current_price = price_info['bid'] if evaluation.direction == "SELL" else price_info['ask']
                        
                        # Aktualizacja oceny
                        self.update_evaluation(evaluation.id, current_price)
                        updated_count += 1
                
                except Exception as e:
                    self.logger.error(f"Błąd podczas aktualizacji ocen dla {symbol}: {e}")
                    continue
            
            self.logger.info(f"Zaktualizowano {updated_count} ocen sygnałów")
            return updated_count
            
        except Exception as e:
            self.logger.error(f"Błąd podczas sprawdzania otwartych ocen sygnałów: {e}")
            return 0
    
    def get_signal_performance(self, symbol: Optional[str] = None, days: int = 30) -> Dict[str, Any]:
        """
        Pobiera statystyki wydajności sygnałów handlowych.
        
        Args:
            symbol: Symbol instrumentu (opcjonalnie)
            days: Liczba dni, dla których pobierać statystyki
            
        Returns:
            Dict[str, Any]: Statystyki wydajności sygnałów
        """
        try:
            self.logger.info(f"Pobieranie statystyk wydajności sygnałów dla {'wszystkich symboli' if symbol is None else symbol}")
            
            # Pobranie podsumowania ocen
            summary = self.evaluation_repository.get_evaluation_summary(symbol, days)
            
            # Sprawdzenie czy podsumowanie zawiera wszystkie potrzebne pola
            if 'total_signals' not in summary or summary['total_signals'] == 0:
                return {
                    'total_signals': 0,
                    'successful_signals': 0,
                    'failed_signals': 0,
                    'hit_target_count': 0,
                    'hit_stop_count': 0,
                    'hit_neither_count': 0,
                    'avg_profit': 0.0,
                    'avg_loss': 0.0,
                    'avg_risk_reward': 0.0,
                    'avg_profit_loss_ratio': 0.0,
                    'success_rate': 0.0,
                    'win_rate': 0.0,
                    'loss_rate': 0.0,
                    'win_ratio': 0.0,
                    'expected_value': 0.0,
                    'timeframe': days,
                    'timestamp': datetime.now().isoformat()
                }
            
            # Dodanie brakujących pól, jeśli nie istnieją
            if 'hit_target_count' not in summary:
                summary['hit_target_count'] = summary.get('successful_signals', 0)
            if 'hit_stop_count' not in summary:
                summary['hit_stop_count'] = summary.get('failed_signals', 0)
            if 'hit_neither_count' not in summary:
                summary['hit_neither_count'] = 0
            if 'avg_profit_loss_ratio' not in summary:
                summary['avg_profit_loss_ratio'] = 0.0
            if 'success_rate' not in summary:
                total = summary['total_signals']
                successful = summary['successful_signals']
                summary['success_rate'] = (successful / total * 100) if total > 0 else 0.0
            
            # Obliczenie dodatkowych statystyk
            win_rate = summary['success_rate']
            loss_rate = 100 - win_rate if win_rate <= 100 else 0
            
            # Obliczenie stosunku wygranych do przegranych
            win_ratio = summary['hit_target_count'] / summary['hit_stop_count'] if summary['hit_stop_count'] > 0 else float('inf')
            
            # Obliczenie oczekiwanej wartości (EV)
            avg_profit = summary['avg_profit_loss_ratio']
            expected_value = (win_rate / 100 * avg_profit) - (loss_rate / 100)
            
            # Rozszerzenie podsumowania o dodatkowe statystyki
            performance = {
                **summary,
                'win_rate': win_rate,
                'loss_rate': loss_rate,
                'win_ratio': win_ratio,
                'expected_value': expected_value,
                'timeframe': days,
                'timestamp': datetime.now().isoformat()
            }
            
            return performance
            
        except Exception as e:
            self.logger.error(f"Błąd podczas pobierania statystyk wydajności sygnałów: {e}")
            return {
                'error': str(e),
                'total_signals': 0,
                'successful_signals': 0,
                'failed_signals': 0,
                'hit_target_count': 0,
                'hit_stop_count': 0,
                'hit_neither_count': 0,
                'avg_profit': 0.0,
                'avg_loss': 0.0,
                'avg_risk_reward': 0.0,
                'avg_profit_loss_ratio': 0.0,
                'success_rate': 0.0,
                'win_rate': 0.0,
                'loss_rate': 0.0,
                'win_ratio': 0.0,
                'expected_value': 0.0,
                'timeframe': days,
                'timestamp': datetime.now().isoformat()
            }
    
    def get_performance_by_confidence(self, days: int = 30) -> Dict[str, Dict[str, Any]]:
        """
        Pobiera statystyki wydajności sygnałów według poziomu pewności.
        
        Args:
            days: Liczba dni wstecz do analizy
            
        Returns:
            Dict: Statystyki wydajności według poziomu pewności
        """
        try:
            self.logger.info(f"Pobieranie statystyk wydajności sygnałów według poziomu pewności dla ostatnich {days} dni")
            start_date = datetime.now() - timedelta(days=days)
            
            # Pobierz wszystkie oceny z określonego okresu
            evaluations = self.evaluation_repository.get_evaluations_by_date_range(start_date=start_date)
            
            # Pogrupuj oceny według poziomów pewności
            confidence_buckets = {
                'low': {'min': 0.5, 'max': 0.7, 'signals': []},
                'medium': {'min': 0.7, 'max': 0.85, 'signals': []},
                'high': {'min': 0.85, 'max': 1.0, 'signals': []}
            }
            
            for eval_record in evaluations:
                conf = eval_record.get('confidence', 0)
                for bucket, bucket_data in confidence_buckets.items():
                    if bucket_data['min'] <= conf < bucket_data['max']:
                        bucket_data['signals'].append(eval_record)
                        break
                        
            # Oblicz statystyki dla każdego poziomu pewności
            result = {}
            for bucket, bucket_data in confidence_buckets.items():
                signals = bucket_data['signals']
                
                if not signals:
                    result[bucket] = {
                        'total_signals': 0,
                        'successful_signals': 0,
                        'failed_signals': 0,
                        'success_rate': 0,
                        'avg_profit': 0,
                        'avg_loss': 0
                    }
                    continue
                    
                # Policz udane sygnały
                successful = [s for s in signals if s.get('evaluation_status') == 'SUCCESS']
                failed = [s for s in signals if s.get('evaluation_status') == 'FAILURE']
                
                # Oblicz statystyki
                total = len(signals)
                success_rate = (len(successful) / total) * 100 if total > 0 else 0
                
                avg_profit = sum(s.get('realized_pips', 0) for s in successful) / len(successful) if successful else 0
                avg_loss = sum(s.get('realized_pips', 0) for s in failed) / len(failed) if failed else 0
                
                result[bucket] = {
                    'total_signals': total,
                    'successful_signals': len(successful),
                    'failed_signals': len(failed),
                    'success_rate': success_rate,
                    'avg_profit': avg_profit,
                    'avg_loss': avg_loss
                }
                
            return result
        except Exception as e:
            self.logger.error(f"Błąd podczas analizy wydajności według poziomów pewności: {e}")
            return {
                'low': {'total_signals': 0, 'successful_signals': 0, 'failed_signals': 0, 'success_rate': 0, 'avg_profit': 0, 'avg_loss': 0},
                'medium': {'total_signals': 0, 'successful_signals': 0, 'failed_signals': 0, 'success_rate': 0, 'avg_profit': 0, 'avg_loss': 0},
                'high': {'total_signals': 0, 'successful_signals': 0, 'failed_signals': 0, 'success_rate': 0, 'avg_profit': 0, 'avg_loss': 0}
            }
    
    def get_performance_by_timeframe(self, days: int = 30) -> Dict[str, Dict[str, Any]]:
        """
        Pobiera statystyki wydajności sygnałów według ramy czasowej.
        
        Args:
            days: Liczba dni wstecz do analizy
            
        Returns:
            Dict: Statystyki wydajności według ramy czasowej
        """
        try:
            self.logger.info(f"Pobieranie statystyk wydajności sygnałów według timeframe dla ostatnich {days} dni")
            start_date = datetime.now() - timedelta(days=days)
            
            # Pobierz wszystkie oceny z określonego okresu
            evaluations = self.evaluation_repository.get_evaluations_by_date_range(start_date=start_date)
            
            # Pogrupuj oceny według timeframe
            timeframe_buckets = {}
            
            for eval_record in evaluations:
                timeframe = eval_record.get('timeframe', 'unknown')
                if timeframe not in timeframe_buckets:
                    timeframe_buckets[timeframe] = []
                timeframe_buckets[timeframe].append(eval_record)
                
            # Oblicz statystyki dla każdego timeframe
            result = {}
            for timeframe, signals in timeframe_buckets.items():
                if not signals:
                    result[timeframe] = {
                        'total_signals': 0,
                        'successful_signals': 0,
                        'failed_signals': 0,
                        'success_rate': 0,
                        'avg_profit': 0,
                        'avg_loss': 0
                    }
                    continue
                    
                # Policz udane sygnały
                successful = [s for s in signals if s.get('evaluation_status') == 'SUCCESS']
                failed = [s for s in signals if s.get('evaluation_status') == 'FAILURE']
                
                # Oblicz statystyki
                total = len(signals)
                success_rate = (len(successful) / total) * 100 if total > 0 else 0
                
                avg_profit = sum(s.get('realized_pips', 0) for s in successful) / len(successful) if successful else 0
                avg_loss = sum(s.get('realized_pips', 0) for s in failed) / len(failed) if failed else 0
                
                result[timeframe] = {
                    'total_signals': total,
                    'successful_signals': len(successful),
                    'failed_signals': len(failed),
                    'success_rate': success_rate,
                    'avg_profit': avg_profit,
                    'avg_loss': avg_loss
                }
                
            return result
        except Exception as e:
            self.logger.error(f"Błąd podczas analizy wydajności według timeframe: {e}")
            return {
                'M5': {'total_signals': 0, 'successful_signals': 0, 'failed_signals': 0, 'success_rate': 0, 'avg_profit': 0, 'avg_loss': 0},
                'M15': {'total_signals': 0, 'successful_signals': 0, 'failed_signals': 0, 'success_rate': 0, 'avg_profit': 0, 'avg_loss': 0},
                'H1': {'total_signals': 0, 'successful_signals': 0, 'failed_signals': 0, 'success_rate': 0, 'avg_profit': 0, 'avg_loss': 0}
            }


def get_signal_evaluator() -> SignalEvaluator:
    """
    Funkcja pomocnicza do pobierania instancji ewaluatora sygnałów.
    
    Returns:
        SignalEvaluator: Instancja ewaluatora sygnałów
    """
    return SignalEvaluator.get_instance() 