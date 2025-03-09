#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Rozbudowany skrypt diagnostyczny do testowania połączenia z MT5
"""

import os
import sys
import time
import socket
import threading
import logging
from pathlib import Path
import datetime

# Dodajemy katalog główny projektu do ścieżki, aby móc importować moduły
sys.path.append(str(Path(__file__).parent.parent))

# Konfiguracja logowania
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("MT5Diagnostic")

def check_port_available(host, port):
    """Sprawdza, czy port jest dostępny."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(1)
        result = s.connect_ex((host, port))
        s.close()
        return result != 0  # Port jest dostępny, jeśli nie można nawiązać połączenia
    except:
        return False

def wait_for_connection(host, port, timeout=60):
    """Czeka na połączenie z EA na określonym porcie."""
    logger.info(f"Nasłuchiwanie na porcie {port} przez maksymalnie {timeout} sekund...")
    
    start_time = time.time()
    server_socket = None
    
    try:
        # Tworzymy socket
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.settimeout(1.0)  # 1 sekunda timeout
        
        # Bindujemy do portu
        server_socket.bind((host, port))
        server_socket.listen(1)
        
        while time.time() - start_time < timeout:
            try:
                client_socket, address = server_socket.accept()
                logger.info(f"Połączenie nawiązane od {address}")
                client_socket.close()
                return True
            except socket.timeout:
                # Timeout - normalne zachowanie podczas oczekiwania
                pass
            except Exception as e:
                logger.error(f"Błąd podczas nasłuchiwania: {str(e)}")
                break
                
            # Krótkie opóźnienie, aby nie obciążać CPU
            time.sleep(0.1)
            
        logger.error(f"Timeout - nie otrzymano połączenia przez {timeout} sekund")
        return False
    except Exception as e:
        logger.error(f"Błąd podczas konfiguracji serwera: {str(e)}")
        return False
    finally:
        if server_socket:
            server_socket.close()

def start_simple_tcp_server(host, port):
    """Uruchamia prosty serwer TCP do testów."""
    try:
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind((host, port))
        server_socket.listen(5)
        server_socket.settimeout(1.0)  # 1 sekunda timeout
        
        logger.info(f"Serwer diagnostyczny uruchomiony na {host}:{port}")
        logger.info("Naciśnij Ctrl+C aby zatrzymać serwer...")
        
        clients = []
        running = True
        
        # Funkcja do odbierania danych od klienta
        def handle_client(client_socket, address):
            logger.info(f"Nowe połączenie od {address}")
            try:
                # Wysyłamy wiadomość powitalną
                client_socket.send(b"CONNECTED:Server is ready\n")
                
                while running:
                    try:
                        # Odbieramy dane
                        data = client_socket.recv(1024)
                        if not data:
                            logger.info(f"Klient {address} rozłączony")
                            break
                            
                        # Dekodujemy i wyświetlamy dane
                        message = data.decode('utf-8').strip()
                        logger.info(f"Otrzymano wiadomość od {address}: {message}")
                        
                        # Wysyłamy odpowiedź
                        if message.startswith("PING"):
                            client_socket.send(b"PONG:Diagnostics\n")
                        elif message.startswith("GET_ACCOUNT_INFO"):
                            client_socket.send(b"ACCOUNT_INFO:BALANCE:10000;EQUITY:10000;MARGIN:0;FREE_MARGIN:10000\n")
                        elif message.startswith("GET_MARKET_DATA"):
                            client_socket.send(b"MARKET_DATA:SYMBOL:EURUSD;BID:1.1;ASK:1.11;SPREAD:10\n")
                        else:
                            client_socket.send(f"ECHO:{message}\n".encode('utf-8'))
                            
                    except socket.timeout:
                        # Timeout - normalne zachowanie
                        pass
                    except Exception as e:
                        logger.error(f"Błąd podczas obsługi klienta {address}: {str(e)}")
                        break
                        
                    # Krótka pauza, aby nie obciążać CPU
                    time.sleep(0.1)
            finally:
                # Zamykamy socket klienta
                if client_socket in clients:
                    clients.remove(client_socket)
                    
                try:
                    client_socket.close()
                except:
                    pass
                    
                logger.info(f"Zakończono obsługę klienta {address}")
        
        # Główna pętla serwera
        try:
            while running:
                try:
                    # Akceptujemy nowe połączenia
                    client_socket, address = server_socket.accept()
                    client_socket.settimeout(1.0)
                    clients.append(client_socket)
                    
                    # Uruchamiamy wątek obsługujący klienta
                    client_thread = threading.Thread(target=handle_client, args=(client_socket, address))
                    client_thread.daemon = True
                    client_thread.start()
                except socket.timeout:
                    # Timeout - normalne zachowanie
                    pass
                except Exception as e:
                    if running:
                        logger.error(f"Błąd podczas akceptowania połączenia: {str(e)}")
                        time.sleep(1)  # Zapobiegamy zbyt częstym próbom w przypadku błędu
                
                # Krótka pauza, aby nie obciążać CPU
                time.sleep(0.1)
        except KeyboardInterrupt:
            logger.info("Zatrzymywanie serwera...")
            running = False
        finally:
            # Zamykamy wszystkie połączenia klientów
            for client in clients:
                try:
                    client.close()
                except:
                    pass
                    
            # Zamykamy socket serwera
            server_socket.close()
            logger.info("Serwer zatrzymany")
    except Exception as e:
        logger.error(f"Błąd podczas uruchamiania serwera: {str(e)}")

def check_mt5_process():
    """Sprawdza, czy process MetaTrader 5 jest uruchomiony."""
    import psutil
    
    for proc in psutil.process_iter(['pid', 'name']):
        try:
            if 'terminal64.exe' in proc.info['name'].lower() or 'metatrader5.exe' in proc.info['name'].lower():
                return True
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
            
    return False

def check_ea_installed():
    """Sprawdza, czy Expert Advisor jest zainstalowany."""
    # Szukamy w typowych lokalizacjach
    appdata_path = os.path.join(os.environ.get('APPDATA', ''), 'MetaQuotes', 'Terminal')
    
    if not os.path.exists(appdata_path):
        logger.error(f"Nie znaleziono katalogu danych MT5: {appdata_path}")
        return False
        
    # Szukamy w każdym katalogu terminala
    for terminal_id in os.listdir(appdata_path):
        ea_path = os.path.join(appdata_path, terminal_id, 'MQL5', 'Experts', 'AgentMT5', 'AgentMT5_EA.mq5')
        compiled_path = os.path.join(appdata_path, terminal_id, 'MQL5', 'Experts', 'AgentMT5', 'AgentMT5_EA.ex5')
        
        if os.path.exists(ea_path):
            logger.info(f"Znaleziono Expert Advisor w: {ea_path}")
            
            if os.path.exists(compiled_path):
                logger.info(f"Expert Advisor został skompilowany: {compiled_path}")
                mod_time = datetime.datetime.fromtimestamp(os.path.getmtime(compiled_path))
                logger.info(f"Data modyfikacji: {mod_time}")
                return True
            else:
                logger.warning(f"Expert Advisor NIE został skompilowany!")
                return False
                
    logger.error("Nie znaleziono Expert Advisora w żadnym z katalogów MT5")
    return False

def print_diagnostic_info():
    """Wyświetla informacje diagnostyczne."""
    logger.info("===== Informacje diagnostyczne =====")
    
    # Sprawdzamy, czy MetaTrader 5 jest uruchomiony
    mt5_running = check_mt5_process()
    logger.info(f"MetaTrader 5 uruchomiony: {mt5_running}")
    
    # Sprawdzamy, czy EA jest zainstalowany i skompilowany
    ea_installed = check_ea_installed()
    logger.info(f"Expert Advisor zainstalowany i skompilowany: {ea_installed}")
    
    # Sprawdzamy, czy port jest dostępny
    port_available = check_port_available('127.0.0.1', 5555)
    logger.info(f"Port 5555 jest dostępny: {port_available}")
    
    if not port_available:
        logger.info("Port 5555 jest zajęty - może to oznaczać, że serwer MT5 jest już uruchomiony")
    
    logger.info("====================================")

def main():
    """Główna funkcja skryptu."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Diagnostyka połączenia z MT5')
    parser.add_argument('--check', action='store_true', help='Sprawdź tylko informacje diagnostyczne')
    parser.add_argument('--wait', action='store_true', help='Czekaj na połączenie od EA')
    parser.add_argument('--host', type=str, default='127.0.0.1', help='Adres hosta (domyślnie: 127.0.0.1)')
    parser.add_argument('--port', type=int, default=5555, help='Port (domyślnie: 5555)')
    
    args = parser.parse_args()
    
    # Wyświetlamy informacje diagnostyczne
    print_diagnostic_info()
    
    if args.check:
        return 0
        
    if args.wait:
        # Czekamy na połączenie
        success = wait_for_connection(args.host, args.port)
        if success:
            logger.info("Połączenie nawiązane pomyślnie!")
        else:
            logger.error("Nie udało się nawiązać połączenia w wyznaczonym czasie")
    else:
        # Uruchamiamy serwer diagnostyczny
        start_simple_tcp_server(args.host, args.port)
        
    return 0

if __name__ == "__main__":
    try:
        # Próbujemy zaimportować psutil, jeśli nie jest zainstalowany, instalujemy go
        import psutil
    except ImportError:
        logger.info("Instalowanie pakietu psutil...")
        import subprocess
        subprocess.call([sys.executable, "-m", "pip", "install", "psutil"])
        
    sys.exit(main()) 