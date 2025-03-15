#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Repozytorium sygnałów handlowych.
"""

import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from src.database.models import TradingSignal
from src.database.db_manager import get_db_manager

logger = logging.getLogger(__name__)

class TradingSignalRepository:
    """Repozytorium sygnałów handlowych."""
    
    _instance = None
    
    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def __init__(self):
        self.db_manager = get_db_manager()
        # Dla uproszczenia używamy pamięci cache jako tymczasowej bazy danych
        self.signals_cache = {}
        self.next_id = 1
        
    def create(self, signal: TradingSignal) -> Optional[TradingSignal]:
        """Dodaje nowy sygnał do bazy danych."""
        try:
            # W pełnej implementacji tutaj byłby kod zapisujący do bazy SQL
            # W tej uproszczonej wersji używamy pamięci cache
            
            # Przypisanie ID jeśli nie zostało podane
            if not hasattr(signal, 'id') or signal.id is None:
                signal.id = self.next_id
                self.next_id += 1
            
            # Dodanie timestampu jeśli nie ma
            if not hasattr(signal, 'timestamp') or signal.timestamp is None:
                signal.timestamp = datetime.now()
                
            # Zapisanie do cache'a
            self.signals_cache[signal.id] = signal
            logger.info(f"Sygnał {signal.id} dla {signal.symbol} zapisany do bazy danych")
            
            return signal
        except Exception as e:
            logger.error(f"Błąd podczas zapisywania sygnału: {e}")
            return None
    
    def save_signal(self, signal: TradingSignal) -> Optional[TradingSignal]:
        """Alias dla metody create."""
        return self.create(signal)
    
    def get_signal_by_id(self, signal_id: int) -> Optional[TradingSignal]:
        """Pobiera sygnał o podanym ID."""
        try:
            return self.signals_cache.get(signal_id)
        except Exception as e:
            logger.error(f"Błąd podczas pobierania sygnału {signal_id}: {e}")
            return None
    
    def get_signals_for_symbol(self, symbol: str, limit: int = 10) -> List[TradingSignal]:
        """Pobiera listę sygnałów dla danego symbolu."""
        try:
            signals = [s for s in self.signals_cache.values() if s.symbol == symbol]
            signals.sort(key=lambda s: s.timestamp, reverse=True)
            return signals[:limit]
        except Exception as e:
            logger.error(f"Błąd podczas pobierania sygnałów dla {symbol}: {e}")
            return []
    
    def get_latest_signals(self, limit: int = 10) -> List[TradingSignal]:
        """Pobiera listę najnowszych sygnałów."""
        try:
            signals = list(self.signals_cache.values())
            signals.sort(key=lambda s: s.timestamp, reverse=True)
            return signals[:limit]
        except Exception as e:
            logger.error(f"Błąd podczas pobierania najnowszych sygnałów: {e}")
            return []
    
    def get_latest_signal_for_symbol(self, symbol: str) -> Optional[TradingSignal]:
        """Pobiera najnowszy sygnał dla danego symbolu."""
        try:
            signals = self.get_signals_for_symbol(symbol, limit=1)
            return signals[0] if signals else None
        except Exception as e:
            logger.error(f"Błąd podczas pobierania najnowszego sygnału dla {symbol}: {e}")
            return None
    
    def update_signal_status(self, signal_id: int, status: str) -> bool:
        """Aktualizuje status sygnału."""
        try:
            signal = self.get_signal_by_id(signal_id)
            if signal:
                signal.status = status
                signal.updated_at = datetime.now()
                return True
            return False
        except Exception as e:
            logger.error(f"Błąd podczas aktualizacji statusu sygnału {signal_id}: {e}")
            return False
    
    def delete_signal(self, signal_id: int) -> bool:
        """Usuwa sygnał z bazy danych."""
        try:
            if signal_id in self.signals_cache:
                del self.signals_cache[signal_id]
                return True
            return False
        except Exception as e:
            logger.error(f"Błąd podczas usuwania sygnału {signal_id}: {e}")
            return False
    
    def get_signals_by_model(self, model_name: str, limit: int = 10) -> List[TradingSignal]:
        """Pobiera listę sygnałów wygenerowanych przez określony model AI."""
        try:
            signals = [s for s in self.signals_cache.values() if s.model_name == model_name]
            signals.sort(key=lambda s: s.timestamp, reverse=True)
            return signals[:limit]
        except Exception as e:
            logger.error(f"Błąd podczas pobierania sygnałów dla modelu {model_name}: {e}")
            return []

def get_trading_signal_repository() -> TradingSignalRepository:
    """
    Zwraca instancję repozytorium sygnałów handlowych (Singleton).
    
    Returns:
        TradingSignalRepository: Instancja repozytorium
    """
    return TradingSignalRepository.get_instance() 