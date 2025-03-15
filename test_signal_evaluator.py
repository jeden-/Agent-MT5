#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Test systemu oceny sygnałów tradingowych.

Ten skrypt testuje działanie klas SignalEvaluator i SignalEvaluationRepository,
które służą do rejestracji, śledzenia i oceny wydajności sygnałów tradingowych.
"""

import os
import sys
import logging
from datetime import datetime, timedelta
import random
import pandas as pd
from dotenv import load_dotenv
import traceback

# Dodanie katalogu głównego projektu do ścieżki Pythona
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Konfiguracja loggera
logging.basicConfig(
    level=logging.DEBUG,  # Zmiana na DEBUG, aby wyświetlać więcej szczegółów
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('test_signal_evaluator')

print("Rozpoczęcie testów systemu oceny sygnałów...")  # Dodajemy bezpośredni print dla debugowania

# Załadowanie zmiennych środowiskowych
load_dotenv()
print("Zmienne środowiskowe załadowane.")  # Dodajemy bezpośredni print dla debugowania

# Importy własnych modułów
try:
    from src.analysis.signal_evaluator import SignalEvaluator
    from src.database import SignalEvaluationRepository, get_signal_evaluation_repository
    from src.mt5_bridge.mt5_connector import MT5Connector, get_mt5_connector
    print("Moduły zaimportowane pomyślnie.")  # Dodajemy bezpośredni print dla debugowania
except Exception as e:
    print(f"Błąd podczas importowania modułów: {e}")
    traceback.print_exc()
    sys.exit(1)

def generate_test_signals(number=10):
    """
    Generuje testowe sygnały tradingowe.
    
    Args:
        number (int): Liczba sygnałów do wygenerowania
        
    Returns:
        list: Lista słowników reprezentujących sygnały
    """
    symbols = ['EURUSD', 'GBPUSD', 'USDJPY', 'AUDUSD']
    timeframes = ['M5', 'M15', 'H1', 'H4']
    directions = ['BUY', 'SELL']
    
    signals = []
    now = datetime.now()
    
    for i in range(number):
        symbol = random.choice(symbols)
        timeframe = random.choice(timeframes)
        direction = random.choice(directions)
        
        # Generowanie losowych cen
        price = round(random.uniform(1.0, 1.5), 5)
        stop_loss = price * (0.99 if direction == 'BUY' else 1.01)
        take_profit = price * (1.02 if direction == 'BUY' else 0.98)
        
        # Zaokrąglenie do 5 miejsc po przecinku
        stop_loss = round(stop_loss, 5)
        take_profit = round(take_profit, 5)
        
        signals.append({
            'signal_id': f"test_signal_{i}_{now.timestamp()}",
            'symbol': symbol,
            'timeframe': timeframe,
            'direction': direction,
            'entry_price': price,
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'confidence': random.uniform(0.6, 0.95),
            'timestamp': now - timedelta(minutes=random.randint(1, 60))
        })
    
    return signals

def test_signal_registration():
    """
    Testuje rejestrację sygnałów tradingowych.
    """
    print("Testowanie rejestracji sygnałów...")  # Dodajemy bezpośredni print dla debugowania
    logger.info("Testowanie rejestracji sygnałów...")
    
    try:
        from src.database.models import TradingSignal
        
        evaluator = SignalEvaluator()
        print(f"Inicjalizator SignalEvaluator utworzony: {evaluator}")  # Dodajemy bezpośredni print dla debugowania
        
        # Sprawdź dostępne metody w klasie SignalEvaluator
        print(f"Dostępne metody w klasie SignalEvaluator: {[method for method in dir(evaluator) if not method.startswith('_')]}")
        
        test_signals = generate_test_signals(2)  # Zmniejszamy liczbę sygnałów do testów
        print(f"Wygenerowano {len(test_signals)} testowych sygnałów")  # Dodajemy bezpośredni print dla debugowania
        
        for i, signal_data in enumerate(test_signals):
            print(f"Rejestracja sygnału {i+1}/{len(test_signals)}: {signal_data['signal_id']}")  # Dodajemy bezpośredni print dla debugowania
            
            # Tworzenie obiektu TradingSignal
            signal = TradingSignal(
                id=signal_data['signal_id'],
                symbol=signal_data['symbol'],
                timeframe=signal_data['timeframe'],
                direction=signal_data['direction'],
                entry_price=signal_data['entry_price'],
                stop_loss=signal_data['stop_loss'],
                take_profit=signal_data['take_profit'],
                confidence=signal_data['confidence'],
                created_at=signal_data['timestamp'],
                status='NEW'
            )
            
            print(f"Utworzony obiekt TradingSignal: {signal.__dict__}")
            
            # Rejestracja sygnału
            try:
                result = evaluator.register_new_signal(signal)
                print(f"Wynik rejestracji sygnału: {result}")
            except Exception as e:
                print(f"Błąd podczas rejestracji sygnału: {e}")
                traceback.print_exc()
        
        logger.info("Rejestracja sygnałów zakończona.")
        print("Rejestracja sygnałów zakończona.")  # Dodajemy bezpośredni print dla debugowania
    except Exception as e:
        logger.error(f"Błąd podczas rejestracji sygnałów: {e}")
        print(f"Błąd podczas rejestracji sygnałów: {e}")  # Dodajemy bezpośredni print dla debugowania
        traceback.print_exc()

def test_update_evaluations():
    """
    Testuje aktualizację oceny sygnałów.
    """
    print("Testowanie aktualizacji oceny sygnałów...")  # Dodajemy bezpośredni print dla debugowania
    logger.info("Testowanie aktualizacji oceny sygnałów...")
    
    try:
        evaluator = SignalEvaluator()
        repo = get_signal_evaluation_repository()
        print(f"Inicjalizator SignalEvaluationRepository utworzony: {repo}")  # Dodajemy bezpośredni print dla debugowania
        
        # Pobierz otwarte oceny
        open_evaluations = repo.get_open_evaluations()
        logger.info(f"Znaleziono {len(open_evaluations)} otwartych ocen sygnałów.")
        print(f"Znaleziono {len(open_evaluations)} otwartych ocen sygnałów.")  # Dodajemy bezpośredni print dla debugowania
        
        # Uzyskaj połączenie z MT5
        mt5_connector = get_mt5_connector()
        print(f"Inicjalizator MT5Connector utworzony: {mt5_connector}")  # Dodajemy bezpośredni print dla debugowania
        
        if not mt5_connector.is_connected():
            logger.info("Łączenie z MT5...")
            print("Łączenie z MT5...")  # Dodajemy bezpośredni print dla debugowania
            mt5_connector.connect()
        
        # Aktualizuj oceny sygnałów na podstawie aktualnych cen
        for i, eval_record in enumerate(open_evaluations):
            symbol = eval_record.symbol
            print(f"Aktualizacja oceny {i+1}/{len(open_evaluations)}: {eval_record.id} dla {symbol}")  # Dodajemy bezpośredni print dla debugowania
            
            current_price = mt5_connector.get_current_price(symbol)
            if current_price:
                evaluator.update_evaluation(
                    evaluation_id=eval_record.id,
                    current_price=current_price
                )
                logger.info(f"Zaktualizowano ocenę dla {symbol} przy cenie {current_price}")
                print(f"Zaktualizowano ocenę dla {symbol} przy cenie {current_price}")  # Dodajemy bezpośredni print dla debugowania
            else:
                logger.warning(f"Nie można pobrać aktualnej ceny dla {symbol}")
                print(f"Nie można pobrać aktualnej ceny dla {symbol}")  # Dodajemy bezpośredni print dla debugowania
        
        logger.info("Aktualizacja ocen zakończona.")
        print("Aktualizacja ocen zakończona.")  # Dodajemy bezpośredni print dla debugowania
    except Exception as e:
        logger.error(f"Błąd podczas aktualizacji ocen: {e}")
        print(f"Błąd podczas aktualizacji ocen: {e}")  # Dodajemy bezpośredni print dla debugowania
        traceback.print_exc()

def test_performance_metrics():
    """
    Testuje pobieranie metryk wydajności sygnałów.
    """
    print("Testowanie metryk wydajności sygnałów...")  # Dodajemy bezpośredni print dla debugowania
    logger.info("Testowanie metryk wydajności sygnałów...")
    
    try:
        evaluator = SignalEvaluator()
        
        # Pobierz ogólne metryki wydajności
        performance = evaluator.get_signal_performance(days=7)
        logger.info("Wyniki sygnałów z ostatnich 7 dni:")
        print("Wyniki sygnałów z ostatnich 7 dni:")  # Dodajemy bezpośredni print dla debugowania
        logger.info(f"Liczba sygnałów: {performance.get('total_signals', 0)}")
        print(f"Liczba sygnałów: {performance.get('total_signals', 0)}")  # Dodajemy bezpośredni print dla debugowania
        logger.info(f"Skuteczność: {performance.get('success_rate', 0):.2f}%")
        print(f"Skuteczność: {performance.get('success_rate', 0):.2f}%")  # Dodajemy bezpośredni print dla debugowania
        logger.info(f"Średni zysk: {performance.get('avg_profit', 0):.4f}")
        print(f"Średni zysk: {performance.get('avg_profit', 0):.4f}")  # Dodajemy bezpośredni print dla debugowania
        
        # Pobierz metryki wydajności według poziomu pewności
        confidence_perf = evaluator.get_performance_by_confidence(days=7)
        logger.info("\nWydajność według poziomu pewności:")
        print("\nWydajność według poziomu pewności:")  # Dodajemy bezpośredni print dla debugowania
        for level, metrics in confidence_perf.items():
            logger.info(f"Poziom pewności {level}: {metrics.get('success_rate', 0):.2f}% skuteczności, średni zysk: {metrics.get('avg_profit', 0):.4f}")
            print(f"Poziom pewności {level}: {metrics.get('success_rate', 0):.2f}% skuteczności, średni zysk: {metrics.get('avg_profit', 0):.4f}")  # Dodajemy bezpośredni print dla debugowania
        
        # Pobierz metryki wydajności według timeframe'u
        timeframe_perf = evaluator.get_performance_by_timeframe(days=7)
        logger.info("\nWydajność według timeframe'u:")
        print("\nWydajność według timeframe'u:")  # Dodajemy bezpośredni print dla debugowania
        for tf, metrics in timeframe_perf.items():
            logger.info(f"Timeframe {tf}: {metrics.get('success_rate', 0):.2f}% skuteczności, średni zysk: {metrics.get('avg_profit', 0):.4f}")
            print(f"Timeframe {tf}: {metrics.get('success_rate', 0):.2f}% skuteczności, średni zysk: {metrics.get('avg_profit', 0):.4f}")  # Dodajemy bezpośredni print dla debugowania
        
        logger.info("Testowanie metryk wydajności zakończone.")
        print("Testowanie metryk wydajności zakończone.")  # Dodajemy bezpośredni print dla debugowania
    except Exception as e:
        logger.error(f"Błąd podczas pobierania metryk wydajności: {e}")
        print(f"Błąd podczas pobierania metryk wydajności: {e}")  # Dodajemy bezpośredni print dla debugowania
        traceback.print_exc()

def main():
    """
    Główna funkcja testowa.
    """
    print("Rozpoczęcie głównej funkcji testowej...")  # Dodajemy bezpośredni print dla debugowania
    logger.info("Rozpoczęcie testów systemu oceny sygnałów...")
    
    try:
        # Test rejestracji sygnałów
        test_signal_registration()
        
        # Test aktualizacji ocen
        test_update_evaluations()
        
        # Test metryk wydajności
        test_performance_metrics()
        
        logger.info("Testy systemu oceny sygnałów zakończone.")
        print("Testy systemu oceny sygnałów zakończone.")  # Dodajemy bezpośredni print dla debugowania
    except Exception as e:
        logger.error(f"Błąd podczas testów: {e}")
        print(f"Błąd podczas testów: {e}")  # Dodajemy bezpośredni print dla debugowania
        traceback.print_exc()

if __name__ == "__main__":
    main() 