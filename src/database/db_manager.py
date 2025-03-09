#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Moduł zarządzający połączeniem z bazą danych PostgreSQL.
"""

import os
import logging
import psycopg2
from psycopg2.pool import ThreadedConnectionPool
from psycopg2.extras import DictCursor
from contextlib import contextmanager
from dotenv import load_dotenv

# Ustawienie loggera
logger = logging.getLogger('trading_agent.database')

class DatabaseManager:
    """Klasa zarządzająca połączeniem z bazą danych PostgreSQL."""
    
    _instance = None
    
    def __new__(cls):
        """Implementacja wzorca Singleton."""
        if cls._instance is None:
            cls._instance = super(DatabaseManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """Inicjalizacja menedżera bazy danych."""
        if self._initialized:
            return
        
        # Wczytanie zmiennych środowiskowych
        load_dotenv()
        
        # Parametry połączenia
        self._host = os.getenv('DB_HOST', 'localhost')
        self._port = os.getenv('DB_PORT', '5432')
        self._dbname = os.getenv('DB_NAME', 'mt5remotetest')
        self._user = os.getenv('DB_USER', 'mt5remote')
        self._password = os.getenv('DB_PASSWORD', 'mt5remote')
        
        # Dodatkowe parametry
        self._pool_min_size = int(os.getenv('DB_POOL_MIN_SIZE', '5'))
        self._pool_max_size = int(os.getenv('DB_POOL_MAX_SIZE', '20'))
        self._command_timeout = int(os.getenv('DB_COMMAND_TIMEOUT', '60'))
        self._connect_timeout = int(os.getenv('DB_CONNECT_TIMEOUT', '30'))
        self._max_retries = int(os.getenv('DB_MAX_RETRIES', '3'))
        self._retry_interval = int(os.getenv('DB_RETRY_INTERVAL', '5'))
        
        # Pula połączeń
        self._pool = None
        self._initialized = True
        
        logger.info(f"Menedżer bazy danych zainicjalizowany dla {self._dbname} na {self._host}:{self._port}")
    
    def connect(self):
        """Nawiązanie połączenia z bazą danych."""
        if self._pool is not None:
            return
        
        conn_string = f"host={self._host} port={self._port} dbname={self._dbname} user={self._user} password={self._password}"
        
        try:
            self._pool = ThreadedConnectionPool(
                self._pool_min_size,
                self._pool_max_size,
                conn_string,
                cursor_factory=DictCursor
            )
            logger.info(f"Połączono z bazą danych {self._dbname}")
        except psycopg2.Error as e:
            logger.error(f"Błąd podczas łączenia z bazą danych: {e}")
            raise
    
    def close(self):
        """Zamknięcie połączenia z bazą danych."""
        if self._pool is not None:
            self._pool.closeall()
            self._pool = None
            logger.info("Połączenie z bazą danych zostało zamknięte")
    
    @contextmanager
    def get_connection(self):
        """
        Kontekstowy menedżer do uzyskiwania i zwalniania połączenia z puli.
        
        Yields:
            psycopg2.extensions.connection: Połączenie z bazą danych.
        """
        if self._pool is None:
            self.connect()
        
        conn = None
        try:
            conn = self._pool.getconn()
            yield conn
        finally:
            if conn:
                self._pool.putconn(conn)
    
    @contextmanager
    def get_cursor(self, commit=False):
        """
        Kontekstowy menedżer do uzyskiwania kursora dla pojedynczej operacji.
        
        Args:
            commit (bool, optional): Czy automatycznie wykonać commit po operacji. Domyślnie False.
        
        Yields:
            psycopg2.extras.DictCursor: Kursor bazy danych.
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            try:
                yield cursor
                if commit:
                    conn.commit()
            except Exception as e:
                conn.rollback()
                logger.error(f"Błąd podczas operacji na bazie danych: {e}")
                raise
            finally:
                cursor.close()
    
    def execute_query(self, query, params=None, fetch=True, commit=True):
        """
        Wykonanie zapytania SQL.
        
        Args:
            query (str): Zapytanie SQL do wykonania.
            params (tuple or dict, optional): Parametry do zapytania. Domyślnie None.
            fetch (bool, optional): Czy pobierać wyniki. Domyślnie True.
            commit (bool, optional): Czy wykonać commit po operacji. Domyślnie True.
        
        Returns:
            list: Lista wyników (jeśli fetch=True), w przeciwnym razie None.
        """
        with self.get_cursor(commit=commit) as cursor:
            cursor.execute(query, params)
            
            if fetch:
                return cursor.fetchall()
            return None
    
    def create_tables(self):
        """Utworzenie wszystkich tabel w bazie danych."""
        self._create_setup_tables()
        self._create_transaction_tables()
        self._create_log_tables()
        logger.info("Wszystkie tabele zostały utworzone")
    
    def _create_setup_tables(self):
        """Utworzenie tabel dla setupów handlowych."""
        with self.get_cursor(commit=True) as cursor:
            # Tabela z instrumentami
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS instruments (
                    id SERIAL PRIMARY KEY,
                    symbol VARCHAR(20) NOT NULL UNIQUE,
                    description TEXT,
                    pip_value NUMERIC(10, 6),
                    min_lot NUMERIC(10, 2),
                    max_lot NUMERIC(10, 2),
                    lot_step NUMERIC(10, 2),
                    active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            ''')
            
            # Tabela z setupami
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS trading_setups (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(50) NOT NULL,
                    description TEXT,
                    symbol VARCHAR(20) NOT NULL REFERENCES instruments(symbol),
                    timeframe VARCHAR(10) NOT NULL,
                    setup_type VARCHAR(20) NOT NULL,
                    direction VARCHAR(10) NOT NULL,
                    entry_conditions TEXT NOT NULL,
                    exit_conditions TEXT,
                    risk_reward_ratio NUMERIC(5, 2),
                    success_rate NUMERIC(5, 2),
                    active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            ''')
            
            # Tabela z sygnałami
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS trading_signals (
                    id SERIAL PRIMARY KEY,
                    setup_id INTEGER REFERENCES trading_setups(id),
                    symbol VARCHAR(20) NOT NULL,
                    timeframe VARCHAR(10) NOT NULL,
                    direction VARCHAR(10) NOT NULL,
                    entry_price NUMERIC(10, 5),
                    stop_loss NUMERIC(10, 5),
                    take_profit NUMERIC(10, 5),
                    confidence NUMERIC(5, 2),
                    status VARCHAR(20) DEFAULT 'pending',
                    ai_analysis TEXT,
                    execution_id INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expired_at TIMESTAMP
                );
            ''')
        logger.info("Tabele dla setupów zostały utworzone")
    
    def _create_transaction_tables(self):
        """Utworzenie tabel dla transakcji."""
        with self.get_cursor(commit=True) as cursor:
            # Tabela z transakcjami
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS transactions (
                    id SERIAL PRIMARY KEY,
                    mt5_order_id BIGINT UNIQUE,
                    signal_id INTEGER REFERENCES trading_signals(id),
                    symbol VARCHAR(20) NOT NULL,
                    order_type VARCHAR(20) NOT NULL,
                    volume NUMERIC(10, 2) NOT NULL,
                    open_price NUMERIC(10, 5),
                    close_price NUMERIC(10, 5),
                    stop_loss NUMERIC(10, 5),
                    take_profit NUMERIC(10, 5),
                    open_time TIMESTAMP,
                    close_time TIMESTAMP,
                    profit NUMERIC(10, 2),
                    commission NUMERIC(10, 2),
                    swap NUMERIC(10, 2),
                    status VARCHAR(20) NOT NULL,
                    comment TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            ''')
            
            # Tabela z modyfikacjami zleceń
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS order_modifications (
                    id SERIAL PRIMARY KEY,
                    transaction_id INTEGER REFERENCES transactions(id),
                    modification_type VARCHAR(20) NOT NULL,
                    old_value NUMERIC(10, 5),
                    new_value NUMERIC(10, 5),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    executed_at TIMESTAMP,
                    status VARCHAR(20) NOT NULL,
                    comment TEXT
                );
            ''')
            
            # Tabela z rachunkami
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS account_snapshots (
                    id SERIAL PRIMARY KEY,
                    balance NUMERIC(15, 2) NOT NULL,
                    equity NUMERIC(15, 2) NOT NULL,
                    margin NUMERIC(15, 2) NOT NULL,
                    free_margin NUMERIC(15, 2) NOT NULL,
                    margin_level NUMERIC(10, 2),
                    open_positions INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            ''')
        logger.info("Tabele dla transakcji zostały utworzone")
    
    def _create_log_tables(self):
        """Utworzenie tabel dla logów i monitoringu."""
        with self.get_cursor(commit=True) as cursor:
            # Tabela z logami systemu
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS system_logs (
                    id SERIAL PRIMARY KEY,
                    log_level VARCHAR(10) NOT NULL,
                    message TEXT NOT NULL,
                    component VARCHAR(50),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            ''')
            
            # Tabela ze statystykami AI
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS ai_stats (
                    id SERIAL PRIMARY KEY,
                    model VARCHAR(20) NOT NULL,
                    query_type VARCHAR(50) NOT NULL,
                    response_time NUMERIC(10, 3),
                    tokens_used INTEGER,
                    cost NUMERIC(10, 6),
                    success BOOLEAN,
                    error_message TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            ''')
            
            # Tabela z metrykami wydajności
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS performance_metrics (
                    id SERIAL PRIMARY KEY,
                    metric_name VARCHAR(50) NOT NULL,
                    metric_value NUMERIC(15, 6) NOT NULL,
                    metric_unit VARCHAR(20),
                    period_start TIMESTAMP,
                    period_end TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            ''')
        logger.info("Tabele dla logów i monitoringu zostały utworzone")


# Przykład użycia:
if __name__ == "__main__":
    # Konfiguracja logowania
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # Przykład tworzenia tabel
    db = DatabaseManager()
    db.create_tables()
    
    # Przykład zapytania
    try:
        result = db.execute_query("SELECT version();")
        print(f"PostgreSQL version: {result[0][0]}")
    finally:
        db.close() 