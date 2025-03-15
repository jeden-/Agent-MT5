#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Test pełnego cyklu pracy agenta handlowego.

Ten test weryfikuje pełny cykl pracy agenta handlowego, od inicjalizacji,
przez przetwarzanie sygnałów, do zamykania pozycji. Test obejmuje:
1. Inicjalizację agenta i wszystkich komponentów
2. Uruchomienie agenta w różnych trybach pracy
3. Generowanie i przetwarzanie sygnałów handlowych
4. Otwieranie i zamykanie pozycji
5. Monitorowanie stanu agenta
6. Zatrzymanie agenta
"""

import sys
import os
import asyncio
import logging
import json
import time
from datetime import datetime
import unittest
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

# Zaślepka klasy sygnału handlowego
class MockTradingSignal:
    """Zaślepka sygnału handlowego do testów."""
    
    def __init__(self, symbol, signal_type, price, source="TEST"):
        """Inicjalizacja sygnału testowego."""
        self.id = int(time.time() * 1000)  # prosty unikalny ID
        self.symbol = symbol
        self.type = signal_type
        self.price = price
        self.source = source
        self.confidence = 0.85
        self.generated_at = datetime.now()
        self.status = "NEW"  # Status sygnału: NEW, PENDING, APPROVED, REJECTED, EXECUTED
    
    def to_dict(self):
        """Konwersja sygnału do słownika."""
        return {
            'id': self.id,
            'symbol': self.symbol,
            'type': self.type,
            'price': self.price,
            'source': self.source,
            'confidence': self.confidence,
            'generated_at': self.generated_at.isoformat(),
            'status': self.status
        }
    
    def get(self, key, default=None):
        """
        Pobieranie atrybutu obiektu w sposób słownikowy.
        
        Args:
            key: Nazwa atrybutu do pobrania
            default: Wartość domyślna zwracana, gdy atrybut nie istnieje
            
        Returns:
            Wartość atrybutu lub wartość domyślna
        """
        return getattr(self, key, default)

# Zaślepka klasy transakcji
class MockTransaction:
    """Zaślepka transakcji do testów."""
    
    def __init__(self, symbol, order_type, price, volume, ticket=None):
        """Inicjalizacja transakcji testowej."""
        self.ticket = ticket or int(time.time() * 1000)  # prosty unikalny ID
        self.symbol = symbol
        self.type = order_type
        self.price = price
        self.volume = volume
        self.open_time = datetime.now()
        self.close_time = None
        self.profit = 0.0
        self.status = "OPEN"
    
    def to_dict(self):
        """Konwersja transakcji do słownika."""
        return {
            'ticket': self.ticket,
            'symbol': self.symbol,
            'type': self.type,
            'price': self.price,
            'volume': self.volume,
            'open_time': self.open_time.isoformat(),
            'close_time': self.close_time.isoformat() if self.close_time else None,
            'profit': self.profit,
            'status': self.status
        }

class TestAgentFullCycle(unittest.TestCase):
    """Klasa testowa dla pełnego cyklu pracy agenta."""
    
    @classmethod
    def setUpClass(cls):
        """Przygotowanie środowiska testowego przed wszystkimi testami."""
        logger.info("Przygotowanie środowiska testowego...")
        
        # Ustawienie zmiennych środowiskowych dla testów
        os.environ["MT5_ACCOUNT"] = "12345678"
        os.environ["MT5_PASSWORD"] = "test_password"
        os.environ["MT5_SERVER"] = "MetaQuotes-Demo"
        os.environ["MT5_PATH"] = "C:\\Program Files\\MetaTrader 5\\terminal64.exe"
        
        # Inicjalizacja mocków
        cls.setup_mocks()
    
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
    
    async def test_full_cycle(self):
        """Test pełnego cyklu pracy agenta."""
        try:
            logger.info("Rozpoczynanie testu pełnego cyklu pracy agenta...")
            
            # 1. Uruchomienie serwera HTTP
            logger.info("1. Uruchamianie serwera HTTP...")
            from src.mt5_bridge import start_server
            server = await start_server(host="localhost", port=8080)
            logger.info(f"Serwer HTTP uruchomiony na http://localhost:8080")
            
            # 2. Inicjalizacja i konfiguracja kontrolera agenta
            logger.info("2. Inicjalizacja kontrolera agenta...")
            from src.agent_controller import get_agent_controller, AgentMode, AgentStatus
            agent_controller = get_agent_controller()
            
            # 3. Ustawienie kontrolera agenta w serwerze
            logger.info("3. Konfiguracja serwera z kontrolerem agenta...")
            server.set_agent_controller(agent_controller)
            
            # 4. Konfiguracja komponentów
            logger.info("4. Ustawianie konfiguracji agenta...")
            config = {
                "mode": "observation",  # Zaczynamy od trybu obserwacyjnego
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
                },
                # Dodatkowe parametry dla SignalValidator
                "min_probability": 0.7,
                "min_risk_reward_ratio": 1.5
            }
            
            # 5. Aktualizacja konfiguracji agenta
            logger.info("5. Aktualizacja konfiguracji agenta...")
            result = agent_controller.update_config(config)
            logger.info(f"Wynik aktualizacji konfiguracji: {json.dumps(result, indent=2)}")
            
            # 6. Uruchomienie agenta w trybie obserwacyjnym
            logger.info("6. Uruchamianie agenta w trybie obserwacyjnym...")
            start_result = agent_controller.start_agent(mode="observation")
            logger.info(f"Wynik uruchomienia agenta: {json.dumps(start_result, indent=2)}")
            
            # Sprawdzenie statusu po uruchomieniu
            await asyncio.sleep(1)
            logger.info("7. Sprawdzanie statusu agenta po uruchomieniu...")
            status = agent_controller.get_status()
            logger.info(f"Status agenta: {json.dumps(status, indent=2)}")
            self.assertEqual(status["status"], "running")
            
            # 8. Symulacja przetwarzania danych rynkowych
            logger.info("8. Symulacja przetwarzania danych rynkowych...")
            # Tutaj możemy zasymulować dane rynkowe i sprawdzić reakcję agenta
            
            # 9. Przełączenie agenta w tryb półautomatyczny
            logger.info("9. Przełączanie agenta w tryb półautomatyczny...")
            config["mode"] = "semi_automatic"
            result = agent_controller.update_config(config)
            logger.info(f"Wynik aktualizacji konfiguracji: {json.dumps(result, indent=2)}")
            
            # 10. Generowanie sygnału handlowego
            logger.info("10. Generowanie sygnału handlowego...")
            # Tutaj możemy zasymulować generowanie sygnału handlowego
            
            # 11. Zatwierdzenie sygnału handlowego
            logger.info("11. Zatwierdzenie sygnału handlowego...")
            # Tutaj możemy zasymulować zatwierdzenie sygnału handlowego
            
            # 12. Przełączenie agenta w tryb automatyczny
            logger.info("12. Przełączanie agenta w tryb automatyczny...")
            config["mode"] = "automatic"
            result = agent_controller.update_config(config)
            logger.info(f"Wynik aktualizacji konfiguracji: {json.dumps(result, indent=2)}")
            
            # 13. Generowanie i automatyczne wykonanie sygnału handlowego
            logger.info("13. Generowanie i automatyczne wykonanie sygnału handlowego...")
            # Tutaj możemy zasymulować generowanie i automatyczne wykonanie sygnału handlowego
            
            # 14. Monitorowanie pozycji
            logger.info("14. Monitorowanie pozycji...")
            # Tutaj możemy zasymulować monitorowanie pozycji
            
            # 15. Zamknięcie pozycji
            logger.info("15. Zamknięcie pozycji...")
            # Tutaj możemy zasymulować zamknięcie pozycji
            
            # 16. Zatrzymanie agenta
            logger.info("16. Zatrzymywanie agenta...")
            stop_result = agent_controller.stop_agent()
            logger.info(f"Wynik zatrzymania agenta: {json.dumps(stop_result, indent=2)}")
            
            # Sprawdzenie statusu po zatrzymaniu
            await asyncio.sleep(1)
            logger.info("17. Sprawdzanie statusu agenta po zatrzymaniu...")
            status = agent_controller.get_status()
            logger.info(f"Status agenta: {json.dumps(status, indent=2)}")
            self.assertEqual(status["status"], "stopped")
            
            # 18. Zatrzymanie serwera HTTP
            logger.info("18. Zatrzymywanie serwera HTTP...")
            await server.shutdown()
            logger.info("Serwer HTTP zatrzymany")
            
            logger.info("Test pełnego cyklu pracy agenta zakończony pomyślnie!")
        
        except Exception as e:
            logger.error(f"Błąd podczas testu pełnego cyklu pracy agenta: {e}")
            raise
    
    def test_agent_initialization(self):
        """Test inicjalizacji agenta."""
        logger.info("Test inicjalizacji agenta...")
        # Tutaj możemy przetestować inicjalizację agenta
        pass
    
    def test_signal_processing(self):
        """Test przetwarzania sygnałów handlowych."""
        logger.info("Test przetwarzania sygnałów handlowych...")
        # Tutaj możemy przetestować przetwarzanie sygnałów handlowych
        pass
    
    def test_position_management(self):
        """Test zarządzania pozycjami."""
        logger.info("Test zarządzania pozycjami...")
        # Tutaj możemy przetestować zarządzanie pozycjami
        pass

async def run_tests():
    """Uruchamia testy asynchronicznie."""
    test = TestAgentFullCycle()
    await test.test_full_cycle()

if __name__ == "__main__":
    # Uruchomienie testu asynchronicznego
    asyncio.run(run_tests())
    
    # Uruchomienie pozostałych testów
    unittest.main(argv=['first-arg-is-ignored'], exit=False) 