#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Moduł zarządzania pozycjami w backtestingu.
Zawiera funkcje do zarządzania pozycjami, takie jak trailing stop, breakeven, częściowe zamykanie.
"""

import logging
from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass, field
from datetime import datetime
import pandas as pd
import numpy as np

from src.models.signal import SignalType

logger = logging.getLogger(__name__)

@dataclass
class BacktestPosition:
    """Klasa reprezentująca pozycję w backtestingu."""
    symbol: str
    position_type: SignalType  # BUY lub SELL
    volume: float
    entry_price: float
    stop_loss: float
    take_profit: float
    open_time: datetime
    comment: str = ""
    position_id: str = ""
    
    # Dodatkowe parametry zarządzania pozycją
    trailing_stop_activated: bool = False
    trailing_stop_level: Optional[float] = None
    breakeven_activated: bool = False
    breakeven_trigger_pips: float = 0.0
    breakeven_plus_pips: float = 0.0
    partial_close_activated: bool = False
    partial_close_levels: List[Tuple[float, float]] = field(default_factory=list)  # lista (poziom, procent)
    
    # Wykonane akcje
    partial_closes: List[Dict[str, Any]] = field(default_factory=list)
    
    # Statystyki bieżące
    current_profit_pips: float = 0.0
    current_profit_amount: float = 0.0
    max_profit_pips: float = 0.0
    max_drawdown_pips: float = 0.0
    open_duration: float = 0.0  # czas w sekundach od otwarcia
    
    def update_stats(self, current_price: float, current_time: datetime, pip_value: float, position_value_per_lot: float) -> Dict[str, Any]:
        """
        Aktualizuje statystyki pozycji na podstawie bieżącej ceny.
        
        Args:
            current_price: Aktualna cena
            current_time: Aktualny czas
            pip_value: Wartość jednego pipa w walucie konta
            position_value_per_lot: Wartość pozycji na 1 lot w walucie konta
            
        Returns:
            Dict z informacjami o zmianach w pozycji
        """
        # Obliczenie zysku w pipsach
        if self.position_type == SignalType.BUY:
            current_profit_pips = (current_price - self.entry_price) * 10000
        else:  # SELL
            current_profit_pips = (self.entry_price - current_price) * 10000
        
        self.current_profit_pips = current_profit_pips
        
        # Obliczenie zysku w walucie konta
        self.current_profit_amount = current_profit_pips * pip_value * self.volume
        
        # Aktualizacja maksymalnego zysku
        if current_profit_pips > self.max_profit_pips:
            self.max_profit_pips = current_profit_pips
        
        # Aktualizacja maksymalnego drawdown
        drawdown_pips = self.max_profit_pips - current_profit_pips
        if drawdown_pips > self.max_drawdown_pips:
            self.max_drawdown_pips = drawdown_pips
        
        # Aktualizacja czasu trwania pozycji
        self.open_duration = (current_time - self.open_time).total_seconds()
        
        return {
            "position_id": self.position_id,
            "current_profit_pips": self.current_profit_pips,
            "current_profit_amount": self.current_profit_amount,
            "max_profit_pips": self.max_profit_pips,
            "max_drawdown_pips": self.max_drawdown_pips,
            "open_duration": self.open_duration
        }
    
    def should_close(self, current_price: float) -> bool:
        """
        Sprawdza, czy pozycja powinna zostać zamknięta (TP lub SL).
        
        Args:
            current_price: Aktualna cena
            
        Returns:
            bool: True jeśli pozycja powinna zostać zamknięta
        """
        if self.position_type == SignalType.BUY:
            if current_price >= self.take_profit:
                return "tp"
            elif current_price <= self.stop_loss:
                return "sl"
        else:  # SELL
            if current_price <= self.take_profit:
                return "tp"
            elif current_price >= self.stop_loss:
                return "sl"
        
        return None
    
    def should_partially_close(self, current_price: float) -> Optional[Tuple[float, float]]:
        """
        Sprawdza, czy pozycja powinna zostać częściowo zamknięta.
        
        Args:
            current_price: Aktualna cena
            
        Returns:
            Optional[Tuple[float, float]]: Poziom i procent do zamknięcia lub None
        """
        if not self.partial_close_activated or not self.partial_close_levels:
            return None
        
        # Sprawdź każdy poziom częściowego zamknięcia
        for level, percent in self.partial_close_levels:
            # Sprawdź czy ten poziom już został aktywowany
            level_already_closed = False
            for closed in self.partial_closes:
                if closed.get("level") == level:
                    level_already_closed = True
                    break
            
            if level_already_closed:
                continue
            
            # Sprawdź czy osiągnięto poziom
            if self.position_type == SignalType.BUY:
                if current_price >= self.entry_price + (level * 0.0001):
                    return (level, percent)
            else:  # SELL
                if current_price <= self.entry_price - (level * 0.0001):
                    return (level, percent)
        
        return None
    
    def partially_close(self, current_price: float, level: float, percent: float, current_time: datetime) -> Dict[str, Any]:
        """
        Częściowo zamyka pozycję.
        
        Args:
            current_price: Aktualna cena
            level: Poziom zamknięcia
            percent: Procent zamknięcia
            current_time: Aktualny czas
            
        Returns:
            Dict z informacjami o częściowym zamknięciu
        """
        volume_to_close = self.volume * (percent / 100.0)
        self.volume -= volume_to_close
        
        partial_close_info = {
            "level": level,
            "percent": percent,
            "volume_closed": volume_to_close,
            "price": current_price,
            "time": current_time,
            "profit_pips": self.current_profit_pips,
            "profit_amount": self.current_profit_amount * (percent / 100.0)
        }
        
        self.partial_closes.append(partial_close_info)
        return partial_close_info
    
    def apply_trailing_stop(self, current_price: float, trailing_pips: float) -> bool:
        """
        Stosuje trailing stop do pozycji.
        
        Args:
            current_price: Aktualna cena
            trailing_pips: Ilość pipsów do trailing stopu
            
        Returns:
            bool: True jeśli stop loss został zmieniony
        """
        if not self.trailing_stop_activated:
            return False
        
        changed = False
        
        if self.position_type == SignalType.BUY:
            new_stop = current_price - (trailing_pips * 0.0001)
            if new_stop > self.stop_loss:
                self.stop_loss = new_stop
                self.trailing_stop_level = new_stop
                changed = True
        else:  # SELL
            new_stop = current_price + (trailing_pips * 0.0001)
            if new_stop < self.stop_loss:
                self.stop_loss = new_stop
                self.trailing_stop_level = new_stop
                changed = True
        
        return changed
    
    def apply_breakeven(self, current_price: float) -> bool:
        """
        Stosuje breakeven do pozycji.
        
        Args:
            current_price: Aktualna cena
            
        Returns:
            bool: True jeśli stop loss został ustawiony na breakeven
        """
        if not self.breakeven_activated:
            return False
        
        changed = False
        
        if self.position_type == SignalType.BUY:
            # Sprawdź czy cena osiągnęła poziom triggera
            if current_price >= self.entry_price + (self.breakeven_trigger_pips * 0.0001):
                new_stop = self.entry_price + (self.breakeven_plus_pips * 0.0001)
                if new_stop > self.stop_loss:
                    self.stop_loss = new_stop
                    changed = True
                    self.breakeven_activated = False  # Breakeven już zaaplikowany
        else:  # SELL
            # Sprawdź czy cena osiągnęła poziom triggera
            if current_price <= self.entry_price - (self.breakeven_trigger_pips * 0.0001):
                new_stop = self.entry_price - (self.breakeven_plus_pips * 0.0001)
                if new_stop < self.stop_loss:
                    self.stop_loss = new_stop
                    changed = True
                    self.breakeven_activated = False  # Breakeven już zaaplikowany
        
        return changed


class PositionManager:
    """
    Klasa do zarządzania pozycjami w backtestingu.
    """
    
    def __init__(self):
        """Inicjalizacja menedżera pozycji."""
        self.logger = logging.getLogger(__name__)
        self.positions = {}  # słownik pozycji: position_id -> BacktestPosition
        self.closed_positions = []  # lista zamkniętych pozycji
        self.position_count = 0  # licznik pozycji (do generowania ID)
    
    def open_position(self, symbol: str, position_type: SignalType, volume: float, 
                    entry_price: float, stop_loss: float, take_profit: float,
                    open_time: datetime, comment: str = "",
                    trailing_stop: bool = False, trailing_pips: float = 20.0,
                    breakeven: bool = False, breakeven_trigger_pips: float = 20.0, breakeven_plus_pips: float = 5.0,
                    partial_close: bool = False, partial_close_levels: List[Tuple[float, float]] = None) -> BacktestPosition:
        """
        Otwiera nową pozycję.
        
        Args:
            symbol: Symbol instrumentu
            position_type: Typ pozycji (BUY lub SELL)
            volume: Wielkość pozycji w lotach
            entry_price: Cena wejścia
            stop_loss: Poziom stop loss
            take_profit: Poziom take profit
            open_time: Czas otwarcia
            comment: Komentarz
            trailing_stop: Czy aktywować trailing stop
            trailing_pips: Ilość pipsów do trailing stopu
            breakeven: Czy aktywować breakeven
            breakeven_trigger_pips: Liczba pipsów zysku do aktywacji breakeven
            breakeven_plus_pips: Liczba pipsów powyżej entry po breakeven
            partial_close: Czy aktywować częściowe zamykanie
            partial_close_levels: Lista tupli (poziom_pipsów, procent_do_zamknięcia)
            
        Returns:
            BacktestPosition: Utworzona pozycja
        """
        self.position_count += 1
        position_id = f"BT{self.position_count}"
        
        # Sprawdzenie poziomów częściowego zamykania
        if partial_close_levels is None:
            partial_close_levels = []
        
        position = BacktestPosition(
            symbol=symbol,
            position_type=position_type,
            volume=volume,
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            open_time=open_time,
            comment=comment,
            position_id=position_id,
            trailing_stop_activated=trailing_stop,
            breakeven_activated=breakeven,
            breakeven_trigger_pips=breakeven_trigger_pips,
            breakeven_plus_pips=breakeven_plus_pips,
            partial_close_activated=partial_close,
            partial_close_levels=partial_close_levels
        )
        
        self.positions[position_id] = position
        self.logger.info(f"Otwarto pozycję {position_id}: {position_type.name} {volume} lota {symbol} @ {entry_price} (SL: {stop_loss}, TP: {take_profit})")
        
        return position
    
    def close_position(self, position_id: str, close_price: float, close_time: datetime, close_reason: str) -> Dict[str, Any]:
        """
        Zamyka pozycję.
        
        Args:
            position_id: ID pozycji do zamknięcia
            close_price: Cena zamknięcia
            close_time: Czas zamknięcia
            close_reason: Powód zamknięcia (tp, sl, manual)
            
        Returns:
            Dict z informacjami o zamkniętej pozycji
        """
        if position_id not in self.positions:
            self.logger.warning(f"Próba zamknięcia nieistniejącej pozycji {position_id}")
            return None
        
        position = self.positions[position_id]
        
        # Obliczenie zysku w pipsach
        if position.position_type == SignalType.BUY:
            profit_pips = (close_price - position.entry_price) * 10000
        else:  # SELL
            profit_pips = (position.entry_price - close_price) * 10000
        
        # Utworzenie informacji o zamkniętej pozycji
        closed_position_info = {
            "position_id": position_id,
            "symbol": position.symbol,
            "position_type": position.position_type.name,
            "volume": position.volume,
            "entry_price": position.entry_price,
            "close_price": close_price,
            "stop_loss": position.stop_loss,
            "take_profit": position.take_profit,
            "open_time": position.open_time,
            "close_time": close_time,
            "profit_pips": profit_pips,
            "close_reason": close_reason,
            "comment": position.comment,
            "max_profit_pips": position.max_profit_pips,
            "max_drawdown_pips": position.max_drawdown_pips,
            "partial_closes": position.partial_closes
        }
        
        self.closed_positions.append(closed_position_info)
        self.logger.info(f"Zamknięto pozycję {position_id}: {profit_pips:.1f} pips zysku, powód: {close_reason}")
        
        # Usunięcie pozycji z aktywnych
        del self.positions[position_id]
        
        return closed_position_info
    
    def update_positions(self, current_prices: Dict[str, float], current_time: datetime, 
                         pip_values: Dict[str, float], position_values: Dict[str, float]) -> Dict[str, Any]:
        """
        Aktualizuje wszystkie pozycje na podstawie bieżących cen.
        
        Args:
            current_prices: Słownik bieżących cen (symbol -> cena)
            current_time: Aktualny czas
            pip_values: Słownik wartości pipa (symbol -> wartość)
            position_values: Słownik wartości pozycji na 1 lot (symbol -> wartość)
            
        Returns:
            Dict z informacjami o aktualizacjach pozycji
        """
        updates = {
            "closed_positions": [],
            "partial_closes": [],
            "trailing_stops": [],
            "breakevens": []
        }
        
        # Aktualizacja każdej pozycji
        positions_to_close = []
        
        for position_id, position in self.positions.items():
            symbol = position.symbol
            
            if symbol not in current_prices:
                self.logger.warning(f"Brak bieżącej ceny dla {symbol}")
                continue
            
            current_price = current_prices[symbol]
            pip_value = pip_values.get(symbol, 0.1)  # domyślnie 0.1 jednostki waluty na pip
            position_value = position_values.get(symbol, 100000)  # domyślnie 100k jednostek na 1 lot
            
            # Aktualizacja statystyk pozycji
            position.update_stats(current_price, current_time, pip_value, position_value)
            
            # Sprawdzenie czy pozycja powinna zostać zamknięta (TP/SL)
            close_reason = position.should_close(current_price)
            if close_reason:
                positions_to_close.append((position_id, current_price, current_time, close_reason))
                continue
            
            # Sprawdzenie czy pozycja powinna zostać częściowo zamknięta
            partial_close = position.should_partially_close(current_price)
            if partial_close:
                level, percent = partial_close
                partial_close_info = position.partially_close(current_price, level, percent, current_time)
                updates["partial_closes"].append(partial_close_info)
            
            # Zastosowanie trailing stop
            if position.trailing_stop_activated:
                trailing_pips = 20.0  # wartość domyślna, można dostosować
                trailing_changed = position.apply_trailing_stop(current_price, trailing_pips)
                if trailing_changed:
                    updates["trailing_stops"].append({
                        "position_id": position_id,
                        "new_stop_loss": position.stop_loss
                    })
            
            # Zastosowanie breakeven
            if position.breakeven_activated:
                breakeven_changed = position.apply_breakeven(current_price)
                if breakeven_changed:
                    updates["breakevens"].append({
                        "position_id": position_id,
                        "new_stop_loss": position.stop_loss
                    })
        
        # Zamknięcie pozycji
        for position_id, close_price, close_time, close_reason in positions_to_close:
            closed_position = self.close_position(position_id, close_price, close_time, close_reason)
            if closed_position:
                updates["closed_positions"].append(closed_position)
        
        return updates
    
    def get_position(self, position_id: str) -> Optional[BacktestPosition]:
        """
        Pobiera pozycję o podanym ID.
        
        Args:
            position_id: ID pozycji
            
        Returns:
            Optional[BacktestPosition]: Pozycja lub None jeśli nie istnieje
        """
        return self.positions.get(position_id)
    
    def get_active_positions(self) -> List[BacktestPosition]:
        """
        Pobiera listę aktywnych pozycji.
        
        Returns:
            List[BacktestPosition]: Lista aktywnych pozycji
        """
        return list(self.positions.values())
    
    def get_closed_positions(self) -> List[Dict[str, Any]]:
        """
        Pobiera listę zamkniętych pozycji.
        
        Returns:
            List[Dict[str, Any]]: Lista zamkniętych pozycji
        """
        return self.closed_positions
    
    def get_position_count(self) -> int:
        """
        Pobiera liczbę aktywnych pozycji.
        
        Returns:
            int: Liczba aktywnych pozycji
        """
        return len(self.positions)
    
    def get_positions_for_symbol(self, symbol: str) -> List[BacktestPosition]:
        """
        Pobiera listę aktywnych pozycji dla danego symbolu.
        
        Args:
            symbol: Symbol instrumentu
            
        Returns:
            List[BacktestPosition]: Lista aktywnych pozycji dla danego symbolu
        """
        return [p for p in self.positions.values() if p.symbol == symbol]
    
    def get_total_exposure(self, symbol: str = None) -> float:
        """
        Pobiera łączną ekspozycję dla danego symbolu lub wszystkich pozycji.
        
        Args:
            symbol: Symbol instrumentu (opcjonalnie)
            
        Returns:
            float: Łączna ekspozycja w lotach
        """
        if symbol:
            return sum(p.volume for p in self.positions.values() if p.symbol == symbol)
        else:
            return sum(p.volume for p in self.positions.values())
    
    def get_net_exposure(self, symbol: str = None) -> float:
        """
        Pobiera ekspozycję netto (uwzględniając kierunek) dla danego symbolu lub wszystkich pozycji.
        
        Args:
            symbol: Symbol instrumentu (opcjonalnie)
            
        Returns:
            float: Ekspozycja netto w lotach (dodatnia dla długich, ujemna dla krótkich)
        """
        positions = self.positions.values()
        if symbol:
            positions = [p for p in positions if p.symbol == symbol]
        
        long_volume = sum(p.volume for p in positions if p.position_type == SignalType.BUY)
        short_volume = sum(p.volume for p in positions if p.position_type == SignalType.SELL)
        
        return long_volume - short_volume
    
    def get_current_profit(self, symbol: str = None) -> float:
        """
        Pobiera bieżący zysk dla danego symbolu lub wszystkich pozycji.
        
        Args:
            symbol: Symbol instrumentu (opcjonalnie)
            
        Returns:
            float: Bieżący zysk w walucie konta
        """
        positions = self.positions.values()
        if symbol:
            positions = [p for p in positions if p.symbol == symbol]
        
        return sum(p.current_profit_amount for p in positions)
    
    def configure_trailing_stop(self, position_id: str, active: bool = True, trailing_pips: float = 20.0) -> bool:
        """
        Konfiguruje trailing stop dla pozycji.
        
        Args:
            position_id: ID pozycji
            active: Czy trailing stop ma być aktywny
            trailing_pips: Ilość pipsów do trailing stopu
            
        Returns:
            bool: True jeśli konfiguracja się powiodła
        """
        position = self.get_position(position_id)
        if not position:
            return False
        
        position.trailing_stop_activated = active
        position.trailing_stop_level = None  # reset poziomu trailing stopu
        
        return True
    
    def configure_breakeven(self, position_id: str, active: bool = True, 
                           trigger_pips: float = 20.0, plus_pips: float = 5.0) -> bool:
        """
        Konfiguruje breakeven dla pozycji.
        
        Args:
            position_id: ID pozycji
            active: Czy breakeven ma być aktywny
            trigger_pips: Liczba pipsów zysku do aktywacji breakeven
            plus_pips: Liczba pipsów powyżej entry po breakeven
            
        Returns:
            bool: True jeśli konfiguracja się powiodła
        """
        position = self.get_position(position_id)
        if not position:
            return False
        
        position.breakeven_activated = active
        position.breakeven_trigger_pips = trigger_pips
        position.breakeven_plus_pips = plus_pips
        
        return True
    
    def configure_partial_close(self, position_id: str, active: bool = True, 
                               levels: List[Tuple[float, float]] = None) -> bool:
        """
        Konfiguruje częściowe zamykanie dla pozycji.
        
        Args:
            position_id: ID pozycji
            active: Czy częściowe zamykanie ma być aktywne
            levels: Lista tupli (poziom_pipsów, procent_do_zamknięcia)
            
        Returns:
            bool: True jeśli konfiguracja się powiodła
        """
        position = self.get_position(position_id)
        if not position:
            return False
        
        position.partial_close_activated = active
        if levels:
            position.partial_close_levels = levels
        
        return True 