#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Skrypt testowy do sprawdzenia połączenia z platformą MetaTrader 5
i pobierania realnych danych rynkowych.
"""

import logging
import sys
import os
import pandas as pd
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
from dotenv import load_dotenv

# Konfiguracja loggera
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("test_mt5_connection")

# Dodanie głównego katalogu projektu do PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Ładowanie zmiennych środowiskowych
load_dotenv()
logger.info("Zmienne środowiskowe załadowane z pliku .env")

# Import komponentów
from src.mt5_bridge.mt5_connector import MT5Connector

def test_connection():
    """Testuje połączenie z platformą MT5."""
    try:
        # Inicjalizacja konektora MT5
        connector = MT5Connector()
        
        # Połączenie z platformą
        logger.info("Próba połączenia z platformą MT5...")
        if connector.connect():
            logger.info("Połączenie z MT5 nawiązane pomyślnie!")
            
            # Pobranie informacji o koncie
            account_info = connector.get_account_info()
            if account_info:
                logger.info(f"Informacje o koncie:")
                logger.info(f"  Login: {account_info['login']}")
                logger.info(f"  Saldo: {account_info['balance']} {account_info['currency']}")
                logger.info(f"  Equity: {account_info['equity']} {account_info['currency']}")
                logger.info(f"  Margin: {account_info['margin']} {account_info['currency']}")
                logger.info(f"  Free Margin: {account_info['margin_free']} {account_info['currency']}")
                logger.info(f"  Margin Level: {account_info['margin_level']}%")
            else:
                logger.error("Nie udało się pobrać informacji o koncie")
                
            # Rozłączenie
            connector.disconnect()
            logger.info("Rozłączono z platformą MT5")
            return True
        else:
            logger.error("Nie udało się połączyć z platformą MT5")
            return False
    except Exception as e:
        logger.error(f"Błąd podczas testowania połączenia: {e}", exc_info=True)
        return False

def get_market_data(symbols=['EURUSD', 'GBPUSD', 'GOLD'], timeframe='M15', bars=100):
    """
    Pobiera i wyświetla dane rynkowe dla podanych instrumentów.
    
    Args:
        symbols: Lista symboli do pobrania
        timeframe: Interwał czasowy (M1, M5, M15, M30, H1, H4, D1)
        bars: Liczba świec do pobrania
    
    Returns:
        Dict: Dane rynkowe dla każdego symbolu
    """
    try:
        # Inicjalizacja konektora MT5
        connector = MT5Connector()
        
        # Połączenie z platformą
        if not connector.connect():
            logger.error("Nie udało się połączyć z platformą MT5")
            return {}
            
        logger.info(f"Pobieranie danych rynkowych dla {len(symbols)} instrumentów...")
        
        # Przygotowanie słownika na dane
        market_data = {}
        
        # Pobieranie danych dla każdego symbolu
        for symbol in symbols:
            logger.info(f"Pobieranie danych dla {symbol} ({timeframe}, {bars} świec)...")
            
            # Pobieranie danych historycznych
            df = connector.get_historical_data(symbol, timeframe, count=bars)
            
            if df is not None and not df.empty:
                logger.info(f"Pobrano {len(df)} świec dla {symbol}")
                market_data[symbol] = df
                
                # Wyświetlenie podstawowych statystyk
                logger.info(f"Statystyki dla {symbol}:")
                logger.info(f"  Zakres dat: {df['time'].min()} - {df['time'].max()}")
                logger.info(f"  Średnia cena zamknięcia: {df['close'].mean():.5f}")
                logger.info(f"  Min/Max cena: {df['low'].min():.5f} / {df['high'].max():.5f}")
                
                # Zapisanie danych do pliku CSV
                csv_filename = f"{symbol}_{timeframe}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
                df.to_csv(csv_filename, index=False)
                logger.info(f"Zapisano dane do pliku {csv_filename}")
            else:
                logger.error(f"Nie udało się pobrać danych dla {symbol}")
        
        # Rozłączenie
        connector.disconnect()
        logger.info("Rozłączono z platformą MT5")
        
        return market_data
    
    except Exception as e:
        logger.error(f"Błąd podczas pobierania danych rynkowych: {e}", exc_info=True)
        if 'connector' in locals() and connector:
            connector.disconnect()
        return {}

def plot_market_data(market_data):
    """
    Tworzy wykres danych rynkowych dla podanych instrumentów.
    
    Args:
        market_data: Słownik z danymi rynkowymi dla poszczególnych symboli
    """
    if not market_data:
        logger.error("Brak danych do wykresu")
        return
        
    try:
        # Tworzenie wykresu dla każdego symbolu
        for symbol, df in market_data.items():
            plt.figure(figsize=(12, 8))
            
            # Wykres świecowy
            plt.subplot(2, 1, 1)
            plt.title(f"{symbol} - Wykres świecowy")
            
            # Uproszczony wykres świecy
            for i in range(len(df)):
                # Kolor świecy zależy od kierunku cenowego
                color = 'green' if df.iloc[i]['close'] >= df.iloc[i]['open'] else 'red'
                
                # Rysowanie korpusu świecy
                plt.plot([i, i], [df.iloc[i]['open'], df.iloc[i]['close']], color=color, linewidth=6)
                
                # Rysowanie cieni świecy
                plt.plot([i, i], [df.iloc[i]['low'], df.iloc[i]['high']], color=color, linewidth=1)
            
            plt.grid(True)
            plt.xticks(range(0, len(df), len(df)//10), [str(date.date()) for date in df['time'][::len(df)//10]])
            plt.xlabel('Data')
            plt.ylabel('Cena')
            
            # Wykres wolumenu
            plt.subplot(2, 1, 2)
            plt.title(f"{symbol} - Wolumen")
            plt.bar(range(len(df)), df['tick_volume'], color='blue', alpha=0.7)
            plt.grid(True)
            plt.xticks(range(0, len(df), len(df)//10), [str(date.date()) for date in df['time'][::len(df)//10]])
            plt.xlabel('Data')
            plt.ylabel('Wolumen')
            
            plt.tight_layout()
            
            # Zapisanie wykresu do pliku
            plot_filename = f"{symbol}_chart_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            plt.savefig(plot_filename)
            logger.info(f"Zapisano wykres do pliku {plot_filename}")
            
            plt.close()
    
    except Exception as e:
        logger.error(f"Błąd podczas tworzenia wykresu: {e}", exc_info=True)

def main():
    """Główna funkcja testowa."""
    try:
        logger.info("=== TEST POŁĄCZENIA Z MT5 ===")
        connection_success = test_connection()
        
        if connection_success:
            logger.info("\n=== POBIERANIE DANYCH RYNKOWYCH ===")
            
            # Lista instrumentów do przetestowania
            instruments = ['EURUSD', 'GBPUSD', 'GOLD', 'US100', 'SILVER']
            
            # Pobieranie danych
            market_data = get_market_data(symbols=instruments, timeframe='M15', bars=100)
            
            # Tworzenie wykresów
            if market_data:
                logger.info("\n=== TWORZENIE WYKRESÓW ===")
                plot_market_data(market_data)
        
        logger.info("Test zakończony")
        
    except Exception as e:
        logger.error(f"Błąd podczas wykonywania testu: {e}", exc_info=True)

if __name__ == "__main__":
    main() 