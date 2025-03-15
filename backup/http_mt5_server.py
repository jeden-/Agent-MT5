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

# Import komponentów monitorowania
from src.monitoring.monitoring_logger import get_logger as get_monitoring_logger
from src.monitoring.monitoring_logger import OperationType, OperationStatus, LogLevel
from src.monitoring.connection_tracker import get_connection_tracker
from src.monitoring.alert_manager import get_alert_manager, AlertLevel, AlertCategory, initialize_default_rules
from src.monitoring.status_reporter import get_status_reporter

# Konfiguracja loggera
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

logger = logging.getLogger('HTTP_MT5_Server')

# Inicjalizacja komponentów monitorowania
monitoring_logger = get_monitoring_logger()
connection_tracker = get_connection_tracker()
alert_manager = get_alert_manager()
status_reporter = get_status_reporter()
initialize_default_rules()

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
            start_time = time.time()
            status_reporter.increment_request_counter()
            
            parsed_url = urlparse(self.path)
            path = parsed_url.path
            query = parse_qs(parsed_url.query)
            
            # Wyciągnięcie EA ID z query
            ea_id = query.get('ea_id', ['UNKNOWN'])[0]
            
            # Aktualizacja aktywności połączenia
            connection_tracker.update_activity(ea_id)
            
            if path == '/ping':
                self.handle_ping()
            elif path == '/commands':
                self.handle_get_commands(query)
            elif path == '/status':
                self.handle_server_status()
            elif path == '/account_info/get':
                self.handle_get_account_info(query)
            # Dodanie nowych endpointów monitorowania
            elif path == '/monitoring/logs':
                self.handle_get_logs(query)
            elif path == '/monitoring/connections':
                self.handle_get_connections(query)
            elif path == '/monitoring/alerts':
                self.handle_get_alerts(query)
            elif path == '/monitoring/status':
                self.handle_get_monitoring_status(query)
            else:
                self.send_error_response("Endpoint not found")
            
            # Rejestracja czasu odpowiedzi
            response_time = (time.time() - start_time) * 1000  # w milisekundach
            status_reporter.record_response_time(response_time)
                
        except Exception as e:
            logger.error(f"Błąd podczas obsługi żądania GET: {str(e)}")
            monitoring_logger.error(
                "SYSTEM", 
                OperationType.SYSTEM, 
                OperationStatus.FAILED, 
                {"error": str(e), "path": self.path}, 
                f"Error in GET request handling: {str(e)}"
            )
            self.send_error_response(f"Internal server error: {str(e)}")
    
    def do_POST(self):
        """Obsługa zapytań POST."""
        try:
            start_time = time.time()
            status_reporter.increment_request_counter()
            
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length).decode('utf-8')
            
            try:
                data = json.loads(post_data)
            except json.JSONDecodeError as e:
                logger.error(f"Błąd parsowania JSON: {str(e)}")
                monitoring_logger.error(
                    "SYSTEM", 
                    OperationType.SYSTEM, 
                    OperationStatus.FAILED, 
                    {"error": str(e), "data": post_data}, 
                    f"JSON parse error in POST request: {str(e)}"
                )
                self.send_error_response(f"Invalid JSON: {str(e)}")
                return
            
            # Wyciągnięcie EA ID z danych
            ea_id = data.get('ea_id', 'UNKNOWN')
            
            # Aktualizacja aktywności połączenia
            connection_tracker.update_activity(ea_id)
            
            # Obsługa endpointów
            parsed_url = urlparse(self.path)
            path = parsed_url.path
            
            if path == '/init':
                self.handle_init(data)
            elif path == '/position/update':
                self.handle_position_update(data)
            elif path == '/market_data':
                self.handle_market_data(data)
            elif path == '/account_info':
                self.handle_account_info(data)
            elif path == '/position/modify':
                self.handle_modify_position(data)
                status_reporter.increment_command_counter()
            elif path == '/position/open':
                self.handle_open_position(data)
                status_reporter.increment_command_counter()
            elif path == '/position/close':
                self.handle_close_position(data)
                status_reporter.increment_command_counter()
            # Dodanie nowych endpointów monitorowania
            elif path == '/monitoring/acknowledge_alert':
                self.handle_acknowledge_alert(data)
            elif path == '/monitoring/resolve_alert':
                self.handle_resolve_alert(data)
            else:
                logger.warning(f"Nieznany endpoint: {path}")
                monitoring_logger.warning(
                    ea_id, 
                    OperationType.SYSTEM, 
                    OperationStatus.FAILED, 
                    {"path": path}, 
                    f"Unknown endpoint: {path}"
                )
                self.send_error_response("Endpoint not found")
            
            # Rejestracja czasu odpowiedzi
            response_time = (time.time() - start_time) * 1000  # w milisekundach
            status_reporter.record_response_time(response_time)
            
        except Exception as e:
            logger.error(f"Błąd podczas obsługi żądania POST: {str(e)}")
            monitoring_logger.error(
                "SYSTEM", 
                OperationType.SYSTEM, 
                OperationStatus.FAILED, 
                {"error": str(e), "path": self.path}, 
                f"Error in POST request handling: {str(e)}"
            )
            self.send_error_response(f"Internal server error: {str(e)}")
    
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
            self.send_error_response("Missing EA ID")
            return
        
        ea_id = data['ea_id']
        action = data.get('action', 'init')
        
        if action == 'shutdown':
            # EA informuje o zamknięciu
            logger.info(f"EA {ea_id} informuje o zamknięciu, powód: {data.get('reason', 'unknown')}")
            connection_tracker.disconnect(ea_id)
            
            monitoring_logger.info(
                ea_id,
                OperationType.INIT,
                OperationStatus.SUCCESS,
                {"action": "shutdown", "reason": data.get('reason', 'unknown')},
                f"EA shutdown, reason: {data.get('reason', 'unknown')}"
            )
        else:
            # EA informuje o inicjalizacji
            logger.info(f"EA {ea_id} zainicjalizowany: {json.dumps(data.get('terminal_info', {}))}")
            connection_tracker.register_connection(ea_id)
            
            monitoring_logger.info(
                ea_id,
                OperationType.INIT,
                OperationStatus.SUCCESS,
                {"terminal_info": data.get('terminal_info', {})},
                f"EA initialized with terminal info: {json.dumps(data.get('terminal_info', {}))}"
            )
        
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps({
            'status': 'ok',
            'message': f'Initialization from {ea_id} received'
        }).encode())
    
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
        """Obsługa aktualizacji informacji o koncie."""
        try:
            required_fields = ['ea_id']
            for field in required_fields:
                if field not in data:
                    self.send_error_response(f"Missing required field: {field}")
                    return
            
            ea_id = data['ea_id']
            
            # Zapisujemy dane konta
            with commands_lock:
                account_info[ea_id] = {
                    'account': data.get('account', 0),
                    'balance': data.get('balance', 0.0),
                    'equity': data.get('equity', 0.0),
                    'margin': data.get('margin', 0.0),
                    'free_margin': data.get('free_margin', 0.0),
                    'currency': data.get('currency', ''),
                    'profit': data.get('profit', 0.0),
                    'name': data.get('name', ''),
                    'leverage': data.get('leverage', 1),
                    'last_update': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
            
            # Logujemy operację
            logger.info(f"Zaktualizowano informacje o koncie EA {ea_id}")
            
            # Wysyłamy odpowiedź
            response = {
                'status': 'ok',
                'message': 'Account info updated successfully'
            }
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(response).encode('utf-8'))
            
        except Exception as e:
            logger.error(f"Błąd podczas aktualizacji informacji o koncie: {str(e)}")
            self.send_error_response(f"Error updating account info: {str(e)}")

    def handle_get_account_info(self, query):
        """Obsługa pobierania informacji o koncie."""
        try:
            if 'ea_id' not in query:
                self.send_error_response("Missing required parameter: ea_id")
                return
            
            ea_id = query['ea_id'][0]
            
            with commands_lock:
                if ea_id in account_info:
                    response = {
                        'status': 'ok',
                        'account_info': account_info[ea_id]
                    }
                else:
                    response = {
                        'status': 'warning',
                        'message': f'No account information for EA {ea_id}',
                        'account_info': {}
                    }
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(response).encode('utf-8'))
            
        except Exception as e:
            logger.error(f"Błąd podczas pobierania informacji o koncie: {str(e)}")
            self.send_error_response(f"Error retrieving account info: {str(e)}")

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
            
            monitoring_logger.error(
                data.get('ea_id', 'UNKNOWN'),
                OperationType.OPEN_POSITION,
                OperationStatus.FAILED,
                {"error": "Missing required fields", "data": data},
                f"Failed to open position: missing required fields"
            )
            status_reporter.record_operation_result(False)
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
        
        monitoring_logger.info(
            ea_id,
            OperationType.OPEN_POSITION,
            OperationStatus.SUCCESS,
            {"symbol": data['symbol'], "type": data['order_type'], "volume": data['volume']},
            f"Added open position command for {data['symbol']} {data['order_type']} {data['volume']}"
        )
        status_reporter.record_operation_result(True)
        
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
            
            monitoring_logger.error(
                data.get('ea_id', 'UNKNOWN'),
                OperationType.CLOSE_POSITION,
                OperationStatus.FAILED,
                {"error": "Missing required fields", "data": data},
                f"Failed to close position: missing required fields"
            )
            status_reporter.record_operation_result(False)
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
        
        monitoring_logger.info(
            ea_id,
            OperationType.CLOSE_POSITION,
            OperationStatus.SUCCESS,
            {"ticket": data['ticket'], "volume": data.get('volume')},
            f"Added close position command for ticket #{data['ticket']}{volume_info}"
        )
        status_reporter.record_operation_result(True)
        
        # Odpowiedź do klienta
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps({
            'status': 'ok',
            'message': 'Position close command added to queue'
        }).encode())

    # Nowe metody obsługi endpointów monitorowania
    
    def handle_get_logs(self, query):
        """Obsługa pobierania logów."""
        # Parametry filtrowania
        start_time = query.get('start_time', [None])[0]
        end_time = query.get('end_time', [None])[0]
        level = query.get('level', [None])[0]
        ea_id = query.get('ea_id', [None])[0]
        limit = int(query.get('limit', ['100'])[0])
        
        # Konwersja parametrów
        from datetime import datetime
        if start_time:
            try:
                start_time = datetime.fromisoformat(start_time)
            except ValueError:
                start_time = None
        if end_time:
            try:
                end_time = datetime.fromisoformat(end_time)
            except ValueError:
                end_time = None
        if level:
            try:
                level = LogLevel[level]
            except KeyError:
                level = None
        
        # Pobieranie logów
        logs = monitoring_logger.get_logs(
            start_time=start_time,
            end_time=end_time,
            level=level,
            ea_id=ea_id,
            limit=limit
        )
        
        # Konwersja do formatu JSON
        logs_json = [log.to_dict() for log in logs]
        
        # Wysłanie odpowiedzi
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps({
            'status': 'ok',
            'logs': logs_json
        }).encode())
    
    def handle_get_connections(self, query):
        """Obsługa pobierania informacji o połączeniach."""
        # Parametry filtrowania
        ea_id = query.get('ea_id', [None])[0]
        
        # Pobieranie informacji o połączeniach
        if ea_id:
            connection_info = connection_tracker.get_connection_info(ea_id)
            connections = [connection_info] if connection_info else []
        else:
            connections = connection_tracker.get_all_connections()
        
        # Wysłanie odpowiedzi
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps({
            'status': 'ok',
            'connections': connections
        }).encode())
    
    def handle_get_alerts(self, query):
        """Obsługa pobierania alertów."""
        # Parametry filtrowania
        level = query.get('level', [None])[0]
        category = query.get('category', [None])[0]
        status = query.get('status', [None])[0]
        ea_id = query.get('ea_id', [None])[0]
        start_time = query.get('start_time', [None])[0]
        end_time = query.get('end_time', [None])[0]
        limit = int(query.get('limit', ['100'])[0])
        
        # Konwersja parametrów
        from datetime import datetime
        if start_time:
            try:
                start_time = datetime.fromisoformat(start_time)
            except ValueError:
                start_time = None
        if end_time:
            try:
                end_time = datetime.fromisoformat(end_time)
            except ValueError:
                end_time = None
        if level:
            try:
                level = AlertLevel[level]
            except KeyError:
                level = None
        if category:
            try:
                category = AlertCategory[category]
            except KeyError:
                category = None
        if status:
            try:
                status = AlertStatus[status]
            except KeyError:
                status = None
        
        # Pobieranie alertów
        alerts = alert_manager.get_alerts(
            level=level,
            category=category,
            status=status,
            ea_id=ea_id,
            start_time=start_time,
            end_time=end_time,
            limit=limit
        )
        
        # Wysłanie odpowiedzi
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps({
            'status': 'ok',
            'alerts': alerts
        }).encode())
    
    def handle_get_monitoring_status(self, query):
        """Obsługa pobierania statusu monitorowania."""
        # Parametry
        detail_level = query.get('detail_level', ['basic'])[0]
        
        # Pobieranie statusu
        if detail_level == 'full':
            status = status_reporter.get_full_status()
        elif detail_level == 'detailed':
            status = status_reporter.get_detailed_status()
        else:
            status = status_reporter.get_basic_status()
        
        # Wysłanie odpowiedzi
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps({
            'status': 'ok',
            'system_status': status
        }).encode())
    
    def handle_acknowledge_alert(self, data):
        """Obsługa potwierdzania alertu."""
        # Sprawdzenie wymaganych pól
        if 'alert_id' not in data:
            self.send_error_response("Missing alert_id")
            return
        
        alert_id = int(data['alert_id'])
        by = data.get('by', 'system')
        
        # Potwierdzenie alertu
        success = alert_manager.acknowledge_alert(alert_id, by)
        
        # Wysłanie odpowiedzi
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        
        if success:
            self.wfile.write(json.dumps({
                'status': 'ok',
                'message': f'Alert {alert_id} acknowledged'
            }).encode())
        else:
            self.wfile.write(json.dumps({
                'status': 'error',
                'message': f'Alert {alert_id} not found or already acknowledged'
            }).encode())
    
    def handle_resolve_alert(self, data):
        """Obsługa rozwiązywania alertu."""
        # Sprawdzenie wymaganych pól
        if 'alert_id' not in data:
            self.send_error_response("Missing alert_id")
            return
        
        alert_id = int(data['alert_id'])
        by = data.get('by', 'system')
        
        # Rozwiązanie alertu
        success = alert_manager.resolve_alert(alert_id, by)
        
        # Wysłanie odpowiedzi
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        
        if success:
            self.wfile.write(json.dumps({
                'status': 'ok',
                'message': f'Alert {alert_id} resolved'
            }).encode())
        else:
            self.wfile.write(json.dumps({
                'status': 'error',
                'message': f'Alert {alert_id} not found or already resolved'
            }).encode())
    
    def send_error_response(self, message):
        """Wysyła odpowiedź błędu."""
        self.send_response(400)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps({
            'status': 'error',
            'message': message
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