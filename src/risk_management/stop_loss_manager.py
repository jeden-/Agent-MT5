#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Moduł zarządzania stop-lossami dla systemu AgentMT5.

Ten moduł zawiera klasy i funkcje odpowiedzialne za zarządzanie stop-lossami,
w tym obliczanie optymalnych poziomów stop-loss, zarządzanie trailing stopami
i monitorowanie pozycji.
"""

import logging
from typing import Dict, List, Optional, Tuple, Union
from datetime import datetime
from enum import Enum
from dataclasses import dataclass

from .risk_manager import RiskManager, get_risk_manager


class StopLossStrategy(Enum):
    """Strategie ustawiania stop-lossów."""
    FIXED_PIPS = 'fixed_pips'
    ATR_BASED = 'atr_based'
    SUPPORT_RESISTANCE = 'support_resistance'
    VOLATILITY_BASED = 'volatility_based'
    PERCENT_BASED = 'percent_based'
    CUSTOM = 'custom'


class TrailingStopStrategy(Enum):
    """Strategie zarządzania trailing stopami."""
    FIXED_PIPS = 'fixed_pips'
    ATR_BASED = 'atr_based'
    PERCENT_BASED = 'percent_based'
    STEP_BASED = 'step_based'
    PARABOLIC_SAR = 'parabolic_sar'
    CUSTOM = 'custom'


@dataclass
class StopLossConfig:
    """Konfiguracja stop-lossów."""
    strategy: StopLossStrategy = StopLossStrategy.FIXED_PIPS
    pips: int = 30
    percent: float = 1.0
    atr_multiplier: float = 2.0
    atr_period: int = 14
    min_distance_pips: int = 10
    max_distance_pips: int = 100
    use_custom_levels: bool = False
    custom_levels: Dict[str, Dict[str, float]] = None


@dataclass
class TrailingStopConfig:
    """Konfiguracja trailing stopów."""
    strategy: TrailingStopStrategy = TrailingStopStrategy.FIXED_PIPS
    activation_pips: int = 20
    step_pips: int = 10
    activation_percent: float = 0.5
    step_percent: float = 0.2
    lock_profit_percent: float = 0.3
    atr_multiplier: float = 1.5
    atr_period: int = 14
    parabolic_step: float = 0.02
    parabolic_maximum: float = 0.2
    enabled: bool = True


class PositionState:
    """
    Klasa przechowująca stan pozycji dla zarządzania stop-lossami.
    
    Ta klasa śledzi stan pozycji, w tym cenę wejścia, aktualny poziom stop-loss,
    najwyższą/najniższą cenę od otwarcia pozycji, itp.
    """
    
    def __init__(self, position_id: int, symbol: str, order_type: str, volume: float,
                entry_price: float, stop_loss: float, take_profit: float,
                open_time: datetime, magic_number: int = 0, comment: str = ""):
        """
        Inicjalizacja stanu pozycji.
        
        Args:
            position_id: Identyfikator pozycji.
            symbol: Symbol instrumentu.
            order_type: Typ zlecenia ('buy' lub 'sell').
            volume: Wolumen pozycji.
            entry_price: Cena wejścia.
            stop_loss: Poziom stop-loss.
            take_profit: Poziom take-profit.
            open_time: Czas otwarcia pozycji.
            magic_number: Identyfikator EA (opcjonalnie).
            comment: Komentarz do pozycji (opcjonalnie).
        """
        self.position_id = position_id
        self.symbol = symbol
        self.order_type = order_type.lower()
        self.volume = volume
        self.entry_price = entry_price
        self.stop_loss = stop_loss
        self.take_profit = take_profit
        self.open_time = open_time
        self.magic_number = magic_number
        self.comment = comment
        
        # Zmienne do śledzenia stanu
        self.highest_price = entry_price if order_type.lower() == 'buy' else 0.0
        self.lowest_price = entry_price if order_type.lower() == 'sell' else float('inf')
        self.current_price = entry_price
        self.last_update_time = open_time
        self.trailing_activated = False
        self.original_stop_loss = stop_loss
        self.stop_loss_modifications = []
        self.current_profit = 0.0
        self.max_profit = 0.0
        self.max_drawdown = 0.0
        self.pip_value = 0.0001 if not self.symbol.endswith('JPY') else 0.01
    
    def update_price(self, price: float, current_time: datetime = None) -> None:
        """
        Aktualizacja aktualnej ceny i śledzonych wartości.
        
        Args:
            price: Aktualna cena rynkowa.
            current_time: Aktualny czas (opcjonalnie, domyślnie: teraz).
        """
        if current_time is None:
            current_time = datetime.now()
        
        self.current_price = price
        self.last_update_time = current_time
        
        # Aktualizacja najwyższej/najniższej ceny
        if self.order_type == 'buy' and price > self.highest_price:
            self.highest_price = price
        elif self.order_type == 'sell' and price < self.lowest_price:
            self.lowest_price = price
        
        # Obliczenie aktualnego zysku/straty
        if self.order_type == 'buy':
            self.current_profit = (price - self.entry_price) * self.volume / self.pip_value
        else:
            self.current_profit = (self.entry_price - price) * self.volume / self.pip_value
        
        # Aktualizacja maksymalnego zysku
        if self.current_profit > self.max_profit:
            self.max_profit = self.current_profit
        
        # Obliczenie maksymalnego drawdown
        drawdown = self.max_profit - self.current_profit
        if drawdown > self.max_drawdown:
            self.max_drawdown = drawdown
    
    def update_stop_loss(self, new_stop_loss: float, reason: str) -> None:
        """
        Aktualizacja poziomu stop-loss.
        
        Args:
            new_stop_loss: Nowy poziom stop-loss.
            reason: Powód zmiany stop-loss.
        """
        old_stop_loss = self.stop_loss
        self.stop_loss = new_stop_loss
        
        # Zapisanie modyfikacji
        self.stop_loss_modifications.append({
            'timestamp': datetime.now().isoformat(),
            'old_stop_loss': old_stop_loss,
            'new_stop_loss': new_stop_loss,
            'reason': reason,
            'price': self.current_price
        })
        
        # Aktualizacja flagi trailing stop
        self.trailing_activated = True
    
    def get_profit_in_pips(self) -> float:
        """
        Zwraca aktualny zysk/stratę w pipsach.
        
        Returns:
            float: Zysk/strata w pipsach.
        """
        if self.order_type == 'buy':
            return (self.current_price - self.entry_price) / self.pip_value
        else:
            return (self.entry_price - self.current_price) / self.pip_value
    
    def get_profit_percent(self, account_balance: float) -> float:
        """
        Zwraca aktualny zysk/stratę jako procent kapitału.
        
        Args:
            account_balance: Saldo konta.
        
        Returns:
            float: Zysk/strata jako procent kapitału.
        """
        if account_balance <= 0:
            return 0.0
        
        profit_value = 0.0
        if self.order_type == 'buy':
            profit_value = (self.current_price - self.entry_price) * self.volume
        else:
            profit_value = (self.entry_price - self.current_price) * self.volume
        
        return (profit_value / account_balance) * 100
    
    def to_dict(self) -> Dict:
        """
        Konwersja stanu pozycji do słownika.
        
        Returns:
            Dict: Słownik ze stanem pozycji.
        """
        return {
            'position_id': self.position_id,
            'symbol': self.symbol,
            'order_type': self.order_type,
            'volume': self.volume,
            'entry_price': self.entry_price,
            'stop_loss': self.stop_loss,
            'take_profit': self.take_profit,
            'open_time': self.open_time.isoformat(),
            'magic_number': self.magic_number,
            'comment': self.comment,
            'highest_price': self.highest_price,
            'lowest_price': self.lowest_price,
            'current_price': self.current_price,
            'last_update_time': self.last_update_time.isoformat(),
            'trailing_activated': self.trailing_activated,
            'original_stop_loss': self.original_stop_loss,
            'stop_loss_modifications': self.stop_loss_modifications,
            'current_profit': self.current_profit,
            'max_profit': self.max_profit,
            'max_drawdown': self.max_drawdown,
            'pip_value': self.pip_value
        }


class StopLossManager:
    """
    Klasa zarządzająca stop-lossami i trailing stopami.
    
    Odpowiada za:
    - Obliczanie optymalnych poziomów stop-loss
    - Zarządzanie trailing stopami
    - Monitorowanie pozycji i dostosowywanie stop-lossów
    """
    
    _instance = None
    
    def __new__(cls):
        """Implementacja wzorca Singleton."""
        if cls._instance is None:
            cls._instance = super(StopLossManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """Inicjalizacja menedżera stop-lossów."""
        if self._initialized:
            return
        
        self._initialized = True
        self.logger = logging.getLogger('trading_agent.risk_management.stop_loss_manager')
        self.risk_manager = get_risk_manager()
        
        # Konfiguracja
        self.stop_loss_config = StopLossConfig()
        self.trailing_stop_config = TrailingStopConfig()
        
        # Słownik aktywnych pozycji (position_id -> PositionState)
        self.positions = {}
        
        # Funkcje obliczające ATR (Average True Range) dla różnych symboli i ram czasowych
        self.atr_functions = {}
        
        # Obserwowane poziomy wsparcia/oporu dla różnych symboli
        self.support_resistance_levels = {}
        
        self.logger.info("Inicjalizacja StopLossManager")
    
    def configure_stop_loss(self, config: Union[Dict, StopLossConfig]) -> None:
        """
        Konfiguracja parametrów stop-loss.
        
        Args:
            config: Konfiguracja stop-loss (słownik lub instancja StopLossConfig).
        """
        if isinstance(config, dict):
            # Konwersja strategii z tekstu na enum
            if 'strategy' in config and isinstance(config['strategy'], str):
                try:
                    config['strategy'] = StopLossStrategy(config['strategy'])
                except ValueError:
                    self.logger.warning(f"Nieznana strategia stop-loss: {config['strategy']}, używam domyślnej")
                    config['strategy'] = StopLossStrategy.FIXED_PIPS
            
            # Aktualizacja konfiguracji
            for key, value in config.items():
                if hasattr(self.stop_loss_config, key):
                    setattr(self.stop_loss_config, key, value)
        else:
            self.stop_loss_config = config
        
        self.logger.info(f"Skonfigurowano stop-loss: {self.stop_loss_config}")
    
    def configure_trailing_stop(self, config: Union[Dict, TrailingStopConfig]) -> None:
        """
        Konfiguracja parametrów trailing stop.
        
        Args:
            config: Konfiguracja trailing stop (słownik lub instancja TrailingStopConfig).
        """
        if isinstance(config, dict):
            # Konwersja strategii z tekstu na enum
            if 'strategy' in config and isinstance(config['strategy'], str):
                try:
                    config['strategy'] = TrailingStopStrategy(config['strategy'])
                except ValueError:
                    self.logger.warning(f"Nieznana strategia trailing stop: {config['strategy']}, używam domyślnej")
                    config['strategy'] = TrailingStopStrategy.FIXED_PIPS
            
            # Aktualizacja konfiguracji
            for key, value in config.items():
                if hasattr(self.trailing_stop_config, key):
                    setattr(self.trailing_stop_config, key, value)
        else:
            self.trailing_stop_config = config
        
        self.logger.info(f"Skonfigurowano trailing stop: {self.trailing_stop_config}")
    
    def register_position(self, position_id: int, symbol: str, order_type: str, volume: float,
                         entry_price: float, stop_loss: float, take_profit: float,
                         open_time: Optional[datetime] = None, magic_number: int = 0,
                         comment: str = "") -> None:
        """
        Rejestracja nowej pozycji do śledzenia.
        
        Args:
            position_id: Identyfikator pozycji.
            symbol: Symbol instrumentu.
            order_type: Typ zlecenia ('buy' lub 'sell').
            volume: Wolumen pozycji.
            entry_price: Cena wejścia.
            stop_loss: Poziom stop-loss.
            take_profit: Poziom take-profit.
            open_time: Czas otwarcia pozycji (opcjonalnie, domyślnie: teraz).
            magic_number: Identyfikator EA (opcjonalnie).
            comment: Komentarz do pozycji (opcjonalnie).
        """
        if open_time is None:
            open_time = datetime.now()
        
        # Utworzenie stanu pozycji
        position_state = PositionState(
            position_id=position_id,
            symbol=symbol,
            order_type=order_type,
            volume=volume,
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            open_time=open_time,
            magic_number=magic_number,
            comment=comment
        )
        
        # Dodanie pozycji do śledzonych
        self.positions[position_id] = position_state
        self.logger.info(f"Zarejestrowano pozycję {position_id} dla {symbol}: {order_type}, cena={entry_price}, SL={stop_loss}, TP={take_profit}")
    
    def unregister_position(self, position_id: int) -> None:
        """
        Wyrejestrowanie pozycji ze śledzenia.
        
        Args:
            position_id: Identyfikator pozycji.
        """
        if position_id in self.positions:
            position = self.positions[position_id]
            self.logger.info(f"Wyrejestrowano pozycję {position_id} dla {position.symbol}")
            del self.positions[position_id]
    
    def update_position_price(self, position_id: int, price: float, current_time: Optional[datetime] = None) -> None:
        """
        Aktualizacja ceny dla śledzonej pozycji.
        
        Args:
            position_id: Identyfikator pozycji.
            price: Aktualna cena rynkowa.
            current_time: Aktualny czas (opcjonalnie, domyślnie: teraz).
        """
        if position_id in self.positions:
            self.positions[position_id].update_price(price, current_time)
    
    def calculate_stop_loss(self, symbol: str, order_type: str, entry_price: float, atr_value: Optional[float] = None) -> float:
        """
        Obliczenie optymalnego poziomu stop-loss na podstawie konfiguracji.
        
        Args:
            symbol: Symbol instrumentu.
            order_type: Typ zlecenia ('buy' lub 'sell').
            entry_price: Cena wejścia.
            atr_value: Wartość ATR (opcjonalnie, tylko dla strategii opartych na ATR).
        
        Returns:
            float: Poziom stop-loss.
        """
        pip_value = 0.0001
        if symbol.endswith('JPY'):
            pip_value = 0.01
        
        # Sprawdzenie strategii
        if self.stop_loss_config.strategy == StopLossStrategy.FIXED_PIPS:
            # Stop-loss oparty na stałej liczbie pipsów
            distance = self.stop_loss_config.pips * pip_value
            if order_type.lower() in ['buy', 'buy_limit', 'buy_stop']:
                return entry_price - distance
            else:
                return entry_price + distance
        
        elif self.stop_loss_config.strategy == StopLossStrategy.ATR_BASED:
            # Stop-loss oparty na ATR
            if atr_value is None:
                # Jeśli nie podano ATR, użyj domyślnej wartości fixed_pips
                self.logger.warning(f"Nie podano ATR dla {symbol}, używam fixed_pips")
                distance = self.stop_loss_config.pips * pip_value
            else:
                distance = atr_value * self.stop_loss_config.atr_multiplier
            
            # Ograniczenie minimalnego i maksymalnego dystansu
            min_distance = self.stop_loss_config.min_distance_pips * pip_value
            max_distance = self.stop_loss_config.max_distance_pips * pip_value
            
            if distance < min_distance:
                distance = min_distance
            elif distance > max_distance:
                distance = max_distance
            
            if order_type.lower() in ['buy', 'buy_limit', 'buy_stop']:
                return entry_price - distance
            else:
                return entry_price + distance
        
        elif self.stop_loss_config.strategy == StopLossStrategy.PERCENT_BASED:
            # Stop-loss oparty na procencie ceny
            distance = entry_price * self.stop_loss_config.percent / 100
            if order_type.lower() in ['buy', 'buy_limit', 'buy_stop']:
                return entry_price - distance
            else:
                return entry_price + distance
        
        elif self.stop_loss_config.strategy == StopLossStrategy.SUPPORT_RESISTANCE:
            # Stop-loss oparty na poziomach wsparcia/oporu
            if symbol in self.support_resistance_levels:
                levels = self.support_resistance_levels[symbol]
                if order_type.lower() in ['buy', 'buy_limit', 'buy_stop']:
                    # Dla pozycji długich, znajdź najbliższy poziom wsparcia poniżej ceny wejścia
                    support_levels = [level for level in levels.get('support', []) if level < entry_price]
                    if support_levels:
                        return max(support_levels)
                else:
                    # Dla pozycji krótkich, znajdź najbliższy poziom oporu powyżej ceny wejścia
                    resistance_levels = [level for level in levels.get('resistance', []) if level > entry_price]
                    if resistance_levels:
                        return min(resistance_levels)
            
            # Jeśli nie znaleziono odpowiednich poziomów, użyj fixed_pips
            self.logger.warning(f"Nie znaleziono poziomów wsparcia/oporu dla {symbol}, używam fixed_pips")
            distance = self.stop_loss_config.pips * pip_value
            if order_type.lower() in ['buy', 'buy_limit', 'buy_stop']:
                return entry_price - distance
            else:
                return entry_price + distance
        
        elif self.stop_loss_config.strategy == StopLossStrategy.CUSTOM and self.stop_loss_config.use_custom_levels:
            # Stop-loss oparty na niestandardowych poziomach
            if (symbol in self.stop_loss_config.custom_levels and 
                order_type in self.stop_loss_config.custom_levels[symbol]):
                return self.stop_loss_config.custom_levels[symbol][order_type]
            
            # Jeśli nie znaleziono niestandardowych poziomów, użyj fixed_pips
            self.logger.warning(f"Nie znaleziono niestandardowych poziomów dla {symbol}/{order_type}, używam fixed_pips")
            distance = self.stop_loss_config.pips * pip_value
            if order_type.lower() in ['buy', 'buy_limit', 'buy_stop']:
                return entry_price - distance
            else:
                return entry_price + distance
        
        else:
            # Domyślnie użyj fixed_pips
            distance = self.stop_loss_config.pips * pip_value
            if order_type.lower() in ['buy', 'buy_limit', 'buy_stop']:
                return entry_price - distance
            else:
                return entry_price + distance
    
    def check_trailing_stop(self, position_id: int) -> Tuple[bool, Optional[float]]:
        """
        Sprawdza, czy należy zmodyfikować stop-loss dla pozycji (trailing stop).
        
        Args:
            position_id: Identyfikator pozycji.
        
        Returns:
            Tuple zawierający:
            - bool: Czy należy zmodyfikować stop-loss.
            - Optional[float]: Nowy poziom stop-loss lub None, jeśli nie ma potrzeby modyfikacji.
        """
        if not self.trailing_stop_config.enabled:
            return False, None
        
        if position_id not in self.positions:
            return False, None
        
        position = self.positions[position_id]
        pip_value = position.pip_value
        
        # Sprawdzenie strategii
        if self.trailing_stop_config.strategy == TrailingStopStrategy.FIXED_PIPS:
            # Trailing stop oparty na stałej liczbie pipsów
            activation_distance = self.trailing_stop_config.activation_pips * pip_value
            step_distance = self.trailing_stop_config.step_pips * pip_value
            
            if position.order_type == 'buy':
                # Dla pozycji długich
                profit_distance = position.current_price - position.entry_price
                if profit_distance >= activation_distance:
                    # Obliczenie nowego poziomu stop-loss
                    new_sl = position.current_price - step_distance
                    # Sprawdzenie, czy nowy SL jest wyższy niż obecny
                    if new_sl > position.stop_loss:
                        return True, new_sl
            else:
                # Dla pozycji krótkich
                profit_distance = position.entry_price - position.current_price
                if profit_distance >= activation_distance:
                    # Obliczenie nowego poziomu stop-loss
                    new_sl = position.current_price + step_distance
                    # Sprawdzenie, czy nowy SL jest niższy niż obecny
                    if new_sl < position.stop_loss:
                        return True, new_sl
        
        elif self.trailing_stop_config.strategy == TrailingStopStrategy.PERCENT_BASED:
            # Trailing stop oparty na procentach
            activation_percent = self.trailing_stop_config.activation_percent / 100
            step_percent = self.trailing_stop_config.step_percent / 100
            
            if position.order_type == 'buy':
                # Dla pozycji długich
                profit_percent = (position.current_price - position.entry_price) / position.entry_price
                if profit_percent >= activation_percent:
                    # Obliczenie nowego poziomu stop-loss
                    new_sl = position.current_price * (1 - step_percent)
                    # Sprawdzenie, czy nowy SL jest wyższy niż obecny
                    if new_sl > position.stop_loss:
                        return True, new_sl
            else:
                # Dla pozycji krótkich
                profit_percent = (position.entry_price - position.current_price) / position.entry_price
                if profit_percent >= activation_percent:
                    # Obliczenie nowego poziomu stop-loss
                    new_sl = position.current_price * (1 + step_percent)
                    # Sprawdzenie, czy nowy SL jest niższy niż obecny
                    if new_sl < position.stop_loss:
                        return True, new_sl
        
        elif self.trailing_stop_config.strategy == TrailingStopStrategy.STEP_BASED:
            # Trailing stop oparty na krokach
            activation_distance = self.trailing_stop_config.activation_pips * pip_value
            step_distance = self.trailing_stop_config.step_pips * pip_value
            
            if position.order_type == 'buy':
                # Dla pozycji długich
                profit_distance = position.current_price - position.entry_price
                if profit_distance >= activation_distance:
                    # Obliczenie liczby kroków
                    steps = int(profit_distance / step_distance)
                    if steps > 0:
                        # Obliczenie nowego poziomu stop-loss
                        new_sl = position.entry_price + (steps - 1) * step_distance
                        # Sprawdzenie, czy nowy SL jest wyższy niż obecny
                        if new_sl > position.stop_loss:
                            return True, new_sl
            else:
                # Dla pozycji krótkich
                profit_distance = position.entry_price - position.current_price
                if profit_distance >= activation_distance:
                    # Obliczenie liczby kroków
                    steps = int(profit_distance / step_distance)
                    if steps > 0:
                        # Obliczenie nowego poziomu stop-loss
                        new_sl = position.entry_price - (steps - 1) * step_distance
                        # Sprawdzenie, czy nowy SL jest niższy niż obecny
                        if new_sl < position.stop_loss:
                            return True, new_sl
        
        # Dla pozostałych strategii lub jeśli nie ma potrzeby modyfikacji
        return False, None
    
    def process_positions(self) -> List[Dict]:
        """
        Przetwarzanie wszystkich śledzonych pozycji i sprawdzenie, czy należy zmodyfikować stop-lossy.
        
        Returns:
            List[Dict]: Lista słowników zawierających informacje o pozycjach do modyfikacji.
        """
        modifications = []
        
        for position_id, position in list(self.positions.items()):
            # Sprawdzenie trailing stop
            should_modify, new_stop_loss = self.check_trailing_stop(position_id)
            
            if should_modify and new_stop_loss is not None:
                # Zapisanie modyfikacji
                position.update_stop_loss(new_stop_loss, "trailing_stop")
                
                modifications.append({
                    'position_id': position_id,
                    'symbol': position.symbol,
                    'order_type': position.order_type,
                    'volume': position.volume,
                    'entry_price': position.entry_price,
                    'current_price': position.current_price,
                    'old_stop_loss': position.original_stop_loss,
                    'new_stop_loss': new_stop_loss,
                    'take_profit': position.take_profit,
                    'reason': "trailing_stop"
                })
                
                self.logger.info(
                    f"Modyfikacja SL dla pozycji {position_id} ({position.symbol}): "
                    f"{position.original_stop_loss} -> {new_stop_loss}, "
                    f"cena: {position.current_price}, zysk: {position.get_profit_in_pips():.1f} pips"
                )
        
        return modifications
    
    def lock_profits(self, position_id: int) -> Tuple[bool, Optional[float]]:
        """
        Przenosi stop-loss na poziom break-even lub wyżej, aby zabezpieczyć zysk.
        
        Args:
            position_id: Identyfikator pozycji.
        
        Returns:
            Tuple zawierający:
            - bool: Czy należy zmodyfikować stop-loss.
            - Optional[float]: Nowy poziom stop-loss lub None, jeśli nie ma potrzeby modyfikacji.
        """
        if position_id not in self.positions:
            return False, None
        
        position = self.positions[position_id]
        pip_value = position.pip_value
        
        # Obliczenie minimalnego zysku do zabezpieczenia (w pipsach)
        lock_profit_pips = self.trailing_stop_config.activation_pips
        
        # Zysk w pipsach
        profit_pips = position.get_profit_in_pips()
        
        if profit_pips >= lock_profit_pips:
            # Obliczenie nowego poziomu stop-loss
            if position.order_type == 'buy':
                # Dla pozycji długich
                # Ustaw SL na wejście + procent zysku
                lock_percent = self.trailing_stop_config.lock_profit_percent
                price_diff = position.current_price - position.entry_price
                new_sl = position.entry_price + (price_diff * lock_percent)
                
                # Sprawdzenie, czy nowy SL jest wyższy niż obecny
                if new_sl > position.stop_loss:
                    return True, new_sl
            else:
                # Dla pozycji krótkich
                # Ustaw SL na wejście - procent zysku
                lock_percent = self.trailing_stop_config.lock_profit_percent
                price_diff = position.entry_price - position.current_price
                new_sl = position.entry_price - (price_diff * lock_percent)
                
                # Sprawdzenie, czy nowy SL jest niższy niż obecny
                if new_sl < position.stop_loss:
                    return True, new_sl
        
        return False, None
    
    def get_position_status(self, position_id: int) -> Optional[Dict]:
        """
        Zwraca status śledzonej pozycji.
        
        Args:
            position_id: Identyfikator pozycji.
        
        Returns:
            Optional[Dict]: Status pozycji lub None, jeśli pozycja nie jest śledzona.
        """
        if position_id not in self.positions:
            return None
        
        position = self.positions[position_id]
        return position.to_dict()
    
    def get_all_positions_status(self) -> Dict[int, Dict]:
        """
        Zwraca statusy wszystkich śledzonych pozycji.
        
        Returns:
            Dict[int, Dict]: Słownik mapujący identyfikatory pozycji na ich statusy.
        """
        return {position_id: position.to_dict() for position_id, position in self.positions.items()}
    
    def set_support_resistance_levels(self, symbol: str, support_levels: List[float], resistance_levels: List[float]) -> None:
        """
        Ustawia poziomy wsparcia i oporu dla symbolu.
        
        Args:
            symbol: Symbol instrumentu.
            support_levels: Lista poziomów wsparcia.
            resistance_levels: Lista poziomów oporu.
        """
        self.support_resistance_levels[symbol] = {
            'support': sorted(support_levels),
            'resistance': sorted(resistance_levels)
        }
        self.logger.info(f"Ustawiono poziomy wsparcia/oporu dla {symbol}: {len(support_levels)} wsparć, {len(resistance_levels)} oporów")
    
    def register_atr_function(self, symbol: str, timeframe: str, atr_function) -> None:
        """
        Rejestruje funkcję do obliczania ATR dla symbolu i ramy czasowej.
        
        Args:
            symbol: Symbol instrumentu.
            timeframe: Rama czasowa.
            atr_function: Funkcja obliczająca ATR (przyjmuje symbol i timeframe, zwraca wartość ATR).
        """
        key = f"{symbol}_{timeframe}"
        self.atr_functions[key] = atr_function
        self.logger.info(f"Zarejestrowano funkcję ATR dla {symbol} na ramie czasowej {timeframe}")
    
    def get_atr_value(self, symbol: str, timeframe: str) -> Optional[float]:
        """
        Pobiera wartość ATR dla symbolu i ramy czasowej.
        
        Args:
            symbol: Symbol instrumentu.
            timeframe: Rama czasowa.
        
        Returns:
            Optional[float]: Wartość ATR lub None, jeśli funkcja nie jest zarejestrowana.
        """
        key = f"{symbol}_{timeframe}"
        if key in self.atr_functions:
            try:
                return self.atr_functions[key](symbol, timeframe)
            except Exception as e:
                self.logger.error(f"Błąd podczas pobierania ATR dla {symbol} na ramie czasowej {timeframe}: {e}")
                return None
        return None


# Utworzenie globalnej instancji StopLossManager
_stop_loss_manager = None

def get_stop_loss_manager() -> StopLossManager:
    """
    Zwraca globalną instancję StopLossManager.
    
    Returns:
        StopLossManager: Instancja menedżera stop-lossów.
    """
    global _stop_loss_manager
    if _stop_loss_manager is None:
        _stop_loss_manager = StopLossManager()
    return _stop_loss_manager 