#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Moduł do walidacji sygnałów tradingowych.

Ten moduł zawiera funkcje i klasy do weryfikacji sygnałów tradingowych
pod kątem zgodności z polityką zarządzania ryzykiem, istniejącymi pozycjami
oraz historycznymi wynikami.
"""

import os
import json
import time
import logging
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Union, Tuple
from enum import Enum, auto

# Importy wewnętrzne
from src.analysis.signal_generator import SignalType, SignalStrength, SignalSource
from src.risk_management.risk_manager import RiskManager, get_risk_manager
from src.position_management.position_manager import PositionManager, get_position_manager
from src.database.signal_repository import SignalRepository, get_signal_repository
from src.utils.config_manager import ConfigManager

# Konfiguracja loggera
logger = logging.getLogger('trading_agent.analysis.signal_validator')


class ValidationResult(Enum):
    """Wynik walidacji sygnału tradingowego."""
    VALID = auto()                      # Sygnał poprawny
    REJECTED_RISK_POLICY = auto()       # Narusza politykę ryzyka
    REJECTED_POSITION_LIMIT = auto()    # Przekracza limit pozycji
    REJECTED_EXPOSURE_LIMIT = auto()    # Przekracza limit ekspozycji
    REJECTED_RISK_REWARD = auto()       # Nieakceptowalny stosunek zysk/ryzyko
    REJECTED_LOW_PROBABILITY = auto()   # Zbyt niska prawdopodobieństwo sukcesu
    REJECTED_EXISTING_POSITION = auto() # Konflikt z istniejącą pozycją
    REJECTED_LOW_SCORE = auto()         # Zbyt niski wynik oceny
    REJECTED_MARKET_CONDITIONS = auto() # Nieodpowiednie warunki rynkowe
    REJECTED_OTHER = auto()             # Inne powody odrzucenia


class SignalValidator:
    """Klasa do walidacji sygnałów tradingowych względem polityki zarządzania ryzykiem."""
    
    _instance = None
    _lock = threading.Lock()
    
    @classmethod
    def __new__(cls, *args, **kwargs):
        """Implementacja wzorca Singleton."""
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(SignalValidator, cls).__new__(cls)
                cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, config):
        """Inicjalizacja walidatora sygnałów."""
        if self._initialized:
            return
            
        self.logger = logging.getLogger('trading_agent.analysis.signal_validator')
        self.logger.info("Inicjalizacja SignalValidator")
        
        # Inicjalizacja zależności
        self.risk_manager = get_risk_manager()
        self.position_manager = get_position_manager()
        self.signal_repository = get_signal_repository()
        
        # Parametry konfiguracyjne
        self.config_manager = ConfigManager()
        self.config = self._load_config()
        
        # Aktualizujemy konfigurację z przekazanych parametrów
        self.config.update(config)
        self.logger.info("Zaktualizowano konfigurację z przekazanych parametrów")
        
        # Buforowanie ostatnich wyników walidacji
        self.validation_cache = {}
        
        self._initialized = True
        
    def _load_config(self) -> Dict[str, Any]:
        """
        Wczytuje konfigurację z pliku config.yaml.
        
        Returns:
            Dict zawierający konfigurację
        """
        try:
            config = self.config_manager.get_config_section('signal_validation')
            self.logger.info("Wczytano konfigurację dla walidatora sygnałów")
            return config
        except Exception as e:
            self.logger.error(f"Błąd wczytywania konfiguracji: {str(e)}")
            # Domyślna konfiguracja w przypadku błędu
            return {
                'min_probability': 0.65,
                'min_risk_reward_ratio': 1.5,
                'max_positions_per_symbol': 3,
                'max_positions_total': 10,
                'max_exposure_per_symbol_percent': 10.0,
                'max_exposure_total_percent': 25.0,
                'scoring_weights': {
                    'confidence': 0.3,
                    'historical_performance': 0.25,
                    'current_market_conditions': 0.2,
                    'risk_reward': 0.25
                },
                'min_score_threshold': 0.6,
                'validation_expiry': 300,  # 5 minut w sekundach
                'enable_historical_analysis': True,
                'enable_correlation_check': True,
                'enable_position_check': True
            }
            
    def validate_signal(self, signal: Dict[str, Any]) -> Dict[str, Any]:
        """
        Waliduje sygnał tradingowy.
        
        Args:
            signal: Sygnał do walidacji
            
        Returns:
            Dict zawierający wynik walidacji oraz metadane
        """
        start_time = time.time()
        self.logger.info(f"Walidacja sygnału typu {signal.get('type')} dla {signal.get('symbol')}")
        
        # Sprawdź cache
        signal_key = f"{signal.get('symbol')}_{signal.get('type')}_{signal.get('timeframe')}"
        if signal_key in self.validation_cache:
            cached_result = self.validation_cache[signal_key]
            if cached_result['timestamp'] + self.config.get('validation_expiry', 300) > time.time():
                self.logger.info(f"Użyto zbuforowanego wyniku walidacji dla {signal_key}")
                return cached_result
        
        # Pobierz aktualne dane o pozycjach i ryzyku
        current_positions = self._get_current_positions(signal.get('symbol'))
        risk_data = self._get_risk_data(signal.get('symbol'))
        
        # Wykonaj walidacje
        result = self._perform_validations(signal, current_positions, risk_data)
        
        # Jeśli sygnał jest ważny, oblicz ostre limity dla zlecenia
        if result['validation_result'] == ValidationResult.VALID:
            result['order_limits'] = self._calculate_order_limits(signal, risk_data)
        
        # Zapisz wynik do cache
        self.validation_cache[signal_key] = result
        
        # Zapisz wynik walidacji do bazy danych, jeśli to konieczne
        if self.config.get('save_validation_results', True):
            self._save_validation_result(signal, result)
        
        self.logger.info(f"Walidacja sygnału {signal_key} zakończona w {time.time() - start_time:.4f}s z wynikiem: {result['validation_result'].name}")
        return result
        
    def validate_signals(self, signals: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Waliduje listę sygnałów tradingowych.
        
        Args:
            signals: Lista sygnałów do walidacji
            
        Returns:
            Lista zawierająca wyniki walidacji
        """
        results = []
        
        for signal in signals:
            result = self.validate_signal(signal)
            results.append(result)
        
        return results
        
    def _perform_validations(self, signal: Dict[str, Any], 
                           positions: List[Dict[str, Any]], 
                           risk_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Wykonuje wszystkie walidacje dla sygnału.
        
        Args:
            signal: Sygnał do walidacji
            positions: Aktualne pozycje
            risk_data: Dane o ryzyku
            
        Returns:
            Dict zawierający wynik walidacji oraz metadane
        """
        # Inicjalizacja wyniku
        result = {
            'signal': signal,
            'validation_result': ValidationResult.VALID,
            'rejection_reason': None,
            'timestamp': time.time(),
            'score': 0.0,
            'position_conflicts': [],
            'risk_assessment': {},
            'order_limits': {}
        }
        
        # 1. Sprawdzenie prawdopodobieństwa sukcesu (confidence)
        if signal.get('confidence', 0) < self.config.get('min_probability', 0.65):
            result['validation_result'] = ValidationResult.REJECTED_LOW_PROBABILITY
            result['rejection_reason'] = f"Zbyt niska pewność: {signal.get('confidence', 0)}"
            return result
        
        # 2. Sprawdzenie limitów pozycji
        if self.config.get('enable_position_check', True):
            position_validation = self._validate_position_limits(signal, positions, risk_data)
            if position_validation['valid'] is False:
                result['validation_result'] = position_validation['validation_result']
                result['rejection_reason'] = position_validation['reason']
                result['position_conflicts'] = position_validation.get('conflicts', [])
                return result
        
        # 3. Sprawdzenie limitów ekspozycji
        exposure_validation = self._validate_exposure_limits(signal, risk_data)
        if exposure_validation['valid'] is False:
            result['validation_result'] = exposure_validation['validation_result']
            result['rejection_reason'] = exposure_validation['reason']
            return result
        
        # 4. Analiza historyczna
        if self.config.get('enable_historical_analysis', True):
            historical_validation = self._validate_historical_performance(signal)
            if historical_validation['valid'] is False:
                result['validation_result'] = ValidationResult.REJECTED_LOW_PROBABILITY
                result['rejection_reason'] = historical_validation['reason']
                return result
            result['historical_stats'] = historical_validation.get('stats', {})
        
        # 5. Sprawdzenie warunków rynkowych
        market_validation = self._validate_market_conditions(signal)
        if market_validation['valid'] is False:
            result['validation_result'] = ValidationResult.REJECTED_MARKET_CONDITIONS
            result['rejection_reason'] = market_validation['reason']
            return result
        
        # 6. Obliczenie ogólnego wyniku
        score = self._calculate_signal_score(signal, historical_validation, market_validation)
        result['score'] = score
        
        if score < self.config.get('min_score_threshold', 0.6):
            result['validation_result'] = ValidationResult.REJECTED_LOW_SCORE
            result['rejection_reason'] = f"Zbyt niski wynik oceny: {score}"
            return result
        
        # Uzupełnienie wyniku o dane oceny ryzyka
        result['risk_assessment'] = {
            'exposure_validation': exposure_validation,
            'position_validation': position_validation,
            'historical_validation': historical_validation,
            'market_validation': market_validation,
            'score': score
        }
        
        return result
        
    def _validate_position_limits(self, signal: Dict[str, Any], 
                                positions: List[Dict[str, Any]], 
                                risk_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Waliduje sygnał pod kątem limitów pozycji.
        
        Args:
            signal: Sygnał do walidacji
            positions: Aktualne pozycje
            risk_data: Dane o ryzyku
            
        Returns:
            Dict zawierający wynik walidacji pozycji
        """
        symbol = signal.get('symbol')
        signal_type = signal.get('type')
        
        # Sprawdzenie konfliktów z istniejącymi pozycjami
        symbol_positions = [p for p in positions if p.get('symbol') == symbol]
        opposing_positions = []
        
        # Sprawdzenie przeciwstawnych pozycji
        if signal_type == SignalType.BUY.value:
            opposing_positions = [p for p in symbol_positions if p.get('type') == 'sell']
        elif signal_type == SignalType.SELL.value:
            opposing_positions = [p for p in symbol_positions if p.get('type') == 'buy']
        
        # Jeśli znaleziono przeciwstawne pozycje i nie zezwalamy na hedging
        if opposing_positions and not self.config.get('allow_hedging', False):
            return {
                'valid': False,
                'validation_result': ValidationResult.REJECTED_EXISTING_POSITION,
                'reason': f"Istnieją przeciwstawne pozycje dla {symbol}",
                'conflicts': opposing_positions
            }
        
        # Sprawdzenie limitu pozycji dla symbolu
        symbol_position_count = len(symbol_positions)
        max_positions_per_symbol = risk_data.get('max_positions_per_symbol', 
                                              self.config.get('max_positions_per_symbol', 3))
                                              
        if symbol_position_count >= max_positions_per_symbol:
            return {
                'valid': False,
                'validation_result': ValidationResult.REJECTED_POSITION_LIMIT,
                'reason': f"Przekroczony limit pozycji dla symbolu: {symbol_position_count}/{max_positions_per_symbol}"
            }
            
        # Sprawdzenie całkowitego limitu pozycji
        total_position_count = len(positions)
        max_positions_total = risk_data.get('max_positions_total', 
                                         self.config.get('max_positions_total', 10))
                                         
        if total_position_count >= max_positions_total:
            return {
                'valid': False,
                'validation_result': ValidationResult.REJECTED_POSITION_LIMIT,
                'reason': f"Przekroczony całkowity limit pozycji: {total_position_count}/{max_positions_total}"
            }
            
        # Sprawdzenie podobnych sygnałów, które mogły już wygenerować pozycje
        recent_signals = self._get_recent_signals(symbol, signal_type)
        if len(recent_signals) > 0:
            # Sprawdzamy czy niedawno wygenerowaliśmy podobny sygnał, który mógł już
            # doprowadzić do otwarcia pozycji, ale nie zdążył się jeszcze pojawić w systemie
            self.logger.info(f"Istnieją niedawne sygnały dla {symbol} typu {signal_type}, ale mogą one nie mieć jeszcze otwartych pozycji")
        
        return {
            'valid': True,
            'symbol_positions': symbol_position_count,
            'total_positions': total_position_count,
            'max_symbol_positions': max_positions_per_symbol,
            'max_total_positions': max_positions_total
        }
        
    def _validate_exposure_limits(self, signal: Dict[str, Any], 
                               risk_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Waliduje sygnał pod kątem limitów ekspozycji.
        
        Args:
            signal: Sygnał do walidacji
            risk_data: Dane o ryzyku
            
        Returns:
            Dict zawierający wynik walidacji ekspozycji
        """
        symbol = signal.get('symbol')
        
        # Pobierz aktualne ekspozycje
        symbol_exposure = risk_data.get('exposure_by_symbol', {}).get(symbol, 0)
        symbol_exposure_percent = risk_data.get('exposure_percent_by_symbol', {}).get(symbol, 0)
        total_exposure = risk_data.get('total_exposure', 0)
        total_exposure_percent = risk_data.get('exposure_percent', 0)
        
        # Pobierz limity ekspozycji
        max_exposure_per_symbol_percent = risk_data.get('max_exposure_per_symbol_percent', 
                                                    self.config.get('max_exposure_per_symbol_percent', 10.0))
        max_exposure_total_percent = risk_data.get('max_exposure_percent', 
                                               self.config.get('max_exposure_total_percent', 25.0))
                                               
        # Sprawdzenie limitu ekspozycji dla symbolu
        if symbol_exposure_percent >= max_exposure_per_symbol_percent:
            return {
                'valid': False,
                'validation_result': ValidationResult.REJECTED_EXPOSURE_LIMIT,
                'reason': f"Przekroczony limit ekspozycji dla {symbol}: {symbol_exposure_percent:.2f}%/{max_exposure_per_symbol_percent:.2f}%"
            }
            
        # Sprawdzenie całkowitego limitu ekspozycji
        if total_exposure_percent >= max_exposure_total_percent:
            return {
                'valid': False,
                'validation_result': ValidationResult.REJECTED_EXPOSURE_LIMIT,
                'reason': f"Przekroczony całkowity limit ekspozycji: {total_exposure_percent:.2f}%/{max_exposure_total_percent:.2f}%"
            }
            
        # Sprawdzenie ekspozycji dla skorelowanych instrumentów
        if self.config.get('enable_correlation_check', True):
            correlations = risk_data.get('symbol_correlations', {}).get(symbol, {})
            correlated_symbols = [s for s, c in correlations.items() if abs(c) > 0.7]
            
            if correlated_symbols:
                correlated_exposure = sum(risk_data.get('exposure_by_symbol', {}).get(s, 0) for s in correlated_symbols)
                correlated_exposure_percent = (correlated_exposure / risk_data.get('account_balance', 1)) * 100
                
                max_correlated_exposure_percent = risk_data.get('max_correlated_symbols_exposure_percent', 
                                                             self.config.get('max_correlated_exposure_percent', 15.0))
                                                             
                if correlated_exposure_percent + symbol_exposure_percent > max_correlated_exposure_percent:
                    return {
                        'valid': False,
                        'validation_result': ValidationResult.REJECTED_EXPOSURE_LIMIT,
                        'reason': f"Przekroczony limit ekspozycji dla skorelowanych instrumentów: {correlated_exposure_percent + symbol_exposure_percent:.2f}%/{max_correlated_exposure_percent:.2f}%"
                    }
        
        return {
            'valid': True,
            'symbol_exposure': symbol_exposure,
            'symbol_exposure_percent': symbol_exposure_percent,
            'total_exposure': total_exposure,
            'total_exposure_percent': total_exposure_percent,
            'max_symbol_exposure_percent': max_exposure_per_symbol_percent,
            'max_total_exposure_percent': max_exposure_total_percent
        }
        
    def _validate_historical_performance(self, signal: Dict[str, Any]) -> Dict[str, Any]:
        """
        Waliduje sygnał na podstawie historycznych wyników.
        
        Args:
            signal: Sygnał do walidacji
            
        Returns:
            Dict zawierający wynik walidacji historycznej
        """
        symbol = signal.get('symbol')
        signal_type = signal.get('type')
        signal_source = signal.get('source')
        
        # Pobierz historyczne sygnały podobnego typu
        historical_signals = self._get_historical_signals(symbol, signal_type, signal_source)
        
        if not historical_signals:
            # Brak danych historycznych, zakładamy że sygnał jest ważny
            return {
                'valid': True,
                'stats': {
                    'count': 0,
                    'win_rate': None,
                    'avg_profit': None,
                    'avg_loss': None
                }
            }
            
        # Oblicz statystyki historyczne
        closed_signals = [s for s in historical_signals if s.get('result') in ['win', 'loss']]
        
        if not closed_signals:
            return {
                'valid': True,
                'stats': {
                    'count': len(historical_signals),
                    'win_rate': None,
                    'avg_profit': None,
                    'avg_loss': None
                }
            }
            
        win_signals = [s for s in closed_signals if s.get('result') == 'win']
        loss_signals = [s for s in closed_signals if s.get('result') == 'loss']
        
        win_rate = len(win_signals) / len(closed_signals) if closed_signals else 0
        avg_profit = sum(s.get('profit', 0) for s in win_signals) / len(win_signals) if win_signals else 0
        avg_loss = sum(s.get('loss', 0) for s in loss_signals) / len(loss_signals) if loss_signals else 0
        
        stats = {
            'count': len(closed_signals),
            'win_rate': win_rate,
            'avg_profit': avg_profit,
            'avg_loss': avg_loss,
            'profit_factor': abs(avg_profit / avg_loss) if avg_loss != 0 else float('inf')
        }
        
        # Minimalna akceptowalna wartość win_rate z konfiguracji
        min_win_rate = self.config.get('min_win_rate', 0.4)
        
        # Walidacja na podstawie statystyk
        if win_rate < min_win_rate and len(closed_signals) >= 10:
            return {
                'valid': False,
                'validation_result': ValidationResult.REJECTED_LOW_PROBABILITY,
                'reason': f"Niska historyczna skuteczność: {win_rate:.2f} < {min_win_rate}",
                'stats': stats
            }
            
        # Jeśli średnia strata jest znacznie większa niż średni zysk
        min_profit_factor = self.config.get('min_profit_factor', 0.7)
        profit_factor = stats['profit_factor']
        
        if profit_factor < min_profit_factor and len(closed_signals) >= 10:
            return {
                'valid': False,
                'validation_result': ValidationResult.REJECTED_RISK_REWARD,
                'reason': f"Niekorzystny stosunek zysku do straty: {profit_factor:.2f} < {min_profit_factor}",
                'stats': stats
            }
        
        return {
            'valid': True,
            'stats': stats
        }
        
    def _validate_market_conditions(self, signal: Dict[str, Any]) -> Dict[str, Any]:
        """
        Waliduje sygnał pod kątem aktualnych warunków rynkowych.
        
        Args:
            signal: Sygnał do walidacji
            
        Returns:
            Dict zawierający wynik walidacji warunków rynkowych
        """
        # W uproszczonej wersji zakładamy, że warunki rynkowe są odpowiednie
        # W pełnej implementacji można sprawdzać:
        # - Czy nie występuje zbyt duża zmienność
        # - Czy nie ma ważnych wydarzeń ekonomicznych
        # - Czy nie ma znaczących trendów przeciwnych do sygnału
        # - Czy nie ma problemów z płynnością
        
        return {
            'valid': True,
            'market_conditions': 'normal'
        }
        
    def _calculate_signal_score(self, signal: Dict[str, Any],
                             historical_validation: Dict[str, Any],
                             market_validation: Dict[str, Any]) -> float:
        """
        Oblicza ogólny wynik (score) dla sygnału.
        
        Args:
            signal: Sygnał do oceny
            historical_validation: Wynik walidacji historycznej
            market_validation: Wynik walidacji warunków rynkowych
            
        Returns:
            Float zawierający wynik w zakresie 0.0-1.0
        """
        # Pobierz wagi z konfiguracji
        weights = self.config.get('scoring_weights', {
            'confidence': 0.3,
            'historical_performance': 0.25,
            'current_market_conditions': 0.2,
            'risk_reward': 0.25
        })
        
        # Składowa pewności (confidence)
        confidence_score = min(signal.get('confidence', 0), 1.0)
        
        # Składowa historycznych wyników
        historical_stats = historical_validation.get('stats', {})
        if historical_stats.get('count', 0) < 5:
            # Zbyt mało danych historycznych, używamy wartości neutralnej
            historical_score = 0.6
        else:
            win_rate = historical_stats.get('win_rate', 0)
            profit_factor = historical_stats.get('profit_factor', 1.0)
            # Normalizacja
            win_rate_score = min(win_rate * 1.25, 1.0)  # Win rate 80% daje 1.0
            profit_factor_score = min(profit_factor / 2.0, 1.0)  # Profit factor 2.0 daje 1.0
            historical_score = (win_rate_score * 0.6) + (profit_factor_score * 0.4)
        
        # Składowa warunków rynkowych
        market_conditions = market_validation.get('market_conditions', 'normal')
        if market_conditions == 'ideal':
            market_score = 1.0
        elif market_conditions == 'good':
            market_score = 0.8
        elif market_conditions == 'normal':
            market_score = 0.6
        elif market_conditions == 'challenging':
            market_score = 0.4
        else:  # 'poor'
            market_score = 0.2
        
        # Składowa stosunku zysku do ryzyka
        risk_reward_ratio = signal.get('risk_reward_ratio', 1.0)
        risk_reward_score = min(risk_reward_ratio / 3.0, 1.0)  # Stosunek 3.0 daje 1.0
        
        # Obliczenie końcowego wyniku
        score = (
            (confidence_score * weights['confidence']) +
            (historical_score * weights['historical_performance']) +
            (market_score * weights['current_market_conditions']) +
            (risk_reward_score * weights['risk_reward'])
        )
        
        return round(score, 2)
        
    def _calculate_order_limits(self, signal: Dict[str, Any], 
                             risk_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Oblicza limity zlecenia dla ważnego sygnału.
        
        Args:
            signal: Zwalidowany sygnał
            risk_data: Dane o ryzyku
            
        Returns:
            Dict zawierający limity zlecenia
        """
        symbol = signal.get('symbol')
        price = signal.get('price', 0)
        
        # Pobierz dane o koncie
        account_balance = risk_data.get('account_balance', 0)
        
        # Obliczenie optymalnego poziomu stop-loss
        if signal.get('type') == SignalType.BUY.value:
            # Dla pozycji długiej stop-loss jest poniżej ceny
            stop_loss = price * 0.99  # Przykładowy stop-loss 1% poniżej ceny
        else:
            # Dla pozycji krótkiej stop-loss jest powyżej ceny
            stop_loss = price * 1.01  # Przykładowy stop-loss 1% powyżej ceny
        
        # Obliczenie optymalnego poziomu take-profit
        min_risk_reward_ratio = risk_data.get('min_risk_reward_ratio', 
                                         self.config.get('min_risk_reward_ratio', 1.5))
        
        if signal.get('type') == SignalType.BUY.value:
            # Dla pozycji długiej take-profit jest powyżej ceny
            risk = price - stop_loss
            take_profit = price + (risk * min_risk_reward_ratio)
        else:
            # Dla pozycji krótkiej take-profit jest poniżej ceny
            risk = stop_loss - price
            take_profit = price - (risk * min_risk_reward_ratio)
        
        # Obliczenie optymalnego rozmiaru pozycji
        # Używamy funkcji risk managera
        position_size = self.risk_manager.calculate_position_size(
            symbol=symbol,
            price=price,
            stop_loss=stop_loss,
            risk_percent=1.0  # Domyślnie 1% ryzyka
        )
        
        # Obliczenie wartości ryzyka
        risk_amount = account_balance * 0.01  # 1% konta
        
        return {
            'position_size': position_size,
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'risk_amount': risk_amount,
            'risk_percent': 1.0,
            'risk_points': abs(price - stop_loss),
            'reward_points': abs(price - take_profit),
            'risk_reward_ratio': min_risk_reward_ratio
        }
        
    def _get_current_positions(self, symbol: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Pobiera aktualne pozycje.
        
        Args:
            symbol: Opcjonalny symbol do filtrowania
            
        Returns:
            Lista aktywnych pozycji
        """
        try:
            positions = self.position_manager.get_active_positions()
            
            # Filtrowanie po symbolu, jeśli podano
            if symbol:
                positions = [p for p in positions if p.symbol == symbol]
            
            # Konwersja na słowniki
            return [p.to_dict() for p in positions]
        except Exception as e:
            self.logger.error(f"Błąd podczas pobierania aktywnych pozycji: {str(e)}")
            return []
        
    def _get_risk_data(self, symbol: Optional[str] = None) -> Dict[str, Any]:
        """
        Pobiera aktualne dane o ryzyku.
        
        Args:
            symbol: Opcjonalny symbol do specyficznych danych o ryzyku
            
        Returns:
            Dict zawierający dane o ryzyku
        """
        try:
            risk_report = self.risk_manager.get_risk_report()
            
            # Dodanie danych specyficznych dla symbolu, jeśli istnieją
            if symbol:
                # Pobierz konfigurację dla symbolu
                symbol_config = self.risk_manager.get_symbol_config(symbol)
                if symbol_config:
                    risk_report.update({
                        'symbol_config': symbol_config
                    })
            
            return risk_report
        except Exception as e:
            self.logger.error(f"Błąd podczas pobierania raportu o ryzyku: {str(e)}")
            return {}
        
    def _get_historical_signals(self, symbol: str, signal_type: str, 
                            source: Optional[str] = None, 
                            days: int = 30) -> List[Dict[str, Any]]:
        """
        Pobiera historyczne sygnały podobnego typu.
        
        Args:
            symbol: Symbol instrumentu
            signal_type: Typ sygnału
            source: Opcjonalne źródło sygnału
            days: Liczba dni wstecz
            
        Returns:
            Lista historycznych sygnałów
        """
        try:
            # Pobierz sygnały z repozytorium
            historical_signals = self.signal_repository.get_signals_by_criteria(
                symbol=symbol,
                signal_type=signal_type,
                source=source,
                days=days
            )
            
            return historical_signals
        except Exception as e:
            self.logger.error(f"Błąd podczas pobierania historycznych sygnałów: {str(e)}")
            return []
        
    def _get_recent_signals(self, symbol: str, signal_type: str, 
                        minutes: int = 60) -> List[Dict[str, Any]]:
        """
        Pobiera niedawne sygnały podobnego typu.
        
        Args:
            symbol: Symbol instrumentu
            signal_type: Typ sygnału
            minutes: Liczba minut wstecz
            
        Returns:
            Lista niedawnych sygnałów
        """
        try:
            # Oblicz czas graniczny
            cutoff_time = time.time() - (minutes * 60)
            
            # Pobierz sygnały z repozytorium
            recent_signals = self.signal_repository.get_signals_by_criteria(
                symbol=symbol,
                signal_type=signal_type,
                since_timestamp=cutoff_time
            )
            
            return recent_signals
        except Exception as e:
            self.logger.error(f"Błąd podczas pobierania niedawnych sygnałów: {str(e)}")
            return []
    
    def _save_validation_result(self, signal: Dict[str, Any], 
                            result: Dict[str, Any]) -> bool:
        """
        Zapisuje wynik walidacji do bazy danych.
        
        Args:
            signal: Zwalidowany sygnał
            result: Wynik walidacji
            
        Returns:
            Bool wskazujący czy zapis się powiódł
        """
        try:
            # Przygotuj dane do zapisu
            validation_data = {
                'signal_id': signal.get('id'),
                'symbol': signal.get('symbol'),
                'type': signal.get('type'),
                'timestamp': time.time(),
                'validation_result': result['validation_result'].name,
                'score': result.get('score', 0),
                'rejection_reason': result.get('rejection_reason'),
                'metadata': json.dumps({
                    'risk_assessment': result.get('risk_assessment', {}),
                    'order_limits': result.get('order_limits', {})
                })
            }
            
            # Zapisz do repozytorium
            self.signal_repository.save_validation_result(validation_data)
            return True
        except Exception as e:
            self.logger.error(f"Błąd podczas zapisywania wyniku walidacji: {str(e)}")
            return False


def get_signal_validator() -> SignalValidator:
    """
    Zwraca instancję SignalValidator (Singleton).
    
    Returns:
        Instancja SignalValidator
    """
    return SignalValidator() 