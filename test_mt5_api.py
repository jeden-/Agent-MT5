import requests
import json
import time

class MT5APITester:
    def __init__(self, server_url="http://127.0.0.1:5555"):
        self.server_url = server_url
        print(f"Inicjalizacja testera MT5API z URL: {server_url}")
    
    def check_connection(self):
        """Sprawdza połączenie z serwerem MT5"""
        try:
            response = requests.get(f"{self.server_url}/commands?ea_id=TEST_API")
            if response.status_code == 200:
                print("Połączenie z serwerem MT5 działa poprawnie")
                print(f"Odpowiedź: {response.json()}")
                return True
            else:
                print(f"Błąd połączenia: status {response.status_code}")
                print(f"Treść odpowiedzi: {response.text}")
                return False
        except Exception as e:
            print(f"Wyjątek podczas sprawdzania połączenia: {str(e)}")
            return False
            
    def get_positions(self):
        """Pobiera otwarte pozycje z serwera MT5"""
        try:
            response = requests.get(f"{self.server_url}/positions")
            if response.status_code == 200:
                positions = response.json()
                print(f"Pobrano {len(positions)} pozycji")
                for pos in positions:
                    print(f"  Symbol: {pos['symbol']}, Typ: {pos['type']}, Wolumen: {pos['volume']}, Zysk: {pos['profit']}")
                return positions
            else:
                print(f"Błąd podczas pobierania pozycji: status {response.status_code}")
                print(f"Treść odpowiedzi: {response.text}")
                return []
        except Exception as e:
            print(f"Wyjątek podczas pobierania pozycji: {str(e)}")
            return []
            
    def execute_trade(self, action="trade", trade_type="buy", symbol="EURUSD.pro", volume=0.01):
        """Wykonuje zlecenie na serwerze MT5"""
        try:
            url = f"{self.server_url}/commands?action={action}&type={trade_type}&symbol={symbol}&volume={volume}"
            print(f"Wysyłanie żądania: {url}")
            
            response = requests.get(url)
            if response.status_code == 200:
                result = response.json()
                print(f"Zlecenie wykonane pomyślnie: {result}")
                return result
            else:
                print(f"Błąd podczas wykonywania zlecenia: status {response.status_code}")
                print(f"Treść odpowiedzi: {response.text}")
                return None
        except Exception as e:
            print(f"Wyjątek podczas wykonywania zlecenia: {str(e)}")
            return None
            
if __name__ == "__main__":
    tester = MT5APITester()
    print("==== Test połączenia z serwerem MT5 ====")
    if tester.check_connection():
        print("\n==== Pobieranie otwartych pozycji ====")
        tester.get_positions()
        
        print("\n==== Test wykonania zlecenia kupna ====")
        response = input("Czy chcesz wykonać test zlecenia handlowego? (tak/nie): ")
        if response.lower() == "tak":
            tester.execute_trade(action="trade", trade_type="buy", symbol="EURUSD.pro", volume=0.01)
        else:
            print("Pomijam test zlecenia handlowego")
    else:
        print("Test nieudany - brak połączenia z serwerem MT5") 