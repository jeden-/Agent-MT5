#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Testy jednostkowe dla strategii handlowych.
"""

import unittest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import sys
import os

# Dodajemy ścieżkę do głównego katalogu projektu
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.backtest.strategy import (
    TradingStrategy,
    SimpleMovingAverageStrategy,
    RSIStrategy,
    BollingerBandsStrategy,
    MACDStrategy,
    CombinedIndicatorsStrategy,
    StrategyConfig,
    StrategySignal
)
from src.models.signal import SignalType


class TestTradingStrategies(unittest.TestCase):
    """Klasa testowa dla strategii handlowych."""
    
    def setUp(self):
        """Przygotowanie środowiska testowego."""
        # Tworzymy testowe dane dla strategii
        dates = pd.date_range(start='2023-01-01', periods=200, freq='H')
        
        # Dane z trendem wzrostowym
        self.uptrend_data = pd.DataFrame({
            'time': dates,
            'open': np.linspace(100, 150, 200) + np.random.normal(0, 2, 200),
            'high': np.linspace(102, 152, 200) + np.random.normal(0, 2, 200),
            'low': np.linspace(98, 148, 200) + np.random.normal(0, 2, 200),
            'close': np.linspace(101, 151, 200) + np.random.normal(0, 2, 200),
            'volume': np.random.randint(100, 1000, 200)
        })
        
        # Dane z trendem spadkowym
        self.downtrend_data = pd.DataFrame({
            'time': dates,
            'open': np.linspace(150, 100, 200) + np.random.normal(0, 2, 200),
            'high': np.linspace(152, 102, 200) + np.random.normal(0, 2, 200),
            'low': np.linspace(148, 98, 200) + np.random.normal(0, 2, 200),
            'close': np.linspace(151, 101, 200) + np.random.normal(0, 2, 200),
            'volume': np.random.randint(100, 1000, 200)
        })
        
        # Dane neutralne (sideways) z oscylacjami
        x = np.linspace(0, 10, 200)
        self.sideways_data = pd.DataFrame({
            'time': dates,
            'open': np.sin(x) * 10 + 100 + np.random.normal(0, 1, 200),
            'high': np.sin(x) * 10 + 102 + np.random.normal(0, 1, 200),
            'low': np.sin(x) * 10 + 98 + np.random.normal(0, 1, 200),
            'close': np.sin(x) * 10 + 101 + np.random.normal(0, 1, 200),
            'volume': np.random.randint(100, 1000, 200)
        })
        
        # Wspólna konfiguracja dla wszystkich strategii
        self.config = StrategyConfig(
            stop_loss_pips=50,
            take_profit_pips=100,
            position_size_pct=1.0
        )
    
    def test_sma_strategy(self):
        """Test strategii opartej na średnich kroczących."""
        # Tworzymy instancję strategii
        sma_strategy = SimpleMovingAverageStrategy(
            config=self.config,
            fast_period=5,
            slow_period=20
        )
        
        # Testujemy na danych z trendem wzrostowym
        uptrend_signals = sma_strategy.generate_signals(self.uptrend_data)
        
        # Powinniśmy mieć przynajmniej jeden sygnał kupna w trendzie wzrostowym
        buy_signals = [s for s in uptrend_signals if s.signal_type == SignalType.BUY]
        self.assertGreater(len(buy_signals), 0, "Brak sygnałów kupna w trendzie wzrostowym")
        
        # Testujemy na danych z trendem spadkowym
        downtrend_signals = sma_strategy.generate_signals(self.downtrend_data)
        
        # Powinniśmy mieć przynajmniej jeden sygnał sprzedaży w trendzie spadkowym
        sell_signals = [s for s in downtrend_signals if s.signal_type == SignalType.SELL]
        self.assertGreater(len(sell_signals), 0, "Brak sygnałów sprzedaży w trendzie spadkowym")
        
        # Sprawdzamy, czy sygnały mają poprawne atrybuty
        for signal in uptrend_signals + downtrend_signals:
            self.assertIsNotNone(signal.entry_price)
            self.assertIsNotNone(signal.stop_loss)
            self.assertIsNotNone(signal.take_profit)
            self.assertIsNotNone(signal.time)
            self.assertIsNotNone(signal.volume)
            self.assertIsNotNone(signal.risk_reward_ratio)
            
            # Weryfikacja poziomów SL/TP dla sygnałów kupna
            if signal.signal_type == SignalType.BUY:
                self.assertLess(signal.stop_loss, signal.entry_price, "SL powinien być niższy od ceny wejścia dla BUY")
                self.assertGreater(signal.take_profit, signal.entry_price, "TP powinien być wyższy od ceny wejścia dla BUY")
            
            # Weryfikacja poziomów SL/TP dla sygnałów sprzedaży
            if signal.signal_type == SignalType.SELL:
                self.assertGreater(signal.stop_loss, signal.entry_price, "SL powinien być wyższy od ceny wejścia dla SELL")
                self.assertLess(signal.take_profit, signal.entry_price, "TP powinien być niższy od ceny wejścia dla SELL")
    
    def test_rsi_strategy(self):
        """Test strategii opartej na RSI."""
        # Tworzymy instancję strategii
        rsi_strategy = RSIStrategy(
            config=self.config,
            period=14,
            oversold=30,
            overbought=70
        )
        
        # Testujemy statyczną metodę calculate_rsi
        close_prices = self.sideways_data['close']
        rsi_values = RSIStrategy.calculate_rsi(close_prices, 14)
        
        # RSI powinien zawierać wartości między 0 a 100
        self.assertTrue(all(0 <= rsi <= 100 for rsi in rsi_values.dropna()), "Wartości RSI poza zakresem [0, 100]")
        
        # Testujemy generowanie sygnałów na danych z oscylacjami (sideways)
        sideways_signals = rsi_strategy.generate_signals(self.sideways_data)
        
        # W danych oscylacyjnych powinny być zarówno sygnały kupna, jak i sprzedaży
        buy_signals = [s for s in sideways_signals if s.signal_type == SignalType.BUY]
        sell_signals = [s for s in sideways_signals if s.signal_type == SignalType.SELL]
        
        self.assertGreater(len(buy_signals), 0, "Brak sygnałów kupna w danych oscylacyjnych")
        self.assertGreater(len(sell_signals), 0, "Brak sygnałów sprzedaży w danych oscylacyjnych")
        
        # Sprawdzamy, czy sygnały mają poprawne atrybuty
        for signal in sideways_signals:
            self.assertIsNotNone(signal.entry_price)
            self.assertIsNotNone(signal.stop_loss)
            self.assertIsNotNone(signal.take_profit)
            self.assertIsNotNone(signal.time)
    
    def test_bollinger_bands_strategy(self):
        """Test strategii opartej na wstęgach Bollingera."""
        # Tworzymy instancję strategii
        bb_strategy = BollingerBandsStrategy(
            config=self.config,
            period=20,
            std_dev=2.0
        )
        
        # Testujemy na danych z oscylacjami (sideways)
        sideways_signals = bb_strategy.generate_signals(self.sideways_data)
        
        # W danych oscylacyjnych powinny być zarówno sygnały kupna, jak i sprzedaży
        buy_signals = [s for s in sideways_signals if s.signal_type == SignalType.BUY]
        sell_signals = [s for s in sideways_signals if s.signal_type == SignalType.SELL]
        
        self.assertGreater(len(buy_signals), 0, "Brak sygnałów kupna w danych oscylacyjnych")
        self.assertGreater(len(sell_signals), 0, "Brak sygnałów sprzedaży w danych oscylacyjnych")
        
        # Sprawdzamy, czy sygnały mają poprawne atrybuty
        for signal in sideways_signals:
            self.assertIsNotNone(signal.entry_price)
            self.assertIsNotNone(signal.stop_loss)
            self.assertIsNotNone(signal.take_profit)
            self.assertIsNotNone(signal.time)
    
    def test_macd_strategy(self):
        """Test strategii opartej na MACD."""
        # Tworzymy instancję strategii
        macd_strategy = MACDStrategy(
            config=self.config,
            fast_period=12,
            slow_period=26,
            signal_period=9
        )
        
        # Testujemy statyczną metodę calculate_ema
        close_prices = self.uptrend_data['close']
        ema_values = MACDStrategy.calculate_ema(close_prices, 12)
        
        # EMA nie powinno zawierać wartości NaN po okresie inicjalizacji
        self.assertFalse(ema_values.iloc[15:].isna().any(), "EMA zawiera wartości NaN po okresie inicjalizacji")
        
        # Testujemy generowanie sygnałów na danych z trendem wzrostowym
        uptrend_signals = macd_strategy.generate_signals(self.uptrend_data)
        
        # Powinniśmy mieć przynajmniej jeden sygnał kupna w trendzie wzrostowym
        buy_signals = [s for s in uptrend_signals if s.signal_type == SignalType.BUY]
        self.assertGreater(len(buy_signals), 0, "Brak sygnałów kupna w trendzie wzrostowym")
        
        # Testujemy generowanie sygnałów na danych z trendem spadkowym
        downtrend_signals = macd_strategy.generate_signals(self.downtrend_data)
        
        # Powinniśmy mieć przynajmniej jeden sygnał sprzedaży w trendzie spadkowym
        sell_signals = [s for s in downtrend_signals if s.signal_type == SignalType.SELL]
        self.assertGreater(len(sell_signals), 0, "Brak sygnałów sprzedaży w trendzie spadkowym")
    
    def test_combined_indicators_strategy(self):
        """Test strategii opartej na kombinacji wskaźników."""
        # Tworzymy instancję strategii z niestandardowymi wagami
        weights = {
            'trend': 0.3,
            'momentum': 0.3,
            'volatility': 0.2,
            'volume': 0.1,
            'candlestick': 0.1
        }
        
        thresholds = {
            'buy': 0.6,
            'sell': 0.6
        }
        
        combined_strategy = CombinedIndicatorsStrategy(
            config=self.config,
            weights=weights,
            thresholds=thresholds
        )
        
        # Testujemy na danych z trendem wzrostowym
        uptrend_signals = combined_strategy.generate_signals(self.uptrend_data)
        
        # Testujemy na danych z trendem spadkowym
        downtrend_signals = combined_strategy.generate_signals(self.downtrend_data)
        
        # W przypadku strategii kombinowanej możemy nie otrzymać sygnałów w każdym przypadku
        # ze względu na progi, ale sprawdźmy czy sygnały mają poprawne atrybuty
        all_signals = uptrend_signals + downtrend_signals
        
        for signal in all_signals:
            self.assertIsNotNone(signal.entry_price)
            self.assertIsNotNone(signal.stop_loss)
            self.assertIsNotNone(signal.take_profit)
            self.assertIsNotNone(signal.time)
            self.assertIsNotNone(signal.risk_reward_ratio)


if __name__ == '__main__':
    unittest.main() 