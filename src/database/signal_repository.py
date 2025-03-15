#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Repozytorium sygnałów handlowych.
"""

import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime

from .repository import Repository
from .models import TradingSignal

logger = logging.getLogger(__name__)

class SignalRepository(Repository):
    """
    Repozytorium sygnałów handlowych, odpowiedzialne za przechowywanie i pobieranie
    sygnałów handlowych.
    """
    
    _instance = None
    
    @classmethod
    def get_instance(cls) -> 'SignalRepository':
        """
        Pobiera instancję repozytorium w trybie singletonu.
        
        Returns:
            SignalRepository: Instancja repozytorium
        """
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def __init__(self):
        """
        Inicjalizacja repozytorium sygnałów handlowych.
        """
        super().__init__("trading_signals")
        self.signals = {}
    
    def save_signal(self, signal: TradingSignal) -> bool:
        """
        Zapisuje sygnał handlowy do bazy danych.
        
        Args:
            signal: Sygnał handlowy do zapisania
            
        Returns:
            bool: True jeśli zapisano pomyślnie
        """
        # Implementacja zaślepka
        logger.info(f"Zapisywanie sygnału handlowego dla {signal.symbol}: {signal.direction}")
        signal_id = id(signal)  # Używamy id obiektu jako klucza
        self.signals[signal_id] = signal
        return True
    
    def get_signal(self, signal_id: int) -> Optional[TradingSignal]:
        """
        Pobiera sygnał handlowy z bazy danych.
        
        Args:
            signal_id: Identyfikator sygnału
            
        Returns:
            Optional[TradingSignal]: Sygnał handlowy lub None
        """
        # Implementacja zaślepka
        return self.signals.get(signal_id)
    
    def get_signals(self, symbol: Optional[str] = None, limit: int = 100) -> List[TradingSignal]:
        """
        Pobiera listę sygnałów handlowych z bazy danych.
        
        Args:
            symbol: Symbol instrumentu (opcjonalnie)
            limit: Maksymalna liczba sygnałów do pobrania
            
        Returns:
            List[TradingSignal]: Lista sygnałów handlowych
        """
        # Implementacja zaślepka
        signals = list(self.signals.values())
        if symbol:
            signals = [s for s in signals if s.symbol == symbol]
        return signals[:limit]
    
    def get_latest_signal(self, symbol: str) -> Optional[TradingSignal]:
        """
        Pobiera ostatni sygnał handlowy dla danego instrumentu.
        
        Args:
            symbol: Symbol instrumentu
            
        Returns:
            Optional[TradingSignal]: Ostatni sygnał handlowy lub None
        """
        # Implementacja zaślepka
        signals = [s for s in self.signals.values() if s.symbol == symbol]
        if signals:
            return max(signals, key=lambda s: s.created_at)
        return None
    
    def update_signal_status(self, signal_id: int, status: str) -> bool:
        """
        Aktualizuje status sygnału handlowego.
        
        Args:
            signal_id: Identyfikator sygnału
            status: Nowy status
            
        Returns:
            bool: True jeśli zaktualizowano pomyślnie
        """
        # Implementacja zaślepka
        if signal_id in self.signals:
            self.signals[signal_id].status = status
            self.signals[signal_id].updated_at = datetime.now()
            return True
        return False
    
    def delete_signal(self, signal_id: int) -> bool:
        """
        Usuwa sygnał handlowy z bazy danych.
        
        Args:
            signal_id: Identyfikator sygnału
            
        Returns:
            bool: True jeśli usunięto pomyślnie
        """
        # Implementacja zaślepka
        if signal_id in self.signals:
            del self.signals[signal_id]
            return True
        return False


def get_signal_repository() -> SignalRepository:
    """
    Funkcja pomocnicza do pobierania instancji repozytorium sygnałów handlowych.
    
    Returns:
        SignalRepository: Instancja repozytorium
    """
    return SignalRepository.get_instance() 