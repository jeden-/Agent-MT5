#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Test bezpośredniego generowania sygnału z bieżących danych rynkowych.
"""

import os
import sys
import logging
import traceback
from datetime import datetime

# Konfiguracja loggera
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("test_direct_signal")

# Dodanie katalogu głównego projektu do sys.path
root_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, root_dir)

# Import modułów projektu
from src.analysis.signal_generator import SignalGenerator
from src.mt5_bridge.mt5_connector import MT5Connector
from src.config.config_manager import ConfigManager
from src.database.db_manager import DatabaseManager

def test_direct_signal():
    """
    Funkcja testująca bezpośrednie generowanie sygnału.
    """
    logger.info("Rozpoczynam test bezpośredniego generowania sygnału")
    
    try:
        # Inicjalizacja zależności
        db_manager = DatabaseManager()
        config_manager = ConfigManager()
        mt5_connector = MT5Connector()
        mt5_connector.connect()
        
        # Inicjalizacja generatora sygnałów z optymalnymi parametrami
        signal_generator = SignalGenerator()
        
        # Wypisz parametry w logach
        logger.info("Parametry sygnału:")
        logger.info("RSI Period: 7 (optymalny)")
        logger.info("MACD Fast: 12 (optymalny)")
        logger.info("MACD Slow: 26 (optymalny)")
        logger.info("BB Period: 15 (optymalny)")
        
        # Testowanie sygnałów dla różnych instrumentów i ram czasowych
        instruments = ["EURUSD", "GBPUSD", "USDJPY", "GOLD", "SILVER"]
        timeframes = ["M1", "M5", "M15", "H1", "D1"]
        signal_count = 0
        
        for instrument in instruments:
            logger.info(f"\n=== Testowanie sygnałów dla {instrument} ===")
            
            for tf in timeframes:
                logger.info(f"\n--- Ramy czasowe: {tf} ---")
                logger.info(f"Generowanie sygnału dla {instrument} na ramach czasowych {tf}")
                
                try:
                    # Pobieranie danych historycznych
                    rates_df = mt5_connector.get_historical_data(instrument, tf, count=100)
                    
                    if rates_df is None or len(rates_df) < 50:
                        logger.warning(f"Niewystarczająca ilość danych dla {instrument}")
                        continue
                    
                    # Wyświetlenie ostatnich wartości wskaźników
                    last_close = rates_df['close'].iloc[-1]
                    
                    # Pobierz szczegóły analizy technicznej bezpośrednio
                    data = {
                        'open': rates_df['open'].astype(float).tolist(),
                        'high': rates_df['high'].astype(float).tolist(),
                        'low': rates_df['low'].astype(float).tolist(),
                        'close': rates_df['close'].astype(float).tolist(),
                        'volume': rates_df['tick_volume'].astype(float).tolist(),
                        'time': [t.strftime('%Y-%m-%d %H:%M:%S') for t in rates_df['time']]
                    }
                    
                    tech_result = signal_generator._analyze_technical_data(instrument, tf, data)
                    
                    # Wyświetl wartości wskaźników
                    if 'details' in tech_result and 'indicators' in tech_result['details']:
                        indicators = tech_result['details']['indicators']
                        logger.info(f"RSI: {indicators['rsi']}")
                        logger.info(f"MACD: {indicators['macd']}, Signal: {indicators['macd_signal']}")
                        logger.info(f"Bollinger Bands: Upper: {indicators['upper_bb']}, Middle: {indicators['middle_bb']}, Lower: {indicators['lower_bb']}")
                        logger.info(f"Aktualna cena: {last_close}")
                    
                    if 'details' in tech_result and 'signals' in tech_result['details']:
                        logger.info(f"Sygnały z poszczególnych wskaźników: {tech_result['details']['signals']}")
                        logger.info(f"Poziomy pewności: {tech_result['details']['confidence_scores']}")
                    
                    # Generowanie sygnału
                    signal = signal_generator.generate_signal(instrument, tf)
                    
                    if signal:
                        signal_count += 1
                        logger.info(f"Wygenerowano sygnał dla {instrument} na ramach czasowych {tf}:")
                        logger.info(f"Kierunek: {signal.direction}")
                        logger.info(f"Pewność: {signal.confidence:.2f}")
                        logger.info(f"Cena wejścia: {signal.entry_price:.5f}")
                        logger.info(f"Stop Loss: {signal.stop_loss:.5f}")
                        logger.info(f"Take Profit: {signal.take_profit:.5f}")
                        logger.info(f"Analiza AI: {signal.ai_analysis}")
                        logger.info(f"Czas: {signal.created_at}")
                    else:
                        logger.info(f"Brak sygnału dla {instrument} na ramach czasowych {tf}\n")
                        
                except Exception as e:
                    logger.error(f"Błąd podczas generowania sygnału dla {instrument} na ramach czasowych {tf}: {e}")
                    logger.debug(traceback.format_exc())
        
        logger.info(f"\nPodsumowanie: wygenerowano {signal_count} sygnałów na {len(instruments) * len(timeframes)} możliwych.")
            
    except Exception as e:
        logger.error(f"Błąd podczas testu: {e}")
        logger.debug(traceback.format_exc())

if __name__ == "__main__":
    logger.info("Rozpoczynanie testu generatora sygnałów")
    test_direct_signal()
    logger.info("Test zakończony") 