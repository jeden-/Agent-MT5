#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Testy jednostkowe dla klasy HistoricalDataManager.

Ten moduł zawiera testy weryfikujące poprawność działania klasy HistoricalDataManager,
która jest odpowiedzialna za zarządzanie danymi historycznymi w systemie backtestingu.
"""

import os
import unittest
from unittest.mock import Mock, patch, MagicMock, call, ANY
from datetime import datetime, timedelta
import tempfile
import shutil
import pandas as pd
import numpy as np

# Patch dla MT5Connector przed importem HistoricalDataManager
with patch('src.mt5_bridge.mt5_connector.MT5Connector') as mock_mt5_connector_class:
    # Teraz importujemy HistoricalDataManager
    from src.backtest.historical_data_manager import HistoricalDataManager


class TestHistoricalDataManager(unittest.TestCase):
    """Testy dla klasy HistoricalDataManager."""
    
    def setUp(self):
        """Przygotowanie środowiska testowego."""
        # Tworzenie tymczasowego katalogu dla cache'u
        self.temp_dir = tempfile.mkdtemp()
        
        # Konfiguracja ścieżki do katalogu cache
        self.cache_dir = self.temp_dir
        
        # Mock dla MT5Connector
        self.mt5_connector_mock = Mock()
        
        # Przykładowe dane historyczne w formacie DataFrame
        self.sample_data = pd.DataFrame({
            'time': pd.date_range(start='2023-01-01', periods=100, freq='H'),
            'open': np.random.rand(100) * 100,
            'high': np.random.rand(100) * 100 + 10,
            'low': np.random.rand(100) * 100 - 10,
            'close': np.random.rand(100) * 100,
            'tick_volume': np.random.randint(1, 1000, 100),
            'spread': np.random.randint(1, 10, 100),
            'real_volume': np.random.randint(1, 10000, 100)
        })
        
        # Ustawienie daty i czasu dla testów
        self.start_date = datetime(2023, 1, 1)
        self.end_date = datetime(2023, 1, 5)
        
        # Przykładowe parametry 
        self.symbol = "EURUSD"
        self.timeframe = "H1"
    
    def tearDown(self):
        """Czyszczenie po testach."""
        # Usunięcie tymczasowego katalogu
        shutil.rmtree(self.temp_dir)
    
    def test_init(self):
        """Test inicjalizacji klasy HistoricalDataManager."""
        # Inicjalizacja HistoricalDataManager z podanym mockiem
        data_manager = HistoricalDataManager(
            cache_dir=self.cache_dir,
            mt5_connector=self.mt5_connector_mock
        )
        
        # Sprawdzenie, czy atrybuty zostały poprawnie ustawione
        self.assertEqual(data_manager.mt5_connector, self.mt5_connector_mock)
        self.assertTrue(os.path.exists(self.cache_dir))
    
    def test_get_historical_data_from_mt5(self):
        """Test pobierania danych historycznych z MT5."""
        # Ustawienie mocka dla MT5Connector.get_historical_data
        self.mt5_connector_mock.get_historical_data.return_value = self.sample_data
        
        # Inicjalizacja HistoricalDataManager z podanym mockiem
        data_manager = HistoricalDataManager(
            cache_dir=self.cache_dir,
            mt5_connector=self.mt5_connector_mock
        )
        
        # Wywołanie metody get_historical_data z use_cache=False
        result = data_manager.get_historical_data(
            symbol=self.symbol,
            timeframe=self.timeframe,
            start_date=self.start_date,
            end_date=self.end_date,
            use_cache=False,  # Wymuszamy pobieranie z MT5, nie z cache'u
            update_cache=True
        )
        
        # Sprawdzenie, czy MT5Connector.get_historical_data został wywołany z odpowiednimi parametrami
        self.mt5_connector_mock.get_historical_data.assert_called_once()
        args, kwargs = self.mt5_connector_mock.get_historical_data.call_args
        
        # Sprawdzenie parametrów wywołania
        self.assertEqual(kwargs['symbol'], self.symbol)
        self.assertEqual(kwargs['timeframe'], self.timeframe)
        self.assertEqual(kwargs['start_time'], self.start_date)
        self.assertEqual(kwargs['end_time'], self.end_date)
        
        # Sprawdzenie, czy zwrócone dane są poprawne
        pd.testing.assert_frame_equal(result, self.sample_data)
    
    @patch('src.backtest.historical_data_manager.HistoricalDataManager._load_cached_data')
    def test_get_historical_data_from_cache(self, mock_load_cached_data):
        """Test pobierania danych historycznych z cache'u."""
        # Konfiguracja mocków
        self.mt5_connector_mock.get_historical_data.return_value = self.sample_data
        mock_load_cached_data.return_value = self.sample_data  # Symulacja danych z cache
        
        # Inicjalizacja HistoricalDataManager
        data_manager = HistoricalDataManager(
            cache_dir=self.cache_dir,
            mt5_connector=self.mt5_connector_mock
        )
        
        # Wywołanie metody get_historical_data z use_cache=True
        result = data_manager.get_historical_data(
            symbol=self.symbol,
            timeframe=self.timeframe,
            start_date=self.start_date,
            end_date=self.end_date,
            use_cache=True,
            update_cache=False
        )
        
        # Sprawdzenie, czy _load_cached_data został wywołany
        mock_load_cached_data.assert_called_once()
        
        # Sprawdzenie, czy MT5Connector.get_historical_data NIE został wywołany
        self.mt5_connector_mock.get_historical_data.assert_not_called()
        
        # Sprawdzenie, czy zwrócone dane są takie same jak oryginalne dane
        self.assertIsInstance(result, pd.DataFrame)
        pd.testing.assert_frame_equal(result, self.sample_data)
    
    def test_get_historical_data_update_cache(self):
        """Test aktualizacji cache'u."""
        # Tworzymy dwa zestawy danych - stare i nowe
        old_data = self.sample_data.copy()
        new_data = pd.DataFrame({
            'time': pd.date_range(start='2023-01-05', periods=50, freq='H'),
            'open': np.random.rand(50) * 100,
            'high': np.random.rand(50) * 100 + 10,
            'low': np.random.rand(50) * 100 - 10,
            'close': np.random.rand(50) * 100,
            'tick_volume': np.random.randint(1, 1000, 50),
            'spread': np.random.randint(1, 10, 50),
            'real_volume': np.random.randint(1, 10000, 50)
        })
        
        # Ustawienie mocka dla MT5Connector
        self.mt5_connector_mock.get_historical_data.side_effect = [old_data, new_data]
        
        # Inicjalizacja HistoricalDataManager
        data_manager = HistoricalDataManager(
            cache_dir=self.cache_dir,
            mt5_connector=self.mt5_connector_mock
        )
        
        # Najpierw zapisujemy stare dane w cache'u
        result1 = data_manager.get_historical_data(
            symbol=self.symbol,
            timeframe=self.timeframe,
            start_date=self.start_date,
            end_date=self.end_date,
            use_cache=False,
            update_cache=True
        )
        
        # Teraz próbujemy pobrać nowe dane z aktualizacją cache'u
        result2 = data_manager.get_historical_data(
            symbol=self.symbol,
            timeframe=self.timeframe,
            start_date=datetime(2023, 1, 5),
            end_date=datetime(2023, 1, 7),
            use_cache=False,  # Wymuszamy pobieranie z MT5, nie z cache'u
            update_cache=True
        )
        
        # Sprawdzenie, czy MT5Connector.get_historical_data został wywołany dwukrotnie
        self.assertEqual(self.mt5_connector_mock.get_historical_data.call_count, 2)
        
        # Sprawdzenie, czy zwrócone dane są poprawne
        pd.testing.assert_frame_equal(result1, old_data)
        pd.testing.assert_frame_equal(result2, new_data)
    
    def test_get_historical_data_with_synthetic(self):
        """Test obsługi danych syntetycznych w przypadku braku rzeczywistych danych."""
        # Ustawienie mocka dla MT5Connector - zwracamy None, aby zasymulować brak danych
        self.mt5_connector_mock.get_historical_data.return_value = None
        
        # Inicjalizacja HistoricalDataManager
        data_manager = HistoricalDataManager(
            cache_dir=self.cache_dir,
            mt5_connector=self.mt5_connector_mock
        )
        
        # Próbujemy pobrać dane z opcją use_synthetic=True
        result = data_manager.get_historical_data(
            symbol=self.symbol,
            timeframe=self.timeframe,
            start_date=self.start_date,
            end_date=self.end_date,
            use_cache=False,
            update_cache=False,
            use_synthetic=True
        )
        
        # Sprawdzenie, czy zwrócone dane są None (w rzeczywistości funkcja generate_synthetic_data
        # nie jest zaimplementowana, więc powinno zwrócić None)
        self.assertIsNone(result)
        
        # W przyszłości, gdy generate_synthetic_data zostanie zaimplementowane:
        # self.assertIsInstance(result, pd.DataFrame)
        # self.assertTrue(result.shape[0] > 0)
    
    def test_get_historical_data_error_handling(self):
        """Test obsługi błędów przy pobieraniu danych."""
        # Ustawienie mocka dla MT5Connector - rzucamy wyjątek
        self.mt5_connector_mock.get_historical_data.side_effect = Exception("Test error")
        
        # Inicjalizacja HistoricalDataManager
        data_manager = HistoricalDataManager(
            cache_dir=self.cache_dir,
            mt5_connector=self.mt5_connector_mock
        )
        
        # Próbujemy pobrać dane
        result = data_manager.get_historical_data(
            symbol=self.symbol,
            timeframe=self.timeframe,
            start_date=self.start_date,
            end_date=self.end_date,
            use_cache=False,
            update_cache=False
        )
        
        # Sprawdzenie, czy zwrócone dane są None
        self.assertIsNone(result)
    
    @patch('pandas.DataFrame.interpolate')
    @patch('pandas.DataFrame.fillna')
    def test_clean_and_validate_data(self, mock_fillna, mock_interpolate):
        """Test czyszczenia i walidacji danych."""
        # Ustawienie zwracanych wartości dla mocków
        mock_fillna.return_value = pd.Series([0] * 100)
        mock_interpolate.return_value = pd.Series([100] * 100)
        
        # Tworzymy dane z duplikatami i brakami
        data_with_issues = pd.DataFrame({
            'time': pd.date_range(start='2023-01-01', periods=100, freq='H').tolist() + 
                    [pd.Timestamp('2023-01-01 00:00:00')] * 5,  # Duplikaty
            'open': np.random.rand(105) * 100,
            'high': np.random.rand(105) * 100 + 10,
            'low': np.random.rand(105) * 100 - 10,
            'close': np.random.rand(105) * 100,
            'tick_volume': np.random.randint(1, 1000, 105),
            'spread': np.random.randint(1, 10, 105),
            'real_volume': np.random.randint(1, 10000, 105)
        })
        
        # Inicjalizacja HistoricalDataManager
        data_manager = HistoricalDataManager(
            cache_dir=self.cache_dir,
            mt5_connector=self.mt5_connector_mock
        )
        
        # Wywołujemy metodę _validate_and_clean_data bezpośrednio
        result = data_manager._validate_and_clean_data(data_with_issues)
        
        # Sprawdzenie, czy dane zostały przetworzone
        self.assertIsInstance(result, pd.DataFrame)
        
        # Sprawdzenie usunięcia duplikatów - to można sprawdzić mimo mocków
        self.assertLessEqual(len(result), 100)  # Powinno być mniej niż 105 (usunięto duplikaty)


if __name__ == '__main__':
    unittest.main() 