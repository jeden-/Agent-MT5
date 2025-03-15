#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Moduł odpowiedzialny za połączenie z platformą MetaTrader 5.
"""

import os
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, Union
import numpy as np
import pandas as pd
from dotenv import load_dotenv
import threading

# Import biblioteki MetaTrader5
try:
    import MetaTrader5 as mt5
except ImportError:
    raise ImportError("Biblioteka MetaTrader5 nie jest zainstalowana. Zainstaluj ją używając: pip install MetaTrader5")

# Ustawienie loggera
logger = logging.getLogger('trading_agent.mt5_bridge')


class MT5Connector:
    """Klasa odpowiedzialna za połączenie z platformą MetaTrader 5."""
    
    # Singleton - jedno połączenie z MT5
    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(MT5Connector, cls).__new__(cls)
                # Flaga inicjalizacji
                cls._instance._initialized = False
            return cls._instance
    
    def __init__(self):
        """Inicjalizacja konektora MT5."""
        if self._initialized:
            return
        
        # Wczytanie zmiennych środowiskowych
        load_dotenv()
        
        # Parametry połączenia
        self._login = int(os.getenv('MT5_LOGIN', '0'))
        self._password = os.getenv('MT5_PASSWORD', '')
        self._server = os.getenv('MT5_SERVER', '')
        self._path = os.getenv('MT5_PATH', '')
        
        # Maksymalna liczba prób połączenia
        self._max_retries = 3
        self._retry_interval = 5  # sekundy
        
        # Status połączenia
        self._connected = False
        self._initialized = True
        
        # Bufor danych rynkowych i pozycji - dla poprawy wydajności
        self._market_data_cache = {}
        self._positions_cache = None
        self._orders_cache = None
        self._account_info_cache = None
        
        # Czasy ostatniego odświeżenia buforów
        self._market_data_cache_time = {}
        self._positions_cache_time = None
        self._orders_cache_time = None
        self._account_info_cache_time = None
        
        # Maksymalny czas ważności buforowanych danych (w sekundach)
        self._market_data_cache_ttl = 1  # 1 sekunda dla danych rynkowych
        self._positions_cache_ttl = 2  # 2 sekundy dla pozycji
        self._orders_cache_ttl = 2  # 2 sekundy dla zleceń
        self._account_info_cache_ttl = 5  # 5 sekund dla informacji o koncie
        
        # Mechanizm wsadowego przetwarzania danych
        self._batch_commands = []
        self._batch_lock = threading.Lock()
        self._batch_processing = False
        self._batch_interval = 0.5  # 500ms
        self._batch_thread = None
        
        logger.info(f"MT5Connector zainicjalizowany dla użytkownika {self._login} na serwerze {self._server}")
    
    def connect(self) -> bool:
        """
        Nawiązanie połączenia z platformą MT5.
        
        Returns:
            bool: True jeśli połączenie zostało nawiązane, False w przeciwnym razie.
        """
        if self._connected:
            logger.debug("Już połączono z platformą MT5")
            return True
        
        # Inicjalizacja MT5
        if not mt5.initialize(
            login=self._login,
            password=self._password,
            server=self._server,
            path=self._path
        ):
            error = mt5.last_error()
            logger.error(f"Nie można zainicjalizować MT5: {error}")
            return False
        
        # Sprawdzenie połączenia
        account_info = mt5.account_info()
        if account_info is None:
            error = mt5.last_error()
            logger.error(f"Nie można pobrać informacji o koncie: {error}")
            mt5.shutdown()
            return False
        
        self._connected = True
        logger.info(f"Połączono z platformą MT5. Konto: {account_info.login}, Saldo: {account_info.balance}")
        return True
    
    def disconnect(self) -> bool:
        """
        Zamknięcie połączenia z platformą MT5.
        
        Returns:
            bool: True jeśli połączenie zostało zamknięte, False w przeciwnym razie.
        """
        if not self._connected:
            logger.debug("Nie jesteś połączony z platformą MT5")
            return True
        
        # Zamknięcie MT5
        result = mt5.shutdown()
        if result:
            self._connected = False
            logger.info("Połączenie z platformą MT5 zostało zamknięte")
        else:
            error = mt5.last_error()
            logger.error(f"Nie można zamknąć połączenia z MT5: {error}")
        
        return result
    
    def ensure_connection(func):
        """
        Dekorator zapewniający połączenie z MT5 przed wykonaniem funkcji.
        """
        def wrapper(self, *args, **kwargs):
            if not self._connected:
                if not self.connect():
                    logger.error("Nie można wykonać operacji MT5 - brak połączenia")
                    return None
            return func(self, *args, **kwargs)
        return wrapper
    
    @ensure_connection
    def get_account_info(self) -> Optional[Dict[str, Any]]:
        """
        Pobranie informacji o koncie.
        
        Returns:
            Dict[str, Any]: Informacje o koncie lub None w przypadku błędu.
        """
        # Sprawdź bufor informacji o koncie
        now = datetime.now()
        if (self._account_info_cache is not None and self._account_info_cache_time is not None and
                (now - self._account_info_cache_time).total_seconds() < self._account_info_cache_ttl):
            return self._account_info_cache
            
        account_info = mt5.account_info()
        if account_info is None:
            error = mt5.last_error()
            logger.error(f"Nie można pobrać informacji o koncie: {error}")
            return None
        
        # Konwersja z namedtuple na słownik
        account_info_dict = {
            'login': account_info.login,
            'balance': account_info.balance,
            'equity': account_info.equity,
            'margin': account_info.margin,
            'margin_free': account_info.margin_free,
            'margin_level': account_info.margin_level,
            'currency': account_info.currency
        }
        
        # Aktualizacja bufora
        self._account_info_cache = account_info_dict
        self._account_info_cache_time = now
        
        return account_info_dict
    
    def _map_symbol(self, symbol: str) -> str:
        """
        Mapuje nazwę symbolu na format używany w MT5.
        
        Args:
            symbol: Nazwa symbolu (np. "GOLD").
            
        Returns:
            str: Nazwa symbolu w formacie MT5 (np. "GOLD.pro").
        """
        # Słownik mapowania symboli
        symbol_mapping = {
            "GOLD": "GOLD.pro",
            "SILVER": "SILVER.pro",
            "US100": "US100.pro",
            "EURUSD": "EURUSD.pro",
            "GBPUSD": "GBPUSD.pro"
        }
        
        # Jeśli symbol już ma sufiks ".pro", nie zmieniamy go
        if ".pro" in symbol:
            return symbol
        
        # Zwróć zmapowany symbol lub oryginalny, jeśli nie ma w mapowaniu
        return symbol_mapping.get(symbol, symbol)
    
    @ensure_connection
    def get_symbol_info(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Pobranie informacji o symbolu.
        
        Args:
            symbol: Symbol instrumentu (np. "EURUSD").
            
        Returns:
            Dict[str, Any]: Informacje o symbolu lub None w przypadku błędu.
        """
        # Mapuj symbol na format MT5
        mapped_symbol = self._map_symbol(symbol)
        
        # Sprawdź bufor danych rynkowych
        now = datetime.now()
        if (mapped_symbol in self._market_data_cache and mapped_symbol in self._market_data_cache_time and
                (now - self._market_data_cache_time[mapped_symbol]).total_seconds() < self._market_data_cache_ttl):
            return self._market_data_cache[mapped_symbol]
        
        # Pobierz dane z MT5
        symbol_info = mt5.symbol_info(mapped_symbol)
        if symbol_info is None:
            error = mt5.last_error()
            logger.error(f"Nie można pobrać informacji o symbolu {symbol} (zmapowany na {mapped_symbol}): {error}")
            return None
        
        # Konwersja z namedtuple na słownik
        symbol_info_dict = {
            'symbol': symbol,  # Używamy oryginalnej nazwy symbolu, nie zmapowanej
            'bid': symbol_info.bid,
            'ask': symbol_info.ask,
            'point': symbol_info.point,
            'digits': symbol_info.digits,
            'volume_min': symbol_info.volume_min,
            'volume_max': symbol_info.volume_max,
            'volume_step': symbol_info.volume_step
        }
        
        # Aktualizacja bufora
        self._market_data_cache[mapped_symbol] = symbol_info_dict
        self._market_data_cache_time[mapped_symbol] = now
        
        return symbol_info_dict
    
    @ensure_connection
    def get_historical_data(self, 
                          symbol: str,
                          timeframe: str,
                          start_time: datetime,
                          end_time: datetime,
                          count: int = 100000) -> Optional[pd.DataFrame]:
        """
        Pobiera dane historyczne dla danego symbolu i timeframe'u.
        
        Args:
            symbol: Symbol instrumentu (np. "EURUSD")
            timeframe: Przedział czasowy ("M1", "M5", "M15", "M30", "H1", "H4", "D1", "W1", "MN1")
            start_time: Data i czas początkowy
            end_time: Data i czas końcowy
            count: Maksymalna liczba rekordów do pobrania
            
        Returns:
            DataFrame z danymi historycznymi lub None w przypadku błędu
        """
        logger.info(f"Pobieranie danych historycznych dla {symbol} {timeframe} od {start_time} do {end_time}")
        
        # Mapowanie timeframe na stałe MT5
        timeframe_map = {
            "M1": mt5.TIMEFRAME_M1,
            "M5": mt5.TIMEFRAME_M5,
            "M15": mt5.TIMEFRAME_M15,
            "M30": mt5.TIMEFRAME_M30,
            "H1": mt5.TIMEFRAME_H1,
            "H4": mt5.TIMEFRAME_H4,
            "D1": mt5.TIMEFRAME_D1,
            "W1": mt5.TIMEFRAME_W1,
            "MN1": mt5.TIMEFRAME_MN1
        }
        
        if timeframe not in timeframe_map:
            logger.error(f"Nieprawidłowy timeframe: {timeframe}. Dostępne: {list(timeframe_map.keys())}")
            return None
        
        # Mapowanie symbolu
        mapped_symbol = self._map_symbol(symbol)
        
        # Sprawdzenie i wybór symbolu
        if not mt5.symbol_select(mapped_symbol, True):
            logger.error(f"Nie można wybrać symbolu {mapped_symbol}: {mt5.last_error()}")
            return None
        
        try:
            # Pobieranie danych z MT5
            mt5_timeframe = timeframe_map[timeframe]
            
            # Konwersja dat na format Unix timestamp
            if isinstance(start_time, datetime):
                start_timestamp = int(start_time.timestamp())
            else:
                start_timestamp = int(pd.Timestamp(start_time).timestamp())
                
            if isinstance(end_time, datetime):
                end_timestamp = int(end_time.timestamp())
            else:
                end_timestamp = int(pd.Timestamp(end_time).timestamp())
            
            # Pobieranie danych metodą copy_rates_range
            rates = mt5.copy_rates_range(mapped_symbol, mt5_timeframe, start_timestamp, end_timestamp)
            
            if rates is None or len(rates) == 0:
                logger.warning(f"Brak danych dla {mapped_symbol} {timeframe} w okresie od {start_time} do {end_time}")
                
                # Próba alternatywnej metody pobierania - ostatnich N słupków
                logger.info(f"Próba alternatywnego pobierania ostatnich {count} słupków...")
                rates = mt5.copy_rates_from_pos(mapped_symbol, mt5_timeframe, 0, min(count, 100000))
                
                if rates is None or len(rates) == 0:
                    logger.error(f"Nie można pobrać danych historycznych dla {mapped_symbol}: {mt5.last_error()}")
                    return None
            
            # Konwersja na DataFrame
            df = pd.DataFrame(rates)
            
            # Konwersja czasu z timestampu na datetime
            if 'time' in df.columns:
                df['time'] = pd.to_datetime(df['time'], unit='s')
            
            # Filtracja danych do zadanego zakresu
            if 'time' in df.columns:
                df = df[(df['time'] >= pd.Timestamp(start_time)) & 
                         (df['time'] <= pd.Timestamp(end_time))]
            
            if df.empty:
                logger.warning(f"Brak danych po filtrowaniu dla {mapped_symbol} {timeframe}")
                return None
            
            logger.info(f"Pobrano {len(df)} rekordów dla {mapped_symbol} {timeframe}")
            return df
            
        except Exception as e:
            logger.error(f"Błąd podczas pobierania danych historycznych: {e}")
            return None
    
    @ensure_connection
    def get_positions(self) -> Optional[List[Dict[str, Any]]]:
        """
        Pobranie aktualnych pozycji.
        
        Returns:
            List[Dict[str, Any]]: Lista aktualnych pozycji lub None w przypadku błędu.
        """
        # Sprawdź bufor pozycji
        now = datetime.now()
        if (self._positions_cache is not None and self._positions_cache_time is not None and
                (now - self._positions_cache_time).total_seconds() < self._positions_cache_ttl):
            return self._positions_cache
            
        # Pobierz dane z MT5
        positions = mt5.positions_get()
        if positions is None:
            error = mt5.last_error()
            if error[0] == 0:  # Brak pozycji (to nie jest błąd)
                return []
            logger.error(f"Nie można pobrać pozycji: {error}")
            return None
        
        # Słownik do odwrotnego mapowania symboli (z SYMBOL.pro na SYMBOL)
        reverse_symbol_mapping = {
            "GOLD.pro": "GOLD",
            "SILVER.pro": "SILVER",
            "US100.pro": "US100",
            "EURUSD.pro": "EURUSD",
            "GBPUSD.pro": "GBPUSD"
        }
        
        # Konwersja pozycji na listę słowników
        positions_list = []
        for position in positions:
            # Odwrotne mapowanie symbolu (z platformy MT5 do nazwy używanej w agencie)
            symbol = position.symbol
            if symbol in reverse_symbol_mapping:
                symbol = reverse_symbol_mapping[symbol]
                
            position_dict = {
                'ticket': position.ticket,
                'symbol': symbol,  # Używamy odwrotnie zmapowanej nazwy symbolu
                'type': 'buy' if position.type == 0 else 'sell',
                'volume': position.volume,
                'open_price': position.price_open,
                'current_price': position.price_current,
                'sl': position.sl,
                'tp': position.tp,
                'profit': position.profit,
                'comment': position.comment,
                'magic': position.magic,
                'open_time': datetime.fromtimestamp(position.time)
            }
            positions_list.append(position_dict)
        
        # Aktualizacja bufora
        self._positions_cache = positions_list
        self._positions_cache_time = now
        
        return positions_list
    
    @ensure_connection
    def get_orders(self) -> Optional[List[Dict[str, Any]]]:
        """
        Pobranie oczekujących zleceń.
        
        Returns:
            List[Dict[str, Any]]: Lista oczekujących zleceń lub None w przypadku błędu.
        """
        # Sprawdź bufor zleceń
        now = datetime.now()
        if (self._orders_cache is not None and self._orders_cache_time is not None and
                (now - self._orders_cache_time).total_seconds() < self._orders_cache_ttl):
            return self._orders_cache
            
        # Pobierz dane z MT5
        orders = mt5.orders_get()
        if orders is None:
            error = mt5.last_error()
            if error[0] == 0:  # Brak zleceń (to nie jest błąd)
                return []
            logger.error(f"Nie można pobrać zleceń: {error}")
            return None
        
        # Konwersja zleceń na listę słowników
        orders_list = []
        for order in orders:
            order_dict = {
                'ticket': order.ticket,
                'symbol': order.symbol,
                'type': order.type,
                'volume': order.volume_initial,
                'price': order.price_open,
                'sl': order.sl,
                'tp': order.tp,
                'comment': order.comment,
                'magic': order.magic,
                'time_setup': datetime.fromtimestamp(order.time_setup)
            }
            orders_list.append(order_dict)
        
        # Aktualizacja bufora
        self._orders_cache = orders_list
        self._orders_cache_time = now
        
        return orders_list
    
    @ensure_connection
    def open_order(
        self, 
        symbol: str, 
        order_type: str, 
        volume: float, 
        price: Optional[float] = None, 
        sl: Optional[float] = None, 
        tp: Optional[float] = None, 
        comment: str = "", 
        magic: int = 0
    ) -> Optional[Dict[str, Any]]:
        """
        Otwarcie zlecenia.
        
        Args:
            symbol: Symbol instrumentu (np. "EURUSD").
            order_type: Typ zlecenia ("buy" lub "sell").
            volume: Wielkość pozycji.
            price: Cena otwarcia (opcjonalnie - dla zleceń oczekujących).
            sl: Poziom Stop Loss (opcjonalnie).
            tp: Poziom Take Profit (opcjonalnie).
            comment: Komentarz do zlecenia (opcjonalnie).
            magic: Numer magiczny (opcjonalnie).
            
        Returns:
            Dict[str, Any]: Informacje o zleceniu lub None w przypadku błędu.
        """
        # Mapuj symbol na format MT5
        mapped_symbol = self._map_symbol(symbol)
        
        # Sprawdź, czy symbol jest dostępny
        symbol_info = mt5.symbol_info(mapped_symbol)
        if symbol_info is None:
            error = mt5.last_error()
            logger.error(f"Nie można pobrać informacji o symbolu {symbol} (zmapowany na {mapped_symbol}): {error}")
            return None
            
        # Sprawdź, czy symbol jest dostępny do handlu
        if not symbol_info.visible:
            logger.error(f"Symbol {symbol} (zmapowany na {mapped_symbol}) nie jest widoczny, próba włączenia...")
            if not mt5.symbol_select(mapped_symbol, True):
                error = mt5.last_error()
                logger.error(f"Nie można wybrać symbolu {symbol} (zmapowany na {mapped_symbol}): {error}")
                return None
        
        # Określenie ceny dla zleceń rynkowych
        if order_type.lower() == 'buy' and not price:
            price = mt5.symbol_info_tick(mapped_symbol).ask
            mt5_order_type = mt5.ORDER_TYPE_BUY
        elif order_type.lower() == 'sell' and not price:
            price = mt5.symbol_info_tick(mapped_symbol).bid
            mt5_order_type = mt5.ORDER_TYPE_SELL
        else:
            logger.error(f"Nieobsługiwany typ zlecenia: {order_type}")
            return None
        
        # Zaokrąglenie ceny do odpowiedniej liczby miejsc po przecinku
        digits = symbol_info.digits
        if price:
            price = round(price, digits)
        if sl:
            sl = round(sl, digits)
        if tp:
            tp = round(tp, digits)
        
        # Przygotowanie żądania
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": mapped_symbol,
            "volume": volume,
            "type": mt5_order_type,
            "price": price,
            "sl": sl,
            "tp": tp,
            "comment": comment,
            "magic": magic,
            "type_time": mt5.ORDER_TIME_GTC,  # Good Till Cancelled
            "type_filling": mt5.ORDER_FILLING_FOK,  # Fill Or Kill
        }
        
        # Wysłanie żądania
        result = mt5.order_send(request)
        if result.retcode != mt5.TRADE_RETCODE_DONE:
            logger.error(f"Nie można otworzyć pozycji na {symbol}: {result.retcode} - {result.comment}")
            return None
        
        logger.info(f"Pozycja na {symbol} otwarta pomyślnie. Ticket: {result.order}")
        return result.order
    
    @ensure_connection
    def close_position(self, ticket: int, comment: str = "") -> bool:
        """
        Zamknięcie pozycji.
        
        Args:
            ticket (int): Numer zlecenia.
            comment (str, optional): Komentarz. Domyślnie "".
        
        Returns:
            bool: True jeśli pozycja została zamknięta, False w przeciwnym razie.
        """
        # Pobranie pozycji
        position = mt5.positions_get(ticket=ticket)
        if not position:
            error = mt5.last_error()
            logger.error(f"Nie można znaleźć pozycji o numerze {ticket}: {error}")
            return False
        
        # Ustawienie typu przeciwnego dla zamknięcia
        if position[0].type == 0:  # Buy
            order_type = mt5.ORDER_TYPE_SELL
            price = mt5.symbol_info_tick(position[0].symbol).bid
        else:  # Sell
            order_type = mt5.ORDER_TYPE_BUY
            price = mt5.symbol_info_tick(position[0].symbol).ask
        
        # Przygotowanie żądania
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": position[0].symbol,
            "volume": position[0].volume,
            "type": order_type,
            "position": ticket,
            "price": price,
            "comment": comment,
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }
        
        # Wysłanie żądania
        result = mt5.order_send(request)
        if result.retcode != mt5.TRADE_RETCODE_DONE:
            logger.error(f"Nie można zamknąć pozycji {ticket}: {result.retcode} - {result.comment}")
            return False
        
        logger.info(f"Pozycja {ticket} zamknięta pomyślnie")
        return True
    
    @ensure_connection
    def modify_position(
        self,
        ticket: int,
        sl: Optional[float] = None,
        tp: Optional[float] = None,
        comment: str = ""
    ) -> bool:
        """
        Modyfikacja pozycji.
        
        Args:
            ticket (int): Numer zlecenia.
            sl (float, optional): Nowy Stop Loss. Domyślnie None (bez zmian).
            tp (float, optional): Nowy Take Profit. Domyślnie None (bez zmian).
            comment (str, optional): Komentarz. Domyślnie "".
        
        Returns:
            bool: True jeśli pozycja została zmodyfikowana, False w przeciwnym razie.
        """
        # Pobranie pozycji
        position = mt5.positions_get(ticket=ticket)
        if not position:
            error = mt5.last_error()
            logger.error(f"Nie można znaleźć pozycji o numerze {ticket}: {error}")
            return False
        
        # Jeśli nie podano nowego SL lub TP, użyj obecnych wartości
        if sl is None:
            sl = position[0].sl
        if tp is None:
            tp = position[0].tp
        
        # Zaokrąglenie wartości SL i TP
        symbol_info = self.get_symbol_info(position[0].symbol)
        if symbol_info:
            sl = round(sl, symbol_info['digits']) if sl else None
            tp = round(tp, symbol_info['digits']) if tp else None
        
        # Przygotowanie żądania
        request = {
            "action": mt5.TRADE_ACTION_SLTP,
            "symbol": position[0].symbol,
            "position": ticket,
            "sl": sl,
            "tp": tp,
            "comment": comment
        }
        
        # Wysłanie żądania
        result = mt5.order_send(request)
        if result.retcode != mt5.TRADE_RETCODE_DONE:
            logger.error(f"Nie można zmodyfikować pozycji {ticket}: {result.retcode} - {result.comment}")
            return False
        
        logger.info(f"Pozycja {ticket} zmodyfikowana pomyślnie")
        return True
    
    @ensure_connection
    def cancel_order(self, ticket: int, comment: str = "") -> bool:
        """
        Anulowanie oczekującego zlecenia.
        
        Args:
            ticket (int): Numer zlecenia.
            comment (str, optional): Komentarz. Domyślnie "".
        
        Returns:
            bool: True jeśli zlecenie zostało anulowane, False w przeciwnym razie.
        """
        # Pobranie zlecenia
        order = mt5.orders_get(ticket=ticket)
        if not order:
            error = mt5.last_error()
            logger.error(f"Nie można znaleźć zlecenia o numerze {ticket}: {error}")
            return False
        
        # Przygotowanie żądania
        request = {
            "action": mt5.TRADE_ACTION_REMOVE,
            "order": ticket,
            "comment": comment
        }
        
        # Wysłanie żądania
        result = mt5.order_send(request)
        if result.retcode != mt5.TRADE_RETCODE_DONE:
            logger.error(f"Nie można anulować zlecenia {ticket}: {result.retcode} - {result.comment}")
            return False
        
        logger.info(f"Zlecenie {ticket} anulowane pomyślnie")
        return True
    
    @ensure_connection
    def calculate_margin(
        self,
        symbol: str,
        order_type: str,
        volume: float,
        price: Optional[float] = None
    ) -> Optional[float]:
        """
        Obliczenie wymaganego depozytu zabezpieczającego dla zlecenia.
        
        Args:
            symbol (str): Symbol.
            order_type (str): Typ zlecenia ('buy' lub 'sell').
            volume (float): Wielkość pozycji.
            price (float, optional): Cena. Domyślnie None (cena rynkowa).
        
        Returns:
            float: Wymagany depozyt zabezpieczający lub None w przypadku błędu.
        """
        # Mapowanie typu zlecenia
        order_type_map = {
            'buy': mt5.ORDER_TYPE_BUY,
            'sell': mt5.ORDER_TYPE_SELL
        }
        
        # Sprawdzenie typu zlecenia
        if order_type not in order_type_map:
            logger.error(f"Nieprawidłowy typ zlecenia: {order_type}. Dostępne: {list(order_type_map.keys())}")
            return None
        
        # Pobranie informacji o symbolu
        symbol_info = self.get_symbol_info(symbol)
        if not symbol_info:
            return None
        
        # Określenie ceny
        if not price:
            if order_type == 'buy':
                price = symbol_info['ask']
            else:
                price = symbol_info['bid']
        
        # Zaokrąglenie ceny do odpowiedniej liczby miejsc po przecinku
        price = round(price, symbol_info['digits'])
        
        # Obliczenie depozytu
        margin = mt5.order_calc_margin(
            order_type_map[order_type],
            symbol,
            volume,
            price
        )
        
        if margin is None:
            error = mt5.last_error()
            logger.error(f"Nie można obliczyć depozytu dla {symbol}: {error}")
            return None
        
        return margin

    def modify_position(self, position_data: Dict[str, Any]) -> bool:
        """
        Modyfikuje parametry istniejącej pozycji.
        
        Args:
            position_data: Słownik z danymi pozycji do modyfikacji.
                Wymagane klucze: ticket, sl, tp.
                
        Returns:
            bool: True jeśli pozycja została zmodyfikowana, False w przeciwnym razie.
        """
        if not self._connected:
            logger.error("Nie połączono z platformą MT5")
            return False
            
        cmd = {
            "action": "modify_position",
            "position": position_data
        }
        
        response = self._send_command(cmd)
        
        if response and response.get("success"):
            logger.info(f"Pozycja {position_data.get('ticket')} zmodyfikowana pomyślnie")
            return True
        else:
            error = response.get("error", "Nieznany błąd") if response else "Brak odpowiedzi"
            logger.error(f"Błąd podczas modyfikacji pozycji: {error}")
            return False
            
    def close_position_partial(self, ticket: int, volume: float) -> bool:
        """
        Częściowo zamyka istniejącą pozycję.
        
        Args:
            ticket: Numer identyfikacyjny pozycji
            volume: Wolumen do zamknięcia (mniejszy niż całkowity wolumen pozycji)
                
        Returns:
            bool: True jeśli pozycja została częściowo zamknięta, False w przeciwnym razie.
        """
        if not self._connected:
            logger.error("Nie połączono z platformą MT5")
            return False
            
        cmd = {
            "action": "close_position_partial",
            "ticket": ticket,
            "volume": volume
        }
        
        response = self._send_command(cmd)
        
        if response and response.get("success"):
            logger.info(f"Pozycja {ticket} częściowo zamknięta (wolumen: {volume})")
            return True
        else:
            error = response.get("error", "Nieznany błąd") if response else "Brak odpowiedzi"
            logger.error(f"Błąd podczas częściowego zamykania pozycji: {error}")
            return False
            
    def place_pending_order(self, symbol: str, order_type: str, volume: float,
                           price: float, sl: float = 0, tp: float = 0) -> Dict[str, Any]:
        """
        Tworzy zlecenie oczekujące.
        
        Args:
            symbol: Symbol instrumentu
            order_type: Typ zlecenia ('buy_limit', 'sell_limit', 'buy_stop', 'sell_stop')
            volume: Wolumen zlecenia
            price: Cena aktywacji zlecenia
            sl: Poziom Stop Loss
            tp: Poziom Take Profit
                
        Returns:
            Dict: Wynik operacji z numerem zlecenia (ticket) w przypadku sukcesu
        """
        if not self._connected:
            logger.error("Nie połączono z platformą MT5")
            return {"success": False, "error": "Nie połączono z platformą MT5"}
            
        cmd = {
            "action": "place_pending_order",
            "order": {
                "symbol": symbol,
                "type": order_type,
                "volume": volume,
                "price": price,
                "sl": sl,
                "tp": tp
            }
        }
        
        response = self._send_command(cmd)
        
        if response and response.get("success"):
            logger.info(f"Zlecenie oczekujące {order_type} dla {symbol} utworzone pomyślnie. Ticket: {response.get('ticket')}")
            return {
                "success": True,
                "ticket": response.get("ticket")
            }
        else:
            error = response.get("error", "Nieznany błąd") if response else "Brak odpowiedzi"
            logger.error(f"Błąd podczas tworzenia zlecenia oczekującego: {error}")
            return {
                "success": False,
                "error": error
            }
            
    def delete_pending_order(self, ticket: int) -> bool:
        """
        Usuwa zlecenie oczekujące.
        
        Args:
            ticket: Numer identyfikacyjny zlecenia
                
        Returns:
            bool: True jeśli zlecenie zostało usunięte, False w przeciwnym razie.
        """
        if not self._connected:
            logger.error("Nie połączono z platformą MT5")
            return False
            
        cmd = {
            "action": "delete_pending_order",
            "ticket": ticket
        }
        
        response = self._send_command(cmd)
        
        if response and response.get("success"):
            logger.info(f"Zlecenie oczekujące {ticket} usunięte pomyślnie")
            return True
        else:
            error = response.get("error", "Nieznany błąd") if response else "Brak odpowiedzi"
            logger.error(f"Błąd podczas usuwania zlecenia oczekującego: {error}")
            return False

    def start_batch_processing(self):
        """
        Uruchamia wątek do wsadowego przetwarzania poleceń.
        """
        if self._batch_thread is None or not self._batch_thread.is_alive():
            self._batch_processing = True
            self._batch_thread = threading.Thread(target=self._process_batch_commands, daemon=True)
            self._batch_thread.start()
            logger.info("Uruchomiono wsadowe przetwarzanie poleceń")
            
    def stop_batch_processing(self):
        """
        Zatrzymuje wątek wsadowego przetwarzania i przetwarza pozostałe polecenia.
        """
        if self._batch_thread is not None and self._batch_thread.is_alive():
            self._batch_processing = False
            self._batch_thread.join(timeout=2.0)
            # Przetwarzanie pozostałych poleceń
            self._execute_batch_commands()
            logger.info("Zatrzymano wsadowe przetwarzanie poleceń")
            
    def add_batch_command(self, command_type: str, command_params: Dict[str, Any]):
        """
        Dodaje polecenie do wsadowego przetwarzania.
        
        Args:
            command_type: Typ polecenia
            command_params: Parametry polecenia
        """
        with self._batch_lock:
            self._batch_commands.append((command_type, command_params))
            
    def _process_batch_commands(self):
        """
        Przetwarza polecenia wsadowo w regularnych odstępach czasu.
        """
        while self._batch_processing:
            # Wykonaj wsadowe przetwarzanie
            if self._batch_commands:
                self._execute_batch_commands()
            
            # Poczekaj określony interwał
            time.sleep(self._batch_interval)
            
    def _execute_batch_commands(self):
        """
        Wykonuje wszystkie zgromadzone polecenia wsadowo.
        """
        commands = []
        
        # Pobierz wszystkie polecenia w bezpieczny sposób
        with self._batch_lock:
            commands = self._batch_commands.copy()
            self._batch_commands = []
            
        if not commands:
            return
            
        # Pogrupuj polecenia według typu
        grouped_commands = {}
        for cmd_type, cmd_params in commands:
            if cmd_type not in grouped_commands:
                grouped_commands[cmd_type] = []
            grouped_commands[cmd_type].append(cmd_params)
            
        # Wykonaj polecenia grupami
        for cmd_type, params_list in grouped_commands.items():
            if cmd_type == 'modify_position':
                # Zoptymalizowane wsadowe modyfikowanie pozycji
                self._batch_modify_positions(params_list)
            # Tutaj można dodać więcej typów poleceń do przetwarzania wsadowego
            
    def _batch_modify_positions(self, positions_params: List[Dict[str, Any]]):
        """
        Optymalizuje modyfikowanie wielu pozycji naraz.
        
        Args:
            positions_params: Lista parametrów dla pozycji do modyfikacji
        """
        if not self._connected and not self.connect():
            logger.error("Nie można wykonać wsadowej modyfikacji pozycji - brak połączenia")
            return
            
        logger.info(f"Wsadowa modyfikacja {len(positions_params)} pozycji")
        
        success_count = 0
        error_count = 0
        
        for params in positions_params:
            position_id = params.get('ticket')
            symbol = params.get('symbol')
            sl = params.get('sl')
            tp = params.get('tp')
            
            # Przygotowanie struktury request
            request = {
                "action": mt5.TRADE_ACTION_SLTP,
                "position": position_id,
                "symbol": symbol
            }
            
            if sl is not None:
                request["sl"] = sl
                
            if tp is not None:
                request["tp"] = tp
                
            # Wykonanie transakcji
            result = mt5.order_send(request)
            
            if result is None:
                error = mt5.last_error()
                logger.error(f"Błąd podczas modyfikacji pozycji {position_id}: {error}")
                error_count += 1
            elif result.retcode != mt5.TRADE_RETCODE_DONE:
                logger.error(f"Błąd podczas modyfikacji pozycji {position_id}: {result.retcode}")
                error_count += 1
            else:
                success_count += 1
                
        logger.info(f"Wsadowa modyfikacja zakończona: {success_count} sukces, {error_count} błędy")
            
    def invalidate_cache(self, cache_type: str = 'all', symbol: str = None):
        """
        Wymusza odświeżenie buforowanych danych.
        
        Args:
            cache_type: Typ bufora do odświeżenia ('market_data', 'positions', 'orders', 'account_info', 'all')
            symbol: Symbol dla odświeżenia danych rynkowych (gdy cache_type='market_data')
        """
        if cache_type == 'market_data' and symbol is not None:
            if symbol in self._market_data_cache:
                del self._market_data_cache[symbol]
                if symbol in self._market_data_cache_time:
                    del self._market_data_cache_time[symbol]
        elif cache_type == 'positions' or cache_type == 'all':
            self._positions_cache = None
            self._positions_cache_time = None
        elif cache_type == 'orders' or cache_type == 'all':
            self._orders_cache = None
            self._orders_cache_time = None
        elif cache_type == 'account_info' or cache_type == 'all':
            self._account_info_cache = None
            self._account_info_cache_time = None
        elif cache_type == 'all':
            self._market_data_cache = {}
            self._market_data_cache_time = {}
            self._positions_cache = None
            self._positions_cache_time = None
            self._orders_cache = None
            self._orders_cache_time = None
            self._account_info_cache = None
            self._account_info_cache_time = None

    @ensure_connection
    def positions_get(self) -> Optional[List[Dict[str, Any]]]:
        """
        Pobranie otwartych pozycji.
        
        Returns:
            List[Dict[str, Any]]: Lista aktualnych pozycji lub None w przypadku błędu.
        """
        # Sprawdź bufor pozycji
        now = datetime.now()
        if (self._positions_cache is not None and self._positions_cache_time is not None and
                (now - self._positions_cache_time).total_seconds() < self._positions_cache_ttl):
            return self._positions_cache
            
        # Pobierz dane z MT5
        positions = mt5.positions_get()
        if positions is None:
            error = mt5.last_error()
            logger.error(f"Nie można pobrać otwartych pozycji: {error}")
            return None
        
        # Konwersja pozycji na listę słowników
        positions_list = []
        for position in positions:
            position_dict = {
                'ticket': position.ticket,
                'symbol': position.symbol,
                'type': 'buy' if position.type == 0 else 'sell',
                'volume': position.volume,
                'open_price': position.price_open,
                'open_time': datetime.fromtimestamp(position.time),
                'sl': position.sl,
                'tp': position.tp,
                'profit': position.profit,
                'comment': position.comment,
                'magic': position.magic
            }
            positions_list.append(position_dict)
        
        # Aktualizacja bufora
        self._positions_cache = positions_list
        self._positions_cache_time = now
        
        return positions_list
    
    # Alias dla kompatybilności
    get_open_positions = positions_get
    
    # Alias dla otwarcia pozycji, aby zachować spójność interfejsu
    open_position = open_order

    def is_connected(self) -> bool:
        """
        Sprawdza, czy połączenie z MT5 jest aktywne.
        
        Returns:
            bool: True jeśli połączenie jest aktywne, False w przeciwnym wypadku
        """
        return mt5.terminal_info() is not None and self._connected

    @ensure_connection
    def get_current_price(self, symbol: str) -> Optional[float]:
        """
        Pobiera aktualną cenę dla danego symbolu.
        
        Args:
            symbol (str): Symbol instrumentu (np. "EURUSD").
            
        Returns:
            float: Aktualna cena (średnia z bid i ask) lub None w przypadku błędu.
        """
        # Mapuj symbol na format MT5
        mapped_symbol = self._map_symbol(symbol)
        
        # Pobierz dane z MT5
        tick = mt5.symbol_info_tick(mapped_symbol)
        if tick is None:
            error = mt5.last_error()
            logger.error(f"Nie można pobrać aktualnej ceny dla {symbol} (zmapowany na {mapped_symbol}): {error}")
            return None
        
        # Zwróć średnią z bid i ask
        return (tick.bid + tick.ask) / 2



# Singleton funkcja dla MT5Connector
_mt5_connector_instance = None

def get_mt5_connector() -> MT5Connector:
    """
    Zwraca singleton instancję MT5Connector.
    
    Returns:
        MT5Connector: Instancja konektora MT5
    """
    global _mt5_connector_instance
    if _mt5_connector_instance is None:
        _mt5_connector_instance = MT5Connector()
    return _mt5_connector_instance


# Przykład użycia:
if __name__ == "__main__":
    # Konfiguracja logowania
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # Przykładowe połączenie
    connector = MT5Connector()
    try:
        if connector.connect():
            # Pobranie informacji o koncie
            account_info = connector.get_account_info()
            if account_info:
                print(f"Saldo: {account_info['balance']} {account_info['currency']}")
            
            # Pobranie informacji o symbolu
            symbol_info = connector.get_symbol_info("EURUSD")
            if symbol_info:
                print(f"EURUSD: Bid={symbol_info['bid']}, Ask={symbol_info['ask']}")
            
            # Pobranie danych historycznych
            data = connector.get_historical_data("EURUSD", "H1", count=10)
            if data is not None:
                print(f"Dane historyczne EURUSD H1:\n{data.head()}")
            
            # Pobranie aktualnych pozycji
            positions = connector.get_positions()
            if positions is not None:
                print(f"Liczba otwartych pozycji: {len(positions)}")
    finally:
        connector.disconnect() 