#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Moduł do przetwarzania danych rynkowych.

Ten moduł zawiera funkcje i klasy do pobierania, normalizacji i przetwarzania
danych rynkowych z MT5 oraz innych źródeł.
"""

import os
import json
import time
import logging
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Union, Tuple
import numpy as np
import pandas as pd

# Importy wewnętrzne
from src.mt5_bridge.mt5_client import MT5Client, get_mt5_client
from src.database.market_data_repository import MarketDataRepository, get_market_data_repository

# Konfiguracja loggera
logger = logging.getLogger('trading_agent.analysis.market_data')


class MarketDataProcessor:
    """Klasa do przetwarzania danych rynkowych z MT5 oraz innych źródeł."""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        """Implementacja wzorca Singleton."""
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(MarketDataProcessor, cls).__new__(cls)
                cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """Inicjalizacja procesora danych rynkowych."""
        if self._initialized:
            return
            
        self.logger = logging.getLogger('trading_agent.analysis.market_data')
        self.logger.info("Inicjalizacja MarketDataProcessor")
        
        # Inicjalizacja klientów
        self.mt5_client = get_mt5_client()
        self.market_data_repository = get_market_data_repository()
        
        # Parametry konfiguracyjne
        self.default_timeframes = ["M1", "M5", "M15", "H1", "D1"]
        self.default_indicators = ["RSI", "MACD", "MA", "Bollinger", "ATR"]
        self.config = self._load_config()
        
        self._initialized = True
    
    def _load_config(self) -> Dict[str, Any]:
        """
        Wczytuje konfigurację z pliku config.yaml.
        
        Returns:
            Dict zawierający konfigurację
        """
        config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
                                  'config', 'config.yaml')
        
        try:
            import yaml
            with open(config_path, 'r', encoding='utf-8') as file:
                config = yaml.safe_load(file)
                
                self.logger.info(f"Wczytano konfigurację z {config_path}")
                return config.get('analysis', {})
        except Exception as e:
            self.logger.error(f"Błąd wczytywania konfiguracji: {str(e)}")
            # Domyślna konfiguracja w przypadku błędu
            return {
                'data_sources': ['mt5'],
                'timeframes': self.default_timeframes,
                'indicators': self.default_indicators,
                'history_periods': {
                    'M1': 1440,    # 1 dzień
                    'M5': 1440,    # 5 dni
                    'M15': 1440,   # 15 dni
                    'H1': 720,     # 30 dni
                    'D1': 252      # 1 rok
                }
            }
    
    def get_market_data(self, symbol: str, timeframe: str = "M15", 
                      num_bars: int = 100) -> Dict[str, Any]:
        """
        Pobiera dane rynkowe dla danego symbolu i przedziału czasowego.
        
        Args:
            symbol: Symbol instrumentu (np. "EURUSD")
            timeframe: Przedział czasowy (np. "M1", "M5", "M15", "H1", "D1")
            num_bars: Liczba świec do pobrania
            
        Returns:
            Dict zawierający dane rynkowe
        """
        try:
            self.logger.info(f"Pobieranie danych dla {symbol} ({timeframe}), {num_bars} świec")
            
            # Próba pobrania z bazy danych
            cached_data = self._get_cached_data(symbol, timeframe, num_bars)
            if cached_data is not None:
                self.logger.info(f"Znaleziono dane w cache dla {symbol} ({timeframe})")
                return cached_data
            
            # Pobranie danych z MT5
            ohlc_data = self.mt5_client.get_ohlc_data(symbol, timeframe, num_bars)
            if ohlc_data is None or len(ohlc_data) == 0:
                raise ValueError(f"Brak danych dla {symbol} ({timeframe})")
            
            # Konwersja do DataFrame
            df = pd.DataFrame(ohlc_data)
            
            # Dodanie podstawowych wskaźników
            df = self._add_indicators(df)
            
            # Normalizacja danych
            market_data = self._normalize_data(df, symbol, timeframe)
            
            # Zapisanie do cache
            self._cache_data(market_data)
            
            return market_data
        
        except Exception as e:
            self.logger.error(f"Błąd podczas pobierania danych dla {symbol}: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "symbol": symbol,
                "timeframe": timeframe
            }
    
    def get_multiple_timeframes(self, symbol: str, 
                             timeframes: List[str] = None) -> Dict[str, Any]:
        """
        Pobiera dane rynkowe dla danego symbolu w wielu przedziałach czasowych.
        
        Args:
            symbol: Symbol instrumentu (np. "EURUSD")
            timeframes: Lista przedziałów czasowych (np. ["M1", "M5", "H1"])
            
        Returns:
            Dict zawierający dane rynkowe dla różnych przedziałów czasowych
        """
        if timeframes is None:
            timeframes = self.default_timeframes
            
        result = {
            "symbol": symbol,
            "timestamp": datetime.now().isoformat(),
            "data": {}
        }
        
        for tf in timeframes:
            try:
                # Pobierz odpowiednią liczbę świec dla danego timeframe
                num_bars = self.config.get('history_periods', {}).get(tf, 100)
                data = self.get_market_data(symbol, tf, num_bars)
                if data.get("success", True):  # Jeśli nie ma błędu lub success=True
                    result["data"][tf] = data
                else:
                    self.logger.warning(f"Nie udało się pobrać danych dla {symbol} ({tf})")
            except Exception as e:
                self.logger.error(f"Błąd podczas pobierania danych dla {symbol} ({tf}): {str(e)}")
                result["data"][tf] = {
                    "success": False,
                    "error": str(e)
                }
        
        return result
    
    def get_current_market_state(self, symbol: str) -> Dict[str, Any]:
        """
        Pobiera aktualny stan rynku dla danego symbolu.
        
        Args:
            symbol: Symbol instrumentu (np. "EURUSD")
            
        Returns:
            Dict zawierający aktualny stan rynku
        """
        try:
            # Pobieranie aktualnego ticku
            tick = self.mt5_client.get_current_tick(symbol)
            if tick is None:
                raise ValueError(f"Brak danych tick dla {symbol}")
            
            # Pobieranie danych z różnych przedziałów czasowych
            timeframe_data = self.get_multiple_timeframes(symbol)
            
            # Agregacja wskaźników z różnych przedziałów czasowych
            indicators = self._aggregate_indicators(timeframe_data)
            
            # Dodanie informacji o wolumenie i zmienności
            volume_data = self._calculate_volume_metrics(symbol)
            volatility_data = self._calculate_volatility_metrics(symbol)
            
            # Tworzenie wynikowego słownika
            result = {
                "symbol": symbol,
                "timestamp": datetime.now().isoformat(),
                "current_price": {
                    "bid": tick.get("bid", 0),
                    "ask": tick.get("ask", 0),
                    "mid": (tick.get("bid", 0) + tick.get("ask", 0)) / 2
                },
                "daily_change": self._calculate_daily_change(symbol),
                "indicators": indicators,
                "volume": volume_data,
                "volatility": volatility_data,
                "timeframes": timeframe_data
            }
            
            return result
            
        except Exception as e:
            self.logger.error(f"Błąd podczas pobierania stanu rynku dla {symbol}: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "symbol": symbol
            }
    
    def _get_cached_data(self, symbol: str, timeframe: str, 
                      num_bars: int) -> Optional[Dict[str, Any]]:
        """
        Pobiera dane z cache.
        
        Args:
            symbol: Symbol instrumentu
            timeframe: Przedział czasowy
            num_bars: Liczba świec
            
        Returns:
            Dict z danymi lub None, jeśli dane nie są w cache
        """
        try:
            return self.market_data_repository.get_market_data(symbol, timeframe, num_bars)
        except Exception as e:
            self.logger.warning(f"Błąd podczas pobierania danych z cache: {str(e)}")
            return None
    
    def _cache_data(self, market_data: Dict[str, Any]) -> None:
        """
        Zapisuje dane do cache.
        
        Args:
            market_data: Dane rynkowe do zapisania
        """
        try:
            self.market_data_repository.save_market_data(market_data)
        except Exception as e:
            self.logger.warning(f"Błąd podczas zapisywania danych do cache: {str(e)}")
    
    def _add_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Dodaje wskaźniki techniczne do DataFrame.
        
        Args:
            df: DataFrame z danymi OHLC
            
        Returns:
            DataFrame z dodanymi wskaźnikami
        """
        # Upewnij się, że kolumny są w odpowiednim formacie
        required_columns = ['time', 'open', 'high', 'low', 'close', 'tick_volume']
        for col in required_columns:
            if col not in df.columns:
                self.logger.warning(f"Brakująca kolumna: {col}")
                if col == 'time':
                    df['time'] = pd.date_range(end=datetime.now(), periods=len(df), freq='min')
                else:
                    df[col] = 0
        
        # Konwersja czasu na indeks
        if not isinstance(df.index, pd.DatetimeIndex):
            if 'time' in df.columns:
                df['time'] = pd.to_datetime(df['time'])
                df.set_index('time', inplace=True)
        
        # Dodanie wskaźników
        indicators = self.config.get('indicators', self.default_indicators)
        
        if "RSI" in indicators:
            # Relative Strength Index
            delta = df['close'].diff()
            gain = delta.where(delta > 0, 0)
            loss = -delta.where(delta < 0, 0)
            avg_gain = gain.rolling(window=14).mean()
            avg_loss = loss.rolling(window=14).mean()
            rs = avg_gain / avg_loss
            df['RSI'] = 100 - (100 / (1 + rs))
        
        if "MACD" in indicators:
            # Moving Average Convergence Divergence
            ema12 = df['close'].ewm(span=12, adjust=False).mean()
            ema26 = df['close'].ewm(span=26, adjust=False).mean()
            df['MACD'] = ema12 - ema26
            df['MACD_signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
        
        if "MA" in indicators:
            # Moving Averages
            df['MA_20'] = df['close'].rolling(window=20).mean()
            df['MA_50'] = df['close'].rolling(window=50).mean()
            df['MA_200'] = df['close'].rolling(window=200).mean()
        
        if "Bollinger" in indicators:
            # Bollinger Bands
            df['BB_middle'] = df['close'].rolling(window=20).mean()
            df['BB_std'] = df['close'].rolling(window=20).std()
            df['BB_upper'] = df['BB_middle'] + (df['BB_std'] * 2)
            df['BB_lower'] = df['BB_middle'] - (df['BB_std'] * 2)
        
        if "ATR" in indicators:
            # Average True Range
            high_low = df['high'] - df['low']
            high_close = (df['high'] - df['close'].shift()).abs()
            low_close = (df['low'] - df['close'].shift()).abs()
            tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
            df['ATR'] = tr.rolling(window=14).mean()
        
        # Wypełnienie brakujących wartości
        df.fillna(0, inplace=True)
        
        return df
    
    def _normalize_data(self, df: pd.DataFrame, symbol: str, 
                      timeframe: str) -> Dict[str, Any]:
        """
        Normalizuje dane do standardowego formatu.
        
        Args:
            df: DataFrame z danymi OHLC i wskaźnikami
            symbol: Symbol instrumentu
            timeframe: Przedział czasowy
            
        Returns:
            Dict zawierający znormalizowane dane
        """
        # Konwersja do słownika
        data = df.reset_index().to_dict(orient='records')
        
        # Dodanie metadanych
        result = {
            "symbol": symbol,
            "timeframe": timeframe,
            "timestamp": datetime.now().isoformat(),
            "data": data,
            "indicators": {}
        }
        
        # Dodanie najnowszych wartości wskaźników
        for indicator in self.config.get('indicators', self.default_indicators):
            try:
                if indicator == "RSI":
                    result["indicators"]["RSI"] = df['RSI'].iloc[-1]
                elif indicator == "MACD":
                    result["indicators"]["MACD"] = df['MACD'].iloc[-1]
                    result["indicators"]["MACD_signal"] = df['MACD_signal'].iloc[-1]
                elif indicator == "MA":
                    result["indicators"]["MA_20"] = df['MA_20'].iloc[-1]
                    result["indicators"]["MA_50"] = df['MA_50'].iloc[-1]
                    result["indicators"]["MA_200"] = df['MA_200'].iloc[-1]
                elif indicator == "Bollinger":
                    result["indicators"]["BB_upper"] = df['BB_upper'].iloc[-1]
                    result["indicators"]["BB_middle"] = df['BB_middle'].iloc[-1]
                    result["indicators"]["BB_lower"] = df['BB_lower'].iloc[-1]
                elif indicator == "ATR":
                    result["indicators"]["ATR"] = df['ATR'].iloc[-1]
            except Exception as e:
                self.logger.warning(f"Błąd podczas normalizacji wskaźnika {indicator}: {str(e)}")
        
        return result
    
    def _aggregate_indicators(self, timeframe_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Agreguje wskaźniki z różnych przedziałów czasowych.
        
        Args:
            timeframe_data: Dane z różnych przedziałów czasowych
            
        Returns:
            Dict zagregowanych wskaźników
        """
        indicators = {}
        
        # Dla każdego przedziału czasowego
        for tf, data in timeframe_data.get("data", {}).items():
            if not isinstance(data, dict) or "indicators" not in data:
                continue
                
            # Dla każdego wskaźnika
            for ind_name, ind_value in data.get("indicators", {}).items():
                # Dodaj wskaźnik z prefiksem przedziału czasowego
                indicators[f"{tf}_{ind_name}"] = ind_value
        
        return indicators
    
    def _calculate_volume_metrics(self, symbol: str) -> Dict[str, float]:
        """
        Oblicza metryki wolumenu dla danego symbolu.
        
        Args:
            symbol: Symbol instrumentu
            
        Returns:
            Dict zawierający metryki wolumenu
        """
        try:
            # Pobieranie danych H1 z ostatniego tygodnia
            data = self.get_market_data(symbol, "H1", 168)  # 168 godzin = 7 dni
            df = pd.DataFrame(data.get("data", []))
            
            # Jeśli brak danych, zwróć wartości domyślne
            if df.empty:
                return {
                    "current": 0,
                    "avg_daily": 0,
                    "relative_strength": 0
                }
            
            # Obliczanie statystyk wolumenu
            current_vol = df['tick_volume'].iloc[-1] if 'tick_volume' in df.columns else 0
            avg_vol = df['tick_volume'].mean() if 'tick_volume' in df.columns else 0
            
            # Względna siła wolumenu (bieżący wolumen / średni wolumen)
            relative_strength = current_vol / avg_vol if avg_vol > 0 else 0
            
            return {
                "current": current_vol,
                "avg_daily": avg_vol,
                "relative_strength": relative_strength
            }
            
        except Exception as e:
            self.logger.error(f"Błąd podczas obliczania metryk wolumenu: {str(e)}")
            return {
                "current": 0,
                "avg_daily": 0,
                "relative_strength": 0
            }
    
    def _calculate_volatility_metrics(self, symbol: str) -> Dict[str, float]:
        """
        Oblicza metryki zmienności dla danego symbolu.
        
        Args:
            symbol: Symbol instrumentu
            
        Returns:
            Dict zawierający metryki zmienności
        """
        try:
            # Pobieranie danych D1 z ostatnich 30 dni
            data = self.get_market_data(symbol, "D1", 30)
            df = pd.DataFrame(data.get("data", []))
            
            # Jeśli brak danych, zwróć wartości domyślne
            if df.empty:
                return {
                    "daily_range": 0,
                    "atr_14": 0,
                    "historical_volatility": 0
                }
            
            # Dzienny zakres (średni zakres high-low)
            daily_range = (df['high'] - df['low']).mean() if 'high' in df.columns and 'low' in df.columns else 0
            
            # ATR (Average True Range) z okresu 14 dni
            atr = df['ATR'].iloc[-1] if 'ATR' in df.columns else 0
            
            # Historyczna zmienność (odchylenie standardowe zwrotów)
            if 'close' in df.columns:
                returns = df['close'].pct_change().dropna()
                historical_volatility = returns.std() * (252 ** 0.5)  # Annualizacja
            else:
                historical_volatility = 0
            
            return {
                "daily_range": daily_range,
                "atr_14": atr,
                "historical_volatility": historical_volatility
            }
            
        except Exception as e:
            self.logger.error(f"Błąd podczas obliczania metryk zmienności: {str(e)}")
            return {
                "daily_range": 0,
                "atr_14": 0,
                "historical_volatility": 0
            }
    
    def _calculate_daily_change(self, symbol: str) -> Dict[str, float]:
        """
        Oblicza dzienną zmianę dla danego symbolu.
        
        Args:
            symbol: Symbol instrumentu
            
        Returns:
            Dict zawierający informacje o dziennej zmianie
        """
        try:
            # Pobieranie danych D1 z ostatnich 2 dni
            data = self.get_market_data(symbol, "D1", 2)
            df = pd.DataFrame(data.get("data", []))
            
            # Jeśli brak danych, zwróć wartości domyślne
            if df.empty or len(df) < 2 or 'close' not in df.columns or 'open' not in df.columns:
                return {
                    "value": 0,
                    "percent": 0
                }
            
            # Poprzednie zamknięcie
            prev_close = df['close'].iloc[-2]
            
            # Dzisiejsze otwarcie i aktualna cena
            today_open = df['open'].iloc[-1]
            current_price = df['close'].iloc[-1]
            
            # Zmiana od poprzedniego zamknięcia
            change_value = current_price - prev_close
            change_percent = (change_value / prev_close * 100) if prev_close > 0 else 0
            
            # Zmiana od dzisiejszego otwarcia
            intraday_change_value = current_price - today_open
            intraday_change_percent = (intraday_change_value / today_open * 100) if today_open > 0 else 0
            
            return {
                "daily": {
                    "value": change_value,
                    "percent": change_percent
                },
                "intraday": {
                    "value": intraday_change_value,
                    "percent": intraday_change_percent
                }
            }
            
        except Exception as e:
            self.logger.error(f"Błąd podczas obliczania dziennej zmiany: {str(e)}")
            return {
                "daily": {
                    "value": 0,
                    "percent": 0
                },
                "intraday": {
                    "value": 0,
                    "percent": 0
                }
            }


def get_market_data_processor() -> MarketDataProcessor:
    """
    Pobiera singleton instancję MarketDataProcessor.
    
    Returns:
        Instancja MarketDataProcessor
    """
    return MarketDataProcessor() 