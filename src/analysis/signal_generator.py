#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Moduł do generowania sygnałów tradingowych.

Ten moduł zawiera funkcje i klasy do generowania sygnałów tradingowych
na podstawie analizy danych rynkowych przy użyciu modeli AI.
"""

import os
import json
import time
import logging
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Union, Tuple
from enum import Enum
import numpy as np
import pandas as pd

# Importy wewnętrzne
from src.analysis.market_data_processor import MarketDataProcessor, get_market_data_processor
from src.ai_models.ai_router import AIRouter, get_ai_router
from src.database.signal_repository import SignalRepository, get_signal_repository
from src.utils.config_manager import ConfigManager

# Konfiguracja loggera
logger = logging.getLogger('trading_agent.analysis.signal_generator')


class SignalType(Enum):
    """Typ sygnału tradingowego."""
    BUY = "BUY"
    SELL = "SELL"
    CLOSE = "CLOSE"
    NO_ACTION = "NO_ACTION"


class SignalStrength(Enum):
    """Siła sygnału tradingowego."""
    WEAK = "WEAK"
    MODERATE = "MODERATE"
    STRONG = "STRONG"
    VERY_STRONG = "VERY_STRONG"


class SignalSource(Enum):
    """Źródło sygnału tradingowego."""
    TECHNICAL = "TECHNICAL"  # Na podstawie analizy technicznej
    FUNDAMENTAL = "FUNDAMENTAL"  # Na podstawie analizy fundamentalnej
    AI = "AI"  # Na podstawie analizy AI
    COMBINED = "COMBINED"  # Kombinacja różnych źródeł
    MANUAL = "MANUAL"  # Ręcznie wprowadzony sygnał


class SignalGenerator:
    """Klasa do generowania sygnałów tradingowych na podstawie analizy danych rynkowych."""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        """Implementacja wzorca Singleton."""
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(SignalGenerator, cls).__new__(cls)
                cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """Inicjalizacja generatora sygnałów."""
        if self._initialized:
            return
            
        self.logger = logging.getLogger('trading_agent.analysis.signal_generator')
        self.logger.info("Inicjalizacja SignalGenerator")
        
        # Inicjalizacja zależności
        self.market_data_processor = get_market_data_processor()
        self.ai_router = get_ai_router()
        self.signal_repository = get_signal_repository()
        
        # Parametry konfiguracyjne
        self.config_manager = ConfigManager()
        self.config = self._load_config()
        
        # Buforowanie ostatnich sygnałów
        self.signal_cache = {}
        self.signal_history = {}
        
        # Inicjalizacja strategii
        self._initialize_strategies()
        
        self._initialized = True
        
    def _load_config(self) -> Dict[str, Any]:
        """
        Wczytuje konfigurację z pliku config.yaml.
        
        Returns:
            Dict zawierający konfigurację
        """
        try:
            config = self.config_manager.get_config_section('signals')
            self.logger.info("Wczytano konfigurację dla generatora sygnałów")
            return config
        except Exception as e:
            self.logger.error(f"Błąd wczytywania konfiguracji: {str(e)}")
            # Domyślna konfiguracja w przypadku błędu
            return {
                'strategies': ['technical', 'ai'],
                'threshold': 0.65,
                'confirmation_count': 2,
                'timeframes': ['M15', 'H1', 'H4'],
                'use_ml_models': True,
                'signal_expiry': 3600,  # 1 godzina w sekundach
                'min_confidence': 0.7,
                'max_signals_per_symbol': 3
            }
            
    def _initialize_strategies(self):
        """Inicjalizacja strategii tradingowych."""
        self.strategies = {}
        
        # Rejestracja strategii na podstawie konfiguracji
        for strategy_name in self.config.get('strategies', []):
            self.logger.info(f"Inicjalizacja strategii: {strategy_name}")
            
            if strategy_name == 'technical':
                self.strategies['technical'] = self._technical_analysis_strategy
            elif strategy_name == 'ai':
                self.strategies['ai'] = self._ai_analysis_strategy
            elif strategy_name == 'combined':
                self.strategies['combined'] = self._combined_strategy
            else:
                self.logger.warning(f"Nieznana strategia: {strategy_name}")
        
    def generate_signals(self, symbol: str, timeframes: List[str] = None) -> Dict[str, Any]:
        """
        Generuje sygnały tradingowe dla wybranego symbolu.
        
        Args:
            symbol: Symbol instrumentu (np. 'EURUSD', 'BTCUSD')
            timeframes: Lista przedziałów czasowych do analizy
            
        Returns:
            Dict zawierający wygenerowane sygnały
        """
        start_time = time.time()
        self.logger.info(f"Generowanie sygnałów dla {symbol}")
        
        # Jeśli nie podano przedziałów czasowych, użyj domyślnych z konfiguracji
        if timeframes is None:
            timeframes = self.config.get('timeframes', ['M15', 'H1', 'H4'])
            
        # Pobierz dane rynkowe z procesora danych
        market_data = self.market_data_processor.get_multiple_timeframes(symbol, timeframes)
        
        if not market_data.get('success', False):
            error_msg = market_data.get('error', 'Nieznany błąd')
            self.logger.error(f"Błąd pobierania danych rynkowych: {error_msg}")
            return {
                'success': False,
                'error': error_msg,
                'signals': []
            }
            
        # Generuj sygnały z każdej dostępnej strategii
        all_signals = []
        for strategy_name, strategy_func in self.strategies.items():
            try:
                signals = strategy_func(symbol, market_data)
                if signals and isinstance(signals, list):
                    for signal in signals:
                        signal['strategy'] = strategy_name
                    all_signals.extend(signals)
            except Exception as e:
                self.logger.error(f"Błąd w strategii {strategy_name}: {str(e)}")
                
        # Agreguj i filtruj sygnały
        final_signals = self._aggregate_signals(all_signals)
        
        # Zapisz sygnały do bazy danych
        if final_signals:
            for signal in final_signals:
                self._save_signal(signal)
            
        # Aktualizuj cache sygnałów
        self.signal_cache[symbol] = {
            'timestamp': time.time(),
            'signals': final_signals
        }
        
        # Dodaj sygnały do historii
        if symbol not in self.signal_history:
            self.signal_history[symbol] = []
        self.signal_history[symbol].append({
            'timestamp': time.time(),
            'signals': final_signals
        })
        
        # Przygotuj wynik
        result = {
            'success': True,
            'symbol': symbol,
            'signals': final_signals,
            'timeframes': timeframes,
            'generation_time': time.time() - start_time
        }
        
        self.logger.info(f"Wygenerowano {len(final_signals)} sygnałów dla {symbol} w {result['generation_time']:.2f}s")
        return result
            
    def _technical_analysis_strategy(self, symbol: str, market_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Strategia bazująca na analizie technicznej.
        
        Args:
            symbol: Symbol instrumentu
            market_data: Dane rynkowe
            
        Returns:
            Lista sygnałów
        """
        signals = []
        
        # Pobierz dane z różnych przedziałów czasowych
        for timeframe, data in market_data.get('data', {}).items():
            # Pomiń jeśli brak danych
            if not isinstance(data, dict) or 'indicators' not in data:
                continue
                
            indicators = data.get('indicators', {})
            df = pd.DataFrame(data.get('candles', []))
            
            # Nie możemy generować sygnałów bez danych
            if df.empty:
                continue
                
            # Generowanie sygnałów na podstawie RSI
            if 'RSI' in indicators:
                rsi = indicators['RSI']
                
                # Sygnał kupna: RSI < 30 (wykupienie)
                if rsi < 30:
                    signals.append({
                        'type': SignalType.BUY.value,
                        'symbol': symbol,
                        'timeframe': timeframe,
                        'price': df.iloc[-1]['close'],
                        'timestamp': time.time(),
                        'confidence': 0.7 + (30 - rsi) / 100,  # Im niższy RSI, tym wyższa pewność
                        'source': SignalSource.TECHNICAL.value,
                        'reason': f"RSI wykupienie ({rsi:.2f})",
                        'strength': SignalStrength.MODERATE.value,
                        'expiry': time.time() + self.config.get('signal_expiry', 3600)
                    })
                
                # Sygnał sprzedaży: RSI > 70 (wyprzedanie)
                elif rsi > 70:
                    signals.append({
                        'type': SignalType.SELL.value,
                        'symbol': symbol,
                        'timeframe': timeframe,
                        'price': df.iloc[-1]['close'],
                        'timestamp': time.time(),
                        'confidence': 0.7 + (rsi - 70) / 100,  # Im wyższy RSI, tym wyższa pewność
                        'source': SignalSource.TECHNICAL.value,
                        'reason': f"RSI wyprzedanie ({rsi:.2f})",
                        'strength': SignalStrength.MODERATE.value,
                        'expiry': time.time() + self.config.get('signal_expiry', 3600)
                    })
            
            # Generowanie sygnałów na podstawie MACD
            if 'MACD' in indicators and 'MACD_signal' in indicators:
                macd = indicators['MACD']
                macd_signal = indicators['MACD_signal']
                
                # Sygnał kupna: MACD przecina sygnał od dołu
                if macd > macd_signal and macd < 0:
                    signals.append({
                        'type': SignalType.BUY.value,
                        'symbol': symbol,
                        'timeframe': timeframe,
                        'price': df.iloc[-1]['close'],
                        'timestamp': time.time(),
                        'confidence': 0.75,
                        'source': SignalSource.TECHNICAL.value,
                        'reason': "MACD przecięcie linii sygnału od dołu",
                        'strength': SignalStrength.MODERATE.value,
                        'expiry': time.time() + self.config.get('signal_expiry', 3600)
                    })
                
                # Sygnał sprzedaży: MACD przecina sygnał od góry
                elif macd < macd_signal and macd > 0:
                    signals.append({
                        'type': SignalType.SELL.value,
                        'symbol': symbol,
                        'timeframe': timeframe,
                        'price': df.iloc[-1]['close'],
                        'timestamp': time.time(),
                        'confidence': 0.75,
                        'source': SignalSource.TECHNICAL.value,
                        'reason': "MACD przecięcie linii sygnału od góry",
                        'strength': SignalStrength.MODERATE.value,
                        'expiry': time.time() + self.config.get('signal_expiry', 3600)
                    })
            
            # Generowanie sygnałów na podstawie Bollinger Bands
            if all(k in indicators for k in ['BB_upper', 'BB_lower']):
                bb_upper = indicators['BB_upper']
                bb_lower = indicators['BB_lower']
                current_price = df.iloc[-1]['close']
                
                # Sygnał kupna: Cena poniżej dolnego pasma
                if current_price < bb_lower:
                    signals.append({
                        'type': SignalType.BUY.value,
                        'symbol': symbol,
                        'timeframe': timeframe,
                        'price': current_price,
                        'timestamp': time.time(),
                        'confidence': 0.8,
                        'source': SignalSource.TECHNICAL.value,
                        'reason': "Cena poniżej dolnego pasma Bollingera",
                        'strength': SignalStrength.STRONG.value,
                        'expiry': time.time() + self.config.get('signal_expiry', 3600)
                    })
                
                # Sygnał sprzedaży: Cena powyżej górnego pasma
                elif current_price > bb_upper:
                    signals.append({
                        'type': SignalType.SELL.value,
                        'symbol': symbol,
                        'timeframe': timeframe,
                        'price': current_price,
                        'timestamp': time.time(),
                        'confidence': 0.8,
                        'source': SignalSource.TECHNICAL.value,
                        'reason': "Cena powyżej górnego pasma Bollingera",
                        'strength': SignalStrength.STRONG.value,
                        'expiry': time.time() + self.config.get('signal_expiry', 3600)
                    })
                
        return signals
        
    def _ai_analysis_strategy(self, symbol: str, market_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Strategia bazująca na analizie AI.
        
        Args:
            symbol: Symbol instrumentu
            market_data: Dane rynkowe
            
        Returns:
            Lista sygnałów
        """
        signals = []
        
        # Wykonaj analizę AI za pomocą routera AI
        ai_analysis = self.ai_router.analyze_market_data(market_data, "complete")
        
        if not ai_analysis.get('success', False):
            self.logger.warning(f"Błąd analizy AI: {ai_analysis.get('error', 'Nieznany błąd')}")
            return signals
            
        # Wyodrębnij analizę
        analysis = ai_analysis.get('analysis', {})
        
        # Pobierz obecnie najbardziej dokładny timeframe
        current_price = None
        current_timeframe = None
        
        for timeframe, data in market_data.get('data', {}).items():
            if isinstance(data, dict) and 'candles' in data and data['candles']:
                candles = data['candles']
                if candles and isinstance(candles, list) and candles[-1]:
                    current_price = candles[-1].get('close')
                    current_timeframe = timeframe
                    break
        
        if not current_price or not current_timeframe:
            self.logger.warning(f"Brak aktualnej ceny dla {symbol}")
            return signals
        
        # Przetwarzanie sygnałów z analizy AI
        ai_signals = analysis.get('signals', [])
        trend = analysis.get('trend', 'neutral')
        sentiment = analysis.get('sentiment', 'neutral')
        strength = analysis.get('strength', 0)
        confidence_level = analysis.get('confidence_level', 0)
        
        # Przekształć sygnały AI na nasze sygnały
        for ai_signal in ai_signals:
            if isinstance(ai_signal, dict):
                signal_type = ai_signal.get('action', '').upper()
                signal_reason = ai_signal.get('reason', 'Analiza AI')
                signal_confidence = ai_signal.get('confidence', confidence_level)
                
                # Mapuj typ sygnału
                if signal_type in [SignalType.BUY.value, SignalType.SELL.value, SignalType.CLOSE.value]:
                    signal_obj = {
                        'type': signal_type,
                        'symbol': symbol,
                        'timeframe': current_timeframe,
                        'price': current_price,
                        'timestamp': time.time(),
                        'confidence': signal_confidence,
                        'source': SignalSource.AI.value,
                        'reason': signal_reason,
                        'strength': self._determine_signal_strength(signal_confidence),
                        'expiry': time.time() + self.config.get('signal_expiry', 3600),
                        'ai_models': ai_analysis.get('models_used', [])
                    }
                    signals.append(signal_obj)
            elif isinstance(ai_signal, str):
                # Próba sparsowania stringa
                parts = ai_signal.split(':')
                if len(parts) >= 2:
                    signal_type = parts[0].strip().upper()
                    signal_reason = parts[1].strip()
                    
                    if signal_type in [SignalType.BUY.value, SignalType.SELL.value, SignalType.CLOSE.value]:
                        signal_obj = {
                            'type': signal_type,
                            'symbol': symbol,
                            'timeframe': current_timeframe,
                            'price': current_price,
                            'timestamp': time.time(),
                            'confidence': confidence_level,
                            'source': SignalSource.AI.value,
                            'reason': signal_reason,
                            'strength': self._determine_signal_strength(confidence_level),
                            'expiry': time.time() + self.config.get('signal_expiry', 3600),
                            'ai_models': ai_analysis.get('models_used', [])
                        }
                        signals.append(signal_obj)
        
        # Jeśli nie ma konkretnych sygnałów, ale jest silny trend/sentyment, generuj sygnał
        if not signals and confidence_level > self.config.get('min_confidence', 0.7):
            if trend == 'bullish' or sentiment == 'bullish':
                signals.append({
                    'type': SignalType.BUY.value,
                    'symbol': symbol,
                    'timeframe': current_timeframe,
                    'price': current_price,
                    'timestamp': time.time(),
                    'confidence': confidence_level,
                    'source': SignalSource.AI.value,
                    'reason': f"Pozytywny trend/sentyment: {trend}/{sentiment}",
                    'strength': self._determine_signal_strength(confidence_level),
                    'expiry': time.time() + self.config.get('signal_expiry', 3600),
                    'ai_models': ai_analysis.get('models_used', [])
                })
            elif trend == 'bearish' or sentiment == 'bearish':
                signals.append({
                    'type': SignalType.SELL.value,
                    'symbol': symbol,
                    'timeframe': current_timeframe,
                    'price': current_price,
                    'timestamp': time.time(),
                    'confidence': confidence_level,
                    'source': SignalSource.AI.value,
                    'reason': f"Negatywny trend/sentyment: {trend}/{sentiment}",
                    'strength': self._determine_signal_strength(confidence_level),
                    'expiry': time.time() + self.config.get('signal_expiry', 3600),
                    'ai_models': ai_analysis.get('models_used', [])
                })
                
        return signals
    
    def _combined_strategy(self, symbol: str, market_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Strategia kombinowana łącząca analizę techniczną i AI.
        
        Args:
            symbol: Symbol instrumentu
            market_data: Dane rynkowe
            
        Returns:
            Lista sygnałów
        """
        # Pobierz sygnały z poszczególnych strategii
        technical_signals = self._technical_analysis_strategy(symbol, market_data)
        ai_signals = self._ai_analysis_strategy(symbol, market_data)
        
        # Zapisz wszystkie sygnały
        all_signals = technical_signals + ai_signals
        
        # Grupuj sygnały według typu (BUY/SELL)
        buy_signals = [s for s in all_signals if s['type'] == SignalType.BUY.value]
        sell_signals = [s for s in all_signals if s['type'] == SignalType.SELL.value]
        close_signals = [s for s in all_signals if s['type'] == SignalType.CLOSE.value]
        
        # Sprawdź, czy mamy potwierdzenie z obu strategii
        combined_signals = []
        
        # Jeśli jest wystarczająca liczba sygnałów kupna, generuj kombinowany sygnał kupna
        if len(buy_signals) >= self.config.get('confirmation_count', 2):
            # Obliczanie średniej pewności i najczęstszej przyczyny
            avg_confidence = sum(s.get('confidence', 0) for s in buy_signals) / len(buy_signals)
            max_strength = max(s.get('strength', SignalStrength.MODERATE.value) for s in buy_signals)
            
            # Lista wszystkich źródeł sygnałów
            sources = [s.get('source') for s in buy_signals]
            
            combined_signals.append({
                'type': SignalType.BUY.value,
                'symbol': symbol,
                'timeframe': 'COMBINED',
                'price': buy_signals[0]['price'],  # Używamy ceny z pierwszego sygnału
                'timestamp': time.time(),
                'confidence': avg_confidence,
                'source': SignalSource.COMBINED.value,
                'reason': f"Potwierdzony sygnał ({len(buy_signals)} źródeł: {', '.join(set(sources))})",
                'strength': max_strength,
                'expiry': time.time() + self.config.get('signal_expiry', 3600) * 2,  # Dłuższy czas wygaśnięcia
                'child_signals': buy_signals
            })
            
        # Jeśli jest wystarczająca liczba sygnałów sprzedaży, generuj kombinowany sygnał sprzedaży
        if len(sell_signals) >= self.config.get('confirmation_count', 2):
            # Obliczanie średniej pewności
            avg_confidence = sum(s.get('confidence', 0) for s in sell_signals) / len(sell_signals)
            max_strength = max(s.get('strength', SignalStrength.MODERATE.value) for s in sell_signals)
            
            # Lista wszystkich źródeł sygnałów
            sources = [s.get('source') for s in sell_signals]
            
            combined_signals.append({
                'type': SignalType.SELL.value,
                'symbol': symbol,
                'timeframe': 'COMBINED',
                'price': sell_signals[0]['price'],  # Używamy ceny z pierwszego sygnału
                'timestamp': time.time(),
                'confidence': avg_confidence,
                'source': SignalSource.COMBINED.value,
                'reason': f"Potwierdzony sygnał ({len(sell_signals)} źródeł: {', '.join(set(sources))})",
                'strength': max_strength,
                'expiry': time.time() + self.config.get('signal_expiry', 3600) * 2,  # Dłuższy czas wygaśnięcia
                'child_signals': sell_signals
            })
        
        # Dodaj wszystkie sygnały zamknięcia
        combined_signals.extend(close_signals)
        
        return combined_signals
    
    def _determine_signal_strength(self, confidence: float) -> str:
        """
        Określa siłę sygnału na podstawie poziomu pewności.
        
        Args:
            confidence: Poziom pewności (0.0 - 1.0)
            
        Returns:
            Siła sygnału jako wartość enum
        """
        if confidence < 0.65:
            return SignalStrength.WEAK.value
        elif confidence < 0.8:
            return SignalStrength.MODERATE.value
        elif confidence < 0.9:
            return SignalStrength.STRONG.value
        else:
            return SignalStrength.VERY_STRONG.value
        
    def _aggregate_signals(self, signals: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Agreguje i filtruje sygnały.
        
        Args:
            signals: Lista sygnałów do agregacji
            
        Returns:
            Lista przefiltrowanych sygnałów
        """
        if not signals:
            return []
            
        # Filtruj sygnały poniżej progu pewności
        min_confidence = self.config.get('min_confidence', 0.7)
        signals = [s for s in signals if s.get('confidence', 0) >= min_confidence]
        
        # Sortuj według pewności (malejąco)
        signals = sorted(signals, key=lambda s: s.get('confidence', 0), reverse=True)
        
        # Ogranicz liczbę sygnałów per symbol
        max_signals = self.config.get('max_signals_per_symbol', 3)
        if len(signals) > max_signals:
            signals = signals[:max_signals]
            
        return signals
        
    def _save_signal(self, signal: Dict[str, Any]) -> bool:
        """
        Zapisuje sygnał do bazy danych.
        
        Args:
            signal: Sygnał do zapisania
            
        Returns:
            True jeśli zapisano pomyślnie, False w przeciwnym razie
        """
        try:
            # Usuń niepotrzebne klucze przed zapisem
            signal_to_save = signal.copy()
            if 'child_signals' in signal_to_save:
                del signal_to_save['child_signals']
                
            # Dodaj timestamp jeśli brak
            if 'timestamp' not in signal_to_save:
                signal_to_save['timestamp'] = time.time()
                
            # Zapisz do repozytorium
            result = self.signal_repository.save_signal(signal_to_save)
            return result.get('success', False)
        except Exception as e:
            self.logger.error(f"Błąd podczas zapisywania sygnału: {str(e)}")
            return False
            
    def get_active_signals(self, symbol: str = None) -> Dict[str, Any]:
        """
        Pobiera aktywne sygnały z bazy danych.
        
        Args:
            symbol: Symbol instrumentu (opcjonalny)
            
        Returns:
            Dict zawierający aktywne sygnały
        """
        try:
            current_time = time.time()
            
            # Pobierz sygnały z bazy
            if symbol:
                signals = self.signal_repository.get_signals_by_symbol(symbol)
            else:
                signals = self.signal_repository.get_all_signals()
                
            # Filtruj sygnały, które nie wygasły
            active_signals = [
                s for s in signals 
                if s.get('expiry', 0) > current_time
            ]
            
            return {
                'success': True,
                'signals': active_signals,
                'count': len(active_signals)
            }
        except Exception as e:
            self.logger.error(f"Błąd podczas pobierania aktywnych sygnałów: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'signals': []
            }
            
    def get_signal_history(self, symbol: str, limit: int = 50) -> Dict[str, Any]:
        """
        Pobiera historię sygnałów dla danego symbolu.
        
        Args:
            symbol: Symbol instrumentu
            limit: Maksymalna liczba sygnałów
            
        Returns:
            Dict zawierający historię sygnałów
        """
        try:
            signals = self.signal_repository.get_signals_by_symbol(symbol, limit)
            
            return {
                'success': True,
                'symbol': symbol,
                'signals': signals,
                'count': len(signals)
            }
        except Exception as e:
            self.logger.error(f"Błąd podczas pobierania historii sygnałów: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'signals': []
            }


def get_signal_generator() -> SignalGenerator:
    """
    Zwraca instancję SignalGenerator (Singleton).
    
    Returns:
        Instancja SignalGenerator
    """
    return SignalGenerator() 