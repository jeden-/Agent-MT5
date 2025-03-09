#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Serwis handlowy odpowiedzialny za wykonywanie operacji handlowych przez MT5.
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any, Union
import pandas as pd

from .mt5_connector import MT5Connector
from src.database.models import TradingSignal, Transaction

# Ustawienie loggera
logger = logging.getLogger('trading_agent.mt5_bridge.trading')


class TradingService:
    """
    Serwis handlowy odpowiedzialny za wykonywanie operacji handlowych.
    """
    
    def __init__(self):
        """Inicjalizacja serwisu handlowego."""
        self.connector = MT5Connector()
        logger.info("TradingService zainicjalizowany")
    
    def connect(self) -> bool:
        """
        Nawiązanie połączenia z platformą MT5.
        
        Returns:
            bool: True jeśli połączenie zostało nawiązane, False w przeciwnym razie.
        """
        return self.connector.connect()
    
    def disconnect(self) -> bool:
        """
        Zamknięcie połączenia z platformą MT5.
        
        Returns:
            bool: True jeśli połączenie zostało zamknięte, False w przeciwnym razie.
        """
        return self.connector.disconnect()
    
    def get_account_info(self) -> Optional[Dict[str, Any]]:
        """
        Pobranie informacji o koncie.
        
        Returns:
            Dict[str, Any]: Informacje o koncie lub None w przypadku błędu.
        """
        return self.connector.get_account_info()
    
    def get_market_data(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Pobranie aktualnych danych rynkowych dla symbolu.
        
        Args:
            symbol (str): Symbol.
        
        Returns:
            Dict[str, Any]: Aktualne dane rynkowe lub None w przypadku błędu.
        """
        symbol_info = self.connector.get_symbol_info(symbol)
        if not symbol_info:
            return None
        
        return {
            'symbol': symbol,
            'bid': symbol_info['bid'],
            'ask': symbol_info['ask'],
            'spread': symbol_info['spread'],
            'time': datetime.fromtimestamp(symbol_info['time']),
            'digits': symbol_info['digits'],
            'point': symbol_info['point']
        }
    
    def get_historical_data(
        self, 
        symbol: str, 
        timeframe: str, 
        bars: int = 1000
    ) -> Optional[pd.DataFrame]:
        """
        Pobranie danych historycznych.
        
        Args:
            symbol (str): Symbol.
            timeframe (str): Timeframe.
            bars (int, optional): Liczba słupków. Domyślnie 1000.
        
        Returns:
            pd.DataFrame: DataFrame z danymi historycznymi lub None w przypadku błędu.
        """
        return self.connector.get_historical_data(symbol, timeframe, count=bars)
    
    def get_open_positions(self) -> Optional[List[Dict[str, Any]]]:
        """
        Pobranie otwartych pozycji.
        
        Returns:
            List[Dict[str, Any]]: Lista otwartych pozycji lub None w przypadku błędu.
        """
        return self.connector.get_positions()
    
    def get_pending_orders(self) -> Optional[List[Dict[str, Any]]]:
        """
        Pobranie oczekujących zleceń.
        
        Returns:
            List[Dict[str, Any]]: Lista oczekujących zleceń lub None w przypadku błędu.
        """
        return self.connector.get_orders()
    
    def execute_signal(self, signal: TradingSignal) -> Optional[Transaction]:
        """
        Wykonanie sygnału handlowego.
        
        Args:
            signal (TradingSignal): Sygnał handlowy do wykonania.
        
        Returns:
            Transaction: Rezultat transakcji lub None w przypadku błędu.
        """
        if not signal:
            logger.error("Nie można wykonać pustego sygnału")
            return None
        
        # Sprawdzenie czy sygnał jest ważny
        if signal.status != 'pending':
            logger.warning(f"Sygnał {signal.id} ma status {signal.status}, oczekiwano 'pending'")
            return None
        
        # Pobranie aktualnych danych rynkowych
        market_data = self.get_market_data(signal.symbol)
        if not market_data:
            logger.error(f"Nie można pobrać danych rynkowych dla {signal.symbol}")
            return None
        
        # Wyliczenie ceny wejścia dla zleceń rynkowych
        entry_price = None
        if signal.direction == 'buy':
            entry_price = market_data['ask']
        elif signal.direction == 'sell':
            entry_price = market_data['bid']
        else:
            logger.error(f"Nieprawidłowy kierunek sygnału: {signal.direction}")
            return None
        
        # Sprawdzenie czy sygnał jest nadal ważny (czy cena nie oddaliła się za bardzo)
        if abs(entry_price - signal.entry_price) / market_data['point'] > 50:  # 50 pipsów odchylenia
            logger.warning(f"Cena zmieniła się zbyt mocno. Oczekiwano: {signal.entry_price}, aktualna: {entry_price}")
            # Można tu dodać logikę decyzyjną czy nadal wykonać sygnał
        
        # Wyliczenie wielkości pozycji (można to ulepszyć w module zarządzania ryzykiem)
        volume = 0.1  # Minimalna wielkość
        
        # Próba otwarcia pozycji
        order_ticket = self.connector.open_position(
            symbol=signal.symbol,
            order_type=signal.direction,
            volume=volume,
            price=None,  # Użyj ceny rynkowej
            sl=signal.stop_loss,
            tp=signal.take_profit,
            comment=f"Signal ID: {signal.id}",
            magic=12345  # Stały identyfikator dla naszych transakcji
        )
        
        if not order_ticket:
            logger.error(f"Nie można otworzyć pozycji dla sygnału {signal.id}")
            return None
        
        # Utworzenie transakcji
        transaction = Transaction(
            symbol=signal.symbol,
            order_type=signal.direction,
            volume=volume,
            status="open",
            open_price=entry_price,
            stop_loss=signal.stop_loss,
            take_profit=signal.take_profit,
            mt5_order_id=order_ticket,
            signal_id=signal.id,
            open_time=datetime.now()
        )
        
        logger.info(f"Sygnał {signal.id} wykonany pomyślnie. Ticket: {order_ticket}")
        return transaction
    
    def close_transaction(self, transaction: Transaction) -> bool:
        """
        Zamknięcie transakcji.
        
        Args:
            transaction (Transaction): Transakcja do zamknięcia.
        
        Returns:
            bool: True jeśli transakcja została zamknięta, False w przeciwnym razie.
        """
        if not transaction:
            logger.error("Nie można zamknąć pustej transakcji")
            return False
        
        # Sprawdzenie czy transakcja ma ID zlecenia MT5
        if not transaction.mt5_order_id:
            logger.error(f"Transakcja {transaction.id} nie ma ID zlecenia MT5")
            return False
        
        # Próba zamknięcia pozycji
        result = self.connector.close_position(
            transaction.mt5_order_id,
            comment=f"Transaction ID: {transaction.id} - Closed"
        )
        
        if not result:
            logger.error(f"Nie można zamknąć pozycji dla transakcji {transaction.id}")
            return False
        
        logger.info(f"Transakcja {transaction.id} zamknięta pomyślnie")
        return True
    
    def modify_transaction(
        self,
        transaction: Transaction,
        sl: Optional[float] = None,
        tp: Optional[float] = None
    ) -> bool:
        """
        Modyfikacja parametrów transakcji.
        
        Args:
            transaction (Transaction): Transakcja do modyfikacji.
            sl (float, optional): Nowy Stop Loss. Domyślnie None (bez zmian).
            tp (float, optional): Nowy Take Profit. Domyślnie None (bez zmian).
        
        Returns:
            bool: True jeśli transakcja została zmodyfikowana, False w przeciwnym razie.
        """
        if not transaction:
            logger.error("Nie można zmodyfikować pustej transakcji")
            return False
        
        # Sprawdzenie czy transakcja ma ID zlecenia MT5
        if not transaction.mt5_order_id:
            logger.error(f"Transakcja {transaction.id} nie ma ID zlecenia MT5")
            return False
        
        # Próba modyfikacji pozycji
        result = self.connector.modify_position(
            transaction.mt5_order_id,
            sl=sl,
            tp=tp,
            comment=f"Transaction ID: {transaction.id} - Modified"
        )
        
        if not result:
            logger.error(f"Nie można zmodyfikować pozycji dla transakcji {transaction.id}")
            return False
        
        logger.info(f"Transakcja {transaction.id} zmodyfikowana pomyślnie")
        return True
    
    def calculate_position_size(
        self,
        symbol: str,
        direction: str,
        risk_percent: float,
        entry_price: float,
        stop_loss: float
    ) -> Optional[float]:
        """
        Obliczenie wielkości pozycji na podstawie ryzyka.
        
        Args:
            symbol (str): Symbol.
            direction (str): Kierunek ('buy' lub 'sell').
            risk_percent (float): Procent kapitału do zaryzykowania.
            entry_price (float): Cena wejścia.
            stop_loss (float): Poziom Stop Loss.
        
        Returns:
            float: Wielkość pozycji lub None w przypadku błędu.
        """
        # Pobranie informacji o koncie
        account_info = self.get_account_info()
        if not account_info:
            return None
        
        # Pobranie informacji o symbolu
        symbol_info = self.connector.get_symbol_info(symbol)
        if not symbol_info:
            return None
        
        # Obliczenie kwoty ryzyka
        risk_amount = account_info['balance'] * (risk_percent / 100.0)
        
        # Obliczenie ryzyka w pipsach
        if direction == 'buy':
            pips_at_risk = (entry_price - stop_loss) / symbol_info['point']
        else:  # sell
            pips_at_risk = (stop_loss - entry_price) / symbol_info['point']
        
        # Walidacja
        if pips_at_risk <= 0:
            logger.error(f"Nieprawidłowy Stop Loss dla kierunku {direction}")
            return None
        
        # Wartość pipsa
        pip_value = symbol_info['trade_contract_size'] * symbol_info['point']
        
        # Obliczenie wielkości pozycji w lotach
        position_size = risk_amount / (pips_at_risk * pip_value)
        
        # Zaokrąglenie wielkości pozycji
        position_size = round(position_size / symbol_info['volume_step']) * symbol_info['volume_step']
        
        # Walidacja minimalnej i maksymalnej wielkości
        position_size = max(position_size, symbol_info['volume_min'])
        position_size = min(position_size, symbol_info['volume_max'])
        
        return position_size
    
    def sync_positions(self) -> Dict[str, Any]:
        """
        Synchronizacja pozycji między MT5 a bazą danych.
        
        Returns:
            Dict[str, Any]: Słownik z wynikami synchronizacji.
        """
        # Ta funkcja będzie uzupełniona o logikę synchronizacji
        # między rzeczywistymi pozycjami w MT5 a bazą danych
        
        # Pobranie pozycji z MT5
        mt5_positions = self.get_open_positions() or []
        
        # W tym miejscu powinna być logika synchronizacji z bazą danych
        # np. porównanie z zapisanymi transakcjami i aktualizacja statusów
        
        return {
            'mt5_positions': len(mt5_positions),
            'synchronized': True
        }


# Przykład użycia:
if __name__ == "__main__":
    # Konfiguracja logowania
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # Przykładowe użycie
    trading = TradingService()
    try:
        if trading.connect():
            # Pobranie informacji o koncie
            account_info = trading.get_account_info()
            if account_info:
                print(f"Saldo: {account_info['balance']} {account_info['currency']}")
            
            # Pobranie danych rynkowych
            market_data = trading.get_market_data("EURUSD")
            if market_data:
                print(f"EURUSD: Bid={market_data['bid']}, Ask={market_data['ask']}")
            
            # Pobranie danych historycznych
            data = trading.get_historical_data("EURUSD", "H1", bars=10)
            if data is not None:
                print(f"Dane historyczne EURUSD H1:\n{data.head()}")
            
            # Pobranie otwartych pozycji
            positions = trading.get_open_positions()
            if positions is not None:
                print(f"Liczba otwartych pozycji: {len(positions)}")
    finally:
        trading.disconnect() 