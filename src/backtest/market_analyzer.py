"""
Moduł do analizy warunków rynkowych dla automatycznego backtestingu.
Zawiera narzędzia do interpretacji danych historycznych i wyboru optymalnej strategii.
"""

import pandas as pd
import numpy as np
from dataclasses import dataclass
from enum import Enum
from typing import Dict, Tuple, List, Any, Optional
import talib


class MarketCondition(Enum):
    """Typy warunków rynkowych"""
    STRONG_UPTREND = "strong_uptrend"
    MODERATE_UPTREND = "moderate_uptrend"
    STRONG_DOWNTREND = "strong_downtrend"
    MODERATE_DOWNTREND = "moderate_downtrend"
    RANGING = "ranging"
    HIGH_VOLATILITY = "high_volatility"
    LOW_VOLATILITY = "low_volatility"


@dataclass
class MarketAnalysis:
    """Wynik analizy rynku"""
    condition: MarketCondition
    metrics: Dict[str, float]
    recommended_strategy: str
    recommended_params: Dict[str, Any]
    description: str


class MarketAnalyzer:
    """
    Klasa analizująca warunki rynkowe i dostarczająca rekomendacji strategii.
    Używana głównie przez automatyczny tryb backtestingu.
    """
    
    def __init__(self, use_main_system_strategy=True):
        """
        Inicjalizacja analizatora rynku.
        
        Args:
            use_main_system_strategy: Jeśli True, zawsze używa CombinedIndicatorsStrategy jako
                                      głównej strategii, zgodnie z produkcyjnym systemem AgentMT5.
        """
        self.use_main_system_strategy = use_main_system_strategy
        
        # Mapowanie warunków rynkowych na rekomendowane strategie
        # Uwaga: Jeśli use_main_system_strategy=True, te mapowania są używane tylko jako fallback
        self.condition_to_strategy = {
            MarketCondition.STRONG_UPTREND: "CombinedIndicators",
            MarketCondition.MODERATE_UPTREND: "CombinedIndicators", 
            MarketCondition.STRONG_DOWNTREND: "CombinedIndicators",
            MarketCondition.MODERATE_DOWNTREND: "CombinedIndicators",
            MarketCondition.RANGING: "CombinedIndicators",
            MarketCondition.HIGH_VOLATILITY: "CombinedIndicators",
            MarketCondition.LOW_VOLATILITY: "CombinedIndicators"
        }
        
        # Mapowanie warunków rynkowych na opisy dla użytkownika
        self.condition_descriptions = {
            MarketCondition.STRONG_UPTREND: "Silny trend wzrostowy - rekomendowane strategie trendowe",
            MarketCondition.MODERATE_UPTREND: "Umiarkowany trend wzrostowy - rekomendowane strategie trendowe",
            MarketCondition.STRONG_DOWNTREND: "Silny trend spadkowy - rekomendowane strategie trendowe",
            MarketCondition.MODERATE_DOWNTREND: "Umiarkowany trend spadkowy - rekomendowane strategie trendowe", 
            MarketCondition.RANGING: "Rynek w konsolidacji - rekomendowane strategie zasięgowe",
            MarketCondition.HIGH_VOLATILITY: "Wysoka zmienność - rekomendowane strategie momentum",
            MarketCondition.LOW_VOLATILITY: "Niska zmienność - rekomendowane powolne strategie trendowe"
        }
        
        # Bazowe parametry dla CombinedIndicatorsStrategy, zgodne z głównym systemem AgentMT5
        self.base_combined_strategy_params = {
            "weights": {
                'trend': 0.25, 'macd': 0.20, 'rsi': 0.20, 'bb': 0.20, 'candle': 0.15,
            },
            "thresholds": {
                'signal_minimum': 0.3
            },
            "rsi_period": 14,
            "macd_fast": 12,
            "macd_slow": 26,
            "macd_signal": 9,
            "bb_period": 20,
            "bb_std": 2.0,
            "ma_fast_period": 10,
            "ma_slow_period": 50
        }
        
        # Parametry strategii dla różnych warunków rynkowych
        # Teraz wszystkie warunki używają CombinedIndicatorsStrategy, ale z różnymi parametrami
        self.strategy_params = {
            MarketCondition.STRONG_UPTREND: {
                "CombinedIndicators": self._get_adjusted_combined_params({
                    "weights": {'trend': 0.35, 'macd': 0.25, 'rsi': 0.15, 'bb': 0.15, 'candle': 0.10},
                }),
                "SimpleMovingAverage": {"fast_ma_period": 8, "slow_ma_period": 21},
            },
            MarketCondition.MODERATE_UPTREND: {
                "CombinedIndicators": self._get_adjusted_combined_params({
                    "weights": {'trend': 0.30, 'macd': 0.25, 'rsi': 0.15, 'bb': 0.15, 'candle': 0.15},
                }),
                "SimpleMovingAverage": {"fast_ma_period": 10, "slow_ma_period": 30},
            },
            MarketCondition.STRONG_DOWNTREND: {
                "CombinedIndicators": self._get_adjusted_combined_params({
                    "weights": {'trend': 0.35, 'macd': 0.25, 'rsi': 0.15, 'bb': 0.15, 'candle': 0.10},
                }),
                "SimpleMovingAverage": {"fast_ma_period": 8, "slow_ma_period": 21},
            },
            MarketCondition.MODERATE_DOWNTREND: {
                "CombinedIndicators": self._get_adjusted_combined_params({
                    "weights": {'trend': 0.30, 'macd': 0.25, 'rsi': 0.15, 'bb': 0.15, 'candle': 0.15},
                }),
                "SimpleMovingAverage": {"fast_ma_period": 10, "slow_ma_period": 30},
            },
            MarketCondition.RANGING: {
                "CombinedIndicators": self._get_adjusted_combined_params({
                    "weights": {'trend': 0.15, 'macd': 0.15, 'rsi': 0.25, 'bb': 0.30, 'candle': 0.15},
                    "bb_std": 1.8,
                }),
                "BollingerBands": {"bb_period": 20, "bb_std": 2.0},
            },
            MarketCondition.HIGH_VOLATILITY: {
                "CombinedIndicators": self._get_adjusted_combined_params({
                    "weights": {'trend': 0.15, 'macd': 0.30, 'rsi': 0.25, 'bb': 0.20, 'candle': 0.10},
                    "rsi_period": 12,
                    "thresholds": {'signal_minimum': 0.35}
                }),
                "RSI": {"rsi_period": 12, "oversold": 35, "overbought": 65},
            },
            MarketCondition.LOW_VOLATILITY: {
                "CombinedIndicators": self._get_adjusted_combined_params({
                    "weights": {'trend': 0.25, 'macd': 0.30, 'rsi': 0.15, 'bb': 0.20, 'candle': 0.10},
                    "macd_fast": 16,
                    "macd_slow": 32,
                }),
                "MACD": {"fast_ema": 16, "slow_ema": 32, "signal_period": 9},
            }
        }
    
    def _get_adjusted_combined_params(self, adjustments):
        """
        Zwraca parametry CombinedIndicatorsStrategy z zastosowanymi modyfikacjami.
        
        Args:
            adjustments: Słownik zmian do zastosowania względem parametrów bazowych
            
        Returns:
            Słownik z pełnym zestawem parametrów
        """
        params = self.base_combined_strategy_params.copy()
        
        # Aplikuj zagnieżdżone modyfikacje dla słowników takich jak weights i thresholds
        for key, value in adjustments.items():
            if isinstance(value, dict) and key in params and isinstance(params[key], dict):
                # Dla zagnieżdżonych słowników, aktualizujemy tylko podane klucze
                for subkey, subvalue in value.items():
                    params[key][subkey] = subvalue
            else:
                # Dla prostych wartości, po prostu nadpisujemy
                params[key] = value
                
        return params
    
    def analyze_market(self, data: pd.DataFrame, risk_profile: str, strategy_preference: str = None, 
                       use_main_system_params: bool = False) -> MarketAnalysis:
        """
        Analizuje dane historyczne i określa warunki rynkowe oraz rekomenduje strategię
        
        Args:
            data: DataFrame z danymi historycznymi (format OHLCV)
            risk_profile: Profil ryzyka (Konserwatywny, Zrównoważony, Agresywny)
            strategy_preference: Preferowany typ strategii (None oznacza automatyczny wybór)
            use_main_system_params: Jeśli True, używa dokładnie tych samych parametrów co system produkcyjny
            
        Returns:
            MarketAnalysis: Wynik analizy zawierający warunki rynkowe, metryki i rekomendacje
        """
        # Analiza trendu
        trend_metrics = self._analyze_trend(data)
        
        # Analiza zmienności
        volatility_metrics = self._analyze_volatility(data)
        
        # Analiza zakresu (konsolidacji)
        range_metrics = self._analyze_range(data)
        
        # Określenie dominującego warunku rynkowego
        condition = self._determine_market_condition(trend_metrics, volatility_metrics, range_metrics)
        
        # Jeśli używamy parametrów systemu głównego, zawsze wybieramy CombinedIndicatorsStrategy
        # i używamy domyślnych parametrów produkcyjnych
        if use_main_system_params:
            recommended_strategy = "CombinedIndicators"
            recommended_params = self.base_combined_strategy_params.copy()
        else:
            # W przeciwnym razie uwzględniamy preferencje użytkownika i warunki rynkowe
            recommended_strategy = self._get_recommended_strategy(condition, strategy_preference)
            
            # Dostosowanie parametrów do profilu ryzyka
            recommended_params = self._adjust_params_for_risk_profile(
                self.strategy_params[condition][recommended_strategy], risk_profile
            )
        
        # Łączymy wszystkie metryki
        combined_metrics = {**trend_metrics, **volatility_metrics, **range_metrics}
        
        return MarketAnalysis(
            condition=condition,
            metrics=combined_metrics,
            recommended_strategy=recommended_strategy,
            recommended_params=recommended_params,
            description=self.condition_descriptions[condition]
        )
    
    def _analyze_trend(self, data: pd.DataFrame) -> Dict[str, float]:
        """Analizuje siłę i kierunek trendu"""
        # Używamy ADX (Average Directional Index) do określenia siły trendu
        close = data['close'].values
        high = data['high'].values
        low = data['low'].values
        
        # Obliczamy ADX - wskaźnik siły trendu
        adx = talib.ADX(high, low, close, timeperiod=14)
        
        # Obliczamy +DI i -DI, które wskazują kierunek trendu
        plus_di = talib.PLUS_DI(high, low, close, timeperiod=14)
        minus_di = talib.MINUS_DI(high, low, close, timeperiod=14)
        
        # Obliczamy MA - do określenia kierunku trendu
        ma50 = talib.SMA(close, timeperiod=50)
        ma200 = talib.SMA(close, timeperiod=200)
        
        # Obliczamy ostatnie wartości (pomijając NaN)
        adx_last = float(adx[~np.isnan(adx)][-1])
        plus_di_last = float(plus_di[~np.isnan(plus_di)][-1])
        minus_di_last = float(minus_di[~np.isnan(minus_di)][-1])
        
        # Określenie trendu na podstawie MA
        ma_trend = 1 if ma50[-1] > ma200[-1] else -1
        
        # Siła trendu
        trend_strength = adx_last / 100.0  # Normalizacja do 0-1
        
        # Kierunek trendu (1 dla wzrostowego, -1 dla spadkowego)
        trend_direction = 1 if plus_di_last > minus_di_last else -1
        
        return {
            'trend_strength': trend_strength,
            'trend_direction': trend_direction,
            'adx': adx_last,
            'ma_trend': ma_trend
        }
    
    def _analyze_volatility(self, data: pd.DataFrame) -> Dict[str, float]:
        """Analizuje zmienność rynku"""
        # Obliczamy zmienność historyczną (HV) jako odchylenie standardowe dziennych zmian ceny
        close = data['close'].values
        returns = np.log(close[1:] / close[:-1])
        
        # Obliczamy zmienność dla różnych okresów
        volatility_20d = np.std(returns[-20:]) * np.sqrt(252) if len(returns) >= 20 else 0  # Annualizowana
        volatility_50d = np.std(returns[-50:]) * np.sqrt(252) if len(returns) >= 50 else 0
        
        # Obliczamy ATR (Average True Range)
        high = data['high'].values
        low = data['low'].values
        atr = talib.ATR(high, low, close, timeperiod=14)
        atr_last = float(atr[~np.isnan(atr)][-1])
        
        # Normalizacja ATR do zakresu ceny
        atr_relative = atr_last / close[-1]
        
        return {
            'volatility_20d': volatility_20d,
            'volatility_50d': volatility_50d,
            'atr': atr_last,
            'atr_relative': atr_relative
        }
    
    def _analyze_range(self, data: pd.DataFrame) -> Dict[str, float]:
        """Analizuje, czy rynek jest w konsolidacji"""
        # Sprawdzamy, czy cena porusza się w ramach zakresu, używając wskaźnika BB
        close = data['close'].values
        
        # Obliczamy Bollinger Bands
        upper, middle, lower = talib.BBANDS(close, timeperiod=20, nbdevup=2, nbdevdn=2)
        
        # Obliczamy szerokość BB i normalizujemy ją do ceny środkowej
        bb_width = (upper - lower) / middle
        bb_width_last = float(bb_width[~np.isnan(bb_width)][-1])
        
        # Obliczamy RSI jako wskaźnik wykupienia/wyprzedania
        rsi = talib.RSI(close, timeperiod=14)
        rsi_last = float(rsi[~np.isnan(rsi)][-1])
        
        # Obliczamy procent czasu, jaki cena spędziła w przedziale 20-80 na RSI
        rsi_range_time = np.sum((rsi >= 40) & (rsi <= 60)) / len(rsi[~np.isnan(rsi)])
        
        return {
            'bb_width': bb_width_last,
            'rsi': rsi_last,
            'rsi_range_time': rsi_range_time
        }
    
    def _determine_market_condition(self, trend_metrics: Dict[str, float], 
                                   volatility_metrics: Dict[str, float], 
                                   range_metrics: Dict[str, float]) -> MarketCondition:
        """Określa dominujący warunek rynkowy na podstawie obliczonych metryk"""
        
        # Sprawdzenie silnego trendu
        if trend_metrics['trend_strength'] > 0.5:  # ADX > 50
            if trend_metrics['trend_direction'] > 0:
                return MarketCondition.STRONG_UPTREND
            else:
                return MarketCondition.STRONG_DOWNTREND
                
        # Sprawdzenie umiarkowanego trendu
        elif trend_metrics['trend_strength'] > 0.25:  # ADX > 25
            if trend_metrics['trend_direction'] > 0:
                return MarketCondition.MODERATE_UPTREND
            else:
                return MarketCondition.MODERATE_DOWNTREND
                
        # Sprawdzenie wysokiej zmienności
        elif volatility_metrics['atr_relative'] > 0.015:  # ATR > 1.5% ceny
            return MarketCondition.HIGH_VOLATILITY
            
        # Sprawdzenie konsolidacji (zakresu)
        elif range_metrics['bb_width'] < 0.04 and range_metrics['rsi_range_time'] > 0.7:
            return MarketCondition.RANGING
            
        # Sprawdzenie niskiej zmienności
        elif volatility_metrics['atr_relative'] < 0.005:  # ATR < 0.5% ceny
            return MarketCondition.LOW_VOLATILITY
            
        # Domyślny przypadek - umiarkowany trend zgodny z MA
        else:
            if trend_metrics['ma_trend'] > 0:
                return MarketCondition.MODERATE_UPTREND
            else:
                return MarketCondition.MODERATE_DOWNTREND
    
    def _get_recommended_strategy(self, condition: MarketCondition, strategy_preference: str = None) -> str:
        """Zwraca rekomendowaną strategię na podstawie warunku rynkowego i preferencji użytkownika"""
        
        # Jeśli ustawiono flagę używania głównej strategii systemu, zawsze zwracamy CombinedIndicators
        if self.use_main_system_strategy:
            return "CombinedIndicators"
        
        # Mapowanie preferencji użytkownika na strategie
        preference_to_strategy = {
            "Trendowa": ["CombinedIndicators", "SimpleMovingAverage", "MACD"],
            "Oscylacyjna": ["CombinedIndicators", "RSI", "BollingerBands"],
            "Mieszana": ["CombinedIndicators"]
        }
        
        # Jeśli użytkownik ma preferencje, próbujemy je uwzględnić
        if strategy_preference and strategy_preference != "Automatyczny wybór":
            # Pobierz dostępne strategie dla preferencji
            preferred_strategies = preference_to_strategy.get(strategy_preference, [])
            
            # Pobierz strategie dostępne dla warunku rynkowego
            available_strategies = list(self.strategy_params[condition].keys())
            
            # Znajdź część wspólną
            common_strategies = [s for s in preferred_strategies if s in available_strategies]
            
            # Jeśli znaleziono strategie pasujące zarówno do preferencji, jak i warunku rynkowego
            if common_strategies:
                return common_strategies[0]
        
        # W przeciwnym razie użyj domyślnej rekomendacji dla warunku rynkowego
        return self.condition_to_strategy[condition]
    
    def _adjust_params_for_risk_profile(self, strategy_params: Dict[str, Any], risk_profile: str) -> Dict[str, Any]:
        """Dostosowuje parametry strategii do profilu ryzyka użytkownika"""
        adjusted_params = strategy_params.copy()
        
        # Dla SimpleMovingAverage
        if "fast_ma_period" in adjusted_params:
            if risk_profile == "Konserwatywny":
                # Dłuższe okresy MA dla mniejszego ryzyka
                adjusted_params["fast_ma_period"] = int(adjusted_params["fast_ma_period"] * 1.5)
                adjusted_params["slow_ma_period"] = int(adjusted_params["slow_ma_period"] * 1.2)
            elif risk_profile == "Agresywny":
                # Krótsze okresy MA dla większego ryzyka
                adjusted_params["fast_ma_period"] = max(5, int(adjusted_params["fast_ma_period"] * 0.7))
                adjusted_params["slow_ma_period"] = max(15, int(adjusted_params["slow_ma_period"] * 0.8))
        
        # Dla RSI
        if "rsi_period" in adjusted_params and "oversold" in adjusted_params:
            if risk_profile == "Konserwatywny":
                # Bardziej ekstremalne poziomy dla konserwatywnego podejścia
                adjusted_params["oversold"] = max(10, adjusted_params["oversold"] - 10)
                adjusted_params["overbought"] = min(90, adjusted_params["overbought"] + 10)
            elif risk_profile == "Agresywny":
                # Mniej ekstremalne poziomy dla agresywnego podejścia
                adjusted_params["oversold"] = min(40, adjusted_params["oversold"] + 10)
                adjusted_params["overbought"] = max(60, adjusted_params["overbought"] - 10)
        
        # Dla BollingerBands
        if "bb_period" in adjusted_params and "bb_std" in adjusted_params:
            if risk_profile == "Konserwatywny":
                # Szersze pasmo dla konserwatywnego podejścia
                adjusted_params["bb_std"] = min(3.0, adjusted_params["bb_std"] + 0.5)
            elif risk_profile == "Agresywny":
                # Węższe pasmo dla agresywnego podejścia
                adjusted_params["bb_std"] = max(1.5, adjusted_params["bb_std"] - 0.5)
        
        # Dla CombinedIndicators
        if "weights" in adjusted_params:
            if risk_profile == "Konserwatywny":
                # Większa waga dla trendów dla konserwatywnego podejścia
                weights = adjusted_params["weights"]
                weights['trend'] = min(0.4, weights['trend'] + 0.1)
                weights['rsi'] = max(0.1, weights['rsi'] - 0.05)
                if "thresholds" in adjusted_params:
                    adjusted_params["thresholds"]['signal_minimum'] = min(0.4, adjusted_params["thresholds"].get('signal_minimum', 0.2) + 0.1)
            elif risk_profile == "Agresywny":
                # Większa waga dla oscylatorów dla agresywnego podejścia
                weights = adjusted_params["weights"]
                weights['trend'] = max(0.1, weights['trend'] - 0.05)
                weights['rsi'] = min(0.4, weights['rsi'] + 0.1)
                if "thresholds" in adjusted_params:
                    adjusted_params["thresholds"]['signal_minimum'] = max(0.1, adjusted_params["thresholds"].get('signal_minimum', 0.2) - 0.1)
        
        return adjusted_params 