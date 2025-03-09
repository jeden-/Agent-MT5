import logging
import os
import json
import psycopg2
from psycopg2 import sql
from psycopg2.extras import RealDictCursor
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timedelta

# Konfiguracja loggera
logger = logging.getLogger(__name__)

class DBManager:
    """Klasa do obsługi bazy danych dla zarządzania pozycjami."""
    
    def __init__(self, connection_string: str):
        """
        Inicjalizacja menedżera bazy danych.
        
        Args:
            connection_string: String połączenia z bazą danych PostgreSQL
        """
        self.conn_string = connection_string
        self.conn = None
        self.cursor = None
        
        # Inicjalizacja połączenia
        self._connect()
        
        # Załadowanie i wykonanie schematu bazy danych
        self._init_db_schema()
        
        logger.info("DBManager zainicjalizowany")
    
    def _connect(self) -> None:
        """Nawiązuje połączenie z bazą danych."""
        try:
            self.conn = psycopg2.connect(self.conn_string)
            self.conn.autocommit = False
            self.cursor = self.conn.cursor(cursor_factory=RealDictCursor)
            logger.info("Połączono z bazą danych")
        except Exception as e:
            logger.error(f"Błąd podczas łączenia z bazą danych: {e}")
            raise
    
    def _disconnect(self) -> None:
        """Zamyka połączenie z bazą danych."""
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()
        logger.info("Rozłączono z bazą danych")
    
    def _reconnect_if_needed(self) -> None:
        """Sprawdza i odnawia połączenie z bazą danych w razie potrzeby."""
        try:
            # Sprawdzenie, czy połączenie jest aktywne
            if self.conn and not self.conn.closed:
                # Wykonanie prostego zapytania testowego
                self.cursor.execute("SELECT 1")
                self.cursor.fetchone()
                return
        except Exception:
            logger.warning("Wykryto nieaktywne połączenie z bazą danych - próba ponownego połączenia")
        
        # Rozłączenie i ponowne połączenie
        self._disconnect()
        self._connect()
    
    def _init_db_schema(self) -> None:
        """Inicjalizuje schemat bazy danych."""
        try:
            # Wczytanie pliku schematu
            schema_path = os.path.join(os.path.dirname(__file__), 'db_schema.sql')
            with open(schema_path, 'r') as file:
                schema_sql = file.read()
            
            # Wykonanie SQL
            self._reconnect_if_needed()
            self.cursor.execute(schema_sql)
            self.conn.commit()
            logger.info("Zainicjalizowano schemat bazy danych")
        except Exception as e:
            logger.error(f"Błąd podczas inicjalizacji schematu bazy danych: {e}")
            if self.conn:
                self.conn.rollback()
            raise
    
    def save_position(self, position_data: Dict[str, Any]) -> int:
        """
        Zapisuje nową pozycję w bazie danych.
        
        Args:
            position_data: Dane pozycji do zapisania
            
        Returns:
            ID zapisanej pozycji
        """
        try:
            self._reconnect_if_needed()
            
            # Konwersja typów danych
            if 'open_time' in position_data and isinstance(position_data['open_time'], str):
                position_data['open_time'] = datetime.strptime(position_data['open_time'], "%Y.%m.%d %H:%M")
            
            if 'close_time' in position_data and position_data['close_time'] and isinstance(position_data['close_time'], str):
                position_data['close_time'] = datetime.strptime(position_data['close_time'], "%Y.%m.%d %H:%M")
            
            # Przygotowanie danych do zapytania
            query = sql.SQL("""
                INSERT INTO positions (
                    ea_id, ticket, symbol, position_type, volume, 
                    open_price, current_price, sl, tp, profit, 
                    open_time, close_price, close_time, status, 
                    sync_status, error_message
                ) VALUES (
                    %(ea_id)s, %(ticket)s, %(symbol)s, %(type)s, %(volume)s, 
                    %(open_price)s, %(current_price)s, %(sl)s, %(tp)s, %(profit)s, 
                    %(open_time)s, %(close_price)s, %(close_time)s, %(status)s, 
                    %(sync_status)s, %(error_message)s
                ) 
                RETURNING id
            """)
            
            self.cursor.execute(query, {
                'ea_id': position_data.get('ea_id'),
                'ticket': position_data.get('ticket'),
                'symbol': position_data.get('symbol'),
                'type': position_data.get('type'),
                'volume': position_data.get('volume'),
                'open_price': position_data.get('open_price'),
                'current_price': position_data.get('current_price'),
                'sl': position_data.get('sl', 0.0),
                'tp': position_data.get('tp', 0.0),
                'profit': position_data.get('profit', 0.0),
                'open_time': position_data.get('open_time'),
                'close_price': position_data.get('close_price'),
                'close_time': position_data.get('close_time'),
                'status': position_data.get('status', 'OPEN'),
                'sync_status': position_data.get('sync_status', True),
                'error_message': position_data.get('error_message')
            })
            
            result = self.cursor.fetchone()
            self.conn.commit()
            
            logger.info(f"Zapisano pozycję {position_data.get('ticket')} w bazie danych")
            return result['id']
        except Exception as e:
            logger.error(f"Błąd podczas zapisywania pozycji w bazie danych: {e}")
            if self.conn:
                self.conn.rollback()
            raise
    
    def update_position(self, position_data: Dict[str, Any]) -> bool:
        """
        Aktualizuje istniejącą pozycję w bazie danych.
        
        Args:
            position_data: Dane pozycji do aktualizacji
            
        Returns:
            True jeśli aktualizacja się powiodła, False w przeciwnym razie
        """
        try:
            self._reconnect_if_needed()
            
            # Konwersja typów danych
            if 'open_time' in position_data and isinstance(position_data['open_time'], str):
                position_data['open_time'] = datetime.strptime(position_data['open_time'], "%Y.%m.%d %H:%M")
            
            if 'close_time' in position_data and position_data['close_time'] and isinstance(position_data['close_time'], str):
                position_data['close_time'] = datetime.strptime(position_data['close_time'], "%Y.%m.%d %H:%M")
            
            # Przygotowanie danych do zapytania
            query = sql.SQL("""
                UPDATE positions
                SET 
                    current_price = %(current_price)s,
                    sl = %(sl)s,
                    tp = %(tp)s,
                    profit = %(profit)s,
                    status = %(status)s,
                    close_price = %(close_price)s,
                    close_time = %(close_time)s,
                    sync_status = %(sync_status)s,
                    error_message = %(error_message)s
                WHERE
                    ea_id = %(ea_id)s AND ticket = %(ticket)s
                RETURNING id
            """)
            
            self.cursor.execute(query, {
                'ea_id': position_data.get('ea_id'),
                'ticket': position_data.get('ticket'),
                'current_price': position_data.get('current_price'),
                'sl': position_data.get('sl', 0.0),
                'tp': position_data.get('tp', 0.0),
                'profit': position_data.get('profit', 0.0),
                'status': position_data.get('status', 'OPEN'),
                'close_price': position_data.get('close_price'),
                'close_time': position_data.get('close_time'),
                'sync_status': position_data.get('sync_status', True),
                'error_message': position_data.get('error_message')
            })
            
            result = self.cursor.fetchone()
            self.conn.commit()
            
            if result:
                logger.info(f"Zaktualizowano pozycję {position_data.get('ticket')} w bazie danych")
                return True
            else:
                logger.warning(f"Nie znaleziono pozycji {position_data.get('ticket')} do aktualizacji")
                return False
        except Exception as e:
            logger.error(f"Błąd podczas aktualizacji pozycji w bazie danych: {e}")
            if self.conn:
                self.conn.rollback()
            return False
    
    def get_position(self, ea_id: str, ticket: int) -> Optional[Dict[str, Any]]:
        """
        Pobiera pozycję z bazy danych.
        
        Args:
            ea_id: Identyfikator EA
            ticket: Numer ticketu pozycji
            
        Returns:
            Dane pozycji jako słownik lub None, jeśli pozycja nie istnieje
        """
        try:
            self._reconnect_if_needed()
            
            query = sql.SQL("""
                SELECT * FROM positions
                WHERE ea_id = %(ea_id)s AND ticket = %(ticket)s
                LIMIT 1
            """)
            
            self.cursor.execute(query, {'ea_id': ea_id, 'ticket': ticket})
            result = self.cursor.fetchone()
            
            if result:
                # Konwersja RealDictRow na zwykły słownik
                return dict(result)
            else:
                return None
        except Exception as e:
            logger.error(f"Błąd podczas pobierania pozycji z bazy danych: {e}")
            return None
    
    def get_all_positions(self) -> List[Dict[str, Any]]:
        """
        Pobiera wszystkie pozycje z bazy danych.
        
        Returns:
            Lista pozycji jako słowniki
        """
        try:
            self._reconnect_if_needed()
            
            query = sql.SQL("""
                SELECT * FROM positions
                ORDER BY open_time DESC
            """)
            
            self.cursor.execute(query)
            results = self.cursor.fetchall()
            
            # Konwersja RealDictRow na zwykłe słowniki
            return [dict(row) for row in results]
        except Exception as e:
            logger.error(f"Błąd podczas pobierania wszystkich pozycji z bazy danych: {e}")
            return []
    
    def get_active_positions(self, ea_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Pobiera aktywne pozycje z bazy danych.
        
        Args:
            ea_id: Opcjonalny identyfikator EA do filtrowania
            
        Returns:
            Lista aktywnych pozycji jako słowniki
        """
        try:
            self._reconnect_if_needed()
            
            if ea_id:
                query = sql.SQL("""
                    SELECT * FROM positions
                    WHERE status = 'OPEN' AND ea_id = %(ea_id)s
                    ORDER BY open_time DESC
                """)
                params = {'ea_id': ea_id}
            else:
                query = sql.SQL("""
                    SELECT * FROM positions
                    WHERE status = 'OPEN'
                    ORDER BY open_time DESC
                """)
                params = {}
            
            self.cursor.execute(query, params)
            results = self.cursor.fetchall()
            
            # Konwersja RealDictRow na zwykłe słowniki
            return [dict(row) for row in results]
        except Exception as e:
            logger.error(f"Błąd podczas pobierania aktywnych pozycji z bazy danych: {e}")
            return []
    
    def get_position_history(self, days: int = 30, ea_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Pobiera historię zamkniętych pozycji z określonego okresu.
        
        Args:
            days: Liczba dni wstecz (domyślnie 30)
            ea_id: Opcjonalny identyfikator EA do filtrowania
            
        Returns:
            Lista zamkniętych pozycji jako słowniki
        """
        try:
            self._reconnect_if_needed()
            
            cutoff_date = datetime.now() - timedelta(days=days)
            
            if ea_id:
                query = sql.SQL("""
                    SELECT * FROM positions
                    WHERE status = 'CLOSED' 
                      AND close_time >= %(cutoff_date)s
                      AND ea_id = %(ea_id)s
                    ORDER BY close_time DESC
                """)
                params = {'cutoff_date': cutoff_date, 'ea_id': ea_id}
            else:
                query = sql.SQL("""
                    SELECT * FROM positions
                    WHERE status = 'CLOSED' 
                      AND close_time >= %(cutoff_date)s
                    ORDER BY close_time DESC
                """)
                params = {'cutoff_date': cutoff_date}
            
            self.cursor.execute(query, params)
            results = self.cursor.fetchall()
            
            # Konwersja RealDictRow na zwykłe słowniki
            return [dict(row) for row in results]
        except Exception as e:
            logger.error(f"Błąd podczas pobierania historii pozycji z bazy danych: {e}")
            return []
    
    def get_position_modifications(self, position_id: int) -> List[Dict[str, Any]]:
        """
        Pobiera historię modyfikacji dla danej pozycji.
        
        Args:
            position_id: ID pozycji
            
        Returns:
            Lista modyfikacji jako słowniki
        """
        try:
            self._reconnect_if_needed()
            
            query = sql.SQL("""
                SELECT * FROM position_history
                WHERE position_id = %(position_id)s
                ORDER BY timestamp DESC
            """)
            
            self.cursor.execute(query, {'position_id': position_id})
            results = self.cursor.fetchall()
            
            # Konwersja RealDictRow na zwykłe słowniki
            return [dict(row) for row in results]
        except Exception as e:
            logger.error(f"Błąd podczas pobierania historii modyfikacji pozycji z bazy danych: {e}")
            return []
    
    def delete_position(self, ea_id: str, ticket: int) -> bool:
        """
        Usuwa pozycję z bazy danych.
        
        Args:
            ea_id: Identyfikator EA
            ticket: Numer ticketu pozycji
            
        Returns:
            True jeśli usunięcie się powiodło, False w przeciwnym razie
        """
        try:
            self._reconnect_if_needed()
            
            query = sql.SQL("""
                DELETE FROM positions
                WHERE ea_id = %(ea_id)s AND ticket = %(ticket)s
                RETURNING id
            """)
            
            self.cursor.execute(query, {'ea_id': ea_id, 'ticket': ticket})
            result = self.cursor.fetchone()
            self.conn.commit()
            
            if result:
                logger.info(f"Usunięto pozycję {ticket} z bazy danych")
                return True
            else:
                logger.warning(f"Nie znaleziono pozycji {ticket} do usunięcia")
                return False
        except Exception as e:
            logger.error(f"Błąd podczas usuwania pozycji z bazy danych: {e}")
            if self.conn:
                self.conn.rollback()
            return False
    
    def get_stats(self, ea_id: Optional[str] = None, days: int = 30) -> Dict[str, Any]:
        """
        Pobiera statystyki handlowe z określonego okresu.
        
        Args:
            ea_id: Opcjonalny identyfikator EA do filtrowania
            days: Liczba dni wstecz (domyślnie 30)
            
        Returns:
            Statystyki handlowe jako słownik
        """
        try:
            self._reconnect_if_needed()
            
            cutoff_date = datetime.now() - timedelta(days=days)
            
            if ea_id:
                # Statystyki dla konkretnego EA
                query = sql.SQL("""
                    SELECT
                        COUNT(*) FILTER (WHERE status = 'CLOSED' AND profit > 0) as profitable_trades,
                        COUNT(*) FILTER (WHERE status = 'CLOSED' AND profit <= 0) as losing_trades,
                        SUM(profit) FILTER (WHERE status = 'CLOSED' AND profit > 0) as total_profit,
                        SUM(ABS(profit)) FILTER (WHERE status = 'CLOSED' AND profit <= 0) as total_loss,
                        AVG(profit) FILTER (WHERE status = 'CLOSED' AND profit > 0) as avg_profit,
                        AVG(ABS(profit)) FILTER (WHERE status = 'CLOSED' AND profit <= 0) as avg_loss,
                        COUNT(*) FILTER (WHERE status = 'OPEN') as open_positions,
                        SUM(profit) FILTER (WHERE status = 'OPEN') as open_positions_profit
                    FROM positions
                    WHERE (status = 'CLOSED' AND close_time >= %(cutoff_date)s)
                       OR status = 'OPEN'
                       AND ea_id = %(ea_id)s
                """)
                params = {'cutoff_date': cutoff_date, 'ea_id': ea_id}
            else:
                # Statystyki dla wszystkich EA
                query = sql.SQL("""
                    SELECT
                        COUNT(*) FILTER (WHERE status = 'CLOSED' AND profit > 0) as profitable_trades,
                        COUNT(*) FILTER (WHERE status = 'CLOSED' AND profit <= 0) as losing_trades,
                        SUM(profit) FILTER (WHERE status = 'CLOSED' AND profit > 0) as total_profit,
                        SUM(ABS(profit)) FILTER (WHERE status = 'CLOSED' AND profit <= 0) as total_loss,
                        AVG(profit) FILTER (WHERE status = 'CLOSED' AND profit > 0) as avg_profit,
                        AVG(ABS(profit)) FILTER (WHERE status = 'CLOSED' AND profit <= 0) as avg_loss,
                        COUNT(*) FILTER (WHERE status = 'OPEN') as open_positions,
                        SUM(profit) FILTER (WHERE status = 'OPEN') as open_positions_profit
                    FROM positions
                    WHERE (status = 'CLOSED' AND close_time >= %(cutoff_date)s)
                       OR status = 'OPEN'
                """)
                params = {'cutoff_date': cutoff_date}
            
            self.cursor.execute(query, params)
            result = self.cursor.fetchone()
            
            if result:
                stats = dict(result)
                
                # Obliczenie dodatkowych statystyk
                total_trades = (stats['profitable_trades'] or 0) + (stats['losing_trades'] or 0)
                if total_trades > 0:
                    stats['win_rate'] = round((stats['profitable_trades'] or 0) / total_trades * 100, 2)
                else:
                    stats['win_rate'] = 0
                
                stats['net_profit'] = (stats['total_profit'] or 0) - (stats['total_loss'] or 0)
                
                if stats['total_loss'] and stats['total_profit']:
                    stats['profit_factor'] = round(stats['total_profit'] / stats['total_loss'], 2) if stats['total_loss'] > 0 else float('inf')
                else:
                    stats['profit_factor'] = 0
                
                return stats
            else:
                return {
                    'profitable_trades': 0,
                    'losing_trades': 0,
                    'total_profit': 0,
                    'total_loss': 0,
                    'avg_profit': 0,
                    'avg_loss': 0,
                    'open_positions': 0,
                    'open_positions_profit': 0,
                    'win_rate': 0,
                    'net_profit': 0,
                    'profit_factor': 0
                }
        except Exception as e:
            logger.error(f"Błąd podczas pobierania statystyk z bazy danych: {e}")
            return {
                'profitable_trades': 0,
                'losing_trades': 0,
                'total_profit': 0,
                'total_loss': 0,
                'avg_profit': 0,
                'avg_loss': 0,
                'open_positions': 0,
                'open_positions_profit': 0,
                'win_rate': 0,
                'net_profit': 0,
                'profit_factor': 0,
                'error': str(e)
            }
    
    def close(self) -> None:
        """Zamyka połączenie z bazą danych."""
        self._disconnect()
    
    def __del__(self) -> None:
        """Destruktor - zamyka połączenie z bazą danych."""
        try:
            self.close()
        except:
            pass 