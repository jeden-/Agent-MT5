#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Moduł do regularnego odświeżania danych rynkowych z platformy MetaTrader 5.
Pobiera dane historyczne dla różnych instrumentów i zapisuje je do plików CSV
lub bazy danych w określonych interwałach czasowych.
"""

import os
import sys
import time
import logging
import argparse
import schedule
import pandas as pd
from datetime import datetime, timedelta
from dotenv import load_dotenv
import signal
import threading

# Konfiguracja loggera
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('data_refresher.log')
    ]
)
logger = logging.getLogger("data_refresher")

# Dodanie głównego katalogu projektu do PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Ładowanie zmiennych środowiskowych
load_dotenv()
logger.info("Zmienne środowiskowe załadowane z pliku .env")

# Import komponentów
from src.mt5_bridge.mt5_connector import MT5Connector
from src.database.market_data_repository import save_market_data, get_market_data_repository
from src.database.models import MarketData

# Flaga do obsługi zakończenia programu
running = True

# Domyślna ścieżka dla danych CSV - katalog "data" obok głównego katalogu projektu
DEFAULT_DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")

class DataRefresher:
    """
    Klasa odpowiedzialna za regularne odświeżanie danych rynkowych.
    
    Attributes:
        connector: Instancja MT5Connector do połączenia z platformą MT5
        instruments: Lista instrumentów do monitorowania
        timeframes: Lista ram czasowych do monitorowania
        data_dir: Katalog do zapisywania danych
        db_save: Czy zapisywać dane do bazy danych
        csv_save: Czy zapisywać dane do plików CSV
    """
    
    def __init__(self, instruments=None, timeframes=None, data_dir=DEFAULT_DATA_DIR, 
                 db_save=True, csv_save=True):
        """
        Inicjalizacja obiektu DataRefresher.
        
        Args:
            instruments: Lista instrumentów do monitorowania
            timeframes: Lista ram czasowych do monitorowania
            data_dir: Katalog do zapisywania danych CSV
            db_save: Czy zapisywać dane do bazy danych
            csv_save: Czy zapisywać dane do plików CSV
        """
        self.connector = None
        self.instruments = instruments or ['EURUSD', 'GBPUSD', 'GOLD', 'US100', 'SILVER']
        self.timeframes = timeframes or ['M1', 'M5', 'M15', 'H1', 'H4', 'D1']
        self.data_dir = data_dir
        self.db_save = db_save
        self.csv_save = csv_save
        self.market_data_repo = get_market_data_repository() if db_save else None
        
        # Upewniamy się, że katalog na dane istnieje
        if self.csv_save:
            os.makedirs(self.data_dir, exist_ok=True)
        
        # Słownik do śledzenia ostatniego czasu odświeżenia dla każdej pary (instrument, timeframe)
        self.last_refresh = {}
        
        # Statystyki wydajności
        self.performance_stats = {
            'total_time': 0,
            'requests_count': 0,
            'data_size': 0,
            'save_time': 0
        }
        
        logger.info(f"DataRefresher zainicjalizowany dla {len(self.instruments)} instrumentów i "
                    f"{len(self.timeframes)} ram czasowych.")
        logger.info(f"Ustawienia zapisu: baza danych={self.db_save}, CSV={self.csv_save}")
        if self.csv_save:
            logger.info(f"Katalog danych CSV: {self.data_dir}")
    
    def connect(self):
        """Nawiązuje połączenie z platformą MT5."""
        try:
            self.connector = MT5Connector()
            connected = self.connector.connect()
            
            if connected:
                logger.info("Połączono z platformą MT5.")
                return True
            else:
                logger.error("Nie udało się połączyć z platformą MT5.")
                return False
                
        except Exception as e:
            logger.error(f"Błąd podczas łączenia z MT5: {e}", exc_info=True)
            return False
    
    def disconnect(self):
        """Zamyka połączenie z platformą MT5."""
        if self.connector:
            self.connector.disconnect()
            logger.info("Rozłączono z platformą MT5.")
    
    def refresh_data(self, instrument, timeframe, bars=100):
        """
        Odświeża dane dla określonego instrumentu i ram czasowych.
        
        Args:
            instrument: Symbol instrumentu
            timeframe: Ramy czasowe
            bars: Liczba świec do pobrania
            
        Returns:
            bool: True jeśli udało się odświeżyć dane, False w przeciwnym przypadku
        """
        try:
            start_time = time.time()
            logger.info(f"Odświeżanie danych dla {instrument} ({timeframe}, {bars} świec)...")
            
            # Pobieranie danych historycznych
            df = self.connector.get_historical_data(instrument, timeframe, count=bars)
            
            fetch_time = time.time() - start_time
            
            if df is None or df.empty:
                logger.error(f"Nie udało się pobrać danych dla {instrument} ({timeframe}).")
                return False
            
            data_size = df.memory_usage(deep=True).sum() / 1024  # w KB
            self.performance_stats['data_size'] += data_size
            self.performance_stats['requests_count'] += 1
            
            logger.info(f"Pobrano {len(df)} świec dla {instrument} ({timeframe}). "
                       f"Czas: {fetch_time:.2f}s, Rozmiar: {data_size:.2f} KB")
            
            save_start_time = time.time()
            
            # Zapisanie danych do pliku CSV
            if self.csv_save:
                # Ścieżka do pliku zawierająca datę dzisiejszą
                today = datetime.now().strftime('%Y%m%d')
                csv_dir = os.path.join(self.data_dir, today)
                os.makedirs(csv_dir, exist_ok=True)
                
                csv_filename = os.path.join(csv_dir, f"{instrument}_{timeframe}.csv")
                df.to_csv(csv_filename, index=False)
                logger.info(f"Zapisano dane do pliku {csv_filename}")
            
            # Zapisanie danych do bazy danych
            if self.db_save and self.market_data_repo:
                try:
                    # Przygotowanie danych do zapisu w bazie
                    for _, row in df.iterrows():
                        market_data = MarketData(
                            symbol=instrument,
                            timeframe=timeframe,
                            timestamp=row['time'],
                            open=row['open'],
                            high=row['high'],
                            low=row['low'],
                            close=row['close'],
                            tick_volume=row['tick_volume'],
                            spread=row.get('spread', 0),
                            real_volume=row.get('real_volume', 0)
                        )
                        
                        # Zapis do bazy danych
                        self.market_data_repo.save_or_update(market_data)
                    
                    logger.info(f"Zapisano {len(df)} rekordów do bazy danych dla {instrument} ({timeframe})")
                except Exception as e:
                    logger.error(f"Błąd podczas zapisu do bazy danych dla {instrument} ({timeframe}): {e}")
            
            save_time = time.time() - save_start_time
            self.performance_stats['save_time'] += save_time
            
            # Aktualizacja czasu ostatniego odświeżenia
            self.last_refresh[(instrument, timeframe)] = datetime.now()
            
            # Aktualizacja statystyk wydajności
            total_time = time.time() - start_time
            self.performance_stats['total_time'] += total_time
            
            logger.info(f"Operacja odświeżania danych dla {instrument} ({timeframe}) "
                       f"zakończona w {total_time:.2f}s (Pobieranie: {fetch_time:.2f}s, "
                       f"Zapis: {save_time:.2f}s)")
            
            return True
            
        except Exception as e:
            logger.error(f"Błąd podczas odświeżania danych dla {instrument} ({timeframe}): {e}", 
                         exc_info=True)
            return False
    
    def refresh_all_data(self):
        """
        Odświeża dane dla wszystkich skonfigurowanych instrumentów i ram czasowych.
        
        Returns:
            int: Liczba par (instrument, timeframe) dla których udało się odświeżyć dane
        """
        if not self.connector:
            connected = self.connect()
            if not connected:
                return 0
        
        # Resetujemy statystyki wydajności dla tej rundy
        self.performance_stats = {
            'total_time': 0,
            'requests_count': 0,
            'data_size': 0,
            'save_time': 0
        }
        
        start_time = time.time()
        success_count = 0
        total_pairs = len(self.instruments) * len(self.timeframes)
        
        logger.info(f"Rozpoczęto odświeżanie danych dla {total_pairs} par (instrument, timeframe)...")
        
        # Odświeżanie danych dla wszystkich par (instrument, timeframe)
        for instrument in self.instruments:
            for timeframe in self.timeframes:
                success = self.refresh_data(instrument, timeframe)
                if success:
                    success_count += 1
        
        total_time = time.time() - start_time
        
        # Podsumowanie operacji
        logger.info(f"Odświeżono dane dla {success_count} z {total_pairs} par.")
        logger.info(f"Statystyki wydajności:")
        logger.info(f"  Całkowity czas: {total_time:.2f}s")
        logger.info(f"  Średni czas na parę: {(total_time / total_pairs):.2f}s")
        logger.info(f"  Całkowity rozmiar danych: {self.performance_stats['data_size']:.2f} KB")
        logger.info(f"  Czas pobierania: {(self.performance_stats['total_time'] - self.performance_stats['save_time']):.2f}s")
        logger.info(f"  Czas zapisu: {self.performance_stats['save_time']:.2f}s")
        
        return success_count
    
    def schedule_refresh(self, interval_minutes=15):
        """
        Planuje regularne odświeżanie danych.
        
        Args:
            interval_minutes: Interwał odświeżania w minutach
            
        Returns:
            bool: True jeśli udało się zaplanować odświeżanie, False w przeciwnym przypadku
        """
        try:
            # Dodajemy zadanie odświeżania danych do harmonogramu
            schedule.every(interval_minutes).minutes.do(self.refresh_all_data)
            logger.info(f"Zaplanowano odświeżanie danych co {interval_minutes} minut.")
            
            # Natychmiastowe pierwsze odświeżenie
            self.refresh_all_data()
            
            return True
            
        except Exception as e:
            logger.error(f"Błąd podczas planowania odświeżania danych: {e}", exc_info=True)
            return False
    
    def run(self, interval_minutes=15):
        """
        Uruchamia proces regularnego odświeżania danych.
        
        Args:
            interval_minutes: Interwał odświeżania w minutach
            
        Returns:
            None
        """
        global running
        
        # Planowanie odświeżania
        self.schedule_refresh(interval_minutes)
        
        # Główna pętla
        logger.info("Rozpoczęto proces regularnego odświeżania danych.")
        
        try:
            while running:
                schedule.run_pending()
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Przerwano proces odświeżania danych.")
        except Exception as e:
            logger.error(f"Błąd podczas procesu odświeżania danych: {e}", exc_info=True)
        finally:
            self.disconnect()
            logger.info("Zakończono proces odświeżania danych.")

def signal_handler(sig, frame):
    """Obsługa sygnałów przerwania (np. CTRL+C)."""
    global running
    logger.info("Otrzymano sygnał przerwania. Zatrzymywanie...")
    running = False

def parse_arguments():
    """
    Parsuje argumenty wiersza poleceń.
    
    Returns:
        argparse.Namespace: Sparsowane argumenty
    """
    parser = argparse.ArgumentParser(description='Regularnie odświeża dane rynkowe z MT5.')
    
    parser.add_argument('--instruments', type=str, nargs='+', 
                        default=['EURUSD', 'GBPUSD', 'GOLD', 'US100', 'SILVER'],
                        help='Lista instrumentów do monitorowania')
    
    parser.add_argument('--timeframes', type=str, nargs='+', 
                        default=['M1', 'M5', 'M15', 'H1', 'H4', 'D1'],
                        help='Lista ram czasowych do monitorowania')
    
    parser.add_argument('--interval', type=int, default=15,
                        help='Interwał odświeżania w minutach')
    
    parser.add_argument('--data-dir', type=str, default=DEFAULT_DATA_DIR,
                        help='Katalog do zapisywania danych CSV')
    
    parser.add_argument('--no-db-save', action='store_true',
                        help='Nie zapisuje danych do bazy danych')
    
    parser.add_argument('--no-csv', action='store_true',
                        help='Nie zapisuje danych do plików CSV')
    
    return parser.parse_args()

def main():
    """
    Główna funkcja uruchamiająca proces odświeżania danych.
    """
    # Rejestrowanie obsługi sygnałów
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Parsowanie argumentów
    args = parse_arguments()
    
    # Inicjalizacja i uruchomienie odświeżacza danych
    refresher = DataRefresher(
        instruments=args.instruments,
        timeframes=args.timeframes,
        data_dir=args.data_dir,
        db_save=not args.no_db_save,
        csv_save=not args.no_csv
    )
    
    refresher.run(interval_minutes=args.interval)

if __name__ == "__main__":
    main() 