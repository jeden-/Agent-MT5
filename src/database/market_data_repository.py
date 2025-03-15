#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Repozytorium danych rynkowych.
"""

import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
import pandas as pd

from .repository import Repository
from .models import MarketData
from .db_manager import DatabaseManager

logger = logging.getLogger(__name__)

class MarketDataRepository(Repository[MarketData]):
    """
    Repozytorium danych rynkowych, odpowiedzialne za przechowywanie i pobieranie
    danych rynkowych dla różnych instrumentów.
    """
    
    _instance = None
    
    @classmethod
    def get_instance(cls) -> 'MarketDataRepository':
        """
        Pobiera instancję repozytorium w trybie singletonu.
        
        Returns:
            MarketDataRepository: Instancja repozytorium
        """
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def __init__(self):
        """
        Inicjalizacja repozytorium danych rynkowych.
        """
        db_manager = DatabaseManager()
        super().__init__(db_manager, "market_data", MarketData)
        self.logger = logging.getLogger(__name__)
        self.cached_data = {}
    
    def save_market_data(self, symbol: str, timeframe: str, data: pd.DataFrame) -> bool:
        """
        Zapisuje dane rynkowe do bazy danych.
        
        Args:
            symbol: Symbol instrumentu
            timeframe: Interwał czasowy
            data: DataFrame z danymi rynkowymi
            
        Returns:
            bool: True jeśli zapisano pomyślnie
        """
        try:
            self.logger.info(f"Zapisywanie danych rynkowych dla {symbol} ({timeframe}): {len(data)} rekordów")
            
            success_count = 0
            for _, row in data.iterrows():
                market_data = MarketData(
                    symbol=symbol,
                    timeframe=timeframe,
                    timestamp=row['time'],
                    open=float(row['open']),
                    high=float(row['high']),
                    low=float(row['low']),
                    close=float(row['close']),
                    tick_volume=int(row['tick_volume']),
                    spread=int(row.get('spread', 0)),
                    real_volume=float(row.get('real_volume', 0.0))
                )
                
                if self.save_or_update(market_data):
                    success_count += 1
            
            self.logger.info(f"Zapisano {success_count} z {len(data)} rekordów dla {symbol} ({timeframe})")
            
            # Aktualizacja cache
            key = f"{symbol}_{timeframe}"
            self.cached_data[key] = data
            
            return success_count == len(data)
        except Exception as e:
            self.logger.error(f"Błąd podczas zapisywania danych rynkowych dla {symbol} ({timeframe}): {e}")
            return False
    
    def save_or_update(self, market_data: MarketData) -> bool:
        """
        Zapisuje lub aktualizuje pojedynczy rekord danych rynkowych.
        
        Args:
            market_data: Obiekt danych rynkowych
            
        Returns:
            bool: True jeśli zapisano pomyślnie
        """
        try:
            # Sprawdzenie, czy rekord już istnieje
            query = """
                SELECT id FROM market_data 
                WHERE symbol = %s AND timeframe = %s AND timestamp = %s
            """
            params = (market_data.symbol, market_data.timeframe, market_data.timestamp)
            result = self.db.execute_query(query, params)
            
            if result and len(result) > 0:
                # Aktualizacja istniejącego rekordu
                market_data.id = result[0]['id']
                query = """
                    UPDATE market_data SET 
                    open = %s, high = %s, low = %s, close = %s, 
                    tick_volume = %s, spread = %s, real_volume = %s
                    WHERE id = %s
                """
                params = (
                    market_data.open, market_data.high, market_data.low, market_data.close,
                    market_data.tick_volume, market_data.spread, market_data.real_volume,
                    market_data.id
                )
                self.db.execute_query(query, params, fetch=False)
            else:
                # Dodanie nowego rekordu
                query = """
                    INSERT INTO market_data 
                    (symbol, timeframe, timestamp, open, high, low, close, tick_volume, spread, real_volume, created_at) 
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                """
                params = (
                    market_data.symbol, market_data.timeframe, market_data.timestamp,
                    market_data.open, market_data.high, market_data.low, market_data.close,
                    market_data.tick_volume, market_data.spread, market_data.real_volume,
                    market_data.created_at
                )
                result = self.db.execute_query(query, params)
                if result and len(result) > 0:
                    market_data.id = result[0]['id']
            
            return True
        except Exception as e:
            self.logger.error(f"Błąd podczas zapisu/aktualizacji danych rynkowych: {e}")
            return False
    
    def get_market_data(self, symbol: str, timeframe: str, start_time: Optional[datetime] = None, 
                      end_time: Optional[datetime] = None, limit: int = 100) -> Optional[pd.DataFrame]:
        """
        Pobiera dane rynkowe z bazy danych.
        
        Args:
            symbol: Symbol instrumentu
            timeframe: Interwał czasowy
            start_time: Początkowy czas (opcjonalnie)
            end_time: Końcowy czas (opcjonalnie)
            limit: Maksymalna liczba rekordów do pobrania
            
        Returns:
            Optional[pd.DataFrame]: DataFrame z danymi rynkowymi lub None
        """
        try:
            conditions = ["symbol = %s", "timeframe = %s"]
            params = [symbol, timeframe]
            
            if start_time:
                conditions.append("timestamp >= %s")
                params.append(start_time)
            
            if end_time:
                conditions.append("timestamp <= %s")
                params.append(end_time)
            
            query = f"""
                SELECT * FROM market_data 
                WHERE {' AND '.join(conditions)}
                ORDER BY timestamp DESC
                LIMIT %s
            """
            params.append(limit)
            
            result = self.db.execute_query(query, tuple(params))
            
            if not result or len(result) == 0:
                return None
            
            # Konwersja na DataFrame
            df = pd.DataFrame(result)
            
            # Zamiana nazw kolumn na zgodne z MT5
            column_map = {
                'timestamp': 'time',
                'tick_volume': 'tick_volume',
                'real_volume': 'real_volume'
            }
            
            df = df.rename(columns=column_map)
            
            # Sortowanie po czasie
            df = df.sort_values('time')
            
            # Aktualizacja cache
            key = f"{symbol}_{timeframe}"
            self.cached_data[key] = df
            
            return df
        
        except Exception as e:
            self.logger.error(f"Błąd podczas pobierania danych rynkowych dla {symbol} ({timeframe}): {e}")
            return None
    
    def get_last_market_data(self, symbol: str, timeframe: str) -> Optional[Dict[str, Any]]:
        """
        Pobiera ostatnie dane rynkowe z bazy danych.
        
        Args:
            symbol: Symbol instrumentu
            timeframe: Interwał czasowy
            
        Returns:
            Optional[Dict[str, Any]]: Ostatnie dane rynkowe lub None
        """
        try:
            query = """
                SELECT * FROM market_data 
                WHERE symbol = %s AND timeframe = %s
                ORDER BY timestamp DESC
                LIMIT 1
            """
            params = (symbol, timeframe)
            
            result = self.db.execute_query(query, params)
            
            if result and len(result) > 0:
                # Zamiana nazw kolumn na zgodne z MT5
                data = result[0]
                data['time'] = data.pop('timestamp')
                return data
            
            return None
        
        except Exception as e:
            self.logger.error(f"Błąd podczas pobierania ostatnich danych rynkowych dla {symbol} ({timeframe}): {e}")
            return None
    
    def delete_market_data(self, symbol: str, timeframe: str, 
                         start_time: Optional[datetime] = None, 
                         end_time: Optional[datetime] = None) -> bool:
        """
        Usuwa dane rynkowe z bazy danych.
        
        Args:
            symbol: Symbol instrumentu
            timeframe: Interwał czasowy
            start_time: Początkowy czas (opcjonalnie)
            end_time: Końcowy czas (opcjonalnie)
            
        Returns:
            bool: True jeśli usunięto pomyślnie
        """
        try:
            conditions = ["symbol = %s", "timeframe = %s"]
            params = [symbol, timeframe]
            
            if start_time:
                conditions.append("timestamp >= %s")
                params.append(start_time)
            
            if end_time:
                conditions.append("timestamp <= %s")
                params.append(end_time)
            
            query = f"""
                DELETE FROM market_data 
                WHERE {' AND '.join(conditions)}
            """
            
            self.db.execute_query(query, tuple(params), fetch=False)
            
            # Usunięcie z cache
            key = f"{symbol}_{timeframe}"
            if key in self.cached_data:
                del self.cached_data[key]
            
            return True
        
        except Exception as e:
            self.logger.error(f"Błąd podczas usuwania danych rynkowych dla {symbol} ({timeframe}): {e}")
            return False
    
    def get_symbols(self) -> List[str]:
        """
        Pobiera listę wszystkich symboli instrumentów w bazie danych.
        
        Returns:
            List[str]: Lista symboli
        """
        try:
            query = """
                SELECT DISTINCT symbol FROM market_data
            """
            
            result = self.db.execute_query(query)
            
            if result:
                return [row['symbol'] for row in result]
            
            return []
        
        except Exception as e:
            self.logger.error(f"Błąd podczas pobierania listy symboli: {e}")
            return []
    
    def get_timeframes(self, symbol: Optional[str] = None) -> List[str]:
        """
        Pobiera listę wszystkich przedziałów czasowych w bazie danych.
        
        Args:
            symbol: Symbol instrumentu (opcjonalnie)
            
        Returns:
            List[str]: Lista przedziałów czasowych
        """
        try:
            if symbol:
                query = """
                    SELECT DISTINCT timeframe FROM market_data
                    WHERE symbol = %s
                """
                params = (symbol,)
                result = self.db.execute_query(query, params)
            else:
                query = """
                    SELECT DISTINCT timeframe FROM market_data
                """
                result = self.db.execute_query(query)
            
            if result:
                return [row['timeframe'] for row in result]
            
            return []
        
        except Exception as e:
            self.logger.error(f"Błąd podczas pobierania listy przedziałów czasowych: {e}")
            return []


def get_market_data_repository() -> MarketDataRepository:
    """
    Funkcja pomocnicza do pobierania instancji repozytorium danych rynkowych.
    
    Returns:
        MarketDataRepository: Instancja repozytorium
    """
    return MarketDataRepository.get_instance()


def save_market_data(symbol: str, timeframe: str, data: pd.DataFrame) -> bool:
    """
    Funkcja pomocnicza do zapisywania danych rynkowych.
    
    Args:
        symbol: Symbol instrumentu
        timeframe: Interwał czasowy
        data: DataFrame z danymi rynkowymi
        
    Returns:
        bool: True jeśli zapisano pomyślnie
    """
    repo = get_market_data_repository()
    return repo.save_market_data(symbol, timeframe, data) 