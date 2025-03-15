#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Testy jednostkowe dla modułu strategii tradingowych.
"""

import unittest
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from typing import List

from src.backtest.strategy import (
    TradingStrategy, StrategyConfig, StrategySignal,
    SimpleMovingAverageStrategy, RSIStrategy, BollingerBandsStrategy, MACDStrategy
)
from src.models.signal import SignalType


def create_test_data(symbol: str = "EURUSD", timeframe: str = "H1", 
                     periods: int = 200, trend_type: str = "up") -> pd.DataFrame:
    """
    Tworzy dane testowe do testowania strategii.
    
    Args:
        symbol: Symbol instrumentu.
        timeframe: Interwał czasowy.
        periods: Liczba okresów.
        trend_type: Typ trendu ('up', 'down', 'sideways', 'volatile').
    
    Returns:
        DataFrame z danymi testowymi.
    """
    # Ustalenie daty początkowej
    start_date = datetime(2022, 1, 1)
    
    # Tworzenie wartości czasowych
    dates = [start_date + timedelta(hours=i) for i in range(periods)]
    
    # Generowanie danych cenowych w zależności od typu trendu
    if trend_type == "up":
        # Trend wzrostowy
        close = np.linspace(100, 120, periods) + np.random.normal(0, 1, periods)
    elif trend_type == "down":
        # Trend spadkowy
        close = np.linspace(120, 100, periods) + np.random.normal(0, 1, periods)
    elif trend_type == "sideways":
        # Trend boczny
        close = np.ones(periods) * 110 + np.random.normal(0, 2, periods)
    elif trend_type == "volatile":
        # Trend zmienny
        close = 110 + 10 * np.sin(np.linspace(0, 10, periods)) + np.random.normal(0, 3, periods)
    else:
        # Domyślnie trend wzrostowy
        close = np.linspace(100, 120, periods) + np.random.normal(0, 1, periods)
    
    # Generowanie pozostałych danych OHLC
    high = close + np.random.uniform(0.5, 2, periods)
    low = close - np.random.uniform(0.5, 2, periods)
    open_prices = close - np.random.uniform(-1, 1, periods)
    
    # Generowanie wolumenu
    volume = np.random.randint(100, 1000, periods)
    
    # Tworzenie DataFrame
    df = pd.DataFrame({
        'time': dates,
        'open': open_prices,
        'high': high,
        'low': low,
        'close': close,
        'volume': volume,
        'symbol': symbol,
        'timeframe': timeframe
    })
    
    return df


class TestTradingStrategy(unittest.TestCase):
    """Testy dla bazowej klasy TradingStrategy."""
    
    def test_calculate_position_size(self):
        """Test obliczania wielkości pozycji."""
        # Tworzenie strategii
        config = StrategyConfig()
        
        # Implementacja prostej strategii testowej
        class TestStrategy(TradingStrategy):
            def generate_signals(self, data):
                return []
        
        strategy = TestStrategy(config)
        
        # Test dla różnych instrumentów
        test_cases = [
            # account_balance, risk_pct, entry_price, stop_loss, symbol, expected_min
            (10000, 1, 1.1000, 1.0950, "EURUSD", 0.01),  # Para walutowa
            (10000, 1, 1800, 1790, "XAUUSD", 0.01),  # Złoto
            (10000, 1, 15000, 14900, "US500", 0.01),  # Indeks
            (10000, 1, 116.00, 115.50, "USDJPY", 0.01),  # JPY
        ]
        
        for balance, risk, entry, sl, symbol, expected_min in test_cases:
            position_size = strategy.calculate_position_size(balance, risk, entry, sl, symbol)
            self.assertGreaterEqual(position_size, expected_min, f"Pozycja dla {symbol} zbyt mała")
            self.assertLessEqual(position_size, balance * 0.05, f"Pozycja dla {symbol} zbyt duża")


class TestSimpleMovingAverageStrategy(unittest.TestCase):
    """Testy dla strategii opartej na średnich kroczących."""
    
    def setUp(self):
        """Przygotowanie danych i strategii do testów."""
        self.config = StrategyConfig(stop_loss_pips=50, take_profit_pips=100)
        self.strategy = SimpleMovingAverageStrategy(self.config, fast_period=5, slow_period=20)
        
        # Dane dla trendu wzrostowego
        self.up_trend_data = create_test_data(trend_type="up")
        
        # Dane dla trendu spadkowego
        self.down_trend_data = create_test_data(trend_type="down")
    
    def test_generate_signals_up_trend(self):
        """Test generowania sygnałów w trendzie wzrostowym."""
        signals = self.strategy.generate_signals(self.up_trend_data)
        
        # Powinny pojawić się sygnały kupna
        buy_signals = [s for s in signals if s.signal_type == SignalType.BUY]
        self.assertGreater(len(buy_signals), 0, "Brak sygnałów BUY w trendzie wzrostowym")
    
    def test_generate_signals_down_trend(self):
        """Test generowania sygnałów w trendzie spadkowym."""
        signals = self.strategy.generate_signals(self.down_trend_data)
        
        # Powinny pojawić się sygnały sprzedaży
        sell_signals = [s for s in signals if s.signal_type == SignalType.SELL]
        self.assertGreater(len(sell_signals), 0, "Brak sygnałów SELL w trendzie spadkowym")
    
    def test_signal_properties(self):
        """Test właściwości generowanych sygnałów."""
        signals = self.strategy.generate_signals(self.up_trend_data)
        
        for signal in signals:
            # Sprawdzenie atrybutów sygnału
            self.assertEqual(signal.symbol, "EURUSD")
            self.assertEqual(signal.timeframe, "H1")
            
            # Sprawdzenie poziomów SL/TP
            if signal.signal_type == SignalType.BUY:
                self.assertLess(signal.stop_loss, signal.entry_price)
                self.assertGreater(signal.take_profit, signal.entry_price)
            else:  # SELL
                self.assertGreater(signal.stop_loss, signal.entry_price)
                self.assertLess(signal.take_profit, signal.entry_price)
            
            # Sprawdzenie risk/reward ratio
            self.assertIsNotNone(signal.risk_reward_ratio)
            self.assertGreater(signal.risk_reward_ratio, 0)


class TestRSIStrategy(unittest.TestCase):
    """Testy dla strategii opartej na RSI."""
    
    def setUp(self):
        """Przygotowanie danych i strategii do testów."""
        self.config = StrategyConfig(stop_loss_pips=50, take_profit_pips=100)
        self.strategy = RSIStrategy(self.config, period=14, oversold=30, overbought=70)
        
        # Dane dla trendu zmiennego, który powinien generować sygnały RSI
        self.volatile_data = create_test_data(trend_type="volatile", periods=300)
    
    def test_calculate_rsi(self):
        """Test obliczania wskaźnika RSI."""
        rsi = RSIStrategy.calculate_rsi(self.volatile_data['close'], period=14)
        
        # RSI powinien być między 0 a 100
        self.assertTrue((rsi.dropna() >= 0).all() and (rsi.dropna() <= 100).all())
        
        # Powinny być wartości zarówno niskie jak i wysokie
        self.assertTrue((rsi.dropna() < 30).any(), "Brak wartości RSI poniżej 30")
        self.assertTrue((rsi.dropna() > 70).any(), "Brak wartości RSI powyżej 70")
    
    def test_generate_signals(self):
        """Test generowania sygnałów na podstawie RSI."""
        signals = self.strategy.generate_signals(self.volatile_data)
        
        # W zmiennym trendzie powinny pojawić się sygnały obu typów
        buy_signals = [s for s in signals if s.signal_type == SignalType.BUY]
        sell_signals = [s for s in signals if s.signal_type == SignalType.SELL]
        
        self.assertGreater(len(buy_signals), 0, "Brak sygnałów BUY")
        self.assertGreater(len(sell_signals), 0, "Brak sygnałów SELL")


class TestBollingerBandsStrategy(unittest.TestCase):
    """Testy dla strategii opartej na Wstęgach Bollingera."""
    
    def setUp(self):
        """Przygotowanie danych i strategii do testów."""
        self.config = StrategyConfig(stop_loss_pips=50, take_profit_pips=100)
        self.strategy = BollingerBandsStrategy(self.config, period=20, std_dev=2.0)
        
        # Dane dla trendu zmiennego, który powinien generować sygnały BB
        self.volatile_data = create_test_data(trend_type="volatile", periods=300)
    
    def test_generate_signals(self):
        """Test generowania sygnałów na podstawie Wstęg Bollingera."""
        signals = self.strategy.generate_signals(self.volatile_data)
        
        # W zmiennym trendzie powinny pojawić się sygnały obu typów
        buy_signals = [s for s in signals if s.signal_type == SignalType.BUY]
        sell_signals = [s for s in signals if s.signal_type == SignalType.SELL]
        
        self.assertGreater(len(buy_signals), 0, "Brak sygnałów BUY")
        self.assertGreater(len(sell_signals), 0, "Brak sygnałów SELL")


class TestMACDStrategy(unittest.TestCase):
    """Testy dla strategii opartej na MACD."""
    
    def setUp(self):
        """Przygotowanie danych i strategii do testów."""
        self.config = StrategyConfig(stop_loss_pips=50, take_profit_pips=100)
        self.strategy = MACDStrategy(self.config, fast_period=12, slow_period=26, signal_period=9)
        
        # Dane dla trendu wzrostowego
        self.up_trend_data = create_test_data(trend_type="up", periods=300)
        
        # Dane dla trendu spadkowego
        self.down_trend_data = create_test_data(trend_type="down", periods=300)
    
    def test_calculate_ema(self):
        """Test obliczania średniej wykładniczej."""
        ema = MACDStrategy.calculate_ema(self.up_trend_data['close'], period=12)
        
        # EMA powinna być zbliżona do ceny, ale wygładzona
        self.assertLess(ema.std(), self.up_trend_data['close'].std())
        
        # Powinna mieć podobną średnią
        self.assertAlmostEqual(ema.mean(), self.up_trend_data['close'].mean(), delta=5)
    
    def test_generate_signals_up_trend(self):
        """Test generowania sygnałów w trendzie wzrostowym."""
        signals = self.strategy.generate_signals(self.up_trend_data)
        
        # W trendzie wzrostowym powinny przeważać sygnały kupna
        buy_signals = [s for s in signals if s.signal_type == SignalType.BUY]
        sell_signals = [s for s in signals if s.signal_type == SignalType.SELL]
        
        self.assertGreater(len(buy_signals), 0, "Brak sygnałów BUY w trendzie wzrostowym")
    
    def test_generate_signals_down_trend(self):
        """Test generowania sygnałów w trendzie spadkowym."""
        signals = self.strategy.generate_signals(self.down_trend_data)
        
        # W trendzie spadkowym powinny przeważać sygnały sprzedaży
        buy_signals = [s for s in signals if s.signal_type == SignalType.BUY]
        sell_signals = [s for s in signals if s.signal_type == SignalType.SELL]
        
        self.assertGreater(len(sell_signals), 0, "Brak sygnałów SELL w trendzie spadkowym")


if __name__ == '__main__':
    unittest.main() 