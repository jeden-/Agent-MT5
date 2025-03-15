#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Moduł harmonogramu zadań dla AgentMT5.

Ten moduł jest odpowiedzialny za planowanie i wykonywanie zadań cyklicznych,
takich jak generowanie sygnałów, aktualizacja danych rynkowych, itd.
"""

import time
import threading
import logging
import random
import psutil
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
import traceback

# Import potrzebnych modułów
from src.analysis.signal_generator import SignalGenerator
from src.mt5_bridge.mt5_connector import MT5Connector

# Konfiguracja loggera
logger = logging.getLogger("scheduler")

class DataRefreshManager:
    """
    Klasa zarządzająca odświeżaniem danych rynkowych dla różnych timeframe'ów.
    Optymalizuje częstotliwość pobierania danych w zależności od timeframe'u.
    """
    
    def __init__(self, mt5_connector: MT5Connector):
        """
        Inicjalizacja menedżera odświeżania danych.
        
        Args:
            mt5_connector: Obiekt konektora MT5
        """
        self.mt5_connector = mt5_connector
        self.last_refresh = {}  # instrument -> {timeframe -> timestamp}
        self.timeframe_intervals = {
            'M1': 10,         # Co 10 sekund
            'M5': 30,         # Co 30 sekund
            'M15': 60,        # Co 1 minutę
            'M30': 120,       # Co 2 minuty
            'H1': 300,        # Co 5 minut
            'H4': 600,        # Co 10 minut
            'D1': 1800,       # Co 30 minut
            'W1': 3600,       # Co godzinę
            'MN1': 7200       # Co 2 godziny
        }
        self.performance_stats = {
            'refresh_count': 0,
            'total_time': 0,
            'avg_time': 0,
            'min_time': float('inf'),
            'max_time': 0,
            'data_size': 0,
            'last_cpu_usage': 0,
            'last_memory_usage': 0,
            'errors': 0
        }
        self._lock = threading.Lock()
        
    def should_refresh(self, instrument: str, timeframe: str) -> bool:
        """
        Sprawdza, czy dane dla danego instrumentu i timeframe'u powinny być odświeżone.
        
        Args:
            instrument: Nazwa instrumentu
            timeframe: Timeframe
            
        Returns:
            bool: True jeśli dane powinny być odświeżone
        """
        now = datetime.now()
        
        with self._lock:
            if instrument not in self.last_refresh:
                self.last_refresh[instrument] = {}
                
            if timeframe not in self.last_refresh[instrument]:
                return True
                
            last_time = self.last_refresh[instrument][timeframe]
            interval = self.timeframe_intervals.get(timeframe, 60)  # Domyślnie co minutę
            
            return (now - last_time).total_seconds() >= interval
            
    def refresh_data(self, instrument: str, timeframes: List[str] = None) -> Dict[str, Any]:
        """
        Odświeża dane dla danego instrumentu i timeframe'u.
        
        Args:
            instrument: Nazwa instrumentu
            timeframes: Lista timeframe'ów do odświeżenia (domyślnie wszystkie)
            
        Returns:
            Dict: Słownik z wynikami odświeżania
        """
        result = {
            'success': True,
            'refreshed_data': {},
            'errors': {}
        }
        
        if timeframes is None:
            timeframes = list(self.timeframe_intervals.keys())
            
        for timeframe in timeframes:
            if self.should_refresh(instrument, timeframe):
                try:
                    start_time = time.time()
                    
                    # Tryb testowania wydajności co 10 odświeżeń
                    if self.performance_stats['refresh_count'] % 10 == 0:
                        self.performance_stats['last_cpu_usage'] = psutil.cpu_percent()
                        self.performance_stats['last_memory_usage'] = psutil.Process(os.getpid()).memory_info().rss / 1024 / 1024  # MB
                    
                    # Pobieranie danych
                    data = self.mt5_connector.get_historical_data(instrument, timeframe, count=100)
                    
                    # Obliczenie czasu wykonania
                    elapsed = time.time() - start_time
                    
                    with self._lock:
                        # Aktualizacja czasu odświeżenia
                        if instrument not in self.last_refresh:
                            self.last_refresh[instrument] = {}
                        self.last_refresh[instrument][timeframe] = datetime.now()
                        
                        # Aktualizacja statystyk
                        self.performance_stats['refresh_count'] += 1
                        self.performance_stats['total_time'] += elapsed
                        self.performance_stats['avg_time'] = self.performance_stats['total_time'] / self.performance_stats['refresh_count']
                        self.performance_stats['min_time'] = min(self.performance_stats['min_time'], elapsed)
                        self.performance_stats['max_time'] = max(self.performance_stats['max_time'], elapsed)
                        
                        if data is not None:
                            data_size = len(data) * 8 * 6  # Przybliżony rozmiar w bajtach (6 kolumn float64)
                            self.performance_stats['data_size'] += data_size
                    
                    logger.debug(f"Odświeżono dane dla {instrument} na timeframe {timeframe} w czasie {elapsed:.4f}s")
                    result['refreshed_data'][timeframe] = True
                    
                except Exception as e:
                    logger.error(f"Błąd podczas odświeżania danych dla {instrument} na timeframe {timeframe}: {e}")
                    with self._lock:
                        self.performance_stats['errors'] += 1
                    result['success'] = False
                    result['errors'][timeframe] = str(e)
        
        return result
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """
        Zwraca statystyki wydajności.
        
        Returns:
            Dict: Statystyki wydajności
        """
        with self._lock:
            return {**self.performance_stats}  # Kopia słownika
    
    def set_refresh_interval(self, timeframe: str, interval: int) -> bool:
        """
        Ustawia interwał odświeżania dla danego timeframe'u.
        
        Args:
            timeframe: Timeframe
            interval: Interwał w sekundach
            
        Returns:
            bool: True jeśli ustawienie się powiodło
        """
        if timeframe not in self.timeframe_intervals:
            logger.warning(f"Nieprawidłowy timeframe: {timeframe}")
            return False
            
        with self._lock:
            self.timeframe_intervals[timeframe] = interval
            
        logger.info(f"Ustawiono interwał odświeżania dla {timeframe} na {interval}s")
        return True
        
    def get_refresh_intervals(self) -> Dict[str, int]:
        """
        Zwraca aktualne interwały odświeżania.
        
        Returns:
            Dict: Interwały odświeżania
        """
        with self._lock:
            return {**self.timeframe_intervals}  # Kopia słownika

class Task:
    """Klasa reprezentująca pojedyncze zadanie w harmonogramie."""
    
    def __init__(
        self, 
        name: str, 
        interval: int, 
        function: Callable, 
        args: tuple = (), 
        kwargs: Dict[str, Any] = None,
        enabled: bool = True
    ):
        """
        Inicjalizacja zadania harmonogramu.
        
        Args:
            name: Nazwa zadania
            interval: Interwał wykonania w sekundach
            function: Funkcja do wykonania
            args: Argumenty pozycyjne funkcji
            kwargs: Argumenty nazwane funkcji
            enabled: Czy zadanie jest włączone
        """
        self.name = name
        self.interval = interval
        self.function = function
        self.args = args
        self.kwargs = kwargs or {}
        self.last_run = None
        self.next_run = datetime.now()
        self.enabled = enabled
        self.running = False
        self.error_count = 0
        self.success_count = 0
        
    def should_run(self) -> bool:
        """
        Sprawdza, czy zadanie powinno zostać uruchomione.
        
        Returns:
            bool: True jeśli zadanie powinno zostać uruchomione
        """
        return self.enabled and datetime.now() >= self.next_run and not self.running
    
    def run(self):
        """Uruchamia zadanie."""
        if not self.enabled:
            return
            
        self.running = True
        try:
            logger.debug(f"Uruchamianie zadania: {self.name}")
            self.function(*self.args, **self.kwargs)
            self.success_count += 1
            logger.debug(f"Zadanie {self.name} zakończone pomyślnie")
        except Exception as e:
            self.error_count += 1
            logger.error(f"Błąd podczas wykonywania zadania {self.name}: {e}")
            logger.debug(traceback.format_exc())
        finally:
            self.last_run = datetime.now()
            self.next_run = self.last_run + timedelta(seconds=self.interval)
            self.running = False
            
    def get_status(self) -> Dict[str, Any]:
        """
        Zwraca status zadania.
        
        Returns:
            Dict[str, Any]: Status zadania
        """
        return {
            "name": self.name,
            "interval": self.interval,
            "last_run": self.last_run.isoformat() if self.last_run else None,
            "next_run": self.next_run.isoformat(),
            "enabled": self.enabled,
            "running": self.running,
            "error_count": self.error_count,
            "success_count": self.success_count
        }


class Scheduler:
    """Harmonogram zadań dla AgentMT5."""
    
    _instance = None
    _lock = threading.Lock()
    
    @classmethod
    def get_instance(cls) -> 'Scheduler':
        """
        Zwraca singleton instancję harmonogramu.
        
        Returns:
            Scheduler: Instancja harmonogramu
        """
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def __init__(self):
        """Inicjalizacja harmonogramu zadań."""
        if Scheduler._instance is not None:
            raise RuntimeError("Użyj metody get_instance() zamiast tworzenia nowej instancji")
            
        self.tasks = {}
        self.run_thread = None
        self.running = False
        self.default_tasks_initialized = False
        
        # Inicjalizacja konektora MT5
        self.mt5_connector = MT5Connector()
        
        # Inicjalizacja generatora sygnałów
        self.signal_generator = SignalGenerator()
        
        # Inicjalizacja menedżera odświeżania danych
        self.data_refresh_manager = DataRefreshManager(self.mt5_connector)
        
        logger.info("Harmonogram zadań zainicjalizowany")
        
    def add_task(
        self, 
        name: str, 
        interval: int, 
        function: Callable, 
        args: tuple = (), 
        kwargs: Dict[str, Any] = None,
        enabled: bool = True
    ) -> bool:
        """
        Dodaje nowe zadanie do harmonogramu.
        
        Args:
            name: Nazwa zadania
            interval: Interwał wykonania w sekundach
            function: Funkcja do wykonania
            args: Argumenty pozycyjne funkcji
            kwargs: Argumenty nazwane funkcji
            enabled: Czy zadanie jest włączone
            
        Returns:
            bool: True jeśli zadanie zostało dodane
        """
        with self._lock:
            if name in self.tasks:
                logger.warning(f"Zadanie o nazwie '{name}' już istnieje")
                return False
                
            self.tasks[name] = Task(name, interval, function, args, kwargs, enabled)
            logger.info(f"Dodano zadanie '{name}' z interwałem {interval}s")
            return True
            
    def remove_task(self, name: str) -> bool:
        """
        Usuwa zadanie z harmonogramu.
        
        Args:
            name: Nazwa zadania
            
        Returns:
            bool: True jeśli zadanie zostało usunięte
        """
        with self._lock:
            if name not in self.tasks:
                logger.warning(f"Zadanie o nazwie '{name}' nie istnieje")
                return False
                
            del self.tasks[name]
            logger.info(f"Usunięto zadanie '{name}'")
            return True
            
    def enable_task(self, name: str) -> bool:
        """
        Włącza zadanie.
        
        Args:
            name: Nazwa zadania
            
        Returns:
            bool: True jeśli zadanie zostało włączone
        """
        with self._lock:
            if name not in self.tasks:
                logger.warning(f"Zadanie o nazwie '{name}' nie istnieje")
                return False
                
            self.tasks[name].enabled = True
            logger.info(f"Włączono zadanie '{name}'")
            return True
            
    def disable_task(self, name: str) -> bool:
        """
        Wyłącza zadanie.
        
        Args:
            name: Nazwa zadania
            
        Returns:
            bool: True jeśli zadanie zostało wyłączone
        """
        with self._lock:
            if name not in self.tasks:
                logger.warning(f"Zadanie o nazwie '{name}' nie istnieje")
                return False
                
            self.tasks[name].enabled = False
            logger.info(f"Wyłączono zadanie '{name}'")
            return True
            
    def get_task_status(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Zwraca status zadania.
        
        Args:
            name: Nazwa zadania
            
        Returns:
            Dict[str, Any]: Status zadania lub None jeśli zadanie nie istnieje
        """
        with self._lock:
            if name not in self.tasks:
                logger.warning(f"Zadanie o nazwie '{name}' nie istnieje")
                return None
                
            return self.tasks[name].get_status()
            
    def get_all_tasks_status(self) -> Dict[str, Dict[str, Any]]:
        """
        Zwraca status wszystkich zadań.
        
        Returns:
            Dict[str, Dict[str, Any]]: Status wszystkich zadań
        """
        with self._lock:
            return {name: task.get_status() for name, task in self.tasks.items()}
            
    def start(self):
        """Uruchamia harmonogram zadań."""
        with self._lock:
            if self.running:
                logger.warning("Harmonogram zadań już działa")
                return
                
            self.running = True
            self.run_thread = threading.Thread(target=self._run)
            self.run_thread.daemon = True
            self.run_thread.start()
            logger.info("Harmonogram zadań uruchomiony")
            
    def stop(self):
        """Zatrzymuje harmonogram zadań."""
        with self._lock:
            if not self.running:
                logger.warning("Harmonogram zadań już jest zatrzymany")
                return
                
            self.running = False
            if self.run_thread:
                self.run_thread.join(timeout=5.0)
                self.run_thread = None
            logger.info("Harmonogram zadań zatrzymany")
            
    def _run(self):
        """Główna pętla harmonogramu zadań."""
        logger.info("Rozpoczęcie głównej pętli harmonogramu zadań")
        
        while self.running:
            try:
                with self._lock:
                    # Wykonanie zadań, które powinny zostać uruchomione
                    for name, task in self.tasks.items():
                        if task.should_run():
                            # Uruchomienie zadania w osobnym wątku
                            thread = threading.Thread(target=task.run)
                            thread.daemon = True
                            thread.start()
                
                # Opóźnienie między sprawdzaniem zadań
                time.sleep(1)
            except Exception as e:
                logger.error(f"Błąd w głównej pętli harmonogramu zadań: {e}")
                logger.debug(traceback.format_exc())
                time.sleep(5)  # Dłuższe opóźnienie w przypadku błędu
                
        logger.info("Zakończenie głównej pętli harmonogramu zadań")
        
    def initialize_default_tasks(self):
        """Inicjalizacja domyślnych zadań harmonogramu."""
        if self.default_tasks_initialized:
            return
        
        # Instrumenty do monitorowania
        instruments = ["EURUSD", "GBPUSD", "USDJPY", "GOLD", "SILVER"]
        
        # Dodawanie zadań generowania sygnałów dla każdego instrumentu
        for instrument in instruments:
            task_name = f"generate_signal_{instrument}"
            # Losowe przesunięcie czasu wykonania, aby uniknąć jednoczesnego wykonania wszystkich zadań
            interval = 60 + random.randint(-5, 5)  # 55-65 sekund
            self.add_task(task_name, interval, self._generate_signal_task, args=(instrument,))
        
        # Zadanie aktualizacji danych rynkowych
        self.add_task("update_market_data", 30, self._update_market_data_task, args=(instruments,))
        
        # Zadanie odświeżania danych historycznych
        self.add_task("refresh_historical_data", 120, self._refresh_historical_data_task, args=(instruments,))
        
        # Zadanie sprawdzania wydajności
        self.add_task("check_performance", 300, self._check_performance_task)
        
        self.default_tasks_initialized = True
        logger.info("Zainicjalizowano domyślne zadania harmonogramu")
        
    def _generate_signal_task(self, instrument: str):
        """
        Zadanie generowania sygnału handlowego.
        
        Args:
            instrument: Symbol instrumentu
        """
        try:
            # Pobranie danych rynkowych
            market_data = self.mt5_connector.get_symbol_info(instrument)
            
            if not market_data:
                logger.warning(f"Nie udało się pobrać danych rynkowych dla {instrument}")
                return
                
            # Generowanie sygnału
            signal = self.signal_generator.generate_signal(instrument, market_data)
            
            if signal:
                logger.info(f"Wygenerowano nowy sygnał dla {instrument}: {signal.direction.upper()} " +
                           f"z pewnością {signal.confidence:.2f}")
            else:
                logger.debug(f"Nie wygenerowano sygnału dla {instrument}")
                
        except Exception as e:
            logger.error(f"Błąd podczas generowania sygnału dla {instrument}: {e}")
            logger.debug(traceback.format_exc())
            
    def _update_market_data_task(self, instruments: List[str]):
        """
        Zadanie aktualizacji danych rynkowych.
        
        Args:
            instruments: Lista instrumentów
        """
        try:
            for instrument in instruments:
                # Wymuszenie odświeżenia danych rynkowych
                self.mt5_connector.invalidate_cache('market_data', instrument)
                
                # Pobranie danych rynkowych
                market_data = self.mt5_connector.get_symbol_info(instrument)
                
                if market_data:
                    logger.debug(f"Zaktualizowano dane rynkowe dla {instrument}: " +
                               f"Bid={market_data['bid']}, Ask={market_data['ask']}")
                else:
                    logger.warning(f"Nie udało się zaktualizować danych rynkowych dla {instrument}")
                    
        except Exception as e:
            logger.error(f"Błąd podczas aktualizacji danych rynkowych: {e}")
            logger.debug(traceback.format_exc())
            
    def _refresh_historical_data_task(self, instruments: List[str]):
        """
        Zadanie odświeżania danych historycznych.
        
        Args:
            instruments: Lista instrumentów
        """
        try:
            for instrument in instruments:
                # Odświeżenie danych dla najpopularniejszych timeframe'ów
                timeframes = ["M1", "M5", "M15", "H1", "D1"]
                result = self.data_refresh_manager.refresh_data(instrument, timeframes)
                
                if result['success']:
                    logger.debug(f"Odświeżono dane historyczne dla {instrument} na timeframe'ach: {', '.join(result['refreshed_data'].keys())}")
                else:
                    error_tfs = ', '.join(result['errors'].keys())
                    logger.warning(f"Błędy podczas odświeżania danych dla {instrument} na timeframe'ach: {error_tfs}")
                    
        except Exception as e:
            logger.error(f"Błąd podczas odświeżania danych historycznych: {e}")
            logger.debug(traceback.format_exc())
            
    def _check_performance_task(self):
        """
        Zadanie sprawdzania wydajności.
        """
        try:
            stats = self.data_refresh_manager.get_performance_stats()
            
            # Formatowanie wyniku do logów
            performance_summary = (
                f"Statystyki wydajności pobierania danych:\n"
                f"Liczba odświeżeń: {stats['refresh_count']}\n"
                f"Średni czas: {stats['avg_time']:.4f}s\n"
                f"Min. czas: {stats['min_time']:.4f}s\n"
                f"Max. czas: {stats['max_time']:.4f}s\n"
                f"Przybliżony rozmiar danych: {stats['data_size'] / 1024 / 1024:.2f} MB\n"
                f"Ostatnie użycie CPU: {stats['last_cpu_usage']:.2f}%\n"
                f"Ostatnie użycie pamięci: {stats['last_memory_usage']:.2f} MB\n"
                f"Liczba błędów: {stats['errors']}"
            )
            
            logger.info(performance_summary)
            
        except Exception as e:
            logger.error(f"Błąd podczas sprawdzania wydajności: {e}")
            logger.debug(traceback.format_exc())
    
    def get_data_refresh_manager(self) -> DataRefreshManager:
        """
        Zwraca instancję menedżera odświeżania danych.
        
        Returns:
            DataRefreshManager: Menedżer odświeżania danych
        """
        return self.data_refresh_manager


# Singleton instancja harmonogramu
def get_scheduler() -> Scheduler:
    """
    Funkcja pomocnicza do uzyskania instancji harmonogramu.
    
    Returns:
        Scheduler: Instancja harmonogramu
    """
    return Scheduler.get_instance()


if __name__ == "__main__":
    # Konfiguracja loggera dla uruchamiania jako samodzielny skrypt
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Uruchomienie harmonogramu
    scheduler = get_scheduler()
    scheduler.initialize_default_tasks()
    scheduler.start()
    
    try:
        # Utrzymanie działania programu
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        # Zatrzymanie harmonogramu przy naciśnięciu Ctrl+C
        scheduler.stop()
        print("Harmonogram zatrzymany.") 