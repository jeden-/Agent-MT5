#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Testy jednostkowe dla HistoricalDataManager.
"""

import unittest
import os
import shutil
import tempfile
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch
import pandas as pd
import numpy as np
from pathlib import Path

from src.backtest.historical_data_manager import HistoricalDataManager


class TestHistoricalDataManager(unittest.TestCase):
    """
    Testy dla klasy HistoricalDataManager.
    """
    
    def setUp(self):
        """Przygotowanie środowiska testowego."""
        # Utworzenie tymczasowego katalogu na cache
        self.temp_dir = tempfile.mkdtemp()
        
        # Mockowanie konektora MT5
        self.mock_mt5_connector = MagicMock()
        
        # Inicjalizacja menedżera danych z używaniem tymczasowego katalogu
        self.data_manager = HistoricalDataManager(
            cache_dir=self.temp_dir,
            mt5_connector=self.mock_mt5_connector
        )
        
        # Przykładowe dane dla testów
        self.sample_data = pd.DataFrame({
            'time': pd.date_range(start='2025-01-01', periods=100, freq='H'),
            'open': np.random.normal(100, 5, 100),
            'high': np.random.normal(102, 5, 100),
            'low': np.random.normal(98, 5, 100),
            'close': np.random.normal(101, 5, 100),
            'volume': np.random.randint(100, 1000, 100),
            'spread': np.random.randint(1, 10, 100)
        })
    
    def tearDown(self):
        """Czyszczenie po testach."""
        # Usunięcie tymczasowego katalogu
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_initialization(self):
        """Test inicjalizacji klasy."""
        # Sprawdzenie, czy katalog cache został utworzony
        self.assertTrue(os.path.exists(self.temp_dir))
        
        # Sprawdzenie, czy atrybuty zostały poprawnie zainicjalizowane
        self.assertEqual(self.data_manager.cache_dir, Path(self.temp_dir))
        self.assertEqual(self.data_manager.mt5_connector, self.mock_mt5_connector)
        self.assertTrue(self.data_manager.validate_data)
        self.assertEqual(self.data_manager.cache_metadata, {})
    
    def test_cache_data(self):
        """Test zapisywania danych do cache."""
        # Zapisanie przykładowych danych
        symbol = "EURUSD"
        timeframe = "H1"
        
        file_path = self.data_manager.cache_data(symbol, timeframe, self.sample_data)
        
        # Sprawdź czy plik został utworzony
        self.assertIsNotNone(file_path)
        self.assertTrue(os.path.exists(file_path))
        
        # Sprawdź czy metadane zostały zaktualizowane
        key = f"{symbol}_{timeframe}"
        self.assertIn(key, self.data_manager.cache_metadata)
        self.assertEqual(len(self.data_manager.cache_metadata[key]), 1)
        
        # Odczytaj dane z pliku
        df = pd.read_parquet(file_path)
        self.assertEqual(len(df), len(self.sample_data))
        
        # Sprawdź czy wszystkie kolumny zostały zapisane
        for col in self.sample_data.columns:
            self.assertIn(col, df.columns)
    
    def test_get_historical_data_from_cache(self):
        """Test pobierania danych z cache."""
        # Zapisanie przykładowych danych
        symbol = "EURUSD"
        timeframe = "H1"
        self.data_manager.cache_data(symbol, timeframe, self.sample_data)
        
        # Pobieranie danych z cache
        start_date = datetime(2025, 1, 1)
        end_date = datetime(2025, 1, 5)
        
        data = self.data_manager.get_historical_data(
            symbol=symbol,
            timeframe=timeframe,
            start_date=start_date,
            end_date=end_date,
            use_cache=True,
            update_cache=False
        )
        
        # Sprawdzenie czy dane zostały pobrane
        self.assertIsNotNone(data)
        self.assertIsInstance(data, pd.DataFrame)
        
        # Sprawdzenie zakresu dat
        self.assertTrue(data['time'].min() >= pd.Timestamp(start_date))
        self.assertTrue(data['time'].max() <= pd.Timestamp(end_date))
        
        # Sprawdzenie, czy konektor MT5 nie został wywołany
        self.mock_mt5_connector.get_historical_data.assert_not_called()
    
    def test_get_historical_data_from_mt5(self):
        """Test pobierania danych z MT5."""
        # Konfiguracja mock-a
        symbol = "EURUSD"
        timeframe = "H1"
        start_date = datetime(2025, 1, 1)
        end_date = datetime(2025, 1, 5)
        
        self.mock_mt5_connector.get_historical_data.return_value = self.sample_data
        
        # Pobieranie danych z MT5
        data = self.data_manager.get_historical_data(
            symbol=symbol,
            timeframe=timeframe,
            start_date=start_date,
            end_date=end_date,
            use_cache=False,
            update_cache=False
        )
        
        # Sprawdzenie czy dane zostały pobrane
        self.assertIsNotNone(data)
        self.assertIsInstance(data, pd.DataFrame)
        
        # Sprawdzenie, czy konektor MT5 został wywołany
        self.mock_mt5_connector.get_historical_data.assert_called_once()
    
    def test_clear_cache(self):
        """Test czyszczenia cache."""
        # Zapisanie kilku plików cache
        symbols = ["EURUSD", "GBPUSD", "USDJPY"]
        timeframes = ["M15", "H1", "D1"]
        
        for symbol in symbols:
            for timeframe in timeframes:
                self.data_manager.cache_data(symbol, timeframe, self.sample_data)
        
        # Sprawdzenie, czy pliki zostały utworzone
        files_count = len(list(Path(self.temp_dir).glob("*.parquet")))
        self.assertEqual(files_count, len(symbols) * len(timeframes))
        
        # Czyszczenie cache dla jednego symbolu
        deleted = self.data_manager.clear_cache(symbol="EURUSD")
        
        # Sprawdzenie, ile plików zostało usuniętych
        self.assertEqual(deleted, len(timeframes))
        
        # Sprawdzenie, ile plików pozostało
        files_count = len(list(Path(self.temp_dir).glob("*.parquet")))
        self.assertEqual(files_count, len(symbols) * len(timeframes) - len(timeframes))
        
        # Czyszczenie całego cache
        deleted = self.data_manager.clear_cache()
        
        # Sprawdzenie, czy wszystkie pozostałe pliki zostały usunięte
        self.assertEqual(deleted, len(symbols) * len(timeframes) - len(timeframes))
        files_count = len(list(Path(self.temp_dir).glob("*.parquet")))
        self.assertEqual(files_count, 0)
    
    def test_get_cache_stats(self):
        """Test pobierania statystyk cache."""
        # Zapisanie kilku plików cache
        symbols = ["EURUSD", "GBPUSD"]
        timeframes = ["H1", "D1"]
        
        for symbol in symbols:
            for timeframe in timeframes:
                self.data_manager.cache_data(symbol, timeframe, self.sample_data)
        
        # Pobieranie statystyk
        stats = self.data_manager.get_cache_stats()
        
        # Sprawdzenie, czy statystyki zawierają oczekiwane wartości
        self.assertEqual(stats["total_files"], len(symbols) * len(timeframes))
        self.assertEqual(stats["unique_symbols"], len(symbols))
        self.assertEqual(stats["unique_timeframes"], len(timeframes))
        self.assertIn("EURUSD", stats["symbols"])
        self.assertIn("H1", stats["timeframes"])
    
    def test_validate_and_clean_data(self):
        """Test walidacji i czyszczenia danych."""
        # Tworzenie danych z brakami
        data_with_nulls = self.sample_data.copy()
        data_with_nulls.loc[10:15, 'close'] = np.nan
        data_with_nulls.loc[5:8, 'volume'] = np.nan
        
        # Walidacja i czyszczenie danych
        cleaned_data = self.data_manager._validate_and_clean_data(data_with_nulls)
        
        # Sprawdzenie, czy NULL-e zostały wypełnione
        self.assertFalse(cleaned_data['close'].isnull().any())
        self.assertFalse(cleaned_data['volume'].isnull().any())
    
    def test_load_cached_data_with_multiple_files(self):
        """Test ładowania danych z wielu plików cache."""
        # Utworzenie kilku plików z różnymi zakresami dat
        symbol = "EURUSD"
        timeframe = "H1"
        
        # Dane dla pierwszego tygodnia
        data1 = pd.DataFrame({
            'time': pd.date_range(start='2025-01-01', end='2025-01-07', freq='H'),
            'open': np.random.normal(100, 5, 145),
            'high': np.random.normal(102, 5, 145),
            'low': np.random.normal(98, 5, 145),
            'close': np.random.normal(101, 5, 145),
            'volume': np.random.randint(100, 1000, 145)
        })
        
        # Dane dla drugiego tygodnia
        data2 = pd.DataFrame({
            'time': pd.date_range(start='2025-01-08', end='2025-01-14', freq='H'),
            'open': np.random.normal(101, 5, 145),
            'high': np.random.normal(103, 5, 145),
            'low': np.random.normal(99, 5, 145),
            'close': np.random.normal(102, 5, 145),
            'volume': np.random.randint(100, 1000, 145)
        })
        
        # Zapisanie obu plików do cache
        self.data_manager.cache_data(symbol, timeframe, data1)
        self.data_manager.cache_data(symbol, timeframe, data2)
        
        # Ładowanie danych z zakresu obejmującego oba pliki
        start_date = datetime(2025, 1, 5)
        end_date = datetime(2025, 1, 10)
        
        combined_data = self.data_manager._load_cached_data(
            symbol=symbol,
            timeframe=timeframe,
            start_date=start_date,
            end_date=end_date
        )
        
        # Sprawdzenie, czy dane zostały poprawnie połączone
        self.assertIsNotNone(combined_data)
        self.assertGreaterEqual(len(combined_data), 24 * 6)  # 6 dni po 24 godziny
        
        # Sprawdzenie zakresu dat
        min_date = combined_data['time'].min()
        max_date = combined_data['time'].max()
        self.assertGreaterEqual(min_date, pd.Timestamp(start_date))
        self.assertLessEqual(max_date, pd.Timestamp(end_date))
    
    def test_estimate_expected_data_points(self):
        """Test szacowania oczekiwanej liczby punktów danych."""
        # Okresy testowe
        start_date = datetime(2025, 1, 1)
        end_date = datetime(2025, 1, 2)  # 1 dzień (24 godziny)
        
        # Szacowanie dla różnych timeframe'ów
        m1_points = self.data_manager._estimate_expected_data_points("M1", start_date, end_date)
        h1_points = self.data_manager._estimate_expected_data_points("H1", start_date, end_date)
        d1_points = self.data_manager._estimate_expected_data_points("D1", start_date, end_date)
        
        # Sprawdzenie wyników
        self.assertEqual(m1_points, 24 * 60)  # 24 godziny * 60 minut
        self.assertEqual(h1_points, 24)  # 24 godziny
        self.assertEqual(d1_points, 1)  # 1 dzień


if __name__ == '__main__':
    unittest.main() 