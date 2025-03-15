#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Repozytorium ocen sygnałów handlowych.
"""

import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from src.database.models import SignalEvaluation
from src.database.db_manager import get_db_manager

logger = logging.getLogger(__name__)

class SignalEvaluationRepository:
    """Repozytorium ocen sygnałów handlowych."""
    
    _instance = None
    
    @classmethod
    def get_instance(cls):
        """Zwraca instancję repozytorium (singleton)."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def __init__(self):
        """Inicjalizacja repozytorium."""
        self.db_manager = get_db_manager()
        self.evaluations_cache = {}
        self.next_id = 1
    
    def create(self, evaluation: SignalEvaluation) -> Optional[SignalEvaluation]:
        """Dodaje nową ocenę sygnału do bazy danych."""
        try:
            # W pełnej implementacji tutaj byłby kod zapisujący do bazy SQL
            # W tej uproszczonej wersji używamy pamięci cache
            
            # Przypisanie ID jeśli nie zostało podane
            if not hasattr(evaluation, 'id') or evaluation.id is None:
                evaluation.id = self.next_id
                self.next_id += 1
            
            # Dodanie timestampu jeśli nie ma
            if not hasattr(evaluation, 'created_at') or evaluation.created_at is None:
                evaluation.created_at = datetime.now()
                
            # Zapisanie do cache'a
            self.evaluations_cache[evaluation.id] = evaluation
            logger.info(f"Ocena sygnału {evaluation.id} dla {evaluation.symbol} zapisana do bazy danych")
            
            return evaluation
        except Exception as e:
            logger.error(f"Błąd podczas zapisywania oceny sygnału: {e}")
            return None
    
    def get_evaluation_by_id(self, evaluation_id: int) -> Optional[SignalEvaluation]:
        """Pobiera ocenę sygnału o podanym ID."""
        try:
            return self.evaluations_cache.get(evaluation_id)
        except Exception as e:
            logger.error(f"Błąd podczas pobierania oceny sygnału {evaluation_id}: {e}")
            return None
    
    def get_evaluations_by_signal_id(self, signal_id: str) -> List[SignalEvaluation]:
        """Pobiera oceny dla danego sygnału."""
        try:
            evaluations = [e for e in self.evaluations_cache.values() if e.signal_id == signal_id]
            evaluations.sort(key=lambda e: e.created_at, reverse=True)
            return evaluations
        except Exception as e:
            logger.error(f"Błąd podczas pobierania ocen dla sygnału {signal_id}: {e}")
            return []
    
    def get_latest_evaluations(self, limit: int = 10) -> List[SignalEvaluation]:
        """Pobiera listę najnowszych ocen sygnałów."""
        try:
            evaluations = list(self.evaluations_cache.values())
            evaluations.sort(key=lambda e: e.created_at, reverse=True)
            return evaluations[:limit]
        except Exception as e:
            logger.error(f"Błąd podczas pobierania najnowszych ocen sygnałów: {e}")
            return []
    
    def update_evaluation(self, evaluation: SignalEvaluation) -> bool:
        """Aktualizuje ocenę sygnału."""
        try:
            if evaluation.id in self.evaluations_cache:
                evaluation.updated_at = datetime.now()
                self.evaluations_cache[evaluation.id] = evaluation
                return True
            return False
        except Exception as e:
            logger.error(f"Błąd podczas aktualizacji oceny sygnału {evaluation.id}: {e}")
            return False
    
    def delete_evaluation(self, evaluation_id: int) -> bool:
        """Usuwa ocenę sygnału z bazy danych."""
        try:
            if evaluation_id in self.evaluations_cache:
                del self.evaluations_cache[evaluation_id]
                return True
            return False
        except Exception as e:
            logger.error(f"Błąd podczas usuwania oceny sygnału {evaluation_id}: {e}")
            return False
    
    def get_evaluations_by_model(self, model_name: str, limit: int = 10) -> List[SignalEvaluation]:
        """Pobiera listę ocen sygnałów wygenerowanych przez określony model AI."""
        try:
            # Obecnie nie mamy bezpośredniego połączenia między oceną a modelem
            # W przyszłości należy dołączyć tabelę sygnałów, aby znaleźć odpowiednie oceny
            return []
        except Exception as e:
            logger.error(f"Błąd podczas pobierania ocen dla modelu {model_name}: {e}")
            return []

def get_signal_evaluation_repository() -> SignalEvaluationRepository:
    """
    Zwraca instancję repozytorium ocen sygnałów handlowych (Singleton).
    
    Returns:
        SignalEvaluationRepository: Instancja repozytorium
    """
    return SignalEvaluationRepository.get_instance() 