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
import re
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn
from urllib.parse import urlparse, parse_qs

# Import biblioteki MetaTrader5 do bezpośredniej komunikacji
try:
    import MetaTrader5 as mt5
    MT5_AVAILABLE = True
    logger = logging.getLogger("MT5Server")
    logger.info("Biblioteka MetaTrader5 została zaimportowana pomyślnie")
except ImportError:
    MT5_AVAILABLE = False
    logger = logging.getLogger("MT5Server")
    logger.warning("Biblioteka MetaTrader5 nie jest zainstalowana. Niektóre funkcje będą niedostępne.")

# Konfiguracja logowania
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/mt5_server.log"),
        logging.StreamHandler()
    ]
)

class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    """Handle requests in a separate thread."""
    daemon_threads = True

class MT5RequestHandler(BaseHTTPRequestHandler):
    """Handler zapytań HTTP dla serwera MT5."""
    
    def __init__(self, *args, mt5_server=None, **kwargs):
        """
        Inicjalizacja handlera z referencją do serwera MT5.
        
        Args:
            mt5_server: Referencja do instancji MT5Server
        """
        self.mt5_server = mt5_server
        super().__init__(*args, **kwargs)
    
    def do_POST(self):
        # Inkrementuj licznik zapytań
        # self.mt5_server.request_count += 1
        
        # Aktualizuj czas ostatniego połączenia
        self.mt5_server.last_connection_time = datetime.datetime.now()
        
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        
        try:
            data = json.loads(post_data.decode('utf-8'))
            logger.info(f"Otrzymano dane: {data}")
            
            # Przetwarzanie różnych endpointów
            if self.path == '/position/update':
                self.mt5_server._handle_positions_update(json.dumps(data))
                self.send_success_response()
            elif self.path == '/market/data':
                self.mt5_server._handle_market_data(json.dumps(data))
                self.send_success_response()
            elif self.path == '/account/info':
                self.mt5_server._handle_account_info(json.dumps(data))
                self.send_success_response()
            elif self.path == '/history/data':
                self.mt5_server._handle_history_data(json.dumps(data))
                self.send_success_response()
            elif self.path == '/ping':
                # Prosty ping-pong
                self.send_success_response()
            else:
                logger.warning(f"Nieznany endpoint POST: {self.path}")
                self.send_response(404)
                self.end_headers()
                return

        except json.JSONDecodeError as e:
            logger.error(f"Błąd parsowania JSON: {e}")
            self.send_response(400)
            self.end_headers()
        except Exception as e:
            logger.error(f"Błąd przetwarzania żądania: {e}")
            self.send_response(500)
            self.end_headers()

    def do_GET(self):
        # Inkrementuj licznik zapytań
        # self.server.request_count += 1
        
        # Parsowanie URL i parametrów
        parsed_url = urlparse(self.path)
        path = parsed_url.path
        query_params = dict(parse_qs(parsed_url.query))
        
        # Logowanie informacji o żądaniu
        if not path.startswith('/status'):  # Pomijamy logowanie statusu aby nie zaśmiecać logów
            logger.debug(f"Otrzymano żądanie GET: {path} z parametrami: {query_params}")
        
        try:
            # Obsługa żądania w zależności od ścieżki
            if path == '/account_info':
                self._handle_account_info()
            elif path == '/transactions':
                # Pobranie parametru limit z zapytania
                limit = 5
                if 'limit' in query_params and len(query_params['limit']) > 0:
                    try:
                        limit = int(query_params['limit'][0])
                    except ValueError:
                        pass
                self._handle_transactions(limit)
            elif path == '/commands':
                self._handle_commands(query_params)
            elif path == '/positions':
                self._handle_positions()
            elif path == '/ping':
                self.send_success_response()
            elif path == '/monitoring/connections':
                self._handle_monitoring_connections()
            else:
                logger.warning(f"Nieznany endpoint GET: {path}")
                self.send_error_response(f"Nieznany endpoint: {path}")
                
        except Exception as e:
            logger.error(f"Błąd podczas obsługi zapytania GET: {str(e)}")
            self.send_error(500, f"Internal server error: {str(e)}")
    
    def _handle_account_info(self):
        """Obsługa zapytania o informacje o koncie."""
        try:
            if not self.mt5_server:
                self.send_error(500, "MT5 server not initialized")
                return
                
            # Pobierz informacje o koncie
            account_info = self.mt5_server.get_account_info()
            
            # Przygotuj odpowiedź
            response = {
                'status': 'ok',
                'data': account_info
            }
            
            # Wyślij odpowiedź
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(response).encode('utf-8'))
            
        except Exception as e:
            logger.error(f"Błąd podczas pobierania informacji o koncie: {str(e)}")
            self.send_error(500, f"Error getting account info: {str(e)}")
    
    def _handle_transactions(self, limit: int = 5):
        """
        Obsługa zapytania o historię transakcji.
        
        Args:
            limit: Maksymalna liczba transakcji do zwrócenia
        """
        try:
            if not self.mt5_server:
                self.send_error(500, "MT5 server not initialized")
                return
                
            # Pobierz historię transakcji
            with self.mt5_server.lock:
                transactions = self.mt5_server.history_data[-limit:]
            
            # Przygotuj odpowiedź
            response = {
                'status': 'ok',
                'data': transactions
            }
            
            # Wyślij odpowiedź
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(response).encode('utf-8'))
            
        except Exception as e:
            logger.error(f"Błąd podczas pobierania historii transakcji: {str(e)}")
            self.send_error(500, f"Error getting transaction history: {str(e)}")
    
    def send_error_response(self, message: str):
        """
        Wysyła odpowiedź z błędem.
        
        Args:
            message: Komunikat błędu
        """
        self.send_response(400)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps({
            'status': 'error',
            'message': message
        }).encode('utf-8'))

    def send_success_response(self):
        """Helper method to send a standard success response"""
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        response = {"status": "ok", "timestamp": str(datetime.datetime.now())}
        self.wfile.write(json.dumps(response).encode())

    def _handle_commands(self, query_params):
        """
        Obsługa zapytań dla endpointu /commands.
        
        Args:
            query_params: Parametry zapytania przekazane w URL
        """
        try:
            if not self.mt5_server:
                self.send_error_response("MT5 server not initialized")
                return
                
            # Sprawdzenie, czy mamy parametr ea_id - ten parametr jest przesyłany przez EA
            ea_id = query_params.get('ea_id', [None])[0]
            if ea_id and 'action' not in query_params:
                # Jeśli to jest ping z EA, zwróć informacje o dostępnych komendach
                response = {
                    "status": "ok", 
                    "message": "MT5 server ready",
                    "available_commands": [
                        "trade", "close", "modify", "refresh"
                    ],
                    "example": "/commands?action=trade&type=buy&symbol=EURUSD&volume=0.1"
                }
                
                # Wysłanie odpowiedzi
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(response).encode('utf-8'))
                return
                
            # Normalny przepływ dla żądań z parametrem action
            # Sprawdzenie czy zapytanie zawiera niezbędne parametry
            # Przykład: /commands?action=trade&type=buy&symbol=EURUSD&volume=0.1
            action = query_params.get('action', [None])[0]
            
            if not action:
                self.send_error_response("Missing required parameter: action")
                return
                
            response = {"status": "ok", "message": "Command processed successfully"}
                
            # Obsługa różnych typów komend
            if action == 'trade':
                # Parametry handlowe
                trade_type = query_params.get('type', [None])[0]
                symbol = query_params.get('symbol', [None])[0]
                volume = query_params.get('volume', [None])[0]
                
                if not all([trade_type, symbol, volume]):
                    self.send_error_response("Missing required trade parameters")
                    return
                
                try:
                    volume = float(volume)
                except ValueError:
                    self.send_error_response("Volume must be a number")
                    return
                
                # Opcjonalne parametry
                price = query_params.get('price', [None])[0]
                sl = query_params.get('sl', [None])[0]
                tp = query_params.get('tp', [None])[0]
                
                # Konwersja opcjonalnych parametrów na float jeśli podane
                if price: 
                    try: price = float(price)
                    except ValueError: price = None
                if sl: 
                    try: sl = float(sl)
                    except ValueError: sl = None
                if tp: 
                    try: tp = float(tp)
                    except ValueError: tp = None
                
                # Wykonanie operacji handlowej
                if trade_type.lower() in ['buy', 'sell']:
                    success = self.mt5_server.open_position(
                        symbol, 
                        trade_type.upper(), 
                        volume, 
                        price, 
                        sl, 
                        tp
                    )
                    
                    if not success:
                        response = {"status": "error", "message": "Failed to execute trade command"}
                else:
                    response = {"status": "error", "message": f"Unknown trade type: {trade_type}"}
            
            elif action == 'close':
                # Zamykanie pozycji
                ticket = query_params.get('ticket', [None])[0]
                
                if not ticket:
                    self.send_error_response("Missing ticket parameter for close action")
                    return
                
                try:
                    ticket = int(ticket)
                except ValueError:
                    self.send_error_response("Ticket must be a number")
                    return
                
                success = self.mt5_server.close_position(ticket)
                if not success:
                    response = {"status": "error", "message": "Failed to close position"}
                
            elif action == 'modify':
                # Modyfikacja pozycji
                ticket = query_params.get('ticket', [None])[0]
                sl = query_params.get('sl', [None])[0]
                tp = query_params.get('tp', [None])[0]
                
                if not ticket:
                    self.send_error_response("Missing ticket parameter for modify action")
                    return
                
                try:
                    ticket = int(ticket)
                    if sl: sl = float(sl)
                    if tp: tp = float(tp)
                except ValueError:
                    self.send_error_response("Invalid numeric parameters")
                    return
                
                success = self.mt5_server.modify_position(ticket, sl, tp)
                if not success:
                    response = {"status": "error", "message": "Failed to modify position"}
            
            elif action == 'refresh':
                # Odświeżenie danych
                symbol = query_params.get('symbol', [None])[0]
                
                if symbol:
                    success = self.mt5_server.request_market_data(symbol)
                    success = success and self.mt5_server.request_account_info()
                    
                    if not success:
                        response = {"status": "error", "message": "Failed to refresh data"}
                else:
                    success = self.mt5_server.request_account_info()
                    if not success:
                        response = {"status": "error", "message": "Failed to refresh account info"}
            
            else:
                response = {"status": "error", "message": f"Unknown action: {action}"}
            
            # Wysłanie odpowiedzi
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(response).encode('utf-8'))
            
        except Exception as e:
            logger.error(f"Błąd podczas obsługi komendy: {str(e)}")
            self.send_error_response(f"Error processing command: {str(e)}")

    def _handle_positions(self):
        """
        Obsługuje żądanie GET /positions, zwracając dane o aktualnych pozycjach.
        """
        positions_data = self.mt5_server.get_positions_data()
        
        # Przygotuj odpowiedź
        response = {
            "status": "ok",
            "positions": positions_data
        }
        
        # Wyślij odpowiedź
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'X-Requested-With, Content-Type')
        self.end_headers()
        self.wfile.write(json.dumps(response).encode())
        
    def _handle_monitoring_connections(self):
        """
        Obsługuje żądanie GET /monitoring/connections, zwracając dane o połączeniach.
        """
        # Przygotuj odpowiedź
        response = {
            "status": "ok",
            "connections": [
                {
                    "id": "EA_connection",
                    "type": "MT5 Expert Advisor",
                    "status": "connected" if self.mt5_server.is_connected() else "disconnected",
                    "last_activity": str(self.mt5_server.last_connection_time)
                }
            ]
        }
        
        # Wyślij odpowiedź
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'X-Requested-With, Content-Type')
        self.end_headers()
        self.wfile.write(json.dumps(response).encode())

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
        self.server = None
        self.is_running = False
        self.message_queue = queue.Queue()
        self.command_queue = queue.Queue()
        self.callback_handlers = {}
        self.last_market_data = {}
        self.last_positions_data = {}
        self.last_account_info = {}
        self.recent_transactions = []  # Lista ostatnich transakcji
        self.history_data = []  # Historia transakcji z MT5
        self.alerts = []  # Lista alertów systemu
        self.last_connection_time = None
        self.lock = threading.Lock()
        self.start_time = datetime.datetime.now()
        self.request_count = 0
        
        # Lista obserwowanych instrumentów (domyślna)
        self.observed_instruments = ["EURUSD", "GBPUSD", "USDJPY", "XAUUSD", "BTCUSD"]
        
        # Inicjalizacja połączenia z MT5 jeśli dostępne
        self._init_mt5_connection()
        
    def _init_mt5_connection(self):
        """Inicjalizuje połączenie z platformą MT5 jeśli dostępna."""
        if not MT5_AVAILABLE:
            logger.warning("Nie można zainicjalizować połączenia z MT5 - biblioteka niedostępna")
            return False
        
        try:
            # Sprawdź, czy MT5 jest już zainicjalizowany
            if not mt5.terminal_info():
                logger.info("Próba inicjalizacji połączenia z MT5...")
                if not mt5.initialize():
                    error = mt5.last_error()
                    logger.error(f"Nie udało się zainicjalizować MT5: kod błędu={error[0]}, opis={error[1]}")
                    return False
                else:
                    # Pobierz informacje o terminalu
                    terminal_info = mt5.terminal_info()
                    if terminal_info is not None:
                        logger.info(f"Pomyślnie połączono z MT5: wersja={mt5.version()}, "
                                   f"nazwa={terminal_info.name}, "
                                   f"ścieżka={terminal_info.path}")
                    else:
                        logger.warning("Połączono z MT5, ale nie można pobrać informacji o terminalu")
                    return True
            else:
                logger.info("MT5 już zainicjalizowany")
                return True
        except Exception as e:
            logger.error(f"Wyjątek podczas inicjalizacji MT5: {str(e)}")
            return False
        
    def fetch_history_data(self, days_back: int = 7) -> bool:
        """
        Pobiera historię transakcji bezpośrednio z MT5 API.
        
        Args:
            days_back: Ile dni wstecz pobierać historię
            
        Returns:
            bool: True jeśli operacja się powiodła
        """
        if not MT5_AVAILABLE:
            logger.warning("Nie można pobrać historii z MT5 - biblioteka niedostępna")
            return False
            
        logger.info(f"Rozpoczynam pobieranie historii z MT5 za ostatnie {days_back} dni...")
        if not self._init_mt5_connection():
            logger.error("Nie można pobrać historii - błąd inicjalizacji MT5")
            return False
            
        try:
            # Pobierz historię transakcji
            from_date = datetime.datetime.now() - datetime.timedelta(days=days_back)
            logger.info(f"Pobieranie historii zleceń od {from_date}...")
            history_orders = mt5.history_orders_get(from_date)
            
            if history_orders is None:
                error = mt5.last_error()
                logger.error(f"Nie udało się pobrać historii zleceń z MT5: kod błędu={error[0]}, opis={error[1]}")
                return False
                
            logger.info(f"Pobieranie historii transakcji od {from_date}...")
            history_deals = mt5.history_deals_get(from_date)
            
            if history_deals is None:
                error = mt5.last_error()
                logger.error(f"Nie udało się pobrać historii transakcji z MT5: kod błędu={error[0]}, opis={error[1]}")
                return False
                
            logger.info(f"Pobrano {len(history_orders)} zleceń i {len(history_deals)} transakcji z historii MT5")
            
            # Mapowanie statusów i typów zleceń
            type_map = {
                mt5.ORDER_TYPE_BUY: "BUY",
                mt5.ORDER_TYPE_SELL: "SELL",
                mt5.ORDER_TYPE_BUY_LIMIT: "BUY LIMIT",
                mt5.ORDER_TYPE_SELL_LIMIT: "SELL LIMIT",
                mt5.ORDER_TYPE_BUY_STOP: "BUY STOP",
                mt5.ORDER_TYPE_SELL_STOP: "SELL STOP"
            }
            
            status_map = {
                mt5.DEAL_ENTRY_IN: "OPEN",
                mt5.DEAL_ENTRY_OUT: "CLOSE",
                mt5.DEAL_ENTRY_INOUT: "REVERSE",
                mt5.DEAL_ENTRY_OUT_BY: "CLOSE BY"
            }
            
            # Przetwarzanie transakcji
            transactions = []
            
            # Utworzenie mapy zleceń dla szybszego wyszukiwania
            orders_map = {}
            for order in history_orders:
                orders_map[order.ticket] = order
                
            # Przetwarzanie zawartych transakcji
            for deal in history_deals:
                order = orders_map.get(deal.order)
                
                if order:
                    transaction = {
                        "id": deal.ticket,
                        "symbol": deal.symbol,
                        "type": type_map.get(deal.type, "UNKNOWN"),
                        "volume": deal.volume,
                        "open_time": datetime.datetime.fromtimestamp(deal.time).strftime('%Y.%m.%d %H:%M:%S'),
                        "close_time": None if deal.entry == mt5.DEAL_ENTRY_IN else datetime.datetime.fromtimestamp(deal.time).strftime('%Y.%m.%d %H:%M:%S'),
                        "open_price": deal.price,
                        "close_price": deal.price,
                        "profit": deal.profit,
                        "status": status_map.get(deal.entry, "UNKNOWN"),
                        "comment": deal.comment
                    }
                    transactions.append(transaction)
            
            with self.lock:
                self.history_data = transactions
                logger.info(f"Pobrano {len(transactions)} transakcji z historii MT5")
                
            return True
            
        except Exception as e:
            logger.error(f"Błąd podczas pobierania historii z MT5: {str(e)}")
            return False
            
    def start(self) -> bool:
        """
        Uruchamia serwer HTTP i zaczyna nasłuchiwać na połączenia.
        
        Returns:
            bool: True, jeśli serwer uruchomił się poprawnie
        """
        if self.is_running:
            logger.warning("Serwer już działa")
            return True
            
        try:
            # Tworzymy handler z przekazaniem referencji do MT5Server
            handler = lambda *args, **kwargs: MT5RequestHandler(*args, mt5_server=self, **kwargs)
            
            self.server = ThreadedHTTPServer((self.host, self.port), handler)
            logger.info(f"Serwer HTTP MT5 uruchomiony na {self.host}:{self.port}")
            
            # Uruchamiamy serwer w osobnym wątku
            self.is_running = True
            threading.Thread(target=self.server.serve_forever, daemon=True).start()
            
            # Inicjalne pobranie historii transakcji
            threading.Thread(target=self.fetch_history_data, daemon=True).start()
            
            # Uruchamiamy wątek do okresowego odświeżania danych
            self._start_refresh_thread()
            
            return True
        except Exception as e:
            logger.error(f"Błąd podczas uruchamiania serwera: {str(e)}")
            self.stop()
            return False
            
    def _start_refresh_thread(self):
        """Uruchamia wątek odświeżający dane co jakiś czas."""
        def refresh_worker():
            # Definicje interwałów odświeżania (w sekundach)
            account_refresh_interval = 60  # co 1 minutę
            market_data_refresh_interval = 30  # co 30 sekund
            positions_refresh_interval = 15  # co 15 sekund
            history_refresh_interval = 300  # co 5 minut
            
            # Liczniki do śledzenia, kiedy ostatnio odświeżono dane
            account_counter = 0
            market_data_counter = 0
            positions_counter = 0
            history_counter = 0
            
            while self.is_running:
                try:
                    # Logika odświeżania różnych typów danych w różnych interwałach
                    
                    # Odświeżanie informacji o koncie
                    if account_counter >= account_refresh_interval:
                        logger.debug("Odświeżanie informacji o koncie")
                        self.request_account_info()
                        account_counter = 0
                    
                    # Odświeżanie danych rynkowych dla obserwowanych instrumentów
                    if market_data_counter >= market_data_refresh_interval:
                        logger.debug("Odświeżanie danych rynkowych")
                        # Pobierz aktualną listę obserwowanych instrumentów
                        for instrument in self.get_observed_instruments():
                            self.request_market_data(instrument)
                        market_data_counter = 0
                    
                    # Odświeżanie informacji o pozycjach
                    if positions_counter >= positions_refresh_interval:
                        logger.debug("Odświeżanie informacji o pozycjach")
                        self.request_positions()
                        positions_counter = 0
                    
                    # Odświeżanie historii transakcji
                    if history_counter >= history_refresh_interval:
                        logger.debug("Odświeżanie historii transakcji")
                        self.fetch_history_data()
                        history_counter = 0
                    
                    # Czekaj 1 sekundę i zwiększ liczniki
                    time.sleep(1)
                    account_counter += 1
                    market_data_counter += 1
                    positions_counter += 1
                    history_counter += 1
                    
                except Exception as e:
                    logger.error(f"Błąd podczas odświeżania danych: {str(e)}")
                    # Krótkie oczekiwanie po błędzie
                    time.sleep(5)
        
        threading.Thread(target=refresh_worker, daemon=True).start()
        logger.info("Uruchomiono wątek odświeżania danych z zaawansowanym harmonogramem")
    
    def stop(self) -> None:
        """Zatrzymuje serwer HTTP."""
        if self.server:
            self.is_running = False
            self.server.shutdown()
            self.server.server_close()
            logger.info("Serwer HTTP MT5 zatrzymany")
    
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
        Pobiera informacje o koncie MT5.
        
        Returns:
            Dict[str, Any]: Słownik z informacjami o koncie
        """
        try:
            if not mt5.initialize():
                logger.error("Nie udało się zainicjalizować MT5")
                return {}
                
            account_info = mt5.account_info()
            if account_info is None:
                logger.error("Nie udało się pobrać informacji o koncie")
                return {}
                
            return {
                "balance": account_info.balance,
                "equity": account_info.equity,
                "margin": account_info.margin,
                "free_margin": account_info.margin_free,
                "margin_level": account_info.margin_level,
                "positions": len(mt5.positions_get())
            }
        except Exception as e:
            logger.error(f"Błąd podczas pobierania informacji o koncie: {str(e)}")
            return {}
    
    def request_account_info(self) -> bool:
        """
        Żąda odświeżenia informacji o koncie.
        
        Returns:
            bool: True, jeśli żądanie zostało wysłane pomyślnie
        """
        try:
            if not MT5_AVAILABLE or not mt5.initialize():
                logger.warning("MT5 nie jest dostępny, nie można pobrać informacji o koncie")
                return False
                
            # Pobierz informacje o koncie
            account_info = mt5.account_info()
            
            if account_info is None:
                logger.warning("Nie można pobrać informacji o koncie z MT5")
                return False
                
            # Konwersja do słownika
            account_info_dict = {
                "login": account_info.login,
                "balance": account_info.balance,
                "equity": account_info.equity,
                "margin": account_info.margin,
                "free_margin": account_info.margin_free,
                "margin_level": account_info.margin_level,
                "leverage": account_info.leverage,
                "currency": account_info.currency
            }
            
            # Aktualizacja ostatnich informacji o koncie
            with self.lock:
                self.last_account_info = account_info_dict
                
            logger.debug(f"Zaktualizowano informacje o koncie: Saldo={account_info_dict['balance']}, Equity={account_info_dict['equity']}")
            
            return True
            
        except Exception as e:
            logger.error(f"Błąd podczas pobierania informacji o koncie: {str(e)}")
            return False
            
    def request_market_data(self, symbol: str) -> bool:
        """
        Żąda odświeżenia danych rynkowych dla danego symbolu.
        
        Args:
            symbol: Symbol instrumentu
            
        Returns:
            bool: True, jeśli żądanie zostało wysłane pomyślnie
        """
        try:
            if not MT5_AVAILABLE or not mt5.initialize():
                logger.warning(f"MT5 nie jest dostępny, nie można pobrać danych dla {symbol}")
                return False
                
            # Pobierz aktualną cenę symbolu
            symbol_info = mt5.symbol_info(symbol)
            
            if symbol_info is None:
                logger.warning(f"Symbol {symbol} nie jest dostępny w MT5")
                return False
                
            # Utworzenie struktury danych rynkowych
            market_data = {
                "symbol": symbol,
                "bid": symbol_info.bid,
                "ask": symbol_info.ask,
                "last": symbol_info.last,
                "volume": symbol_info.volume,
                "time": datetime.datetime.now().isoformat(),
                "timeframe": "CURRENT"
            }
            
            # Aktualizacja ostatnich danych rynkowych
            with self.lock:
                self.last_market_data[symbol] = market_data
                
            logger.debug(f"Zaktualizowano dane rynkowe dla {symbol}: Bid={market_data['bid']}, Ask={market_data['ask']}")
            
            return True
            
        except Exception as e:
            logger.error(f"Błąd podczas pobierania danych rynkowych dla {symbol}: {str(e)}")
            return False
            
    def request_positions(self) -> bool:
        """
        Żąda odświeżenia informacji o otwartych pozycjach.
        
        Returns:
            bool: True, jeśli żądanie zostało wysłane pomyślnie
        """
        try:
            if not MT5_AVAILABLE or not mt5.initialize():
                logger.warning("MT5 nie jest dostępny, nie można pobrać informacji o pozycjach")
                return False
                
            # Pobierz informacje o otwartych pozycjach
            positions = mt5.positions_get()
            
            if positions is None:
                logger.warning("Nie można pobrać informacji o pozycjach z MT5")
                return False
                
            # Konwersja do listy słowników
            positions_list = []
            for position in positions:
                position_dict = {
                    "ticket": position.ticket,
                    "symbol": position.symbol,
                    "type": "BUY" if position.type == mt5.POSITION_TYPE_BUY else "SELL",
                    "volume": position.volume,
                    "open_price": position.price_open,
                    "current_price": position.price_current,
                    "sl": position.sl,
                    "tp": position.tp,
                    "profit": position.profit,
                    "comment": position.comment,
                    "magic": position.magic,
                    "open_time": datetime.datetime.fromtimestamp(position.time).isoformat()
                }
                positions_list.append(position_dict)
                
            # Aktualizacja ostatnich informacji o pozycjach
            with self.lock:
                self.last_positions_data = positions_list
                
            logger.debug(f"Zaktualizowano informacje o pozycjach: {len(positions_list)} aktywnych pozycji")
            
            return True
            
        except Exception as e:
            logger.error(f"Błąd podczas pobierania informacji o pozycjach: {str(e)}")
            return False
    
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
    
    def _handle_market_data(self, data: str) -> None:
        """
        Przetwarza dane rynkowe od EA MT5.
        
        Args:
            data: Dane w formacie JSON
        """
        try:
            market_data = self._parse_data(data)
            
            # Aktualizujemy dane rynkowe
            with self.lock:
                symbol = market_data.get("symbol", "unknown")
                self.last_market_data[symbol] = market_data
                self.last_connection_time = datetime.datetime.now()
                
            logger.info(f"Otrzymano dane rynkowe dla {symbol}")
            
            # Wywołujemy callback, jeśli istnieje
            if "MARKET_DATA" in self.callback_handlers:
                try:
                    self.callback_handlers["MARKET_DATA"](data)
                except Exception as e:
                    logger.error(f"Błąd w callbacku dla MARKET_DATA: {str(e)}")
        except Exception as e:
            logger.error(f"Błąd podczas przetwarzania danych rynkowych: {str(e)}")

    def _handle_positions_update(self, data: str) -> None:
        """
        Przetwarza aktualizację pozycji od EA MT5.
        
        Args:
            data: Dane w formacie JSON
        """
        try:
            positions_data = self._parse_data(data)
            
            # Aktualizujemy dane o pozycjach
            with self.lock:
                if "positions" in positions_data:
                    positions = positions_data.get("positions", [])
                    # Organizujemy pozycje według ticketu
                    positions_dict = {}
                    for position in positions:
                        ticket = position.get("ticket", 0)
                        if ticket > 0:
                            positions_dict[ticket] = position
                    
                    self.last_positions_data = positions_dict
                else:
                    # Dla kompatybilności ze starszym formatem
                    ticket = positions_data.get("ticket", 0)
                    if ticket > 0:
                        self.last_positions_data[ticket] = positions_data
                
                self.last_connection_time = datetime.datetime.now()
                
            logger.info(f"Otrzymano aktualizację pozycji: {len(self.last_positions_data)} pozycji")
            
            # Wywołujemy callback, jeśli istnieje
            if "POSITIONS_UPDATE" in self.callback_handlers:
                try:
                    self.callback_handlers["POSITIONS_UPDATE"](data)
                except Exception as e:
                    logger.error(f"Błąd w callbacku dla POSITIONS_UPDATE: {str(e)}")
        except Exception as e:
            logger.error(f"Błąd podczas przetwarzania aktualizacji pozycji: {str(e)}")

    def _handle_account_info(self, data: str) -> None:
        """
        Przetwarza informacje o koncie od EA MT5.
        
        Args:
            data: Dane w formacie JSON
        """
        try:
            account_info = self._parse_data(data)
            
            # Aktualizujemy informacje o koncie
            with self.lock:
                self.last_account_info = account_info
                self.last_connection_time = datetime.datetime.now()
                
            logger.info(f"Otrzymano informacje o koncie: {account_info.get('ea_id', 'unknown')}")
            
            # Wywołujemy callback, jeśli istnieje
            if "ACCOUNT_INFO" in self.callback_handlers:
                try:
                    self.callback_handlers["ACCOUNT_INFO"](data)
                except Exception as e:
                    logger.error(f"Błąd w callbacku dla ACCOUNT_INFO: {str(e)}")
        except Exception as e:
            logger.error(f"Błąd podczas przetwarzania informacji o koncie: {str(e)}")

    def _parse_data(self, data: str) -> Dict[str, Any]:
        """
        Parsuje dane JSON.
        
        Args:
            data: Dane w formacie JSON
            
        Returns:
            Dict: Sparsowane dane
        """
        try:
            return json.loads(data)
        except json.JSONDecodeError:
            logger.error(f"Nieprawidłowy format JSON: {data}")
            return {}

    def get_recent_transactions(self) -> List[Dict[str, Any]]:
        """
        Pobiera listę ostatnich transakcji.
        
        Returns:
            List[Dict]: Lista ostatnich transakcji
        """
        with self.lock:
            # Jeśli mamy historię z MT5, użyj jej
            if self.history_data:
                # Przekształcamy dane historii do formatu wymaganego przez interfejs
                transactions = []
                for i, history_item in enumerate(self.history_data[:10]):  # Pobierz max 10 transakcji
                    try:
                        transaction = {
                            "id": i,
                            "symbol": history_item.get("symbol", ""),
                            "type": history_item.get("type", ""),
                            "open_time": history_item.get("open_time", ""),
                            "close_time": history_item.get("close_time", ""),
                            "profit": float(history_item.get("profit", 0)),
                            "status": "CLOSED" if history_item.get("close_time") else "OPEN"
                        }
                        transactions.append(transaction)
                    except Exception as e:
                        logger.error(f"Błąd podczas przetwarzania elementu historii: {e}")
                
                return transactions
            
            # Jeśli brak historii, sprawdź czy mamy aktywne pozycje
            active_positions = []
            for ticket, position in self.last_positions_data.items():
                try:
                    transaction = {
                        "id": len(active_positions),
                        "symbol": position.get("symbol", ""),
                        "type": position.get("type", ""),
                        "open_time": position.get("open_time", ""),
                        "close_time": None,
                        "profit": float(position.get("profit", 0)),
                        "status": "OPEN"
                    }
                    active_positions.append(transaction)
                except Exception as e:
                    logger.error(f"Błąd podczas przetwarzania pozycji: {e}")
            
            # Jeśli są aktywne pozycje, zwróć je
            if active_positions:
                return active_positions
            
            # Jeśli brak danych, zwróć przykładowe dane
            return [
                {"id": 1, "symbol": "EURUSD", "type": "BUY", "open_time": str(datetime.datetime.now() - datetime.timedelta(hours=2)), 
                "close_time": str(datetime.datetime.now() - datetime.timedelta(minutes=45)), "profit": 45.80, "status": "CLOSED"},
                {"id": 2, "symbol": "GOLD", "type": "SELL", "open_time": str(datetime.datetime.now() - datetime.timedelta(hours=3)), 
                "close_time": None, "profit": -12.35, "status": "OPEN"},
                {"id": 3, "symbol": "USDJPY", "type": "BUY", "open_time": str(datetime.datetime.now() - datetime.timedelta(hours=4)), 
                "close_time": str(datetime.datetime.now() - datetime.timedelta(hours=2)), "profit": 33.25, "status": "CLOSED"},
            ]

    def get_alerts(self) -> List[Dict[str, Any]]:
        """
        Pobiera listę alertów systemu.
        
        Returns:
            List[Dict]: Lista alertów
        """
        # Jeśli nie mamy prawdziwych danych, zwracamy przykładowe
        if not self.alerts:
            # Przykładowe dane alertów
            self.alerts = [
                {
                    "id": "alert1",
                    "level": "info",
                    "category": "system",
                    "message": "System uruchomiony pomyślnie",
                    "timestamp": str(self.start_time),
                    "status": "acknowledged"
                }
            ]
            
        with self.lock:
            return self.alerts

    def _handle_history_data(self, data: str) -> None:
        """
        Przetwarza dane historii transakcji z MT5.
        
        Args:
            data: Dane w formacie JSON
        """
        try:
            history_data = self._parse_data(data)
            
            with self.lock:
                if "history" in history_data and isinstance(history_data["history"], list):
                    self.history_data = history_data["history"]
                    self.last_connection_time = datetime.datetime.now()
                
            logger.info(f"Otrzymano dane historii: {len(self.history_data)} transakcji")
            
            # Wywołujemy callback, jeśli istnieje
            if "HISTORY_DATA" in self.callback_handlers:
                try:
                    self.callback_handlers["HISTORY_DATA"](data)
                except Exception as e:
                    logger.error(f"Błąd w callbacku dla HISTORY_DATA: {str(e)}")
        except Exception as e:
            logger.error(f"Błąd podczas przetwarzania danych historii: {str(e)}")

    def update_observed_instruments(self, instruments: List[str]) -> bool:
        """
        Aktualizuje listę obserwowanych instrumentów.
        
        Args:
            instruments: Lista symboli instrumentów do obserwowania
            
        Returns:
            bool: True, jeśli aktualizacja się powiodła
        """
        try:
            if not instruments:
                logger.warning("Próba aktualizacji listy instrumentów z pustą listą")
                return False
                
            # Sprawdź, czy wszystkie instrumenty są dostępne w MT5
            if MT5_AVAILABLE and mt5.initialize():
                valid_instruments = []
                invalid_instruments = []
                
                for instrument in instruments:
                    if mt5.symbol_info(instrument) is not None:
                        valid_instruments.append(instrument)
                    else:
                        invalid_instruments.append(instrument)
                        
                if invalid_instruments:
                    logger.warning(f"Następujące instrumenty nie są dostępne w MT5: {', '.join(invalid_instruments)}")
                    
                # Aktualizuj listę tylko prawidłowymi instrumentami
                if valid_instruments:
                    with self.lock:
                        self.observed_instruments = valid_instruments
                    logger.info(f"Zaktualizowano listę obserwowanych instrumentów: {', '.join(valid_instruments)}")
                    return True
                else:
                    logger.error("Żaden z podanych instrumentów nie jest dostępny w MT5")
                    return False
            else:
                # Jeśli MT5 nie jest dostępny, po prostu zapisz listę bez walidacji
                with self.lock:
                    self.observed_instruments = instruments
                logger.info(f"Zaktualizowano listę obserwowanych instrumentów bez walidacji: {', '.join(instruments)}")
                return True
                
        except Exception as e:
            logger.error(f"Błąd podczas aktualizacji listy obserwowanych instrumentów: {str(e)}")
            return False
            
    def get_observed_instruments(self) -> List[str]:
        """
        Zwraca listę obserwowanych instrumentów.
        
        Returns:
            List[str]: Lista obserwowanych instrumentów
        """
        with self.lock:
            return self.observed_instruments.copy()


# Przykład użycia jako standalone server
if __name__ == "__main__":
    try:
        server = MT5Server()
        if server.start():
            print("Naciśnij Ctrl+C aby zatrzymać serwer...")
            
            # Przykład callbacków
            def on_market_data(data):
                print(f"Callback: Otrzymano dane rynkowe: {data[:100]}...")
                
            def on_positions_update(data):
                print(f"Callback: Otrzymano aktualizację pozycji: {data[:100]}...")
                
            def on_account_info(data):
                print(f"Callback: Otrzymano informacje o koncie: {data[:100]}...")
            
            server.register_callback("MARKET_DATA", on_market_data)
            server.register_callback("POSITIONS_UPDATE", on_positions_update)
            server.register_callback("ACCOUNT_INFO", on_account_info)
            
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
            server.shutdown() 