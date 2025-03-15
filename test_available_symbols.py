import os
import sys
import logging
import pandas as pd
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from dotenv import load_dotenv

# Ładowanie zmiennych środowiskowych z pliku .env
load_dotenv()

# Dodanie katalogu głównego projektu do ścieżki
script_dir = os.path.dirname(os.path.abspath(__file__))
project_dir = os.path.dirname(script_dir) if os.path.basename(script_dir) == 'scripts' else script_dir
if project_dir not in sys.path:
    sys.path.append(project_dir)

# Konfiguracja logowania
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

try:
    import MetaTrader5 as mt5
except ImportError:
    logger.error("Biblioteka MetaTrader5 nie jest zainstalowana. Zainstaluj ją używając: pip install MetaTrader5")
    sys.exit(1)

def init_mt5() -> bool:
    """
    Inicjalizacja połączenia z platformą MT5.
    
    Returns:
        bool: True jeśli połączenie zostało nawiązane, False w przeciwnym wypadku.
    """
    if not mt5.initialize():
        logger.error(f"Inicjalizacja MT5 nie powiodła się: {mt5.last_error()}")
        return False
    
    # Dane logowania z pliku .env
    account = int(os.getenv("MT5_LOGIN", "62499981"))  # ID konta demo
    password = os.getenv("MT5_PASSWORD", "mVBu5x!3")  # Hasło
    server = os.getenv("MT5_SERVER", "OANDATMS-MT5")  # Serwer
    
    logger.info(f"Próba logowania do MT5 na konto {account} na serwerze {server}")
    
    if not mt5.login(account, password, server):
        logger.error(f"Logowanie do MT5 nie powiodło się: {mt5.last_error()}")
        mt5.shutdown()
        return False
    
    logger.info(f"Połączono z MT5 na koncie {account}")
    return True

def get_available_symbols() -> List[Dict[str, Any]]:
    """
    Pobiera listę dostępnych symboli/instrumentów.
    
    Returns:
        List[Dict[str, Any]]: Lista słowników z informacjami o symbolach.
    """
    # Pobierz wszystkie symbole
    symbols = mt5.symbols_get()
    if symbols is None:
        logger.error(f"Nie udało się pobrać symboli: {mt5.last_error()}")
        return []
    
    # Przetwarzanie symboli
    symbol_info = []
    for sym in symbols:
        # Pobierz podstawowe informacje
        info = {
            "symbol": sym.name,
            "description": sym.description,
            "path": sym.path,
            "currency_base": sym.currency_base,
            "currency_profit": sym.currency_profit,
            "trade_calc_mode": sym.trade_calc_mode,
            "filling_mode": sym.filling_mode,
            "visible": sym.visible,
            "select": sym.select,
            "margin_hedged_use_leg": sym.margin_hedged_use_leg,
            "expiration_mode": sym.expiration_mode
        }
        symbol_info.append(info)
    
    return symbol_info

def main():
    """
    Funkcja główna programu.
    """
    logger.info("Sprawdzanie dostępnych symboli/instrumentów na koncie demo MT5")
    
    # Inicjalizacja MT5
    if not init_mt5():
        return
    
    try:
        # Pobierz dostępne symbole
        symbols = get_available_symbols()
        logger.info(f"Pobrano {len(symbols)} symboli")
        
        # Wypisanie listy symboli z interesującymi nas polami
        pd.set_option('display.max_rows', None)
        pd.set_option('display.max_columns', None)
        pd.set_option('display.width', 1000)
        
        # Utworzenie DataFrame z symboli
        df = pd.DataFrame(symbols)
        
        # Wypisanie podsumowania
        print("\n===== PODSUMOWANIE DOSTĘPNYCH SYMBOLI =====")
        print(f"Liczba wszystkich symboli: {len(df)}")
        
        # Wypisanie najczęstszych trybów wypełniania
        print("\n===== TRYBY WYPEŁNIANIA =====")
        filling_modes = df['filling_mode'].value_counts()
        for mode, count in filling_modes.items():
            mode_desc = []
            if mode & mt5.ORDER_FILLING_FOK:
                mode_desc.append("FOK")
            if mode & mt5.ORDER_FILLING_IOC:
                mode_desc.append("IOC")
            if mode & mt5.ORDER_FILLING_RETURN:
                mode_desc.append("RETURN")
            if not mode_desc:
                mode_desc = ["NONE"]
            print(f"Tryb {mode} ({', '.join(mode_desc)}): {count} symboli")
            
        # Wypisanie wszystkich symboli
        print("\n===== SZCZEGÓŁY WYBRANYCH SYMBOLI =====")
        # Zaktualizowana lista szukanych symboli
        search_symbols = ['EURUSD.pro', 'GBPUSD.pro', 'GOLD.pro', 'US100.pro', 'SILVER.pro']
        
        for symbol in search_symbols:
            # Dokładne dopasowanie
            exact_match = df[df['symbol'] == symbol]
            
            if not exact_match.empty:
                print(f"\n--- Symbol '{symbol}' ---")
                # Wybierz interesujące nas kolumny
                selected_cols = ['symbol', 'description', 'currency_base', 'currency_profit', 'filling_mode', 'visible', 'select']
                print(exact_match[selected_cols].to_string(index=False))
            else:
                # Szukanie podobnych symboli (jeśli dokładne dopasowanie nie istnieje)
                symbol_base = symbol.replace('.pro', '')
                similar_matches = df[df['symbol'].str.contains(symbol_base, case=False)]
                
                if not similar_matches.empty:
                    print(f"\n--- Symbole podobne do '{symbol}' (dokładny symbol nie znaleziony) ---")
                    selected_cols = ['symbol', 'description', 'currency_base', 'currency_profit', 'filling_mode', 'visible', 'select']
                    print(similar_matches[selected_cols].to_string(index=False))
                else:
                    print(f"\nBrak symboli '{symbol}' ani podobnych")
        
        # Zamknięcie połączenia
        mt5.shutdown()
        logger.info("Zamknięto połączenie z MT5")
        
    except Exception as e:
        logger.error(f"Wystąpił błąd: {e}", exc_info=True)
        mt5.shutdown()

if __name__ == "__main__":
    main() 