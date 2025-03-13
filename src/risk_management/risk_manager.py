#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Moduł zarządzania ryzykiem dla systemu AgentMT5.

Ten moduł zawiera klasy i funkcje odpowiedzialne za zarządzanie ryzykiem w systemie tradingowym,
w tym walidację zleceń, limity pozycji, zarządzanie stop-lossami i śledzenie ekspozycji.
"""

import logging
import json
from datetime import datetime
from typing import Dict, List, Optional, Union, Tuple
from dataclasses import dataclass
from enum import Enum

# Konfiguracja loggera
logger = logging.getLogger('trading_agent.risk_management')


class RiskLevel(Enum):
    """Poziomy ryzyka dla różnych typów zabezpieczeń."""
    LOW = 'low'
    MEDIUM = 'medium'
    HIGH = 'high'
    CRITICAL = 'critical'


class OrderValidationResult(Enum):
    """Wyniki walidacji zleceń."""
    VALID = 'valid'
    INVALID_SYMBOL = 'invalid_symbol'
    INVALID_VOLUME = 'invalid_volume'
    INVALID_PRICE = 'invalid_price'
    INVALID_SL = 'invalid_stop_loss'
    INVALID_TP = 'invalid_take_profit'
    POSITION_LIMIT_EXCEEDED = 'position_limit_exceeded'
    EXPOSURE_LIMIT_EXCEEDED = 'exposure_limit_exceeded'
    RISK_REWARD_INVALID = 'risk_reward_invalid'
    OTHER_ERROR = 'other_error'


@dataclass
class RiskParameters:
    """Parametry zarządzania ryzykiem."""
    
    def __init__(self):
        # Parametry limitów pozycji
        self.max_positions_per_symbol = 1    # Maksymalna liczba pozycji na symbol
        self.max_positions_total = 3         # Maksymalna łączna liczba pozycji (zwiększamy do 3)
        
        # Parametry codziennego limitu strat
        self.daily_loss_limit_percent = 5.0  # Limit dziennej straty jako procent kapitału
        self.daily_loss_limit_absolute = 0.0 # Limit dziennej straty jako wartość absolutna (0 oznacza brak limitu)
        
        # Parametry wielkości pozycji
        self.max_lot_size = 0.1              # Maksymalny rozmiar lota
        self.base_lot_size = 0.01            # Podstawowy rozmiar lota
        self.position_sizing_method = 'fixed' # fixed, percent, kelly, martingale
        self.max_risk_per_trade_percent = 2.0 # Maksymalne ryzyko na transakcję jako procent kapitału
        self.position_size_percent = 5.0     # Maksymalny rozmiar pozycji jako procent kapitału
        
        # Parametry stosunku zysku do ryzyka
        self.min_risk_reward_ratio = 1.5     # Minimalny stosunek potencjalnego zysku do ryzyka
        self.target_risk_reward_ratio = 2.0  # Docelowy stosunek potencjalnego zysku do ryzyka
        
    def check_daily_loss_limit(self, current_balance, starting_balance):
        """Sprawdza, czy dzienny limit strat został przekroczony."""
        if starting_balance <= 0:
            return False
        
        loss_percent = (starting_balance - current_balance) / starting_balance * 100
        
        # Sprawdź procentowy limit strat
        if self.daily_loss_limit_percent > 0 and loss_percent >= self.daily_loss_limit_percent:
            return True
        
        # Sprawdź absolutny limit strat
        if self.daily_loss_limit_absolute > 0 and (starting_balance - current_balance) >= self.daily_loss_limit_absolute:
            return True
        
        return False
    
    def calculate_position_size(self, account_balance, risk_per_trade=None, price=None, stop_loss=None):
        """Oblicza wielkość pozycji na podstawie parametrów ryzyka."""
        if risk_per_trade is None:
            risk_per_trade = self.max_risk_per_trade_percent
        
        # Metoda stałej wielkości
        if self.position_sizing_method == 'fixed':
            return min(self.base_lot_size, self.max_lot_size)
        
        # Metoda procentowa
        elif self.position_sizing_method == 'percent':
            if price is None or stop_loss is None or price == stop_loss:
                return min(self.base_lot_size, self.max_lot_size)
            
            risk_amount = account_balance * (risk_per_trade / 100)
            pip_value = 10  # 10 USD per pip dla standardowego lota
            price_difference = abs(price - stop_loss)
            
            # Oblicz wielkość pozycji
            position_size = risk_amount / (price_difference * pip_value)
            
            # Ograniczenie do maks. wielkości pozycji
            return min(position_size, self.max_lot_size)
        
        # Domyślnie zwróć podstawową wielkość
        return min(self.base_lot_size, self.max_lot_size)
    
    def check_risk_reward_ratio(self, entry_price, stop_loss, take_profit):
        """Sprawdza, czy stosunek potencjalnego zysku do ryzyka jest akceptowalny."""
        if entry_price is None or stop_loss is None or take_profit is None:
            return False
        
        if entry_price == stop_loss or entry_price == take_profit:
            return False
        
        risk = abs(entry_price - stop_loss)
        reward = abs(entry_price - take_profit)
        
        if risk == 0:
            return False
        
        risk_reward_ratio = reward / risk
        
        return risk_reward_ratio >= self.min_risk_reward_ratio


class RiskManager:
    """
    Klasa zarządzająca ryzykiem w systemie tradingowym.
    
    Odpowiada za:
    - Walidację zleceń przed ich wykonaniem
    - Zarządzanie limitami pozycji
    - Zarządzanie stop-lossami
    - Śledzenie i kontrolę ekspozycji
    - Generowanie alertów o ryzyku
    """
    
    _instance = None
    
    def __new__(cls):
        """Implementacja wzorca Singleton."""
        if cls._instance is None:
            cls._instance = super(RiskManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """Inicjalizacja menedżera ryzyka."""
        if self._initialized:
            return
        
        self._initialized = True
        self.parameters = RiskParameters()
        self.current_exposure = {}
        self.position_counts = {}
        self.daily_pl = 0.0
        self.account_balance = 0.0
        self.account_equity = 0.0
        self.symbol_correlations = {}
        
        logger.info("Inicjalizacja RiskManager")
    
    def configure(self, parameters: Union[Dict, RiskParameters]) -> None:
        """
        Konfiguracja parametrów zarządzania ryzykiem.
        
        Args:
            parameters: Parametry ryzyka w postaci słownika lub instancji RiskParameters.
        """
        if isinstance(parameters, dict):
            for key, value in parameters.items():
                if hasattr(self.parameters, key):
                    setattr(self.parameters, key, value)
        else:
            self.parameters = parameters
        
        logger.info(f"Skonfigurowano parametry ryzyka: {self.parameters}")
    
    def load_configuration(self, config_file: str) -> None:
        """
        Wczytanie konfiguracji z pliku JSON.
        
        Args:
            config_file: Ścieżka do pliku konfiguracyjnego.
        """
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
                self.configure(config)
            logger.info(f"Wczytano konfigurację z pliku: {config_file}")
        except Exception as e:
            logger.error(f"Błąd podczas wczytywania konfiguracji z pliku {config_file}: {e}")
    
    def update_account_info(self, balance: float, equity: float) -> None:
        """
        Aktualizacja informacji o stanie konta.
        
        Args:
            balance: Saldo konta.
            equity: Kapitał własny konta.
        """
        self.account_balance = balance
        self.account_equity = equity
        
        # Resetowanie dziennego P/L o północy
        current_time = datetime.now()
        if current_time.hour == 0 and current_time.minute == 0:
            self.daily_pl = 0.0
            logger.info("Zresetowano dzienny P/L")
    
    def update_daily_pl(self, profit_loss: float) -> None:
        """
        Aktualizacja dziennego zysku/straty.
        
        Args:
            profit_loss: Wartość zysku lub straty do dodania.
        """
        self.daily_pl += profit_loss
        
        # Sprawdzenie limitu dziennej straty
        if self.daily_pl < 0 and abs(self.daily_pl) > (self.account_balance * self.parameters.daily_loss_limit_percent / 100):
            logger.warning(f"Przekroczony limit dziennej straty: {self.daily_pl}")
            # TODO: Implementacja akcji po przekroczeniu limitu dziennej straty
    
    def update_position_counts(self, symbol: str, count_change: int) -> None:
        """
        Aktualizacja liczby pozycji dla symbolu.
        
        Args:
            symbol: Symbol instrumentu.
            count_change: Zmiana liczby pozycji (+1 dla otwarcia, -1 dla zamknięcia).
        """
        if symbol not in self.position_counts:
            self.position_counts[symbol] = 0
        
        self.position_counts[symbol] += count_change
        
        # Zapewnienie, że liczba pozycji nie jest ujemna
        if self.position_counts[symbol] < 0:
            self.position_counts[symbol] = 0
    
    def update_exposure(self, symbol: str, volume: float, price: float, operation: str) -> None:
        """
        Aktualizacja ekspozycji dla symbolu.
        
        Args:
            symbol: Symbol instrumentu.
            volume: Wolumen pozycji.
            price: Cena otwarcia pozycji.
            operation: Rodzaj operacji ('add' lub 'remove').
        """
        exposure_value = volume * price
        
        if symbol not in self.current_exposure:
            self.current_exposure[symbol] = 0.0
        
        if operation == 'add':
            self.current_exposure[symbol] += exposure_value
        elif operation == 'remove':
            self.current_exposure[symbol] -= exposure_value
            
            # Zapewnienie, że ekspozycja nie jest ujemna
            if self.current_exposure[symbol] < 0:
                self.current_exposure[symbol] = 0.0
    
    def validate_order(self, order: Dict) -> Tuple[bool, OrderValidationResult, Optional[str]]:
        """
        Walidacja zlecenia przed jego wykonaniem.
        
        Args:
            order: Słownik zawierający parametry zlecenia.
        
        Returns:
            Tuple zawierające:
            - bool: Czy zlecenie jest poprawne.
            - OrderValidationResult: Wynik walidacji.
            - Optional[str]: Opcjonalny komunikat błędu.
        """
        symbol = order.get('symbol')
        volume = order.get('volume', 0.0)
        price = order.get('price', 0.0)
        sl = order.get('stop_loss')
        tp = order.get('take_profit')
        
        # Walidacja symbolu
        if not symbol or len(symbol) < 2:
            return False, OrderValidationResult.INVALID_SYMBOL, "Nieprawidłowy symbol"
        
        # Walidacja wolumenu
        if volume <= 0:
            return False, OrderValidationResult.INVALID_VOLUME, "Nieprawidłowy wolumen"
        
        # Walidacja ceny
        if price <= 0:
            return False, OrderValidationResult.INVALID_PRICE, "Nieprawidłowa cena"
        
        # Sprawdzenie limitu pozycji dla symbolu
        symbol_positions = self.position_counts.get(symbol, 0)
        if symbol_positions >= self.parameters.max_positions_per_symbol:
            return False, OrderValidationResult.POSITION_LIMIT_EXCEEDED, f"Przekroczony limit pozycji dla symbolu {symbol}"
        
        # Sprawdzenie całkowitego limitu pozycji
        total_positions = sum(self.position_counts.values())
        if total_positions >= self.parameters.max_positions_total:
            return False, OrderValidationResult.POSITION_LIMIT_EXCEEDED, "Przekroczony całkowity limit pozycji"
        
        # Sprawdzenie rozmiaru pozycji w stosunku do kapitału
        position_size_percent = (volume * price / self.account_balance) * 100
        if position_size_percent > self.parameters.position_size_percent:
            return False, OrderValidationResult.EXPOSURE_LIMIT_EXCEEDED, f"Rozmiar pozycji przekracza limit {self.parameters.position_size_percent}%"
        
        # Sprawdzenie ekspozycji dla symbolu
        symbol_exposure = self.current_exposure.get(symbol, 0) + (volume * price)
        symbol_exposure_percent = (symbol_exposure / self.account_balance) * 100
        if symbol_exposure_percent > self.parameters.max_exposure_per_symbol_percent:
            return False, OrderValidationResult.EXPOSURE_LIMIT_EXCEEDED, f"Ekspozycja dla {symbol} przekracza limit {self.parameters.max_exposure_per_symbol_percent}%"
        
        # Sprawdzenie całkowitej ekspozycji
        total_exposure = sum(self.current_exposure.values()) + (volume * price)
        total_exposure_percent = (total_exposure / self.account_balance) * 100
        if total_exposure_percent > self.parameters.max_exposure_percent:
            return False, OrderValidationResult.EXPOSURE_LIMIT_EXCEEDED, f"Całkowita ekspozycja przekracza limit {self.parameters.max_exposure_percent}%"
        
        # Sprawdzenie stop-lossa i take-profita
        if sl is not None and tp is not None:
            # Sprawdzenie kierunku
            if 'type' in order and order['type'] in ['buy', 'buy_limit', 'buy_stop']:
                # Dla pozycji długich (buy)
                if sl >= price:
                    return False, OrderValidationResult.INVALID_SL, "Stop-loss dla pozycji długiej musi być poniżej ceny wejścia"
                if tp <= price:
                    return False, OrderValidationResult.INVALID_TP, "Take-profit dla pozycji długiej musi być powyżej ceny wejścia"
                
                # Sprawdzenie stosunku zysk/ryzyko
                risk = price - sl
                reward = tp - price
                if risk > 0 and reward / risk < self.parameters.risk_reward_ratio:
                    return False, OrderValidationResult.RISK_REWARD_INVALID, f"Stosunek zysk/ryzyko poniżej minimum {self.parameters.risk_reward_ratio}"
            
            elif 'type' in order and order['type'] in ['sell', 'sell_limit', 'sell_stop']:
                # Dla pozycji krótkich (sell)
                if sl <= price:
                    return False, OrderValidationResult.INVALID_SL, "Stop-loss dla pozycji krótkiej musi być powyżej ceny wejścia"
                if tp >= price:
                    return False, OrderValidationResult.INVALID_TP, "Take-profit dla pozycji krótkiej musi być poniżej ceny wejścia"
                
                # Sprawdzenie stosunku zysk/ryzyko
                risk = sl - price
                reward = price - tp
                if risk > 0 and reward / risk < self.parameters.risk_reward_ratio:
                    return False, OrderValidationResult.RISK_REWARD_INVALID, f"Stosunek zysk/ryzyko poniżej minimum {self.parameters.risk_reward_ratio}"
        
        return True, OrderValidationResult.VALID, None
    
    def calculate_position_size(self, symbol: str, price: float, stop_loss: float, risk_percent: float) -> float:
        """
        Obliczenie optymalnego rozmiaru pozycji na podstawie ryzyka.
        
        Args:
            symbol: Symbol instrumentu.
            price: Cena wejścia.
            stop_loss: Poziom stop-loss.
            risk_percent: Procent kapitału do zaryzykowania.
        
        Returns:
            float: Optymalny rozmiar pozycji.
        """
        if price <= 0 or stop_loss <= 0:
            return 0.0
        
        # Maksymalna kwota do zaryzykowania
        risk_amount = self.account_balance * (risk_percent / 100)
        
        # Obliczenie różnicy między ceną wejścia a stop-lossem
        price_difference = abs(price - stop_loss)
        if price_difference == 0:
            return 0.0
        
        # Obliczenie rozmiaru pozycji
        position_size = risk_amount / price_difference
        
        # Limitowanie rozmiaru pozycji do maksymalnego dozwolonego procentu
        max_position_size = (self.account_balance * self.parameters.position_size_percent / 100) / price
        if position_size > max_position_size:
            position_size = max_position_size
        
        return position_size
    
    def calculate_stop_loss_level(self, symbol: str, order_type: str, entry_price: float, atr_value: Optional[float] = None) -> float:
        """
        Obliczenie optymalnego poziomu stop-loss na podstawie ATR lub domyślnych wartości.
        
        Args:
            symbol: Symbol instrumentu.
            order_type: Typ zlecenia ('buy' lub 'sell').
            entry_price: Cena wejścia.
            atr_value: Wartość Average True Range (opcjonalnie).
        
        Returns:
            float: Poziom stop-loss.
        """
        # Domyślna wartość w pipsach
        default_pips = self.parameters.stop_loss_percent * 100
        
        # Konwersja pipsów na punkty cenowe (zależy od instrumentu)
        pip_value = 0.0001  # Domyślna wartość dla par FOREX (może wymagać dostosowania dla innych instrumentów)
        if symbol.endswith('JPY'):
            pip_value = 0.01
        
        # Obliczenie poziomu stop-loss
        if atr_value:
            # Jeśli podano ATR, użyj go do obliczenia stop-loss (zazwyczaj 1.5-2.5 * ATR)
            sl_distance = 2.0 * atr_value
        else:
            # W przeciwnym razie użyj domyślnej wartości
            sl_distance = default_pips * pip_value
        
        # Poziom stop-loss zależy od typu zlecenia
        if order_type.lower() in ['buy', 'buy_limit', 'buy_stop']:
            stop_loss = entry_price - sl_distance
        else:
            stop_loss = entry_price + sl_distance
        
        return stop_loss
    
    def calculate_take_profit_level(self, symbol: str, order_type: str, entry_price: float, stop_loss: float) -> float:
        """
        Obliczenie optymalnego poziomu take-profit na podstawie poziomu stop-loss i wymaganego stosunku zysk/ryzyko.
        
        Args:
            symbol: Symbol instrumentu.
            order_type: Typ zlecenia ('buy' lub 'sell').
            entry_price: Cena wejścia.
            stop_loss: Poziom stop-loss.
        
        Returns:
            float: Poziom take-profit.
        """
        # Wymagany stosunek zysk/ryzyko
        risk_reward_ratio = self.parameters.risk_reward_ratio
        
        # Obliczenie różnicy między ceną wejścia a stop-lossem
        risk_distance = abs(entry_price - stop_loss)
        
        # Obliczenie poziomu take-profit
        if order_type.lower() in ['buy', 'buy_limit', 'buy_stop']:
            take_profit = entry_price + (risk_distance * risk_reward_ratio)
        else:
            take_profit = entry_price - (risk_distance * risk_reward_ratio)
        
        return take_profit
    
    def should_adjust_trailing_stop(self, symbol: str, order_type: str, entry_price: float, 
                                   current_price: float, current_sl: float) -> Tuple[bool, Optional[float]]:
        """
        Sprawdza, czy należy dostosować trailing stop i oblicza nowy poziom.
        
        Args:
            symbol: Symbol instrumentu.
            order_type: Typ zlecenia ('buy' lub 'sell').
            entry_price: Cena wejścia.
            current_price: Aktualna cena rynkowa.
            current_sl: Aktualny poziom stop-loss.
        
        Returns:
            Tuple zawierający:
            - bool: Czy należy dostosować trailing stop.
            - Optional[float]: Nowy poziom stop-loss (lub None, jeśli nie trzeba dostosować).
        """
        # Konwersja pipsów na punkty cenowe
        pip_value = 0.0001
        if symbol.endswith('JPY'):
            pip_value = 0.01
        
        # Minimalna aktywacja trailing stop w punktach cenowych
        activation_distance = self.parameters.max_correlated_symbols_exposure_percent * pip_value
        
        if order_type.lower() in ['buy', 'buy_limit', 'buy_stop']:
            # Dla pozycji długich (buy)
            profit_distance = current_price - entry_price
            if profit_distance >= activation_distance:
                # Obliczenie nowego poziomu stop-loss
                new_sl = current_price - activation_distance
                # Sprawdzenie, czy nowy SL jest wyższy niż obecny
                if new_sl > current_sl:
                    return True, new_sl
        else:
            # Dla pozycji krótkich (sell)
            profit_distance = entry_price - current_price
            if profit_distance >= activation_distance:
                # Obliczenie nowego poziomu stop-loss
                new_sl = current_price + activation_distance
                # Sprawdzenie, czy nowy SL jest niższy niż obecny
                if new_sl < current_sl:
                    return True, new_sl
        
        return False, None
    
    def get_exposure_risk_level(self) -> RiskLevel:
        """
        Określa poziom ryzyka na podstawie aktualnej ekspozycji.
        
        Returns:
            RiskLevel: Poziom ryzyka.
        """
        if not self.account_balance:
            return RiskLevel.LOW
        
        total_exposure = sum(self.current_exposure.values())
        exposure_percent = (total_exposure / self.account_balance) * 100
        
        if exposure_percent >= self.parameters.max_exposure_percent:
            return RiskLevel.CRITICAL
        elif exposure_percent >= self.parameters.max_exposure_percent * 0.8:
            return RiskLevel.HIGH
        elif exposure_percent >= self.parameters.max_exposure_percent * 0.5:
            return RiskLevel.MEDIUM
        else:
            return RiskLevel.LOW
    
    def get_risk_report(self) -> Dict:
        """
        Generuje raport o aktualnym stanie ryzyka.
        
        Returns:
            Dict: Raport o ryzyku.
        """
        total_exposure = sum(self.current_exposure.values())
        exposure_percent = (total_exposure / self.account_balance) * 100 if self.account_balance else 0
        
        total_positions = sum(self.position_counts.values())
        
        return {
            'timestamp': datetime.now().isoformat(),
            'account_balance': self.account_balance,
            'account_equity': self.account_equity,
            'daily_pl': self.daily_pl,
            'daily_pl_percent': (self.daily_pl / self.account_balance) * 100 if self.account_balance else 0,
            'total_positions': total_positions,
            'position_counts': self.position_counts,
            'total_exposure': total_exposure,
            'exposure_percent': exposure_percent,
            'exposure_by_symbol': {symbol: exposure for symbol, exposure in self.current_exposure.items()},
            'exposure_percent_by_symbol': {
                symbol: (exposure / self.account_balance) * 100 if self.account_balance else 0
                for symbol, exposure in self.current_exposure.items()
            },
            'risk_level': self.get_exposure_risk_level().value,
            'max_positions_per_symbol': self.parameters.max_positions_per_symbol,
            'max_positions_total': self.parameters.max_positions_total,
            'daily_loss_limit_percent': self.parameters.daily_loss_limit_percent,
            'daily_loss_limit_absolute': self.parameters.daily_loss_limit_absolute,
            'position_size_percent': self.parameters.position_size_percent,
            'position_size_fixed': self.parameters.position_size_fixed,
            'risk_reward_ratio': self.parameters.risk_reward_ratio,
            'stop_loss_percent': self.parameters.stop_loss_percent,
            'take_profit_percent': self.parameters.take_profit_percent,
            'max_exposure_percent': self.parameters.max_exposure_percent,
            'max_exposure_per_symbol_percent': self.parameters.max_exposure_per_symbol_percent,
            'max_correlated_symbols_exposure_percent': self.parameters.max_correlated_symbols_exposure_percent
        }
    
    def validate_signal(self, signal: Dict) -> Dict:
        """
        Walidacja sygnału handlowego pod kątem ryzyka.
        
        Args:
            signal: Słownik zawierający parametry sygnału.
            
        Returns:
            Dict zawierający wynik walidacji:
            - valid: Czy sygnał jest poprawny z punktu widzenia zarządzania ryzykiem.
            - reason: Opcjonalny powód odrzucenia sygnału.
            - risk_assessment: Dane o ocenie ryzyka.
        """
        # Sprawdzamy, czy mamy wszystkie potrzebne dane
        if not signal:
            return {'valid': False, 'reason': 'Brak danych sygnału'}
            
        symbol = signal.get('symbol')
        signal_type = signal.get('type')
        price = signal.get('price', 0.0)
        confidence = signal.get('confidence', 0.0)
        
        # Walidacja podstawowych parametrów
        if not symbol:
            return {'valid': False, 'reason': 'Brak symbolu instrumentu'}
            
        if not signal_type:
            return {'valid': False, 'reason': 'Brak typu sygnału'}
            
        if price <= 0:
            return {'valid': False, 'reason': f'Nieprawidłowa cena: {price}'}
            
        # Sprawdzenie limitów pozycji dla symbolu
        symbol_positions = self.position_counts.get(symbol, 0)
        if symbol_positions >= self.parameters.max_positions_per_symbol:
            return {
                'valid': False, 
                'reason': f'Przekroczony limit pozycji dla {symbol}: {symbol_positions}/{self.parameters.max_positions_per_symbol}'
            }
        
        # Sprawdzenie całkowitego limitu pozycji
        total_positions = sum(self.position_counts.values())
        if total_positions >= self.parameters.max_positions_total:
            return {
                'valid': False, 
                'reason': f'Przekroczony całkowity limit pozycji: {total_positions}/{self.parameters.max_positions_total}'
            }
            
        # Sprawdzenie ekspozycji dla symbolu
        # Zakładamy, że sygnał będzie realizowany z pewnym wolumenem, więc sprawdzamy tylko istniejącą ekspozycję
        symbol_exposure_percent = 0
        if self.account_balance > 0:
            symbol_exposure = self.current_exposure.get(symbol, 0)
            symbol_exposure_percent = (symbol_exposure / self.account_balance) * 100
            
        if symbol_exposure_percent > self.parameters.max_exposure_per_symbol_percent:
            return {
                'valid': False, 
                'reason': f'Przekroczony limit ekspozycji dla {symbol}: {symbol_exposure_percent:.2f}%/{self.parameters.max_exposure_per_symbol_percent:.2f}%'
            }
            
        # Sprawdzenie całkowitej ekspozycji
        total_exposure_percent = 0
        if self.account_balance > 0:
            total_exposure = sum(self.current_exposure.values())
            total_exposure_percent = (total_exposure / self.account_balance) * 100
            
        if total_exposure_percent > self.parameters.max_exposure_percent:
            return {
                'valid': False, 
                'reason': f'Przekroczony całkowity limit ekspozycji: {total_exposure_percent:.2f}%/{self.parameters.max_exposure_percent:.2f}%'
            }
            
        # Zwracamy pozytywny wynik walidacji
        return {
            'valid': True,
            'risk_assessment': {
                'symbol_positions': symbol_positions,
                'total_positions': total_positions,
                'symbol_exposure_percent': symbol_exposure_percent,
                'total_exposure_percent': total_exposure_percent,
                'risk_level': self.get_exposure_risk_level().value
            }
        }


# Funkcja do tworzenia instancji menedżera ryzyka
def get_risk_manager() -> RiskManager:
    """
    Zwraca instancję menedżera ryzyka (Singleton).
    
    Returns:
        RiskManager: Instancja menedżera ryzyka.
    """
    return RiskManager() 