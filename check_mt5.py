import os
import logging
import MetaTrader5 as mt5
from datetime import datetime, timedelta

# Konfiguracja logowania
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def check_mt5_connection():
    """Sprawdza połączenie z terminalem MT5"""
    logger.info("Sprawdzanie połączenia z MT5...")
    
    # Inicjalizacja MT5
    if not mt5.initialize():
        logger.error(f"Nie można połączyć się z MT5: {mt5.last_error()}")
        return False
    
    # Sprawdzanie informacji o terminalu
    terminal_info = mt5.terminal_info()
    if terminal_info is None:
        logger.error(f"Nie można pobrać informacji o terminalu: {mt5.last_error()}")
        mt5.shutdown()
        return False
    
    logger.info(f"Połączono z MT5. Wersja: {mt5.__version__}")
    logger.info(f"Nazwa terminala: {terminal_info.name}")
    logger.info(f"Terminal jest połączony: {terminal_info.connected}")
    logger.info(f"Handel jest dozwolony: {terminal_info.trade_allowed}")
    
    return True

def check_symbol_availability(symbol="EURUSD"):
    """Sprawdza dostępność symbolu w MT5"""
    logger.info(f"Sprawdzanie dostępności symbolu {symbol}...")
    
    # Sprawdzanie wszystkich symboli
    symbols = mt5.symbols_get()
    if symbols is None:
        logger.error(f"Nie można pobrać symboli: {mt5.last_error()}")
        return False
    
    logger.info(f"Liczba dostępnych symboli: {len(symbols)}")
    
    # Sprawdzanie czy żądany symbol jest dostępny
    exact_match = [s.name for s in symbols if s.name == symbol]
    similar_match = [s.name for s in symbols if symbol in s.name]
    
    if exact_match:
        logger.info(f"Symbol {symbol} jest dostępny")
    else:
        logger.warning(f"Symbol {symbol} nie jest bezpośrednio dostępny")
    
    if similar_match:
        logger.info(f"Podobne symbole: {similar_match}")
    
    # Wybieranie symbolu do handlu
    if not mt5.symbol_select(symbol, True):
        alternative_names = [s.name for s in symbols if symbol in s.name]
        if alternative_names:
            alternative = alternative_names[0]
            logger.warning(f"Nie można wybrać symbolu {symbol}, próba alternatywnego symbolu: {alternative}")
            if not mt5.symbol_select(alternative, True):
                logger.error(f"Nie można wybrać alternatywnego symbolu {alternative}: {mt5.last_error()}")
                return False
            else:
                symbol = alternative
        else:
            logger.error(f"Nie można wybrać symbolu {symbol} i nie znaleziono alternatyw: {mt5.last_error()}")
            return False
    
    # Sprawdzanie informacji o symbolu
    symbol_info = mt5.symbol_info(symbol)
    if symbol_info is None:
        logger.error(f"Nie można pobrać informacji o symbolu {symbol}: {mt5.last_error()}")
        return False
    
    logger.info(f"Symbol {symbol_info.name}:")
    logger.info(f"  Bid: {symbol_info.bid}, Ask: {symbol_info.ask}")
    logger.info(f"  Wartość punktu: {symbol_info.point}")
    logger.info(f"  Liczba cyfr po przecinku: {symbol_info.digits}")
    
    return True

def check_historical_data(symbol="EURUSD", timeframe="H1"):
    """Sprawdza możliwość pobierania danych historycznych"""
    logger.info(f"Sprawdzanie dostępu do danych historycznych dla {symbol} na timeframe {timeframe}...")
    
    # Mapowanie timeframe na stałe MT5
    timeframe_map = {
        "M1": mt5.TIMEFRAME_M1,
        "M5": mt5.TIMEFRAME_M5,
        "M15": mt5.TIMEFRAME_M15,
        "M30": mt5.TIMEFRAME_M30,
        "H1": mt5.TIMEFRAME_H1,
        "H4": mt5.TIMEFRAME_H4,
        "D1": mt5.TIMEFRAME_D1,
        "W1": mt5.TIMEFRAME_W1,
        "MN1": mt5.TIMEFRAME_MN1
    }
    
    if timeframe not in timeframe_map:
        logger.error(f"Nieprawidłowy timeframe: {timeframe}. Dostępne: {list(timeframe_map.keys())}")
        return False
    
    mt5_timeframe = timeframe_map[timeframe]
    
    # Pobieranie danych historycznych
    now = datetime.now()
    from_date = now - timedelta(days=1)  # Dane z ostatniego dnia
    
    # Pobieranie danych
    rates = mt5.copy_rates_range(symbol, mt5_timeframe, from_date, now)
    if rates is None or len(rates) == 0:
        logger.error(f"Nie można pobrać danych historycznych dla {symbol} na timeframe {timeframe}: {mt5.last_error()}")
        
        # Próba pobrania 10 ostatnich słupków
        logger.info("Próba pobrania ostatnich 10 słupków...")
        rates = mt5.copy_rates_from_pos(symbol, mt5_timeframe, 0, 10)
        if rates is None or len(rates) == 0:
            logger.error(f"Nie można pobrać ostatnich słupków dla {symbol}: {mt5.last_error()}")
            return False
    
    logger.info(f"Pobrano {len(rates)} słupków danych historycznych")
    
    # Wyświetlenie pierwszych kilku słupków
    for i, rate in enumerate(rates[:5]):
        time_str = datetime.fromtimestamp(rate[0]).strftime('%Y-%m-%d %H:%M:%S')
        logger.info(f"  {i+1}: {time_str} - OHLC: {rate[1]:.5f}, {rate[2]:.5f}, {rate[3]:.5f}, {rate[4]:.5f}")
    
    return True

if __name__ == "__main__":
    try:
        # Sprawdzenie połączenia z MT5
        if not check_mt5_connection():
            logger.error("Test połączenia z MT5 nie powiódł się")
            exit(1)
        
        # Sprawdzenie dostępności symbolu
        if not check_symbol_availability("EURUSD"):
            logger.warning("Test dostępności symbolu EURUSD nie powiódł się")
        
        # Sprawdzenie danych historycznych
        if not check_historical_data("EURUSD", "H1"):
            logger.warning("Test pobierania danych historycznych dla EURUSD H1 nie powiódł się")
            
    finally:
        # Zamknięcie połączenia z MT5
        mt5.shutdown()
        logger.info("Testy zakończone, połączenie z MT5 zamknięte") 