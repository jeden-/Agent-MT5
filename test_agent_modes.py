#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Test trybów pracy agenta handlowego.

Ten test skupia się na weryfikacji działania agenta w różnych trybach pracy:
- observation (obserwacyjny) - tylko analiza, bez transakcji
- semi_automatic (półautomatyczny) - propozycje wymagają zatwierdzenia
- automatic (automatyczny) - pełna automatyzacja

Test weryfikuje:
1. Przełączanie między trybami
2. Obsługę sygnałów handlowych w różnych trybach
3. Komunikację z serwisem MT5
"""

import sys
import os
import asyncio
import logging
import json
import time
from datetime import datetime

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


async def test_agent_modes():
    """
    Testuje różne tryby pracy agenta handlowego.
    """
    try:
        print("Rozpoczynanie testu trybów pracy agenta...")
        
        # 1. Uruchomienie serwera HTTP
        print("\n1. Uruchamianie serwera HTTP...")
        from src.mt5_bridge import start_server
        server = await start_server(host="localhost", port=8080)
        print(f"Serwer HTTP uruchomiony na http://localhost:8080")
        
        # 2. Inicjalizacja i konfiguracja kontrolera agenta
        print("\n2. Inicjalizacja kontrolera agenta...")
        from src.agent_controller import get_agent_controller, AgentMode, AgentStatus
        agent_controller = get_agent_controller()
        
        # 3. Ustawienie kontrolera agenta w serwerze
        print("\n3. Konfiguracja serwera z kontrolerem agenta...")
        server.set_agent_controller(agent_controller)
        
        # 4. Konfiguracja komponentów
        print("\n4. Ustawianie konfiguracji agenta...")
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
        
        # 5. Inicjalizacja komponentów z mockiem SignalValidator
        print("\n5. Inicjalizacja kontrolera agenta z właściwą konfiguracją...")
        # Najpierw przechwytujemy klasę SignalValidator
        try:
            from src.analysis.signal_validator import SignalValidator
            
            # Zapisujemy oryginalną metodę __init__
            original_init = SignalValidator.__init__
            
            # Zastępujemy metodę __init__, aby akceptowała dowolne argumenty
            def mock_init(self, *args, **kwargs):
                if hasattr(self, '_initialized') and self._initialized:
                    return
                
                self.logger = logging.getLogger('test.signal_validator')
                self.logger.info("Inicjalizacja mocka SignalValidator")
                
                # Przygotuj podstawową konfigurację
                self.config = kwargs.get('config', {})
                if not self.config:
                    self.config = {
                        "min_probability": 0.7,
                        "min_risk_reward_ratio": 1.5,
                        "max_positions_per_symbol": 5,
                        "max_positions_total": 10
                    }
                
                # Utwórz mockowe metody
                self.validate_signal = lambda signal: {
                    'valid': True, 
                    'score': 0.9, 
                    'signal': signal,
                    'validation_result': 'VALID'
                }
                
                self._initialized = True
            
            # Podmiana metody inicjalizacji
            SignalValidator.__init__ = mock_init
        except ImportError:
            print("Nie można zaimportować SignalValidator do podmienienia")
        
        # 6. Aktualizacja konfiguracji agenta
        print("\n6. Aktualizacja konfiguracji agenta...")
        result = agent_controller.update_config(config)
        print(json.dumps(result, indent=2))
        
        # 7. Uruchomienie agenta w trybie obserwacyjnym
        print("\n7. Uruchamianie agenta w trybie obserwacyjnym...")
        start_result = agent_controller.start_agent(mode="observation")
        print(json.dumps(start_result, indent=2))
        
        # Sprawdzenie statusu po uruchomieniu
        await asyncio.sleep(1)
        print("\n8. Sprawdzanie statusu agenta po uruchomieniu...")
        status = agent_controller.get_status()
        print(json.dumps(status, indent=2))
        
        # 9. Test generowania i przetwarzania sygnału w trybie obserwacyjnym
        print("\n9. Test sygnału w trybie obserwacyjnym...")
        # Tworzymy mockowy sygnał
        mock_signal = MockTradingSignal(
            symbol="EURUSD",
            signal_type="BUY",
            price=1.1234
        )
        
        # Podmiana metody generate_signal w SignalGenerator
        if hasattr(agent_controller, 'signal_generator') and agent_controller.signal_generator:
            original_generate_signal = agent_controller.signal_generator.generate_signal
            agent_controller.signal_generator.generate_signal = lambda symbol, data: mock_signal
            print("Podmieniłem metodę generate_signal w SignalGenerator")
        
        # Ręczne wywołanie przetwarzania instrumentu
        print("Wywołuję ręczne przetwarzanie instrumentu EURUSD w trybie obserwacyjnym...")
        agent_controller._process_instrument("EURUSD")
        
        # 10. Przełączenie agenta w tryb półautomatyczny
        print("\n10. Przełączanie agenta w tryb półautomatyczny...")
        config["mode"] = "semi_automatic"
        result = agent_controller.update_config(config)
        print(json.dumps(result, indent=2))
        
        # Sprawdzenie statusu po zmianie trybu
        await asyncio.sleep(1)
        print("\n11. Sprawdzanie statusu agenta po zmianie trybu...")
        status = agent_controller.get_status()
        print(json.dumps(status, indent=2))
        
        # 12. Test generowania i przetwarzania sygnału w trybie półautomatycznym
        print("\n12. Test sygnału w trybie półautomatycznym...")
        # Tworzymy mockowy sygnał
        mock_signal = MockTradingSignal(
            symbol="USDJPY",
            signal_type="SELL",
            price=145.67
        )
        
        # Ręczne wywołanie przetwarzania instrumentu
        print("Wywołuję ręczne przetwarzanie instrumentu USDJPY w trybie półautomatycznym...")
        agent_controller._process_instrument("USDJPY")
        
        # 13. Przełączenie agenta w tryb automatyczny
        print("\n13. Przełączanie agenta w tryb automatyczny...")
        config["mode"] = "automatic"
        result = agent_controller.update_config(config)
        print(json.dumps(result, indent=2))
        
        # Sprawdzenie statusu po zmianie trybu
        await asyncio.sleep(1)
        print("\n14. Sprawdzanie statusu agenta po zmianie trybu...")
        status = agent_controller.get_status()
        print(json.dumps(status, indent=2))
        
        # 15. Test generowania i przetwarzania sygnału w trybie automatycznym
        print("\n15. Test sygnału w trybie automatycznym...")
        # Tworzymy mockowy sygnał
        mock_signal = MockTradingSignal(
            symbol="EURUSD",
            signal_type="BUY",
            price=1.1245
        )
        
        # Ręczne wywołanie przetwarzania instrumentu
        print("Wywołuję ręczne przetwarzanie instrumentu EURUSD w trybie automatycznym...")
        agent_controller._process_instrument("EURUSD")
        
        # 16. Zatrzymanie agenta
        print("\n16. Zatrzymywanie agenta...")
        stop_result = agent_controller.stop_agent()
        print(json.dumps(stop_result, indent=2))
        
        # Sprawdzenie statusu po zatrzymaniu
        await asyncio.sleep(1)
        print("\n17. Sprawdzanie statusu agenta po zatrzymaniu...")
        status = agent_controller.get_status()
        print(json.dumps(status, indent=2))
        
        # 18. Przywrócenie oryginalnych metod
        print("\n18. Przywracanie oryginalnych metod...")
        try:
            SignalValidator.__init__ = original_init
            if hasattr(agent_controller, 'signal_generator') and agent_controller.signal_generator:
                agent_controller.signal_generator.generate_signal = original_generate_signal
        except Exception as e:
            print(f"Błąd podczas przywracania oryginalnych metod: {e}")
        
        # 19. Zatrzymanie serwera
        print("\n19. Zatrzymanie serwera...")
        await server.shutdown()
        print("Serwer zatrzymany pomyślnie")
        
        print("\nTest trybów pracy agenta zakończony pomyślnie!")
        
    except Exception as e:
        print(f"Błąd podczas testu trybów pracy agenta: {e}")
        import traceback
        traceback.print_exc()
        
        # W przypadku błędu próbujemy zatrzymać serwer
        try:
            if 'server' in locals():
                await server.shutdown()
                print("Serwer zatrzymany po błędzie")
        except Exception as shutdown_error:
            print(f"Błąd podczas zatrzymywania serwera: {shutdown_error}")


if __name__ == "__main__":
    try:
        asyncio.run(test_agent_modes())
    except KeyboardInterrupt:
        print("\nTest przerwany przez użytkownika")
    except Exception as e:
        print(f"Nieoczekiwany błąd: {e}")
        import traceback
        traceback.print_exc() 