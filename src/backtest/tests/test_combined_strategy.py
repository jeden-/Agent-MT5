#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Test dla strategii CombinedIndicatorsStrategy.
"""

import os
import sys
import logging
import unittest
from datetime import datetime, timedelta
from pathlib import Path

# Dodanie ścieżek projektu do sys.path
current_dir = Path(__file__).resolve().parent
project_root = current_dir.parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

import pandas as pd
import numpy as np
from src.backtest.strategy import CombinedIndicatorsStrategy, StrategyConfig, SignalType
from src.utils.logger import setup_logger

# Konfiguracja logowania
logger = setup_logger(__name__)

class TestCombinedIndicatorsStrategy(unittest.TestCase):
    """Testy dla strategii CombinedIndicatorsStrategy."""
    
    def setUp(self):
        """Konfiguracja testów."""
        # Konfiguracja strategii
        self.strategy_config = StrategyConfig(
            stop_loss_pips=20,
            take_profit_pips=30,
            position_size_pct=2.0,
            params={
                # Domyślne wagi wskaźników
                'weights': {
                    'trend': 0.25,
                    'macd': 0.30,
                    'rsi': 0.20,
                    'bb': 0.15,
                    'candle': 0.10
                },
                # Progi decyzyjne
                'thresholds': {
                    'signal_minimum': 0.2,
                    'signal_ratio': 1.2,
                    'rsi_overbought': 65,
                    'rsi_oversold': 35
                },
                # Parametry wskaźników
                'rsi_period': 7,
                'trend_fast_period': 12,
                'trend_slow_period': 26,
                'macd_fast': 12,
                'macd_slow': 26,
                'macd_signal': 9,
                'bb_period': 15,
                'bb_std_dev': 2.0
            }
        )
        
        # Inicjalizacja strategii
        self.strategy = CombinedIndicatorsStrategy(config=self.strategy_config)
        
        # Utworzenie testowych danych historycznych
        self.create_test_data()
    
    def create_test_data(self):
        """Tworzy testowe dane historyczne."""
        # Utworzenie danych cenowych na podstawie losowego ruchu
        np.random.seed(42)  # Ustaw ziarno dla powtarzalności
        
        # Parametry generowania danych
        n_points = 500
        start_price = 1.2000
        volatility = 0.0002
        
        # Generowanie czasu
        now = datetime.now()
        timestamps = [now - timedelta(minutes=15*i) for i in range(n_points)]
        timestamps.reverse()  # Odwróć listę, aby czas szedł od najstarszego do najnowszego
        
        # Generowanie cen
        prices = [start_price]
        for i in range(1, n_points):
            # Losowy ruch cenowy z trendem
            rnd = np.random.normal(0, 1)
            change = volatility * rnd
            
            # Dodaj trend
            if i < n_points // 3:
                # Trend wzrostowy
                change += 0.00002
            elif i < 2 * (n_points // 3):
                # Trend boczny
                change += 0.0
            else:
                # Trend spadkowy
                change -= 0.00002
            
            new_price = prices[-1] * (1 + change)
            prices.append(new_price)
        
        # Tworzenie danych OHLC
        data = []
        for i in range(n_points):
            base_price = prices[i]
            high = base_price * (1 + np.random.uniform(0, volatility))
            low = base_price * (1 - np.random.uniform(0, volatility))
            
            # W zależności od kierunku, open i close będą różne
            if i > 0 and prices[i] > prices[i-1]:
                # Świeca wzrostowa
                open_price = base_price * (1 - np.random.uniform(0, volatility*0.5))
                close_price = base_price * (1 + np.random.uniform(0, volatility*0.5))
            else:
                # Świeca spadkowa
                open_price = base_price * (1 + np.random.uniform(0, volatility*0.5))
                close_price = base_price * (1 - np.random.uniform(0, volatility*0.5))
            
            # Upewnij się, że high > open, close i low < open, close
            high = max(high, open_price, close_price)
            low = min(low, open_price, close_price)
            
            # Dodaj punkt danych
            data.append({
                'time': timestamps[i],
                'open': open_price,
                'high': high,
                'low': low,
                'close': close_price,
                'volume': np.random.randint(100, 1000),
                'symbol': 'EURUSD',
                'timeframe': 'M15'
            })
        
        # Utworzenie DataFrame
        self.test_data = pd.DataFrame(data)
    
    def test_strategy_initialization(self):
        """Test inicjalizacji strategii."""
        self.assertEqual(self.strategy.name, "CombinedIndicators")
        self.assertEqual(self.strategy.weights['trend'], 0.25)
        self.assertEqual(self.strategy.weights['macd'], 0.30)
        self.assertEqual(self.strategy.weights['rsi'], 0.20)
        self.assertEqual(self.strategy.weights['bb'], 0.15)
        self.assertEqual(self.strategy.weights['candle'], 0.10)
        
        self.assertEqual(self.strategy.thresholds['signal_minimum'], 0.2)
        self.assertEqual(self.strategy.thresholds['rsi_overbought'], 65)
        self.assertEqual(self.strategy.thresholds['rsi_oversold'], 35)
        
        self.assertEqual(self.strategy.rsi_period, 7)
        self.assertEqual(self.strategy.trend_fast_period, 12)
        self.assertEqual(self.strategy.trend_slow_period, 26)
    
    def test_calculate_indicators(self):
        """Test obliczania wskaźników."""
        data_with_indicators = self.strategy._calculate_indicators(self.test_data)
        
        # Sprawdź czy wskaźniki zostały dodane
        self.assertIn('ema_fast', data_with_indicators.columns)
        self.assertIn('ema_slow', data_with_indicators.columns)
        self.assertIn('rsi', data_with_indicators.columns)
        self.assertIn('macd', data_with_indicators.columns)
        self.assertIn('macd_signal', data_with_indicators.columns)
        self.assertIn('bb_middle', data_with_indicators.columns)
        self.assertIn('bb_upper', data_with_indicators.columns)
        self.assertIn('bb_lower', data_with_indicators.columns)
        
        # Sprawdź formacje świecowe
        self.assertIn('bullish_engulfing', data_with_indicators.columns)
        self.assertIn('bearish_engulfing', data_with_indicators.columns)
        self.assertIn('hammer', data_with_indicators.columns)
        self.assertIn('shooting_star', data_with_indicators.columns)
    
    def test_analyze_indicators(self):
        """Test analizy wskaźników."""
        data_with_indicators = self.strategy._calculate_indicators(self.test_data)
        
        # Testuj dla kilku punktów danych
        for index in [50, 100, 200, 300, 400]:
            signals, confidence = self.strategy._analyze_indicators(data_with_indicators, index)
            
            # Sprawdź czy są wszystkie oczekiwane klucze
            self.assertIn('trend', signals)
            self.assertIn('macd', signals)
            self.assertIn('rsi', signals)
            self.assertIn('bb', signals)
            self.assertIn('candle', signals)
            
            self.assertIn('trend', confidence)
            self.assertIn('macd', confidence)
            self.assertIn('rsi', confidence)
            self.assertIn('bb', confidence)
            self.assertIn('candle', confidence)
            
            # Sprawdź czy sygnały mają poprawny typ
            for key, value in signals.items():
                self.assertIn(value, ["BUY", "SELL", "NEUTRAL"])
            
            # Sprawdź czy pewności są w zakresie [0, 1]
            for key, value in confidence.items():
                self.assertGreaterEqual(value, 0.0)
                self.assertLessEqual(value, 1.0)
    
    def test_determine_final_signal(self):
        """Test ustalania finalnego sygnału."""
        # Testuj przypadek z przewagą sygnałów BUY
        signals_buy = {
            'trend': "BUY",
            'macd': "BUY",
            'rsi': "NEUTRAL",
            'bb': "BUY",
            'candle': "NEUTRAL"
        }
        confidence_buy = {
            'trend': 0.6,
            'macd': 0.7,
            'rsi': 0.5,
            'bb': 0.8,
            'candle': 0.5
        }
        signal_type, confidence = self.strategy._determine_final_signal(signals_buy, confidence_buy)
        self.assertEqual(signal_type, "BUY")
        self.assertGreaterEqual(confidence, 0.45)
        
        # Testuj przypadek z przewagą sygnałów SELL
        signals_sell = {
            'trend': "SELL",
            'macd': "SELL",
            'rsi': "SELL",
            'bb': "NEUTRAL",
            'candle': "NEUTRAL"
        }
        confidence_sell = {
            'trend': 0.7,
            'macd': 0.8,
            'rsi': 0.9,
            'bb': 0.5,
            'candle': 0.5
        }
        signal_type, confidence = self.strategy._determine_final_signal(signals_sell, confidence_sell)
        self.assertEqual(signal_type, "SELL")
        self.assertGreaterEqual(confidence, 0.45)
        
        # Testuj przypadek z równoważnymi sygnałami
        signals_neutral = {
            'trend': "BUY",
            'macd': "SELL",
            'rsi': "BUY",
            'bb': "SELL",
            'candle': "NEUTRAL"
        }
        confidence_neutral = {
            'trend': 0.6,
            'macd': 0.6,
            'rsi': 0.6,
            'bb': 0.6,
            'candle': 0.5
        }
        signal_type, confidence = self.strategy._determine_final_signal(signals_neutral, confidence_neutral)
        # Tu mogą być różne wyniki, w zależności od implementacji, więc sprawdzamy tylko czy confidence jest liczbą
        self.assertIsInstance(confidence, float)
    
    def test_generate_signals(self):
        """Test generowania sygnałów."""
        signals = self.strategy.generate_signals(self.test_data)
        
        # Sprawdź czy funkcja zwraca listę
        self.assertIsInstance(signals, list)
        
        # Sprawdź czy są jakieś sygnały
        self.assertGreater(len(signals), 0)
        
        # Sprawdź strukturę pierwszego sygnału
        if signals:
            signal = signals[0]
            self.assertIn(signal.signal_type, [SignalType.BUY, SignalType.SELL])
            self.assertEqual(signal.symbol, "EURUSD")
            self.assertEqual(signal.timeframe, "M15")
            self.assertIsNotNone(signal.entry_price)
            self.assertIsNotNone(signal.stop_loss)
            self.assertIsNotNone(signal.take_profit)
            
            # Sprawdź komentarz
            self.assertTrue(signal.comment.startswith("COMBINED_"))
            
            # Sprawdź czy SL i TP są poprawnie ustawione
            if signal.signal_type == SignalType.BUY:
                self.assertLess(signal.stop_loss, signal.entry_price)
                self.assertGreater(signal.take_profit, signal.entry_price)
            else:
                self.assertGreater(signal.stop_loss, signal.entry_price)
                self.assertLess(signal.take_profit, signal.entry_price)

if __name__ == "__main__":
    unittest.main() 