#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Moduł do zarządzania danymi historycznymi dla systemu backtestingu.

Ten moduł zawiera funkcje i klasy do pobierania, przechowywania i zarządzania
danymi historycznymi, wykorzystywanymi w backtestingu strategii handlowych.
"""

import os
import re
import logging
import hashlib
from typing import Dict, List, Optional, Tuple, Any, Union
from datetime import datetime, timedelta
from pathlib import Path
import pandas as pd
import numpy as np
import threading

from src.mt5_bridge.mt5_connector import MT5Connector

logger = logging.getLogger(__name__)

class HistoricalDataManager:
    """
    Klasa do zarządzania danymi historycznymi dla systemu backtestingu.
    
    Klasa implementuje mechanizm cache'owania danych historycznych w formacie Parquet
    dla efektywnego backtestingu. Dane są organizowane według symbolu, timeframe'u 
    i zakresu czasowego w celu łatwego dostępu i zarządzania.
    
    Attributes:
        cache_dir (Path): Ścieżka do katalogu cache
        mt5_connector (MT5Connector): Konektor do MT5 do pobierania danych
        validate_data (bool): Czy walidować dane przed zapisem
        cache_metadata (Dict): Metadane o zbuforowanych danych
        lock (threading.Lock): Blokada dla operacji zapisu/odczytu
    """
    
    def __init__(self, 
                 cache_dir: str = "market_data_cache", 
                 mt5_connector: Optional[MT5Connector] = None,
                 validate_data: bool = True):
        """
        Inicjalizacja menedżera danych historycznych.
        
        Args:
            cache_dir: Ścieżka do katalogu cache
            mt5_connector: Konektor do MT5 do pobierania danych
            validate_data: Czy walidować dane przed zapisem
        """
        self.cache_dir = Path(cache_dir)
        self.mt5_connector = mt5_connector
        self.validate_data = validate_data
        self.cache_metadata = {}
        self.lock = threading.Lock()
        
        # Tworzenie katalogu cache, jeśli nie istnieje
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Inicjalizacja metadanych cache'u
        self._initialize_cache_metadata()
        
        logger.info(f"Inicjalizacja HistoricalDataManager z katalogiem cache: {self.cache_dir}")
    
    def _initialize_cache_metadata(self):
        """Inicjalizacja metadanych cache'u na podstawie istniejących plików."""
        try:
            with self.lock:
                if not self.cache_dir.exists():
                    logger.warning(f"Katalog cache {self.cache_dir} nie istnieje. Tworzenie...")
                    self.cache_dir.mkdir(parents=True, exist_ok=True)
                    return
                
                # Skanowanie plików w cache
                for file_path in self.cache_dir.glob("*.parquet"):
                    try:
                        # Ekstrakcja informacji z nazwy pliku
                        match = re.search(r"([A-Za-z0-9]+)_([A-Za-z0-9]+)_(\d{8})_(\d{8})\.parquet", file_path.name)
                        if match:
                            symbol, timeframe, start_date_str, end_date_str = match.groups()
                            start_date = datetime.strptime(start_date_str, "%Y%m%d")
                            end_date = datetime.strptime(end_date_str, "%Y%m%d")
                            
                            # Dodanie do metadanych
                            key = f"{symbol}_{timeframe}"
                            if key not in self.cache_metadata:
                                self.cache_metadata[key] = []
                            
                            # Dodanie informacji o pliku
                            file_info = {
                                "path": file_path,
                                "start_date": start_date,
                                "end_date": end_date,
                                "size": file_path.stat().st_size,
                                "created": datetime.fromtimestamp(file_path.stat().st_ctime)
                            }
                            self.cache_metadata[key].append(file_info)
                    except Exception as e:
                        logger.error(f"Błąd podczas przetwarzania pliku cache {file_path}: {e}")
                
                # Sortowanie plików dla każdego klucza według daty
                for key in self.cache_metadata:
                    self.cache_metadata[key].sort(key=lambda x: x["start_date"])
                
                logger.info(f"Zainicjalizowano metadane cache. Znaleziono dane dla {len(self.cache_metadata)} par symbol-timeframe.")
        except Exception as e:
            logger.error(f"Błąd podczas inicjalizacji metadanych cache: {e}")
    
    def get_historical_data(self, 
                           symbol: str, 
                           timeframe: str, 
                           start_date: Union[datetime, str], 
                           end_date: Union[datetime, str],
                           use_cache: bool = True,
                           update_cache: bool = True,
                           use_synthetic: bool = False) -> Optional[pd.DataFrame]:
        """
        Pobiera dane historyczne dla danego symbolu i timeframe'u.
        
        Args:
            symbol: Symbol instrumentu
            timeframe: Timeframe (np. "M1", "M5", "H1")
            start_date: Data początkowa
            end_date: Data końcowa
            use_cache: Czy używać cache'u
            update_cache: Czy aktualizować cache w przypadku braku danych
            use_synthetic: Czy używać danych syntetycznych, gdy rzeczywiste dane są niedostępne
            
        Returns:
            DataFrame z danymi historycznymi lub None w przypadku błędu
        """
        # Konwersja dat do obiektów datetime, jeśli są stringami
        if isinstance(start_date, str):
            start_date = datetime.strptime(start_date, "%Y-%m-%d") if "-" in start_date else datetime.strptime(start_date, "%Y%m%d")
        if isinstance(end_date, str):
            end_date = datetime.strptime(end_date, "%Y-%m-%d") if "-" in end_date else datetime.strptime(end_date, "%Y%m%d")
        
        logger.info(f"Pobieranie danych historycznych dla {symbol} {timeframe} od {start_date} do {end_date}")
        
        # Jeśli nie używamy cache'u, pobierz dane z MT5
        if not use_cache:
            return self._fetch_from_mt5(symbol, timeframe, start_date, end_date)
        
        # Sprawdź czy mamy dane w cache'u
        cached_data = self._load_cached_data(symbol, timeframe, start_date, end_date)
        
        # Jeśli dane są kompletne, zwróć je
        if cached_data is not None and not cached_data.empty:
            logger.info(f"Pobrano dane z cache dla {symbol} {timeframe} ({len(cached_data)} rekordów)")
            return cached_data
        
        # Jeśli nie mamy danych w cache'u lub są niekompletne
        if update_cache:
            # Pobierz dane z MT5
            mt5_data = self._fetch_from_mt5(symbol, timeframe, start_date, end_date)
            
            # Jeśli udało się pobrać dane, zapisz je do cache'u
            if mt5_data is not None and not mt5_data.empty:
                self.cache_data(symbol, timeframe, mt5_data)
                logger.info(f"Pobrano dane z MT5 i zapisano do cache dla {symbol} {timeframe} ({len(mt5_data)} rekordów)")
                return mt5_data
        
        # Jeśli nie udało się pobrać danych i use_synthetic jest True, można by tu dodać generowanie danych syntetycznych
        if use_synthetic:
            logger.warning(f"Nie udało się pobrać danych dla {symbol} {timeframe}. Parametr use_synthetic=True, ale funkcjonalność nie jest zaimplementowana.")
            # TODO: Implementacja generowania danych syntetycznych
        
        # Jeśli nie udało się pobrać danych
        logger.warning(f"Nie udało się pobrać danych dla {symbol} {timeframe} od {start_date} do {end_date}")
        return None
    
    def _fetch_from_mt5(self,
                       symbol: str,
                       timeframe: str,
                       start_date: datetime,
                       end_date: datetime) -> Optional[pd.DataFrame]:
        """
        Pobiera dane bezpośrednio z MT5.
        
        Args:
            symbol: Symbol instrumentu
            timeframe: Timeframe
            start_date: Data początkowa
            end_date: Data końcowa
            
        Returns:
            DataFrame z danymi lub None w przypadku błędu
        """
        if self.mt5_connector is None:
            logger.error("Brak połączenia z MT5. Nie można pobrać danych.")
            return None
        
        try:
            # Pobieranie danych z MT5
            data = self.mt5_connector.get_historical_data(
                symbol=symbol,
                timeframe=timeframe,
                start_time=start_date,
                end_time=end_date,
                count=100000  # Duża wartość, aby pobrać wszystkie dostępne dane
            )
            
            if data is None or data.empty:
                logger.warning(f"Brak danych z MT5 dla {symbol} {timeframe} od {start_date} do {end_date}")
                return None
            
            # Walidacja danych
            if self.validate_data:
                data = self._validate_and_clean_data(data)
            
            return data
        
        except Exception as e:
            logger.error(f"Błąd podczas pobierania danych z MT5: {e}")
            return None
    
    def _validate_and_clean_data(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Waliduje i czyści dane historyczne.
        
        Args:
            data: DataFrame z danymi do walidacji
            
        Returns:
            Oczyszczony DataFrame
        """
        # Sprawdzenie wymaganych kolumn
        required_columns = ['time', 'open', 'high', 'low', 'close', 'volume']
        for col in required_columns:
            if col not in data.columns:
                logger.warning(f"Brakująca kolumna {col} w danych. Dodawanie wartości domyślnej.")
                
                # Dodanie wartości domyślnej
                if col == 'time':
                    data[col] = pd.date_range(start=datetime.now() - timedelta(days=len(data)), periods=len(data), freq='H')
                elif col == 'volume':
                    data[col] = 0
                else:
                    # Dla kolumn cenowych, użyj średniej z dostępnych kolumn
                    price_cols = [c for c in ['open', 'high', 'low', 'close'] if c in data.columns]
                    if price_cols:
                        data[col] = data[price_cols].mean(axis=1)
                    else:
                        data[col] = 0.0
        
        # Sprawdzenie wartości NULL
        for col in data.columns:
            if data[col].isnull().any():
                null_count = data[col].isnull().sum()
                logger.warning(f"Znaleziono {null_count} wartości NULL w kolumnie {col}. Wypełnianie...")
                
                # Wypełnianie NULL-i
                if col == 'time':
                    # Dla czasu, możemy interpolować
                    data = data.sort_values('time')
                    data['time'] = pd.date_range(
                        start=data['time'].min(), 
                        end=data['time'].max(), 
                        periods=len(data)
                    )
                elif col in ['open', 'high', 'low', 'close']:
                    # Dla cen, użyj metody interpolacji
                    data[col] = data[col].interpolate(method='linear')
                elif col == 'volume':
                    # Dla wolumenu, wypełnij zerami
                    data[col] = data[col].fillna(0)
                else:
                    # Dla innych kolumn, użyj mediany
                    data[col] = data[col].fillna(data[col].median())
        
        # Sortowanie po czasie
        if 'time' in data.columns:
            data = data.sort_values('time')
        
        # Usunięcie duplikatów
        if 'time' in data.columns:
            data = data.drop_duplicates(subset=['time'])
        
        return data
    
    def cache_data(self, symbol: str, timeframe: str, data: pd.DataFrame) -> Optional[Path]:
        """
        Zapisuje dane historyczne do cache'u.
        
        Args:
            symbol: Symbol instrumentu
            timeframe: Timeframe
            data: DataFrame z danymi do zapisania
            
        Returns:
            Ścieżka do zapisanego pliku lub None w przypadku błędu
        """
        if data is None or data.empty:
            logger.warning(f"Puste dane dla {symbol} {timeframe}. Nie zapisuję do cache.")
            return None
        
        try:
            with self.lock:
                # Walidacja danych przed zapisem
                if self.validate_data:
                    data = self._validate_and_clean_data(data)
                
                # Format nazwy pliku
                if 'time' in data.columns:
                    # Użyj pierwszej i ostatniej daty z danych
                    min_date = data['time'].min().strftime('%Y%m%d')
                    max_date = data['time'].max().strftime('%Y%m%d')
                else:
                    # Użyj aktualnej daty
                    current_date = datetime.now().strftime('%Y%m%d')
                    min_date = max_date = current_date
                
                filename = f"{symbol}_{timeframe}_{min_date}_{max_date}.parquet"
                file_path = self.cache_dir / filename
                
                # Zapis do pliku Parquet
                data.to_parquet(file_path, index=False)
                
                # Aktualizacja metadanych
                key = f"{symbol}_{timeframe}"
                if key not in self.cache_metadata:
                    self.cache_metadata[key] = []
                
                # Dodanie informacji o nowym pliku
                file_info = {
                    "path": file_path,
                    "start_date": datetime.strptime(min_date, "%Y%m%d"),
                    "end_date": datetime.strptime(max_date, "%Y%m%d"),
                    "size": file_path.stat().st_size,
                    "created": datetime.now()
                }
                self.cache_metadata[key].append(file_info)
                
                # Sortowanie plików według daty
                self.cache_metadata[key].sort(key=lambda x: x["start_date"])
                
                logger.info(f"Zapisano dane do cache: {file_path} ({file_path.stat().st_size / 1024:.2f} KB)")
                return file_path
                
        except Exception as e:
            logger.error(f"Błąd podczas zapisywania danych do cache: {e}")
            return None
    
    def _load_cached_data(self, 
                         symbol: str, 
                         timeframe: str, 
                         start_date: datetime, 
                         end_date: datetime) -> Optional[pd.DataFrame]:
        """
        Ładuje dane z cache'u dla podanego okresu.
        
        Args:
            symbol: Symbol instrumentu
            timeframe: Timeframe
            start_date: Data początkowa
            end_date: Data końcowa
            
        Returns:
            DataFrame z danymi lub None, jeśli dane nie są dostępne w cache
        """
        try:
            with self.lock:
                key = f"{symbol}_{timeframe}"
                
                # Sprawdź czy mamy dane dla tej pary symbol-timeframe
                if key not in self.cache_metadata or not self.cache_metadata[key]:
                    logger.debug(f"Brak danych w cache dla {symbol} {timeframe}")
                    return None
                
                # Znajdź pliki, które mogą zawierać dane z żądanego okresu
                relevant_files = []
                for file_info in self.cache_metadata[key]:
                    file_start = file_info["start_date"]
                    file_end = file_info["end_date"]
                    
                    # Sprawdź czy zakres czasowy pliku pokrywa się z żądanym
                    if (file_start <= end_date and file_end >= start_date):
                        relevant_files.append(file_info)
                
                if not relevant_files:
                    logger.debug(f"Brak odpowiednich plików w cache dla {symbol} {timeframe} od {start_date} do {end_date}")
                    return None
                
                # Wczytaj dane z każdego odpowiedniego pliku
                dfs = []
                for file_info in relevant_files:
                    file_path = file_info["path"]
                    
                    # Sprawdź czy plik istnieje
                    if not file_path.exists():
                        logger.warning(f"Plik {file_path} nie istnieje mimo obecności w metadanych. Usuwam z metadanych.")
                        continue
                    
                    # Wczytaj dane
                    df = pd.read_parquet(file_path)
                    
                    # Filtruj dane według zakresu czasowego
                    if 'time' in df.columns:
                        df = df[(df['time'] >= pd.Timestamp(start_date)) & 
                                (df['time'] <= pd.Timestamp(end_date))]
                    
                    if not df.empty:
                        dfs.append(df)
                
                if not dfs:
                    logger.debug(f"Wczytane pliki cache nie zawierają danych dla {symbol} {timeframe} od {start_date} do {end_date}")
                    return None
                
                # Połącz wszystkie DataFrame'y
                combined_df = pd.concat(dfs, ignore_index=True)
                
                # Usuń duplikaty (jeśli istnieją)
                if 'time' in combined_df.columns:
                    combined_df = combined_df.drop_duplicates(subset=['time'])
                    combined_df = combined_df.sort_values('time')
                
                # Sprawdź kompletność danych
                if 'time' in combined_df.columns:
                    # Prosta heurystyka - sprawdź czy mamy przynajmniej 90% oczekiwanych danych
                    expected_points = self._estimate_expected_data_points(timeframe, start_date, end_date)
                    actual_points = len(combined_df)
                    
                    completeness = actual_points / expected_points if expected_points > 0 else 0
                    if completeness < 0.9:  # Arbitralny próg kompletności
                        logger.warning(f"Dane z cache są niekompletne: {actual_points}/{expected_points} punktów ({completeness:.2%})")
                        # Zwracamy dane mimo niekompletności, ale logujemy ostrzeżenie
                
                return combined_df
                
        except Exception as e:
            logger.error(f"Błąd podczas ładowania danych z cache: {e}")
            return None
    
    def _estimate_expected_data_points(self, timeframe: str, start_date: datetime, end_date: datetime) -> int:
        """
        Szacuje oczekiwaną liczbę punktów danych dla danego timeframe'u i okresu.
        
        Args:
            timeframe: Timeframe
            start_date: Data początkowa
            end_date: Data końcowa
            
        Returns:
            Przybliżona liczba punktów danych
        """
        # Konwersja różnicy czasu na minuty
        total_minutes = (end_date - start_date).total_seconds() / 60
        
        # Obliczenie liczby punktów na podstawie timeframe'u
        if timeframe == "M1":
            return int(total_minutes)
        elif timeframe == "M5":
            return int(total_minutes / 5)
        elif timeframe == "M15":
            return int(total_minutes / 15)
        elif timeframe == "M30":
            return int(total_minutes / 30)
        elif timeframe == "H1":
            return int(total_minutes / 60)
        elif timeframe == "H4":
            return int(total_minutes / 240)
        elif timeframe == "D1":
            return int(total_minutes / 1440)
        elif timeframe == "W1":
            return int(total_minutes / (1440 * 7))
        elif timeframe == "MN1":
            return int(total_minutes / (1440 * 30))
        else:
            return int(total_minutes)  # Domyślnie zakładamy M1
    
    def clear_cache(self, 
                   symbol: Optional[str] = None, 
                   timeframe: Optional[str] = None,
                   older_than: Optional[datetime] = None) -> int:
        """
        Czyści cache dla określonych parametrów.
        
        Args:
            symbol: Symbol do wyczyszczenia (None = wszystkie)
            timeframe: Timeframe do wyczyszczenia (None = wszystkie)
            older_than: Usuń tylko dane starsze niż ta data
            
        Returns:
            Liczba usuniętych plików
        """
        try:
            with self.lock:
                deleted_count = 0
                keys_to_check = []
                
                # Określ klucze do sprawdzenia
                if symbol is not None and timeframe is not None:
                    keys_to_check = [f"{symbol}_{timeframe}"]
                elif symbol is not None:
                    keys_to_check = [k for k in self.cache_metadata.keys() if k.startswith(f"{symbol}_")]
                elif timeframe is not None:
                    keys_to_check = [k for k in self.cache_metadata.keys() if k.endswith(f"_{timeframe}")]
                else:
                    keys_to_check = list(self.cache_metadata.keys())
                
                # Dla każdego klucza
                for key in keys_to_check:
                    files_to_keep = []
                    
                    for file_info in self.cache_metadata[key]:
                        file_path = file_info["path"]
                        
                        # Sprawdź czy plik powinien zostać usunięty
                        if older_than is not None and file_info["created"] >= older_than:
                            files_to_keep.append(file_info)
                            continue
                        
                        # Usuń plik
                        if file_path.exists():
                            file_path.unlink()
                            deleted_count += 1
                            logger.info(f"Usunięto plik cache: {file_path}")
                        else:
                            logger.warning(f"Plik {file_path} nie istnieje mimo obecności w metadanych.")
                    
                    # Aktualizacja metadanych
                    if files_to_keep:
                        self.cache_metadata[key] = files_to_keep
                    else:
                        del self.cache_metadata[key]
                
                logger.info(f"Wyczyszczono cache. Usunięto {deleted_count} plików.")
                return deleted_count
                
        except Exception as e:
            logger.error(f"Błąd podczas czyszczenia cache: {e}")
            return 0
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Pobiera statystyki cache'u.
        
        Returns:
            Słownik ze statystykami cache'u
        """
        try:
            with self.lock:
                total_size = 0
                total_files = 0
                symbols = set()
                timeframes = set()
                oldest_file = datetime.now()
                newest_file = datetime(1970, 1, 1)
                
                # Zbieranie statystyk
                for key, files in self.cache_metadata.items():
                    for file_info in files:
                        total_size += file_info["size"]
                        total_files += 1
                        
                        if file_info["created"] < oldest_file:
                            oldest_file = file_info["created"]
                        if file_info["created"] > newest_file:
                            newest_file = file_info["created"]
                    
                    # Ekstrakcja symbolu i timeframe'u z klucza
                    if "_" in key:
                        sym, tf = key.split("_", 1)
                        symbols.add(sym)
                        timeframes.add(tf)
                
                # Przygotowanie wyniku
                return {
                    "total_size_kb": total_size / 1024,
                    "total_size_mb": total_size / (1024 * 1024),
                    "total_files": total_files,
                    "unique_symbols": len(symbols),
                    "symbols": list(symbols),
                    "unique_timeframes": len(timeframes),
                    "timeframes": list(timeframes),
                    "oldest_file": oldest_file if total_files > 0 else None,
                    "newest_file": newest_file if total_files > 0 else None,
                }
                
        except Exception as e:
            logger.error(f"Błąd podczas pobierania statystyk cache: {e}")
            return {
                "error": str(e),
                "total_size_kb": 0,
                "total_files": 0
            }

def create_historical_data_manager(mt5_connector: Optional[MT5Connector] = None) -> HistoricalDataManager:
    """
    Tworzy i zwraca instancję HistoricalDataManager.
    
    Args:
        mt5_connector: Opcjonalny konektor MT5
        
    Returns:
        Instancja HistoricalDataManager
    """
    return HistoricalDataManager(mt5_connector=mt5_connector) 