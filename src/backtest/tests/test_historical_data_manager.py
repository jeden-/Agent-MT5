#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Testy jednostkowe dla klasy HistoricalDataManager.
"""

import unittest
import os
import shutil
import tempfile
from datetime import datetime, timedelta
from unittest.mock import Mock, patch
import pandas as pd
import numpy as np
from pathlib import Path

from src.backtest.historical_data_manager import HistoricalDataManager
from src.mt5_bridge.mt5_connector import MT5Connector

class TestHistoricalDataManager(unittest.TestCase):
    """
    Klasa testowa dla HistoricalDataManager.
    """
    
    def setUp(self):
        """Przygotowanie środowiska testowego."""
        # Tworzenie tymczasowego katalogu na cache
        self.temp_dir = tempfile.mkdtemp()
        
        # Mock dla MT5Connector
        self.mock_mt5_connector = Mock(spec=MT5Connector)
        
        # Przykładowe dane historyczne do testów
        self.sample_data = pd.DataFrame({
            'time': pd.date_range(start='2024-01-01', periods=100, freq='H'),
            'open': np.random.rand(100) * 100 + 50,
            'high': np.random.rand(100) * 100 + 60,
            'low': np.random.rand(100) * 100 + 40,
            'close': np.random.rand(100) * 100 + 50,
            'volume': np.random.randint(1, 1000, 100)
        })
        
        # Konfiguracja mocka MT5Connector
        self.mock_mt5_connector.get_historical_data.return_value = self.sample_data
        
        # Inicjalizacja menedżera danych
        self.manager = HistoricalDataManager(
            cache_dir=self.temp_dir,
            mt5_connector=self.mock_mt5_connector,
            validate_data=True
        )
    
    def tearDown(self):
        """Czyszczenie po testach."""
        # Usunięcie tymczasowego katalogu
        shutil.rmtree(self.temp_dir)
    
    def test_initialization(self):
        """Test inicjalizacji HistoricalDataManager."""
        # Sprawdzenie czy katalog cache został utworzony
        self.assertTrue(Path(self.temp_dir).exists())
        
        # Sprawdzenie czy właściwości zostały poprawnie ustawione
        self.assertEqual(self.manager.cache_dir, Path(self.temp_dir))
        self.assertEqual(self.manager.mt5_connector, self.mock_mt5_connector)
        self.assertTrue(self.manager.validate_data)
        self.assertIsNotNone(self.manager.cache_metadata)
        self.assertIsNotNone(self.manager.lock)
    
    def test_fetch_from_mt5(self):
        """Test pobierania danych z MT5."""
        # Parametry testu
        symbol = 'EURUSD'
        timeframe = 'H1'
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 1, 5)
        
        # Wywołanie metody
        data = self.manager._fetch_from_mt5(symbol, timeframe, start_date, end_date)
        
        # Sprawdzenie czy MT5Connector został wywołany z poprawnymi parametrami
        self.mock_mt5_connector.get_historical_data.assert_called_once_with(
            symbol=symbol,
            timeframe=timeframe,
            start_time=start_date,
            end_time=end_date,
            count=100000
        )
        
        # Sprawdzenie wyniku
        pd.testing.assert_frame_equal(data, self.sample_data)
    
    def test_fetch_from_mt5_no_connector(self):
        """Test pobierania danych bez dostępnego konektora."""
        # Parametry testu
        symbol = 'EURUSD'
        timeframe = 'H1'
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 1, 5)
        
        # Manager bez konektora
        manager_no_connector = HistoricalDataManager(
            cache_dir=self.temp_dir,
            mt5_connector=None
        )
        
        # Wywołanie metody
        data = manager_no_connector._fetch_from_mt5(symbol, timeframe, start_date, end_date)
        
        # Sprawdzenie wyniku
        self.assertIsNone(data)
    
    def test_validate_and_clean_data(self):
        """Test walidacji i czyszczenia danych."""
        # Dane z brakującymi wartościami
        data_with_nulls = self.sample_data.copy()
        data_with_nulls.iloc[5:10, 1:4] = np.nan  # Dodajemy NULL do cen
        
        # Wywołanie metody
        cleaned_data = self.manager._validate_and_clean_data(data_with_nulls)
        
        # Sprawdzenie wyniku
        self.assertFalse(cleaned_data.isnull().any().any())  # Brak NULL-i
        self.assertEqual(len(cleaned_data), len(data_with_nulls))  # Zachowanie liczby wierszy
    
    def test_validate_and_clean_data_missing_columns(self):
        """Test walidacji danych z brakującymi kolumnami."""
        # Dane z brakującymi kolumnami
        data_missing_cols = self.sample_data[['time', 'close', 'volume']].copy()
        
        # Wywołanie metody
        cleaned_data = self.manager._validate_and_clean_data(data_missing_cols)
        
        # Sprawdzenie wyniku
        self.assertTrue('open' in cleaned_data.columns)
        self.assertTrue('high' in cleaned_data.columns)
        self.assertTrue('low' in cleaned_data.columns)
        self.assertEqual(len(cleaned_data), len(data_missing_cols))
    
    def test_cache_data(self):
        """Test zapisywania danych do cache'u."""
        # Parametry testu
        symbol = 'EURUSD'
        timeframe = 'H1'
        
        # Wywołanie metody
        file_path = self.manager.cache_data(symbol, timeframe, self.sample_data)
        
        # Sprawdzenie czy plik został utworzony
        self.assertIsNotNone(file_path)
        self.assertTrue(file_path.exists())
        
        # Sprawdzenie metadanych
        key = f"{symbol}_{timeframe}"
        self.assertTrue(key in self.manager.cache_metadata)
        self.assertEqual(len(self.manager.cache_metadata[key]), 1)
        
        # Sprawdzenie zawartości pliku
        loaded_data = pd.read_parquet(file_path)
        pd.testing.assert_frame_equal(loaded_data, self.sample_data)
    
    def test_get_historical_data_from_cache(self):
        """Test pobierania danych z cache'u."""
        # Parametry testu
        symbol = 'EURUSD'
        timeframe = 'H1'
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 1, 5)
        
        # Najpierw zapisujemy dane do cache'u
        self.manager.cache_data(symbol, timeframe, self.sample_data)
        
        # Resetujemy mock MT5Connector, aby sprawdzić, czy nie będzie wywoływany
        self.mock_mt5_connector.get_historical_data.reset_mock()
        
        # Wywołanie metody z użyciem cache'u
        data = self.manager.get_historical_data(
            symbol=symbol,
            timeframe=timeframe,
            start_date=start_date,
            end_date=end_date,
            use_cache=True
        )
        
        # Sprawdzenie czy dane zostały pobrane z cache'u (MT5Connector nie wywołany)
        self.mock_mt5_connector.get_historical_data.assert_not_called()
        
        # Sprawdzenie wyniku
        self.assertIsNotNone(data)
        self.assertFalse(data.empty)
    
    def test_get_historical_data_from_mt5(self):
        """Test pobierania danych z MT5 gdy brak cache'u."""
        # Parametry testu
        symbol = 'EURUSD'
        timeframe = 'H1'
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 1, 5)
        
        # Wywołanie metody bez używania cache'u
        data = self.manager.get_historical_data(
            symbol=symbol,
            timeframe=timeframe,
            start_date=start_date,
            end_date=end_date,
            use_cache=False
        )
        
        # Sprawdzenie czy MT5Connector został wywołany
        self.mock_mt5_connector.get_historical_data.assert_called_once()
        
        # Sprawdzenie wyniku
        pd.testing.assert_frame_equal(data, self.sample_data)
    
    def test_get_historical_data_update_cache(self):
        """Test aktualizacji cache'u przy pobieraniu danych."""
        # Parametry testu
        symbol = 'EURUSD'
        timeframe = 'H1'
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 1, 5)
        
        # Wywołanie metody z aktualizacją cache'u
        data = self.manager.get_historical_data(
            symbol=symbol,
            timeframe=timeframe,
            start_date=start_date,
            end_date=end_date,
            use_cache=True,
            update_cache=True
        )
        
        # Sprawdzenie czy MT5Connector został wywołany
        self.mock_mt5_connector.get_historical_data.assert_called_once()
        
        # Sprawdzenie czy dane zostały zapisane do cache'u
        key = f"{symbol}_{timeframe}"
        self.assertTrue(key in self.manager.cache_metadata)
        self.assertEqual(len(self.manager.cache_metadata[key]), 1)
        
        # Sprawdzenie wyniku
        pd.testing.assert_frame_equal(data, self.sample_data)
    
    def test_clear_cache(self):
        """Test czyszczenia cache'u."""
        # Przygotowanie danych w cache'u
        symbols = ['EURUSD', 'GBPUSD']
        timeframes = ['H1', 'D1']
        
        for symbol in symbols:
            for timeframe in timeframes:
                self.manager.cache_data(symbol, timeframe, self.sample_data)
        
        # Sprawdzenie czy dane zostały zapisane
        for symbol in symbols:
            for timeframe in timeframes:
                key = f"{symbol}_{timeframe}"
                self.assertTrue(key in self.manager.cache_metadata)
        
        # Czyszczenie cache'u dla konkretnego symbolu
        deleted_count = self.manager.clear_cache(symbol='EURUSD')
        
        # Sprawdzenie czy pliki zostały usunięte
        self.assertEqual(deleted_count, 2)  # EURUSD_H1 i EURUSD_D1
        
        # Sprawdzenie metadanych
        self.assertFalse('EURUSD_H1' in self.manager.cache_metadata)
        self.assertFalse('EURUSD_D1' in self.manager.cache_metadata)
        self.assertTrue('GBPUSD_H1' in self.manager.cache_metadata)
        self.assertTrue('GBPUSD_D1' in self.manager.cache_metadata)
    
    def test_get_cache_stats(self):
        """Test pobierania statystyk cache'u."""
        # Przygotowanie danych w cache'u
        symbols = ['EURUSD', 'GBPUSD']
        timeframes = ['H1', 'D1']
        
        for symbol in symbols:
            for timeframe in timeframes:
                self.manager.cache_data(symbol, timeframe, self.sample_data)
        
        # Pobranie statystyk
        stats = self.manager.get_cache_stats()
        
        # Sprawdzenie wyniku
        self.assertEqual(stats['total_files'], 4)
        self.assertEqual(stats['unique_symbols'], 2)
        self.assertEqual(stats['unique_timeframes'], 2)
        self.assertTrue('EURUSD' in stats['symbols'])
        self.assertTrue('GBPUSD' in stats['symbols'])
        self.assertTrue('H1' in stats['timeframes'])
        self.assertTrue('D1' in stats['timeframes'])

if __name__ == '__main__':
    unittest.main() 