#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Moduł mt5_server.py - Serwer komunikacyjny dla EA MT5
"""

import os
import socket
import threading
import time
import json
import logging
from typing import Dict, Any, Optional, List, Tuple, Callable
import queue
import datetime

# Konfiguracja logowania
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/mt5_server.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("MT5Server")

class MT5Server:
    """Serwer komunikacyjny do obsługi połączeń z EA MT5."""
    
    def __init__(self, host: str = '127.0.0.1', port: int = 5555):
        """
        Inicjalizacja serwera MT5.
        
        Args:
            host: Adres hosta, domyślnie localhost
            port: Port nasłuchiwania, domyślnie 5555
        """
        self.host = host
        self.port = port
        self.server_socket = None
        self.is_running = False
        self.clients = []
        self.message_queue = queue.Queue()
        self.command_queue = queue.Queue()
        self.callback_handlers = {}
        self.last_market_data = {}
        self.last_positions_data = {}
        self.last_account_info = {}
        self.last_connection_time = None
        self.lock = threading.Lock()
        
    def start(self) -> bool:
        """
        Uruchamia serwer i zaczyna nasłuchiwać na połączenia.
        
        Returns:
            bool: True, jeśli serwer uruchomił się poprawnie
        """
        if self.is_running:
            logger.warning("Serwer już działa")
            return True
            
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(5)
            self.server_socket.settimeout(1.0)  # 1 sekunda timeout dla accept()
            
            logger.info(f"Serwer MT5 uruchomiony na {self.host}:{self.port}")
            self.is_running = True
            
            # Uruchamiamy wątki
            threading.Thread(target=self._accept_connections, daemon=True).start()
            threading.Thread(target=self._process_messages, daemon=True).start()
            
            return True
        except Exception as e:
            logger.error(f"Błąd podczas uruchamiania serwera: {str(e)}")
            self.stop()
            return False
    
    def stop(self) -> None:
        """Zatrzymuje serwer i zamyka wszystkie połączenia."""
        self.is_running = False
        
        # Zamykamy połączenia klientów
        for client in self.clients:
            try:
                client.close()
            except:
                pass
        self.clients = []
        
        # Zamykamy socket serwera
        if self.server_socket:
            try:
                self.server_socket.close()
            except:
                pass
            self.server_socket = None
            
        logger.info("Serwer MT5 zatrzymany")
    
    def is_connected(self) -> bool:
        """
        Sprawdza, czy EA MT5 jest podłączony.
        
        Returns:
            bool: True, jeśli jest aktywne połączenie
        """
        if not self.last_connection_time:
            return False
            
        # Sprawdzamy, czy połączenie było aktywne w ciągu ostatnich 10 sekund
        return (datetime.datetime.now() - self.last_connection_time).total_seconds() < 10
    
    def send_command(self, command_type: str, command_data: str = "") -> bool:
        """
        Wysyła komendę do EA MT5.
        
        Args:
            command_type: Typ komendy (np. OPEN_POSITION, CLOSE_POSITION)
            command_data: Dane komendy w formacie string
            
        Returns:
            bool: True, jeśli komenda została dodana do kolejki
        """
        if not self.is_running:
            logger.error("Serwer nie jest uruchomiony. Nie można wysłać komendy.")
            return False
            
        command = f"{command_type}:{command_data}"
        self.command_queue.put(command)
        logger.debug(f"Dodano komendę do kolejki: {command}")
        return True
    
    def register_callback(self, message_type: str, callback: Callable[[str], None]) -> None:
        """
        Rejestruje callback dla określonego typu wiadomości.
        
        Args:
            message_type: Typ wiadomości (np. MARKET_DATA, POSITIONS_UPDATE)
            callback: Funkcja wywoływana gdy przychodzi wiadomość danego typu
        """
        self.callback_handlers[message_type] = callback
        logger.debug(f"Zarejestrowano callback dla: {message_type}")
    
    def get_market_data(self, symbol: str = None) -> Dict[str, Any]:
        """
        Pobiera ostatnie dane rynkowe.
        
        Args:
            symbol: Symbol instrumentu (opcjonalnie)
            
        Returns:
            Dict: Dane rynkowe lub pusty słownik, jeśli brak danych
        """
        with self.lock:
            if symbol:
                return self.last_market_data.get(symbol, {})
            return self.last_market_data
    
    def get_positions_data(self) -> Dict[str, Any]:
        """
        Pobiera dane o otwartych pozycjach.
        
        Returns:
            Dict: Dane o pozycjach lub pusty słownik, jeśli brak danych
        """
        with self.lock:
            return self.last_positions_data
    
    def get_account_info(self) -> Dict[str, Any]:
        """
        Pobiera informacje o koncie.
        
        Returns:
            Dict: Informacje o koncie lub pusty słownik, jeśli brak danych
        """
        with self.lock:
            return self.last_account_info
    
    def request_account_info(self) -> bool:
        """
        Wysyła żądanie informacji o koncie.
        
        Returns:
            bool: True, jeśli żądanie zostało wysłane
        """
        return self.send_command("GET_ACCOUNT_INFO")
    
    def request_market_data(self, symbol: str) -> bool:
        """
        Wysyła żądanie danych rynkowych dla określonego symbolu.
        
        Args:
            symbol: Symbol instrumentu
            
        Returns:
            bool: True, jeśli żądanie zostało wysłane
        """
        return self.send_command("GET_MARKET_DATA", f"SYMBOL:{symbol}")
    
    def open_position(self, symbol: str, order_type: str, volume: float, 
                     price: Optional[float] = None, sl: Optional[float] = None, 
                     tp: Optional[float] = None) -> bool:
        """
        Wysyła komendę otwarcia pozycji.
        
        Args:
            symbol: Symbol instrumentu
            order_type: Typ zlecenia ('BUY' lub 'SELL')
            volume: Wielkość pozycji
            price: Cena otwarcia (opcjonalnie, dla zleceń oczekujących)
            sl: Stop Loss (opcjonalnie)
            tp: Take Profit (opcjonalnie)
            
        Returns:
            bool: True, jeśli komenda została wysłana
        """
        command_data = f"SYMBOL:{symbol};TYPE:{order_type};VOLUME:{volume}"
        
        if price is not None:
            command_data += f";PRICE:{price}"
        if sl is not None:
            command_data += f";SL:{sl}"
        if tp is not None:
            command_data += f";TP:{tp}"
            
        return self.send_command("OPEN_POSITION", command_data)
    
    def close_position(self, ticket: int) -> bool:
        """
        Wysyła komendę zamknięcia pozycji.
        
        Args:
            ticket: Numer ticketu pozycji
            
        Returns:
            bool: True, jeśli komenda została wysłana
        """
        return self.send_command("CLOSE_POSITION", f"TICKET:{ticket}")
    
    def modify_position(self, ticket: int, sl: Optional[float] = None, 
                       tp: Optional[float] = None) -> bool:
        """
        Wysyła komendę modyfikacji pozycji.
        
        Args:
            ticket: Numer ticketu pozycji
            sl: Nowy Stop Loss (opcjonalnie)
            tp: Nowy Take Profit (opcjonalnie)
            
        Returns:
            bool: True, jeśli komenda została wysłana
        """
        command_data = f"TICKET:{ticket}"
        
        if sl is not None:
            command_data += f";SL:{sl}"
        if tp is not None:
            command_data += f";TP:{tp}"
            
        return self.send_command("MODIFY_POSITION", command_data)
    
    def ping(self) -> bool:
        """
        Wysyła ping do EA MT5 w celu sprawdzenia połączenia.
        
        Returns:
            bool: True, jeśli ping został wysłany
        """
        return self.send_command("PING")
    
    def _accept_connections(self) -> None:
        """Wątek akceptujący nowe połączenia od klientów."""
        logger.info("Rozpoczęto akceptowanie połączeń")
        
        while self.is_running:
            try:
                client_socket, address = self.server_socket.accept()
                logger.info(f"Nowe połączenie od {address}")
                
                # Ustawiamy timeout na socket klienta
                client_socket.settimeout(1.0)
                
                # Dodajemy klienta do listy
                self.clients.append(client_socket)
                
                # Uruchamiamy wątek obsługujący komunikację z klientem
                threading.Thread(target=self._handle_client, 
                                args=(client_socket, address), 
                                daemon=True).start()
            except socket.timeout:
                # Timeout - normalne zachowanie
                continue
            except Exception as e:
                if self.is_running:
                    logger.error(f"Błąd podczas akceptowania połączenia: {str(e)}")
                    time.sleep(1)  # Zapobiegamy zbyt częstym próbom w przypadku błędu
    
    def _handle_client(self, client_socket: socket.socket, address: Tuple[str, int]) -> None:
        """
        Obsługuje komunikację z pojedynczym klientem.
        
        Args:
            client_socket: Socket klienta
            address: Adres klienta
        """
        logger.info(f"Rozpoczęto obsługę klienta {address}")
        
        try:
            while self.is_running:
                # Sprawdzamy, czy są komendy do wysłania
                try:
                    if not self.command_queue.empty():
                        command = self.command_queue.get_nowait()
                        logger.debug(f"Wysyłanie komendy: {command}")
                        
                        client_socket.send((command + "\n").encode('utf-8'))
                        self.command_queue.task_done()
                except queue.Empty:
                    pass
                except Exception as e:
                    logger.error(f"Błąd podczas wysyłania komendy: {str(e)}")
                    break
                    
                # Odbieramy wiadomości od klienta
                try:
                    # Sprawdzamy, czy są dane do odczytu
                    ready = threading.Thread(target=self._check_socket_ready, args=(client_socket,))
                    ready.start()
                    ready.join(0.1)  # Czekamy 100ms
                    
                    if ready.is_alive():  # Jeśli wątek nadal działa, nie ma danych
                        continue
                    
                    data = client_socket.recv(4096)
                    if not data:
                        logger.warning(f"Klient {address} rozłączony")
                        break
                        
                    # Aktualizujemy czas ostatniego połączenia
                    self.last_connection_time = datetime.datetime.now()
                    
                    # Przetwarzamy dane
                    messages = data.decode('utf-8').strip().split('\n')
                    for message in messages:
                        if message:
                            logger.debug(f"Odebrano wiadomość: {message}")
                            self.message_queue.put(message)
                except socket.timeout:
                    # Timeout - normalne zachowanie
                    pass
                except Exception as e:
                    if self.is_running:
                        logger.error(f"Błąd podczas odbierania danych: {str(e)}")
                    break
                    
                # Krótka pauza, aby nie obciążać CPU
                time.sleep(0.01)
        finally:
            # Sprzątamy po zakończeniu obsługi klienta
            if client_socket in self.clients:
                self.clients.remove(client_socket)
                
            try:
                client_socket.close()
            except:
                pass
                
            logger.info(f"Zakończono obsługę klienta {address}")
    
    def _check_socket_ready(self, client_socket: socket.socket) -> None:
        """
        Sprawdza, czy socket jest gotowy do odczytu (pomocnicza funkcja dla wątku).
        
        Args:
            client_socket: Socket klienta
        """
        try:
            socket.select([client_socket], [], [], 1.0)
        except:
            pass
    
    def _process_messages(self) -> None:
        """Wątek przetwarzający odebrane wiadomości."""
        logger.info("Rozpoczęto przetwarzanie wiadomości")
        
        while self.is_running:
            try:
                # Pobieramy wiadomość z kolejki (z timeoutem, aby nie blokować wątku)
                try:
                    message = self.message_queue.get(timeout=1.0)
                except queue.Empty:
                    continue
                    
                # Parsujemy wiadomość
                try:
                    message_parts = message.split(':', 1)
                    if len(message_parts) < 2:
                        logger.warning(f"Nieprawidłowy format wiadomości: {message}")
                        continue
                        
                    message_type = message_parts[0]
                    message_data = message_parts[1]
                    
                    # Przetwarzamy wiadomość w zależności od typu
                    self._handle_message(message_type, message_data)
                    
                    # Wywołujemy zarejestrowany callback, jeśli istnieje
                    if message_type in self.callback_handlers:
                        try:
                            self.callback_handlers[message_type](message_data)
                        except Exception as e:
                            logger.error(f"Błąd w callbacku dla {message_type}: {str(e)}")
                except Exception as e:
                    logger.error(f"Błąd podczas przetwarzania wiadomości: {str(e)}")
                    
                # Oznaczamy wiadomość jako przetworzoną
                self.message_queue.task_done()
            except Exception as e:
                logger.error(f"Błąd w wątku przetwarzania wiadomości: {str(e)}")
                time.sleep(1)  # Zapobiegamy zbyt częstym próbom w przypadku błędu
    
    def _handle_message(self, message_type: str, message_data: str) -> None:
        """
        Obsługuje odebrane wiadomości od EA MT5.
        
        Args:
            message_type: Typ wiadomości
            message_data: Dane wiadomości
        """
        logger.debug(f"Przetwarzanie wiadomości typu {message_type}")
        
        if message_type == "MARKET_DATA":
            self._handle_market_data(message_data)
        elif message_type == "POSITIONS_UPDATE":
            self._handle_positions_update(message_data)
        elif message_type == "ACCOUNT_INFO":
            self._handle_account_info(message_data)
        elif message_type == "INIT":
            logger.info(f"EA zainicjalizowany: {message_data}")
        elif message_type == "DEINIT":
            logger.info(f"EA zatrzymany: {message_data}")
        elif message_type == "ERROR":
            logger.error(f"Błąd z EA: {message_data}")
        elif message_type == "SUCCESS":
            logger.info(f"Sukces operacji: {message_data}")
        elif message_type == "PONG":
            logger.debug("Otrzymano odpowiedź PONG")
        elif message_type == "CLOSE":
            logger.info(f"EA zamknął połączenie: {message_data}")
        else:
            logger.warning(f"Nieznany typ wiadomości: {message_type} - {message_data}")
    
    def _handle_market_data(self, data: str) -> None:
        """
        Przetwarza dane rynkowe.
        
        Args:
            data: Dane w formacie string
        """
        parsed_data = self._parse_data(data)
        if not parsed_data or 'SYMBOL' not in parsed_data:
            logger.warning(f"Niepoprawne dane rynkowe: {data}")
            return
            
        symbol = parsed_data['SYMBOL']
        
        with self.lock:
            self.last_market_data[symbol] = parsed_data
    
    def _handle_positions_update(self, data: str) -> None:
        """
        Przetwarza dane o pozycjach.
        
        Args:
            data: Dane w formacie string
        """
        # Dane pozycji mogą zawierać wiele pozycji oddzielonych '|'
        positions = {}
        
        if not data:
            # Brak pozycji
            with self.lock:
                self.last_positions_data = {}
            return
            
        positions_data = data.split('|')
        for position_data in positions_data:
            parsed_position = self._parse_data(position_data)
            if parsed_position and 'TICKET' in parsed_position:
                ticket = parsed_position['TICKET']
                positions[ticket] = parsed_position
        
        with self.lock:
            self.last_positions_data = positions
    
    def _handle_account_info(self, data: str) -> None:
        """
        Przetwarza informacje o koncie.
        
        Args:
            data: Dane w formacie string
        """
        parsed_data = self._parse_data(data)
        if not parsed_data:
            logger.warning(f"Niepoprawne dane konta: {data}")
            return
            
        with self.lock:
            self.last_account_info = parsed_data
    
    def _parse_data(self, data: str) -> Dict[str, Any]:
        """
        Parsuje dane w formacie klucz:wartość;
        
        Args:
            data: String danych do sparsowania
            
        Returns:
            Dict: Sparsowane dane lub pusty słownik w przypadku błędu
        """
        result = {}
        
        try:
            # Dzielimy string na pary klucz:wartość
            pairs = data.split(';')
            for pair in pairs:
                if not pair:
                    continue
                    
                # Dzielimy parę na klucz i wartość
                kv = pair.split(':', 1)
                if len(kv) == 2:
                    key, value = kv
                    
                    # Konwersja wartości do odpowiedniego typu
                    try:
                        # Próbujemy skonwertować do float
                        value = float(value)
                        
                        # Jeśli to liczba całkowita, konwertujemy do int
                        if value.is_integer():
                            value = int(value)
                    except ValueError:
                        # Jeśli nie można skonwertować, zostawiamy jako string
                        pass
                        
                    result[key] = value
        except Exception as e:
            logger.error(f"Błąd podczas parsowania danych: {str(e)} - {data}")
            return {}
            
        return result


# Przykład użycia jako standalone server
if __name__ == "__main__":
    try:
        server = MT5Server()
        if server.start():
            print("Naciśnij Ctrl+C aby zatrzymać serwer...")
            
            # Przykład callbacku
            def on_market_data(data):
                print(f"Nowe dane rynkowe: {data}")
                
            server.register_callback("MARKET_DATA", on_market_data)
            
            # Utrzymujemy serwer uruchomiony
            while True:
                time.sleep(1)
                
                # Co 5 sekund wysyłamy ping, jeśli jesteśmy połączeni
                if server.is_connected():
                    server.ping()
        else:
            print("Nie można uruchomić serwera")
    except KeyboardInterrupt:
        print("Zatrzymywanie serwera...")
    finally:
        if 'server' in locals():
            server.stop() 