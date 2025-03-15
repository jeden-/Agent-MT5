#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Repozytorium do przechowywania danych o użyciu modeli AI.

Ten moduł jest odpowiedzialny za:
- Zapisywanie informacji o użyciu modeli AI
- Pobieranie statystyk użycia
- Analizę kosztów i wydajności
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple

# Importy wewnętrzne
try:
    from src.database.db_manager import DatabaseManager, get_db_manager
except ImportError:
    try:
        from database.db_manager import DatabaseManager, get_db_manager
    except ImportError:
        # Dla testów jednostkowych
        pass


class AIUsageRepository:
    """Repozytorium do przechowywania danych o użyciu modeli AI."""
    
    _instance = None
    
    def __new__(cls):
        """Implementacja wzorca Singleton."""
        if cls._instance is None:
            cls._instance = super(AIUsageRepository, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """Inicjalizacja repozytorium."""
        if self._initialized:
            return
            
        self.logger = logging.getLogger('trading_agent.database.ai_usage')
        self.logger.info("Inicjalizacja AIUsageRepository")
        
        # Inicjalizacja menedżera bazy danych
        self.db_manager = get_db_manager()
        
        # Utworzenie tabeli, jeśli nie istnieje
        self._create_tables()
        
        self._initialized = True
    
    def _create_tables(self) -> None:
        """Tworzy tabele w bazie danych, jeśli nie istnieją."""
        create_table_query = """
        CREATE TABLE IF NOT EXISTS ai_usage (
            id SERIAL PRIMARY KEY,
            model_name VARCHAR(50) NOT NULL,
            timestamp TIMESTAMP NOT NULL,
            request_type VARCHAR(50) NOT NULL,
            tokens_input INTEGER NOT NULL,
            tokens_output INTEGER NOT NULL,
            duration_ms INTEGER NOT NULL,
            success BOOLEAN NOT NULL,
            error_message TEXT,
            cost FLOAT NOT NULL,
            signal_generated BOOLEAN NOT NULL,
            decision_quality FLOAT
        );
        
        CREATE INDEX IF NOT EXISTS idx_ai_usage_model_name ON ai_usage(model_name);
        CREATE INDEX IF NOT EXISTS idx_ai_usage_timestamp ON ai_usage(timestamp);
        """
        
        try:
            self.db_manager.execute_query(create_table_query)
            self.logger.info("Tabela ai_usage została utworzona lub już istnieje")
        except Exception as e:
            self.logger.error(f"Błąd podczas tworzenia tabeli ai_usage: {e}")
            raise
    
    def insert_usage(self, usage_data: Dict[str, Any]) -> int:
        """
        Zapisuje informacje o użyciu modelu AI.
        
        Args:
            usage_data: Słownik z danymi o użyciu
            
        Returns:
            int: ID zapisanego rekordu
        """
        insert_query = """
        INSERT INTO ai_usage (
            model_name, timestamp, request_type, tokens_input, tokens_output,
            duration_ms, success, error_message, cost, signal_generated, decision_quality
        ) VALUES (
            %(model_name)s, %(timestamp)s, %(request_type)s, %(tokens_input)s, %(tokens_output)s,
            %(duration_ms)s, %(success)s, %(error_message)s, %(cost)s, %(signal_generated)s, %(decision_quality)s
        ) RETURNING id;
        """
        
        # Konwersja timestamp z ISO format do datetime
        if isinstance(usage_data.get('timestamp'), str):
            usage_data['timestamp'] = datetime.fromisoformat(usage_data['timestamp'])
        
        try:
            result = self.db_manager.execute_query(insert_query, usage_data)
            record_id = result[0][0] if result else None
            self.logger.debug(f"Zapisano użycie AI, ID: {record_id}")
            return record_id
        except Exception as e:
            self.logger.error(f"Błąd podczas zapisywania użycia AI: {e}")
            raise
    
    def get_usage_in_timeframe(self, start_time: datetime, end_time: datetime) -> List[Dict[str, Any]]:
        """
        Pobiera dane o użyciu modeli AI w określonym przedziale czasowym.
        
        Args:
            start_time: Początek przedziału czasowego
            end_time: Koniec przedziału czasowego
            
        Returns:
            List[Dict]: Lista słowników z danymi o użyciu
        """
        query = """
        SELECT * FROM ai_usage
        WHERE timestamp BETWEEN %s AND %s
        ORDER BY timestamp DESC;
        """
        
        try:
            results = self.db_manager.execute_query(query, (start_time, end_time))
            
            # Konwersja wyników do słowników
            columns = [
                'id', 'model_name', 'timestamp', 'request_type', 'tokens_input',
                'tokens_output', 'duration_ms', 'success', 'error_message',
                'cost', 'signal_generated', 'decision_quality'
            ]
            
            return [dict(zip(columns, row)) for row in results]
        except Exception as e:
            self.logger.error(f"Błąd podczas pobierania danych o użyciu AI: {e}")
            return []
    
    def get_daily_cost(self, model_name: str, day: datetime) -> float:
        """
        Pobiera łączny koszt użycia modelu AI w danym dniu.
        
        Args:
            model_name: Nazwa modelu
            day: Data (początek dnia)
            
        Returns:
            float: Łączny koszt w USD
        """
        next_day = day + timedelta(days=1)
        
        query = """
        SELECT SUM(cost) FROM ai_usage
        WHERE model_name = %s AND timestamp BETWEEN %s AND %s;
        """
        
        try:
            result = self.db_manager.execute_query(query, (model_name, day, next_day))
            total_cost = result[0][0] if result and result[0][0] is not None else 0.0
            return float(total_cost)
        except Exception as e:
            self.logger.error(f"Błąd podczas pobierania kosztu dziennego: {e}")
            return 0.0
    
    def get_model_performance(self, model_name: str, days: int = 7) -> Dict[str, Any]:
        """
        Pobiera statystyki wydajności modelu AI z ostatnich dni.
        
        Args:
            model_name: Nazwa modelu
            days: Liczba dni do analizy
            
        Returns:
            Dict: Słownik ze statystykami wydajności
        """
        end_time = datetime.now()
        start_time = end_time - timedelta(days=days)
        
        query = """
        SELECT 
            COUNT(*) as total_requests,
            AVG(CASE WHEN success THEN 1 ELSE 0 END) * 100 as success_rate,
            AVG(tokens_input) as avg_tokens_input,
            AVG(tokens_output) as avg_tokens_output,
            AVG(duration_ms) as avg_duration_ms,
            SUM(cost) as total_cost,
            AVG(CASE WHEN signal_generated THEN 1 ELSE 0 END) * 100 as signal_rate,
            AVG(decision_quality) as avg_decision_quality
        FROM ai_usage
        WHERE model_name = %s AND timestamp BETWEEN %s AND %s;
        """
        
        try:
            result = self.db_manager.execute_query(query, (model_name, start_time, end_time))
            
            if not result:
                return {}
                
            columns = [
                'total_requests', 'success_rate', 'avg_tokens_input', 'avg_tokens_output',
                'avg_duration_ms', 'total_cost', 'signal_rate', 'avg_decision_quality'
            ]
            
            stats = dict(zip(columns, result[0]))
            
            # Dodaj informacje o okresie
            stats['start_time'] = start_time.isoformat()
            stats['end_time'] = end_time.isoformat()
            stats['days'] = days
            
            return stats
        except Exception as e:
            self.logger.error(f"Błąd podczas pobierania statystyk wydajności: {e}")
            return {}
    
    def get_daily_usage_stats(self, days: int = 30) -> List[Dict[str, Any]]:
        """
        Pobiera dzienne statystyki użycia wszystkich modeli.
        
        Args:
            days: Liczba dni do analizy
            
        Returns:
            List[Dict]: Lista słowników ze statystykami dziennymi
        """
        end_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        start_date = end_date - timedelta(days=days)
        
        query = """
        SELECT 
            DATE(timestamp) as day,
            model_name,
            COUNT(*) as requests,
            SUM(cost) as daily_cost,
            AVG(CASE WHEN success THEN 1 ELSE 0 END) * 100 as success_rate
        FROM ai_usage
        WHERE timestamp BETWEEN %s AND %s
        GROUP BY DATE(timestamp), model_name
        ORDER BY day DESC, model_name;
        """
        
        try:
            results = self.db_manager.execute_query(query, (start_date, end_date))
            
            columns = ['day', 'model_name', 'requests', 'daily_cost', 'success_rate']
            return [dict(zip(columns, row)) for row in results]
        except Exception as e:
            self.logger.error(f"Błąd podczas pobierania dziennych statystyk: {e}")
            return []


def get_ai_usage_repository() -> AIUsageRepository:
    """
    Zwraca instancję AIUsageRepository (Singleton).
    
    Returns:
        Instancja AIUsageRepository
    """
    return AIUsageRepository() 