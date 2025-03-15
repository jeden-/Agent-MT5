#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Moduł zawierający interfejs strategii tradingowych i podstawowe implementacje dla backtestingu.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Union
import logging
import pandas as pd
import numpy as np

from src.models.signal import SignalType


@dataclass
class StrategyConfig:
    """Konfiguracja strategii tradingowej."""
    # Parametry pozycji
    stop_loss_pips: float = 50
    take_profit_pips: float = 100
    position_size_pct: float = 1.0  # Procent kapitału na jedną pozycję
    max_positions: int = 5  # Maksymalna liczba jednoczesnych pozycji
    
    # Parametry ryzyka
    max_daily_loss_pct: float = 3.0  # Maksymalna dzienna strata
    max_open_risk_pct: float = 5.0  # Maksymalne ryzyko otwartych pozycji
    
    # Dodatkowe parametry
    allow_overnight: bool = True  # Czy pozycje mogą być otwarte na noc
    allow_weekend: bool = True  # Czy pozycje mogą być otwarte na weekend
    
    # Parametry specyficzne dla strategii
    params: Dict = None
    
    def __post_init__(self):
        if self.params is None:
            self.params = {}


@dataclass
class StrategySignal:
    """Sygnał wygenerowany przez strategię."""
    symbol: str
    timeframe: str
    signal_type: SignalType
    entry_price: float
    stop_loss: float
    take_profit: float
    time: datetime
    volume: float = 0.01
    comment: str = ""
    
    # Dodatkowe informacje dla analizy
    risk_reward_ratio: float = None
    
    def __post_init__(self):
        if self.risk_reward_ratio is None and self.stop_loss and self.take_profit:
            # Obliczenie stosunku zysku do ryzyka
            if self.signal_type == SignalType.BUY:
                risk = self.entry_price - self.stop_loss
                reward = self.take_profit - self.entry_price
            else:  # SELL
                risk = self.stop_loss - self.entry_price
                reward = self.entry_price - self.take_profit
            
            if risk > 0:
                self.risk_reward_ratio = reward / risk
            else:
                self.risk_reward_ratio = 0


class TradingStrategy(ABC):
    """
    Abstrakcyjny interfejs dla strategii tradingowych.
    Wszystkie strategie powinny dziedziczyć po tej klasie i implementować metodę generate_signals.
    """
    
    def __init__(self, config: Optional[StrategyConfig] = None):
        """
        Inicjalizacja strategii.
        
        Args:
            config: Konfiguracja strategii. Jeśli None, używana jest domyślna konfiguracja.
        """
        self.config = config or StrategyConfig()
        self.logger = logging.getLogger(f"{self.__class__.__name__}")
        self.name = self.__class__.__name__
    
    @abstractmethod
    def generate_signals(self, data: pd.DataFrame) -> List[StrategySignal]:
        """
        Generowanie sygnałów tradingowych na podstawie danych historycznych.
        
        Args:
            data: DataFrame z danymi historycznymi. Powinien zawierać kolumny:
                 'time', 'open', 'high', 'low', 'close', 'volume'.
        
        Returns:
            Lista sygnałów tradingowych.
        """
        pass
    
    def calculate_position_size(self, account_balance: float, risk_pct: float, entry_price: float, 
                               stop_loss: float, symbol: str) -> float:
        """
        Obliczanie wielkości pozycji na podstawie zarządzania ryzykiem.
        
        Args:
            account_balance: Saldo konta.
            risk_pct: Procent salda, który można zaryzykować.
            entry_price: Cena wejścia.
            stop_loss: Poziom stop loss.
            symbol: Symbol instrumentu.
        
        Returns:
            Wielkość pozycji (wolumen).
        """
        risk_amount = account_balance * (risk_pct / 100)
        pip_value = 0.0001  # Domyślna wartość pipa dla par walutowych
        
        # Dla indeksów i innych instrumentów wartość pipa może być inna
        if symbol.endswith('JPY'):
            pip_value = 0.01
        elif 'XAU' in symbol or 'GOLD' in symbol:
            pip_value = 0.01
        elif 'US30' in symbol or 'US500' in symbol or 'USTEC' in symbol:
            pip_value = 0.01
        
        pip_distance = abs(entry_price - stop_loss) / pip_value
        
        if pip_distance == 0:
            self.logger.warning(f"Zeros pip distance for {symbol}. Entry: {entry_price}, SL: {stop_loss}")
            return 0.01  # Minimalny wolumen
        
        # Przybliżona wartość 1 lota
        lot_value = 100000  # Dla par walutowych
        if 'XAU' in symbol or 'GOLD' in symbol:
            lot_value = 100  # Dla złota (uncje)
        elif 'US30' in symbol or 'US500' in symbol or 'USTEC' in symbol:
            lot_value = 1  # Dla indeksów (kontrakty)
        
        # Obliczenie wolumenu
        position_size = risk_amount / (pip_distance * pip_value * lot_value)
        
        # Ograniczenie do maksymalnej wielkości pozycji
        max_position = account_balance * (self.config.position_size_pct / 100) / (entry_price * lot_value)
        position_size = min(position_size, max_position)
        
        # Zaokrąglenie do 2 miejsc po przecinku (standardowa dokładność MT5)
        position_size = round(position_size, 2)
        
        # Minimalna wielkość pozycji
        return max(0.01, position_size)


class SimpleMovingAverageStrategy(TradingStrategy):
    """
    Prosta strategia oparta na przecięciu średnich kroczących.
    Generuje sygnał BUY gdy szybka MA przebija wolną MA od dołu.
    Generuje sygnał SELL gdy szybka MA przebija wolną MA od góry.
    """
    
    def __init__(self, config: Optional[StrategyConfig] = None, fast_period: int = 10, slow_period: int = 30):
        """
        Inicjalizacja strategii.
        
        Args:
            config: Konfiguracja strategii.
            fast_period: Okres szybkiej średniej kroczącej.
            slow_period: Okres wolnej średniej kroczącej.
        """
        super().__init__(config)
        self.fast_period = fast_period
        self.slow_period = slow_period
        
        if config and config.params:
            self.fast_period = config.params.get('fast_period', self.fast_period)
            self.slow_period = config.params.get('slow_period', self.slow_period)
        
        self.name = f"SMA_{self.fast_period}_{self.slow_period}"
    
    def generate_signals(self, data: pd.DataFrame) -> List[StrategySignal]:
        """
        Generowanie sygnałów na podstawie przecięcia średnich kroczących.
        
        Args:
            data: DataFrame z danymi historycznymi.
        
        Returns:
            Lista sygnałów tradingowych.
        """
        if len(data) < self.slow_period + 10:
            self.logger.warning("Insufficient data for SMA strategy")
            return []
        
        # Kopiowanie danych, aby uniknąć modyfikacji oryginalnego DataFrame
        df = data.copy()
        
        # Obliczanie średnich kroczących
        df['fast_ma'] = df['close'].rolling(window=self.fast_period).mean()
        df['slow_ma'] = df['close'].rolling(window=self.slow_period).mean()
        
        # Generowanie sygnałów na podstawie przecięcia
        df['fast_ma_prev'] = df['fast_ma'].shift(1)
        df['slow_ma_prev'] = df['slow_ma'].shift(1)
        
        # Sygnał BUY: fast_ma przebija slow_ma od dołu
        df['buy_signal'] = (df['fast_ma_prev'] <= df['slow_ma_prev']) & (df['fast_ma'] > df['slow_ma'])
        
        # Sygnał SELL: fast_ma przebija slow_ma od góry
        df['sell_signal'] = (df['fast_ma_prev'] >= df['slow_ma_prev']) & (df['fast_ma'] < df['slow_ma'])
        
        # Usunięcie wierszy z brakującymi wartościami
        df = df.dropna()
        
        signals = []
        stop_loss_pips = self.config.stop_loss_pips
        take_profit_pips = self.config.take_profit_pips
        
        # Przetwarzanie sygnałów BUY
        buy_signals = df[df['buy_signal']].copy()
        for idx, row in buy_signals.iterrows():
            entry_price = row['close']
            stop_loss = entry_price - (stop_loss_pips * 0.0001)
            take_profit = entry_price + (take_profit_pips * 0.0001)
            
            signal = StrategySignal(
                symbol=data['symbol'].iloc[0] if 'symbol' in data.columns else "UNKNOWN",
                timeframe=data['timeframe'].iloc[0] if 'timeframe' in data.columns else "UNKNOWN",
                signal_type=SignalType.BUY,
                entry_price=entry_price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                time=row['time'],
                comment=f"SMA_{self.fast_period}_{self.slow_period}_BUY"
            )
            signals.append(signal)
        
        # Przetwarzanie sygnałów SELL
        sell_signals = df[df['sell_signal']].copy()
        for idx, row in sell_signals.iterrows():
            entry_price = row['close']
            stop_loss = entry_price + (stop_loss_pips * 0.0001)
            take_profit = entry_price - (take_profit_pips * 0.0001)
            
            signal = StrategySignal(
                symbol=data['symbol'].iloc[0] if 'symbol' in data.columns else "UNKNOWN",
                timeframe=data['timeframe'].iloc[0] if 'timeframe' in data.columns else "UNKNOWN",
                signal_type=SignalType.SELL,
                entry_price=entry_price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                time=row['time'],
                comment=f"SMA_{self.fast_period}_{self.slow_period}_SELL"
            )
            signals.append(signal)
        
        return signals


class RSIStrategy(TradingStrategy):
    """
    Strategia oparta na wskaźniku Relative Strength Index (RSI).
    Generuje sygnał BUY gdy RSI jest poniżej poziomu wyprzedania.
    Generuje sygnał SELL gdy RSI jest powyżej poziomu wykupienia.
    """
    
    def __init__(self, config: Optional[StrategyConfig] = None, 
                 period: int = 14, 
                 oversold: int = 30, 
                 overbought: int = 70):
        """
        Inicjalizacja strategii.
        
        Args:
            config: Konfiguracja strategii.
            period: Okres RSI.
            oversold: Poziom wyprzedania (domyślnie 30).
            overbought: Poziom wykupienia (domyślnie 70).
        """
        super().__init__(config)
        self.period = period
        self.oversold = oversold
        self.overbought = overbought
        
        if config and config.params:
            self.period = config.params.get('period', self.period)
            self.oversold = config.params.get('oversold', self.oversold)
            self.overbought = config.params.get('overbought', self.overbought)
        
        self.name = f"RSI_{self.period}_{self.oversold}_{self.overbought}"
    
    @staticmethod
    def calculate_rsi(data: pd.Series, period: int = 14) -> pd.Series:
        """
        Obliczanie wskaźnika RSI.
        
        Args:
            data: Seria danych cenowych.
            period: Okres RSI.
        
        Returns:
            Seria wartości RSI.
        """
        # Obliczanie zmian cen
        delta = data.diff()
        
        # Rozdzielenie na zyski i straty
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        
        # Obliczanie średnich z danego okresu
        avg_gain = gain.rolling(window=period).mean()
        avg_loss = loss.rolling(window=period).mean()
        
        # Obliczanie współczynnika RS (Relative Strength)
        rs = avg_gain / avg_loss
        
        # Obliczanie RSI
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    def generate_signals(self, data: pd.DataFrame) -> List[StrategySignal]:
        """
        Generowanie sygnałów na podstawie wskaźnika RSI.
        
        Args:
            data: DataFrame z danymi historycznymi.
        
        Returns:
            Lista sygnałów tradingowych.
        """
        if len(data) < self.period + 10:
            self.logger.warning("Insufficient data for RSI strategy")
            return []
        
        # Kopiowanie danych, aby uniknąć modyfikacji oryginalnego DataFrame
        df = data.copy()
        
        # Obliczanie RSI
        df['rsi'] = self.calculate_rsi(df['close'], self.period)
        
        # Przesunięcie RSI o 1 okres (poprzednia wartość)
        df['rsi_prev'] = df['rsi'].shift(1)
        
        # Generowanie sygnałów
        # Sygnał BUY: RSI przekracza poziom wyprzedania od dołu
        df['buy_signal'] = (df['rsi_prev'] < self.oversold) & (df['rsi'] >= self.oversold)
        
        # Sygnał SELL: RSI przekracza poziom wykupienia od góry
        df['sell_signal'] = (df['rsi_prev'] > self.overbought) & (df['rsi'] <= self.overbought)
        
        # Usunięcie wierszy z brakującymi wartościami
        df = df.dropna()
        
        signals = []
        stop_loss_pips = self.config.stop_loss_pips
        take_profit_pips = self.config.take_profit_pips
        
        # Przetwarzanie sygnałów BUY
        buy_signals = df[df['buy_signal']].copy()
        for idx, row in buy_signals.iterrows():
            entry_price = row['close']
            stop_loss = entry_price - (stop_loss_pips * 0.0001)
            take_profit = entry_price + (take_profit_pips * 0.0001)
            
            signal = StrategySignal(
                symbol=data['symbol'].iloc[0] if 'symbol' in data.columns else "UNKNOWN",
                timeframe=data['timeframe'].iloc[0] if 'timeframe' in data.columns else "UNKNOWN",
                signal_type=SignalType.BUY,
                entry_price=entry_price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                time=row['time'],
                comment=f"RSI_{self.period}_BUY"
            )
            signals.append(signal)
        
        # Przetwarzanie sygnałów SELL
        sell_signals = df[df['sell_signal']].copy()
        for idx, row in sell_signals.iterrows():
            entry_price = row['close']
            stop_loss = entry_price + (stop_loss_pips * 0.0001)
            take_profit = entry_price - (take_profit_pips * 0.0001)
            
            signal = StrategySignal(
                symbol=data['symbol'].iloc[0] if 'symbol' in data.columns else "UNKNOWN",
                timeframe=data['timeframe'].iloc[0] if 'timeframe' in data.columns else "UNKNOWN",
                signal_type=SignalType.SELL,
                entry_price=entry_price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                time=row['time'],
                comment=f"RSI_{self.period}_SELL"
            )
            signals.append(signal)
        
        return signals


class BollingerBandsStrategy(TradingStrategy):
    """
    Strategia oparta na Wstęgach Bollingera.
    Generuje sygnał BUY gdy cena odbija się od dolnej wstęgi.
    Generuje sygnał SELL gdy cena odbija się od górnej wstęgi.
    """
    
    def __init__(self, config: Optional[StrategyConfig] = None, 
                 period: int = 20, 
                 std_dev: float = 2.0):
        """
        Inicjalizacja strategii.
        
        Args:
            config: Konfiguracja strategii.
            period: Okres średniej kroczącej dla Wstęg Bollingera.
            std_dev: Liczba odchyleń standardowych dla Wstęg Bollingera.
        """
        super().__init__(config)
        self.period = period
        self.std_dev = std_dev
        
        if config and config.params:
            self.period = config.params.get('period', self.period)
            self.std_dev = config.params.get('std_dev', self.std_dev)
        
        self.name = f"BB_{self.period}_{self.std_dev}"
    
    def generate_signals(self, data: pd.DataFrame) -> List[StrategySignal]:
        """
        Generowanie sygnałów na podstawie Wstęg Bollingera.
        
        Args:
            data: DataFrame z danymi historycznymi.
        
        Returns:
            Lista sygnałów tradingowych.
        """
        if len(data) < self.period + 10:
            self.logger.warning("Insufficient data for Bollinger Bands strategy")
            return []
        
        # Kopiowanie danych, aby uniknąć modyfikacji oryginalnego DataFrame
        df = data.copy()
        
        # Obliczanie Wstęg Bollingera
        df['sma'] = df['close'].rolling(window=self.period).mean()
        df['std'] = df['close'].rolling(window=self.period).std()
        df['upper_band'] = df['sma'] + (df['std'] * self.std_dev)
        df['lower_band'] = df['sma'] - (df['std'] * self.std_dev)
        
        # Przesunięcie cen o 1 okres (poprzednia wartość)
        df['close_prev'] = df['close'].shift(1)
        
        # Generowanie sygnałów
        # Sygnał BUY: Cena przekracza dolną wstęgę od dołu
        df['buy_signal'] = (df['close_prev'] < df['lower_band']) & (df['close'] >= df['lower_band'])
        
        # Sygnał SELL: Cena przekracza górną wstęgę od góry
        df['sell_signal'] = (df['close_prev'] > df['upper_band']) & (df['close'] <= df['upper_band'])
        
        # Usunięcie wierszy z brakującymi wartościami
        df = df.dropna()
        
        signals = []
        stop_loss_pips = self.config.stop_loss_pips
        take_profit_pips = self.config.take_profit_pips
        
        # Przetwarzanie sygnałów BUY
        buy_signals = df[df['buy_signal']].copy()
        for idx, row in buy_signals.iterrows():
            entry_price = row['close']
            stop_loss = entry_price - (stop_loss_pips * 0.0001)
            take_profit = entry_price + (take_profit_pips * 0.0001)
            
            signal = StrategySignal(
                symbol=data['symbol'].iloc[0] if 'symbol' in data.columns else "UNKNOWN",
                timeframe=data['timeframe'].iloc[0] if 'timeframe' in data.columns else "UNKNOWN",
                signal_type=SignalType.BUY,
                entry_price=entry_price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                time=row['time'],
                comment=f"BB_{self.period}_{self.std_dev}_BUY"
            )
            signals.append(signal)
        
        # Przetwarzanie sygnałów SELL
        sell_signals = df[df['sell_signal']].copy()
        for idx, row in sell_signals.iterrows():
            entry_price = row['close']
            stop_loss = entry_price + (stop_loss_pips * 0.0001)
            take_profit = entry_price - (take_profit_pips * 0.0001)
            
            signal = StrategySignal(
                symbol=data['symbol'].iloc[0] if 'symbol' in data.columns else "UNKNOWN",
                timeframe=data['timeframe'].iloc[0] if 'timeframe' in data.columns else "UNKNOWN",
                signal_type=SignalType.SELL,
                entry_price=entry_price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                time=row['time'],
                comment=f"BB_{self.period}_{self.std_dev}_SELL"
            )
            signals.append(signal)
        
        return signals


class MACDStrategy(TradingStrategy):
    """
    Strategia oparta na wskaźniku MACD (Moving Average Convergence Divergence).
    """
    
    def __init__(self, config: Optional[StrategyConfig] = None, 
                 fast_period: int = 12, 
                 slow_period: int = 26, 
                 signal_period: int = 9):
        """
        Inicjalizuje strategię MACD.
        
        Args:
            config: Konfiguracja strategii
            fast_period: Okres szybkiej EMA
            slow_period: Okres wolnej EMA
            signal_period: Okres linii sygnałowej
        """
        super().__init__(config)
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.signal_period = signal_period
        
        # Jeśli podano parametry w konfiguracji, nadpisz domyślne
        if config and config.params:
            self.fast_period = config.params.get('fast_period', self.fast_period)
            self.slow_period = config.params.get('slow_period', self.slow_period)
            self.signal_period = config.params.get('signal_period', self.signal_period)
        
        self.name = f"MACD_{self.fast_period}_{self.slow_period}_{self.signal_period}"
        self.logger = logging.getLogger(__name__)
    
    @staticmethod
    def calculate_ema(data: pd.Series, period: int) -> pd.Series:
        """
        Oblicza Exponential Moving Average (EMA).
        
        Args:
            data: Szereg danych
            period: Okres EMA
        
        Returns:
            pd.Series: Wartości EMA
        """
        return data.ewm(span=period, adjust=False).mean()
    
    def generate_signals(self, data: pd.DataFrame) -> List[StrategySignal]:
        """
        Generowanie sygnałów na podstawie wskaźnika MACD.
        
        Args:
            data: DataFrame z danymi historycznymi.
        
        Returns:
            Lista sygnałów tradingowych.
        """
        if len(data) < self.slow_period + self.signal_period + 10:
            self.logger.warning("Insufficient data for MACD strategy")
            return []
        
        # Kopiowanie danych, aby uniknąć modyfikacji oryginalnego DataFrame
        df = data.copy()
        
        # Obliczanie MACD
        df['ema_fast'] = self.calculate_ema(df['close'], self.fast_period)
        df['ema_slow'] = self.calculate_ema(df['close'], self.slow_period)
        df['macd'] = df['ema_fast'] - df['ema_slow']
        df['signal_line'] = self.calculate_ema(df['macd'], self.signal_period)
        df['histogram'] = df['macd'] - df['signal_line']
        
        # Przesunięcie wskaźników o 1 okres (poprzednia wartość)
        df['macd_prev'] = df['macd'].shift(1)
        df['signal_line_prev'] = df['signal_line'].shift(1)
        
        # Generowanie sygnałów
        # Sygnał BUY: MACD przebija linię sygnałową od dołu
        df['buy_signal'] = (df['macd_prev'] < df['signal_line_prev']) & (df['macd'] > df['signal_line'])
        
        # Sygnał SELL: MACD przebija linię sygnałową od góry
        df['sell_signal'] = (df['macd_prev'] > df['signal_line_prev']) & (df['macd'] < df['signal_line'])
        
        # Usunięcie wierszy z brakującymi wartościami
        df = df.dropna()
        
        signals = []
        stop_loss_pips = self.config.stop_loss_pips
        take_profit_pips = self.config.take_profit_pips
        
        # Przetwarzanie sygnałów BUY
        buy_signals = df[df['buy_signal']].copy()
        for idx, row in buy_signals.iterrows():
            entry_price = row['close']
            stop_loss = entry_price - (stop_loss_pips * 0.0001)
            take_profit = entry_price + (take_profit_pips * 0.0001)
            
            signal = StrategySignal(
                symbol=data['symbol'].iloc[0] if 'symbol' in data.columns else "UNKNOWN",
                timeframe=data['timeframe'].iloc[0] if 'timeframe' in data.columns else "UNKNOWN",
                signal_type=SignalType.BUY,
                entry_price=entry_price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                time=row['time'],
                comment=f"MACD_{self.fast_period}_{self.slow_period}_{self.signal_period}_BUY"
            )
            signals.append(signal)
        
        # Przetwarzanie sygnałów SELL
        sell_signals = df[df['sell_signal']].copy()
        for idx, row in sell_signals.iterrows():
            entry_price = row['close']
            stop_loss = entry_price + (stop_loss_pips * 0.0001)
            take_profit = entry_price - (take_profit_pips * 0.0001)
            
            signal = StrategySignal(
                symbol=data['symbol'].iloc[0] if 'symbol' in data.columns else "UNKNOWN",
                timeframe=data['timeframe'].iloc[0] if 'timeframe' in data.columns else "UNKNOWN",
                signal_type=SignalType.SELL,
                entry_price=entry_price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                time=row['time'],
                comment=f"MACD_{self.fast_period}_{self.slow_period}_{self.signal_period}_SELL"
            )
            signals.append(signal)
        
        return signals


class CombinedIndicatorsStrategy(TradingStrategy):
    """
    Strategia łącząca różne wskaźniki, odwzorowująca działanie głównego generatora sygnałów.
    """
    
    def __init__(self, config: Optional[StrategyConfig] = None, 
                 weights: Optional[Dict[str, float]] = None,
                 thresholds: Optional[Dict[str, float]] = None):
        """
        Inicjalizacja strategii łączonej.
        
        Args:
            config: Konfiguracja strategii
            weights: Słownik wag dla poszczególnych wskaźników
            thresholds: Słownik progów dla różnych decyzji
        """
        super().__init__(config)
        
        # Domyślne wagi wskaźników odpowiadające głównemu generatorowi sygnałów
        self.weights = weights or {
            'trend': 0.25,     # Waga trendu
            'macd': 0.30,      # Waga MACD
            'rsi': 0.20,       # Waga RSI
            'bb': 0.15,        # Waga Bollinger Bands
            'candle': 0.10     # Waga formacji świecowych
        }
        
        # Inicjalizacja domyślnych progów decyzyjnych
        default_thresholds = {
            'signal_minimum': 0.2,  # Minimalny próg pewności do wygenerowania sygnału
            'signal_ratio': 1.2,    # Wymagany stosunek pewności między BUY i SELL
            'rsi_overbought': 65,   # Próg wyprzedania dla RSI
            'rsi_oversold': 35      # Próg wykupienia dla RSI
        }
        
        # Aktualizacja domyślnych progów wartościami od użytkownika
        if thresholds:
            default_thresholds.update(thresholds)
        
        self.thresholds = default_thresholds
        
        # Parametry techniczne
        self.trend_fast_period = 12
        self.trend_slow_period = 26
        self.rsi_period = 7
        self.bb_period = 15
        self.bb_std_dev = 2.0
        self.macd_fast = 12
        self.macd_slow = 26
        self.macd_signal = 9
        
        # Ustawienie parametrów z konfiguracji, jeśli są dostępne
        if config and config.params:
            if 'weights' in config.params:
                self.weights.update(config.params['weights'])
            if 'thresholds' in config.params:
                self.thresholds.update(config.params['thresholds'])
            
            # Parametry techniczne
            self.trend_fast_period = config.params.get('trend_fast_period', self.trend_fast_period)
            self.trend_slow_period = config.params.get('trend_slow_period', self.trend_slow_period)
            self.rsi_period = config.params.get('rsi_period', self.rsi_period)
            self.bb_period = config.params.get('bb_period', self.bb_period)
            self.bb_std_dev = config.params.get('bb_std_dev', self.bb_std_dev)
            self.macd_fast = config.params.get('macd_fast', self.macd_fast)
            self.macd_slow = config.params.get('macd_slow', self.macd_slow)
            self.macd_signal = config.params.get('macd_signal', self.macd_signal)
        
        self.name = "CombinedIndicators"
        self.logger = logging.getLogger(__name__)
    
    def generate_signals(self, data: pd.DataFrame) -> List[StrategySignal]:
        """
        Generuje sygnały na podstawie kombinacji wskaźników, naśladując logikę głównego generatora.
        
        Args:
            data: DataFrame z danymi historycznymi
            
        Returns:
            Lista sygnałów tradingowych
        """
        if len(data) < 50:
            self.logger.warning("Niewystarczająca ilość danych dla strategii kombinowanej")
            return []
        
        # Obliczenie wskaźników
        data = self._calculate_indicators(data)
        
        # Generowanie i ocena sygnałów
        signals = []
        
        # Dla każdego wiersza danych (z wyjątkiem pierwszych potrzebnych do obliczenia wskaźników)
        for i in range(max(50, self.trend_slow_period + 10), len(data)):
            row = data.iloc[i]
            
            # Analiza wszystkich wskaźników dla bieżącego wiersza
            indicator_signals, confidence_scores = self._analyze_indicators(data, i)
            
            # Ustalenie finalnego sygnału
            signal_type, confidence = self._determine_final_signal(indicator_signals, confidence_scores)
            
            # Jeśli mamy sygnał, dodajemy go do listy
            if signal_type != "NEUTRAL":
                entry_price = row['close']
                
                # Obliczenie ATR do określenia SL i TP
                atr = self._calculate_atr(data, i)
                
                if signal_type == "BUY":
                    signal = StrategySignal(
                        symbol=data['symbol'].iloc[0] if 'symbol' in data.columns else "UNKNOWN",
                        timeframe=data['timeframe'].iloc[0] if 'timeframe' in data.columns else "UNKNOWN",
                        signal_type=SignalType.BUY,
                        entry_price=entry_price,
                        stop_loss=entry_price - 2 * atr,
                        take_profit=entry_price + 3 * atr,
                        time=row['time'],
                        volume=0.01,  # Domyślny wolumen
                        comment=f"COMBINED_BUY_{confidence:.2f}"
                    )
                    signals.append(signal)
                elif signal_type == "SELL":
                    signal = StrategySignal(
                        symbol=data['symbol'].iloc[0] if 'symbol' in data.columns else "UNKNOWN",
                        timeframe=data['timeframe'].iloc[0] if 'timeframe' in data.columns else "UNKNOWN",
                        signal_type=SignalType.SELL,
                        entry_price=entry_price,
                        stop_loss=entry_price + 2 * atr,
                        take_profit=entry_price - 3 * atr,
                        time=row['time'],
                        volume=0.01,  # Domyślny wolumen
                        comment=f"COMBINED_SELL_{confidence:.2f}"
                    )
                    signals.append(signal)
        
        return signals
    
    def _calculate_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Oblicza wszystkie wskaźniki potrzebne dla strategii.
        
        Args:
            data: DataFrame z danymi historycznymi
            
        Returns:
            DataFrame z dodanymi kolumnami wskaźników
        """
        df = data.copy()
        
        # EMA dla trendu
        df['ema_fast'] = df['close'].ewm(span=self.trend_fast_period, adjust=False).mean()
        df['ema_slow'] = df['close'].ewm(span=self.trend_slow_period, adjust=False).mean()
        
        # RSI
        df['rsi'] = self._calculate_rsi(df['close'], self.rsi_period)
        
        # MACD
        df['macd'] = df['close'].ewm(span=self.macd_fast, adjust=False).mean() - df['close'].ewm(span=self.macd_slow, adjust=False).mean()
        df['macd_signal'] = df['macd'].ewm(span=self.macd_signal, adjust=False).mean()
        df['macd_hist'] = df['macd'] - df['macd_signal']
        
        # Bollinger Bands
        df['bb_middle'] = df['close'].rolling(window=self.bb_period).mean()
        df['bb_std'] = df['close'].rolling(window=self.bb_period).std()
        df['bb_upper'] = df['bb_middle'] + (df['bb_std'] * self.bb_std_dev)
        df['bb_lower'] = df['bb_middle'] - (df['bb_std'] * self.bb_std_dev)
        
        # Dodanie kolumn do analizy świec
        df = self._detect_candlestick_patterns(df)
        
        return df
    
    def _detect_candlestick_patterns(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Wykrywa podstawowe formacje świecowe.
        
        Args:
            data: DataFrame z danymi OHLC
            
        Returns:
            DataFrame z dodatkowymi kolumnami reprezentującymi wykryte formacje
        """
        df = data.copy()
        
        # Obliczenie długości ciał świec i cieni
        df['body_length'] = abs(df['close'] - df['open'])
        df['upper_shadow'] = df['high'] - df[['open', 'close']].max(axis=1)
        df['lower_shadow'] = df[['open', 'close']].min(axis=1) - df['low']
        df['total_length'] = df['high'] - df['low']
        
        # Inicjalizacja kolumn dla formacji świecowych
        df['bullish_engulfing'] = False
        df['bearish_engulfing'] = False
        df['hammer'] = False
        df['shooting_star'] = False
        df['doji'] = False
        df['morning_star'] = False
        df['evening_star'] = False
        
        # Wykrywanie formacji Engulfing
        for i in range(1, len(df)):
            # Bullish Engulfing
            if (df['close'].iloc[i-1] < df['open'].iloc[i-1] and  # Poprzednia świeca jest spadkowa
                df['close'].iloc[i] > df['open'].iloc[i] and      # Bieżąca świeca jest wzrostowa
                df['open'].iloc[i] < df['close'].iloc[i-1] and    # Otwarcie poniżej zamknięcia poprzedniej
                df['close'].iloc[i] > df['open'].iloc[i-1]):      # Zamknięcie powyżej otwarcia poprzedniej
                df.loc[df.index[i], 'bullish_engulfing'] = True
            
            # Bearish Engulfing
            if (df['close'].iloc[i-1] > df['open'].iloc[i-1] and  # Poprzednia świeca jest wzrostowa
                df['close'].iloc[i] < df['open'].iloc[i] and      # Bieżąca świeca jest spadkowa
                df['open'].iloc[i] > df['close'].iloc[i-1] and    # Otwarcie powyżej zamknięcia poprzedniej
                df['close'].iloc[i] < df['open'].iloc[i-1]):      # Zamknięcie poniżej otwarcia poprzedniej
                df.loc[df.index[i], 'bearish_engulfing'] = True
        
        # Wykrywanie formacji Doji, Hammer, Shooting Star
        for i in range(len(df)):
            # Doji (mały korpus, długie cienie)
            if df['body_length'].iloc[i] * 3 < df['total_length'].iloc[i] and df['body_length'].iloc[i] < 0.1 * df['total_length'].iloc[i]:
                df.loc[df.index[i], 'doji'] = True
            
            # Hammer (długi dolny cień, mały korpus na górze)
            if (df['lower_shadow'].iloc[i] > 2 * df['body_length'].iloc[i] and
                df['upper_shadow'].iloc[i] < 0.2 * df['body_length'].iloc[i] and
                df['body_length'].iloc[i] > 0):
                df.loc[df.index[i], 'hammer'] = True
            
            # Shooting Star (długi górny cień, mały korpus na dole)
            if (df['upper_shadow'].iloc[i] > 2 * df['body_length'].iloc[i] and
                df['lower_shadow'].iloc[i] < 0.2 * df['body_length'].iloc[i] and
                df['body_length'].iloc[i] > 0):
                df.loc[df.index[i], 'shooting_star'] = True
        
        # Wykrywanie formacji Morning Star i Evening Star
        for i in range(2, len(df)):
            # Morning Star
            if (df['close'].iloc[i-2] < df['open'].iloc[i-2] and                 # Pierwsza świeca jest spadkowa
                abs(df['close'].iloc[i-1] - df['open'].iloc[i-1]) < df['body_length'].iloc[i-2] * 0.3 and  # Druga świeca ma mały korpus
                df['close'].iloc[i] > df['open'].iloc[i] and                     # Trzecia świeca jest wzrostowa
                df['close'].iloc[i] > (df['open'].iloc[i-2] + df['close'].iloc[i-2]) / 2):  # Trzecia świeca zamyka się powyżej środka pierwszej
                df.loc[df.index[i], 'morning_star'] = True
            
            # Evening Star
            if (df['close'].iloc[i-2] > df['open'].iloc[i-2] and                 # Pierwsza świeca jest wzrostowa
                abs(df['close'].iloc[i-1] - df['open'].iloc[i-1]) < df['body_length'].iloc[i-2] * 0.3 and  # Druga świeca ma mały korpus
                df['close'].iloc[i] < df['open'].iloc[i] and                     # Trzecia świeca jest spadkowa
                df['close'].iloc[i] < (df['open'].iloc[i-2] + df['close'].iloc[i-2]) / 2):  # Trzecia świeca zamyka się poniżej środka pierwszej
                df.loc[df.index[i], 'evening_star'] = True
        
        return df
    
    def _analyze_indicators(self, data: pd.DataFrame, index: int) -> Tuple[Dict[str, str], Dict[str, float]]:
        """
        Analizuje wskaźniki dla danego indeksu w danych.
        
        Args:
            data: DataFrame z obliczonymi wskaźnikami
            index: Indeks wiersza do analizy
            
        Returns:
            Tuple zawierające sygnały wskaźników i ich pewności
        """
        row = data.iloc[index]
        prev_row = data.iloc[index-1]
        
        signals = {}
        confidence_scores = {}
        
        # Analiza trendu na podstawie EMA
        if row['ema_fast'] > row['ema_slow']:
            signals['trend'] = "BUY"
            confidence_scores['trend'] = min(1.0, (row['ema_fast'] - row['ema_slow']) / row['ema_slow'] * 15)
        elif row['ema_fast'] < row['ema_slow']:
            signals['trend'] = "SELL"
            confidence_scores['trend'] = min(1.0, (row['ema_slow'] - row['ema_fast']) / row['ema_slow'] * 15)
        else:
            signals['trend'] = "NEUTRAL"
            confidence_scores['trend'] = 0.5
        
        # Analiza RSI
        if row['rsi'] > self.thresholds['rsi_overbought']:
            signals['rsi'] = "SELL"
            confidence_scores['rsi'] = min(1.0, (row['rsi'] - self.thresholds['rsi_overbought']) / (100 - self.thresholds['rsi_overbought']))
        elif row['rsi'] < self.thresholds['rsi_oversold']:
            signals['rsi'] = "BUY"
            confidence_scores['rsi'] = min(1.0, (self.thresholds['rsi_oversold'] - row['rsi']) / self.thresholds['rsi_oversold'])
        else:
            signals['rsi'] = "NEUTRAL"
            confidence_scores['rsi'] = 0.5
        
        # Analiza MACD
        if row['macd'] > row['macd_signal'] and prev_row['macd'] <= prev_row['macd_signal']:
            signals['macd'] = "BUY"
            confidence_scores['macd'] = min(1.0, (row['macd'] - row['macd_signal']) * 15)
        elif row['macd'] < row['macd_signal'] and prev_row['macd'] >= prev_row['macd_signal']:
            signals['macd'] = "SELL"
            confidence_scores['macd'] = min(1.0, (row['macd_signal'] - row['macd']) * 15)
        else:
            # Analiza zbliżania się do przecięcia
            diff_current = abs(row['macd'] - row['macd_signal'])
            diff_previous = abs(prev_row['macd'] - prev_row['macd_signal'])
            
            if diff_current < diff_previous and diff_current < 0.0005:
                if row['macd'] > prev_row['macd']:
                    signals['macd'] = "BUY"
                    confidence_scores['macd'] = 0.6 - diff_current * 100
                else:
                    signals['macd'] = "SELL"
                    confidence_scores['macd'] = 0.6 - diff_current * 100
            else:
                signals['macd'] = "NEUTRAL"
                confidence_scores['macd'] = 0.5
        
        # Analiza Bollinger Bands
        if row['close'] > row['bb_upper'] * 0.97:
            signals['bb'] = "SELL"
            confidence_scores['bb'] = min(1.0, (row['close'] - row['bb_upper'] * 0.97) / (row['bb_upper'] * 0.03))
        elif row['close'] < row['bb_lower'] * 1.03:
            signals['bb'] = "BUY"
            confidence_scores['bb'] = min(1.0, (row['bb_lower'] * 1.03 - row['close']) / (row['bb_lower'] * 0.03))
        else:
            signals['bb'] = "NEUTRAL"
            confidence_scores['bb'] = 0.5
        
        # Analiza formacji świecowych
        candle_signal = "NEUTRAL"
        candle_confidence = 0.5
        
        if row['bullish_engulfing'] or row['hammer'] or row['morning_star']:
            candle_signal = "BUY"
            # Waga formacji: Engulfing > Morning Star > Hammer
            if row['bullish_engulfing']:
                candle_confidence = 0.8
            elif row['morning_star']:
                candle_confidence = 0.7
            elif row['hammer']:
                candle_confidence = 0.6
        elif row['bearish_engulfing'] or row['shooting_star'] or row['evening_star']:
            candle_signal = "SELL"
            # Waga formacji: Engulfing > Evening Star > Shooting Star
            if row['bearish_engulfing']:
                candle_confidence = 0.8
            elif row['evening_star']:
                candle_confidence = 0.7
            elif row['shooting_star']:
                candle_confidence = 0.6
        
        signals['candle'] = candle_signal
        confidence_scores['candle'] = candle_confidence
        
        return signals, confidence_scores
    
    def _determine_final_signal(self, signals: Dict[str, str], 
                              confidence_scores: Dict[str, float]) -> Tuple[str, float]:
        """
        Ustala finalny sygnał na podstawie wszystkich wskaźników.
        
        Args:
            signals: Słownik sygnałów z poszczególnych wskaźników
            confidence_scores: Słownik pewności dla poszczególnych sygnałów
            
        Returns:
            Tuple zawierające typ sygnału i pewność
        """
        # Policzenie liczby sygnałów BUY i SELL
        buy_signals = sum(1 for signal in signals.values() if signal == "BUY")
        sell_signals = sum(1 for signal in signals.values() if signal == "SELL")
        
        # Obliczenie ważonej pewności dla sygnałów
        buy_confidence = sum(confidence_scores[indicator] * self.weights[indicator] 
                          for indicator in signals 
                          if signals[indicator] == "BUY")
        
        sell_confidence = sum(confidence_scores[indicator] * self.weights[indicator] 
                           for indicator in signals 
                           if signals[indicator] == "SELL")
        
        # Znajdź najsilniejszy sygnał kupna i sprzedaży
        max_buy_confidence = max([confidence_scores[indicator] for indicator in signals if signals[indicator] == "BUY"], default=0)
        max_sell_confidence = max([confidence_scores[indicator] for indicator in signals if signals[indicator] == "SELL"], default=0)
        
        # Wzmocnij pewność na podstawie najsilniejszego sygnału
        if max_buy_confidence > 0.7:
            buy_confidence = max(buy_confidence, max_buy_confidence * 0.5)
        if max_sell_confidence > 0.7:
            sell_confidence = max(sell_confidence, max_sell_confidence * 0.5)
        
        # Finalny sygnał
        if buy_signals > sell_signals and buy_confidence > self.thresholds['signal_minimum']:
            return "BUY", buy_confidence
        elif sell_signals > buy_signals and sell_confidence > self.thresholds['signal_minimum']:
            return "SELL", sell_confidence
        elif buy_signals == sell_signals:
            if (buy_confidence > self.thresholds['signal_minimum'] and 
                buy_confidence > sell_confidence * self.thresholds['signal_ratio']):
                return "BUY", buy_confidence
            elif (sell_confidence > self.thresholds['signal_minimum'] and 
                 sell_confidence > buy_confidence * self.thresholds['signal_ratio']):
                return "SELL", sell_confidence
        
        return "NEUTRAL", max(0.5, abs(buy_confidence - sell_confidence))
    
    def _calculate_atr(self, data: pd.DataFrame, index: int, period: int = 14) -> float:
        """
        Oblicza Average True Range dla danego indeksu.
        
        Args:
            data: DataFrame z danymi
            index: Indeks wiersza do analizy
            period: Okres ATR
            
        Returns:
            Wartość ATR
        """
        if index < period:
            return 0.001  # Domyślna wartość dla przypadku, gdy nie ma wystarczająco danych
        
        true_ranges = []
        for i in range(index - period + 1, index + 1):
            tr1 = data['high'].iloc[i] - data['low'].iloc[i]
            tr2 = abs(data['high'].iloc[i] - data['close'].iloc[i-1])
            tr3 = abs(data['low'].iloc[i] - data['close'].iloc[i-1])
            true_ranges.append(max(tr1, tr2, tr3))
        
        return sum(true_ranges) / period
    
    def _calculate_rsi(self, prices: pd.Series, period: int = 14) -> pd.Series:
        """
        Oblicza wskaźnik RSI.
        
        Args:
            prices: Seria cen
            period: Okres RSI
            
        Returns:
            Seria z wartościami RSI
        """
        delta = prices.diff()
        
        # Zyski (delta dodatnia) i straty (delta ujemna)
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        
        # Średnie zysków i strat
        avg_gain = gain.rolling(window=period).mean()
        avg_loss = loss.rolling(window=period).mean()
        
        # Obliczanie RS i RSI
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi 