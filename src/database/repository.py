#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Repozytorium dla operacji CRUD na tabelach bazy danych.
"""

import logging
from typing import List, Optional, Dict, Any, TypeVar, Generic, Type
from datetime import datetime
import json

from .db_manager import DatabaseManager
from .models import (
    Instrument, TradingSetup, TradingSignal, Transaction,
    OrderModification, AccountSnapshot, SystemLog,
    AIStats, PerformanceMetric
)

# Ustawienie loggera
logger = logging.getLogger('trading_agent.database.repository')

# Generyczny typ dla modeli
T = TypeVar('T')


class Repository(Generic[T]):
    """Generyczne repozytorium dla operacji CRUD."""
    
    def __init__(self, db_manager: DatabaseManager, table_name: str, model_class: Type[T]):
        """
        Inicjalizacja repozytorium.
        
        Args:
            db_manager: Instancja menedżera bazy danych
            table_name: Nazwa tabeli w bazie danych
            model_class: Klasa modelu dla tej tabeli
        """
        self.db = db_manager
        self.table_name = table_name
        self.model_class = model_class
    
    def create(self, entity: T) -> Optional[T]:
        """
        Dodanie nowego rekordu do tabeli.
        
        Args:
            entity: Instancja modelu do dodania
        
        Returns:
            Utworzony model z przypisanym ID lub None w przypadku błędu
        """
        try:
            # Konwersja dataclass do słownika (bez pól None)
            entity_dict = {k: v for k, v in entity.__dict__.items() if v is not None and k != 'id'}
            
            # Konwersja słowników na JSON
            for key, value in entity_dict.items():
                if isinstance(value, dict):
                    entity_dict[key] = json.dumps(value)
            
            # Budowa zapytania
            columns = ', '.join(entity_dict.keys())
            placeholders = ', '.join(['%s'] * len(entity_dict))
            
            query = f"""
                INSERT INTO {self.table_name} ({columns})
                VALUES ({placeholders})
                RETURNING id
            """
            
            result = self.db.execute_query(query, list(entity_dict.values()))
            if result and len(result) > 0:
                # Przypisanie ID do encji
                setattr(entity, 'id', result[0][0])
                return entity
            return None
        except Exception as e:
            logger.error(f"Błąd podczas dodawania rekordu do {self.table_name}: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return None
    
    def update(self, entity: T) -> Optional[T]:
        """
        Aktualizacja rekordu w tabeli.
        
        Args:
            entity: Instancja modelu do aktualizacji (musi mieć ustawione ID)
        
        Returns:
            Zaktualizowany model lub None w przypadku błędu
        """
        try:
            import json
            
            entity_id = getattr(entity, 'id', None)
            if entity_id is None:
                logger.error(f"Nie można zaktualizować rekordu bez ID w tabeli {self.table_name}")
                return None
            
            # Konwersja dataclass do słownika (bez pól None i bez id)
            entity_dict = {k: v for k, v in entity.__dict__.items() if v is not None and k != 'id'}
            
            # Konwersja słowników na JSON
            for key, value in entity_dict.items():
                if isinstance(value, dict):
                    entity_dict[key] = json.dumps(value)
            
            # Dodanie pola updated_at jeśli istnieje w modelu
            if hasattr(entity, 'updated_at'):
                entity_dict['updated_at'] = datetime.now()
            
            # Budowa zapytania
            set_clause = ', '.join([f"{k} = %s" for k in entity_dict.keys()])
            
            query = f"""
                UPDATE {self.table_name}
                SET {set_clause}
                WHERE id = %s
                RETURNING id
            """
            
            params = list(entity_dict.values()) + [entity_id]
            result = self.db.execute_query(query, params)
            
            if result and len(result) > 0:
                return entity
            return None
        except Exception as e:
            logger.error(f"Błąd podczas aktualizacji rekordu w {self.table_name}: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return None
    
    def delete(self, entity_id: int) -> bool:
        """
        Usunięcie rekordu z tabeli.
        
        Args:
            entity_id: ID rekordu do usunięcia
        
        Returns:
            True jeśli usunięto pomyślnie, False w przypadku błędu
        """
        try:
            query = f"DELETE FROM {self.table_name} WHERE id = %s RETURNING id"
            result = self.db.execute_query(query, [entity_id])
            
            return result and len(result) > 0
        except Exception as e:
            logger.error(f"Błąd podczas usuwania rekordu z {self.table_name}: {e}")
            return False
    
    def find_by_id(self, entity_id: int) -> Optional[T]:
        """
        Wyszukanie rekordu po ID.
        
        Args:
            entity_id: ID rekordu do znalezienia
        
        Returns:
            Instancja modelu lub None jeśli nie znaleziono
        """
        try:
            query = f"SELECT * FROM {self.table_name} WHERE id = %s"
            result = self.db.execute_query(query, [entity_id])
            
            if result and len(result) > 0:
                return self._map_row_to_entity(result[0])
            return None
        except Exception as e:
            logger.error(f"Błąd podczas wyszukiwania rekordu w {self.table_name}: {e}")
            return None
    
    def find_all(self, limit: int = 100, offset: int = 0) -> List[T]:
        """
        Pobranie wszystkich rekordów z tabeli.
        
        Args:
            limit: Maksymalna liczba rekordów do pobrania
            offset: Przesunięcie
        
        Returns:
            Lista instancji modeli
        """
        try:
            query = f"SELECT * FROM {self.table_name} ORDER BY id LIMIT %s OFFSET %s"
            result = self.db.execute_query(query, [limit, offset])
            
            if result:
                return [self._map_row_to_entity(row) for row in result]
            return []
        except Exception as e:
            logger.error(f"Błąd podczas pobierania rekordów z {self.table_name}: {e}")
            return []
    
    def find_by_field(self, field_name: str, field_value: Any) -> List[T]:
        """
        Wyszukanie rekordów po wartości pola.
        
        Args:
            field_name: Nazwa pola
            field_value: Wartość pola
        
        Returns:
            Lista instancji modeli
        """
        try:
            query = f"SELECT * FROM {self.table_name} WHERE {field_name} = %s"
            result = self.db.execute_query(query, [field_value])
            
            if result:
                return [self._map_row_to_entity(row) for row in result]
            return []
        except Exception as e:
            logger.error(f"Błąd podczas wyszukiwania rekordów w {self.table_name} po polu {field_name}: {e}")
            return []
    
    def _map_row_to_entity(self, row: Dict[str, Any]) -> T:
        """
        Mapowanie wiersza z bazy danych na instancję modelu.
        
        Args:
            row: Wiersz z bazy danych (jako słownik)
        
        Returns:
            Instancja modelu
        """
        # Konwersja dict_row do zwykłego słownika
        if hasattr(row, 'keys'):
            row_dict = {key: row[key] for key in row.keys()}
        else:
            # W przypadku zwykłej krotki, trzeba znać nazwy kolumn
            # To byłoby implementowane w przypadku specyficznego modelu
            row_dict = row
        
        return self.model_class(**row_dict)


# Konkretne implementacje repozytoriów
class InstrumentRepository(Repository[Instrument]):
    """Repozytorium dla instrumentów handlowych."""
    
    def __init__(self, db_manager: DatabaseManager):
        super().__init__(db_manager, 'instruments', Instrument)
    
    def find_by_symbol(self, symbol: str) -> Optional[Instrument]:
        """
        Wyszukanie instrumentu po symbolu.
        
        Args:
            symbol: Symbol instrumentu
        
        Returns:
            Instancja Instrument lub None jeśli nie znaleziono
        """
        results = self.find_by_field('symbol', symbol)
        return results[0] if results else None


class TradingSetupRepository(Repository[TradingSetup]):
    """Repozytorium dla setupów handlowych."""
    
    def __init__(self, db_manager: DatabaseManager):
        super().__init__(db_manager, 'trading_setups', TradingSetup)
    
    def find_by_symbol_and_timeframe(self, symbol: str, timeframe: str) -> List[TradingSetup]:
        """
        Wyszukanie setupów po symbolu i timeframe.
        
        Args:
            symbol: Symbol instrumentu
            timeframe: Przedział czasowy
        
        Returns:
            Lista setupów
        """
        try:
            query = "SELECT * FROM trading_setups WHERE symbol = %s AND timeframe = %s"
            result = self.db.execute_query(query, [symbol, timeframe])
            
            if result:
                return [self._map_row_to_entity(row) for row in result]
            return []
        except Exception as e:
            logger.error(f"Błąd podczas wyszukiwania setupów: {e}")
            return []


class TradingSignalRepository(Repository[TradingSignal]):
    """Repozytorium dla sygnałów handlowych."""
    
    def __init__(self, db_manager: DatabaseManager):
        super().__init__(db_manager, 'trading_signals', TradingSignal)
    
    def find_active_signals(self) -> List[TradingSignal]:
        """
        Wyszukanie aktywnych sygnałów.
        
        Returns:
            Lista aktywnych sygnałów
        """
        try:
            query = """
                SELECT * FROM trading_signals 
                WHERE status IN ('pending', 'active') 
                AND (expired_at IS NULL OR expired_at > NOW())
            """
            result = self.db.execute_query(query)
            
            if result:
                return [self._map_row_to_entity(row) for row in result]
            return []
        except Exception as e:
            logger.error(f"Błąd podczas wyszukiwania aktywnych sygnałów: {e}")
            return []


class TransactionRepository(Repository[Transaction]):
    """Repozytorium dla transakcji."""
    
    def __init__(self, db_manager: DatabaseManager):
        super().__init__(db_manager, 'transactions', Transaction)
    
    def find_open_positions(self) -> List[Transaction]:
        """
        Wyszukanie otwartych pozycji.
        
        Returns:
            Lista otwartych pozycji
        """
        try:
            query = "SELECT * FROM transactions WHERE status = 'open'"
            result = self.db.execute_query(query)
            
            if result:
                return [self._map_row_to_entity(row) for row in result]
            return []
        except Exception as e:
            logger.error(f"Błąd podczas wyszukiwania otwartych pozycji: {e}")
            return []


class AccountSnapshotRepository(Repository[AccountSnapshot]):
    """Repozytorium dla stanów rachunku."""
    
    def __init__(self, db_manager: DatabaseManager):
        super().__init__(db_manager, 'account_snapshots', AccountSnapshot)
    
    def get_latest_snapshot(self) -> Optional[AccountSnapshot]:
        """
        Pobranie najnowszego stanu rachunku.
        
        Returns:
            Najnowszy stan rachunku lub None
        """
        try:
            query = "SELECT * FROM account_snapshots ORDER BY created_at DESC LIMIT 1"
            result = self.db.execute_query(query)
            
            if result and len(result) > 0:
                return self._map_row_to_entity(result[0])
            return None
        except Exception as e:
            logger.error(f"Błąd podczas pobierania najnowszego stanu rachunku: {e}")
            return None


class SystemLogRepository(Repository[SystemLog]):
    """Repozytorium dla logów systemowych."""
    
    def __init__(self, db_manager: DatabaseManager):
        super().__init__(db_manager, 'system_logs', SystemLog)
    
    def add_log(self, level: str, message: str, component: str = "") -> Optional[SystemLog]:
        """
        Dodanie logu do bazy.
        
        Args:
            level: Poziom logu
            message: Treść komunikatu
            component: Nazwa komponentu
        
        Returns:
            Utworzony log lub None
        """
        log = SystemLog(log_level=level, message=message, component=component)
        return self.create(log)


class AIStatsRepository(Repository[AIStats]):
    """Repozytorium dla statystyk AI."""
    
    def __init__(self, db_manager: DatabaseManager):
        super().__init__(db_manager, 'ai_stats', AIStats)


class PerformanceMetricRepository(Repository[PerformanceMetric]):
    """Repozytorium dla metryk wydajności."""
    
    def __init__(self, db_manager: DatabaseManager):
        super().__init__(db_manager, 'performance_metrics', PerformanceMetric) 