#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Generator sygnałów handlowych.
"""

import logging
import random
import time
from typing import Dict, List, Optional, Any, Tuple
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from enum import Enum, auto
import json
import traceback

import MetaTrader5 as mt5

from src.database.models import TradingSignal
from src.database.trading_signal_repository import get_trading_signal_repository
from src.config.config_manager import ConfigManager
from src.mt5_bridge.mt5_connector import MT5Connector
from src.notifications.notification_manager import get_notification_manager, NotificationType

logger = logging.getLogger(__name__)


class SignalType(Enum):
    """Typ sygnału handlowego."""
    ENTRY = auto()     # Sygnał wejścia
    EXIT = auto()      # Sygnał wyjścia
    SL_ADJUST = auto() # Dostosowanie Stop Loss
    TP_ADJUST = auto() # Dostosowanie Take Profit
    WARNING = auto()   # Ostrzeżenie
    INFO = auto()      # Informacja


class SignalStrength(Enum):
    """Siła sygnału handlowego."""
    VERY_STRONG = auto()  # Bardzo silny sygnał
    STRONG = auto()       # Silny sygnał
    MODERATE = auto()     # Umiarkowany sygnał
    WEAK = auto()         # Słaby sygnał
    VERY_WEAK = auto()    # Bardzo słaby sygnał


class SignalSource(Enum):
    """Źródło sygnału handlowego."""
    TECHNICAL = auto()    # Analiza techniczna
    FUNDAMENTAL = auto()  # Analiza fundamentalna
    AI_MODEL = auto()     # Model AI
    COMBINED = auto()     # Sygnał złożony
    MANUAL = auto()       # Ręczne wprowadzenie


class SignalGenerator:
    """
    Generator sygnałów handlowych oparty na analizie technicznej.
    Generuje sygnały kupna/sprzedaży na podstawie wskaźników technicznych.
    """
    
    def __init__(self):
        """
        Inicjalizacja generatora sygnałów.
        """
        # Upewnij się, że logger jest pierwszy - przed inicjalizacją innych komponentów
        self.logger = logging.getLogger('src.analysis.signal_generator')
        
        try:
            self.signal_repository = get_trading_signal_repository()
            self.config = ConfigManager().get_config()
            self.mt5_connector = MT5Connector()
            self.signals_memory = {}  # Słownik do przechowywania sygnałów w pamięci
            
            # Inicjalizacja dodatkowych parametrów konfiguracyjnych
            self.instruments = []  # Lista dostępnych instrumentów
            self.timeframes = ["M5", "M15", "H1"]  # Domyślne ramy czasowe
            
            self.logger.info("SignalGenerator zainicjalizowany")
        except Exception as e:
            self.logger.error(f"Błąd podczas inicjalizacji SignalGenerator: {e}")
            import traceback
            self.logger.debug(traceback.format_exc())
    
    def generate_signal_from_data(self, symbol: str, timeframe: str, data: pd.DataFrame) -> Optional[TradingSignal]:
        """
        Generuje sygnał handlowy na podstawie dostarczonych danych historycznych.
        Ta metoda jest używana głównie podczas backtestingu.
        
        Args:
            symbol: Symbol instrumentu
            timeframe: Ramy czasowe analizy
            data: DataFrame z danymi historycznymi (musi zawierać kolumny: open, high, low, close, tick_volume, time)
            
        Returns:
            TradingSignal lub None w przypadku braku sygnału
        """
        try:
            self.logger.info(f"Generuję sygnał dla {symbol} na ramach czasowych {timeframe} na podstawie dostarczonych danych")
            
            if data is None or len(data) < 50:
                self.logger.warning(f"Niewystarczająca ilość danych dla {symbol}")
                return None
                
            # Przygotowanie danych w formacie potrzebnym dla analizy technicznej
            # Konwertujemy wszystkie wartości na float, aby uniknąć problemów z typami
            tech_data = {
                'open': data['open'].astype(float).tolist(),
                'high': data['high'].astype(float).tolist(),
                'low': data['low'].astype(float).tolist(),
                'close': data['close'].astype(float).tolist(),
                'volume': data['tick_volume'].astype(float).tolist() if 'tick_volume' in data.columns else data['volume'].astype(float).tolist(),
                # Konwertujemy czas na string ISO format, aby uniknąć problemów z typami datetime
                'time': [t.strftime('%Y-%m-%d %H:%M:%S') if isinstance(t, datetime) else t for t in data['time']]
            }
            
            # Analiza techniczna
            self.logger.info(f"Rozpoczynam analizę techniczną dla {symbol}")
            tech_result = self._analyze_technical_data(symbol, timeframe, tech_data)
            
            if not tech_result or tech_result["signal"] == "NEUTRAL" or tech_result["signal"] == "BRAK":
                self.logger.warning(f"Analiza techniczna nie wygenerowała sygnału dla {symbol}")
                return None
            
            # Utworzenie sygnału
            entry_price = data['close'].iloc[-1]  # Ostatnia cena zamknięcia jako cena wejścia
            
            # Obliczenie ATR do określenia poziomów SL i TP
            true_ranges = []
            for i in range(1, len(data)):
                tr1 = data['high'].iloc[i] - data['low'].iloc[i]
                tr2 = abs(data['high'].iloc[i] - data['close'].iloc[i-1])
                tr3 = abs(data['low'].iloc[i] - data['close'].iloc[i-1])
                true_ranges.append(max(tr1, tr2, tr3))
            
            atr = sum(true_ranges[-14:]) / 14 if true_ranges else 0.001
            
            # Ustawianie SL i TP na podstawie ATR i kierunku sygnału
            if tech_result["signal"] == "BUY":
                stop_loss = entry_price - 2 * atr
                take_profit = entry_price + 3 * atr
            else:  # SELL
                stop_loss = entry_price + 2 * atr
                take_profit = entry_price - 3 * atr
            
            # Generowanie opisu analizy
            analysis_description = self._generate_analysis_description(
                symbol, 
                tech_result["signal"], 
                tech_result["details"]["indicators"].get("rsi", 50.0),
                sum(data['close'][-20:]) / 20 if len(data) >= 20 else data['close'].iloc[-1],
                sum(data['close'][-50:]) / 50 if len(data) >= 50 else data['close'].iloc[-1],
                tech_result["confidence"]
            )
            
            # Utworzenie obiektu sygnału
            signal = TradingSignal(
                symbol=symbol,
                timeframe=timeframe,
                direction=tech_result["signal"],
                entry_price=entry_price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                confidence=tech_result["confidence"],
                ai_analysis=analysis_description,
                created_at=datetime.now(),
                expired_at=datetime.now() + timedelta(hours=24)
            )
            
            self.logger.info(f"Wygenerowano sygnał {signal.direction} dla {symbol} z pewnością {signal.confidence:.2f}")
            self.logger.debug(f"Szczegóły sygnału: {signal}")
            
            # Zapisanie sygnału do bazy danych
            try:
                saved_signal = self.signal_repository.save_signal(signal)
                self.logger.info(f"Sygnał dla {symbol} zapisany do bazy danych, ID: {saved_signal.id}")
                # Zapisujemy również w pamięci podręcznej
                self.signals_memory[symbol] = signal
                
                # Wysyłamy powiadomienie o nowym sygnale
                self.send_notification(saved_signal)
            except Exception as e:
                self.logger.error(f"Błąd podczas zapisywania sygnału do bazy danych: {e}")
                import traceback
                self.logger.debug(traceback.format_exc())
            
            return signal
            
        except Exception as e:
            self.logger.error(f"Błąd podczas generowania sygnału dla {symbol}: {e}")
            import traceback
            self.logger.debug(traceback.format_exc())
            return None
    
    def generate_signal(self, symbol: str, timeframe: str) -> Optional[TradingSignal]:
        """
        Generuje sygnał handlowy dla określonego instrumentu.
        
        Args:
            symbol: Symbol instrumentu
            timeframe: Ramy czasowe analizy
            
        Returns:
            TradingSignal lub None w przypadku braku sygnału
        """
        try:
            self.logger.info(f"Generuję sygnał dla {symbol} na ramach czasowych {timeframe}")
            
            # Pobieranie danych historycznych za ostatnie 30 dni
            end_date = datetime.now()
            start_date = end_date - timedelta(days=30)  # Ostatnie 30 dni
            
            # Importujemy HistoricalDataManager tylko gdy jest potrzebny
            from src.backtest.historical_data_manager import HistoricalDataManager
            
            # Tworzymy instancję HistoricalDataManager
            data_manager = HistoricalDataManager(mt5_connector=self.mt5_connector)
            
            # Pobieramy dane historyczne
            rates_df = data_manager.get_historical_data(
                symbol=symbol,
                timeframe=timeframe,
                start_date=start_date,
                end_date=end_date,
                use_cache=True,
                update_cache=True,
                use_synthetic=False  # Nie używamy danych syntetycznych w tym przypadku
            )
            
            if rates_df is None or len(rates_df) < 50:
                self.logger.warning(f"Niewystarczająca ilość danych dla {symbol}")
                return None
            
            # Przygotowanie danych w formacie potrzebnym dla analizy technicznej
            # Konwertujemy wszystkie wartości na float, aby uniknąć problemów z typami
            data = {
                'open': rates_df['open'].astype(float).tolist(),
                'high': rates_df['high'].astype(float).tolist(),
                'low': rates_df['low'].astype(float).tolist(),
                'close': rates_df['close'].astype(float).tolist(),
                'volume': rates_df['tick_volume'].astype(float).tolist(),
                # Konwertujemy czas na string ISO format, aby uniknąć problemów z typami datetime
                'time': [t.strftime('%Y-%m-%d %H:%M:%S') for t in rates_df['time']]
            }
            
            # Analiza techniczna
            self.logger.info(f"Rozpoczynam analizę techniczną dla {symbol}")
            tech_result = self._analyze_technical_data(symbol, timeframe, data)
            
            if not tech_result or tech_result["signal"] == "NEUTRAL" or tech_result["signal"] == "BRAK":
                self.logger.warning(f"Analiza techniczna nie wygenerowała sygnału dla {symbol}")
                return None
            
            # Utworzenie sygnału
            entry_price = data['close'][-1]  # Ostatnia cena zamknięcia jako cena wejścia
            
            # Obliczenie ATR do określenia poziomów SL i TP
            true_ranges = []
            for i in range(1, len(data['close'])):
                tr1 = data['high'][i] - data['low'][i]
                tr2 = abs(data['high'][i] - data['close'][i-1])
                tr3 = abs(data['low'][i] - data['close'][i-1])
                true_ranges.append(max(tr1, tr2, tr3))
            
            atr = sum(true_ranges[-14:]) / 14 if true_ranges else 0.001
            
            # Ustawianie SL i TP na podstawie ATR i kierunku sygnału
            if tech_result["signal"] == "BUY":
                stop_loss = entry_price - 2 * atr
                take_profit = entry_price + 3 * atr
            else:  # SELL
                stop_loss = entry_price + 2 * atr
                take_profit = entry_price - 3 * atr
            
            # Generowanie opisu analizy
            analysis_description = self._generate_analysis_description(
                symbol, 
                tech_result["signal"], 
                tech_result["details"]["indicators"].get("rsi", 50.0),
                sum(data['close'][-20:]) / 20 if len(data['close']) >= 20 else data['close'][-1],
                sum(data['close'][-50:]) / 50 if len(data['close']) >= 50 else data['close'][-1],
                tech_result["confidence"]
            )
            
            # Utworzenie obiektu sygnału
            signal = TradingSignal(
                symbol=symbol,
                timeframe=timeframe,
                direction=tech_result["signal"],
                entry_price=entry_price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                confidence=tech_result["confidence"],
                ai_analysis=analysis_description,
                created_at=datetime.now(),
                expired_at=datetime.now() + timedelta(hours=24)
            )
            
            # Zapisanie ostatniego sygnału
            self.last_signal = signal
            
            self.logger.info(f"Wygenerowano sygnał {signal.direction} dla {symbol} z pewnością {signal.confidence:.2f}")
            self.logger.debug(f"Szczegóły sygnału: {signal}")
            
            # Zapisanie sygnału do bazy danych
            try:
                saved_signal = self.signal_repository.save_signal(signal)
                self.logger.info(f"Sygnał dla {symbol} zapisany do bazy danych, ID: {saved_signal.id}")
                # Zapisujemy również w pamięci podręcznej
                self.signals_memory[symbol] = signal
                
                # Wysyłamy powiadomienie o nowym sygnale
                self.send_notification(saved_signal)
            except Exception as e:
                self.logger.error(f"Błąd podczas zapisywania sygnału do bazy danych: {e}")
                import traceback
                self.logger.debug(traceback.format_exc())
            
            return signal
            
        except Exception as e:
            self.logger.error(f"Błąd podczas generowania sygnału dla {symbol}: {e}")
            import traceback
            self.logger.debug(traceback.format_exc())
            return None
    
    def _analyze_technical_data(self, symbol: str, timeframe: str, data: dict) -> dict:
        """
        Analizuje dane techniczne dla danego instrumentu i ram czasowych.
        
        Args:
            symbol: Symbol instrumentu
            timeframe: Ramy czasowe
            data: Dane historyczne
            
        Returns:
            dict: Wynik analizy technicznej
        """
        self.logger.info(f"Analizuję dane techniczne dla {symbol} na ramach czasowych {timeframe}")
        
        # Konwersja danych na tablice NumPy
        if not data or 'close' not in data:
            self.logger.error(f"Brak danych cenowych dla {symbol}")
            return {"signal": "BRAK", "confidence": 0.0, "details": {}}
        
        try:
            import numpy as np
            import sys
            import os
            
            # Dodanie ścieżki głównej projektu do sys.path, aby umożliwić import modułów
            root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            if root_dir not in sys.path:
                sys.path.append(root_dir)
            
            from test_indicators import (
                calculate_sma, calculate_ema, calculate_rsi, calculate_macd,
                calculate_bollinger_bands, calculate_stochastic_oscillator,
                detect_candlestick_patterns
            )
            
            # Przygotowanie danych
            close_prices = np.array(data['close'])
            open_prices = np.array(data['open'])
            high_prices = np.array(data['high'])
            low_prices = np.array(data['low'])
            
            # Zoptymalizowane parametry na podstawie testów
            rsi_period = 7  # Optymalny parametr
            macd_fast = 12  # Optymalny parametr
            macd_slow = 26  # Optymalny parametr
            bb_period = 15  # Optymalny parametr
            
            # Obliczenie wskaźników z optymalnymi parametrami
            sma_20 = calculate_sma(close_prices, 20)
            ema_12 = calculate_ema(close_prices, macd_fast)
            ema_26 = calculate_ema(close_prices, macd_slow)
            rsi = calculate_rsi(close_prices, rsi_period)
            macd_line, signal_line, histogram = calculate_macd(close_prices, macd_fast, macd_slow)
            upper_band, middle_band, lower_band = calculate_bollinger_bands(close_prices, bb_period)
            k, d = calculate_stochastic_oscillator(high_prices, low_prices, close_prices)
            patterns = detect_candlestick_patterns(open_prices, high_prices, low_prices, close_prices)
            
            # Przygotowanie słownika na sygnały z poszczególnych wskaźników
            signals = {}
            confidence_scores = {}
            details = {}
            
            # Analiza trendu na podstawie SMA i EMA
            if not np.isnan(ema_12[-1]) and not np.isnan(ema_26[-1]):
                if ema_12[-1] > ema_26[-1]:
                    # Trend wzrostowy (krótka EMA powyżej długiej EMA)
                    signals['trend'] = "BUY"
                    confidence_scores['trend'] = min(1.0, (ema_12[-1] - ema_26[-1]) / ema_26[-1] * 15)  # Zwiększona wrażliwość
                elif ema_12[-1] < ema_26[-1]:
                    # Trend spadkowy (krótka EMA poniżej długiej EMA)
                    signals['trend'] = "SELL"
                    confidence_scores['trend'] = min(1.0, (ema_26[-1] - ema_12[-1]) / ema_26[-1] * 15)  # Zwiększona wrażliwość
                else:
                    signals['trend'] = "NEUTRAL"
                    confidence_scores['trend'] = 0.5
            else:
                signals['trend'] = "NEUTRAL"
                confidence_scores['trend'] = 0.5
            
            # Analiza RSI - mniej konserwatywne progi
            if not np.isnan(rsi[-1]):
                if rsi[-1] > 65:  # Obniżono próg z 70 na 65
                    # Wykupienie (sygnał sprzedaży)
                    signals['rsi'] = "SELL"
                    confidence_scores['rsi'] = min(1.0, (rsi[-1] - 65) / 35)  # Dostosowany zakres
                elif rsi[-1] < 35:  # Zwiększono próg z 30 na 35
                    # Wyprzedanie (sygnał kupna)
                    signals['rsi'] = "BUY"
                    confidence_scores['rsi'] = min(1.0, (35 - rsi[-1]) / 35)  # Dostosowany zakres
                else:
                    signals['rsi'] = "NEUTRAL"
                    confidence_scores['rsi'] = 0.5
            else:
                signals['rsi'] = "NEUTRAL"
                confidence_scores['rsi'] = 0.5
            
            # Analiza MACD - bardziej wrażliwa na przecięcia
            if (not np.isnan(macd_line[-1]) and not np.isnan(signal_line[-1]) and 
                not np.isnan(macd_line[-2]) and not np.isnan(signal_line[-2])):
                
                # Przecięcie MACD z linią sygnałową
                if macd_line[-1] > signal_line[-1] and macd_line[-2] <= signal_line[-2]:
                    # Sygnał kupna (MACD przecina linię sygnałową od dołu)
                    signals['macd'] = "BUY"
                    confidence_scores['macd'] = min(1.0, (macd_line[-1] - signal_line[-1]) * 15)  # Zwiększona wrażliwość
                elif macd_line[-1] < signal_line[-1] and macd_line[-2] >= signal_line[-2]:
                    # Sygnał sprzedaży (MACD przecina linię sygnałową od góry)
                    signals['macd'] = "SELL"
                    confidence_scores['macd'] = min(1.0, (signal_line[-1] - macd_line[-1]) * 15)  # Zwiększona wrażliwość
                else:
                    # Dodana logika zbliżania się do przecięcia
                    diff_current = abs(macd_line[-1] - signal_line[-1])
                    diff_previous = abs(macd_line[-2] - signal_line[-2])
                    
                    if diff_current < diff_previous and diff_current < 0.0005:  # Blisko przecięcia
                        if macd_line[-1] > macd_line[-2]:  # Macd rośnie
                            signals['macd'] = "BUY"
                            confidence_scores['macd'] = 0.6 - diff_current * 100  # Tym bliżej przecięcia, tym większa pewność
                        else:  # Macd spada
                            signals['macd'] = "SELL"
                            confidence_scores['macd'] = 0.6 - diff_current * 100  # Tym bliżej przecięcia, tym większa pewność
                    else:
                        signals['macd'] = "NEUTRAL"
                        confidence_scores['macd'] = 0.5
            else:
                signals['macd'] = "NEUTRAL"
                confidence_scores['macd'] = 0.5
            
            # Analiza Bollinger Bands - bardziej wrażliwa
            if (not np.isnan(upper_band[-1]) and not np.isnan(middle_band[-1]) and 
                not np.isnan(lower_band[-1])):
                
                # Cena blisko górnego pasma (potencjalny sygnał sprzedaży) - zwiększona wrażliwość
                if close_prices[-1] > upper_band[-1] * 0.97:  # Zmieniono z 0.95 na 0.97
                    signals['bb'] = "SELL"
                    confidence_scores['bb'] = min(1.0, (close_prices[-1] - upper_band[-1] * 0.97) / (upper_band[-1] * 0.03))
                # Cena blisko dolnego pasma (potencjalny sygnał kupna) - zwiększona wrażliwość
                elif close_prices[-1] < lower_band[-1] * 1.03:  # Zmieniono z 1.05 na 1.03
                    signals['bb'] = "BUY"
                    confidence_scores['bb'] = min(1.0, (lower_band[-1] * 1.03 - close_prices[-1]) / (lower_band[-1] * 0.03))
                else:
                    signals['bb'] = "NEUTRAL"
                    confidence_scores['bb'] = 0.5
            else:
                signals['bb'] = "NEUTRAL"
                confidence_scores['bb'] = 0.5
            
            # Analiza formacji świecowych
            candle_signal = "NEUTRAL"
            candle_confidence = 0.5
            
            if patterns['bullish_engulfing'][-1] or patterns['hammer'][-1] or patterns['morning_star'][-1]:
                candle_signal = "BUY"
                # Waga formacji: Engulfing > Morning Star > Hammer
                if patterns['bullish_engulfing'][-1]:
                    candle_confidence = 0.8
                elif patterns['morning_star'][-1]:
                    candle_confidence = 0.7
                elif patterns['hammer'][-1]:
                    candle_confidence = 0.6
            elif patterns['bearish_engulfing'][-1] or patterns['shooting_star'][-1] or patterns['evening_star'][-1]:
                candle_signal = "SELL"
                # Waga formacji: Engulfing > Evening Star > Shooting Star
                if patterns['bearish_engulfing'][-1]:
                    candle_confidence = 0.8
                elif patterns['evening_star'][-1]:
                    candle_confidence = 0.7
                elif patterns['shooting_star'][-1]:
                    candle_confidence = 0.6
            
            signals['candle'] = candle_signal
            confidence_scores['candle'] = candle_confidence
            
            # Ustalenie wag dla wskaźników - zoptymalizowane wagi
            weights = {
                'trend': 0.25,     # Zmniejszona waga trendu
                'macd': 0.30,      # Zwiększona waga MACD
                'rsi': 0.20,       # Zwiększona waga RSI
                'bb': 0.15,        # Bollinger Bands
                'candle': 0.10     # Zmniejszona waga formacji świecowych
            }
            
            # Policzenie liczby sygnałów BUY i SELL
            buy_signals = sum(1 for signal in signals.values() if signal == "BUY")
            sell_signals = sum(1 for signal in signals.values() if signal == "SELL")
            
            # Obliczenie ważonej pewności dla sygnałów kupna i sprzedaży
            buy_confidence = sum(confidence_scores[indicator] * weights[indicator] 
                                for indicator in signals 
                                if signals[indicator] == "BUY")
            
            sell_confidence = sum(confidence_scores[indicator] * weights[indicator] 
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
            
            # Dodanie szczegółów analizy
            details = {
                'indicators': {
                    'sma20': float(sma_20[-1]) if not np.isnan(sma_20[-1]) else None,
                    'ema12': float(ema_12[-1]) if not np.isnan(ema_12[-1]) else None,
                    'ema26': float(ema_26[-1]) if not np.isnan(ema_26[-1]) else None,
                    'rsi': float(rsi[-1]) if not np.isnan(rsi[-1]) else None,
                    'macd': float(macd_line[-1]) if not np.isnan(macd_line[-1]) else None,
                    'macd_signal': float(signal_line[-1]) if not np.isnan(signal_line[-1]) else None,
                    'upper_bb': float(upper_band[-1]) if not np.isnan(upper_band[-1]) else None,
                    'middle_bb': float(middle_band[-1]) if not np.isnan(middle_band[-1]) else None,
                    'lower_bb': float(lower_band[-1]) if not np.isnan(lower_band[-1]) else None,
                    'stoch_k': float(k[-1]) if not np.isnan(k[-1]) else None,
                    'stoch_d': float(d[-1]) if not np.isnan(d[-1]) else None
                },
                'signals': signals,
                'confidence_scores': confidence_scores,
                'patterns': {
                    'bullish_engulfing': bool(patterns['bullish_engulfing'][-1]),
                    'bearish_engulfing': bool(patterns['bearish_engulfing'][-1]),
                    'hammer': bool(patterns['hammer'][-1]),
                    'shooting_star': bool(patterns['shooting_star'][-1]),
                    'doji': bool(patterns['doji'][-1]),
                    'morning_star': bool(patterns['morning_star'][-1]),
                    'evening_star': bool(patterns['evening_star'][-1])
                }
            }
            
            # Ustalenie finalnego sygnału - obniżenie progów dla generowania sygnałów
            if buy_signals > sell_signals and buy_confidence > 0.2:  # Zmieniono z 0.3 na 0.2
                signal = "BUY"
                confidence = buy_confidence
            elif sell_signals > buy_signals and sell_confidence > 0.2:  # Zmieniono z 0.3 na 0.2
                signal = "SELL"
                confidence = sell_confidence
            # Dodajemy warunek dla równej liczby sygnałów
            elif buy_signals == sell_signals:
                if buy_confidence > 0.25 and buy_confidence > sell_confidence * 1.2:
                    signal = "BUY"
                    confidence = buy_confidence
                elif sell_confidence > 0.25 and sell_confidence > buy_confidence * 1.2:
                    signal = "SELL"
                    confidence = sell_confidence
                else:
                    signal = "NEUTRAL"
                    confidence = max(0.5, abs(buy_confidence - sell_confidence))
            else:
                signal = "NEUTRAL"
                confidence = max(0.5, abs(buy_confidence - sell_confidence))
            
            self.logger.info(f"Sygnał dla {symbol}: {signal} z pewnością {confidence:.2f}")
            self.logger.debug(f"Szczegóły analizy: {details}")
            
            return {
                "signal": signal,
                "confidence": float(confidence),
                "details": details
            }
            
        except Exception as e:
            self.logger.error(f"Błąd podczas analizy technicznej dla {symbol}: {e}")
            import traceback
            self.logger.debug(traceback.format_exc())
            
            # W przypadku błędu zwracamy neutralny sygnał
            return {"signal": "NEUTRAL", "confidence": 0.0, "details": {"error": str(e)}}
    
    def _generate_analysis_description(self, symbol: str, direction: str, rsi: float, 
                                      ma20: float, ma50: float, confidence: float) -> str:
        """
        Generuje opis analizy technicznej w formie tekstowej.
        
        Args:
            symbol: Symbol instrumentu
            direction: Kierunek sygnału (BUY/SELL)
            rsi: Wartość wskaźnika RSI
            ma20: Średnia krocząca 20-okresowa
            ma50: Średnia krocząca 50-okresowa
            confidence: Poziom pewności sygnału
            
        Returns:
            Opis analizy w formie tekstowej
        """
        action_type = "kupna" if direction == "BUY" else "sprzedaży"
        confidence_text = "wysoką" if confidence > 0.8 else "średnią" if confidence > 0.65 else "umiarkowaną"
        
        rsi_desc = ""
        if rsi < 30:
            rsi_desc = f"RSI ({rsi:.1f}) wskazuje na silne wykupienie rynku, co sugeruje potencjalny ruch w górę"
        elif rsi > 70:
            rsi_desc = f"RSI ({rsi:.1f}) wskazuje na silne wyprzedanie rynku, co sugeruje potencjalny ruch w dół"
        else:
            rsi_desc = f"RSI ({rsi:.1f}) jest w strefie neutralnej"
        
        ma_desc = ""
        if ma20 > ma50:
            ma_desc = "Średnie kroczące pokazują trend wzrostowy (MA20 > MA50)"
        elif ma20 < ma50:
            ma_desc = "Średnie kroczące pokazują trend spadkowy (MA20 < MA50)"
        else:
            ma_desc = "Średnie kroczące są w konsolidacji"
        
        model_name = self._select_model_name(confidence)
        
        # Generowanie losowej analizy w zależności od modelu AI
        if model_name == "Claude":
            analysis = (
                f"Na podstawie kompleksowej analizy technicznej, zidentyfikowaliśmy sygnał {action_type} dla {symbol} "
                f"z {confidence_text} pewnością ({confidence:.1%}). {rsi_desc}. {ma_desc}. "
                f"Struktury cenowe wskazują na potencjalną kontynuację ruchu, z możliwymi poziomami oporu "
                f"i wsparcia wyznaczonymi przez wcześniejsze szczyty i dołki."
            )
        elif model_name == "Grok":
            analysis = (
                f"Sygnał {action_type} dla {symbol}! {rsi_desc}. {ma_desc}. "
                f"Analiza wzorców cenowych sugeruje {confidence_text} prawdopodobieństwo ruchu zgodnego z sygnałem. "
                f"Na podstawie badania obecnej struktury rynku i zachowania ceny, przewiduję potencjalny ruch "
                f"z prawdopodobieństwem {confidence:.1%}."
            )
        elif model_name == "DeepSeek":
            analysis = (
                f"Dogłębna analiza techniczna {symbol} ujawnia sygnał {action_type}. {rsi_desc}. {ma_desc}. "
                f"Badania historycznych wzorców cenowych wskazują na {confidence_text} korelację z obecną strukturą rynku. "
                f"Na podstawie tych wskaźników, prawdopodobieństwo sukcesu sygnału wynosi {confidence:.1%}."
            )
        else:  # Ensemble
            analysis = (
                f"Zespół modeli wskazuje na sygnał {action_type} dla {symbol}. {rsi_desc}. {ma_desc}. "
                f"Analiza wskaźników technicznych i wzorców cenowych daje {confidence_text} pewność ({confidence:.1%}). "
                f"Badania historycznych ruchów cen w podobnych warunkach rynkowych wspierają ten sygnał handlowy."
            )
        
        return analysis
    
    def _select_model_name(self, confidence: float) -> str:
        """
        Wybiera nazwę modelu AI do przypisania do sygnału.
        
        Args:
            confidence: Poziom pewności sygnału
            
        Returns:
            Nazwa modelu AI
        """
        models = ["Claude", "Grok", "DeepSeek", "Ensemble"]
        
        # Przypisanie wag do modeli w zależności od pewności
        weights = []
        
        if confidence > 0.85:
            weights = [0.50, 0.15, 0.0, 0.35]  # Zdecydowanie preferujemy Claude przy wysokiej pewności
        elif confidence > 0.7:
            weights = [0.45, 0.25, 0.0, 0.30]  # Preferujemy Claude przy średniej pewności
        else:
            weights = [0.40, 0.30, 0.0, 0.30]  # Nadal preferujemy Claude przy niskiej pewności
        
        # Zwrócenie losowo wybranego modelu na podstawie wag
        return random.choices(models, weights=weights, k=1)[0]
    
    def get_last_signal(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Pobiera ostatni wygenerowany sygnał dla danego instrumentu.
        
        Args:
            symbol: Symbol instrumentu
            
        Returns:
            Optional[Dict[str, Any]]: Ostatni wygenerowany sygnał lub None
        """
        return self.signals_memory.get(symbol, None)
    
    def update_config(self, config: Dict[str, Any]):
        """
        Aktualizuje konfigurację generatora sygnałów.
        
        Args:
            config: Słownik z parametrami konfiguracyjnymi
        """
        try:
            self.logger.info(f"Aktualizuję konfigurację generatora sygnałów: {config}")
            
            # Zapisujemy dostępne instrumenty
            if "instruments" in config:
                self.instruments = config.get("instruments", [])
                self.logger.info(f"Zaktualizowano listę instrumentów: {self.instruments}")
            
            # Zapisujemy dostępne ramy czasowe
            if "timeframes" in config:
                self.timeframes = config.get("timeframes", ["M5", "M15", "H1"])
                self.logger.info(f"Zaktualizowano ramy czasowe: {self.timeframes}")
            
            # Aktualizujemy inne parametry konfiguracyjne
            if isinstance(self.config, dict):
                for key, value in config.items():
                    if key not in ["instruments", "timeframes"]:
                        self.config[key] = value
                        self.logger.info(f"Zaktualizowano parametr {key}: {value}")
            
            self.logger.info("Konfiguracja generatora sygnałów została zaktualizowana")
            
        except Exception as e:
            self.logger.error(f"Błąd podczas aktualizacji konfiguracji generatora sygnałów: {e}")
            import traceback
            self.logger.debug(traceback.format_exc())

    def send_notification(self, signal: TradingSignal):
        """
        Wysyła powiadomienie o nowym sygnale.
        
        Args:
            signal: Obiekt TradingSignal reprezentujący nowy sygnał
        """
        try:
            notification_manager = get_notification_manager()
            notification_manager.notify_new_signal(signal)
            self.logger.info(f"Powiadomienie o nowym sygnale wysłane: {signal.symbol} {signal.direction}")
        except Exception as e:
            self.logger.error(f"Błąd podczas wysyłania powiadomienia o nowym sygnale: {e}")
            import traceback
            self.logger.debug(traceback.format_exc()) 