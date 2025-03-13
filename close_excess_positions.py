#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Skrypt do zamykania nadmiarowych pozycji na platformie MT5.

Ten skrypt identyfikuje i zamyka nadmiarowe pozycje, pozostawiając tylko 
określoną liczbę najlepszych pozycji dla każdego symbolu, zgodnie z 
ustawieniami RiskManager. Dodatkowo przestrzega globalnego limitu pozycji.
"""

import os
import sys
import logging
from datetime import datetime
from dotenv import load_dotenv
import pandas as pd
from collections import defaultdict

# Dodanie ścieżki projektu do sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import modułów projektu
from src.mt5_bridge import MT5Server
from src.mt5_bridge.mt5_connector import MT5Connector
from src.trading_integration import TradingIntegration
from src.risk_management import RiskManager
from src.position_management import PositionManager
from src.utils.patches import patched_close_position

# Konfiguracja loggera
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('close_positions.log')
    ]
)
logger = logging.getLogger('close_excess_positions')

def init_mt5():
    """Inicjalizacja połączenia z MT5."""
    # Wczytanie zmiennych środowiskowych
    load_dotenv()
    
    # Pobieranie danych logowania z .env
    mt5_login = int(os.getenv('MT5_LOGIN'))
    mt5_password = os.getenv('MT5_PASSWORD')
    mt5_server = os.getenv('MT5_SERVER')
    
    # Inicjalizacja połączenia z MT5
    logger.info("Inicjalizacja połączenia z MT5...")
    mt5_connector = MT5Connector()
    
    # Połączenie z MT5
    if not mt5_connector.connect():
        logger.error("Nie udało się połączyć z MT5")
        return None
    
    logger.info(f"Połączono z MT5")
    return mt5_connector

def get_positions(mt5_connector):
    """Pobiera otwarte pozycje z MT5."""
    positions = mt5_connector.get_open_positions()
    if positions is None:
        logger.error("Nie udało się pobrać otwartych pozycji")
        return []
    
    logger.info(f"Pobrano {len(positions)} otwartych pozycji")
    return positions

def group_positions_by_symbol(positions):
    """Grupuje pozycje według symbolu i typu."""
    grouped = defaultdict(lambda: defaultdict(list))
    
    for pos in positions:
        symbol = pos['symbol']
        pos_type = pos['type']
        grouped[symbol][pos_type].append(pos)
    
    return grouped

def determine_positions_to_close(grouped_positions, max_per_symbol=1, max_total=1):
    """
    Określa, które pozycje należy zamknąć, przestrzegając:
    1. Limit max_per_symbol pozycji dla każdego symbolu i kierunku
    2. Limit max_total pozycji łącznie w całym portfelu
    
    Metoda sortuje wszystkie pozycje według zysku i zachowuje tylko najlepsze.
    """
    positions_to_close = []
    all_filtered_positions = []
    
    # Krok 1: Filtroowanie na podstawie limitu per symbol
    for symbol, type_positions in grouped_positions.items():
        for pos_type, positions in type_positions.items():
            # Sortowanie pozycji według zysku (od najlepszej do najgorszej)
            sorted_positions = sorted(positions, key=lambda x: x['profit'], reverse=True)
            
            # Zachowaj max_per_symbol najlepszych pozycji
            best_positions = sorted_positions[:max_per_symbol]
            
            # Dodaj pozostałe do listy do zamknięcia
            positions_to_close.extend(sorted_positions[max_per_symbol:])
            
            # Dodaj najlepsze pozycje do ogólnej listy posortowanych pozycji
            all_filtered_positions.extend(best_positions)
    
    # Krok 2: Jeśli po filtrowaniu per symbol mamy nadal za dużo pozycji, 
    # sortujemy je wszystkie i zachowujemy najlepsze max_total
    if len(all_filtered_positions) > max_total:
        # Sortowanie według zysku (od najlepszej do najgorszej)
        all_filtered_positions.sort(key=lambda x: x['profit'], reverse=True)
        
        # Pozycje do zamknięcia to wszystkie poza max_total najlepszymi
        positions_to_close.extend(all_filtered_positions[max_total:])
    
    return positions_to_close

def close_positions(mt5_connector, positions_to_close):
    """Zamyka określone pozycje."""
    closed_count = 0
    
    for pos in positions_to_close:
        logger.info(f"Zamykanie pozycji {pos['ticket']} dla {pos['symbol']} (typ: {pos['type']}, zysk: {pos['profit']})")
        
        try:
            result = patched_close_position(mt5_connector, pos['ticket'])
            if result:
                logger.info(f"Pozycja {pos['ticket']} zamknięta pomyślnie")
                closed_count += 1
            else:
                logger.error(f"Nie udało się zamknąć pozycji {pos['ticket']}")
        except Exception as e:
            logger.error(f"Błąd podczas zamykania pozycji {pos['ticket']}: {str(e)}")
    
    return closed_count

def main():
    """Główna funkcja skryptu."""
    logger.info("Rozpoczynam proces zamykania nadmiarowych pozycji")
    
    # Inicjalizacja połączenia z MT5
    mt5_connector = init_mt5()
    if mt5_connector is None:
        return
    
    try:
        # Inicjalizacja RiskManager
        risk_manager = RiskManager()
        max_per_symbol = risk_manager.parameters.max_positions_per_symbol
        max_total = risk_manager.parameters.max_positions_total
        
        logger.info(f"Limity pozycji: {max_per_symbol} per symbol, {max_total} łącznie")
        
        # Pobieranie otwartych pozycji
        positions = get_positions(mt5_connector)
        if not positions:
            logger.info("Brak otwartych pozycji do przetworzenia")
            return
        
        # Grupowanie pozycji według symbolu i typu
        grouped_positions = group_positions_by_symbol(positions)
        
        # Określenie pozycji do zamknięcia
        positions_to_close = determine_positions_to_close(grouped_positions, max_per_symbol, max_total)
        
        if not positions_to_close:
            logger.info("Brak nadmiarowych pozycji do zamknięcia")
            return
        
        logger.info(f"Znaleziono {len(positions_to_close)} nadmiarowych pozycji do zamknięcia")
        
        # Zamknięcie nadmiarowych pozycji
        closed_count = close_positions(mt5_connector, positions_to_close)
        logger.info(f"Zamknięto {closed_count} z {len(positions_to_close)} nadmiarowych pozycji")
        
    finally:
        # Zamknięcie połączenia z MT5
        if mt5_connector:
            mt5_connector.disconnect()
            logger.info("Połączenie z MT5 zostało zamknięte")

if __name__ == "__main__":
    main() 