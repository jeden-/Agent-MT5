#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
AgentMT5 Interactive Tester

Ten skrypt pozwala na interaktywne testowanie różnych komponentów systemu AgentMT5.
Zapewnia prosty interfejs REPL (Read-Eval-Print Loop) do wykonywania poleceń i wizualizacji wyników.

Możliwe komendy:
- help - wyświetla dostępne komendy
- exit/quit - kończy działanie skryptu
- connect - testuje połączenie z MT5
- symbols - wyświetla dostępne symbole
- positions - wyświetla aktualne pozycje
- market [symbol] - wyświetla dane rynkowe dla symbolu
- test_mt5 - testuje podstawowe funkcje MT5
- run [script_name] - uruchamia wybrany skrypt testowy

Przykład użycia:
    python scripts/interactive_tester.py
"""

import os
import sys
import cmd
import json
import time
import logging
import traceback
import importlib
import subprocess
from datetime import datetime
from pathlib import Path

# Dodajemy katalog główny projektu do ścieżki, aby można było importować moduły
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Konfiguracja logowania
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("AgentMT5-Tester")

# Sprawdzenie środowiska wirtualnego
if not os.environ.get('VIRTUAL_ENV'):
    logger.warning("UWAGA: Nie wykryto aktywowanego środowiska wirtualnego. Zalecane jest uruchomienie w venv.")

class AgentMT5Tester(cmd.Cmd):
    """Interaktywny tester dla AgentMT5"""
    
    intro = """
    ╔═══════════════════════════════════════════════════╗
    ║           AgentMT5 Interactive Tester             ║
    ╠═══════════════════════════════════════════════════╣
    ║ Wpisz 'help' aby zobaczyć dostępne komendy        ║
    ║ Wpisz 'exit' lub 'quit' aby zakończyć             ║
    ╚═══════════════════════════════════════════════════╝
    """
    prompt = '(AgentMT5) > '
    
    def __init__(self):
        super().__init__()
        self.mt5_connector = None
        self.trading_service = None
        self.available_scripts = self._find_available_scripts()
        self._check_mt5_bridge()
    
    def _check_mt5_bridge(self):
        """Sprawdza dostępność modułu MT5Bridge"""
        try:
            from src.mt5_bridge.mt5_connector import MT5Connector
            logger.info("Moduł MT5Bridge jest dostępny.")
            self.mt5_bridge_available = True
        except ImportError as e:
            logger.warning(f"Moduł MT5Bridge nie jest dostępny: {str(e)}")
            self.mt5_bridge_available = False
    
    def _find_available_scripts(self):
        """Znajduje dostępne skrypty testowe w katalogu scripts"""
        scripts_dir = Path(__file__).parent
        script_files = [f.name for f in scripts_dir.glob("*.py") 
                        if f.is_file() and f.name.startswith(("test_", "performance_", "run_"))]
        return script_files
    
    def _import_module_safe(self, module_path):
        """Bezpieczny import modułu - zwraca None w przypadku błędu"""
        try:
            return importlib.import_module(module_path)
        except ImportError as e:
            logger.warning(f"Nie można zaimportować modułu {module_path}: {str(e)}")
            return None
    
    def do_list_scripts(self, arg):
        """Wyświetla dostępne skrypty testowe"""
        print("\nDostępne skrypty testowe:")
        print("=" * 50)
        for idx, script in enumerate(self.available_scripts, 1):
            print(f"{idx:2}. {script}")
    
    def do_run(self, arg):
        """Uruchamia wybrany skrypt testowy"""
        if not arg:
            self.do_list_scripts("")
            print("\nUżycie: run [nazwa_skryptu]")
            print("Przykład: run test_mt5_connection.py")
            return
            
        script_name = arg.strip()
        if not script_name.endswith(".py"):
            script_name += ".py"
            
        if script_name not in self.available_scripts:
            logger.warning(f"Skrypt {script_name} nie istnieje. Użyj komendy 'list_scripts' aby zobaczyć dostępne skrypty.")
            return
            
        logger.info(f"Uruchamianie skryptu {script_name}...")
        script_path = Path(__file__).parent / script_name
        
        try:
            # Uruchomienie skryptu jako podprocesu
            cmd = [sys.executable, str(script_path)]
            process = subprocess.Popen(
                cmd, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE,
                universal_newlines=True,
                bufsize=1
            )
            
            # Wyświetlanie wyjścia na bieżąco
            for line in iter(process.stdout.readline, ''):
                print(line, end='')
                
            # Czekanie na zakończenie procesu
            return_code = process.wait()
            
            if return_code != 0:
                error_output = process.stderr.read()
                logger.error(f"Skrypt zakończył się z błędem (kod: {return_code})")
                if error_output:
                    print("\nBłędy:")
                    print(error_output)
            else:
                logger.info(f"Skrypt {script_name} zakończył się poprawnie.")
                
        except Exception as e:
            logger.error(f"Błąd podczas uruchamiania skryptu: {str(e)}")
            traceback.print_exc()
    
    def do_connect(self, arg):
        """Nawiązuje połączenie z MT5"""
        if not self.mt5_bridge_available:
            logger.warning("Moduł MT5Bridge nie jest dostępny. Nie można nawiązać połączenia z MT5.")
            return False
            
        try:
            from src.mt5_bridge.mt5_connector import MT5Connector
            
            logger.info("Inicjalizacja MT5Connector...")
            self.mt5_connector = MT5Connector(connect=False)
            
            logger.info("Łączenie z MT5...")
            result = self.mt5_connector.connect()
            
            if result:
                account_info = self.mt5_connector.account_info()
                logger.info(f"Połączono z MT5 - Konto: {account_info['login']} ({account_info['server']})")
                logger.info(f"Saldo: {account_info['balance']} {account_info['currency']}")
                logger.info(f"Zysk/Strata: {account_info['profit']} {account_info['currency']}")
                
                # Inicjalizacja usług tradingowych
                try:
                    from src.mt5_bridge.trading_service import TradingService
                    self.trading_service = TradingService(self.mt5_connector)
                    logger.info("Usługa handlowa zainicjalizowana.")
                except ImportError:
                    logger.warning("Nie można zainicjalizować usługi handlowej - moduł nie jest dostępny.")
                
                return True
            else:
                logger.error("Nie udało się połączyć z MT5")
                return False
                
        except Exception as e:
            logger.error(f"Błąd podczas łączenia z MT5: {str(e)}")
            traceback.print_exc()
            return False
    
    def do_symbols(self, arg):
        """Wyświetla dostępne symbole"""
        if not self.mt5_connector or not self.mt5_connector.is_connected():
            logger.warning("Nie jesteś połączony z MT5. Użyj komendy 'connect'.")
            return
        
        try:
            logger.info("Pobieranie dostępnych symboli...")
            symbols = self.mt5_connector.symbols_get()
            
            print("\nDostępne symbole:")
            print("=" * 50)
            for idx, symbol in enumerate(symbols[:20], 1):  # Pokazujemy tylko 20 pierwszych symboli
                print(f"{idx:2}. {symbol['name']:10} | Digits: {symbol['digits']} | Trade Mode: {symbol['trade_mode']}")
            
            if len(symbols) > 20:
                print(f"\n...i {len(symbols) - 20} więcej.")
            
            logger.info(f"Pobrano {len(symbols)} symboli.")
            
        except Exception as e:
            logger.error(f"Błąd podczas pobierania symboli: {str(e)}")
            traceback.print_exc()
    
    def do_positions(self, arg):
        """Wyświetla aktualne pozycje"""
        if not self.mt5_connector or not self.mt5_connector.is_connected():
            logger.warning("Nie jesteś połączony z MT5. Użyj komendy 'connect'.")
            return
        
        try:
            logger.info("Pobieranie otwartych pozycji...")
            positions = self.mt5_connector.positions_get()
            
            if not positions:
                logger.info("Brak otwartych pozycji.")
                return
            
            print("\nOtwarte pozycje:")
            print("=" * 80)
            print(f"{'Ticket':10} | {'Symbol':10} | {'Type':6} | {'Volume':8} | {'Price':10} | {'SL':10} | {'TP':10} | {'Profit':10}")
            print("-" * 80)
            
            for pos in positions:
                pos_type = "BUY" if pos['type'] == 0 else "SELL"
                print(f"{pos['ticket']:10} | {pos['symbol']:10} | {pos_type:6} | {pos['volume']:8.2f} | "
                      f"{pos['price_open']:10.5f} | {pos['sl']:10.5f} | {pos['tp']:10.5f} | {pos['profit']:10.2f}")
            
            print("-" * 80)
            total_profit = sum(pos['profit'] for pos in positions)
            print(f"Całkowity zysk/strata: {total_profit:.2f}")
            
        except Exception as e:
            logger.error(f"Błąd podczas pobierania pozycji: {str(e)}")
            traceback.print_exc()
    
    def do_market(self, arg):
        """Wyświetla dane rynkowe dla symbolu"""
        if not arg:
            logger.warning("Podaj symbol, np. 'market EURUSD'")
            return
            
        if not self.mt5_connector or not self.mt5_connector.is_connected():
            logger.warning("Nie jesteś połączony z MT5. Użyj komendy 'connect'.")
            return
        
        try:
            symbol = arg.strip().upper()
            logger.info(f"Pobieranie danych rynkowych dla {symbol}...")
            
            # Pobieramy dane tick
            tick = self.mt5_connector.symbol_info_tick(symbol)
            if not tick:
                logger.error(f"Nie można pobrać danych dla symbolu {symbol}")
                return
                
            # Pobieramy informacje o symbolu
            symbol_info = self.mt5_connector.symbol_info(symbol)
            if not symbol_info:
                logger.error(f"Nie można pobrać informacji o symbolu {symbol}")
                return
            
            print(f"\nDane rynkowe dla {symbol}:")
            print("=" * 50)
            print(f"Bid: {tick['bid']:.5f}")
            print(f"Ask: {tick['ask']:.5f}")
            print(f"Spread: {(tick['ask'] - tick['bid']) / symbol_info['point']:.1f} punktów")
            print(f"Czas: {datetime.fromtimestamp(tick['time']).strftime('%Y-%m-%d %H:%M:%S')}")
            
            print("\nInformacje o symbolu:")
            print(f"Digits: {symbol_info['digits']}")
            print(f"Wielkość punktu: {symbol_info['point']:.6f}")
            print(f"Wielkość lota: {symbol_info['trade_contract_size']}")
            print(f"Min. wolumen: {symbol_info['volume_min']}")
            print(f"Max. wolumen: {symbol_info['volume_max']}")
            print(f"Krok wolumenu: {symbol_info['volume_step']}")
            
        except Exception as e:
            logger.error(f"Błąd podczas pobierania danych rynkowych: {str(e)}")
            traceback.print_exc()
    
    def do_test_mt5(self, arg):
        """Testuje podstawowe funkcje MT5"""
        if not self.mt5_connector or not self.mt5_connector.is_connected():
            logger.warning("Nie jesteś połączony z MT5. Użyj komendy 'connect'.")
            return
            
        logger.info("Test podstawowych funkcji MT5...")
        start_time = time.time()
        
        try:
            # Test pobierania informacji o koncie
            account_info = self.mt5_connector.account_info()
            print("\nInformacje o koncie:")
            print("=" * 50)
            print(f"Login: {account_info['login']}")
            print(f"Serwer: {account_info['server']}")
            print(f"Saldo: {account_info['balance']} {account_info['currency']}")
            print(f"Equity: {account_info['equity']} {account_info['currency']}")
            print(f"Margin: {account_info['margin']} {account_info['currency']}")
            print(f"Margin Free: {account_info['margin_free']} {account_info['currency']}")
            print(f"Margin Level: {account_info['margin_level']:.2f}%")
            
            # Test pobierania symboli
            symbols = self.mt5_connector.symbols_get()
            print(f"\nLiczba dostępnych symboli: {len(symbols)}")
            
            # Test pobierania pozycji
            positions = self.mt5_connector.positions_get()
            print(f"Liczba otwartych pozycji: {len(positions) if positions else 0}")
            
            # Test pobierania historii zamówień
            orders = self.mt5_connector.orders_get()
            print(f"Liczba aktywnych zleceń: {len(orders) if orders else 0}")
            
            elapsed_time = time.time() - start_time
            logger.info(f"Test podstawowych funkcji MT5 zakończony (czas: {elapsed_time:.2f}s)")
            
        except Exception as e:
            logger.error(f"Błąd podczas testowania MT5: {str(e)}")
            traceback.print_exc()
    
    def do_open_position(self, arg):
        """Otwiera pozycję testową (UWAGA: TO OPERACJA RZECZYWISTA!)
        Użycie: open_position SYMBOL TYPE VOLUME [SL] [TP]
        Przykład: open_position EURUSD BUY 0.01 1.05 1.07"""
        if not arg:
            print("Użycie: open_position SYMBOL TYPE VOLUME [SL] [TP]")
            print("Przykład: open_position EURUSD BUY 0.01 1.05 1.07")
            return
        
        if not self.trading_service:
            logger.warning("Usługa handlowa nie jest zainicjalizowana. Użyj komendy 'connect'.")
            return
        
        try:
            args = arg.strip().split()
            if len(args) < 3:
                print("Za mało argumentów. Użycie: open_position SYMBOL TYPE VOLUME [SL] [TP]")
                return
            
            symbol = args[0].upper()
            order_type = args[1].upper()
            volume = float(args[2])
            sl = float(args[3]) if len(args) > 3 else 0
            tp = float(args[4]) if len(args) > 4 else 0
            
            if order_type not in ["BUY", "SELL"]:
                print("Nieprawidłowy typ zlecenia. Użyj BUY lub SELL.")
                return
            
            # Potwierdzenie od użytkownika
            print("\n" + "!" * 50)
            print(f"UWAGA: Zamierzasz otworzyć rzeczywistą pozycję!")
            print(f"Symbol: {symbol}")
            print(f"Typ: {order_type}")
            print(f"Wolumen: {volume}")
            print(f"SL: {sl}")
            print(f"TP: {tp}")
            print("!" * 50)
            
            confirm = input("\nCzy na pewno chcesz kontynuować? (tak/nie): ")
            if confirm.lower() != "tak":
                print("Operacja anulowana.")
                return
            
            logger.info(f"Otwieranie pozycji {symbol} {order_type} {volume}...")
            
            if order_type == "BUY":
                result = self.trading_service.open_buy_position(symbol, volume, sl, tp)
            else:
                result = self.trading_service.open_sell_position(symbol, volume, sl, tp)
            
            if result.get('status') == 'success':
                logger.info(f"Pozycja została otwarta pomyślnie. Ticket: {result.get('ticket')}")
                print(f"\nPozycja otwarta pomyślnie:")
                print(f"Ticket: {result.get('ticket')}")
                print(f"Cena: {result.get('price')}")
            else:
                logger.error(f"Nie udało się otworzyć pozycji: {result.get('message')}")
                print(f"\nBłąd podczas otwierania pozycji:")
                print(f"Komunikat: {result.get('message')}")
            
        except Exception as e:
            logger.error(f"Błąd podczas otwierania pozycji: {str(e)}")
            traceback.print_exc()
    
    def do_close_position(self, arg):
        """Zamyka pozycję (UWAGA: TO OPERACJA RZECZYWISTA!)
        Użycie: close_position TICKET [VOLUME]
        Przykład: close_position 123456789 0.01"""
        if not arg:
            print("Użycie: close_position TICKET [VOLUME]")
            print("Przykład: close_position 123456789 0.01")
            return
        
        if not self.trading_service:
            logger.warning("Usługa handlowa nie jest zainicjalizowana. Użyj komendy 'connect'.")
            return
        
        try:
            args = arg.strip().split()
            if len(args) < 1:
                print("Za mało argumentów. Użycie: close_position TICKET [VOLUME]")
                return
            
            ticket = int(args[0])
            volume = float(args[1]) if len(args) > 1 else 0
            
            # Pobieranie informacji o pozycji
            positions = self.mt5_connector.positions_get()
            position = next((p for p in positions if p['ticket'] == ticket), None)
            
            if not position:
                logger.error(f"Nie znaleziono pozycji o numerze {ticket}")
                return
            
            if volume <= 0 or volume > position['volume']:
                volume = position['volume']
            
            # Potwierdzenie od użytkownika
            print("\n" + "!" * 50)
            print(f"UWAGA: Zamierzasz zamknąć rzeczywistą pozycję!")
            print(f"Ticket: {ticket}")
            print(f"Symbol: {position['symbol']}")
            print(f"Typ: {'BUY' if position['type'] == 0 else 'SELL'}")
            print(f"Wolumen do zamknięcia: {volume} z {position['volume']}")
            print(f"Zysk/strata: {position['profit']}")
            print("!" * 50)
            
            confirm = input("\nCzy na pewno chcesz kontynuować? (tak/nie): ")
            if confirm.lower() != "tak":
                print("Operacja anulowana.")
                return
            
            logger.info(f"Zamykanie pozycji {ticket}...")
            result = self.trading_service.close_position(ticket, volume)
            
            if result.get('status') == 'success':
                logger.info(f"Pozycja została zamknięta pomyślnie.")
                print(f"\nPozycja zamknięta pomyślnie.")
                print(f"Cena zamknięcia: {result.get('price')}")
                print(f"Zysk/strata: {result.get('profit')}")
            else:
                logger.error(f"Nie udało się zamknąć pozycji: {result.get('message')}")
                print(f"\nBłąd podczas zamykania pozycji:")
                print(f"Komunikat: {result.get('message')}")
            
        except Exception as e:
            logger.error(f"Błąd podczas zamykania pozycji: {str(e)}")
            traceback.print_exc()
    
    def do_modify_position(self, arg):
        """Modyfikuje pozycję (UWAGA: TO OPERACJA RZECZYWISTA!)
        Użycie: modify_position TICKET SL TP
        Przykład: modify_position 123456789 1.05 1.07"""
        if not arg:
            print("Użycie: modify_position TICKET SL TP")
            print("Przykład: modify_position 123456789 1.05 1.07")
            return
        
        if not self.trading_service:
            logger.warning("Usługa handlowa nie jest zainicjalizowana. Użyj komendy 'connect'.")
            return
        
        try:
            args = arg.strip().split()
            if len(args) < 3:
                print("Za mało argumentów. Użycie: modify_position TICKET SL TP")
                return
            
            ticket = int(args[0])
            sl = float(args[1])
            tp = float(args[2])
            
            # Pobieranie informacji o pozycji
            positions = self.mt5_connector.positions_get()
            position = next((p for p in positions if p['ticket'] == ticket), None)
            
            if not position:
                logger.error(f"Nie znaleziono pozycji o numerze {ticket}")
                return
            
            # Potwierdzenie od użytkownika
            print("\n" + "!" * 50)
            print(f"UWAGA: Zamierzasz zmodyfikować rzeczywistą pozycję!")
            print(f"Ticket: {ticket}")
            print(f"Symbol: {position['symbol']}")
            print(f"Typ: {'BUY' if position['type'] == 0 else 'SELL'}")
            print(f"Aktualny SL: {position['sl']} -> Nowy SL: {sl}")
            print(f"Aktualny TP: {position['tp']} -> Nowy TP: {tp}")
            print("!" * 50)
            
            confirm = input("\nCzy na pewno chcesz kontynuować? (tak/nie): ")
            if confirm.lower() != "tak":
                print("Operacja anulowana.")
                return
            
            logger.info(f"Modyfikowanie pozycji {ticket}...")
            result = self.trading_service.modify_position(ticket, sl, tp)
            
            if result.get('status') == 'success':
                logger.info(f"Pozycja została zmodyfikowana pomyślnie.")
                print(f"\nPozycja zmodyfikowana pomyślnie.")
            else:
                logger.error(f"Nie udało się zmodyfikować pozycji: {result.get('message')}")
                print(f"\nBłąd podczas modyfikowania pozycji:")
                print(f"Komunikat: {result.get('message')}")
            
        except Exception as e:
            logger.error(f"Błąd podczas modyfikowania pozycji: {str(e)}")
            traceback.print_exc()
    
    def do_account(self, arg):
        """Wyświetla szczegółowe informacje o koncie"""
        if not self.mt5_connector or not self.mt5_connector.is_connected():
            logger.warning("Nie jesteś połączony z MT5. Użyj komendy 'connect'.")
            return
        
        try:
            account_info = self.mt5_connector.account_info()
            
            print("\nSzczegółowe informacje o koncie:")
            print("=" * 50)
            for key, value in account_info.items():
                print(f"{key:20} : {value}")
            
        except Exception as e:
            logger.error(f"Błąd podczas pobierania informacji o koncie: {str(e)}")
            traceback.print_exc()
    
    def do_history(self, arg):
        """Wyświetla historię zamkniętych pozycji
        Użycie: history [days=7]
        Przykład: history 30"""
        if not self.mt5_connector or not self.mt5_connector.is_connected():
            logger.warning("Nie jesteś połączony z MT5. Użyj komendy 'connect'.")
            return
        
        days = 7
        if arg:
            try:
                days = int(arg.strip())
            except ValueError:
                logger.warning(f"Nieprawidłowa liczba dni: {arg}. Używam domyślnej wartości {days} dni.")
        
        try:
            from datetime import datetime, timedelta
            
            # Obliczanie zakresu dat
            date_to = datetime.now()
            date_from = date_to - timedelta(days=days)
            
            logger.info(f"Pobieranie historii zamkniętych pozycji z ostatnich {days} dni...")
            
            # Pobieranie historii
            history = self.mt5_connector.history_deals_get(date_from, date_to)
            
            if not history:
                logger.info("Brak historii transakcji w podanym okresie.")
                return
            
            # Filtrowanie tylko zamkniętych pozycji
            closed_positions = [deal for deal in history if deal['type'] == 1]  # typ 1 to zamknięcie pozycji
            
            if not closed_positions:
                logger.info("Brak zamkniętych pozycji w podanym okresie.")
                return
            
            print("\nHistoria zamkniętych pozycji:")
            print("=" * 100)
            print(f"{'Time':20} | {'Ticket':10} | {'Symbol':10} | {'Type':6} | {'Volume':8} | {'Price':10} | {'Profit':10}")
            print("-" * 100)
            
            for deal in closed_positions:
                deal_time = datetime.fromtimestamp(deal['time']).strftime('%Y-%m-%d %H:%M:%S')
                deal_type = "BUY" if deal['entry'] == 0 else "SELL"
                print(f"{deal_time:20} | {deal['position_id']:10} | {deal['symbol']:10} | {deal_type:6} | "
                      f"{deal['volume']:8.2f} | {deal['price']:10.5f} | {deal['profit']:10.2f}")
            
            print("-" * 100)
            total_profit = sum(deal['profit'] for deal in closed_positions)
            print(f"Całkowity zysk/strata: {total_profit:.2f}")
            
        except Exception as e:
            logger.error(f"Błąd podczas pobierania historii: {str(e)}")
            traceback.print_exc()
    
    def do_exit(self, arg):
        """Kończy działanie programu"""
        logger.info("Kończenie działania programu...")
        
        # Sprzątanie
        if self.mt5_connector and self.mt5_connector.is_connected():
            self.mt5_connector.shutdown()
            logger.info("Zamknięto połączenie z MT5")
        
        print("\nDo widzenia!")
        return True
        
    do_quit = do_exit  # alias
    
    def default(self, line):
        """Obsługa nieznanych poleceń"""
        logger.warning(f"Nieznane polecenie: '{line}'")
        print("Wpisz 'help' aby zobaczyć dostępne komendy.")

def main():
    """Funkcja główna"""
    try:
        # Uruchom interaktywny tester
        tester = AgentMT5Tester()
        tester.cmdloop()
        
    except KeyboardInterrupt:
        print("\nProgram przerwany przez użytkownika.")
    except Exception as e:
        logger.error(f"Błąd podczas działania programu: {str(e)}")
        traceback.print_exc()

if __name__ == "__main__":
    main() 