#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Skrypt do uruchamiania agenta tradingowego z ograniczeniem liczby pozycji.

Ten skrypt uruchamia agenta tradingowego z dodatkowymi zabezpieczeniami,
które ograniczają liczbę otwieranych pozycji zgodnie z ustawieniami w RiskManager.
"""

import os
import sys
import time
import logging
from datetime import datetime
from dotenv import load_dotenv
import asyncio
import json

# Dodanie ścieżki projektu do sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import modułów projektu
from src.mt5_bridge import MT5Server
from src.mt5_bridge.mt5_connector import MT5Connector
from src.trading_integration import TradingIntegration
from src.risk_management import RiskManager
from src.position_management import PositionManager
from src.analysis import SignalGenerator
from src.database import DatabaseManager
from start import load_config

# Konfiguracja loggera
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('agent_with_limits.log')
    ]
)
logger = logging.getLogger('agent_with_limits')

def init_components():
    """Inicjalizacja komponentów systemu."""
    # Wczytanie zmiennych środowiskowych
    load_dotenv()
    
    # Inicjalizacja połączenia z MT5
    logger.info("Inicjalizacja połączenia z MT5...")
    mt5_connector = MT5Connector()
    
    # Połączenie z MT5
    if not mt5_connector.connect():
        logger.error("Nie udało się połączyć z MT5")
        return None
    
    logger.info(f"Połączono z MT5")
    
    # Inicjalizacja pozostałych komponentów
    trading_service = mt5_connector.get_trading_service()
    risk_manager = RiskManager()
    position_manager = PositionManager({})
    
    # Wczytanie konfiguracji
    config = load_config()
    
    # Inicjalizacja TradingIntegration
    trading_integration = TradingIntegration(
        trading_service=trading_service,
        position_manager=position_manager,
        risk_manager=risk_manager,
        config=config
    )
    
    # Inicjalizacja generatora sygnałów
    signal_generator = SignalGenerator()
    
    return {
        'mt5_connector': mt5_connector,
        'trading_service': trading_service,
        'risk_manager': risk_manager,
        'position_manager': position_manager,
        'trading_integration': trading_integration,
        'signal_generator': signal_generator,
        'config': config
    }

def register_instruments(trading_integration, instruments):
    """Rejestruje instrumenty do handlu."""
    for symbol, max_lot_size in instruments.items():
        logger.info(f"Rejestrowanie instrumentu: {symbol} (max_lot_size={max_lot_size})")
        trading_integration.register_instrument(symbol, max_lot_size)

def check_position_limits(position_manager, risk_manager):
    """
    Sprawdza, czy limity pozycji są przestrzegane.
    
    Returns:
        bool: True jeśli limity są przestrzegane, False w przeciwnym razie
    """
    try:
        # Pobierz otwarte pozycje
        open_positions = position_manager.get_active_positions()
        
        # Grupuj pozycje według symbolu
        positions_by_symbol = {}
        for pos in open_positions:
            if pos.symbol not in positions_by_symbol:
                positions_by_symbol[pos.symbol] = []
            positions_by_symbol[pos.symbol].append(pos)
        
        # Sprawdź limity dla każdego symbolu
        for symbol, positions in positions_by_symbol.items():
            if len(positions) > risk_manager.parameters.max_positions_per_symbol:
                logger.warning(f"Przekroczono limit pozycji dla symbolu {symbol}: {len(positions)} > {risk_manager.parameters.max_positions_per_symbol}")
                return False
        
        # Sprawdź całkowity limit pozycji
        total_positions = len(open_positions)
        if total_positions > risk_manager.parameters.max_positions_total:
            logger.warning(f"Przekroczono całkowity limit pozycji: {total_positions} > {risk_manager.parameters.max_positions_total}")
            return False
        
        return True
    
    except Exception as e:
        logger.error(f"Błąd podczas sprawdzania limitów pozycji: {e}")
        return False

def process_signal(trading_integration, signal, position_manager, risk_manager):
    """
    Przetwarza sygnał handlowy z uwzględnieniem limitów pozycji.
    
    Returns:
        bool: True jeśli sygnał został przetworzony i pozycja otwarta, False w przeciwnym razie
    """
    # Sprawdź, czy limity pozycji są przestrzegane
    if not check_position_limits(position_manager, risk_manager):
        logger.warning(f"Pomijam sygnał dla {signal.symbol} ze względu na przekroczone limity pozycji")
        return False
    
    # Sprawdź, czy symbol jest zarejestrowany do handlu
    if signal.symbol not in trading_integration.registered_instruments:
        logger.warning(f"Symbol {signal.symbol} nie jest zarejestrowany do handlu")
        return False
    
    # Wykonaj sygnał
    logger.info(f"Wykonuję sygnał dla {signal.symbol} ({signal.direction})")
    result = trading_integration.execute_signal(signal)
    
    if result:
        logger.info(f"Pozycja dla {signal.symbol} otwarta pomyślnie")
    else:
        logger.warning(f"Nie udało się otworzyć pozycji dla {signal.symbol}")
    
    return result

def main():
    """Główna funkcja skryptu."""
    logger.info("Uruchamiam agenta tradingowego z ograniczeniami pozycji")
    
    # Inicjalizacja komponentów
    components = init_components()
    if components is None:
        return
    
    mt5_connector = components['mt5_connector']
    trading_integration = components['trading_integration']
    risk_manager = components['risk_manager']
    position_manager = components['position_manager']
    signal_generator = components['signal_generator']
    config = components['config']
    
    try:
        # Wczytanie instrumentów z konfiguracji
        instruments = config.get('instruments', {
            'EURUSD.pro': 0.1,
            'GBPUSD.pro': 0.1,
            'GOLD.pro': 0.1,
            'US100.pro': 0.1,
            'SILVER.pro': 0.1
        })
        
        # Rejestracja instrumentów
        register_instruments(trading_integration, instruments)
        
        # Główna pętla agenta
        logger.info("Rozpoczynam pętlę handlową agenta")
        while True:
            try:
                # Aktualizacja informacji o koncie
                account_info = mt5_connector.get_account_info()
                if account_info:
                    balance = account_info.get('balance', 0)
                    equity = account_info.get('equity', 0)
                    risk_manager.update_account_info(balance, equity)
                    logger.info(f"Saldo konta: {balance}, Kapitał: {equity}")
                
                # Sprawdzenie limitów pozycji
                limits_ok = check_position_limits(position_manager, risk_manager)
                logger.info(f"Limity pozycji przestrzegane: {limits_ok}")
                
                # Pobierz otwarte pozycje dla każdego symbolu
                for symbol in trading_integration.registered_instruments.keys():
                    # Pobierz dane historyczne
                    historical_data = mt5_connector.get_historical_data(symbol, "M15", 100)
                    if historical_data is None:
                        logger.warning(f"Nie udało się pobrać danych historycznych dla {symbol}")
                        continue
                    
                    # Generowanie sygnału tylko jeśli limity są OK
                    if limits_ok:
                        # Generowanie sygnału
                        signal = signal_generator.generate_signal(symbol, historical_data, "M15")
                        if signal and signal.direction in ['BUY', 'SELL']:
                            logger.info(f"Wygenerowano sygnał {signal.direction} dla {symbol}")
                            process_signal(trading_integration, signal, position_manager, risk_manager)
                    
                # Opóźnienie przed kolejną iteracją (15 minut)
                time.sleep(60 * 15)
            
            except Exception as e:
                logger.error(f"Błąd w pętli handlowej: {e}", exc_info=True)
                time.sleep(60)
    
    finally:
        # Zamknięcie połączenia z MT5
        if mt5_connector:
            mt5_connector.disconnect()
            logger.info("Połączenie z MT5 zostało zamknięte")

if __name__ == "__main__":
    main() 