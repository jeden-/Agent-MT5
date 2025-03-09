#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
HTTP Serwer dla MT5 EA - prosty serwer HTTP do obsługi zapytań z EA MT5.
Używa podejścia opartego na pollingu zamiast stałego połączenia.
"""

import http.server
import socketserver
import json
import logging
import argparse
import threading
import time
import os
from datetime import datetime
from urllib.parse import urlparse, parse_qs

# Konfiguracja loggera
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

logger = logging.getLogger('HTTP_MT5_Server')

# Globalny stan serwera
connected_clients = {}  # Słownik klientów: {ea_id: {last_active: timestamp, ...}}
command_queue = {}      # Kolejka poleceń dla EA: {ea_id: [command1, command2, ...]}
position_registry = {}  # Rejestr pozycji: {ticket: {symbol, type, volume, ...}}
operation_history = []  # Historia operacji
account_info = {}       # Informacje o koncie
market_data = {}        # Dane rynkowe: {symbol: {bid, ask, time, ...}}

# Mutex dla dostępu do współdzielonych zasobów
clients_lock = threading.Lock()
commands_lock = threading.Lock()
positions_lock = threading.Lock()
history_lock = threading.Lock()
account_lock = threading.Lock()
market_data_lock = threading.Lock()

class MT5RequestHandler(http.server.BaseHTTPRequestHandler):
    """Obsługa zapytań od EA poprzez HTTP."""
    
    def do_GET(self):
        """Obsługa zapytań GET."""
        try:
            parsed_url = urlparse(self.path)
            path = parsed_url.path
            query = parse_qs(parsed_url.query)
            
            if path == '/ping':
                self.handle_ping()
            elif path == '/commands':
                self.handle_get_commands(query)
            elif path == '/status':
                self.handle_server_status()
            else:
                self.send_response(404)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'status': 'error', 'message': 'Endpoint not found'}).encode())
        except Exception as e:
            logger.error(f"Błąd podczas obsługi zapytania GET: {str(e)}")
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'status': 'error', 'message': str(e)}).encode())
    
    def do_POST(self):
        """Obsługa zapytań POST."""
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            
            try:
                data = json.loads(post_data.decode('utf-8'))
            except json.JSONDecodeError:
                self.send_response(400)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'status': 'error', 'message': 'Invalid JSON'}).encode())
                return
            
            if self.path == '/init':
                self.handle_init(data)
            elif self.path == '/position/update':
                self.handle_position_update(data)
            elif self.path == '/market_data':
                self.handle_market_data(data)
            elif self.path == '/account_info':
                self.handle_account_info(data)
            elif self.path == '/position/open':
                self.handle_open_position(data)
            elif self.path == '/position/close':
                self.handle_close_position(data)
            elif self.path == '/position/modify':
                self.handle_modify_position(data)
            else:
                self.send_response(404)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'status': 'error', 'message': 'Endpoint not found'}).encode())
        except Exception as e:
            logger.error(f"Błąd podczas obsługi zapytania POST: {str(e)}")
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'status': 'error', 'message': str(e)}).encode())
    
    def handle_ping(self):
        """Obsługa pingowania serwera."""
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps({'status': 'ok', 'message': 'pong', 'time': datetime.now().isoformat()}).encode())
    
    def handle_get_commands(self, query):
        """Pobieranie poleceń dla EA."""
        if 'ea_id' not in query:
            self.send_response(400)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'status': 'error', 'message': 'Missing ea_id parameter'}).encode())
            return
        
        ea_id = query['ea_id'][0]
        
        # Aktualizacja czasu ostatniej aktywności klienta
        with clients_lock:
            if ea_id in connected_clients:
                connected_clients[ea_id]['last_active'] = time.time()
            else:
                connected_clients[ea_id] = {'last_active': time.time()}
        
        # Pobieranie poleceń z kolejki
        commands = []
        with commands_lock:
            if ea_id in command_queue and command_queue[ea_id]:
                commands = command_queue[ea_id]
                command_queue[ea_id] = []  # Czyszczenie kolejki po pobraniu
        
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps({'status': 'ok', 'commands': commands}).encode())
    
    def handle_server_status(self):
        """Zwracanie statusu serwera."""
        with clients_lock:
            # Usuwanie nieaktywnych klientów (timeout 60 sekund)
            current_time = time.time()
            inactive_clients = [ea_id for ea_id, client in connected_clients.items() 
                              if current_time - client['last_active'] > 60]
            
            for ea_id in inactive_clients:
                del connected_clients[ea_id]
            
            client_count = len(connected_clients)
            client_list = list(connected_clients.keys())
        
        with positions_lock:
            position_count = len(position_registry)
        
        status_data = {
            'status': 'ok',
            'server_time': datetime.now().isoformat(),
            'uptime': time.time() - server_start_time,
            'clients': {
                'count': client_count,
                'list': client_list
            },
            'positions': {
                'count': position_count
            }
        }
        
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(status_data).encode())
    
    def handle_init(self, data):
        """Obsługa inicjalizacji EA."""
        if 'ea_id' not in data:
            self.send_response(400)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'status': 'error', 'message': 'Missing ea_id parameter'}).encode())
            return
        
        ea_id = data['ea_id']
        
        with clients_lock:
            # Zapisanie lub aktualizacja informacji o kliencie
            if 'action' in data and data['action'] == 'shutdown':
                # EA informuje o zamknięciu
                if ea_id in connected_clients:
                    logger.info(f"Klient {ea_id} zgłosił zamknięcie, powód: {data.get('reason', 'nieznany')}")
                    del connected_clients[ea_id]
            else:
                # Nowa inicjalizacja EA
                connected_clients[ea_id] = {
                    'last_active': time.time(),
                    'terminal_info': data.get('terminal_info', {}),
                    'init_time': datetime.now().isoformat()
                }
                logger.info(f"Nowy klient podłączony: {ea_id}")
        
        # Przygotowanie odpowiedzi
        response = {
            'status': 'ok',
            'message': 'Initialization successful',
            'server_time': datetime.now().isoformat()
        }
        
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(response).encode())
    
    def handle_position_update(self, data):
        """Aktualizacja informacji o pozycji."""
        if 'ea_id' not in data or 'ticket' not in data:
            self.send_response(400)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'status': 'error', 'message': 'Missing required parameters'}).encode())
            return
        
        ea_id = data['ea_id']
        ticket = data['ticket']
        
        # Aktualizacja czasu ostatniej aktywności klienta
        with clients_lock:
            if ea_id in connected_clients:
                connected_clients[ea_id]['last_active'] = time.time()
        
        # Aktualizacja rejestru pozycji
        with positions_lock:
            position_registry[ticket] = {
                'ea_id': ea_id,
                'symbol': data.get('symbol', ''),
                'type': data.get('type', ''),
                'volume': data.get('volume', 0.0),
                'open_price': data.get('open_price', 0.0),
                'current_price': data.get('current_price', 0.0),
                'sl': data.get('sl', 0.0),
                'tp': data.get('tp', 0.0),
                'profit': data.get('profit', 0.0),
                'open_time': data.get('open_time', ''),
                'last_update': datetime.now().isoformat()
            }
        
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps({'status': 'ok', 'message': f'Position {ticket} updated'}).encode())
    
    def handle_market_data(self, data):
        """Obsługa danych rynkowych."""
        if 'ea_id' not in data or 'symbol' not in data:
            self.send_response(400)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'status': 'error', 'message': 'Missing required parameters'}).encode())
            return
        
        ea_id = data['ea_id']
        symbol = data['symbol']
        
        # Aktualizacja czasu ostatniej aktywności klienta
        with clients_lock:
            if ea_id in connected_clients:
                connected_clients[ea_id]['last_active'] = time.time()
        
        # Aktualizacja danych rynkowych
        with market_data_lock:
            market_data[symbol] = {
                'bid': data.get('bid', 0.0),
                'ask': data.get('ask', 0.0),
                'time': data.get('time', ''),
                'volume': data.get('volume', 0),
                'spread': data.get('spread', 0),
                'last_update': datetime.now().isoformat(),
                'updated_by': ea_id
            }
        
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps({'status': 'ok', 'message': f'Market data for {symbol} updated'}).encode())
    
    def handle_account_info(self, data):
        """Obsługa informacji o koncie."""
        if 'ea_id' not in data or 'account' not in data:
            self.send_response(400)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'status': 'error', 'message': 'Missing required parameters'}).encode())
            return
        
        ea_id = data['ea_id']
        account_id = data['account']
        
        # Aktualizacja czasu ostatniej aktywności klienta
        with clients_lock:
            if ea_id in connected_clients:
                connected_clients[ea_id]['last_active'] = time.time()
        
        # Aktualizacja informacji o koncie
        with account_lock:
            account_info[account_id] = {
                'balance': data.get('balance', 0.0),
                'equity': data.get('equity', 0.0),
                'margin': data.get('margin', 0.0),
                'free_margin': data.get('free_margin', 0.0),
                'currency': data.get('currency', ''),
                'profit': data.get('profit', 0.0),
                'name': data.get('name', ''),
                'leverage': data.get('leverage', 0),
                'last_update': datetime.now().isoformat(),
                'updated_by': ea_id
            }
        
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps({'status': 'ok', 'message': f'Account info for {account_id} updated'}).encode())

    def handle_modify_position(self, data):
        """Obsługa modyfikacji pozycji."""
        required_fields = ['ea_id', 'ticket']
        if not all(field in data for field in required_fields):
            self.send_response(400)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({
                'status': 'error', 
                'message': f'Missing required fields. Required: {required_fields}'
            }).encode())
            return
        
        # Przygotowanie polecenia modyfikacji pozycji
        command = {
            'action': 'MODIFY_POSITION',
            'ticket': data['ticket'],
            'timestamp': datetime.now().isoformat()
        }
        
        # Dodanie opcjonalnych parametrów
        if 'sl' in data:
            command['sl'] = data['sl']
        if 'tp' in data:
            command['tp'] = data['tp']
        
        # Dodanie polecenia do kolejki dla danego EA
        ea_id = data['ea_id']
        with commands_lock:
            if ea_id not in command_queue:
                command_queue[ea_id] = []
            command_queue[ea_id].append(command)
        
        # Logowanie operacji
        logger.info(f"Dodano polecenie modyfikacji pozycji #{data['ticket']} dla EA {ea_id}")
        
        # Odpowiedź do klienta
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps({
            'status': 'ok',
            'message': 'Position modification command added to queue'
        }).encode())

    def handle_open_position(self, data):
        """Obsługa otwierania nowej pozycji."""
        required_fields = ['ea_id', 'symbol', 'order_type', 'volume']
        if not all(field in data for field in required_fields):
            self.send_response(400)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({
                'status': 'error', 
                'message': f'Missing required fields. Required: {required_fields}'
            }).encode())
            return
        
        # Przygotowanie polecenia otwarcia pozycji
        command = {
            'action': 'OPEN_POSITION',
            'symbol': data['symbol'],
            'type': data['order_type'],
            'volume': data['volume'],
            'timestamp': datetime.now().isoformat()
        }
        
        # Dodanie opcjonalnych parametrów
        if 'price' in data:
            command['price'] = data['price']
        if 'sl' in data:
            command['sl'] = data['sl']
        if 'tp' in data:
            command['tp'] = data['tp']
        if 'comment' in data:
            command['comment'] = data['comment']
        
        # Dodanie polecenia do kolejki dla danego EA
        ea_id = data['ea_id']
        with commands_lock:
            if ea_id not in command_queue:
                command_queue[ea_id] = []
            command_queue[ea_id].append(command)
        
        # Logowanie operacji
        logger.info(f"Dodano polecenie otwarcia pozycji {data['symbol']} {data['order_type']} {data['volume']} dla EA {ea_id}")
        
        # Odpowiedź do klienta
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps({
            'status': 'ok',
            'message': 'Position open command added to queue'
        }).encode())

    def handle_close_position(self, data):
        """Obsługa zamykania pozycji."""
        required_fields = ['ea_id', 'ticket']
        if not all(field in data for field in required_fields):
            self.send_response(400)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({
                'status': 'error', 
                'message': f'Missing required fields. Required: {required_fields}'
            }).encode())
            return
        
        # Przygotowanie polecenia zamknięcia pozycji
        command = {
            'action': 'CLOSE_POSITION',
            'ticket': data['ticket'],
            'timestamp': datetime.now().isoformat()
        }
        
        # Dodanie opcjonalnego parametru volume dla częściowego zamknięcia
        if 'volume' in data:
            command['volume'] = data['volume']
        
        # Dodanie polecenia do kolejki dla danego EA
        ea_id = data['ea_id']
        with commands_lock:
            if ea_id not in command_queue:
                command_queue[ea_id] = []
            command_queue[ea_id].append(command)
        
        # Logowanie operacji
        volume_info = f" (volume={data['volume']})" if 'volume' in data else ""
        logger.info(f"Dodano polecenie zamknięcia pozycji #{data['ticket']}{volume_info} dla EA {ea_id}")
        
        # Odpowiedź do klienta
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps({
            'status': 'ok',
            'message': 'Position close command added to queue'
        }).encode())

def status_printer():
    """Funkcja wypisująca status serwera co minutę."""
    while True:
        try:
            with clients_lock:
                client_count = len(connected_clients)
            
            with positions_lock:
                position_count = len(position_registry)
            
            logger.info(f"Status serwera: {client_count} aktywnych klientów, {position_count} zarejestrowanych pozycji")
            time.sleep(60)
        except Exception as e:
            logger.error(f"Błąd w funkcji status_printer: {str(e)}")
            time.sleep(60)

def main():
    global server_start_time
    
    parser = argparse.ArgumentParser(description='HTTP Server dla Expert Advisor MT5')
    parser.add_argument('--host', default='127.0.0.1', help='Adres hosta (domyślnie: 127.0.0.1)')
    parser.add_argument('--port', type=int, default=5555, help='Port (domyślnie: 5555)')
    args = parser.parse_args()
    
    # Zapisanie czasu startu serwera
    server_start_time = time.time()
    
    # Uruchomienie threada do wypisywania statusu
    status_thread = threading.Thread(target=status_printer, daemon=True)
    status_thread.start()
    
    # Utworzenie serwera HTTP
    server = socketserver.ThreadingTCPServer((args.host, args.port), MT5RequestHandler)
    
    logger.info(f"Serwer HTTP uruchomiony na {args.host}:{args.port}")
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("Zatrzymanie serwera")
    finally:
        server.server_close()

if __name__ == "__main__":
    main() 