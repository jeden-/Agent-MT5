#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Test długoterminowej stabilności agenta handlowego.

Ten test weryfikuje długoterminową stabilność agenta handlowego, w tym:
1. Odporność na błędy i awarie
2. Zarządzanie zasobami (pamięć, CPU)
3. Stabilność połączenia z MT5
4. Odzyskiwanie po utracie połączenia
5. Zarządzanie długotrwałymi sesjami handlowymi
"""

import sys
import os
import asyncio
import logging
import json
import time
import threading
import random
import psutil
import unittest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

# Dodanie głównego katalogu projektu do PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Konfiguracja loggera
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)

logger = logging.getLogger(__name__)

class TestAgentLongterm(unittest.TestCase):
    """Klasa testowa dla długoterminowej stabilności agenta."""
    
    @classmethod
    def setUpClass(cls):
        """Przygotowanie środowiska testowego przed wszystkimi testami."""
        logger.info("Przygotowanie środowiska testowego dla testów długoterminowych...")
        
        # Ustawienie zmiennych środowiskowych dla testów
        os.environ["MT5_ACCOUNT"] = "12345678"
        os.environ["MT5_PASSWORD"] = "test_password"
        os.environ["MT5_SERVER"] = "MetaQuotes-Demo"
        os.environ["MT5_PATH"] = "C:\\Program Files\\MetaTrader 5\\terminal64.exe"
        
        # Inicjalizacja mocków
        cls.setup_mocks()
        
        # Inicjalizacja zmiennych dla testów
        cls.test_duration = 60  # Czas trwania testu w sekundach (w rzeczywistości powinno być dłużej)
        cls.check_interval = 1  # Interwał sprawdzania w sekundach
        cls.memory_threshold = 200 * 1024 * 1024  # 200 MB
        cls.cpu_threshold = 50  # 50% CPU
    
    @classmethod
    def tearDownClass(cls):
        """Czyszczenie po wszystkich testach."""
        logger.info("Czyszczenie środowiska testowego...")
        
        # Usunięcie zmiennych środowiskowych
        for var in ["MT5_ACCOUNT", "MT5_PASSWORD", "MT5_SERVER", "MT5_PATH"]:
            if var in os.environ:
                del os.environ[var]
    
    @classmethod
    def setup_mocks(cls):
        """Konfiguracja mocków dla testów."""
        # Tutaj będziemy konfigurować mocki dla różnych komponentów
        pass
    
    def test_memory_usage(self):
        """Test zużycia pamięci podczas długotrwałej pracy agenta."""
        logger.info("Test zużycia pamięci podczas długotrwałej pracy agenta...")
        
        # Inicjalizacja agenta
        from src.agent_controller import get_agent_controller
        agent_controller = get_agent_controller()
        
        # Konfiguracja agenta
        config = {
            "mode": "observation",
            "risk_limits": {
                "max_positions": 3,
                "max_risk_per_trade": 0.01,
                "max_daily_risk": 0.05
            },
            "instruments": {
                "EURUSD": {
                    "active": True,
                    "max_lot_size": 0.2
                },
                "USDJPY": {
                    "active": True,
                    "max_lot_size": 0.1
                }
            }
        }
        agent_controller.update_config(config)
        
        # Uruchomienie agenta
        agent_controller.start_agent(mode="observation")
        
        # Monitorowanie zużycia pamięci
        start_time = time.time()
        memory_usage = []
        
        try:
            while time.time() - start_time < self.test_duration:
                # Pobranie zużycia pamięci
                process = psutil.Process(os.getpid())
                memory_info = process.memory_info()
                memory_usage.append(memory_info.rss)
                
                # Logowanie zużycia pamięci
                logger.info(f"Zużycie pamięci: {memory_info.rss / (1024 * 1024):.2f} MB")
                
                # Sprawdzenie, czy zużycie pamięci nie przekracza progu
                self.assertLess(memory_info.rss, self.memory_threshold, 
                               f"Zużycie pamięci przekroczyło próg {self.memory_threshold / (1024 * 1024)} MB")
                
                # Oczekiwanie na następne sprawdzenie
                time.sleep(self.check_interval)
        
        finally:
            # Zatrzymanie agenta
            agent_controller.stop_agent()
        
        # Analiza zużycia pamięci
        if memory_usage:
            avg_memory = sum(memory_usage) / len(memory_usage)
            max_memory = max(memory_usage)
            logger.info(f"Średnie zużycie pamięci: {avg_memory / (1024 * 1024):.2f} MB")
            logger.info(f"Maksymalne zużycie pamięci: {max_memory / (1024 * 1024):.2f} MB")
    
    def test_cpu_usage(self):
        """Test zużycia CPU podczas długotrwałej pracy agenta."""
        logger.info("Test zużycia CPU podczas długotrwałej pracy agenta...")
        
        # Inicjalizacja agenta
        from src.agent_controller import get_agent_controller
        agent_controller = get_agent_controller()
        
        # Konfiguracja agenta
        config = {
            "mode": "observation",
            "risk_limits": {
                "max_positions": 3,
                "max_risk_per_trade": 0.01,
                "max_daily_risk": 0.05
            },
            "instruments": {
                "EURUSD": {
                    "active": True,
                    "max_lot_size": 0.2
                },
                "USDJPY": {
                    "active": True,
                    "max_lot_size": 0.1
                }
            }
        }
        agent_controller.update_config(config)
        
        # Uruchomienie agenta
        agent_controller.start_agent(mode="observation")
        
        # Monitorowanie zużycia CPU
        start_time = time.time()
        cpu_usage = []
        
        try:
            while time.time() - start_time < self.test_duration:
                # Pobranie zużycia CPU
                process = psutil.Process(os.getpid())
                cpu_percent = process.cpu_percent(interval=1)
                cpu_usage.append(cpu_percent)
                
                # Logowanie zużycia CPU
                logger.info(f"Zużycie CPU: {cpu_percent:.2f}%")
                
                # Sprawdzenie, czy zużycie CPU nie przekracza progu
                self.assertLess(cpu_percent, self.cpu_threshold, 
                               f"Zużycie CPU przekroczyło próg {self.cpu_threshold}%")
                
                # Oczekiwanie na następne sprawdzenie
                time.sleep(self.check_interval)
        
        finally:
            # Zatrzymanie agenta
            agent_controller.stop_agent()
        
        # Analiza zużycia CPU
        if cpu_usage:
            avg_cpu = sum(cpu_usage) / len(cpu_usage)
            max_cpu = max(cpu_usage)
            logger.info(f"Średnie zużycie CPU: {avg_cpu:.2f}%")
            logger.info(f"Maksymalne zużycie CPU: {max_cpu:.2f}%")
    
    def test_connection_stability(self):
        """Test stabilności połączenia z MT5."""
        logger.info("Test stabilności połączenia z MT5...")
        
        # Inicjalizacja agenta
        from src.agent_controller import get_agent_controller
        agent_controller = get_agent_controller()
        
        # Konfiguracja agenta
        config = {
            "mode": "observation",
            "risk_limits": {
                "max_positions": 3,
                "max_risk_per_trade": 0.01,
                "max_daily_risk": 0.05
            },
            "instruments": {
                "EURUSD": {
                    "active": True,
                    "max_lot_size": 0.2
                },
                "USDJPY": {
                    "active": True,
                    "max_lot_size": 0.1
                }
            }
        }
        agent_controller.update_config(config)
        
        # Uruchomienie agenta
        agent_controller.start_agent(mode="observation")
        
        # Symulacja utraty połączenia
        def simulate_connection_loss():
            time.sleep(10)  # Oczekiwanie 10 sekund przed symulacją utraty połączenia
            logger.info("Symulacja utraty połączenia z MT5...")
            
            # Symulacja utraty połączenia przez podmianę metody is_connected
            if hasattr(agent_controller.trading_integration.trading_service, 'is_connected'):
                original_is_connected = agent_controller.trading_integration.trading_service.is_connected
                agent_controller.trading_integration.trading_service.is_connected = lambda: False
                
                # Przywrócenie oryginalnej metody po 5 sekundach
                time.sleep(5)
                logger.info("Przywracanie połączenia z MT5...")
                agent_controller.trading_integration.trading_service.is_connected = original_is_connected
        
        # Uruchomienie symulacji utraty połączenia w osobnym wątku
        connection_thread = threading.Thread(target=simulate_connection_loss)
        connection_thread.daemon = True
        connection_thread.start()
        
        # Monitorowanie statusu połączenia
        start_time = time.time()
        connection_status = []
        
        try:
            while time.time() - start_time < self.test_duration:
                # Pobranie statusu agenta
                status = agent_controller.get_status()
                
                # Logowanie statusu
                logger.info(f"Status agenta: {status['status']}")
                
                # Zapisanie statusu
                connection_status.append(status['status'])
                
                # Oczekiwanie na następne sprawdzenie
                time.sleep(self.check_interval)
        
        finally:
            # Zatrzymanie agenta
            agent_controller.stop_agent()
        
        # Sprawdzenie, czy agent odzyskał połączenie
        self.assertEqual(connection_status[-1], "running", "Agent nie odzyskał połączenia po symulowanej utracie")
    
    def test_error_recovery(self):
        """Test odzyskiwania po błędach."""
        logger.info("Test odzyskiwania po błędach...")
        
        # Inicjalizacja agenta
        from src.agent_controller import get_agent_controller
        agent_controller = get_agent_controller()
        
        # Konfiguracja agenta
        config = {
            "mode": "observation",
            "risk_limits": {
                "max_positions": 3,
                "max_risk_per_trade": 0.01,
                "max_daily_risk": 0.05
            },
            "instruments": {
                "EURUSD": {
                    "active": True,
                    "max_lot_size": 0.2
                },
                "USDJPY": {
                    "active": True,
                    "max_lot_size": 0.1
                }
            }
        }
        agent_controller.update_config(config)
        
        # Uruchomienie agenta
        agent_controller.start_agent(mode="observation")
        
        # Symulacja błędów
        def simulate_errors():
            time.sleep(5)  # Oczekiwanie 5 sekund przed symulacją błędów
            
            for i in range(3):  # Symulacja 3 błędów
                logger.info(f"Symulacja błędu {i+1}/3...")
                
                # Symulacja błędu przez wywołanie wyjątku w metodzie _process_instrument
                original_process_instrument = agent_controller._process_instrument
                
                def mock_process_instrument(instrument):
                    if random.random() < 0.5:  # 50% szans na błąd
                        raise Exception(f"Symulowany błąd w przetwarzaniu instrumentu {instrument}")
                    return original_process_instrument(instrument)
                
                agent_controller._process_instrument = mock_process_instrument
                
                # Oczekiwanie 5 sekund przed przywróceniem oryginalnej metody
                time.sleep(5)
                agent_controller._process_instrument = original_process_instrument
                
                # Oczekiwanie 5 sekund przed następnym błędem
                time.sleep(5)
        
        # Uruchomienie symulacji błędów w osobnym wątku
        error_thread = threading.Thread(target=simulate_errors)
        error_thread.daemon = True
        error_thread.start()
        
        # Monitorowanie statusu agenta
        start_time = time.time()
        agent_status = []
        
        try:
            while time.time() - start_time < self.test_duration:
                # Pobranie statusu agenta
                status = agent_controller.get_status()
                
                # Logowanie statusu
                logger.info(f"Status agenta: {status['status']}")
                
                # Zapisanie statusu
                agent_status.append(status['status'])
                
                # Oczekiwanie na następne sprawdzenie
                time.sleep(self.check_interval)
        
        finally:
            # Zatrzymanie agenta
            agent_controller.stop_agent()
        
        # Sprawdzenie, czy agent pozostał uruchomiony pomimo błędów
        self.assertEqual(agent_status[-1], "running", "Agent nie pozostał uruchomiony po symulowanych błędach")
    
    def test_long_session(self):
        """Test długiej sesji handlowej."""
        logger.info("Test długiej sesji handlowej...")
        
        # Inicjalizacja agenta
        from src.agent_controller import get_agent_controller
        agent_controller = get_agent_controller()
        
        # Konfiguracja agenta
        config = {
            "mode": "observation",
            "risk_limits": {
                "max_positions": 3,
                "max_risk_per_trade": 0.01,
                "max_daily_risk": 0.05
            },
            "instruments": {
                "EURUSD": {
                    "active": True,
                    "max_lot_size": 0.2
                },
                "USDJPY": {
                    "active": True,
                    "max_lot_size": 0.1
                }
            }
        }
        agent_controller.update_config(config)
        
        # Uruchomienie agenta
        agent_controller.start_agent(mode="observation")
        
        # Symulacja długiej sesji handlowej
        start_time = time.time()
        session_duration = self.test_duration  # W rzeczywistości powinno być dłużej, np. 8 godzin
        
        try:
            while time.time() - start_time < session_duration:
                # Pobranie statusu agenta
                status = agent_controller.get_status()
                
                # Logowanie statusu
                logger.info(f"Status agenta: {status['status']}")
                logger.info(f"Czas pracy: {time.time() - start_time:.2f} s")
                
                # Sprawdzenie, czy agent jest nadal uruchomiony
                self.assertEqual(status['status'], "running", "Agent zatrzymał się podczas długiej sesji")
                
                # Oczekiwanie na następne sprawdzenie
                time.sleep(self.check_interval)
        
        finally:
            # Zatrzymanie agenta
            agent_controller.stop_agent()
        
        # Sprawdzenie, czy agent działał przez cały czas sesji
        elapsed_time = time.time() - start_time
        logger.info(f"Całkowity czas sesji: {elapsed_time:.2f} s")
        self.assertGreaterEqual(elapsed_time, session_duration * 0.9, 
                               f"Agent nie działał przez wymagany czas sesji ({session_duration} s)")

async def run_tests():
    """Uruchamia testy asynchronicznie."""
    # Tutaj możemy uruchomić testy asynchroniczne, jeśli są potrzebne
    pass

if __name__ == "__main__":
    # Uruchomienie testów asynchronicznych
    asyncio.run(run_tests())
    
    # Uruchomienie testów jednostkowych
    unittest.main(argv=['first-arg-is-ignored'], exit=False) 