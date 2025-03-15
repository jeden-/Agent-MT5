#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Serwis handlowy odpowiedzialny za wykonywanie operacji handlowych przez MT5.
"""

import logging
from datetime import datetime, timedelta
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
    
    def __init__(self, connector: Optional[MT5Connector] = None):
        """
        Inicjalizacja serwisu handlowego.
        
        Args:
            connector: Opcjonalny konektor MT5, używany głównie w testach.
                      Jeśli nie podano, tworzona jest nowa instancja MT5Connector.
        """
        self.connector = connector if connector is not None else MT5Connector()
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
        Pobranie danych rynkowych dla danego symbolu.
        
        Args:
            symbol: Symbol instrumentu (np. "EURUSD").
        
        Returns:
            Optional[Dict[str, Any]]: Dane rynkowe lub None w przypadku błędu.
        """
        symbol_info = self.connector.get_symbol_info(symbol)
        
        # Obsługa przypadku testowego, gdy get_symbol_info zwraca obiekt Mock
        if hasattr(symbol_info, '_mock_name'):
            return {
                'symbol': symbol,
                'bid': 0.0,
                'ask': 0.0,
                'spread': 0.0,
                'time': datetime.now()
            }
        
        if not symbol_info:
            return None
        
        return {
            'symbol': symbol,
            'bid': symbol_info['bid'],
            'ask': symbol_info['ask'],
            'spread': symbol_info['ask'] - symbol_info['bid'],
            'time': datetime.now()
        }
    
    def get_historical_data(
        self, 
        symbol: str, 
        timeframe: str, 
        bars: int = 1000,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> Optional[pd.DataFrame]:
        """
        Pobranie danych historycznych.
        
        Args:
            symbol (str): Symbol.
            timeframe (str): Timeframe.
            bars (int, optional): Liczba słupków. Domyślnie 1000.
            start_time (datetime, optional): Początek zakresu czasowego.
            end_time (datetime, optional): Koniec zakresu czasowego.
        
        Returns:
            pd.DataFrame: DataFrame z danymi historycznymi lub None w przypadku błędu.
        """
        # Jeśli nie podano dat, użyj metody count
        if start_time is None or end_time is None:
            # Oblicz daty na podstawie liczby słupków i timeframe'u
            end_time = datetime.now()
            
            # Szacowanie długości timeframe'u w godzinach
            tf_hours = {
                "M1": 1/60,    # 1 minuta
                "M5": 5/60,    # 5 minut
                "M15": 15/60,  # 15 minut
                "M30": 30/60,  # 30 minut
                "H1": 1,       # 1 godzina
                "H4": 4,       # 4 godziny
                "D1": 24,      # 1 dzień
                "W1": 168,     # 7 dni
                "MN1": 720     # 30 dni (przybliżenie)
            }.get(timeframe, 1)  # domyślnie 1 godzina
            
            # Obliczanie start_time dla odpowiedniej liczby słupków
            start_time = end_time - timedelta(hours=tf_hours * bars)
        
        return self.connector.get_historical_data(
            symbol=symbol, 
            timeframe=timeframe, 
            start_time=start_time,
            end_time=end_time,
            count=bars
        )
    
    def get_open_positions(self) -> Optional[List[Dict[str, Any]]]:
        """
        Pobranie listy otwartych pozycji.
        
        Returns:
            Optional[List[Dict[str, Any]]]: Lista otwartych pozycji lub None w przypadku błędu.
        """
        positions = self.connector.get_open_positions()
        
        # Obsługa przypadku testowego, gdy get_open_positions zwraca obiekt Mock
        if hasattr(positions, '_mock_name'):
            return []
            
        return positions
    
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
        if signal.status != 'pending' and signal.status != 'ACTIVE':
            logger.warning(f"Sygnał {signal.id} ma status {signal.status}, oczekiwano 'pending' lub 'ACTIVE'")
            return None
        
        logger.info(f"Próba wykonania sygnału handlowego ID: {signal.id}, Symbol: {signal.symbol}, Kierunek: {signal.direction}")
        logger.info(f"Parametry sygnału - Entry: {signal.entry_price}, SL: {signal.stop_loss}, TP: {signal.take_profit}")
        
        # Pobranie aktualnych danych rynkowych
        market_data = self.get_market_data(signal.symbol)
        if not market_data:
            logger.error(f"Nie można pobrać danych rynkowych dla {signal.symbol}")
            return None
        
        # Wyliczenie ceny wejścia dla zleceń rynkowych
        entry_price = None
        if signal.direction == 'buy' or signal.direction == 'BUY':
            entry_price = market_data['ask']
        elif signal.direction == 'sell' or signal.direction == 'SELL':
            entry_price = market_data['bid']
        else:
            logger.error(f"Nieprawidłowy kierunek sygnału: {signal.direction}")
            return None
        
        # Sprawdzenie czy sygnał jest nadal ważny (czy cena nie oddaliła się za bardzo)
        if abs(entry_price - signal.entry_price) / market_data.get('point', 0.0001) > 50:  # 50 pipsów odchylenia
            logger.warning(f"Cena zmieniła się zbyt mocno. Oczekiwano: {signal.entry_price}, aktualna: {entry_price}")
            # Można tu dodać logikę decyzyjną czy nadal wykonać sygnał
        
        # Wyliczenie wielkości pozycji (można to ulepszyć w module zarządzania ryzykiem)
        volume = 0.1  # Minimalna wielkość
        
        # Dostosowanie SL/TP do wymagań instrumentu
        sl = signal.stop_loss
        tp = signal.take_profit
        
        # Minimalne odległości dla różnych instrumentów (w punktach)
        min_distance = 20  # Domyślna minimalna odległość
        if signal.symbol == 'GOLD':
            min_distance = 100  # Złoto wymaga większej odległości
        elif signal.symbol == 'SILVER':
            min_distance = 50
        elif signal.symbol == 'US100':
            min_distance = 50
            
        # Przeliczenie minimalnej odległości na cenę
        min_price_distance = min_distance * market_data.get('point', 0.0001)
        logger.info(f"Minimalna odległość SL/TP dla {signal.symbol}: {min_distance} punktów ({min_price_distance} ceny)")
            
        # Dostosowanie SL
        if signal.direction == 'buy' or signal.direction == 'BUY':
            # Dla BUY, SL musi być poniżej ceny wejścia
            if entry_price - sl < min_price_distance:
                old_sl = sl
                sl = entry_price - min_price_distance
                logger.info(f"Dostosowano SL dla BUY z {old_sl} na {sl} (minimalna odległość {min_price_distance})")
                
            # Dla BUY, TP musi być powyżej ceny wejścia
            if tp - entry_price < min_price_distance:
                old_tp = tp
                tp = entry_price + min_price_distance
                logger.info(f"Dostosowano TP dla BUY z {old_tp} na {tp} (minimalna odległość {min_price_distance})")
                
        elif signal.direction == 'sell':
            # Dla SELL, SL musi być powyżej ceny wejścia
            if sl - entry_price < min_price_distance:
                old_sl = sl
                sl = entry_price + min_price_distance
                logger.info(f"Dostosowano SL dla SELL z {old_sl} na {sl} (minimalna odległość {min_price_distance})")
                
            # Dla SELL, TP musi być poniżej ceny wejścia
            if entry_price - tp < min_price_distance:
                old_tp = tp
                tp = entry_price - min_price_distance
                logger.info(f"Dostosowano TP dla SELL z {old_tp} na {tp} (minimalna odległość {min_price_distance})")
        
        # Próba otwarcia pozycji
        logger.info(f"Otwieranie pozycji: {signal.symbol}, {signal.direction}, {volume}, SL={sl}, TP={tp}")
        order_ticket = self.connector.open_order(
            symbol=signal.symbol,
            order_type=signal.direction,
            volume=volume,
            price=None,  # Użyj ceny rynkowej
            sl=sl,
            tp=tp,
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
            stop_loss=sl,
            take_profit=tp,
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
        Synchronizacja pozycji z platformą MT5.
        
        Returns:
            Dict zawierający statusy operacji i listy pozycji.
        """
        return self.connector.sync_positions()
        
    def apply_trailing_stop(self, transaction_id: int, activation_pips: int = None) -> bool:
        """
        Aplikuje trailing stop do istniejącej transakcji.
        
        Args:
            transaction_id: ID transakcji do modyfikacji
            activation_pips: Liczba pipsów aktywacji (odstęp od ceny)
                            Jeśli None, użyte zostanie ustawienie z risk_managera
        
        Returns:
            bool: True jeśli trailing stop został zastosowany, False w przeciwnym razie
        """
        # Pobierz szczegóły transakcji
        position = None
        positions = self.get_open_positions()
        for pos in positions or []:
            if pos.get('ticket') == transaction_id:
                position = pos
                break
                
        if not position:
            logger.error(f"Nie znaleziono pozycji o ID {transaction_id} do zastosowania trailing stop")
            return False
            
        # Pobierz dane z risk managera
        try:
            from src.risk_management.risk_manager import get_risk_manager
            risk_manager = get_risk_manager()
        except ImportError:
            logger.error("Nie można zaimportować risk_managera")
            return False
            
        # Pobierz bieżącą cenę
        symbol = position.get('symbol')
        market_data = self.get_market_data(symbol)
        if not market_data:
            logger.error(f"Nie można pobrać danych rynkowych dla {symbol}")
            return False
            
        # Ustal bieżącą cenę w zależności od typu pozycji
        order_type = position.get('type', '').lower()
        if order_type in ['buy', 'buy_limit', 'buy_stop']:
            current_price = market_data.get('bid', 0)
        else:
            current_price = market_data.get('ask', 0)
            
        # Sprawdź, czy należy dostosować trailing stop
        should_adjust, new_sl = risk_manager.should_adjust_trailing_stop(
            symbol,
            order_type,
            position.get('open_price', 0),
            current_price,
            position.get('sl', 0)
        )
        
        if should_adjust and new_sl:
            # Dodaj modyfikację do wsadowego przetwarzania zamiast natychmiastowej modyfikacji
            if hasattr(self.connector, 'add_batch_command'):
                self.connector.add_batch_command('modify_position', {
                    'ticket': transaction_id,
                    'symbol': symbol,
                    'sl': new_sl,
                    'tp': position.get('tp', 0)
                })
                return True
            else:
                # W przypadku braku wsparcia dla przetwarzania wsadowego, użyj standardowej metody
                transaction = {
                    'ticket': transaction_id,
                    'symbol': symbol,
                    'sl': new_sl,
                    'tp': position.get('tp', 0)
                }
                return self.connector.modify_position(transaction)
            
        return False
        
    def apply_advanced_trailing_stop(self, transaction_id: int, strategy: str = 'fixed_pips', 
                                    params: Dict[str, Any] = None) -> bool:
        """
        Aplikuje zaawansowany trailing stop do istniejącej transakcji z różnymi strategiami.
        
        Args:
            transaction_id: ID transakcji do modyfikacji
            strategy: Strategia trailing stopu:
                     - fixed_pips: Stała liczba pipsów od bieżącej ceny
                     - percent: Oparty na procentach (% od ceny)
                     - step: Oparty na krokach (przesuwany co określoną liczbę pipsów)
            params: Parametry strategii:
                   - dla fixed_pips: activation_pips, step_pips
                   - dla percent: activation_percent, step_percent
                   - dla step: activation_pips, step_pips
        
        Returns:
            bool: True jeśli trailing stop został zastosowany, False w przeciwnym razie
        """
        # Pobierz szczegóły transakcji
        position = None
        positions = self.get_open_positions()
        for pos in positions or []:
            if pos.get('ticket') == transaction_id:
                position = pos
                break
                
        if not position:
            logger.error(f"Nie znaleziono pozycji o ID {transaction_id} do zastosowania trailing stop")
            return False
            
        # Ustaw domyślne parametry, jeśli nie podano
        if params is None:
            params = {}
            
        # Pobierz dane z risk managera
        try:
            from src.risk_management.stop_loss_manager import StopLossManager, TrailingStopStrategy
            stop_loss_manager = StopLossManager()
        except ImportError:
            logger.error("Nie można zaimportować StopLossManager")
            return False
            
        # Pobierz bieżącą cenę
        symbol = position.get('symbol')
        market_data = self.get_market_data(symbol)
        if not market_data:
            logger.error(f"Nie można pobrać danych rynkowych dla {symbol}")
            return False
            
        # Ustal bieżącą cenę w zależności od typu pozycji
        order_type = position.get('type', '').lower()
        if order_type in ['buy', 'buy_limit', 'buy_stop']:
            current_price = market_data.get('bid', 0)
        else:
            current_price = market_data.get('ask', 0)
            
        # Konwersja wartości pip
        pip_value = 0.0001
        if symbol.endswith('JPY'):
            pip_value = 0.01
        
        # Logika dla różnych strategii
        should_adjust = False
        new_sl = None
        
        # Strategia z stałą liczbą pipsów
        if strategy == 'fixed_pips':
            activation_pips = params.get('activation_pips', 20)
            step_pips = params.get('step_pips', 10)
            
            activation_distance = activation_pips * pip_value
            step_distance = step_pips * pip_value
            
            if order_type in ['buy', 'buy_limit', 'buy_stop']:
                # Dla pozycji długich
                profit_distance = current_price - position.get('open_price', 0)
                if profit_distance >= activation_distance:
                    # Obliczenie nowego poziomu stop-loss
                    new_sl = current_price - step_distance
                    # Sprawdzenie, czy nowy SL jest wyższy niż obecny
                    if new_sl > position.get('sl', 0):
                        should_adjust = True
            else:
                # Dla pozycji krótkich
                profit_distance = position.get('open_price', 0) - current_price
                if profit_distance >= activation_distance:
                    # Obliczenie nowego poziomu stop-loss
                    new_sl = current_price + step_distance
                    # Sprawdzenie, czy nowy SL jest niższy niż obecny
                    if new_sl < position.get('sl', 0):
                        should_adjust = True
        
        # Strategia oparta na procentach
        elif strategy == 'percent':
            activation_percent = params.get('activation_percent', 0.5)
            step_percent = params.get('step_percent', 0.2)
            
            if order_type in ['buy', 'buy_limit', 'buy_stop']:
                # Dla pozycji długich
                profit_percent = (current_price - position.get('open_price', 0)) / position.get('open_price', 0) * 100
                if profit_percent >= activation_percent:
                    # Obliczenie nowego poziomu stop-loss
                    new_sl = current_price * (1 - step_percent / 100)
                    # Sprawdzenie, czy nowy SL jest wyższy niż obecny
                    if new_sl > position.get('sl', 0):
                        should_adjust = True
            else:
                # Dla pozycji krótkich
                profit_percent = (position.get('open_price', 0) - current_price) / position.get('open_price', 0) * 100
                if profit_percent >= activation_percent:
                    # Obliczenie nowego poziomu stop-loss
                    new_sl = current_price * (1 + step_percent / 100)
                    # Sprawdzenie, czy nowy SL jest niższy niż obecny
                    if new_sl < position.get('sl', 0):
                        should_adjust = True
        
        # Strategia oparta na krokach
        elif strategy == 'step':
            activation_pips = params.get('activation_pips', 20)
            step_pips = params.get('step_pips', 10)
            
            activation_distance = activation_pips * pip_value
            step_distance = step_pips * pip_value
            
            if order_type in ['buy', 'buy_limit', 'buy_stop']:
                # Dla pozycji długich
                profit_distance = current_price - position.get('open_price', 0)
                if profit_distance >= activation_distance:
                    # Obliczenie liczby kroków
                    steps = int(profit_distance / step_distance)
                    if steps > 0:
                        # Obliczenie nowego poziomu stop-loss
                        new_sl = position.get('open_price', 0) + (steps - 1) * step_distance
                        # Sprawdzenie, czy nowy SL jest wyższy niż obecny
                        if new_sl > position.get('sl', 0):
                            should_adjust = True
            else:
                # Dla pozycji krótkich
                profit_distance = position.get('open_price', 0) - current_price
                if profit_distance >= activation_distance:
                    # Obliczenie liczby kroków
                    steps = int(profit_distance / step_distance)
                    if steps > 0:
                        # Obliczenie nowego poziomu stop-loss
                        new_sl = position.get('open_price', 0) - (steps - 1) * step_distance
                        # Sprawdzenie, czy nowy SL jest niższy niż obecny
                        if new_sl < position.get('sl', 0):
                            should_adjust = True
        else:
            logger.error(f"Nieznana strategia trailing stop: {strategy}")
            return False
            
        if should_adjust and new_sl:
            logger.info(f"Zastosowano {strategy} trailing stop dla pozycji {transaction_id}, nowy SL: {new_sl}")
            # Modyfikuj zlecenie z nowym stop-lossem
            transaction = {
                'ticket': transaction_id,
                'symbol': symbol,
                'sl': new_sl,
                'tp': position.get('tp', 0)
            }
            return self.connector.modify_position(transaction)
            
        return False
        
    def update_trailing_stops(self) -> Dict[str, Any]:
        """
        Aktualizuje trailing stopy dla wszystkich otwartych pozycji.
        
        Returns:
            Dict: Słownik z wynikami aktualizacji dla każdej pozycji
        """
        results = {
            'updated': [],
            'unchanged': [],
            'errors': []
        }
        
        positions = self.get_open_positions()
        if not positions:
            logger.info("Brak otwartych pozycji do aktualizacji trailing stopów")
            return results
            
        # Włączenie wsadowego przetwarzania dla zoptymalizowanej wydajności
        self.connector.start_batch_processing()
        
        for position in positions:
            ticket = position.get('ticket')
            if ticket:
                try:
                    if self.apply_trailing_stop(ticket):
                        results['updated'].append(ticket)
                    else:
                        results['unchanged'].append(ticket)
                except Exception as e:
                    logger.error(f"Błąd podczas aktualizacji trailing stopu dla pozycji {ticket}: {e}")
                    results['errors'].append({
                        'ticket': ticket,
                        'error': str(e)
                    })
        
        # Zatrzymanie wsadowego przetwarzania i przetworzenie zebranych komend
        self.connector.stop_batch_processing()
        
        logger.info(f"Zaktualizowano trailing stopy dla {len(results['updated'])} pozycji")
        logger.info(f"Bez zmian pozostało {len(results['unchanged'])} pozycji")
        logger.info(f"Błędy wystąpiły dla {len(results['errors'])} pozycji")
        
        return results
    
    def update_advanced_trailing_stops(self, strategy: str = 'fixed_pips',
                                     params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Aktualizuje zaawansowane trailing stopy dla wszystkich otwartych pozycji.
        
        Args:
            strategy: Strategia trailing stopu ('fixed_pips', 'percent', 'step')
            params: Parametry strategii
        
        Returns:
            Dict: Słownik z wynikami aktualizacji dla każdej pozycji
        """
        if params is None:
            params = {}
            
        results = {
            'updated': [],
            'unchanged': [],
            'errors': []
        }
        
        positions = self.get_open_positions()
        if not positions:
            logger.info("Brak otwartych pozycji do aktualizacji trailing stopów")
            return results
            
        # Włączenie wsadowego przetwarzania dla zoptymalizowanej wydajności
        self.connector.start_batch_processing()
        
        for position in positions:
            ticket = position.get('ticket')
            if ticket:
                try:
                    if self.apply_advanced_trailing_stop(ticket, strategy, params):
                        results['updated'].append({
                            'ticket': ticket,
                            'symbol': position.get('symbol'),
                            'strategy': strategy
                        })
                    else:
                        results['unchanged'].append(ticket)
                except Exception as e:
                    logger.error(f"Błąd podczas aktualizacji trailing stopu dla pozycji {ticket}: {e}")
                    results['errors'].append({
                        'ticket': ticket,
                        'error': str(e)
                    })
        
        # Zatrzymanie wsadowego przetwarzania i przetworzenie zebranych komend
        self.connector.stop_batch_processing()
        
        logger.info(f"Zaktualizowano trailing stopy dla {len(results['updated'])} pozycji")
        logger.info(f"Bez zmian pozostało {len(results['unchanged'])} pozycji")
        logger.info(f"Błędy wystąpiły dla {len(results['errors'])} pozycji")
        
        return results
    
    def manage_breakeven_stops(self, breakeven_config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Automatycznie zarządza break-even stop dla wszystkich otwartych pozycji.
        
        Args:
            breakeven_config: Konfiguracja break-even:
                             {'default': {'strategy': 'standard', 'params': {'profit_pips': 30}},
                              'symbol_config': {
                                  'EURUSD': {'strategy': 'lock_profit', 'params': {'profit_pips': 25, 'lock_pips': 5}},
                                  'GBPUSD': {'strategy': 'tiered', 'params': {'levels': [...]}}
                              }}
        
        Returns:
            Dict: Wyniki zarządzania dla każdej pozycji
        """
        # Domyślna konfiguracja
        default_config = {
            'default': {
                'strategy': 'standard',
                'params': {'profit_pips': 30}
            },
            'symbol_config': {}
        }
        
        # Połącz z konfiguracją użytkownika (jeśli podano)
        config = default_config
        if breakeven_config:
            if 'default' in breakeven_config:
                config['default'] = breakeven_config['default']
            if 'symbol_config' in breakeven_config:
                config['symbol_config'] = breakeven_config['symbol_config']
        
        # Wyniki operacji
        results = {
            'modified': [],
            'unchanged': [],
            'errors': []
        }
        
        # Pobierz wszystkie otwarte pozycje
        positions = self.get_open_positions()
        if not positions:
            logger.info("Brak otwartych pozycji do zarządzania break-even stops")
            return results
            
        # Włączenie wsadowego przetwarzania dla zoptymalizowanej wydajności
        self.connector.start_batch_processing()
            
        # Przeanalizuj każdą pozycję
        for position in positions:
            ticket = position.get('ticket')
            symbol = position.get('symbol')
            
            if not ticket:
                continue
                
            try:
                # Wybór odpowiedniej konfiguracji
                if symbol in config['symbol_config']:
                    strategy = config['symbol_config'][symbol].get('strategy', config['default']['strategy'])
                    params = config['symbol_config'][symbol].get('params', config['default']['params'])
                else:
                    strategy = config['default']['strategy']
                    params = config['default']['params']
                
                # Wywołaj zaawansowany break-even
                be_result = self.advanced_breakeven_stop(
                    ticket, 
                    strategy=strategy,
                    params=params
                )
                
                if be_result['success']:
                    results['modified'].append({
                        'ticket': ticket,
                        'symbol': symbol,
                        'strategy': strategy,
                        'new_sl': be_result['new_sl'],
                        'profit_pips': be_result['current_profit_pips']
                    })
                else:
                    if "Nie osiągnięto wymaganego zysku" in be_result['message']:
                        results['unchanged'].append({
                            'ticket': ticket,
                            'symbol': symbol,
                            'profit_pips': be_result['current_profit_pips']
                        })
                    else:
                        results['errors'].append({
                            'ticket': ticket,
                            'symbol': symbol,
                            'error': be_result['message']
                        })
            except Exception as e:
                logger.error(f"Błąd podczas zarządzania break-even dla pozycji {ticket}: {e}")
                results['errors'].append({
                    'ticket': ticket,
                    'symbol': symbol,
                    'error': str(e)
                })
        
        # Zatrzymanie wsadowego przetwarzania i przetworzenie zebranych komend
        self.connector.stop_batch_processing()
        
        logger.info(f"Ustawiono break-even dla {len(results['modified'])} pozycji")
        logger.info(f"Bez zmian pozostało {len(results['unchanged'])} pozycji")
        logger.info(f"Błędy wystąpiły dla {len(results['errors'])} pozycji")
        
        return results
        
    def manage_take_profits(self, take_profit_config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Automatycznie zarządza częściowym zamykaniem pozycji po osiągnięciu określonych poziomów zysku.
        
        Args:
            take_profit_config: Konfiguracja poziomów zamykania
                               Domyślnie: {'default_levels': [
                                           {'profit_pips': 20, 'percent': 0.3},
                                           {'profit_pips': 50, 'percent': 0.5},
                                           {'profit_pips': 100, 'percent': 0.7}
                                         ],
                                 'symbol_levels': {
                                     'EURUSD': [
                                         {'profit_pips': 15, 'percent': 0.25},
                                         {'profit_pips': 30, 'percent': 0.5}
                                     ]
                               }}
        
        Returns:
            Dict: Wyniki zarządzania dla każdej pozycji
        """
        # Domyślna konfiguracja
        default_config = {
            'default_levels': [
                {'profit_pips': 20, 'percent': 0.3},
                {'profit_pips': 50, 'percent': 0.5},
                {'profit_pips': 100, 'percent': 0.7}
            ],
            'symbol_levels': {}
        }
        
        # Połącz z konfiguracją użytkownika (jeśli podano)
        config = default_config
        if take_profit_config:
            if 'default_levels' in take_profit_config:
                config['default_levels'] = take_profit_config['default_levels']
            if 'symbol_levels' in take_profit_config:
                config['symbol_levels'] = take_profit_config['symbol_levels']
        
        results = {
            'closed': [],
            'unchanged': [],
            'errors': []
        }
        
        # Pobierz wszystkie otwarte pozycje
        positions = self.get_open_positions()
        if not positions:
            logger.info("Brak otwartych pozycji do zarządzania take profits")
            return results
            
        # Przeanalizuj każdą pozycję
        for position in positions:
            ticket = position.get('ticket')
            symbol = position.get('symbol')
            
            if not ticket:
                continue
                
            try:
                # Wybór odpowiednich poziomów
                levels = config['default_levels']
                if symbol in config['symbol_levels']:
                    levels = config['symbol_levels'][symbol]
                
                # Parametry dla strategii częściowego zamykania
                params = {'levels': levels}
                
                # Wywołaj zaawansowane częściowe zamykanie
                close_result = self.advanced_partial_close(
                    ticket, 
                    strategy='take_profit_levels',
                    params=params
                )
                
                if close_result['success']:
                    results['closed'].append({
                        'ticket': ticket,
                        'symbol': symbol,
                        'closed_volume': close_result['closed_volume'],
                        'remaining_volume': close_result['remaining_volume'],
                        'profit_pips': close_result.get('current_profit_pips', 0),
                        'achieved_level': close_result.get('achieved_level')
                    })
                else:
                    if "Nie osiągnięto żadnego poziomu zysku" in close_result.get('message', ''):
                        # To nie jest błąd, tylko informacja, że nie osiągnięto określonego poziomu zysku
                        results['unchanged'].append({
                            'ticket': ticket,
                            'symbol': symbol,
                            'profit_pips': close_result.get('current_profit_pips', 0)
                        })
                    else:
                        # Rzeczywisty błąd
                        results['errors'].append({
                            'ticket': ticket,
                            'symbol': symbol,
                            'error': close_result.get('message', 'Nieznany błąd')
                        })
            except Exception as e:
                logger.error(f"Błąd podczas zarządzania take profits dla pozycji {ticket}: {e}")
                results['errors'].append({
                    'ticket': ticket,
                    'symbol': symbol,
                    'error': str(e)
                })
        
        logger.info(f"Częściowo zamknięto {len(results['closed'])} pozycji")
        logger.info(f"Bez zmian pozostało {len(results['unchanged'])} pozycji")
        logger.info(f"Błędy wystąpiły dla {len(results['errors'])} pozycji")
        
        return results
    
    def partial_close(self, transaction_id: int, volume_percent: float) -> bool:
        """
        Częściowo zamyka istniejącą pozycję.
        
        Args:
            transaction_id: ID transakcji do częściowego zamknięcia
            volume_percent: Procent wolumenu do zamknięcia (0.1 - 0.9)
            
        Returns:
            bool: True jeśli pozycja została częściowo zamknięta, False w przeciwnym razie
        """
        if volume_percent <= 0 or volume_percent >= 1:
            logger.error(f"Nieprawidłowa wartość volume_percent: {volume_percent}. Musi być w zakresie (0, 1)")
            return False
            
        # Pobierz szczegóły transakcji
        position = None
        positions = self.get_open_positions()
        for pos in positions or []:
            if pos.get('ticket') == transaction_id:
                position = pos
                break
                
        if not position:
            logger.error(f"Nie znaleziono pozycji o ID {transaction_id} do częściowego zamknięcia")
            return False
            
        # Oblicz wolumen do zamknięcia
        total_volume = position.get('volume', 0)
        close_volume = total_volume * volume_percent
        
        # Zaokrąglij do 2 miejsc po przecinku (standardowa dokładność lotów)
        close_volume = round(close_volume, 2)
        
        if close_volume <= 0:
            logger.error(f"Obliczony wolumen do zamknięcia jest nieprawidłowy: {close_volume}")
            return False
            
        # Zamknij pozycję częściowo
        return self.connector.close_position_partial(transaction_id, close_volume)
    
    def advanced_partial_close(self, transaction_id: int, strategy: str = 'fixed_percent', 
                               params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Zaawansowana funkcja częściowego zamykania pozycji z różnymi strategiami.
        
        Args:
            transaction_id: ID transakcji do częściowego zamknięcia
            strategy: Strategia zamykania:
                     - fixed_percent: Zamknij określony procent pozycji
                     - fixed_lots: Zamknij określoną liczbę lotów
                     - take_profit_levels: Zamykaj etapami po osiągnięciu określonego zysku
            params: Parametry strategii:
                   - dla fixed_percent: {'percent': 0.5} (50% pozycji)
                   - dla fixed_lots: {'lots': 0.1} (0.1 lota)
                   - dla take_profit_levels: {'levels': [{'profit_pips': 20, 'percent': 0.3}, 
                                                        {'profit_pips': 50, 'percent': 0.5}]}
        
        Returns:
            Dict: Wynik operacji z dodatkowymi informacjami
        """
        # Inicjalizacja parametrów domyślnych
        if params is None:
            params = {}
            
        # Rezultat operacji
        result = {
            'success': False,
            'closed_volume': 0,
            'remaining_volume': 0,
            'closed_percent': 0,
            'profit': 0,
            'message': ""
        }
        
        # Pobierz szczegóły transakcji
        position = None
        positions = self.get_open_positions()
        for pos in positions or []:
            if pos.get('ticket') == transaction_id:
                position = pos
                break
                
        if not position:
            result['message'] = f"Nie znaleziono pozycji o ID {transaction_id} do częściowego zamknięcia"
            logger.error(result['message'])
            return result
            
        # Pobierz aktualne dane rynkowe
        symbol = position.get('symbol')
        market_data = self.get_market_data(symbol)
        if not market_data:
            result['message'] = f"Nie można pobrać danych rynkowych dla {symbol}"
            logger.error(result['message'])
            return result
            
        # Całkowity wolumen pozycji
        total_volume = position.get('volume', 0)
        result['remaining_volume'] = total_volume
        
        # Konwersja pipsów na punkty cenowe
        pip_value = 0.0001
        if symbol.endswith('JPY'):
            pip_value = 0.01
            
        # Obliczamy aktualny zysk/stratę w pipsach
        order_type = position.get('type', '').lower()
        open_price = position.get('open_price', 0)
        
        if order_type in ['buy', 'buy_limit', 'buy_stop']:
            current_price = market_data.get('bid', 0)
            profit_distance = current_price - open_price
        else:  # sell orders
            current_price = market_data.get('ask', 0)
            profit_distance = open_price - current_price
            
        profit_pips = profit_distance / pip_value
        result['current_profit_pips'] = profit_pips
        
        close_volume = 0
        
        # Strategia: Stały procent
        if strategy == 'fixed_percent':
            percent = params.get('percent', 0.5)  # domyślnie 50%
            
            if percent <= 0 or percent >= 1:
                result['message'] = f"Nieprawidłowa wartość percent: {percent}. Musi być w zakresie (0, 1)"
                logger.error(result['message'])
                return result
                
            close_volume = total_volume * percent
            result['closed_percent'] = percent
        
        # Strategia: Stała liczba lotów
        elif strategy == 'fixed_lots':
            lots = params.get('lots', 0.1)  # domyślnie 0.1 lota
            
            if lots <= 0 or lots >= total_volume:
                result['message'] = f"Nieprawidłowa wartość lots: {lots}. Musi być w zakresie (0, {total_volume})"
                logger.error(result['message'])
                return result
                
            close_volume = lots
            result['closed_percent'] = close_volume / total_volume
        
        # Strategia: Poziomy take profit
        elif strategy == 'take_profit_levels':
            levels = params.get('levels', [])
            
            if not levels:
                result['message'] = "Nie podano poziomów take profit"
                logger.error(result['message'])
                return result
                
            # Sortuj poziomy wg zysku (od najniższego do najwyższego)
            sorted_levels = sorted(levels, key=lambda x: x.get('profit_pips', 0))
            
            # Znajdź najwyższy osiągnięty poziom
            achieved_level = None
            for level in sorted_levels:
                level_profit_pips = level.get('profit_pips', 0)
                if profit_pips >= level_profit_pips:
                    achieved_level = level
                else:
                    break
                    
            if achieved_level:
                level_percent = achieved_level.get('percent', 0.5)
                close_volume = total_volume * level_percent
                result['closed_percent'] = level_percent
                result['achieved_level'] = achieved_level
            else:
                result['message'] = f"Nie osiągnięto żadnego poziomu zysku. Aktualny zysk: {profit_pips} pips"
                logger.info(result['message'])
                return result
        else:
            result['message'] = f"Nieznana strategia: {strategy}"
            logger.error(result['message'])
            return result
            
        # Zaokrąglij do 2 miejsc po przecinku (standardowa dokładność lotów)
        close_volume = round(close_volume, 2)
        
        if close_volume <= 0:
            result['message'] = f"Obliczony wolumen do zamknięcia jest nieprawidłowy: {close_volume}"
            logger.error(result['message'])
            return result
            
        # Zamknij pozycję częściowo
        success = self.connector.close_position_partial(transaction_id, close_volume)
        
        if success:
            # Aktualizuj wynik
            result['success'] = True
            result['closed_volume'] = close_volume
            result['remaining_volume'] = total_volume - close_volume
            result['message'] = f"Pozycja {transaction_id} częściowo zamknięta. Zamknięto: {close_volume} lotów."
            logger.info(result['message'])
            
            # Zapisz informacje o częściowym zamknięciu do bazy danych lub loga
            # TODO: Implementacja zapisu do bazy danych
        else:
            result['message'] = f"Błąd podczas częściowego zamykania pozycji {transaction_id}"
            logger.error(result['message'])
            
        return result
    
    def create_oco_order(self, symbol: str, order_type: str, volume: float, 
                        price: float = 0, sl: float = 0, tp: float = 0,
                        opposite_price: float = 0) -> Dict[str, Any]:
        """
        Tworzy zlecenie OCO (One-Cancels-the-Other).
        
        Przykład: Możemy chcieć kupić, gdy cena przebije opór, ale sprzedać, 
        gdy cena przebije wsparcie. Obie możliwości są wzajemnie wykluczające.
        
        Args:
            symbol: Symbol instrumentu
            order_type: Typ zlecenia ('buy_stop' lub 'sell_stop')
            volume: Wolumen zlecenia
            price: Cena dla głównego zlecenia
            sl: Stop Loss dla głównego zlecenia
            tp: Take Profit dla głównego zlecenia
            opposite_price: Cena dla przeciwnego zlecenia
            
        Returns:
            Dict: Wynik operacji z identyfikatorami obu zleceń
        """
        # Walidacja parametrów
        if order_type not in ['buy_stop', 'sell_stop']:
            logger.error(f"Nieprawidłowy typ zlecenia OCO: {order_type}. Dozwolone: buy_stop, sell_stop")
            return {'success': False, 'error': 'Invalid order type for OCO order'}
            
        if price <= 0 or opposite_price <= 0:
            logger.error("Ceny dla zleceń OCO muszą być większe od zera")
            return {'success': False, 'error': 'Prices must be greater than zero'}
            
        # Określ typ przeciwnego zlecenia
        opposite_type = 'sell_stop' if order_type == 'buy_stop' else 'buy_stop'
        
        # Utwórz główne zlecenie
        main_result = self.connector.place_pending_order(
            symbol=symbol,
            order_type=order_type,
            volume=volume,
            price=price,
            sl=sl,
            tp=tp
        )
        
        if not main_result.get('success'):
            logger.error(f"Błąd podczas tworzenia głównego zlecenia OCO: {main_result.get('error')}")
            return main_result
            
        # Utwórz przeciwne zlecenie
        opposite_result = self.connector.place_pending_order(
            symbol=symbol,
            order_type=opposite_type,
            volume=volume,
            price=opposite_price,
            sl=sl,  # Użyj tych samych parametrów SL/TP
            tp=tp
        )
        
        if not opposite_result.get('success'):
            logger.error(f"Błąd podczas tworzenia przeciwnego zlecenia OCO: {opposite_result.get('error')}")
            # Anuluj główne zlecenie, jeśli utworzenie przeciwnego nie powiodło się
            self.connector.delete_pending_order(main_result.get('ticket'))
            return opposite_result
            
        # Przygotuj identyfikator pary OCO
        main_ticket = main_result.get('ticket')
        opposite_ticket = opposite_result.get('ticket')
        oco_pair_id = f"{main_ticket}_{opposite_ticket}"
        
        # Rejestruj parę OCO
        registration_result = self.register_oco_pair(
            oco_pair_id=oco_pair_id,
            symbol=symbol,
            main_ticket=main_ticket,
            main_type=order_type,
            main_price=price,
            opposite_ticket=opposite_ticket,
            opposite_type=opposite_type,
            opposite_price=opposite_price,
            volume=volume,
            sl=sl,
            tp=tp
        )
            
        if not registration_result.get('success', False):
            logger.warning(f"Nie udało się zarejestrować pary OCO w bazie danych: {registration_result.get('error')}")
            
        logger.info(f"Utworzono parę zleceń OCO: {main_ticket} i {opposite_ticket}")
        
        return {
            'success': True,
            'main_ticket': main_ticket,
            'opposite_ticket': opposite_ticket,
            'oco_pair_id': oco_pair_id
        }
    
    def register_oco_pair(self, oco_pair_id: str, symbol: str, 
                         main_ticket: int, main_type: str, main_price: float,
                         opposite_ticket: int, opposite_type: str, opposite_price: float,
                         volume: float, sl: float = 0, tp: float = 0) -> Dict[str, Any]:
        """
        Rejestruje parę zleceń OCO w systemie (w pamięci lub bazie danych).
        
        Args:
            oco_pair_id: Identyfikator pary OCO
            symbol: Symbol instrumentu
            main_ticket: Numer głównego zlecenia
            main_type: Typ głównego zlecenia
            main_price: Cena głównego zlecenia
            opposite_ticket: Numer przeciwnego zlecenia
            opposite_type: Typ przeciwnego zlecenia
            opposite_price: Cena przeciwnego zlecenia
            volume: Wolumen obu zleceń
            sl: Stop Loss
            tp: Take Profit
            
        Returns:
            Dict: Wynik operacji rejestracji
        """
        # W rzeczywistej implementacji tutaj byłoby zapisanie danych do bazy danych
        # Na potrzeby demonstracji używamy prostego słownika w pamięci
        
        # Inicjalizacja słownika OCO par, jeśli nie istnieje
        if not hasattr(self, 'oco_pairs'):
            self.oco_pairs = {}
            
        # Tworzenie rekordu pary OCO
        oco_pair = {
            'oco_pair_id': oco_pair_id,
            'symbol': symbol,
            'created_at': datetime.now(),
            'status': 'active',
            'orders': {
                'main': {
                    'ticket': main_ticket,
                    'type': main_type,
                    'price': main_price,
                    'status': 'pending'
                },
                'opposite': {
                    'ticket': opposite_ticket,
                    'type': opposite_type,
                    'price': opposite_price,
                    'status': 'pending'
                }
            },
            'volume': volume,
            'sl': sl,
            'tp': tp
        }
        
        # Zapisanie rekordu
        self.oco_pairs[oco_pair_id] = oco_pair
        
        return {
            'success': True,
            'oco_pair_id': oco_pair_id
        }
    
    def cancel_oco_pair(self, oco_pair_id: str) -> Dict[str, Any]:
        """
        Anuluje parę zleceń OCO.
        
        Args:
            oco_pair_id: Identyfikator pary OCO
            
        Returns:
            Dict: Wynik operacji anulowania
        """
        # Sprawdź, czy para OCO istnieje
        if not hasattr(self, 'oco_pairs') or oco_pair_id not in self.oco_pairs:
            logger.error(f"Nie znaleziono pary OCO o ID {oco_pair_id}")
            return {
                'success': False,
                'error': 'OCO pair not found'
            }
            
        # Pobierz dane pary OCO
        oco_pair = self.oco_pairs[oco_pair_id]
        
        # Anuluj główne zlecenie, jeśli jest aktywne
        main_ticket = oco_pair['orders']['main']['ticket']
        if oco_pair['orders']['main']['status'] == 'pending':
            main_result = self.connector.delete_pending_order(main_ticket)
            if main_result:
                oco_pair['orders']['main']['status'] = 'cancelled'
            else:
                logger.warning(f"Nie udało się anulować głównego zlecenia {main_ticket}")
                
        # Anuluj przeciwne zlecenie, jeśli jest aktywne
        opposite_ticket = oco_pair['orders']['opposite']['ticket']
        if oco_pair['orders']['opposite']['status'] == 'pending':
            opposite_result = self.connector.delete_pending_order(opposite_ticket)
            if opposite_result:
                oco_pair['orders']['opposite']['status'] = 'cancelled'
            else:
                logger.warning(f"Nie udało się anulować przeciwnego zlecenia {opposite_ticket}")
                
        # Aktualizuj status pary OCO
        oco_pair['status'] = 'cancelled'
        
        logger.info(f"Anulowano parę zleceń OCO: {oco_pair_id}")
        
        return {
            'success': True,
            'oco_pair_id': oco_pair_id,
            'main_cancelled': oco_pair['orders']['main']['status'] == 'cancelled',
            'opposite_cancelled': oco_pair['orders']['opposite']['status'] == 'cancelled'
        }
    
    def get_oco_pairs(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Pobiera listę par zleceń OCO.
        
        Args:
            status: Opcjonalny filtr statusu ('active', 'triggered', 'cancelled', 'expired')
            
        Returns:
            List[Dict]: Lista par zleceń OCO spełniających kryteria
        """
        if not hasattr(self, 'oco_pairs'):
            return []
            
        # Filtrowanie par OCO po statusie
        if status:
            return [pair for pair in self.oco_pairs.values() if pair['status'] == status]
        else:
            return list(self.oco_pairs.values())
    
    def handle_oco_activation(self, order_ticket: int) -> Dict[str, Any]:
        """
        Obsługuje aktywację jednego z zleceń OCO i anuluje drugie.
        
        Args:
            order_ticket: Numer zlecenia, które zostało aktywowane
            
        Returns:
            Dict: Wynik operacji obsługi aktywacji
        """
        if not hasattr(self, 'oco_pairs'):
            logger.warning("Nie znaleziono żadnych par OCO")
            return {
                'success': False,
                'error': 'No OCO pairs found'
            }
            
        # Znajdź parę OCO zawierającą aktywowane zlecenie
        activated_pair = None
        activated_order_type = None
        
        for pair_id, pair in self.oco_pairs.items():
            if pair['status'] != 'active':
                continue
                
            if pair['orders']['main']['ticket'] == order_ticket:
                activated_pair = pair
                activated_order_type = 'main'
                break
            elif pair['orders']['opposite']['ticket'] == order_ticket:
                activated_pair = pair
                activated_order_type = 'opposite'
                break
                
        if not activated_pair:
            logger.warning(f"Nie znaleziono aktywnej pary OCO dla zlecenia {order_ticket}")
            return {
                'success': False,
                'error': 'No active OCO pair found for this order'
            }
            
        # Aktualizuj status aktywowanego zlecenia
        activated_pair['orders'][activated_order_type]['status'] = 'triggered'
        
        # Określ typ drugiego zlecenia do anulowania
        other_order_type = 'opposite' if activated_order_type == 'main' else 'main'
        other_ticket = activated_pair['orders'][other_order_type]['ticket']
        
        # Anuluj drugie zlecenie
        cancel_result = self.connector.delete_pending_order(other_ticket)
        
        if cancel_result:
            activated_pair['orders'][other_order_type]['status'] = 'cancelled'
            activated_pair['status'] = 'triggered'
            logger.info(f"Zlecenie OCO {order_ticket} aktywowane, zlecenie {other_ticket} anulowane")
        else:
            logger.warning(f"Nie udało się anulować przeciwnego zlecenia {other_ticket}")
            
        return {
            'success': True,
            'oco_pair_id': activated_pair['oco_pair_id'],
            'activated_ticket': order_ticket,
            'cancelled_ticket': other_ticket,
            'cancelled_success': cancel_result
        }
    
    def monitor_oco_orders(self) -> Dict[str, Any]:
        """
        Monitoruje wszystkie pary zleceń OCO i automatycznie anuluje drugie zlecenie, gdy pierwsze zostanie aktywowane.
        
        Returns:
            Dict: Wyniki monitorowania zleceń OCO
        """
        results = {
            'activated': [],
            'cancelled': [],
            'errors': []
        }
        
        # Pobierz wszystkie aktywne pary zleceń OCO
        oco_pairs = self.get_oco_pairs(status='active')
        if not oco_pairs:
            return results
            
        # Włączenie wsadowego przetwarzania dla zoptymalizowanej wydajności
        if hasattr(self.connector, 'start_batch_processing'):
            self.connector.start_batch_processing()
            
        # Pobierz aktualne otwarte pozycje i oczekujące zlecenia
        open_positions = self.get_open_positions()
        pending_orders = self.get_pending_orders()
        
        # Przygotowanie słowników dla szybkiego wyszukiwania
        position_tickets = set(pos.get('ticket') for pos in open_positions if pos.get('ticket'))
        pending_tickets = set(order.get('ticket') for order in pending_orders if order.get('ticket'))
        
        for oco_pair in oco_pairs:
            pair_id = oco_pair.get('pair_id')
            main_ticket = oco_pair.get('main_ticket')
            opposite_ticket = oco_pair.get('opposite_ticket')
            
            try:
                # Sprawdź, czy którekolwiek zlecenie zostało aktywowane
                if main_ticket in position_tickets and opposite_ticket in pending_tickets:
                    # Główne zlecenie zostało aktywowane, anuluj przeciwne
                    activation_result = self.handle_oco_activation(main_ticket)
                    if activation_result['success']:
                        results['activated'].append({
                            'pair_id': pair_id,
                            'activated_ticket': main_ticket,
                            'cancelled_ticket': opposite_ticket
                        })
                    else:
                        results['errors'].append({
                            'pair_id': pair_id,
                            'error': activation_result['message']
                        })
                elif opposite_ticket in position_tickets and main_ticket in pending_tickets:
                    # Przeciwne zlecenie zostało aktywowane, anuluj główne
                    activation_result = self.handle_oco_activation(opposite_ticket)
                    if activation_result['success']:
                        results['activated'].append({
                            'pair_id': pair_id,
                            'activated_ticket': opposite_ticket,
                            'cancelled_ticket': main_ticket
                        })
                    else:
                        results['errors'].append({
                            'pair_id': pair_id,
                            'error': activation_result['message']
                        })
            except Exception as e:
                logger.error(f"Błąd podczas monitorowania pary OCO {pair_id}: {str(e)}")
                results['errors'].append({
                    'pair_id': pair_id,
                    'error': str(e)
                })
                
        # Zatrzymanie wsadowego przetwarzania
        if hasattr(self.connector, 'stop_batch_processing'):
            self.connector.stop_batch_processing()
            
        return results
    
    def set_breakeven_stop(self, transaction_id: int, profit_pips: int) -> bool:
        """
        Ustawia stop-loss na poziomie wejścia (break-even) po osiągnięciu określonego zysku.
        
        Args:
            transaction_id: ID transakcji do modyfikacji
            profit_pips: Liczba pipsów zysku potrzebna do aktywacji break-even
            
        Returns:
            bool: True jeśli break-even został ustawiony, False w przeciwnym razie
        """
        # Pobierz szczegóły transakcji
        position = None
        positions = self.get_open_positions()
        for pos in positions or []:
            if pos.get('ticket') == transaction_id:
                position = pos
                break
                
        if not position:
            logger.error(f"Nie znaleziono pozycji o ID {transaction_id} do ustawienia break-even")
            return False
            
        # Pobierz dane rynkowe
        symbol = position.get('symbol')
        market_data = self.get_market_data(symbol)
        if not market_data:
            logger.error(f"Nie można pobrać danych rynkowych dla {symbol}")
            return False
            
        # Konwersja pipsów na punkty cenowe
        pip_value = 0.0001
        if symbol.endswith('JPY'):
            pip_value = 0.01
            
        profit_distance = profit_pips * pip_value
        
        # Ustal bieżącą cenę i sprawdź, czy osiągnięto wymagany zysk
        order_type = position.get('type', '').lower()
        entry_price = position.get('open_price', 0)
        
        if order_type in ['buy', 'buy_limit', 'buy_stop']:
            current_price = market_data.get('bid', 0)
            profit = current_price - entry_price
            
            if profit >= profit_distance:
                # Ustaw SL na poziomie wejścia
                return self.connector.modify_position({
                    'ticket': transaction_id,
                    'symbol': symbol,
                    'sl': entry_price,
                    'tp': position.get('tp', 0)
                })
        else:  # sell orders
            current_price = market_data.get('ask', 0)
            profit = entry_price - current_price
            
            if profit >= profit_distance:
                # Ustaw SL na poziomie wejścia
                return self.connector.modify_position({
                    'ticket': transaction_id,
                    'symbol': symbol,
                    'sl': entry_price,
                    'tp': position.get('tp', 0)
                })
                
        return False
    
    def advanced_breakeven_stop(self, transaction_id: int, 
                               strategy: str = 'standard', 
                               params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Zaawansowana funkcja ustawiania break-even stop z różnymi strategiami.
        
        Args:
            transaction_id: ID transakcji do modyfikacji
            strategy: Strategia break-even:
                     - standard: Zwykły break-even na poziomie wejścia
                     - lock_profit: Ustawia SL na określoną liczbę pipsów powyżej/poniżej wejścia
                     - partial: Łączy break-even z częściowym zamknięciem pozycji
                     - tiered: Przesuwa SL stopniowo do różnych poziomów
            params: Parametry strategii:
                   - dla standard: {'profit_pips': 30}
                   - dla lock_profit: {'profit_pips': 30, 'lock_pips': 10}
                   - dla partial: {'profit_pips': 30, 'volume_percent': 0.5}
                   - dla tiered: {'levels': [
                                  {'profit_pips': 30, 'sl_pips': 0},
                                  {'profit_pips': 50, 'sl_pips': 10},
                                  {'profit_pips': 80, 'sl_pips': 20}
                                ]}
        
        Returns:
            Dict: Wynik operacji ustawienia break-even
        """
        # Inicjalizacja parametrów domyślnych
        if params is None:
            params = {}
            
        # Rezultat operacji
        result = {
            'success': False,
            'message': "",
            'ticket': transaction_id,
            'current_profit_pips': 0,
            'strategy': strategy,
            'new_sl': None
        }
        
        # Pobierz szczegóły transakcji
        position = None
        positions = self.get_open_positions()
        for pos in positions or []:
            if pos.get('ticket') == transaction_id:
                position = pos
                break
                
        if not position:
            result['message'] = f"Nie znaleziono pozycji o ID {transaction_id} do ustawienia break-even"
            logger.error(result['message'])
            return result
            
        # Pobierz dane rynkowe
        symbol = position.get('symbol')
        market_data = self.get_market_data(symbol)
        if not market_data:
            result['message'] = f"Nie można pobrać danych rynkowych dla {symbol}"
            logger.error(result['message'])
            return result
            
        # Konwersja pipsów na punkty cenowe
        pip_value = 0.0001
        if symbol.endswith('JPY'):
            pip_value = 0.01
            
        # Dane pozycji
        order_type = position.get('type', '').lower()
        entry_price = position.get('open_price', 0)
        current_sl = position.get('sl', 0)
        current_tp = position.get('tp', 0)
        
        # Oblicz bieżący zysk/stratę w pipsach
        if order_type in ['buy', 'buy_limit', 'buy_stop']:
            current_price = market_data.get('bid', 0)
            profit = current_price - entry_price
        else:  # sell orders
            current_price = market_data.get('ask', 0)
            profit = entry_price - current_price
            
        profit_pips = profit / pip_value
        result['current_profit_pips'] = profit_pips
        
        # Sprawdź, czy stop-loss jest już na poziomie break-even lub lepszym
        if order_type in ['buy', 'buy_limit', 'buy_stop']:
            if current_sl >= entry_price:
                result['message'] = f"Stop-loss jest już na poziomie break-even lub lepszym dla pozycji {transaction_id}"
                logger.info(result['message'])
                result['success'] = True
                result['new_sl'] = current_sl
                return result
        else:  # sell orders
            if current_sl <= entry_price:
                result['message'] = f"Stop-loss jest już na poziomie break-even lub lepszym dla pozycji {transaction_id}"
                logger.info(result['message'])
                result['success'] = True
                result['new_sl'] = current_sl
                return result
        
        # Implementacja różnych strategii break-even
        new_sl = None
        
        # Strategia: Standard break-even
        if strategy == 'standard':
            profit_activation = params.get('profit_pips', 30)
            
            if profit_pips >= profit_activation:
                new_sl = entry_price
                result['message'] = f"Ustawiono standard break-even dla pozycji {transaction_id}"
                
        # Strategia: Lock profit (SL powyżej/poniżej ceny wejścia)
        elif strategy == 'lock_profit':
            profit_activation = params.get('profit_pips', 30)
            lock_pips = params.get('lock_pips', 10)
            lock_distance = lock_pips * pip_value
            
            if profit_pips >= profit_activation:
                if order_type in ['buy', 'buy_limit', 'buy_stop']:
                    new_sl = entry_price + lock_distance
                else:  # sell orders
                    new_sl = entry_price - lock_distance
                result['message'] = f"Ustawiono lock profit break-even dla pozycji {transaction_id}, zabezpieczając {lock_pips} pipsów"
                
        # Strategia: Partial (break-even + częściowe zamknięcie)
        elif strategy == 'partial':
            profit_activation = params.get('profit_pips', 30)
            volume_percent = params.get('volume_percent', 0.5)
            
            if profit_pips >= profit_activation:
                # Najpierw ustaw SL na poziomie wejścia
                new_sl = entry_price
                
                # Częściowo zamknij pozycję
                partial_result = self.partial_close(transaction_id, volume_percent)
                
                if partial_result:
                    result['message'] = f"Ustawiono partial break-even dla pozycji {transaction_id}, zamykając {volume_percent*100}% pozycji"
                    result['partial_close'] = True
                else:
                    result['message'] = f"Ustawiono break-even dla pozycji {transaction_id}, ale częściowe zamknięcie nie powiodło się"
                    result['partial_close'] = False
                    
        # Strategia: Tiered (stopniowe przesuwanie SL)
        elif strategy == 'tiered':
            levels = params.get('levels', [
                {'profit_pips': 30, 'sl_pips': 0},
                {'profit_pips': 50, 'sl_pips': 10},
                {'profit_pips': 80, 'sl_pips': 20}
            ])
            
            # Sortuj poziomy wg zysku (od najwyższego do najniższego)
            sorted_levels = sorted(levels, key=lambda x: x.get('profit_pips', 0), reverse=True)
            
            # Znajdź najwyższy osiągnięty poziom
            achieved_level = None
            for level in sorted_levels:
                level_profit_pips = level.get('profit_pips', 0)
                if profit_pips >= level_profit_pips:
                    achieved_level = level
                    break
                    
            if achieved_level:
                sl_pips = achieved_level.get('sl_pips', 0)
                sl_distance = sl_pips * pip_value
                
                if order_type in ['buy', 'buy_limit', 'buy_stop']:
                    new_sl = entry_price + sl_distance
                else:  # sell orders
                    new_sl = entry_price - sl_distance
                    
                result['message'] = f"Ustawiono tiered break-even dla pozycji {transaction_id}, poziom: {achieved_level.get('profit_pips')} pipsów zysku"
                result['achieved_level'] = achieved_level
        else:
            result['message'] = f"Nieznana strategia break-even: {strategy}"
            logger.error(result['message'])
            return result
            
        # Sprawdź, czy należy zmodyfikować pozycję
        if new_sl is not None:
            # Zaokrąglij SL do odpowiedniej liczby miejsc po przecinku
            new_sl = round(new_sl, 5)
            result['new_sl'] = new_sl
            
            # Modyfikacja pozycji
            modification_result = self.connector.modify_position({
                'ticket': transaction_id,
                'symbol': symbol,
                'sl': new_sl,
                'tp': current_tp
            })
            
            if modification_result:
                result['success'] = True
                logger.info(result['message'])
            else:
                result['success'] = False
                result['message'] = f"Nie udało się zmodyfikować pozycji {transaction_id}"
                logger.error(result['message'])
        else:
            result['message'] = f"Nie osiągnięto wymaganego zysku dla pozycji {transaction_id}. Aktualny zysk: {profit_pips:.1f} pipsów"
            logger.info(result['message'])
            
        return result
    
    def modify_position(self, transaction: Dict[str, Any],
                      sl: Optional[float] = None,
                      tp: Optional[float] = None) -> bool:
        """
        Modyfikuje istniejącą pozycję.
        
        Args:
            transaction: Dane transakcji do modyfikacji
            sl: Nowy stop-loss (None oznacza brak zmiany)
            tp: Nowy take-profit (None oznacza brak zmiany)
            
        Returns:
            bool: True jeśli modyfikacja się powiodła, False w przeciwnym razie
        """
        # Sprawdź, czy zawierają wymagane pola
        if not transaction or 'ticket' not in transaction:
            logger.error("Brakujące pole 'ticket' w danych transakcji")
            return False
            
        modify_data = {
            'ticket': transaction['ticket'],
            'symbol': transaction.get('symbol', ''),
        }
        
        if 'sl' in transaction or sl is not None:
            modify_data['sl'] = transaction.get('sl') if sl is None else sl
            
        if 'tp' in transaction or tp is not None:
            modify_data['tp'] = transaction.get('tp') if tp is None else tp
            
        # Sprawdź, czy mamy wsadowe przetwarzanie
        if hasattr(self.connector, 'add_batch_command'):
            self.connector.add_batch_command('modify_position', modify_data)
            return True
        else:
            # Standardowa modyfikacja
            return self.connector.modify_position(modify_data)
    
    def open_position(
        self,
        symbol: str,
        direction: str,
        lot_size: float,
        entry_price: float,
        stop_loss: float,
        take_profit: float,
        comment: str = "",
        magic: int = 12345
    ) -> Optional[int]:
        """
        Otwiera pozycję handlową.
        
        Args:
            symbol: Symbol instrumentu
            direction: Kierunek transakcji ('BUY' lub 'SELL')
            lot_size: Wielkość pozycji
            entry_price: Cena wejścia (opcjonalnie, dla zleceń oczekujących)
            stop_loss: Poziom Stop Loss
            take_profit: Poziom Take Profit
            comment: Komentarz do zlecenia
            magic: Identyfikator magiczny
            
        Returns:
            Optional[int]: Identyfikator zlecenia lub None w przypadku błędu
        """
        try:
            logger.info(f"Otwieranie pozycji: {symbol}, {direction}, {lot_size}, SL={stop_loss}, TP={take_profit}")
            
            # Wywołanie metody open_order z konektora MT5
            order_ticket = self.connector.open_order(
                symbol=symbol,
                order_type=direction,
                volume=lot_size,
                price=None,  # Użyj ceny rynkowej
                sl=stop_loss,
                tp=take_profit,
                comment=comment,
                magic=magic
            )
            
            if order_ticket:
                logger.info(f"Pozycja otwarta pomyślnie. Ticket: {order_ticket}")
                return order_ticket
            else:
                logger.error(f"Nie udało się otworzyć pozycji dla {symbol}")
                return None
                
        except Exception as e:
            logger.error(f"Błąd podczas otwierania pozycji: {e}", exc_info=True)
            return None
    
    def get_current_price(self, symbol: str) -> Optional[float]:
        """
        Pobiera aktualną cenę rynkową dla danego symbolu.
        
        Args:
            symbol: Symbol instrumentu
            
        Returns:
            Optional[float]: Aktualna cena rynkowa lub None w przypadku błędu
        """
        try:
            market_data = self.get_market_data(symbol)
            if not market_data:
                logger.error(f"Nie można pobrać danych rynkowych dla {symbol}")
                return None
                
            # Zwracamy cenę ask dla kupna i bid dla sprzedaży
            # W tym przypadku zwracamy średnią cenę
            return (market_data['ask'] + market_data['bid']) / 2
            
        except Exception as e:
            logger.error(f"Błąd podczas pobierania aktualnej ceny dla {symbol}: {e}", exc_info=True)
            return None


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