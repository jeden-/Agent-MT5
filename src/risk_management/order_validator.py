#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Moduł walidacji zleceń dla systemu AgentMT5.

Ten moduł zawiera klasy i funkcje odpowiedzialne za walidację zleceń handlowych
zgodnie z regułami zarządzania ryzykiem.
"""

import logging
from typing import Dict, List, Optional, Tuple, Union
from datetime import datetime

from .risk_manager import RiskManager, OrderValidationResult, get_risk_manager


class Order:
    """
    Klasa reprezentująca zlecenie handlowe.
    
    Ta klasa opakuje parametry zlecenia w wygodny obiekt, który można łatwiej
    walidować i przetwarzać.
    """
    
    def __init__(self, symbol: str, order_type: str, volume: float, price: float = 0.0,
                 stop_loss: Optional[float] = None, take_profit: Optional[float] = None,
                 comment: str = "", expiration: Optional[datetime] = None,
                 magic_number: int = 0, ea_id: str = ""):
        """
        Inicjalizacja zlecenia handlowego.
        
        Args:
            symbol: Symbol instrumentu.
            order_type: Typ zlecenia ('buy', 'sell', 'buy_limit', itp.).
            volume: Wolumen zlecenia (rozmiar lota).
            price: Cena zlecenia (dla zleceń oczekujących).
            stop_loss: Poziom stop-loss (opcjonalnie).
            take_profit: Poziom take-profit (opcjonalnie).
            comment: Komentarz do zlecenia.
            expiration: Data wygaśnięcia zlecenia (dla zleceń oczekujących).
            magic_number: Unikalny identyfikator zlecenia.
            ea_id: Identyfikator EA, który utworzył zlecenie.
        """
        self.symbol = symbol
        self.order_type = order_type.lower()
        self.volume = volume
        self.price = price
        self.stop_loss = stop_loss
        self.take_profit = take_profit
        self.comment = comment
        self.expiration = expiration
        self.magic_number = magic_number
        self.ea_id = ea_id
        self.validation_result = None
        self.validation_message = None
        self.is_valid = None
    
    @classmethod
    def from_dict(cls, order_dict: Dict) -> 'Order':
        """
        Utworzenie zlecenia z słownika.
        
        Args:
            order_dict: Słownik zawierający parametry zlecenia.
        
        Returns:
            Order: Nowa instancja zlecenia.
        """
        return cls(
            symbol=order_dict.get('symbol', ''),
            order_type=order_dict.get('type', ''),
            volume=float(order_dict.get('volume', 0.0)),
            price=float(order_dict.get('price', 0.0)),
            stop_loss=float(order_dict.get('stop_loss')) if order_dict.get('stop_loss') is not None else None,
            take_profit=float(order_dict.get('take_profit')) if order_dict.get('take_profit') is not None else None,
            comment=order_dict.get('comment', ''),
            expiration=datetime.fromisoformat(order_dict['expiration']) if 'expiration' in order_dict else None,
            magic_number=int(order_dict.get('magic_number', 0)),
            ea_id=order_dict.get('ea_id', '')
        )
    
    def to_dict(self) -> Dict:
        """
        Konwersja zlecenia do słownika.
        
        Returns:
            Dict: Słownik z parametrami zlecenia.
        """
        result = {
            'symbol': self.symbol,
            'type': self.order_type,
            'volume': self.volume,
            'price': self.price,
            'comment': self.comment,
            'magic_number': self.magic_number,
            'ea_id': self.ea_id
        }
        
        if self.stop_loss is not None:
            result['stop_loss'] = self.stop_loss
        
        if self.take_profit is not None:
            result['take_profit'] = self.take_profit
        
        if self.expiration:
            result['expiration'] = self.expiration.isoformat()
        
        return result
    
    def is_market_order(self) -> bool:
        """
        Sprawdza, czy zlecenie jest zleceniem rynkowym.
        
        Returns:
            bool: True, jeśli zlecenie jest rynkowe, False w przeciwnym razie.
        """
        return self.order_type in ['buy', 'sell']
    
    def is_pending_order(self) -> bool:
        """
        Sprawdza, czy zlecenie jest zleceniem oczekującym.
        
        Returns:
            bool: True, jeśli zlecenie jest oczekujące, False w przeciwnym razie.
        """
        return self.order_type in ['buy_limit', 'sell_limit', 'buy_stop', 'sell_stop']
    
    def is_buy_order(self) -> bool:
        """
        Sprawdza, czy zlecenie jest zleceniem kupna.
        
        Returns:
            bool: True, jeśli zlecenie jest kupnem, False w przeciwnym razie.
        """
        return self.order_type in ['buy', 'buy_limit', 'buy_stop']
    
    def is_sell_order(self) -> bool:
        """
        Sprawdza, czy zlecenie jest zleceniem sprzedaży.
        
        Returns:
            bool: True, jeśli zlecenie jest sprzedażą, False w przeciwnym razie.
        """
        return self.order_type in ['sell', 'sell_limit', 'sell_stop']
    
    def calculate_risk_reward_ratio(self) -> Optional[float]:
        """
        Oblicza stosunek zysk/ryzyko dla zlecenia.
        
        Returns:
            Optional[float]: Stosunek zysk/ryzyko lub None, jeśli nie można obliczyć.
        """
        if self.stop_loss is None or self.take_profit is None:
            return None
        
        if self.is_buy_order():
            # Dla pozycji długich (buy)
            if self.price <= 0:
                return None
            
            risk = self.price - self.stop_loss
            reward = self.take_profit - self.price
        else:
            # Dla pozycji krótkich (sell)
            if self.price <= 0:
                return None
            
            risk = self.stop_loss - self.price
            reward = self.price - self.take_profit
        
        if risk <= 0:
            return None
        
        return reward / risk
    
    def __str__(self) -> str:
        """
        Reprezentacja tekstowa zlecenia.
        
        Returns:
            str: Reprezentacja tekstowa.
        """
        return (
            f"Order({self.symbol}, {self.order_type}, volume={self.volume}, "
            f"price={self.price}, SL={self.stop_loss}, TP={self.take_profit})"
        )


class OrderValidator:
    """
    Klasa odpowiedzialna za walidację zleceń handlowych.
    
    Używa RiskManager do sprawdzenia, czy zlecenie jest zgodne z regułami
    zarządzania ryzykiem.
    """
    
    def __init__(self, risk_manager: Optional[RiskManager] = None):
        """
        Inicjalizacja walidatora zleceń.
        
        Args:
            risk_manager: Instancja RiskManager (opcjonalnie, jeśli None, użyje globalnej instancji).
        """
        self.logger = logging.getLogger('trading_agent.risk_management.order_validator')
        self.risk_manager = risk_manager or get_risk_manager()
    
    def validate_order(self, order: Union[Order, Dict]) -> Tuple[bool, OrderValidationResult, Optional[str]]:
        """
        Walidacja zlecenia handlowego.
        
        Args:
            order: Zlecenie handlowe (instancja Order lub słownik).
        
        Returns:
            Tuple zawierający:
            - bool: Czy zlecenie jest poprawne.
            - OrderValidationResult: Wynik walidacji.
            - Optional[str]: Opcjonalny komunikat błędu.
        """
        if isinstance(order, dict):
            order = Order.from_dict(order)
        
        # Przekształcenie Order na słownik dla RiskManager.validate_order
        order_dict = order.to_dict()
        
        # Walidacja przez RiskManager
        is_valid, result, message = self.risk_manager.validate_order(order_dict)
        
        # Zapisanie wyniku walidacji w obiekcie Order
        order.is_valid = is_valid
        order.validation_result = result
        order.validation_message = message
        
        # Logowanie wyniku walidacji
        if is_valid:
            self.logger.debug(f"Zlecenie {order} zostało zwalidowane")
        else:
            self.logger.warning(f"Zlecenie {order} nie przeszło walidacji: {result.value} - {message}")
        
        return is_valid, result, message
    
    def optimize_order(self, order: Order) -> Order:
        """
        Optymalizacja zlecenia zgodnie z regułami ryzyka.
        
        Jeśli zlecenie nie ma określonych poziomów SL/TP, zostaną one obliczone.
        Jeśli zlecenie ma niewłaściwy rozmiar, zostanie dostosowany.
        
        Args:
            order: Zlecenie handlowe do optymalizacji.
        
        Returns:
            Order: Zoptymalizowane zlecenie.
        """
        # Obliczenie SL, jeśli nie jest ustawiony
        if order.stop_loss is None and order.price > 0:
            order.stop_loss = self.risk_manager.calculate_stop_loss_level(
                order.symbol, order.order_type, order.price
            )
            self.logger.debug(f"Obliczono poziom SL dla {order}: {order.stop_loss}")
        
        # Obliczenie TP, jeśli nie jest ustawiony, ale SL jest
        if order.take_profit is None and order.stop_loss is not None and order.price > 0:
            order.take_profit = self.risk_manager.calculate_take_profit_level(
                order.symbol, order.order_type, order.price, order.stop_loss
            )
            self.logger.debug(f"Obliczono poziom TP dla {order}: {order.take_profit}")
        
        # Optymalizacja rozmiaru pozycji, jeśli SL jest ustawiony
        if order.stop_loss is not None and order.price > 0:
            risk_percent = 1.0  # domyślnie ryzykujemy 1% kapitału
            optimized_volume = self.risk_manager.calculate_position_size(
                order.symbol, order.price, order.stop_loss, risk_percent
            )
            
            # Jeśli obliczony wolumen jest mniejszy niż obecny, dostosuj go
            if optimized_volume < order.volume:
                self.logger.info(
                    f"Dostosowano wolumen zlecenia {order} z {order.volume} na {optimized_volume} "
                    f"zgodnie z ryzykiem {risk_percent}%"
                )
                order.volume = optimized_volume
        
        return order
    
    def get_order_risk_report(self, order: Order) -> Dict:
        """
        Generuje raport o ryzyku związanym ze zleceniem.
        
        Args:
            order: Zlecenie handlowe.
        
        Returns:
            Dict: Raport o ryzyku zlecenia.
        """
        risk_reward_ratio = order.calculate_risk_reward_ratio()
        
        # Obliczenie wartości ryzyka (w jednostkach waluty)
        risk_value = 0.0
        if order.stop_loss is not None and order.price > 0:
            risk_distance = abs(order.price - order.stop_loss)
            risk_value = risk_distance * order.volume
        
        # Obliczenie potencjalnego zysku (w jednostkach waluty)
        reward_value = 0.0
        if order.take_profit is not None and order.price > 0:
            reward_distance = abs(order.price - order.take_profit)
            reward_value = reward_distance * order.volume
        
        # Obliczenie procentu kapitału ryzykowanego w zleceniu
        risk_percent = 0.0
        if risk_value > 0 and self.risk_manager.account_balance > 0:
            risk_percent = (risk_value / self.risk_manager.account_balance) * 100
        
        return {
            'symbol': order.symbol,
            'order_type': order.order_type,
            'volume': order.volume,
            'price': order.price,
            'stop_loss': order.stop_loss,
            'take_profit': order.take_profit,
            'risk_reward_ratio': risk_reward_ratio,
            'risk_value': risk_value,
            'reward_value': reward_value,
            'risk_percent': risk_percent,
            'is_valid': order.is_valid,
            'validation_result': order.validation_result.value if order.validation_result else None,
            'validation_message': order.validation_message
        }


# Utworzenie globalnej instancji OrderValidator
_order_validator = None

def get_order_validator() -> OrderValidator:
    """
    Zwraca globalną instancję OrderValidator.
    
    Returns:
        OrderValidator: Instancja walidatora zleceń.
    """
    global _order_validator
    if _order_validator is None:
        _order_validator = OrderValidator()
    return _order_validator 