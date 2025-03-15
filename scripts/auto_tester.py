#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
AgentMT5 Automatic Tester

Ten skrypt automatycznie testuje różne funkcje systemu AgentMT5 i generuje raport z testów.
Pozwala na wykrywanie i raportowanie błędów w systemie.

Przykład użycia:
    python scripts/auto_tester.py
"""

import os
import sys
import time
import logging
import traceback
from pathlib import Path
from datetime import datetime

# Dodajemy katalog główny projektu do ścieżki, aby można było importować moduły
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Konfiguracja logowania
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("auto_tester_log.txt", mode="w")
    ]
)
logger = logging.getLogger("AgentMT5-AutoTester")

class TestResult:
    """Klasa przechowująca wynik pojedynczego testu"""
    def __init__(self, name, status=False, error=None, details=None):
        self.name = name
        self.status = status  # True = sukces, False = błąd
        self.error = error
        self.details = details or {}
        self.timestamp = datetime.now()
    
    def __str__(self):
        status_str = "SUKCES" if self.status else "BŁĄD"
        result = f"Test: {self.name} - Status: {status_str} - Czas: {self.timestamp.strftime('%H:%M:%S')}"
        if self.error:
            result += f"\nBłąd: {self.error}"
        if self.details:
            result += "\nSzczegóły:"
            for key, value in self.details.items():
                result += f"\n  {key}: {value}"
        return result

class AgentMT5AutoTester:
    """Automatyczny tester dla AgentMT5"""
    
    def __init__(self):
        self.results = []
        self.mt5_connector = None
        self.trading_service = None
        self.is_connected = False
        
        # Sprawdź, czy jesteśmy w środowisku wirtualnym
        if not os.environ.get('VIRTUAL_ENV'):
            logger.warning("UWAGA: Nie wykryto aktywowanego środowiska wirtualnego. Zalecane jest uruchomienie w venv.")
            print("UWAGA: Nie wykryto aktywowanego środowiska wirtualnego!")
            print("Zaleca się uruchomienie skryptu w aktywowanym środowisku wirtualnym.")
            print("Użyj: .\\venv\\Scripts\\Activate.ps1 w systemie Windows")
            print("lub: source venv/bin/activate w systemie Linux/Mac")
            response = input("Czy chcesz kontynuować mimo to? (tak/nie): ")
            if response.lower() != 'tak':
                logger.info("Przerwano działanie skryptu ze względu na brak aktywowanego środowiska.")
                sys.exit(0)
    
    def initialize_components(self):
        """Inicjalizuje komponenty systemu"""
        try:
            logger.info("Inicjalizacja komponentów...")
            
            # Importujemy komponenty
            try:
                from src.mt5_bridge.mt5_connector import MT5Connector
                logger.info("Moduł MT5Connector zaimportowany pomyślnie.")
                
                # Inicjalizujemy konektor MT5 (bez parametrów - zgodnie z implementacją)
                self.mt5_connector = MT5Connector()
                logger.info("MT5Connector zainicjalizowany pomyślnie.")
                
                return TestResult("initialize_components", True, details={"components": ["MT5Connector"]})
            except ImportError as e:
                logger.error(f"Nie można zaimportować modułu MT5Connector: {str(e)}")
                return TestResult("initialize_components", False, f"Import Error: {str(e)}")
            except Exception as e:
                logger.error(f"Błąd podczas inicjalizacji MT5Connector: {str(e)}")
                return TestResult("initialize_components", False, f"Init Error: {str(e)}")
            
        except Exception as e:
            logger.error(f"Błąd podczas inicjalizacji komponentów: {str(e)}")
            traceback.print_exc()
            return TestResult("initialize_components", False, f"Exception: {str(e)}")
    
    def connect_to_mt5(self):
        """Nawiązuje połączenie z MT5"""
        if not self.mt5_connector:
            logger.error("MT5Connector nie jest zainicjalizowany.")
            return TestResult("connect_to_mt5", False, "MT5Connector nie jest zainicjalizowany.")
        
        try:
            logger.info("Łączenie z MT5...")
            result = self.mt5_connector.connect()
            
            if result:
                account_info = self.mt5_connector.get_account_info()
                if not account_info:
                    logger.error("Nie udało się pobrać informacji o koncie.")
                    return TestResult("connect_to_mt5", False, "Nie udało się pobrać informacji o koncie.")
                
                login = account_info.get('login', 'N/A')
                balance = account_info.get('balance', 0)
                currency = account_info.get('currency', 'USD')
                profit = account_info.get('profit', 0)
                
                logger.info(f"Połączono z MT5 - Konto: {login}")
                logger.info(f"Saldo: {balance} {currency}")
                logger.info(f"Equity: {account_info.get('equity', 0)} {currency}")
                
                self.is_connected = True
                
                try:
                    from src.mt5_bridge.trading_service import TradingService
                    self.trading_service = TradingService(self.mt5_connector)
                    logger.info("Usługa handlowa zainicjalizowana.")
                    
                    return TestResult("connect_to_mt5", True, details={
                        "login": login,
                        "balance": balance,
                        "currency": currency,
                        "margin": account_info.get('margin', 0),
                        "margin_free": account_info.get('margin_free', 0),
                        "components": ["MT5Connector", "TradingService"]
                    })
                except ImportError as e:
                    logger.warning(f"Nie można zainicjalizować usługi handlowej: {str(e)}")
                    return TestResult("connect_to_mt5", True, details={
                        "login": login,
                        "balance": balance,
                        "currency": currency,
                        "components": ["MT5Connector"],
                        "warning": f"Nie można zainicjalizować TradingService: {str(e)}"
                    })
            else:
                logger.error("Nie udało się połączyć z MT5")
                return TestResult("connect_to_mt5", False, "Nie udało się połączyć z MT5")
                
        except Exception as e:
            logger.error(f"Błąd podczas łączenia z MT5: {str(e)}")
            traceback.print_exc()
            return TestResult("connect_to_mt5", False, f"Exception: {str(e)}")
    
    def test_get_symbols(self):
        """Testuje pobieranie informacji o symbolu"""
        if not self.is_connected:
            logger.warning("Nie jesteś połączony z MT5.")
            return TestResult("test_get_symbols", False, "Nie jesteś połączony z MT5.")
        
        try:
            symbol = "EURUSD"  # Testujemy na jednym symbolu
            logger.info(f"Pobieranie informacji o symbolu {symbol}...")
            start_time = time.time()
            symbol_info = self.mt5_connector.get_symbol_info(symbol)
            elapsed_time = time.time() - start_time
            
            if symbol_info:
                logger.info(f"Pobrano informacje o symbolu {symbol} w czasie {elapsed_time:.2f}s.")
                logger.info(f"Bid: {symbol_info.get('bid', 0):.5f}, Ask: {symbol_info.get('ask', 0):.5f}")
                
                return TestResult("test_get_symbols", True, details={
                    "symbol": symbol,
                    "bid": symbol_info.get('bid', 0),
                    "ask": symbol_info.get('ask', 0),
                    "point": symbol_info.get('point', 0),
                    "digits": symbol_info.get('digits', 0),
                    "volume_min": symbol_info.get('volume_min', 0),
                    "volume_max": symbol_info.get('volume_max', 0),
                    "time": elapsed_time
                })
            else:
                logger.error(f"Nie udało się pobrać informacji o symbolu {symbol}.")
                return TestResult("test_get_symbols", False, f"Nie udało się pobrać informacji o symbolu {symbol}.")
            
        except Exception as e:
            logger.error(f"Błąd podczas pobierania informacji o symbolu: {str(e)}")
            traceback.print_exc()
            return TestResult("test_get_symbols", False, f"Exception: {str(e)}")
    
    def test_get_positions(self):
        """Testuje pobieranie otwartych pozycji"""
        if not self.is_connected:
            logger.warning("Nie jesteś połączony z MT5.")
            return TestResult("test_get_positions", False, "Nie jesteś połączony z MT5.")
        
        try:
            logger.info("Pobieranie otwartych pozycji...")
            start_time = time.time()
            positions = self.mt5_connector.positions_get()
            elapsed_time = time.time() - start_time
            
            positions_list = []
            total_profit = 0
            
            if positions:
                for pos in positions:
                    pos_type = "BUY" if pos.get('type', 0) == 0 else "SELL"
                    positions_list.append({
                        "ticket": pos.get('ticket', 0),
                        "symbol": pos.get('symbol', 'N/A'),
                        "type": pos_type,
                        "volume": pos.get('volume', 0),
                        "profit": pos.get('profit', 0)
                    })
                    total_profit += pos.get('profit', 0)
                
                logger.info(f"Pobrano {len(positions)} pozycji w czasie {elapsed_time:.2f}s.")
                logger.info(f"Całkowity zysk/strata: {total_profit:.2f}")
                
                return TestResult("test_get_positions", True, details={
                    "count": len(positions),
                    "positions": positions_list,
                    "total_profit": total_profit,
                    "time": elapsed_time
                })
            else:
                logger.info("Brak otwartych pozycji.")
                return TestResult("test_get_positions", True, details={
                    "count": 0,
                    "time": elapsed_time
                })
            
        except Exception as e:
            logger.error(f"Błąd podczas pobierania pozycji: {str(e)}")
            traceback.print_exc()
            return TestResult("test_get_positions", False, f"Exception: {str(e)}")
    
    def test_market_data(self, symbol="EURUSD"):
        """Testuje pobieranie danych rynkowych"""
        if not self.is_connected:
            logger.warning("Nie jesteś połączony z MT5.")
            return TestResult("test_market_data", False, "Nie jesteś połączony z MT5.")
        
        try:
            logger.info(f"Pobieranie danych rynkowych dla {symbol}...")
            start_time = time.time()
            
            # Pobieramy informacje o symbolu
            symbol_info = self.mt5_connector.get_symbol_info(symbol)
            if not symbol_info:
                logger.error(f"Nie można pobrać informacji o symbolu {symbol}")
                return TestResult("test_market_data", False, f"Nie można pobrać informacji o symbolu {symbol}")
            
            elapsed_time = time.time() - start_time
            
            bid = symbol_info.get('bid', 0)
            ask = symbol_info.get('ask', 0)
            
            logger.info(f"Pobrano dane rynkowe dla {symbol} w czasie {elapsed_time:.2f}s.")
            logger.info(f"Bid: {bid:.5f}, Ask: {ask:.5f}")
            
            return TestResult("test_market_data", True, details={
                "symbol": symbol,
                "bid": bid,
                "ask": ask,
                "time": elapsed_time,
                "point": symbol_info.get('point', 0),
                "digits": symbol_info.get('digits', 0),
                "trade_contract_size": symbol_info.get('trade_contract_size', 0),
                "volume_min": symbol_info.get('volume_min', 0),
                "volume_max": symbol_info.get('volume_max', 0)
            })
            
        except Exception as e:
            logger.error(f"Błąd podczas pobierania danych rynkowych: {str(e)}")
            traceback.print_exc()
            return TestResult("test_market_data", False, f"Exception: {str(e)}")
    
    def test_account_info(self):
        """Testuje pobieranie informacji o koncie"""
        if not self.is_connected:
            logger.warning("Nie jesteś połączony z MT5.")
            return TestResult("test_account_info", False, "Nie jesteś połączony z MT5.")
        
        try:
            logger.info("Pobieranie informacji o koncie...")
            start_time = time.time()
            account_info = self.mt5_connector.get_account_info()
            elapsed_time = time.time() - start_time
            
            if account_info:
                login = account_info.get('login', 'N/A')
                balance = account_info.get('balance', 0)
                equity = account_info.get('equity', 0)
                currency = account_info.get('currency', 'USD')
                
                logger.info(f"Pobrano informacje o koncie w czasie {elapsed_time:.2f}s.")
                logger.info(f"Login: {login}")
                logger.info(f"Saldo: {balance} {currency}")
                logger.info(f"Equity: {equity} {currency}")
                
                return TestResult("test_account_info", True, details={
                    "login": login,
                    "currency": currency,
                    "balance": balance,
                    "equity": equity,
                    "margin": account_info.get('margin', 0),
                    "margin_free": account_info.get('margin_free', 0),
                    "margin_level": account_info.get('margin_level', 0),
                    "time": elapsed_time
                })
            else:
                logger.error("Nie udało się pobrać informacji o koncie.")
                return TestResult("test_account_info", False, "Nie udało się pobrać informacji o koncie.")
            
        except Exception as e:
            logger.error(f"Błąd podczas pobierania informacji o koncie: {str(e)}")
            traceback.print_exc()
            return TestResult("test_account_info", False, f"Exception: {str(e)}")
    
    def test_orders(self):
        """Testuje pobieranie aktywnych zleceń oczekujących"""
        if not self.is_connected:
            logger.warning("Nie jesteś połączony z MT5.")
            return TestResult("test_orders", False, "Nie jesteś połączony z MT5.")
        
        try:
            logger.info("Pobieranie aktywnych zleceń oczekujących...")
            start_time = time.time()
            orders = self.mt5_connector.get_orders()
            elapsed_time = time.time() - start_time
            
            orders_list = []
            
            if orders:
                for order in orders:
                    order_type = order.get('type', 0)
                    type_str = "BUY" if order_type == 0 else "SELL" if order_type == 1 else f"TYPE_{order_type}"
                    
                    orders_list.append({
                        "ticket": order.get('ticket', 0),
                        "symbol": order.get('symbol', 'N/A'),
                        "type": type_str,
                        "volume": order.get('volume_current', 0),
                        "price_open": order.get('price_open', 0),
                        "sl": order.get('sl', 0),
                        "tp": order.get('tp', 0)
                    })
                
                logger.info(f"Pobrano {len(orders)} zleceń oczekujących w czasie {elapsed_time:.2f}s.")
                
                return TestResult("test_orders", True, details={
                    "count": len(orders),
                    "orders": orders_list,
                    "time": elapsed_time
                })
            else:
                logger.info("Brak aktywnych zleceń oczekujących.")
                return TestResult("test_orders", True, details={
                    "count": 0,
                    "time": elapsed_time
                })
            
        except Exception as e:
            logger.error(f"Błąd podczas pobierania zleceń oczekujących: {str(e)}")
            traceback.print_exc()
            return TestResult("test_orders", False, f"Exception: {str(e)}")
    
    def test_history_deals(self, days=7):
        """Testuje pobieranie historii transakcji"""
        if not self.is_connected:
            logger.warning("Nie jesteś połączony z MT5.")
            return TestResult("test_history_deals", False, "Nie jesteś połączony z MT5.")
        
        try:
            from datetime import datetime, timedelta
            
            # Obliczanie zakresu dat
            date_to = datetime.now()
            date_from = date_to - timedelta(days=days)
            
            logger.info(f"Pobieranie historii transakcji z ostatnich {days} dni...")
            
            # Sprawdzamy, czy metoda history_deals_get istnieje
            if not hasattr(self.mt5_connector, 'history_deals_get'):
                logger.warning("Metoda history_deals_get nie jest dostępna w MT5Connector.")
                return TestResult("test_history_deals", False, "Metoda history_deals_get nie jest dostępna w MT5Connector.")
            
            start_time = time.time()
            history = self.mt5_connector.history_deals_get(date_from, date_to)
            elapsed_time = time.time() - start_time
            
            if history:
                # Filtrowanie tylko zamkniętych pozycji
                closed_positions = [deal for deal in history if deal['type'] == 1]  # typ 1 to zamknięcie pozycji
                
                deals_list = []
                total_profit = 0
                
                for deal in closed_positions:
                    deal_time = datetime.fromtimestamp(deal['time']).strftime('%Y-%m-%d %H:%M:%S')
                    deal_type = "BUY" if deal['entry'] == 0 else "SELL"
                    deals_list.append({
                        "time": deal_time,
                        "position_id": deal['position_id'],
                        "symbol": deal['symbol'],
                        "type": deal_type,
                        "volume": deal['volume'],
                        "price": deal['price'],
                        "profit": deal['profit']
                    })
                    total_profit += deal['profit']
                
                logger.info(f"Pobrano {len(history)} transakcji, z czego {len(closed_positions)} to zamknięte pozycje.")
                logger.info(f"Całkowity zysk/strata z zamkniętych pozycji: {total_profit:.2f}")
                
                return TestResult("test_history_deals", True, details={
                    "total_deals": len(history),
                    "closed_positions": len(closed_positions),
                    "deals": deals_list[:10],  # Pokazujemy tylko 10 pierwszych transakcji
                    "total_profit": total_profit,
                    "time": elapsed_time
                })
            else:
                logger.info("Brak historii transakcji w podanym okresie.")
                return TestResult("test_history_deals", True, details={
                    "count": 0,
                    "time": elapsed_time
                })
            
        except Exception as e:
            logger.error(f"Błąd podczas pobierania historii transakcji: {str(e)}")
            traceback.print_exc()
            return TestResult("test_history_deals", False, f"Exception: {str(e)}")
    
    def shutdown(self):
        """Kończy działanie testera"""
        if self.is_connected and self.mt5_connector:
            logger.info("Zamykanie połączenia z MT5...")
            self.mt5_connector.disconnect()
            logger.info("Połączenie z MT5 zostało zamknięte.")
    
    def generate_report(self):
        """Generuje raport z testów"""
        logger.info("Generowanie raportu z testów...")
        
        success_count = sum(1 for r in self.results if r.status)
        fail_count = sum(1 for r in self.results if not r.status)
        
        report = f"""
=============================================
     AgentMT5 Automatic Tester Report
=============================================
Data: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Liczba testów: {len(self.results)}
Sukces: {success_count}
Błędy: {fail_count}
Procent sukcesu: {100 * success_count / len(self.results) if self.results else 0:.1f}%
=============================================
Szczegóły testów:
"""
        
        for i, result in enumerate(self.results, 1):
            status_str = "✅ SUKCES" if result.status else "❌ BŁĄD"
            report += f"\n{i}. {result.name} - {status_str} - {result.timestamp.strftime('%H:%M:%S')}"
            if not result.status and result.error:
                report += f"\n   Błąd: {result.error}"
        
        report += "\n\n=============================================\n"
        
        # Zapisz raport do pliku
        with open("auto_tester_report.txt", "w", encoding="utf-8") as f:
            f.write(report)
        
        logger.info(f"Raport został zapisany do pliku auto_tester_report.txt")
        
        return report
    
    def run_all_tests(self):
        """Uruchamia wszystkie testy"""
        logger.info("=== Rozpoczynam automatyczne testy AgentMT5 ===")
        
        # Inicjalizacja komponentów
        result = self.initialize_components()
        self.results.append(result)
        
        if not result.status:
            logger.error("Nie udało się zainicjalizować komponentów. Kończę testy.")
            return False
        
        # Połączenie z MT5
        result = self.connect_to_mt5()
        self.results.append(result)
        
        if not result.status:
            logger.error("Nie udało się połączyć z MT5. Kończę testy.")
            return False
        
        # Testowanie podstawowych funkcji
        self.results.append(self.test_account_info())
        self.results.append(self.test_get_symbols())
        self.results.append(self.test_get_positions())
        self.results.append(self.test_orders())
        self.results.append(self.test_market_data("EURUSD"))
        self.results.append(self.test_market_data("GBPUSD"))
        
        # Pomijamy test historii, ponieważ może nie być dostępny
        # self.results.append(self.test_history_deals())
        
        # Generowanie raportu
        report = self.generate_report()
        print(report)
        
        # Zamknięcie połączenia
        self.shutdown()
        
        return True

def main():
    """Funkcja główna"""
    print("\n" + "=" * 60)
    print("     AgentMT5 Automatic Tester")
    print("=" * 60)
    
    # Sprawdź, czy środowisko wirtualne jest aktywne
    if not os.environ.get('VIRTUAL_ENV'):
        print("\nUWAGA: Nie wykryto aktywowanego środowiska wirtualnego!")
        print("Zaleca się uruchomienie skryptu w aktywowanym środowisku wirtualnym.")
        print("Użyj: .\\venv\\Scripts\\Activate.ps1 w systemie Windows")
        print("lub: source venv/bin/activate w systemie Linux/Mac")
        response = input("Czy chcesz kontynuować mimo to? (tak/nie): ")
        if response.lower() != 'tak':
            print("Przerwano działanie skryptu.")
            return
    
    try:
        tester = AgentMT5AutoTester()
        tester.run_all_tests()
        
    except KeyboardInterrupt:
        logger.info("Program przerwany przez użytkownika.")
        print("\nProgram przerwany przez użytkownika.")
    except Exception as e:
        logger.error(f"Błąd podczas działania programu: {str(e)}")
        traceback.print_exc()
        print(f"\nBłąd podczas działania programu: {str(e)}")

if __name__ == "__main__":
    main() 