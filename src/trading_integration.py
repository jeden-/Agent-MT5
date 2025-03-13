#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Moduł integracji z systemem tradingowym.
"""

import asyncio
from typing import Dict, List, Optional, Any, Union
from datetime import datetime
import logging
import json

from src.mt5_bridge import TradingService
from src.position_management import PositionManager
from src.risk_management import RiskManager
from src.database.models import TradingSignal, Transaction

logger = logging.getLogger(__name__)

class TradingIntegration:
    def __init__(self, trading_service: Optional[TradingService] = None,
                 position_manager: Optional[PositionManager] = None,
                 risk_manager: Optional[RiskManager] = None,
                 config: Optional[Dict[str, Any]] = None):
        """
        Inicjalizacja integracji handlowej.
        
        Args:
            trading_service: Usługa handlowa do komunikacji z MT5
            position_manager: Manager pozycji
            risk_manager: Manager ryzyka
            config: Konfiguracja (opcjonalnie)
        """
        self.trading_service = trading_service or TradingService()
        self.position_manager = position_manager or PositionManager(config={})
        self.risk_manager = risk_manager or RiskManager()
        self.config = config or {}
        self.registered_instruments = {}
        self.pending_signals = []
        self.max_price_deviation = 0.005  # Maksymalna dopuszczalna odchyłka ceny (0.5%)
        logger.info("TradingIntegration zainicjalizowany")

    def register_instrument(self, symbol: str, max_lot_size: float = 0.1) -> bool:
        """
        Rejestruje instrument do handlu.
        
        Args:
            symbol: Symbol instrumentu
            max_lot_size: Maksymalny rozmiar pozycji
            
        Returns:
            bool: True jeśli zarejestrowano pomyślnie
        """
        try:
            logger.info(f"Rejestrowanie instrumentu: {symbol} (max_lot_size={max_lot_size})")
            self.registered_instruments[symbol] = {
                "max_lot_size": max_lot_size,
                "active": True,
                "last_update": datetime.now()
            }
            return True
        except Exception as e:
            logger.error(f"Błąd podczas rejestracji instrumentu {symbol}: {e}")
            return False

    def unregister_instrument(self, symbol: str) -> bool:
        """
        Wyrejestrowuje instrument z handlu.
        
        Args:
            symbol: Symbol instrumentu
            
        Returns:
            bool: True jeśli wyrejestrowano pomyślnie
        """
        try:
            if symbol in self.registered_instruments:
                logger.info(f"Wyrejestrowywanie instrumentu: {symbol}")
                self.registered_instruments[symbol]["active"] = False
                self.registered_instruments[symbol]["last_update"] = datetime.now()
                return True
            return False
        except Exception as e:
            logger.error(f"Błąd podczas wyrejestrowywania instrumentu {symbol}: {e}")
            return False

    def execute_signal(self, signal: TradingSignal) -> bool:
        """
        Wykonuje sygnał tradingowy, otwierając odpowiednią pozycję.
        
        Args:
            signal: Sygnał tradingowy do wykonania
            
        Returns:
            bool: True jeśli pozycja została otwarta, False w przeciwnym wypadku
        """
        try:
            logger.info(f"Wykonywanie sygnału handlowego: {signal}")
            
            # Sprawdzenie, czy instrument jest zarejestrowany
            if signal.symbol not in self.registered_instruments:
                logger.error(f"Instrument {signal.symbol} nie jest zarejestrowany")
                return False
                
            # Sprawdzenie, czy sygnał jest aktywny
            if signal.status not in ['ACTIVE', 'pending']:
                logger.warning(f"Sygnał dla {signal.symbol} ma status {signal.status} - pomijam")
                return False
            
            # DODANO: Sprawdzenie limitów pozycji przed próbą otwarcia
            # Pobierz aktualne pozycje
            current_positions = self.position_manager.get_positions()
            
            # Sprawdź limity pozycji dla symbolu
            symbol_positions = [p for p in current_positions if p.get('symbol') == signal.symbol]
            if len(symbol_positions) >= self.risk_manager.parameters.max_positions_per_symbol:
                logger.warning(f"Przekroczony limit pozycji dla symbolu {signal.symbol}: "
                             f"{len(symbol_positions)}/{self.risk_manager.parameters.max_positions_per_symbol}")
                return False
                
            # Sprawdź całkowity limit pozycji
            if len(current_positions) >= self.risk_manager.parameters.max_positions_total:
                logger.warning(f"Przekroczony całkowity limit pozycji: "
                             f"{len(current_positions)}/{self.risk_manager.parameters.max_positions_total}")
                return False
                
            # Pobranie aktualnej ceny rynkowej
            current_price = self.trading_service.get_current_price(signal.symbol)
            if current_price is None:
                logger.error(f"Nie można pobrać aktualnej ceny dla {signal.symbol}")
                return False
                
            # Sprawdzenie, czy cena nie odbiega zbyt mocno od ceny wejścia
            price_deviation = abs(current_price - signal.entry_price) / signal.entry_price
            if price_deviation > self.max_price_deviation:
                logger.warning(f"Zbyt duża odchyłka ceny dla {signal.symbol}: {price_deviation:.4f} > {self.max_price_deviation:.4f}")
                return False
                
            # Obliczenie wielkości pozycji na podstawie zarządzania ryzykiem
            lot_size = self.risk_manager.calculate_position_size(
                symbol=signal.symbol,
                price=signal.entry_price,
                stop_loss=signal.stop_loss,
                risk_percent=2.0 * signal.confidence  # Ryzyko zależne od pewności sygnału (0.5-2.0%)
            )
            
            # Jeśli obliczona wielkość pozycji jest <= 0, użyj minimalnej wartości
            if lot_size <= 0:
                logger.warning(f"Obliczona wielkość pozycji dla {signal.symbol} jest <= 0")
                lot_size = 0.01  # Minimalna wielkość pozycji
            
            # Zapisz informację o limitach przed otwarciem pozycji
            logger.info(f"Otwieranie pozycji dla {signal.symbol}. "
                      f"Aktualne pozycje: {len(current_positions)}/{self.risk_manager.parameters.max_positions_total}, "
                      f"Pozycje dla symbolu: {len(symbol_positions)}/{self.risk_manager.parameters.max_positions_per_symbol}")
                
            # Otwarcie pozycji
            position_id = self.trading_service.open_position(
                symbol=signal.symbol,
                direction=signal.direction,
                lot_size=lot_size,
                entry_price=signal.entry_price,
                stop_loss=signal.stop_loss,
                take_profit=signal.take_profit
            )
            
            if position_id:
                logger.info(f"Otwarto pozycję {position_id} dla {signal.symbol} ({signal.direction})")
                
                # Aktualizacja sygnału
                signal.status = "executed"
                signal.execution_id = position_id
                
                # Dodanie pozycji do menedżera pozycji
                self.position_manager.add_position({
                    'ticket': position_id,
                    'symbol': signal.symbol,
                    'type': signal.direction,
                    'volume': lot_size,
                    'open_price': signal.entry_price,
                    'current_price': signal.entry_price,
                    'sl': signal.stop_loss,
                    'tp': signal.take_profit,
                    'profit': 0.0,
                    'open_time': datetime.now(),
                    'status': 'OPEN',
                    'ea_id': 'AgentMT5',
                    'signal_id': signal.id if hasattr(signal, 'id') else None
                })
                
                return True
            else:
                logger.error(f"Nie udało się otworzyć pozycji dla {signal.symbol}")
                return False
                
        except Exception as e:
            logger.error(f"Błąd podczas wykonywania sygnału: {e}", exc_info=True)
            return False

    def save_signal_for_approval(self, signal: TradingSignal) -> bool:
        """
        Zapisuje sygnał handlowy do zatwierdzenia.
        
        Args:
            signal: Sygnał handlowy do zatwierdzenia
            
        Returns:
            bool: True jeśli zapisano pomyślnie
        """
        try:
            logger.info(f"Zapisywanie sygnału handlowego do zatwierdzenia: {signal}")
            self.pending_signals.append({
                "signal": signal,
                "created_at": datetime.now(),
                "status": "pending"
            })
            return True
        except Exception as e:
            logger.error(f"Błąd podczas zapisywania sygnału: {e}")
            return False

    def get_pending_signals(self) -> List[Dict[str, Any]]:
        """
        Pobiera listę oczekujących sygnałów handlowych.
        
        Returns:
            List[Dict[str, Any]]: Lista oczekujących sygnałów
        """
        return self.pending_signals

    def approve_signal(self, signal_id: str) -> Optional[Transaction]:
        """
        Zatwierdza oczekujący sygnał handlowy.
        
        Args:
            signal_id: Identyfikator sygnału do zatwierdzenia
            
        Returns:
            Optional[Transaction]: Transakcja utworzona na podstawie sygnału lub None w przypadku błędu
        """
        try:
            # Znalezienie sygnału
            signal_index = None
            signal_data = None
            for i, data in enumerate(self.pending_signals):
                if data["signal"].id == signal_id:
                    signal_index = i
                    signal_data = data
                    break
            
            if signal_index is None:
                logger.warning(f"Nie znaleziono sygnału o ID {signal_id}")
                return None
            
            # Wykonanie sygnału
            transaction = self.execute_signal(signal_data["signal"])
            
            # Aktualizacja statusu
            if transaction:
                self.pending_signals[signal_index]["status"] = "approved"
                logger.info(f"Sygnał {signal_id} zatwierdzony i wykonany")
            else:
                self.pending_signals[signal_index]["status"] = "error"
                logger.error(f"Sygnał {signal_id} zatwierdzony, ale nie wykonany")
            
            return transaction
        except Exception as e:
            logger.error(f"Błąd podczas zatwierdzania sygnału {signal_id}: {e}")
            return None

    def reject_signal(self, signal_id: str) -> bool:
        """
        Odrzuca oczekujący sygnał handlowy.
        
        Args:
            signal_id: Identyfikator sygnału do odrzucenia
            
        Returns:
            bool: True jeśli odrzucono pomyślnie
        """
        try:
            # Znalezienie sygnału
            signal_index = None
            for i, data in enumerate(self.pending_signals):
                if data["signal"].id == signal_id:
                    signal_index = i
                    break
            
            if signal_index is None:
                logger.warning(f"Nie znaleziono sygnału o ID {signal_id}")
                return False
            
            # Odrzucenie sygnału
            self.pending_signals[signal_index]["status"] = "rejected"
            logger.info(f"Sygnał {signal_id} odrzucony")
            return True
        except Exception as e:
            logger.error(f"Błąd podczas odrzucania sygnału {signal_id}: {e}")
            return False

    async def get_historical_data(self, symbol: str, timeframe: str,
                                num_candles: int) -> List[Dict[str, Any]]:
        """
        Pobiera historyczne dane dla instrumentu.
        
        Args:
            symbol: Symbol instrumentu
            timeframe: Interwał czasowy
            num_candles: Liczba świec do pobrania
            
        Returns:
            List[Dict[str, Any]]: Lista danych historycznych
        """
        try:
            if not self.trading_service:
                logger.error("Brak serwisu handlowego")
                return []
            
            # Pobranie danych historycznych
            data = self.trading_service.get_historical_data(symbol, timeframe, num_candles)
            if data is not None:
                return data.to_dict('records')
            else:
                logger.warning(f"Brak danych historycznych dla {symbol} ({timeframe})")
                return []
        except Exception as e:
            logger.error(f"Błąd podczas pobierania danych historycznych: {e}")
            return [] 