#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Moduł śledzenia ekspozycji dla systemu AgentMT5.

Ten moduł zawiera klasy i funkcje odpowiedzialne za śledzenie ekspozycji
na ryzyko w różnych instrumentach i rynkach.
"""

import logging
import json
from typing import Dict, List, Optional, Set, Tuple, Union
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

from .risk_manager import RiskManager, RiskLevel, get_risk_manager


class ExposureTracker:
    """
    Klasa odpowiedzialna za śledzenie ekspozycji na ryzyko.
    
    Śledzi ekspozycję na różnych instrumentach, rynkach i w różnych kierunkach.
    Utrzymuje historyczne dane o ekspozycji i udostępnia metody do analizy
    i wizualizacji ekspozycji.
    """
    
    _instance = None
    
    def __new__(cls):
        """Implementacja wzorca Singleton."""
        if cls._instance is None:
            cls._instance = super(ExposureTracker, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """Inicjalizacja trackera ekspozycji."""
        if self._initialized:
            return
        
        self._initialized = True
        self.logger = logging.getLogger('trading_agent.risk_management.exposure_tracker')
        self.risk_manager = get_risk_manager()
        
        # Słowniki do śledzenia ekspozycji
        self.current_exposure = {}  # symbol -> wartość ekspozycji
        self.direction_exposure = {
            'buy': 0.0,  # Ekspozycja na pozycje długie
            'sell': 0.0   # Ekspozycja na pozycje krótkie
        }
        self.market_exposure = {
            'forex': 0.0,
            'stocks': 0.0,
            'commodities': 0.0,
            'indices': 0.0,
            'crypto': 0.0
        }
        
        # Macierz korelacji między symbolami
        self.correlation_matrix = {}
        
        # Historia ekspozycji
        self.exposure_history = []
        
        # Interwał zapisu historii ekspozycji (w minutach)
        self.history_interval_minutes = 60
        self.last_history_update = datetime.now()
        
        self.logger.info("Inicjalizacja ExposureTracker")
    
    def update_exposure(self, symbol: str, volume: float, price: float, 
                       order_type: str, operation: str) -> None:
        """
        Aktualizacja ekspozycji dla symbolu.
        
        Args:
            symbol: Symbol instrumentu.
            volume: Wolumen pozycji.
            price: Cena otwarcia/zamknięcia pozycji.
            order_type: Typ zlecenia ('buy', 'sell', itp.).
            operation: Rodzaj operacji ('add' lub 'remove').
        """
        # Obliczenie wartości ekspozycji
        exposure_value = volume * price
        
        # Aktualizacja ekspozycji dla symbolu
        if symbol not in self.current_exposure:
            self.current_exposure[symbol] = 0.0
        
        old_exposure = self.current_exposure[symbol]
        
        if operation == 'add':
            self.current_exposure[symbol] += exposure_value
        elif operation == 'remove':
            self.current_exposure[symbol] -= exposure_value
            # Zapewnienie, że ekspozycja nie jest ujemna
            if self.current_exposure[symbol] < 0:
                self.current_exposure[symbol] = 0.0
        
        # Aktualizacja ekspozycji dla kierunku
        direction = 'buy' if order_type.lower() in ['buy', 'buy_limit', 'buy_stop'] else 'sell'
        if operation == 'add':
            self.direction_exposure[direction] += exposure_value
        elif operation == 'remove':
            self.direction_exposure[direction] -= exposure_value
            # Zapewnienie, że ekspozycja nie jest ujemna
            if self.direction_exposure[direction] < 0:
                self.direction_exposure[direction] = 0.0
        
        # Aktualizacja ekspozycji dla rynku
        market = self._get_symbol_market(symbol)
        if operation == 'add':
            self.market_exposure[market] += exposure_value
        elif operation == 'remove':
            self.market_exposure[market] -= exposure_value
            # Zapewnienie, że ekspozycja nie jest ujemna
            if self.market_exposure[market] < 0:
                self.market_exposure[market] = 0.0
        
        # Aktualizacja u RiskManager
        self.risk_manager.update_exposure(symbol, volume, price, operation)
        
        # Zapisanie historii ekspozycji (raz na ustalony interwał)
        current_time = datetime.now()
        if (current_time - self.last_history_update).total_seconds() / 60 >= self.history_interval_minutes:
            self._update_exposure_history()
            self.last_history_update = current_time
        
        # Logowanie
        self.logger.debug(
            f"Zaktualizowano ekspozycję dla {symbol}: {old_exposure} -> {self.current_exposure[symbol]}, "
            f"operacja: {operation}, kierunek: {direction}"
        )
    
    def get_total_exposure(self) -> float:
        """
        Zwraca całkowitą ekspozycję na wszystkich symbolach.
        
        Returns:
            float: Całkowita ekspozycja.
        """
        return sum(self.current_exposure.values())
    
    def get_exposure_percent(self, symbol: Optional[str] = None) -> float:
        """
        Zwraca ekspozycję jako procent kapitału.
        
        Args:
            symbol: Symbol instrumentu (opcjonalnie, jeśli None, zwraca całkowitą ekspozycję).
        
        Returns:
            float: Ekspozycja jako procent kapitału.
        """
        if self.risk_manager.account_balance <= 0:
            return 0.0
        
        if symbol:
            exposure = self.current_exposure.get(symbol, 0.0)
        else:
            exposure = self.get_total_exposure()
        
        return (exposure / self.risk_manager.account_balance) * 100
    
    def get_risk_level(self, symbol: Optional[str] = None) -> RiskLevel:
        """
        Zwraca poziom ryzyka dla symbolu lub całkowitej ekspozycji.
        
        Args:
            symbol: Symbol instrumentu (opcjonalnie, jeśli None, zwraca ryzyko całkowitej ekspozycji).
        
        Returns:
            RiskLevel: Poziom ryzyka.
        """
        exposure_percent = self.get_exposure_percent(symbol)
        max_percent = self.risk_manager.parameters.max_exposure_per_symbol_percent if symbol else self.risk_manager.parameters.max_exposure_percent
        
        if exposure_percent >= max_percent:
            return RiskLevel.CRITICAL
        elif exposure_percent >= max_percent * 0.8:
            return RiskLevel.HIGH
        elif exposure_percent >= max_percent * 0.5:
            return RiskLevel.MEDIUM
        else:
            return RiskLevel.LOW
    
    def get_correlated_exposure(self, symbol: str) -> float:
        """
        Zwraca ekspozycję na wszystkie skorelowane instrumenty.
        
        Args:
            symbol: Symbol instrumentu.
        
        Returns:
            float: Ekspozycja na wszystkie skorelowane instrumenty.
        """
        # Jeśli nie mamy macierzy korelacji, zwróć tylko ekspozycję na dany symbol
        if not self.correlation_matrix:
            return self.current_exposure.get(symbol, 0.0)
        
        # Lista skorelowanych symboli (korelacja > 0.7)
        correlated_symbols = []
        for other_symbol in self.current_exposure:
            if symbol == other_symbol:
                continue
            
            # Sprawdzenie korelacji w obu kierunkach
            correlation_key = f"{symbol}_{other_symbol}"
            reverse_correlation_key = f"{other_symbol}_{symbol}"
            
            correlation = 0.0
            if correlation_key in self.correlation_matrix:
                correlation = self.correlation_matrix[correlation_key]
            elif reverse_correlation_key in self.correlation_matrix:
                correlation = self.correlation_matrix[reverse_correlation_key]
            
            if abs(correlation) > 0.7:
                correlated_symbols.append(other_symbol)
        
        # Suma ekspozycji na wszystkie skorelowane symbole
        total_correlated_exposure = self.current_exposure.get(symbol, 0.0)
        for corr_symbol in correlated_symbols:
            total_correlated_exposure += self.current_exposure.get(corr_symbol, 0.0)
        
        return total_correlated_exposure
    
    def update_correlation_matrix(self, correlation_data: Dict[str, float]) -> None:
        """
        Aktualizacja macierzy korelacji między symbolami.
        
        Args:
            correlation_data: Słownik zawierający dane o korelacji (klucz: "symbol1_symbol2", wartość: wartość korelacji).
        """
        self.correlation_matrix.update(correlation_data)
        self.logger.info(f"Zaktualizowano macierz korelacji: {len(correlation_data)} rekordów")
    
    def load_correlation_matrix(self, file_path: str) -> None:
        """
        Wczytanie macierzy korelacji z pliku JSON.
        
        Args:
            file_path: Ścieżka do pliku JSON z danymi o korelacji.
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                self.correlation_matrix = json.load(f)
            self.logger.info(f"Wczytano macierz korelacji z pliku {file_path}: {len(self.correlation_matrix)} rekordów")
        except Exception as e:
            self.logger.error(f"Błąd podczas wczytywania macierzy korelacji z pliku {file_path}: {e}")
    
    def save_correlation_matrix(self, file_path: str) -> None:
        """
        Zapisanie macierzy korelacji do pliku JSON.
        
        Args:
            file_path: Ścieżka do pliku JSON, w którym zostaną zapisane dane o korelacji.
        """
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(self.correlation_matrix, f, indent=2)
            self.logger.info(f"Zapisano macierz korelacji do pliku {file_path}: {len(self.correlation_matrix)} rekordów")
        except Exception as e:
            self.logger.error(f"Błąd podczas zapisywania macierzy korelacji do pliku {file_path}: {e}")
    
    def _get_symbol_market(self, symbol: str) -> str:
        """
        Określa typ rynku dla danego symbolu.
        
        Args:
            symbol: Symbol instrumentu.
        
        Returns:
            str: Typ rynku ('forex', 'stocks', 'commodities', 'indices', 'crypto').
        """
        # Waluty (Forex)
        forex_pairs = [
            'EURUSD', 'GBPUSD', 'USDJPY', 'AUDUSD', 'USDCHF', 'USDCAD', 'NZDUSD',
            'EURGBP', 'EURJPY', 'GBPJPY', 'AUDCAD', 'AUDNZD', 'AUDCHF', 'AUDSGD'
        ]
        if any(symbol.upper().startswith(pair) for pair in forex_pairs) or len(symbol) == 6 and symbol.isupper():
            return 'forex'
        
        # Surowce
        commodities = [
            'XAUUSD', 'XAGUSD', 'GOLD', 'SILVER', 'OIL', 'BRENT', 'NATGAS',
            'COPPER', 'PLATINUM', 'PALLADIUM'
        ]
        if any(commodity in symbol.upper() for commodity in commodities):
            return 'commodities'
        
        # Indeksy
        indices = [
            'US30', 'SPX500', 'NAS100', 'UK100', 'GER30', 'FRA40', 'JPN225',
            'AUS200', 'HK50', 'NIKKEI', 'DAX', 'FTSE'
        ]
        if any(index in symbol.upper() for index in indices):
            return 'indices'
        
        # Kryptowaluty
        crypto = [
            'BTCUSD', 'ETHUSD', 'LTCUSD', 'XRPUSD', 'BCHUSD', 'ADAUSD',
            'BTC', 'ETH', 'LTC', 'XRP', 'BCH', 'ADA'
        ]
        if any(crypto in symbol.upper() for crypto in crypto):
            return 'crypto'
        
        # Domyślnie zakładamy, że to akcje
        return 'stocks'
    
    def _update_exposure_history(self) -> None:
        """Zapisanie bieżącego stanu ekspozycji do historii."""
        current_time = datetime.now()
        
        # Stworzenie wpisu historii
        history_entry = {
            'timestamp': current_time.isoformat(),
            'total_exposure': self.get_total_exposure(),
            'exposure_percent': self.get_exposure_percent(),
            'symbol_exposure': self.current_exposure.copy(),
            'direction_exposure': self.direction_exposure.copy(),
            'market_exposure': self.market_exposure.copy(),
            'risk_level': self.get_risk_level().value
        }
        
        # Dodanie wpisu do historii
        self.exposure_history.append(history_entry)
        
        # Ograniczenie historii do ostatnich 7 dni
        cutoff_time = current_time - timedelta(days=7)
        self.exposure_history = [
            entry for entry in self.exposure_history
            if datetime.fromisoformat(entry['timestamp']) >= cutoff_time
        ]
    
    def get_exposure_report(self) -> Dict:
        """
        Generuje raport o aktualnej ekspozycji.
        
        Returns:
            Dict: Raport o ekspozycji.
        """
        total_exposure = self.get_total_exposure()
        exposure_percent = self.get_exposure_percent()
        
        return {
            'timestamp': datetime.now().isoformat(),
            'total_exposure': total_exposure,
            'exposure_percent': exposure_percent,
            'risk_level': self.get_risk_level().value,
            'symbol_exposure': {
                symbol: {
                    'value': exposure,
                    'percent': (exposure / self.risk_manager.account_balance) * 100 if self.risk_manager.account_balance > 0 else 0,
                    'risk_level': self.get_risk_level(symbol).value
                }
                for symbol, exposure in self.current_exposure.items()
            },
            'direction_exposure': {
                direction: {
                    'value': exposure,
                    'percent': (exposure / self.risk_manager.account_balance) * 100 if self.risk_manager.account_balance > 0 else 0
                }
                for direction, exposure in self.direction_exposure.items()
            },
            'market_exposure': {
                market: {
                    'value': exposure,
                    'percent': (exposure / self.risk_manager.account_balance) * 100 if self.risk_manager.account_balance > 0 else 0
                }
                for market, exposure in self.market_exposure.items()
            },
            'net_direction_exposure': self.direction_exposure['buy'] - self.direction_exposure['sell'],
            'net_direction_exposure_percent': 
                ((self.direction_exposure['buy'] - self.direction_exposure['sell']) / self.risk_manager.account_balance) * 100
                if self.risk_manager.account_balance > 0 else 0,
            'account_balance': self.risk_manager.account_balance,
            'account_equity': self.risk_manager.account_equity
        }
    
    def get_exposure_history_dataframe(self) -> pd.DataFrame:
        """
        Zwraca historię ekspozycji jako DataFrame.
        
        Returns:
            pd.DataFrame: Historia ekspozycji.
        """
        if not self.exposure_history:
            return pd.DataFrame()
        
        # Konwersja historii na DataFrame
        df = pd.DataFrame(self.exposure_history)
        
        # Konwersja timestampów na datetime
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        return df
    
    def get_potential_exposure_impact(self, symbol: str, volume: float, price: float, order_type: str) -> Dict:
        """
        Ocenia potencjalny wpływ nowego zlecenia na ekspozycję.
        
        Args:
            symbol: Symbol instrumentu.
            volume: Wolumen zlecenia.
            price: Cena zlecenia.
            order_type: Typ zlecenia ('buy', 'sell', itp.).
        
        Returns:
            Dict: Raport o potencjalnym wpływie.
        """
        # Obliczenie wartości nowej ekspozycji
        new_exposure_value = volume * price
        
        # Obliczenie procentowego wpływu na ekspozycję
        total_exposure = self.get_total_exposure()
        new_total_exposure = total_exposure + new_exposure_value
        
        # Aktualny i nowy procent ekspozycji
        current_exposure_percent = self.get_exposure_percent()
        if self.risk_manager.account_balance <= 0:
            new_exposure_percent = 0.0
        else:
            new_exposure_percent = (new_total_exposure / self.risk_manager.account_balance) * 100
        
        # Aktualny i nowy poziom ryzyka
        current_risk_level = self.get_risk_level()
        
        # Symulacja nowego poziomu ryzyka
        new_risk_level = current_risk_level
        if new_exposure_percent >= self.risk_manager.parameters.max_exposure_percent:
            new_risk_level = RiskLevel.CRITICAL
        elif new_exposure_percent >= self.risk_manager.parameters.max_exposure_percent * 0.8:
            new_risk_level = RiskLevel.HIGH
        elif new_exposure_percent >= self.risk_manager.parameters.max_exposure_percent * 0.5:
            new_risk_level = RiskLevel.MEDIUM
        else:
            new_risk_level = RiskLevel.LOW
        
        # Symulacja ekspozycji kierunkowej
        direction = 'buy' if order_type.lower() in ['buy', 'buy_limit', 'buy_stop'] else 'sell'
        new_direction_exposure = self.direction_exposure.copy()
        new_direction_exposure[direction] += new_exposure_value
        
        # Różnica netto między kierunkami (przed i po)
        current_net_direction = self.direction_exposure['buy'] - self.direction_exposure['sell']
        new_net_direction = new_direction_exposure['buy'] - new_direction_exposure['sell']
        
        return {
            'symbol': symbol,
            'new_exposure_value': new_exposure_value,
            'current_total_exposure': total_exposure,
            'new_total_exposure': new_total_exposure,
            'exposure_increase': new_exposure_value,
            'exposure_increase_percent': (new_exposure_value / total_exposure) * 100 if total_exposure > 0 else 100,
            'current_exposure_percent': current_exposure_percent,
            'new_exposure_percent': new_exposure_percent,
            'exposure_percent_increase': new_exposure_percent - current_exposure_percent,
            'current_risk_level': current_risk_level.value,
            'new_risk_level': new_risk_level.value,
            'risk_level_increased': new_risk_level.value != current_risk_level.value,
            'current_direction_balance': current_net_direction,
            'new_direction_balance': new_net_direction,
            'direction_balance_change': new_net_direction - current_net_direction,
            'would_exceed_limits': new_exposure_percent > self.risk_manager.parameters.max_exposure_percent
        }


# Utworzenie globalnej instancji ExposureTracker
_exposure_tracker = None

def get_exposure_tracker() -> ExposureTracker:
    """
    Zwraca globalną instancję ExposureTracker.
    
    Returns:
        ExposureTracker: Instancja trackera ekspozycji.
    """
    global _exposure_tracker
    if _exposure_tracker is None:
        _exposure_tracker = ExposureTracker()
    return _exposure_tracker 