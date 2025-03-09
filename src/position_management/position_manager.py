from datetime import datetime
from enum import Enum, auto
import logging
from typing import Dict, List, Optional, Any, Union

# Konfiguracja loggera
logger = logging.getLogger(__name__)

class PositionStatus(Enum):
    """Status pozycji handlowej."""
    OPEN = auto()      # Pozycja otwarta
    CLOSED = auto()    # Pozycja zamknięta
    PENDING = auto()   # Pozycja oczekująca
    ERROR = auto()     # Pozycja z błędem

class PositionError(Exception):
    """Wyjątek związany z obsługą pozycji."""
    pass

class Position:
    """Klasa reprezentująca pozycję handlową."""
    
    def __init__(self, ea_id: str, ticket: int, symbol: str, type: str, volume: float, 
                 open_price: float, current_price: float, sl: float, tp: float, 
                 profit: float, open_time: datetime, status: PositionStatus = PositionStatus.OPEN,
                 close_price: float = None, close_time: datetime = None):
        """
        Inicjalizacja nowej pozycji.
        
        Args:
            ea_id: Identyfikator EA, który utworzył pozycję
            ticket: Numer identyfikacyjny pozycji w MT5
            symbol: Symbol instrumentu (np. "EURUSD.pro")
            type: Typ pozycji ("BUY" lub "SELL")
            volume: Wolumen pozycji (ilość lotów)
            open_price: Cena otwarcia pozycji
            current_price: Aktualna cena instrumentu
            sl: Poziom Stop Loss (0 jeśli nie ustawiono)
            tp: Poziom Take Profit (0 jeśli nie ustawiono)
            profit: Aktualny zysk/strata na pozycji
            open_time: Czas otwarcia pozycji
            status: Status pozycji (domyślnie OPEN)
            close_price: Cena zamknięcia pozycji (opcjonalnie)
            close_time: Czas zamknięcia pozycji (opcjonalnie)
        """
        self.ea_id = ea_id
        self.ticket = ticket
        self.symbol = symbol
        self.type = type
        self.volume = volume
        self.open_price = open_price
        self.current_price = current_price
        self.sl = sl
        self.tp = tp
        self.profit = profit
        self.open_time = open_time
        self.status = status
        self.close_price = close_price
        self.close_time = close_time
        self.last_update = datetime.now()
        
        # Dodatkowe informacje do śledzenia stanu
        self.sync_status = True  # Czy pozycja jest zsynchronizowana z MT5
        self.error_message = None  # Komunikat o błędzie, jeśli wystąpił
    
    def update(self, data: Dict[str, Any]) -> None:
        """
        Aktualizuje dane pozycji.
        
        Args:
            data: Słownik z nowymi wartościami pól
        """
        for key, value in data.items():
            if hasattr(self, key) and key not in ['ticket', 'ea_id', 'open_time', 'status']:
                setattr(self, key, value)
        
        self.last_update = datetime.now()
    
    def close(self, close_price: float, close_time: Union[str, datetime], profit: float) -> None:
        """
        Zamyka pozycję.
        
        Args:
            close_price: Cena zamknięcia pozycji
            close_time: Czas zamknięcia pozycji (string lub datetime)
            profit: Ostateczny zysk/strata na pozycji
        """
        self.close_price = close_price
        
        if isinstance(close_time, str):
            self.close_time = datetime.strptime(close_time, "%Y.%m.%d %H:%M")
        else:
            self.close_time = close_time
            
        self.profit = profit
        self.status = PositionStatus.CLOSED
        self.last_update = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Konwertuje pozycję na słownik.
        
        Returns:
            Słownik z danymi pozycji
        """
        return {
            'ea_id': self.ea_id,
            'ticket': self.ticket,
            'symbol': self.symbol,
            'type': self.type,
            'volume': self.volume,
            'open_price': self.open_price,
            'current_price': self.current_price,
            'sl': self.sl,
            'tp': self.tp,
            'profit': self.profit,
            'open_time': self.open_time.strftime("%Y.%m.%d %H:%M") if self.open_time else None,
            'status': self.status.name,
            'close_price': self.close_price,
            'close_time': self.close_time.strftime("%Y.%m.%d %H:%M") if self.close_time else None,
            'last_update': self.last_update.strftime("%Y.%m.%d %H:%M:%S"),
            'sync_status': self.sync_status,
            'error_message': self.error_message
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Position':
        """
        Tworzy instancję pozycji z słownika.
        
        Args:
            data: Słownik z danymi pozycji
            
        Returns:
            Nowa instancja Position
        """
        # Konwersja string -> datetime
        if 'open_time' in data and isinstance(data['open_time'], str):
            data['open_time'] = datetime.strptime(data['open_time'], "%Y.%m.%d %H:%M")
        
        if 'close_time' in data and data['close_time'] and isinstance(data['close_time'], str):
            data['close_time'] = datetime.strptime(data['close_time'], "%Y.%m.%d %H:%M")
        
        # Konwersja string -> enum
        if 'status' in data and isinstance(data['status'], str):
            data['status'] = PositionStatus[data['status']]
        elif 'status' not in data:
            data['status'] = PositionStatus.OPEN
        
        # Tworzenie instancji
        position = cls(
            ea_id=data.get('ea_id'),
            ticket=data.get('ticket'),
            symbol=data.get('symbol'),
            type=data.get('type'),
            volume=data.get('volume'),
            open_price=data.get('open_price'),
            current_price=data.get('current_price'),
            sl=data.get('sl', 0.0),
            tp=data.get('tp', 0.0),
            profit=data.get('profit', 0.0),
            open_time=data.get('open_time'),
            status=data.get('status'),
            close_price=data.get('close_price'),
            close_time=data.get('close_time')
        )
        
        # Dodatkowe pola
        if 'sync_status' in data:
            position.sync_status = data['sync_status']
        
        if 'error_message' in data:
            position.error_message = data['error_message']
        
        return position

class PositionManager:
    """Menedżer pozycji handlowych."""
    
    def __init__(self, db_connection=None, api_client=None):
        """
        Inicjalizacja menedżera pozycji.
        
        Args:
            db_connection: Połączenie z bazą danych
            api_client: Klient API do komunikacji z MT5
        """
        self._positions: Dict[int, Position] = {}  # ticket -> Position
        self.db = db_connection
        self.api_client = api_client
        
        # Wczytanie pozycji z bazy danych, jeśli istnieje
        self._load_positions_from_db()
        
        logger.info("PositionManager zainicjalizowany")
    
    def _load_positions_from_db(self) -> None:
        """Wczytuje pozycje z bazy danych."""
        if self.db is None:
            logger.warning("Brak połączenia z bazą danych - pozycje nie zostaną wczytane")
            return
        
        try:
            positions_data = self.db.get_all_positions()
            for data in positions_data:
                position = Position.from_dict(data)
                self._positions[position.ticket] = position
            
            logger.info(f"Wczytano {len(positions_data)} pozycji z bazy danych")
        except Exception as e:
            logger.error(f"Błąd podczas wczytywania pozycji z bazy danych: {e}")
    
    def add_position(self, position_data: Dict[str, Any]) -> Position:
        """
        Dodaje nową pozycję do systemu.
        
        Args:
            position_data: Dane pozycji
            
        Returns:
            Utworzona pozycja
        """
        # Utworzenie instancji pozycji
        position = Position.from_dict(position_data)
        
        # Dodanie do słownika
        self._positions[position.ticket] = position
        
        # Zapisanie w bazie danych
        if self.db:
            try:
                self.db.save_position(position.to_dict())
            except Exception as e:
                logger.error(f"Błąd podczas zapisywania pozycji {position.ticket} w bazie danych: {e}")
                position.sync_status = False
                position.error_message = str(e)
        
        logger.info(f"Dodano nową pozycję {position.ticket} dla symbolu {position.symbol}")
        return position
    
    def get_position_by_ticket(self, ticket: int) -> Position:
        """
        Pobiera pozycję na podstawie numeru ticketu.
        
        Args:
            ticket: Numer ticketu pozycji
            
        Returns:
            Pozycja o podanym numerze ticketu
            
        Raises:
            PositionError: Gdy pozycja o podanym tickecie nie istnieje
        """
        if ticket not in self._positions:
            raise PositionError(f"Pozycja o numerze ticketu {ticket} nie istnieje")
        
        return self._positions[ticket]
    
    def update_position(self, ticket: int, update_data: Dict[str, Any]) -> Position:
        """
        Aktualizuje istniejącą pozycję.
        
        Args:
            ticket: Numer ticketu pozycji
            update_data: Dane do aktualizacji
            
        Returns:
            Zaktualizowana pozycja
            
        Raises:
            PositionError: Gdy pozycja o podanym tickecie nie istnieje
        """
        if ticket not in self._positions:
            raise PositionError(f"Nie można zaktualizować - pozycja {ticket} nie istnieje")
        
        # Aktualizacja pozycji
        position = self._positions[ticket]
        position.update(update_data)
        
        # Zapisanie w bazie danych
        if self.db:
            try:
                self.db.update_position(position.to_dict())
            except Exception as e:
                logger.error(f"Błąd podczas aktualizacji pozycji {ticket} w bazie danych: {e}")
                position.sync_status = False
                position.error_message = str(e)
        
        logger.info(f"Zaktualizowano pozycję {ticket}")
        return position
    
    def close_position(self, ticket: int, close_data: Dict[str, Any]) -> Position:
        """
        Zamyka istniejącą pozycję.
        
        Args:
            ticket: Numer ticketu pozycji
            close_data: Dane zamknięcia (close_price, close_time, profit)
            
        Returns:
            Zamknięta pozycja
            
        Raises:
            PositionError: Gdy pozycja o podanym tickecie nie istnieje
        """
        if ticket not in self._positions:
            raise PositionError(f"Nie można zamknąć - pozycja {ticket} nie istnieje")
        
        # Pobranie pozycji
        position = self._positions[ticket]
        
        # Zamknięcie pozycji
        position.close(
            close_price=close_data.get('close_price'),
            close_time=close_data.get('close_time'),
            profit=close_data.get('profit')
        )
        
        # Zapisanie w bazie danych
        if self.db:
            try:
                self.db.update_position(position.to_dict())
            except Exception as e:
                logger.error(f"Błąd podczas zapisywania zamkniętej pozycji {ticket} w bazie danych: {e}")
                position.sync_status = False
                position.error_message = str(e)
        
        logger.info(f"Zamknięto pozycję {ticket} z profitem {position.profit}")
        return position
    
    def get_active_positions(self) -> List[Position]:
        """
        Pobiera wszystkie aktywne pozycje.
        
        Returns:
            Lista aktywnych pozycji
        """
        return [p for p in self._positions.values() if p.status == PositionStatus.OPEN]
    
    def get_positions_by_ea_id(self, ea_id: str) -> List[Position]:
        """
        Pobiera wszystkie pozycje dla danego EA.
        
        Args:
            ea_id: Identyfikator EA
            
        Returns:
            Lista pozycji dla danego EA
        """
        return [p for p in self._positions.values() if p.ea_id == ea_id]
    
    def get_position_history(self, days: int = 30) -> List[Position]:
        """
        Pobiera historię pozycji z określonego okresu.
        
        Args:
            days: Liczba dni wstecz (domyślnie 30)
            
        Returns:
            Lista pozycji z podanego okresu
        """
        cutoff_time = datetime.now()
        cutoff_time = cutoff_time.replace(hour=0, minute=0, second=0, microsecond=0)
        cutoff_time = cutoff_time.replace(day=cutoff_time.day - days)
        
        return [p for p in self._positions.values() 
                if p.status == PositionStatus.CLOSED and p.close_time and p.close_time >= cutoff_time]
    
    def sync_positions_with_mt5(self, ea_id: str) -> None:
        """
        Synchronizuje pozycje z MT5 dla danego EA.
        
        Args:
            ea_id: Identyfikator EA
        """
        if self.api_client is None:
            logger.warning("Brak klienta API - synchronizacja z MT5 niemożliwa")
            return
        
        try:
            # Pobranie aktywnych pozycji z MT5
            mt5_positions = self.api_client.get_active_positions(ea_id)
            
            # Set do śledzenia aktualnych ticketów z MT5
            mt5_tickets = set()
            
            # Przetwarzanie pozycji z MT5
            for mt5_pos in mt5_positions:
                ticket = mt5_pos.get('ticket')
                mt5_tickets.add(ticket)
                
                if ticket in self._positions:
                    # Aktualizacja istniejącej pozycji
                    self.update_position(ticket, mt5_pos)
                else:
                    # Dodanie nowej pozycji
                    self.add_position(mt5_pos)
            
            # Sprawdzenie pozycji, które zostały zamknięte w MT5, ale są otwarte w naszym systemie
            for pos in self.get_positions_by_ea_id(ea_id):
                if pos.status == PositionStatus.OPEN and pos.ticket not in mt5_tickets:
                    # Pozycja zamknięta w MT5, ale otwarta w naszym systemie
                    # Pobieramy dane historyczne pozycji z MT5
                    try:
                        closed_position_data = self.api_client.get_closed_position(ea_id, pos.ticket)
                        if closed_position_data:
                            self.close_position(pos.ticket, closed_position_data)
                    except Exception as e:
                        logger.error(f"Błąd podczas pobierania danych zamkniętej pozycji {pos.ticket}: {e}")
            
            logger.info(f"Zakończono synchronizację pozycji dla EA {ea_id}")
        except Exception as e:
            logger.error(f"Błąd podczas synchronizacji pozycji z MT5: {e}")
    
    def recover_positions(self, ea_id: str) -> None:
        """
        Odzyskuje stan pozycji w przypadku awarii.
        
        Args:
            ea_id: Identyfikator EA
        """
        logger.info(f"Rozpoczęto procedurę odzyskiwania pozycji dla EA {ea_id}")
        
        # Synchronizacja z MT5
        self.sync_positions_with_mt5(ea_id)
        
        # Sprawdzenie niezsynchrozinowanych pozycji
        unsync_positions = [p for p in self.get_positions_by_ea_id(ea_id) if not p.sync_status]
        
        if unsync_positions:
            logger.warning(f"Znaleziono {len(unsync_positions)} niezsynchrozinowanych pozycji")
            
            for pos in unsync_positions:
                try:
                    # Próba ponownej synchronizacji
                    if pos.status == PositionStatus.OPEN:
                        # Sprawdzenie, czy pozycja istnieje w MT5
                        mt5_pos = self.api_client.get_position(ea_id, pos.ticket)
                        if mt5_pos:
                            # Aktualizacja pozycji
                            self.update_position(pos.ticket, mt5_pos)
                            pos.sync_status = True
                            pos.error_message = None
                        else:
                            # Pozycja nie istnieje w MT5, próba pobrania danych historycznych
                            closed_pos = self.api_client.get_closed_position(ea_id, pos.ticket)
                            if closed_pos:
                                # Zamknięcie pozycji
                                self.close_position(pos.ticket, closed_pos)
                                pos.sync_status = True
                                pos.error_message = None
                    elif pos.status == PositionStatus.CLOSED:
                        # Pozycja jest już zamknięta, aktualizacja w bazie danych
                        if self.db:
                            self.db.update_position(pos.to_dict())
                            pos.sync_status = True
                            pos.error_message = None
                except Exception as e:
                    logger.error(f"Błąd podczas odzyskiwania pozycji {pos.ticket}: {e}")
        
        logger.info(f"Zakończono procedurę odzyskiwania pozycji dla EA {ea_id}") 