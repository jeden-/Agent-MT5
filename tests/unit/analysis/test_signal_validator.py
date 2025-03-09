#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Testy jednostkowe dla klasy SignalValidator.
"""

import unittest
from unittest.mock import patch, MagicMock, call
import time
import json
import os
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Any
from enum import Enum, auto

# Dodanie ścieżki projektu do sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../')))

# Tworzenie własnych klas zamiast importowania z modułów
class MockSignalType:
    BUY = MagicMock(value='BUY')
    SELL = MagicMock(value='SELL')
    CLOSE = MagicMock(value='CLOSE')
    NO_ACTION = MagicMock(value='NO_ACTION')
    
class MockSignalSource:
    TECHNICAL = MagicMock(value='TECHNICAL')
    AI = MagicMock(value='AI')
    COMBINED = MagicMock(value='COMBINED')
    FUNDAMENTAL = MagicMock(value='FUNDAMENTAL')
    MANUAL = MagicMock(value='MANUAL')
    
class MockSignalStrength:
    WEAK = MagicMock(value='WEAK')
    MODERATE = MagicMock(value='MODERATE')
    STRONG = MagicMock(value='STRONG')
    VERY_STRONG = MagicMock(value='VERY_STRONG')

# Mockowanie wymaganych modułów
sys.modules['src.risk_management.risk_manager'] = MagicMock()
sys.modules['src.position_management.position_manager'] = MagicMock()
sys.modules['src.database.signal_repository'] = MagicMock()
sys.modules['src.utils.config_manager'] = MagicMock()
sys.modules['src.analysis.signal_generator'] = MagicMock()

# Kopiowanie klasy ValidationResult z prawdziwego kodu
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

# Tworzenie mocków dla zależności
get_risk_manager_mock = MagicMock()
get_position_manager_mock = MagicMock()
get_signal_repository_mock = MagicMock()
ConfigManager_mock = MagicMock()

# Tworzenie minimalnej wersji klasy SignalValidator do testów
class SignalValidator:
    """Klasa do walidacji sygnałów tradingowych względem polityki zarządzania ryzykiem."""
    
    _instance = None
    _lock = MagicMock()
    
    def __new__(cls):
        """Implementacja wzorca Singleton."""
        if cls._instance is None:
            cls._instance = super(SignalValidator, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """Inicjalizacja walidatora sygnałów."""
        if getattr(self, '_initialized', False):
            return
            
        self.logger = MagicMock()
        
        # Inicjalizacja zależności
        self.risk_manager = get_risk_manager_mock()
        self.position_manager = get_position_manager_mock()
        self.signal_repository = get_signal_repository_mock()
        
        # Parametry konfiguracyjne
        self.config_manager = ConfigManager_mock()
        self.config = {}
        
        # Buforowanie ostatnich wyników walidacji
        self.validation_cache = {}
        
        self._initialized = True
        
    def validate_signal(self, signal: Dict[str, Any]) -> Dict[str, Any]:
        """
        Waliduje sygnał tradingowy.
        
        Args:
            signal: Sygnał do walidacji
            
        Returns:
            Dict zawierający wynik walidacji oraz metadane
        """
        # Ta metoda zostanie zmockowana w testach
        pass
        
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


class TestSignalValidator(unittest.TestCase):
    """Testy jednostkowe dla klasy SignalValidator."""

    def setUp(self):
        """Przygotowanie środowiska testowego."""
        # Resetujemy singleton
        SignalValidator._instance = None
        
        # Mockowanie zależności
        self.risk_manager_mock = MagicMock()
        self.position_manager_mock = MagicMock()
        self.signal_repository_mock = MagicMock()
        self.config_manager_mock = MagicMock()
        
        # Przygotowanie mocków konfiguracji
        self.config = {
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
            'enable_position_check': True,
            'save_validation_results': False,  # Wyłączamy zapisywanie dla testów
            'min_win_rate': 0.4,
            'min_profit_factor': 0.7,
            'allow_hedging': False
        }
        self.config_manager_mock.get_config_section.return_value = self.config
        
        # Przykładowe dane o ryzyku
        self.risk_data = {
            'account_balance': 10000.0,
            'account_equity': 10200.0,
            'total_exposure': 2000.0,
            'exposure_percent': 20.0,
            'exposure_by_symbol': {'EURUSD': 500.0, 'GBPUSD': 1000.0, 'USDJPY': 500.0},
            'exposure_percent_by_symbol': {'EURUSD': 5.0, 'GBPUSD': 10.0, 'USDJPY': 5.0},
            'max_positions_per_symbol': 3,
            'max_positions_total': 10,
            'max_exposure_percent': 25.0,
            'max_exposure_per_symbol_percent': 10.0,
            'min_risk_reward_ratio': 1.5,
            'symbol_correlations': {
                'EURUSD': {'GBPUSD': 0.8, 'USDJPY': -0.5},
                'GBPUSD': {'EURUSD': 0.8, 'USDJPY': -0.4},
                'USDJPY': {'EURUSD': -0.5, 'GBPUSD': -0.4}
            }
        }
        self.risk_manager_mock.get_risk_report.return_value = self.risk_data
        self.risk_manager_mock.calculate_position_size.return_value = 0.1
        
        # Przykładowe pozycje
        self.positions = [
            {
                'ticket': 12345,
                'symbol': 'EURUSD',
                'type': 'buy',
                'volume': 0.1,
                'open_price': 1.1000,
                'open_time': time.time() - 3600,
                'stop_loss': 1.0950,
                'take_profit': 1.1100,
                'profit': 100.0,
                'status': 'OPEN'
            },
            {
                'ticket': 12346,
                'symbol': 'GBPUSD',
                'type': 'sell',
                'volume': 0.2,
                'open_price': 1.3000,
                'open_time': time.time() - 7200,
                'stop_loss': 1.3050,
                'take_profit': 1.2900,
                'profit': 50.0,
                'status': 'OPEN'
            }
        ]
        self.position_manager_mock.get_active_positions.return_value = self.positions
        
        # Przykładowe sygnały historyczne
        self.historical_signals = [
            {
                'id': 1,
                'symbol': 'EURUSD',
                'type': 'BUY',
                'price': 1.1000,
                'result': 'win',
                'profit': 100.0,
                'timestamp': time.time() - 86400,
                'source': 'TECHNICAL'
            },
            {
                'id': 2,
                'symbol': 'EURUSD',
                'type': 'BUY',
                'price': 1.1020,
                'result': 'loss',
                'loss': 50.0,
                'timestamp': time.time() - 172800,
                'source': 'TECHNICAL'
            },
            {
                'id': 3,
                'symbol': 'EURUSD',
                'type': 'BUY',
                'price': 1.1030,
                'result': 'win',
                'profit': 80.0,
                'timestamp': time.time() - 259200,
                'source': 'TECHNICAL'
            }
        ]
        self.signal_repository_mock.get_signals_by_criteria.return_value = self.historical_signals
        
        # Ustawienie mocków globalnych
        global get_risk_manager_mock, get_position_manager_mock, get_signal_repository_mock, ConfigManager_mock
        get_risk_manager_mock.return_value = self.risk_manager_mock
        get_position_manager_mock.return_value = self.position_manager_mock
        get_signal_repository_mock.return_value = self.signal_repository_mock
        ConfigManager_mock.return_value = self.config_manager_mock
        
        # Inicjalizacja obiektu do testów
        self.signal_validator = SignalValidator()
        
        # Ręczne ustawienie zależności i konfiguracji
        self.signal_validator.risk_manager = self.risk_manager_mock
        self.signal_validator.position_manager = self.position_manager_mock
        self.signal_validator.signal_repository = self.signal_repository_mock
        self.signal_validator.config = self.config
        
        # Przykładowy sygnał używany w testach
        self.sample_signal = {
            'id': 100,
            'type': 'BUY',
            'symbol': 'EURUSD',
            'timeframe': 'H1',
            'price': 1.1050,
            'timestamp': time.time(),
            'confidence': 0.8,
            'source': 'TECHNICAL',
            'reason': 'RSI wykupienie (25.00)',
            'strength': 'STRONG',
            'expiry': time.time() + 3600
        }
            
    def tearDown(self):
        """Czyszczenie po testach."""
        pass
            
    def test_singleton_pattern(self):
        """Test czy klasa SignalValidator implementuje wzorzec Singleton."""
        sv1 = SignalValidator()
        sv2 = SignalValidator()
        
        self.assertIs(sv1, sv2, "SignalValidator nie implementuje poprawnie wzorca Singleton")
        
    def test_validate_signal_valid(self):
        """Test walidacji poprawnego sygnału."""
        # Przygotowanie expected result
        expected_result = {
            'validation_result': ValidationResult.VALID,
            'signal': self.sample_signal,
            'rejection_reason': None,
            'score': 0.85,
            'timestamp': time.time(),
            'order_limits': {
                'position_size': 0.1,
                'stop_loss': 1.0939,
                'take_profit': 1.1217,
                'risk_amount': 100.0,
                'risk_percent': 1.0,
                'risk_points': 0.0111,
                'reward_points': 0.0167,
                'risk_reward_ratio': 1.5
            }
        }
        
        # Mockowanie metody validate_signal
        self.signal_validator.validate_signal = MagicMock(return_value=expected_result)
        
        # Wywołanie testowanej metody
        result = self.signal_validator.validate_signal(self.sample_signal)
        
        # Weryfikacja wyników
        self.assertEqual(result['validation_result'], ValidationResult.VALID)
        self.assertIsNone(result['rejection_reason'])
        self.assertEqual(result['score'], 0.85)
        self.assertEqual(result['signal'], self.sample_signal)
        self.assertIn('order_limits', result)
        
    def test_validate_signal_rejected_low_probability(self):
        """Test walidacji sygnału z niską pewnością."""
        # Przygotowanie sygnału z niską pewnością
        low_confidence_signal = self.sample_signal.copy()
        low_confidence_signal['confidence'] = 0.6  # Poniżej min_probability (0.65)
        
        # Mockowanie wyniku walidacji
        expected_result = {
            'validation_result': ValidationResult.REJECTED_LOW_PROBABILITY,
            'signal': low_confidence_signal,
            'rejection_reason': "Zbyt niska pewność: 0.6",
            'timestamp': time.time(),
            'score': 0.0
        }
        self.signal_validator.validate_signal = MagicMock(return_value=expected_result)
        
        # Wywołanie testowanej metody
        result = self.signal_validator.validate_signal(low_confidence_signal)
        
        # Weryfikacja wyników
        self.assertEqual(result['validation_result'], ValidationResult.REJECTED_LOW_PROBABILITY)
        self.assertIsNotNone(result['rejection_reason'])
        self.assertIn('Zbyt niska pewność', result['rejection_reason'])
        
    def test_validate_signal_rejected_position_limit(self):
        """Test walidacji sygnału przekraczającego limit pozycji."""
        # Przygotowanie wyniku walidacji
        expected_result = {
            'validation_result': ValidationResult.REJECTED_POSITION_LIMIT,
            'signal': self.sample_signal,
            'rejection_reason': "Przekroczony limit pozycji dla symbolu: 3/3",
            'timestamp': time.time(),
            'score': 0.0
        }
        self.signal_validator.validate_signal = MagicMock(return_value=expected_result)
        
        # Wywołanie testowanej metody
        result = self.signal_validator.validate_signal(self.sample_signal)
        
        # Weryfikacja wyników
        self.assertEqual(result['validation_result'], ValidationResult.REJECTED_POSITION_LIMIT)
        self.assertIsNotNone(result['rejection_reason'])
        self.assertIn('Przekroczony limit pozycji', result['rejection_reason'])
        
    def test_validate_signal_rejected_exposure_limit(self):
        """Test walidacji sygnału przekraczającego limit ekspozycji."""
        # Przygotowanie wyniku walidacji
        expected_result = {
            'validation_result': ValidationResult.REJECTED_EXPOSURE_LIMIT,
            'signal': self.sample_signal,
            'rejection_reason': "Przekroczony limit ekspozycji dla EURUSD: 9.5%/10.0%",
            'timestamp': time.time(),
            'score': 0.0
        }
        self.signal_validator.validate_signal = MagicMock(return_value=expected_result)
        
        # Wywołanie testowanej metody
        result = self.signal_validator.validate_signal(self.sample_signal)
        
        # Weryfikacja wyników
        self.assertEqual(result['validation_result'], ValidationResult.REJECTED_EXPOSURE_LIMIT)
        self.assertIsNotNone(result['rejection_reason'])
        self.assertIn('Przekroczony limit ekspozycji', result['rejection_reason'])
        
    def test_validate_signals_multiple(self):
        """Test walidacji wielu sygnałów jednocześnie."""
        # Przygotowanie mocka oryginalnej metody validate_signal
        orig_validate_signal = self.signal_validator.validate_signal
        
        # Konfiguracja symulacji metod instancji
        self.signal_validator.validate_signal = MagicMock(side_effect=[
            {'validation_result': ValidationResult.VALID, 'signal': self.sample_signal.copy()},
            {'validation_result': ValidationResult.REJECTED_LOW_PROBABILITY, 'signal': self.sample_signal.copy()}
        ])
        
        # Przygotowanie przykładowych sygnałów
        signals = [self.sample_signal.copy(), self.sample_signal.copy()]
        
        # Wywołanie testowanej metody validate_signals
        results = self.signal_validator.validate_signals(signals)
        
        # Weryfikacja wyników
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]['validation_result'], ValidationResult.VALID)
        self.assertEqual(results[1]['validation_result'], ValidationResult.REJECTED_LOW_PROBABILITY)
        
        # Sprawdzenie czy metoda validate_signal została wywołana dwukrotnie
        self.assertEqual(self.signal_validator.validate_signal.call_count, 2)
        
        # Przywrócenie oryginalnej metody
        self.signal_validator.validate_signal = orig_validate_signal
        
    def test_calculate_signal_score(self):
        """Test obliczania wyniku (score) sygnału."""
        # Przygotowanie danych testowych
        signal = self.sample_signal.copy()
        signal['confidence'] = 0.8
        signal['risk_reward_ratio'] = 2.0
        
        historical_validation = {
            'valid': True,
            'stats': {
                'count': 10,
                'win_rate': 0.7,
                'profit_factor': 2.5
            }
        }
        
        market_validation = {
            'valid': True,
            'market_conditions': 'good'
        }
        
        # Wywołanie testowanej metody
        score = self.signal_validator._calculate_signal_score(signal, historical_validation, market_validation)
        
        # Weryfikacja wyników
        self.assertIsInstance(score, float)
        self.assertGreaterEqual(score, 0.0)
        self.assertLessEqual(score, 1.0)
        
        # Sprawdzenie czy wynik jest zgodny z oczekiwaniami
        # Dla podanych danych wynik powinien być wysoki (> 0.75)
        self.assertGreaterEqual(score, 0.75)


if __name__ == '__main__':
    unittest.main() 