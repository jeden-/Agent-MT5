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

# Import biblioteki MetaTrader5
try:
    import MetaTrader5 as mt5
except ImportError:
    raise ImportError("Biblioteka MetaTrader5 nie jest zainstalowana. Zainstaluj ją używając: pip install MetaTrader5")

# Ustawienie loggera
logger = logging.getLogger('trading_agent.mt5_bridge')


class MT5Connector:
    """Klasa odpowiedzialna za połączenie z platformą MetaTrader 5."""
    
    _instance = None
    
    def __new__(cls):
        """Implementacja wzorca Singleton."""
        if cls._instance is None:
            cls._instance = super(MT5Connector, cls).__new__(cls)
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
        account_info = mt5.account_info()
        if account_info is None:
            error = mt5.last_error()
            logger.error(f"Nie można pobrać informacji o koncie: {error}")
            return None
        
        # Konwersja z namedtuple na słownik
        return {
            'login': account_info.login,
            'balance': account_info.balance,
            'equity': account_info.equity,
            'margin': account_info.margin,
            'free_margin': account_info.margin_free,
            'margin_level': account_info.margin_level,
            'leverage': account_info.leverage,
            'currency': account_info.currency,
            'server': account_info.server,
            'company': account_info.company
        }
    
    @ensure_connection
    def get_symbol_info(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Pobranie informacji o symbolu.
        
        Args:
            symbol (str): Symbol do sprawdzenia.
        
        Returns:
            Dict[str, Any]: Informacje o symbolu lub None w przypadku błędu.
        """
        # Sprawdzenie czy symbol istnieje
        if not mt5.symbol_select(symbol, True):
            error = mt5.last_error()
            logger.error(f"Nie można wybrać symbolu {symbol}: {error}")
            return None
        
        symbol_info = mt5.symbol_info(symbol)
        if symbol_info is None:
            error = mt5.last_error()
            logger.error(f"Nie można pobrać informacji o symbolu {symbol}: {error}")
            return None
        
        # Konwersja z namedtuple na słownik
        return {
            'name': symbol_info.name,
            'description': symbol_info.description,
            'digits': symbol_info.digits,
            'spread': symbol_info.spread,
            'point': symbol_info.point,
            'trade_tick_size': symbol_info.trade_tick_size,
            'trade_contract_size': symbol_info.trade_contract_size,
            'volume_min': symbol_info.volume_min,
            'volume_max': symbol_info.volume_max,
            'volume_step': symbol_info.volume_step,
            'bid': symbol_info.bid,
            'ask': symbol_info.ask,
            'time': symbol_info.time
        }
    
    @ensure_connection
    def get_historical_data(
        self, 
        symbol: str, 
        timeframe: str, 
        start_time: Optional[datetime] = None, 
        end_time: Optional[datetime] = None, 
        count: int = 1000
    ) -> Optional[pd.DataFrame]:
        """
        Pobranie danych historycznych.
        
        Args:
            symbol (str): Symbol do pobrania danych.
            timeframe (str): Timeframe (np. "M1", "M5", "H1", "D1").
            start_time (datetime, optional): Początek okresu. Domyślnie None.
            end_time (datetime, optional): Koniec okresu. Domyślnie None.
            count (int, optional): Liczba słupków do pobrania. Domyślnie 1000.
        
        Returns:
            pd.DataFrame: DataFrame z danymi historycznymi lub None w przypadku błędu.
        """
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
        
        # Sprawdzenie czy timeframe jest poprawny
        if timeframe not in timeframe_map:
            logger.error(f"Nieprawidłowy timeframe: {timeframe}. Dostępne: {list(timeframe_map.keys())}")
            return None
        
        # Pobranie danych
        rates = mt5.copy_rates_from_pos(symbol, timeframe_map[timeframe], 0, count)
        if rates is None or len(rates) == 0:
            error = mt5.last_error()
            logger.error(f"Nie można pobrać danych historycznych dla {symbol} na timeframe {timeframe}: {error}")
            return None
        
        # Konwersja na DataFrame
        df = pd.DataFrame(rates)
        df['time'] = pd.to_datetime(df['time'], unit='s')
        
        # Filtrowanie po czasie, jeśli podano
        if start_time:
            df = df[df['time'] >= start_time]
        if end_time:
            df = df[df['time'] <= end_time]
        
        # Sortowanie po czasie
        df.sort_values('time', inplace=True)
        df.reset_index(drop=True, inplace=True)
        
        return df
    
    @ensure_connection
    def get_positions(self) -> Optional[List[Dict[str, Any]]]:
        """
        Pobranie aktualnych pozycji.
        
        Returns:
            List[Dict[str, Any]]: Lista aktualnych pozycji lub None w przypadku błędu.
        """
        positions = mt5.positions_get()
        if positions is None:
            error = mt5.last_error()
            if error[0] == 0:  # Brak pozycji (to nie jest błąd)
                return []
            logger.error(f"Nie można pobrać pozycji: {error}")
            return None
        
        result = []
        for position in positions:
            # Konwersja z namedtuple na słownik
            result.append({
                'ticket': position.ticket,
                'symbol': position.symbol,
                'type': position.type,  # 0 - buy, 1 - sell
                'volume': position.volume,
                'open_price': position.price_open,
                'current_price': position.price_current,
                'sl': position.sl,
                'tp': position.tp,
                'profit': position.profit,
                'comment': position.comment,
                'magic': position.magic,
                'open_time': datetime.fromtimestamp(position.time)
            })
        
        return result
    
    @ensure_connection
    def get_orders(self) -> Optional[List[Dict[str, Any]]]:
        """
        Pobranie oczekujących zleceń.
        
        Returns:
            List[Dict[str, Any]]: Lista oczekujących zleceń lub None w przypadku błędu.
        """
        orders = mt5.orders_get()
        if orders is None:
            error = mt5.last_error()
            if error[0] == 0:  # Brak zleceń (to nie jest błąd)
                return []
            logger.error(f"Nie można pobrać zleceń: {error}")
            return None
        
        result = []
        for order in orders:
            # Konwersja z namedtuple na słownik
            result.append({
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
            })
        
        return result
    
    @ensure_connection
    def open_position(
        self,
        symbol: str,
        order_type: str,
        volume: float,
        price: Optional[float] = None,
        sl: Optional[float] = None,
        tp: Optional[float] = None,
        comment: str = "",
        magic: int = 0
    ) -> Optional[int]:
        """
        Otwarcie pozycji.
        
        Args:
            symbol (str): Symbol.
            order_type (str): Typ zlecenia ('buy' lub 'sell').
            volume (float): Wielkość pozycji.
            price (float, optional): Cena otwarcia (dla zleceń oczekujących). Domyślnie None (cena rynkowa).
            sl (float, optional): Stop Loss. Domyślnie None.
            tp (float, optional): Take Profit. Domyślnie None.
            comment (str, optional): Komentarz. Domyślnie "".
            magic (int, optional): Magic number. Domyślnie 0.
        
        Returns:
            int: Numer zlecenia lub None w przypadku błędu.
        """
        # Mapowanie typu zlecenia
        order_type_map = {
            'buy': mt5.ORDER_TYPE_BUY,
            'sell': mt5.ORDER_TYPE_SELL,
            'buy_limit': mt5.ORDER_TYPE_BUY_LIMIT,
            'sell_limit': mt5.ORDER_TYPE_SELL_LIMIT,
            'buy_stop': mt5.ORDER_TYPE_BUY_STOP,
            'sell_stop': mt5.ORDER_TYPE_SELL_STOP
        }
        
        # Sprawdzenie typu zlecenia
        if order_type not in order_type_map:
            logger.error(f"Nieprawidłowy typ zlecenia: {order_type}. Dostępne: {list(order_type_map.keys())}")
            return None
        
        # Pobranie informacji o symbolu
        symbol_info = self.get_symbol_info(symbol)
        if not symbol_info:
            return None
        
        # Określenie ceny dla zleceń rynkowych
        if order_type == 'buy' and not price:
            price = symbol_info['ask']
        elif order_type == 'sell' and not price:
            price = symbol_info['bid']
        
        # Zaokrąglenie ceny do odpowiedniej liczby miejsc po przecinku
        if price:
            price = round(price, symbol_info['digits'])
        if sl:
            sl = round(sl, symbol_info['digits'])
        if tp:
            tp = round(tp, symbol_info['digits'])
        
        # Przygotowanie żądania
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": volume,
            "type": order_type_map[order_type],
            "price": price,
            "sl": sl,
            "tp": tp,
            "comment": comment,
            "magic": magic,
            "type_time": mt5.ORDER_TIME_GTC,  # Good Till Cancelled
            "type_filling": mt5.ORDER_FILLING_IOC,  # Immediate Or Cancel
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