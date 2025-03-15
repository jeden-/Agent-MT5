#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Test kontrolera agenta handlowego.
"""

import sys
import os
import asyncio
from datetime import datetime
import logging
import json

# Dodanie głównego katalogu projektu do PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Konfiguracja loggera
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)

# Import kontrolera agenta
from src.agent_controller import get_agent_controller, AgentMode, AgentStatus


async def test_agent_controller():
    """
    Testuje podstawowe funkcjonalności kontrolera agenta.
    """
    print("Rozpoczęcie testu kontrolera agenta...")
    agent_controller = get_agent_controller()
    
    # 1. Test statusu początkowego
    print("\n1. Status początkowy:")
    status = agent_controller.get_status()
    print(json.dumps(status, indent=2))
    
    # 2. Test uruchomienia agenta w trybie obserwacyjnym
    print("\n2. Uruchomienie agenta w trybie obserwacyjnym:")
    result = agent_controller.start_agent(mode="observation")
    print(json.dumps(result, indent=2))
    
    # Sprawdzenie statusu po uruchomieniu
    await asyncio.sleep(2)
    print("\nStatus po uruchomieniu:")
    status = agent_controller.get_status()
    print(json.dumps(status, indent=2))
    
    # 3. Test aktualizacji konfiguracji
    print("\n3. Aktualizacja konfiguracji agenta:")
    config = {
        "mode": "semi_automatic",
        "risk_limits": {
            "max_positions": 3,
            "max_risk_per_trade": 0.01
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
    result = agent_controller.update_config(config)
    print(json.dumps(result, indent=2))
    
    # 4. Test zatrzymania agenta
    print("\n4. Zatrzymanie agenta:")
    result = agent_controller.stop_agent()
    print(json.dumps(result, indent=2))
    
    # Sprawdzenie statusu po zatrzymaniu
    await asyncio.sleep(1)
    print("\nStatus po zatrzymaniu:")
    status = agent_controller.get_status()
    print(json.dumps(status, indent=2))
    
    # 5. Test restartu agenta w trybie automatycznym
    print("\n5. Restart agenta w trybie automatycznym:")
    result = agent_controller.restart_agent(mode="automatic")
    print(json.dumps(result, indent=2))
    
    # Sprawdzenie statusu po restarcie
    await asyncio.sleep(2)
    print("\nStatus po restarcie:")
    status = agent_controller.get_status()
    print(json.dumps(status, indent=2))
    
    # 6. Finalne zatrzymanie agenta
    print("\n6. Finalne zatrzymanie agenta:")
    result = agent_controller.stop_agent()
    print(json.dumps(result, indent=2))
    
    print("\nTest kontrolera agenta zakończony pomyślnie!")


if __name__ == "__main__":
    try:
        asyncio.run(test_agent_controller())
    except KeyboardInterrupt:
        print("Test przerwany przez użytkownika")
    except Exception as e:
        print(f"Błąd podczas testu: {e}")
        import traceback
        traceback.print_exc() 