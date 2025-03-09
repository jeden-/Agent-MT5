#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Testy jednostkowe dla klasy SignalGenerator.
"""

import unittest
from unittest.mock import patch, MagicMock, call
import time
import json
import os
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Any

# Dodanie ścieżki projektu do sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../')))

# Mockowanie modułów przed ich importem
sys.modules['src.mt5_bridge.mt5_client'] = MagicMock()
sys.modules['src.database.market_data_repository'] = MagicMock()
sys.modules['src.database.signal_repository'] = MagicMock()
sys.modules['src.utils.config_manager'] = MagicMock()
sys.modules['src.analysis.signal_validator'] = MagicMock()
sys.modules['src.analysis.feedback_loop'] = MagicMock()

# Modyfikacja pliku __init__.py dla testów
import src.analysis
src.analysis.SignalValidator = MagicMock()
src.analysis.FeedbackLoop = MagicMock()

# Importy testowanych modułów
with patch('src.analysis.signal_generator.get_market_data_processor'), \
     patch('src.analysis.signal_generator.get_ai_router'), \
     patch('src.analysis.signal_generator.get_signal_repository'), \
     patch('src.analysis.signal_generator.ConfigManager'):
    from src.analysis.signal_generator import (
        SignalGenerator, SignalType, SignalStrength, SignalSource
    )


class TestSignalGenerator(unittest.TestCase):
    """Testy jednostkowe dla klasy SignalGenerator."""

    def setUp(self):
        """Przygotowanie środowiska testowego."""
        # Mockowanie zależności
        self.market_data_processor_mock = MagicMock()
        self.ai_router_mock = MagicMock()
        self.signal_repository_mock = MagicMock()
        self.config_manager_mock = MagicMock()
        
        # Przygotowanie mocków konfiguracji
        self.config = {
            'strategies': ['technical', 'ai', 'combined'],
            'threshold': 0.65,
            'confirmation_count': 2,
            'timeframes': ['M15', 'H1'],
            'use_ml_models': True,
            'signal_expiry': 3600,
            'min_confidence': 0.7,
            'max_signals_per_symbol': 3
        }
        self.config_manager_mock.get_config_section.return_value = self.config
        
        # Patche dla zależności
        self.patches = [
            patch('src.analysis.signal_generator.get_market_data_processor', 
                  return_value=self.market_data_processor_mock),
            patch('src.analysis.signal_generator.get_ai_router', 
                  return_value=self.ai_router_mock),
            patch('src.analysis.signal_generator.get_signal_repository', 
                  return_value=self.signal_repository_mock),
            patch('src.analysis.signal_generator.ConfigManager', 
                  return_value=self.config_manager_mock)
        ]
        
        # Zastosowanie patchy
        for p in self.patches:
            p.start()
            
        # Przygotowanie przykładowych danych rynkowych
        self.sample_market_data = self._get_sample_market_data()
        
        # Przygotowanie przykładowej analizy AI
        self.sample_ai_analysis = self._get_sample_ai_analysis()
        self.ai_router_mock.analyze_market_data.return_value = self.sample_ai_analysis
        
        # Ustawienie symulowanych odpowiedzi dla repozytorium sygnałów
        self.signal_repository_mock.save_signal.return_value = {'success': True, 'id': 123}
        self.signal_repository_mock.get_signals_by_symbol.return_value = [
            {
                'id': 1,
                'type': SignalType.BUY.value,
                'expiry': time.time() + 1000  # Aktywny
            }
        ]
        
        # Ustawienie symulowanych odpowiedzi dla procesora danych rynkowych
        self.market_data_processor_mock.get_multiple_timeframes.return_value = self.sample_market_data
        
        # Inicjalizacja obiektu do testów - przekazujemy mu wszystkie mockowane zależności
        self.signal_generator = SignalGenerator()
        
        # Ręczne ustawienie konfiguracji
        self.signal_generator.config = self.config

        # Ręczne ustawienie zależności
        self.signal_generator.market_data_processor = self.market_data_processor_mock
        self.signal_generator.ai_router = self.ai_router_mock
        self.signal_generator.signal_repository = self.signal_repository_mock
        
        # Reinicjalizacja strategii
        self.signal_generator._initialize_strategies()
            
    def tearDown(self):
        """Czyszczenie po testach."""
        # Zatrzymanie patchy
        for p in self.patches:
            p.stop()
            
    def _get_sample_market_data(self):
        """Przygotowuje przykładowe dane rynkowe do testów."""
        return {
            'success': True,
            'symbol': 'EURUSD',
            'data': {
                'M15': {
                    'candles': [
                        {'time': time.time() - 900, 'open': 1.1000, 'high': 1.1010, 
                         'low': 1.0990, 'close': 1.1005, 'volume': 100},
                        {'time': time.time(), 'open': 1.1005, 'high': 1.1015, 
                         'low': 1.0995, 'close': 1.1010, 'volume': 120}
                    ],
                    'indicators': {
                        'RSI': 25,  # Sygnał kupna (wykupienie)
                        'MACD': 0.0015,
                        'MACD_signal': 0.0010,
                        'BB_upper': 1.1020,
                        'BB_lower': 1.1000,
                        'ATR': 0.0010
                    }
                },
                'H1': {
                    'candles': [
                        {'time': time.time() - 3600, 'open': 1.0980, 'high': 1.1020, 
                         'low': 1.0970, 'close': 1.1000, 'volume': 500},
                        {'time': time.time(), 'open': 1.1000, 'high': 1.1030, 
                         'low': 1.0990, 'close': 1.1010, 'volume': 550}
                    ],
                    'indicators': {
                        'RSI': 75,  # Sygnał sprzedaży (wyprzedanie)
                        'MACD': -0.0005,
                        'MACD_signal': -0.0010,
                        'BB_upper': 1.1030,
                        'BB_lower': 1.0990,
                        'ATR': 0.0030
                    }
                }
            }
        }
        
    def _get_sample_ai_analysis(self):
        """Przygotowuje przykładową analizę AI do testów."""
        return {
            'success': True,
            'models_used': ['claude', 'deepseek'],
            'analysis': {
                'sentiment': 'bullish',
                'trend': 'bullish',
                'signals': [
                    {'action': 'BUY', 'reason': 'Silny trend wzrostowy', 'confidence': 0.85},
                    {'action': 'BUY', 'reason': 'Wsparcie na poziomie 1.1000', 'confidence': 0.78}
                ],
                'insights': ['Wzrost wolumenu', 'Silne wsparcie'],
                'strength': 0.8,
                'confidence_level': 0.82
            }
        }

    def test_singleton_pattern(self):
        """Test czy klasa SignalGenerator implementuje wzorzec Singleton."""
        sg1 = SignalGenerator()
        sg2 = SignalGenerator()
        
        self.assertIs(sg1, sg2, "SignalGenerator nie implementuje poprawnie wzorca Singleton")
        
    def test_initialize_strategies(self):
        """Test inicjalizacji strategii."""
        # Resetuj mockowaną konfigurację, aby zawierała tylko strategie 'technical' i 'ai'
        self.signal_generator.config = {
            'strategies': ['technical', 'ai', 'unknown_strategy']
        }
        
        # Wywołaj metodę inicjalizacji strategii
        self.signal_generator._initialize_strategies()
        
        # Sprawdź, czy strategie zostały zainicjalizowane
        self.assertIn('technical', self.signal_generator.strategies)
        self.assertIn('ai', self.signal_generator.strategies)
        self.assertNotIn('unknown_strategy', self.signal_generator.strategies)
        
    def test_generate_signals_with_market_data_error(self):
        """Test generowania sygnałów, gdy wystąpi błąd pobierania danych rynkowych."""
        # Mock zwracający błąd
        self.market_data_processor_mock.get_multiple_timeframes.return_value = {
            'success': False,
            'error': 'Błąd pobierania danych'
        }
        
        # Wywołanie testowanej metody
        result = self.signal_generator.generate_signals('EURUSD')
        
        # Weryfikacja wyników
        self.assertFalse(result['success'])
        self.assertEqual(result['error'], 'Błąd pobierania danych')
        self.assertEqual(result['signals'], [])
        
    def test_technical_analysis_strategy(self):
        """Test strategii analizy technicznej."""
        # Wywołanie testowanej metody
        signals = self.signal_generator._technical_analysis_strategy('EURUSD', self.sample_market_data)
        
        # Weryfikacja wyników
        self.assertGreater(len(signals), 0, "Strategia powinna generować sygnały")
        
        # Powinien być co najmniej jeden sygnał kupna (z RSI < 30 w M15)
        buy_signals = [s for s in signals if s['type'] == SignalType.BUY.value]
        self.assertGreater(len(buy_signals), 0, "Powinien być co najmniej jeden sygnał kupna")
        
        # Powinien być co najmniej jeden sygnał sprzedaży (z RSI > 70 w H1)
        sell_signals = [s for s in signals if s['type'] == SignalType.SELL.value]
        self.assertGreater(len(sell_signals), 0, "Powinien być co najmniej jeden sygnał sprzedaży")
        
        # Sprawdźmy zawartość sygnału
        for signal in signals:
            self.assertEqual(signal['symbol'], 'EURUSD')
            self.assertIn(signal['timeframe'], ['M15', 'H1'])
            self.assertIn('price', signal)
            self.assertIn('timestamp', signal)
            self.assertIn('confidence', signal)
            self.assertEqual(signal['source'], SignalSource.TECHNICAL.value)
            self.assertIn('reason', signal)
            self.assertIn('strength', signal)
            self.assertIn('expiry', signal)
        
    def test_ai_analysis_strategy(self):
        """Test strategii analizy AI."""
        # Przygotowanie symulowanej odpowiedzi aby uniknąć problemu z None
        # dla wartości price i current_timeframe
        sample_data = self._get_sample_market_data()
        
        # Wywołanie testowanej metody
        signals = self.signal_generator._ai_analysis_strategy('EURUSD', sample_data)
        
        # Weryfikacja wywołania AI routera
        self.ai_router_mock.analyze_market_data.assert_called_once()
            
    def test_determine_signal_strength(self):
        """Test określania siły sygnału na podstawie pewności."""
        # Testowanie różnych poziomów pewności
        self.assertEqual(
            self.signal_generator._determine_signal_strength(0.60), 
            SignalStrength.WEAK.value
        )
        self.assertEqual(
            self.signal_generator._determine_signal_strength(0.70), 
            SignalStrength.MODERATE.value
        )
        self.assertEqual(
            self.signal_generator._determine_signal_strength(0.85), 
            SignalStrength.STRONG.value
        )
        self.assertEqual(
            self.signal_generator._determine_signal_strength(0.95), 
            SignalStrength.VERY_STRONG.value
        )
            
    def test_aggregate_signals(self):
        """Test agregacji i filtrowania sygnałów."""
        # Przygotowanie przykładowych sygnałów
        signals = [
            {
                'type': SignalType.BUY.value,
                'confidence': 0.65,  # Poniżej min_confidence (0.7)
                'price': 1.1000
            },
            {
                'type': SignalType.BUY.value,
                'confidence': 0.75,
                'price': 1.1005
            },
            {
                'type': SignalType.BUY.value,
                'confidence': 0.85,
                'price': 1.1010
            },
            {
                'type': SignalType.SELL.value,
                'confidence': 0.95,
                'price': 1.1015
            }
        ]
        
        # Wywołanie testowanej metody
        result = self.signal_generator._aggregate_signals(signals)
        
        # Weryfikacja wyników
        # Powinny być tylko 3 sygnały (jeden poniżej progu min_confidence)
        self.assertEqual(len(result), 3, "Powinny być tylko 3 sygnały (jeden poniżej progu)")
        
        # Sygnały powinny być posortowane według pewności (malejąco)
        self.assertEqual(result[0]['confidence'], 0.95)
        self.assertEqual(result[1]['confidence'], 0.85)
        self.assertEqual(result[2]['confidence'], 0.75)
        
    def test_save_signal(self):
        """Test zapisywania sygnału do bazy danych."""
        # Przygotowanie przykładowego sygnału
        signal = {
            'type': SignalType.BUY.value,
            'symbol': 'EURUSD',
            'timeframe': 'M15',
            'price': 1.1000,
            'timestamp': time.time(),
            'confidence': 0.80,
            'source': SignalSource.TECHNICAL.value,
            'reason': "Test signal",
            'strength': SignalStrength.STRONG.value,
            'expiry': time.time() + 3600,
            'child_signals': [{'type': SignalType.BUY.value}]  # Ten klucz powinien być usunięty
        }
        
        # Wywołanie testowanej metody
        result = self.signal_generator._save_signal(signal)
        
        # Weryfikacja wyników
        self.assertTrue(result)
        
        # Sprawdź, czy save_signal zostało wywołane
        self.signal_repository_mock.save_signal.assert_called_once()
            
    def test_get_active_signals(self):
        """Test pobierania aktywnych sygnałów."""
        # Ustawienie symulowanej odpowiedzi repozytoriów
        current_time = time.time()
        self.signal_repository_mock.get_signals_by_symbol.return_value = [
            {
                'id': 1,
                'type': SignalType.BUY.value,
                'expiry': current_time + 1000  # Aktywny
            },
            {
                'id': 2,
                'type': SignalType.SELL.value,
                'expiry': current_time - 1000  # Wygasły
            }
        ]
        
        # Wywołanie testowanej metody
        result = self.signal_generator.get_active_signals('EURUSD')
        
        # Weryfikacja wyników
        self.assertTrue(result['success'])
        self.assertEqual(len(result['signals']), 1)  # Tylko jeden sygnał jest aktywny
        self.assertEqual(result['signals'][0]['id'], 1)


if __name__ == '__main__':
    unittest.main() 