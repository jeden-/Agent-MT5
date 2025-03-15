#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Moduł repozytorium konfiguracji agenta.

Odpowiada za zapis i odczyt konfiguracji agenta z bazy danych.
"""

import logging
import json
import threading
from datetime import datetime
from typing import Dict, Any, Optional, List

from src.database.db_manager import DatabaseManager

# Konfiguracja loggera
logger = logging.getLogger('trading_agent.database.agent_config_repository')

class AgentConfigRepository:
    """
    Repozytorium konfiguracji agenta.
    
    Ta klasa zarządza przechowywaniem i odczytem konfiguracji agenta w bazie danych.
    """
    
    _instance = None
    _lock = threading.Lock()
    
    @classmethod
    def get_instance(cls) -> 'AgentConfigRepository':
        """
        Pobiera instancję repozytorium konfiguracji.
        
        Returns:
            AgentConfigRepository: Instancja repozytorium
        """
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance
    
    def __init__(self):
        """Inicjalizacja repozytorium konfiguracji agenta."""
        self.db_manager = DatabaseManager()
        self._ensure_table_exists()
        logger.info("AgentConfigRepository zainicjalizowane")
    
    def _ensure_table_exists(self):
        """Zapewnia, że tabela konfiguracji agenta istnieje w bazie danych."""
        try:
            with self.db_manager.get_connection() as conn:
                with conn.cursor() as cursor:
                    # Sprawdzenie, czy tabela istnieje
                    cursor.execute("""
                        SELECT EXISTS (
                            SELECT FROM information_schema.tables 
                            WHERE table_schema = 'public' 
                            AND table_name = 'agent_config_history'
                        );
                    """)
                    
                    table_exists = cursor.fetchone()[0]
                    
                    if not table_exists:
                        # Tworzenie tabeli, jeśli nie istnieje
                        cursor.execute("""
                            CREATE TABLE agent_config_history (
                                id SERIAL PRIMARY KEY,
                                timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                                mode VARCHAR(32) NOT NULL,
                                config JSONB NOT NULL,
                                comment TEXT,
                                user_id VARCHAR(64) DEFAULT 'system'
                            );
                            
                            -- Indeksy dla wydajności zapytań
                            CREATE INDEX idx_agent_config_history_timestamp ON agent_config_history(timestamp);
                            CREATE INDEX idx_agent_config_history_mode ON agent_config_history(mode);
                        """)
                        conn.commit()
                        logger.info("Utworzono tabelę agent_config_history")
                    else:
                        logger.info("Tabela agent_config_history już istnieje")
        
        except Exception as e:
            logger.error(f"Błąd podczas inicjalizacji tabeli konfiguracji agenta: {e}")
    
    def save_config(self, mode: str, config: Dict[str, Any], comment: Optional[str] = None, user_id: str = "system") -> bool:
        """
        Zapisuje konfigurację agenta do bazy danych.
        
        Args:
            mode: Tryb pracy agenta
            config: Konfiguracja agenta
            comment: Opcjonalny komentarz
            user_id: Identyfikator użytkownika
            
        Returns:
            bool: True jeśli zapisano pomyślnie
        """
        try:
            with self.db_manager.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        INSERT INTO agent_config_history (mode, config, comment, user_id)
                        VALUES (%s, %s, %s, %s)
                        RETURNING id;
                    """, (mode, json.dumps(config), comment, user_id))
                    
                    config_id = cursor.fetchone()[0]
                    conn.commit()
                    
                    logger.info(f"Zapisano konfigurację agenta (ID: {config_id}, tryb: {mode})")
                    return True
        
        except Exception as e:
            logger.error(f"Błąd podczas zapisywania konfiguracji agenta: {e}")
            return False
    
    def get_latest_config(self) -> Optional[Dict[str, Any]]:
        """
        Pobiera najnowszą konfigurację agenta z bazy danych.
        
        Returns:
            Dict[str, Any] or None: Najnowsza konfiguracja agenta lub None w przypadku błędu
        """
        try:
            with self.db_manager.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        SELECT id, timestamp, mode, config, comment, user_id
                        FROM agent_config_history
                        ORDER BY timestamp DESC
                        LIMIT 1;
                    """)
                    
                    result = cursor.fetchone()
                    
                    if result:
                        config_id, timestamp, mode, config_json, comment, user_id = result
                        
                        logger.info(f"Pobrano najnowszą konfigurację agenta (ID: {config_id}, tryb: {mode})")
                        
                        return {
                            "id": config_id,
                            "timestamp": timestamp.isoformat(),
                            "mode": mode,
                            "config": json.loads(config_json),
                            "comment": comment,
                            "user_id": user_id
                        }
                    else:
                        logger.info("Brak zapisanej konfiguracji agenta w bazie danych")
                        return None
        
        except Exception as e:
            logger.error(f"Błąd podczas pobierania najnowszej konfiguracji agenta: {e}")
            return None
    
    def get_config_history(self, limit: int = 10, offset: int = 0) -> List[Dict[str, Any]]:
        """
        Pobiera historię konfiguracji agenta z bazy danych.
        
        Args:
            limit: Maksymalna liczba rekordów do pobrania
            offset: Przesunięcie względem początku
            
        Returns:
            List[Dict[str, Any]]: Lista konfiguracji agenta
        """
        try:
            with self.db_manager.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        SELECT id, timestamp, mode, config, comment, user_id
                        FROM agent_config_history
                        ORDER BY timestamp DESC
                        LIMIT %s OFFSET %s;
                    """, (limit, offset))
                    
                    results = cursor.fetchall()
                    
                    history = []
                    for result in results:
                        config_id, timestamp, mode, config_json, comment, user_id = result
                        
                        history.append({
                            "id": config_id,
                            "timestamp": timestamp.isoformat(),
                            "mode": mode,
                            "config": json.loads(config_json),
                            "comment": comment,
                            "user_id": user_id
                        })
                    
                    logger.info(f"Pobrano {len(history)} rekordów historii konfiguracji agenta")
                    return history
        
        except Exception as e:
            logger.error(f"Błąd podczas pobierania historii konfiguracji agenta: {e}")
            return []
    
    def get_config_by_id(self, config_id: int) -> Optional[Dict[str, Any]]:
        """
        Pobiera konfigurację agenta o podanym ID.
        
        Args:
            config_id: ID konfiguracji
            
        Returns:
            Dict[str, Any] or None: Konfiguracja agenta lub None w przypadku błędu
        """
        try:
            with self.db_manager.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        SELECT id, timestamp, mode, config, comment, user_id
                        FROM agent_config_history
                        WHERE id = %s;
                    """, (config_id,))
                    
                    result = cursor.fetchone()
                    
                    if result:
                        config_id, timestamp, mode, config_json, comment, user_id = result
                        
                        logger.info(f"Pobrano konfigurację agenta (ID: {config_id}, tryb: {mode})")
                        
                        return {
                            "id": config_id,
                            "timestamp": timestamp.isoformat(),
                            "mode": mode,
                            "config": json.loads(config_json),
                            "comment": comment,
                            "user_id": user_id
                        }
                    else:
                        logger.warning(f"Nie znaleziono konfiguracji agenta o ID {config_id}")
                        return None
        
        except Exception as e:
            logger.error(f"Błąd podczas pobierania konfiguracji agenta o ID {config_id}: {e}")
            return None

# Funkcja pomocnicza do uzyskania instancji repozytorium
def get_agent_config_repository() -> AgentConfigRepository:
    """
    Funkcja pomocnicza do uzyskania instancji repozytorium konfiguracji agenta.
    
    Returns:
        AgentConfigRepository: Instancja repozytorium
    """
    return AgentConfigRepository.get_instance() 