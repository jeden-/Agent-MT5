#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Test całego systemu, uwzględniający prawidłowe inicjalizacje komponentów.
"""

import sys
import os
import asyncio
import logging
from datetime import datetime
import json

# Dodanie głównego katalogu projektu do PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Konfiguracja loggera
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)

logger = logging.getLogger(__name__)

async def test_system():
    """
    Testuje cały system, inicjalizując komponenty w odpowiedniej kolejności.
    """
    try:
        print("Rozpoczynanie testu systemu...")
        
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
        
        # 4. Test statusu kontrolera agenta
        print("\n4. Sprawdzanie statusu agenta...")
        status = agent_controller.get_status()
        print(json.dumps(status, indent=2))
        
        # 5. Test aktualizacji konfiguracji agenta
        print("\n5. Aktualizacja konfiguracji agenta...")
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
        
        # 6. Test uruchomienia agenta
        print("\n6. Próba uruchomienia agenta w trybie obserwacji...")
        start_result = agent_controller.start_agent(mode="observation")
        print(json.dumps(start_result, indent=2))
        
        # Sprawdzenie statusu po uruchomieniu
        print("\n7. Sprawdzanie statusu po uruchomieniu...")
        status = agent_controller.get_status()
        print(json.dumps(status, indent=2))
        
        # Jeśli agent został uruchomiony, zatrzymaj go
        if status.get("status") == "running":
            print("\n8. Zatrzymywanie agenta...")
            stop_result = agent_controller.stop_agent()
            print(json.dumps(stop_result, indent=2))
        
        # 9. Test API endpointów
        print("\n9. Testowanie API endpointów...")
        import aiohttp
        
        async with aiohttp.ClientSession() as session:
            # Test endpointu /ping
            print("\n9.1. Test endpointu /ping")
            async with session.get("http://localhost:8080/ping") as response:
                print(f"Status: {response.status}")
                print(f"Odpowiedź: {await response.text()}")
            
            # Test endpointu /agent/status
            print("\n9.2. Test endpointu /agent/status")
            async with session.get("http://localhost:8080/agent/status") as response:
                print(f"Status: {response.status}")
                data = await response.json()
                print(f"Odpowiedź: {json.dumps(data, indent=2)}")
            
            # Test endpointu /agent/config
            print("\n9.3. Test endpointu /agent/config")
            async with session.post("http://localhost:8080/agent/config", json=config) as response:
                print(f"Status: {response.status}")
                data = await response.json()
                print(f"Odpowiedź: {json.dumps(data, indent=2)}")
            
            # Test endpointu /agent/start
            print("\n9.4. Test endpointu /agent/start")
            start_data = {"mode": "observation"}
            async with session.post("http://localhost:8080/agent/start", json=start_data) as response:
                print(f"Status: {response.status}")
                data = await response.json()
                print(f"Odpowiedź: {json.dumps(data, indent=2)}")
            
            # Test endpointu /agent/stop
            print("\n9.5. Test endpointu /agent/stop")
            async with session.post("http://localhost:8080/agent/stop") as response:
                print(f"Status: {response.status}")
                data = await response.json()
                print(f"Odpowiedź: {json.dumps(data, indent=2)}")
        
        # 10. Zatrzymanie serwera
        print("\n10. Zatrzymanie serwera...")
        await server.shutdown()
        print("Serwer zatrzymany pomyślnie")
        
        print("\nTest systemu zakończony pomyślnie!")
        
    except Exception as e:
        print(f"Błąd podczas testu systemu: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    try:
        asyncio.run(test_system())
    except KeyboardInterrupt:
        print("\nTest przerwany przez użytkownika")
    except Exception as e:
        print(f"Nieoczekiwany błąd: {e}")
        import traceback
        traceback.print_exc() 