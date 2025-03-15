import os
import sys
import logging
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path

# Dodaj katalog główny projektu do ścieżki
project_root = Path(__file__).resolve().parent
sys.path.append(str(project_root))

# Import właściwych modułów
from src.mt5_bridge.mt5_connector import MT5Connector
from src.backtest.historical_data_manager import HistoricalDataManager

# Konfiguracja logowania
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('data_check')

def check_data_availability(symbols=None, timeframes=None, days_back=30):
    """
    Sprawdza dostępność danych historycznych dla podanych symboli i interwałów czasowych.
    
    Args:
        symbols: Lista symboli do sprawdzenia (None = domyślna lista)
        timeframes: Lista timeframe'ów do sprawdzenia (None = domyślna lista)
        days_back: Ile dni wstecz sprawdzać
    """
    # Domyślne wartości
    if symbols is None:
        symbols = ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCAD", "USDCHF", "NZDUSD", 
                  "EURJPY", "EURGBP", "GOLD", "SILVER", "OIL", "US100", "US500", "DE30", "UK100"]
    
    if timeframes is None:
        timeframes = ["M1", "M5", "M15", "M30", "H1", "H4", "D1", "W1", "MN1"]
    
    # Inicjalizacja MT5Connector
    mt5 = MT5Connector()
    
    # Sprawdzenie połączenia
    if not mt5.connect():
        logger.error("Nie można połączyć się z MT5")
        return
    
    logger.info(f"Połączono z MT5. Sprawdzanie dostępności danych dla {len(symbols)} symboli i {len(timeframes)} timeframe'ów")
    
    # Przygotowanie dat
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days_back)
    
    # Przygotowanie wyników
    results = []
    
    # Sprawdzenie każdej kombinacji symbolu i timeframe'u
    for symbol in symbols:
        for timeframe in timeframes:
            logger.info(f"Sprawdzanie {symbol} na {timeframe}...")
            
            try:
                # Próba pobrania danych
                data = mt5.get_historical_data(
                    symbol=symbol,
                    timeframe=timeframe,
                    start_time=start_date,
                    end_time=end_date
                )
                
                # Analiza wyników
                if data is None or data.empty:
                    status = "Brak danych"
                    count = 0
                    first_date = None
                    last_date = None
                else:
                    status = "OK"
                    count = len(data)
                    first_date = data['time'].min()
                    last_date = data['time'].max()
                
                # Zapisanie wyników
                results.append({
                    'Symbol': symbol,
                    'Timeframe': timeframe,
                    'Status': status,
                    'Liczba rekordów': count,
                    'Pierwsza data': first_date,
                    'Ostatnia data': last_date
                })
                
            except Exception as e:
                logger.error(f"Błąd podczas sprawdzania {symbol} {timeframe}: {e}")
                results.append({
                    'Symbol': symbol,
                    'Timeframe': timeframe,
                    'Status': f"BŁĄD: {str(e)}",
                    'Liczba rekordów': 0,
                    'Pierwsza data': None,
                    'Ostatnia data': None
                })
    
    # Zamknięcie połączenia
    mt5.disconnect()
    
    # Konwersja wyników do DataFrame
    results_df = pd.DataFrame(results)
    
    # Zapisanie wyników do pliku CSV
    output_file = "data_availability_check.csv"
    results_df.to_csv(output_file, index=False)
    logger.info(f"Wyniki zapisane do pliku {output_file}")
    
    # Wyświetlenie podsumowania
    print("\nPodsumowanie dostępności danych:")
    print(f"Sprawdzono {len(symbols)} symboli na {len(timeframes)} timeframe'ach")
    print(f"Dostępne dane: {len(results_df[results_df['Status'] == 'OK'])}/{len(results_df)} kombinacji")
    
    # Wyświetlenie symboli bez danych
    no_data = results_df[results_df['Status'] != 'OK']
    if not no_data.empty:
        print("\nSymbole bez dostępnych danych:")
        grouped = no_data.groupby('Symbol').size()
        for symbol, count in grouped.items():
            print(f"  {symbol}: brak danych dla {count}/{len(timeframes)} timeframe'ów")
    
    return results_df

def test_historical_data_manager():
    """
    Testuje działanie HistoricalDataManager, w tym zapis i odczyt danych z cache.
    """
    # Inicjalizacja konektorów
    mt5 = MT5Connector()
    hdm = HistoricalDataManager(mt5_connector=mt5)
    
    if not mt5.connect():
        logger.error("Nie można połączyć się z MT5")
        return
    
    # Parametry testu
    symbols = ["EURUSD", "GBPUSD", "GOLD"]
    timeframes = ["H1", "D1"]
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)
    
    for symbol in symbols:
        for timeframe in timeframes:
            logger.info(f"Testowanie cache dla {symbol} {timeframe}...")
            
            # Test 1: Pobieranie danych bez cache'u
            data1 = hdm.get_historical_data(
                symbol=symbol,
                timeframe=timeframe,
                start_date=start_date,
                end_date=end_date,
                use_cache=False,
                update_cache=True
            )
            
            if data1 is None or data1.empty:
                logger.warning(f"Brak danych dla {symbol} {timeframe}")
                continue
                
            logger.info(f"Pobrano {len(data1)} rekordów bez cache'u")
            
            # Test 2: Pobieranie danych z cache'u
            data2 = hdm.get_historical_data(
                symbol=symbol,
                timeframe=timeframe,
                start_date=start_date,
                end_date=end_date,
                use_cache=True
            )
            
            if data2 is None or data2.empty:
                logger.error(f"Nie udało się pobrać danych z cache'u dla {symbol} {timeframe}")
                continue
                
            logger.info(f"Pobrano {len(data2)} rekordów z cache'u")
            
            # Porównanie danych
            if len(data1) == len(data2):
                logger.info(f"Zgodność liczby rekordów: OK")
            else:
                logger.warning(f"Niezgodność liczby rekordów: {len(data1)} vs {len(data2)}")
            
            # Sprawdzenie metadanych cache'u
            key = f"{symbol}_{timeframe}"
            if key in hdm.cache_metadata:
                logger.info(f"Metadane cache dla {key}: {len(hdm.cache_metadata[key])} plików")
            else:
                logger.warning(f"Brak metadanych cache dla {key}")
    
    # Sprawdzenie statystyk cache'u
    stats = hdm.get_cache_stats()
    logger.info(f"Statystyki cache: {stats}")
    
    # Zamknięcie połączenia
    mt5.disconnect()
    
    return stats

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Narzędzie do sprawdzania dostępności danych historycznych w MT5")
    parser.add_argument("--symbols", nargs="+", help="Lista symboli do sprawdzenia")
    parser.add_argument("--timeframes", nargs="+", help="Lista timeframe'ów do sprawdzenia")
    parser.add_argument("--days", type=int, default=30, help="Liczba dni wstecz do sprawdzenia")
    parser.add_argument("--test-cache", action="store_true", help="Testuj HistoricalDataManager i cache")
    
    args = parser.parse_args()
    
    if args.test_cache:
        test_historical_data_manager()
    else:
        check_data_availability(symbols=args.symbols, timeframes=args.timeframes, days_back=args.days) 