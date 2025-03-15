#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Implementacja podstawowych wskaźników technicznych do analizy danych rynkowych.
Wskaźniki te będą wykorzystywane w procesie generowania sygnałów handlowych.
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from typing import Dict, List, Tuple, Optional, Union

def calculate_sma(data: Union[np.ndarray, pd.Series], period: int) -> np.ndarray:
    """
    Oblicza Simple Moving Average (SMA).
    
    Args:
        data: Dane cenowe (np.ndarray lub pd.Series)
        period: Okres SMA
        
    Returns:
        np.ndarray: Wartości SMA
    """
    sma = np.zeros_like(data)
    sma[:] = np.nan
    
    for i in range(period - 1, len(data)):
        sma[i] = np.mean(data[i - period + 1:i + 1])
    
    return sma

def calculate_ema(data: Union[np.ndarray, pd.Series], period: int) -> np.ndarray:
    """
    Oblicza Exponential Moving Average (EMA).
    
    Args:
        data: Dane cenowe (np.ndarray lub pd.Series)
        period: Okres EMA
        
    Returns:
        np.ndarray: Wartości EMA
    """
    ema = np.zeros_like(data)
    ema[:] = np.nan
    
    # Obliczenie współczynnika smoothing
    alpha = 2 / (period + 1)
    
    # Inicjalizacja EMA jako SMA dla pierwszych 'period' elementów
    ema[period - 1] = np.mean(data[:period])
    
    # Obliczenie EMA dla pozostałych elementów
    for i in range(period, len(data)):
        ema[i] = data[i] * alpha + ema[i - 1] * (1 - alpha)
    
    return ema

def calculate_rsi(data: Union[np.ndarray, pd.Series], period: int = 14) -> np.ndarray:
    """
    Oblicza Relative Strength Index (RSI).
    
    Args:
        data: Dane cenowe (np.ndarray lub pd.Series)
        period: Okres RSI (domyślnie 14)
        
    Returns:
        np.ndarray: Wartości RSI
    """
    # Przekształcenie danych wejściowych na tablicę numpy
    if isinstance(data, pd.Series):
        data = data.values
    
    # Inicjalizacja tablicy wynikowej
    rsi = np.zeros_like(data)
    rsi[:] = np.nan
    
    # Obliczenie różnic cen
    deltas = np.diff(data)
    
    # Podział na zyski i straty
    gains = np.where(deltas > 0, deltas, 0)
    losses = np.where(deltas < 0, -deltas, 0)
    
    # Inicjalizacja średnich
    avg_gain = np.sum(gains[:period]) / period
    avg_loss = np.sum(losses[:period]) / period
    
    # Obliczenie pierwszego RSI
    if avg_loss == 0:
        rsi[period] = 100
    else:
        rs = avg_gain / avg_loss
        rsi[period] = 100 - (100 / (1 + rs))
    
    # Obliczenie pozostałych wartości RSI
    for i in range(period + 1, len(data)):
        avg_gain = (avg_gain * (period - 1) + gains[i - 1]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i - 1]) / period
        
        if avg_loss == 0:
            rsi[i] = 100
        else:
            rs = avg_gain / avg_loss
            rsi[i] = 100 - (100 / (1 + rs))
    
    return rsi

def calculate_macd(data: Union[np.ndarray, pd.Series], fast_period: int = 12, 
                 slow_period: int = 26, signal_period: int = 9) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Oblicza Moving Average Convergence Divergence (MACD).
    
    Args:
        data: Dane cenowe (np.ndarray lub pd.Series)
        fast_period: Okres szybkiej EMA (domyślnie 12)
        slow_period: Okres wolnej EMA (domyślnie 26)
        signal_period: Okres linii sygnalowej (domyślnie 9)
        
    Returns:
        Tuple[np.ndarray, np.ndarray, np.ndarray]: (MACD, Signal, Histogram)
    """
    # Obliczenie EMA
    fast_ema = calculate_ema(data, fast_period)
    slow_ema = calculate_ema(data, slow_period)
    
    # Obliczenie MACD
    macd_line = fast_ema - slow_ema
    
    # Obliczenie linii sygnalowej
    signal_line = calculate_ema(macd_line, signal_period)
    
    # Obliczenie histogramu
    histogram = macd_line - signal_line
    
    return macd_line, signal_line, histogram

def calculate_bollinger_bands(data: Union[np.ndarray, pd.Series], period: int = 20, 
                            num_std: float = 2.0) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Oblicza Bollinger Bands.
    
    Args:
        data: Dane cenowe (np.ndarray lub pd.Series)
        period: Okres SMA (domyślnie 20)
        num_std: Liczba odchyleń standardowych (domyślnie 2.0)
        
    Returns:
        Tuple[np.ndarray, np.ndarray, np.ndarray]: (Górne pasmo, SMA, Dolne pasmo)
    """
    # Obliczenie SMA
    middle_band = calculate_sma(data, period)
    
    # Inicjalizacja pasm
    upper_band = np.zeros_like(data)
    lower_band = np.zeros_like(data)
    upper_band[:] = np.nan
    lower_band[:] = np.nan
    
    # Obliczenie pasm
    for i in range(period - 1, len(data)):
        std = np.std(data[i - period + 1:i + 1])
        upper_band[i] = middle_band[i] + (std * num_std)
        lower_band[i] = middle_band[i] - (std * num_std)
    
    return upper_band, middle_band, lower_band

def calculate_stochastic_oscillator(high: Union[np.ndarray, pd.Series], 
                                  low: Union[np.ndarray, pd.Series], 
                                  close: Union[np.ndarray, pd.Series], 
                                  k_period: int = 14, 
                                  d_period: int = 3) -> Tuple[np.ndarray, np.ndarray]:
    """
    Oblicza Stochastic Oscillator.
    
    Args:
        high: Najwyższe ceny (np.ndarray lub pd.Series)
        low: Najniższe ceny (np.ndarray lub pd.Series)
        close: Ceny zamknięcia (np.ndarray lub pd.Series)
        k_period: Okres %K (domyślnie 14)
        d_period: Okres %D (domyślnie 3)
        
    Returns:
        Tuple[np.ndarray, np.ndarray]: (%K, %D)
    """
    # Konwersja na tablice numpy
    if isinstance(high, pd.Series):
        high = high.values
    if isinstance(low, pd.Series):
        low = low.values
    if isinstance(close, pd.Series):
        close = close.values
    
    # Inicjalizacja tablic wynikowych
    k = np.zeros_like(close)
    k[:] = np.nan
    d = np.zeros_like(close)
    d[:] = np.nan
    
    # Obliczenie %K
    for i in range(k_period - 1, len(close)):
        highest_high = np.max(high[i - k_period + 1:i + 1])
        lowest_low = np.min(low[i - k_period + 1:i + 1])
        
        if highest_high - lowest_low == 0:
            k[i] = 50  # Wartość neutralna w przypadku braku zmienności
        else:
            k[i] = 100 * (close[i] - lowest_low) / (highest_high - lowest_low)
    
    # Obliczenie %D jako SMA %K
    d = calculate_sma(k, d_period)
    
    return k, d

def calculate_atr(high: Union[np.ndarray, pd.Series], 
                low: Union[np.ndarray, pd.Series], 
                close: Union[np.ndarray, pd.Series], 
                period: int = 14) -> np.ndarray:
    """
    Oblicza Average True Range (ATR).
    
    Args:
        high: Najwyższe ceny (np.ndarray lub pd.Series)
        low: Najniższe ceny (np.ndarray lub pd.Series)
        close: Ceny zamknięcia (np.ndarray lub pd.Series)
        period: Okres ATR (domyślnie 14)
        
    Returns:
        np.ndarray: Wartości ATR
    """
    # Konwersja na tablice numpy
    if isinstance(high, pd.Series):
        high = high.values
    if isinstance(low, pd.Series):
        low = low.values
    if isinstance(close, pd.Series):
        close = close.values
    
    # Inicjalizacja tablicy TR
    tr = np.zeros(len(close))
    
    # Obliczenie TR
    for i in range(1, len(close)):
        tr[i] = max(
            high[i] - low[i],                     # Zakres bieżący
            abs(high[i] - close[i - 1]),         # Zakres względem poprzedniego zamknięcia (do góry)
            abs(low[i] - close[i - 1])            # Zakres względem poprzedniego zamknięcia (w dół)
        )
    
    # Inicjalizacja ATR
    atr = np.zeros_like(close)
    atr[:] = np.nan
    
    # Obliczenie pierwszego ATR jako średniej TR
    atr[period - 1] = np.mean(tr[1:period])
    
    # Obliczenie pozostałych wartości ATR
    for i in range(period, len(close)):
        atr[i] = (atr[i - 1] * (period - 1) + tr[i]) / period
    
    return atr

def calculate_adx(high: Union[np.ndarray, pd.Series], 
                low: Union[np.ndarray, pd.Series], 
                close: Union[np.ndarray, pd.Series], 
                period: int = 14) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Oblicza Average Directional Index (ADX) oraz linie +DI i -DI.
    
    Args:
        high: Najwyższe ceny (np.ndarray lub pd.Series)
        low: Najniższe ceny (np.ndarray lub pd.Series)
        close: Ceny zamknięcia (np.ndarray lub pd.Series)
        period: Okres ADX (domyślnie 14)
        
    Returns:
        Tuple[np.ndarray, np.ndarray, np.ndarray]: (ADX, +DI, -DI)
    """
    # Konwersja na tablice numpy
    if isinstance(high, pd.Series):
        high = high.values
    if isinstance(low, pd.Series):
        low = low.values
    if isinstance(close, pd.Series):
        close = close.values
    
    # Inicjalizacja tablic
    tr = np.zeros(len(close))
    plus_dm = np.zeros(len(close))
    minus_dm = np.zeros(len(close))
    
    # Obliczenie TR i DM
    for i in range(1, len(close)):
        # True Range
        tr[i] = max(
            high[i] - low[i],                     
            abs(high[i] - close[i - 1]),         
            abs(low[i] - close[i - 1])            
        )
        
        # Plus DM
        up_move = high[i] - high[i - 1]
        down_move = low[i - 1] - low[i]
        
        if up_move > down_move and up_move > 0:
            plus_dm[i] = up_move
        else:
            plus_dm[i] = 0
        
        # Minus DM
        if down_move > up_move and down_move > 0:
            minus_dm[i] = down_move
        else:
            minus_dm[i] = 0
    
    # Inicjalizacja wygładzonych tablic
    smoothed_tr = np.zeros_like(close)
    smoothed_plus_dm = np.zeros_like(close)
    smoothed_minus_dm = np.zeros_like(close)
    
    # Inicjalizacja pierwszych wartości
    smoothed_tr[period] = np.sum(tr[1:period+1])
    smoothed_plus_dm[period] = np.sum(plus_dm[1:period+1])
    smoothed_minus_dm[period] = np.sum(minus_dm[1:period+1])
    
    # Wygładzanie TR i DM
    for i in range(period + 1, len(close)):
        smoothed_tr[i] = smoothed_tr[i - 1] - (smoothed_tr[i - 1] / period) + tr[i]
        smoothed_plus_dm[i] = smoothed_plus_dm[i - 1] - (smoothed_plus_dm[i - 1] / period) + plus_dm[i]
        smoothed_minus_dm[i] = smoothed_minus_dm[i - 1] - (smoothed_minus_dm[i - 1] / period) + minus_dm[i]
    
    # Inicjalizacja DI i ADX
    plus_di = np.zeros_like(close)
    minus_di = np.zeros_like(close)
    plus_di[:] = np.nan
    minus_di[:] = np.nan
    
    dx = np.zeros_like(close)
    dx[:] = np.nan
    
    adx = np.zeros_like(close)
    adx[:] = np.nan
    
    # Obliczenie DI
    for i in range(period, len(close)):
        if smoothed_tr[i] > 0:
            plus_di[i] = 100 * smoothed_plus_dm[i] / smoothed_tr[i]
            minus_di[i] = 100 * smoothed_minus_dm[i] / smoothed_tr[i]
        else:
            plus_di[i] = 0
            minus_di[i] = 0
        
        # Obliczenie DX
        if (plus_di[i] + minus_di[i]) > 0:
            dx[i] = 100 * abs(plus_di[i] - minus_di[i]) / (plus_di[i] + minus_di[i])
        else:
            dx[i] = 0
    
    # Obliczenie pierwszego ADX
    adx[2 * period - 1] = np.mean(dx[period:2 * period])
    
    # Obliczenie pozostałych wartości ADX
    for i in range(2 * period, len(close)):
        adx[i] = (adx[i - 1] * (period - 1) + dx[i]) / period
    
    return adx, plus_di, minus_di

def detect_candlestick_patterns(open_prices: Union[np.ndarray, pd.Series],
                              high: Union[np.ndarray, pd.Series], 
                              low: Union[np.ndarray, pd.Series], 
                              close: Union[np.ndarray, pd.Series]) -> Dict[str, np.ndarray]:
    """
    Wykrywa podstawowe formacje świecowe.
    
    Args:
        open_prices: Ceny otwarcia (np.ndarray lub pd.Series)
        high: Najwyższe ceny (np.ndarray lub pd.Series)
        low: Najniższe ceny (np.ndarray lub pd.Series)
        close: Ceny zamknięcia (np.ndarray lub pd.Series)
        
    Returns:
        Dict[str, np.ndarray]: Słownik tablic boolowskich oznaczających wykryte formacje
    """
    # Konwersja na tablice numpy
    if isinstance(open_prices, pd.Series):
        open_prices = open_prices.values
    if isinstance(high, pd.Series):
        high = high.values
    if isinstance(low, pd.Series):
        low = low.values
    if isinstance(close, pd.Series):
        close = close.values
    
    # Inicjalizacja słownika wyników
    patterns = {}
    
    # Inicjalizacja tablic
    length = len(close)
    bullish_engulfing = np.zeros(length, dtype=bool)
    bearish_engulfing = np.zeros(length, dtype=bool)
    hammer = np.zeros(length, dtype=bool)
    shooting_star = np.zeros(length, dtype=bool)
    doji = np.zeros(length, dtype=bool)
    morning_star = np.zeros(length, dtype=bool)
    evening_star = np.zeros(length, dtype=bool)
    
    # Długości korpusów świec
    body_length = np.abs(close - open_prices)
    
    # Długości cieni świec
    upper_shadow = high - np.maximum(open_prices, close)
    lower_shadow = np.minimum(open_prices, close) - low
    
    # Całkowita długość świecy
    total_length = high - low
    
    # Formacje świecowe Engulfing
    for i in range(1, length):
        # Bullish Engulfing (pattern odwrócenia trendu spadkowego)
        if (close[i-1] < open_prices[i-1] and  # Poprzednia świeca jest spadkowa
            close[i] > open_prices[i] and      # Bieżąca świeca jest wzrostowa
            open_prices[i] < close[i-1] and    # Otwarcie poniżej zamknięcia poprzedniej
            close[i] > open_prices[i-1]):      # Zamknięcie powyżej otwarcia poprzedniej
            bullish_engulfing[i] = True
        
        # Bearish Engulfing (pattern odwrócenia trendu wzrostowego)
        if (close[i-1] > open_prices[i-1] and  # Poprzednia świeca jest wzrostowa
            close[i] < open_prices[i] and      # Bieżąca świeca jest spadkowa
            open_prices[i] > close[i-1] and    # Otwarcie powyżej zamknięcia poprzedniej
            close[i] < open_prices[i-1]):      # Zamknięcie poniżej otwarcia poprzedniej
            bearish_engulfing[i] = True
    
    # Formacja Doji (mały korpus, długie cienie)
    for i in range(length):
        if (body_length[i] * 3 < total_length[i] and  # Korpus jest mały w porównaniu do całej świecy
            body_length[i] < 0.1 * total_length[i]):   # Korpus stanowi mniej niż 10% długości świecy
            doji[i] = True
    
    # Formacja Hammer (długi dolny cień, mały korpus na górze)
    for i in range(length):
        if (lower_shadow[i] > 2 * body_length[i] and  # Dolny cień jest przynajmniej 2x dłuższy od korpusu
            upper_shadow[i] < 0.2 * body_length[i] and # Górny cień jest krótki
            body_length[i] > 0):                       # Korpus istnieje
            hammer[i] = True
    
    # Formacja Shooting Star (długi górny cień, mały korpus na dole)
    for i in range(length):
        if (upper_shadow[i] > 2 * body_length[i] and  # Górny cień jest przynajmniej 2x dłuższy od korpusu
            lower_shadow[i] < 0.2 * body_length[i] and # Dolny cień jest krótki
            body_length[i] > 0):                       # Korpus istnieje
            shooting_star[i] = True
    
    # Formacje złożone (Morning Star & Evening Star)
    for i in range(2, length):
        # Morning Star (pattern odwrócenia trendu spadkowego)
        if (close[i-2] < open_prices[i-2] and                 # Pierwsza świeca jest spadkowa
            abs(close[i-1] - open_prices[i-1]) < body_length[i-2] * 0.3 and  # Druga świeca ma mały korpus
            close[i] > open_prices[i] and                     # Trzecia świeca jest wzrostowa
            close[i] > (open_prices[i-2] + close[i-2]) / 2):  # Trzecia świeca zamyka się powyżej środka pierwszej
            morning_star[i] = True
        
        # Evening Star (pattern odwrócenia trendu wzrostowego)
        if (close[i-2] > open_prices[i-2] and                 # Pierwsza świeca jest wzrostowa
            abs(close[i-1] - open_prices[i-1]) < body_length[i-2] * 0.3 and  # Druga świeca ma mały korpus
            close[i] < open_prices[i] and                     # Trzecia świeca jest spadkowa
            close[i] < (open_prices[i-2] + close[i-2]) / 2):  # Trzecia świeca zamyka się poniżej środka pierwszej
            evening_star[i] = True
    
    # Dodanie wykrytych formacji do słownika wyników
    patterns['bullish_engulfing'] = bullish_engulfing
    patterns['bearish_engulfing'] = bearish_engulfing
    patterns['hammer'] = hammer
    patterns['shooting_star'] = shooting_star
    patterns['doji'] = doji
    patterns['morning_star'] = morning_star
    patterns['evening_star'] = evening_star
    
    return patterns

def test_indicators():
    """
    Funkcja testowa do wizualizacji wskaźników na przykładowych danych.
    """
    # Wczytanie przykładowych danych (używamy CSV wygenerowanego przez test_mt5_connection.py)
    try:
        import glob
        csv_files = glob.glob("*.csv")
        
        if not csv_files:
            print("Nie znaleziono plików CSV do analizy.")
            return
        
        # Użycie pierwszego znalezionego pliku CSV
        test_file = csv_files[0]
        print(f"Używanie pliku danych: {test_file}")
        
        # Wczytanie danych
        df = pd.read_csv(test_file)
        
        # Przygotowanie danych
        close_prices = df['close'].values
        high_prices = df['high'].values
        low_prices = df['low'].values
        open_prices = df['open'].values
        
        # Obliczenie wskaźników
        print("Obliczanie wskaźników technicznych...")
        sma_20 = calculate_sma(close_prices, 20)
        ema_12 = calculate_ema(close_prices, 12)
        ema_26 = calculate_ema(close_prices, 26)
        rsi = calculate_rsi(close_prices)
        macd_line, signal_line, histogram = calculate_macd(close_prices)
        upper_band, middle_band, lower_band = calculate_bollinger_bands(close_prices)
        k, d = calculate_stochastic_oscillator(high_prices, low_prices, close_prices)
        atr = calculate_atr(high_prices, low_prices, close_prices)
        adx, plus_di, minus_di = calculate_adx(high_prices, low_prices, close_prices)
        patterns = detect_candlestick_patterns(open_prices, high_prices, low_prices, close_prices)
        
        # Wyświetlenie wykresu
        plt.figure(figsize=(12, 12))
        
        # Wykres cenowy z SMA i EMA
        plt.subplot(3, 1, 1)
        plt.title(f"Wykres cenowy z SMA(20), EMA(12), EMA(26) i Bollinger Bands")
        plt.plot(close_prices, label='Cena zamknięcia')
        plt.plot(sma_20, label='SMA(20)', color='red', linestyle='--')
        plt.plot(ema_12, label='EMA(12)', color='blue', linestyle='--')
        plt.plot(ema_26, label='EMA(26)', color='green', linestyle='--')
        plt.plot(upper_band, label='Upper BB', color='purple', linestyle=':')
        plt.plot(middle_band, label='Middle BB', color='orange', linestyle=':')
        plt.plot(lower_band, label='Lower BB', color='purple', linestyle=':')
        
        # Dodanie oznaczeń wykrytych formacji świecowych
        for i in range(len(close_prices)):
            if patterns['bullish_engulfing'][i]:
                plt.axvline(x=i, color='green', alpha=0.3)
            if patterns['bearish_engulfing'][i]:
                plt.axvline(x=i, color='red', alpha=0.3)
            if patterns['hammer'][i]:
                plt.scatter(i, low_prices[i], color='green', marker='^')
            if patterns['shooting_star'][i]:
                plt.scatter(i, high_prices[i], color='red', marker='v')
            if patterns['morning_star'][i]:
                plt.scatter(i, low_prices[i], color='green', marker='*', s=100)
            if patterns['evening_star'][i]:
                plt.scatter(i, high_prices[i], color='red', marker='*', s=100)
            
        plt.grid(True)
        plt.legend()
        
        # Wykres MACD
        plt.subplot(3, 1, 2)
        plt.title("MACD")
        plt.plot(macd_line, label='MACD')
        plt.plot(signal_line, label='Signal', color='red')
        plt.bar(range(len(histogram)), histogram, label='Histogram', alpha=0.3)
        plt.axhline(y=0, color='black', linestyle='-', alpha=0.3)
        plt.grid(True)
        plt.legend()
        
        # Wykres RSI i Stochastic
        plt.subplot(3, 1, 3)
        plt.title("RSI i Stochastic Oscillator")
        plt.plot(rsi, label='RSI', color='purple')
        plt.plot(k, label='%K', color='blue')
        plt.plot(d, label='%D', color='red')
        plt.axhline(y=80, color='red', linestyle='--', alpha=0.3)
        plt.axhline(y=20, color='green', linestyle='--', alpha=0.3)
        plt.axhline(y=50, color='black', linestyle='--', alpha=0.3)
        plt.grid(True)
        plt.legend()
        
        plt.tight_layout()
        
        # Zapisanie wykresu do pliku
        output_file = f"technical_indicators_{test_file.split('.')[0]}.png"
        plt.savefig(output_file)
        print(f"Wykres zapisany do pliku: {output_file}")
        
        plt.close()
        
    except Exception as e:
        print(f"Błąd podczas testowania wskaźników: {e}")

if __name__ == "__main__":
    test_indicators() 