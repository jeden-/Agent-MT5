#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import os
import asyncio
import json
import aiohttp

# Dodanie ścieżki do modułów
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

async def test_endpoints():
    try:
        # Uruchomienie serwera (korzystamy z innego procesu lub już uruchomionego serwera)
        from mt5_bridge.server import MT5Server
        server = MT5Server(host="localhost", port=8080)
        await server.start()
        print("Serwer uruchomiony na http://localhost:8080")
        
        # Krótkie oczekiwanie, aby serwer zdążył się uruchomić
        await asyncio.sleep(2)
        
        # Test endpointów
        async with aiohttp.ClientSession() as session:
            base_url = "http://localhost:8080"
            
            # 1. Test statusu agenta
            print("\n1. Testowanie GET /agent/status")
            async with session.get(f"{base_url}/agent/status") as response:
                data = await response.json()
                print(f"Status agenta: {json.dumps(data, indent=2)}")
            
            # 2. Test uruchomienia agenta
            print("\n2. Testowanie POST /agent/start")
            start_params = {"mode": "observation"}
            async with session.post(f"{base_url}/agent/start", json=start_params) as response:
                data = await response.json()
                print(f"Start agenta: {json.dumps(data, indent=2)}")
            
            # Sprawdzenie statusu po uruchomieniu
            print("\nSprawdzenie statusu po uruchomieniu:")
            async with session.get(f"{base_url}/agent/status") as response:
                data = await response.json()
                print(f"Status agenta: {json.dumps(data, indent=2)}")
            
            # 3. Test konfiguracji agenta
            print("\n3. Testowanie POST /agent/config")
            config = {
                "mode": "semi_automatic",
                "risk_limits": {
                    "max_positions": 5,
                    "max_risk_per_trade": 0.02
                },
                "instruments": {
                    "EURUSD": {
                        "active": True,
                        "max_lot_size": 0.1
                    },
                    "GBPUSD": {
                        "active": True,
                        "max_lot_size": 0.05
                    }
                }
            }
            async with session.post(f"{base_url}/agent/config", json=config) as response:
                data = await response.json()
                print(f"Konfiguracja agenta: {json.dumps(data, indent=2)}")
            
            # 4. Test zatrzymania agenta
            print("\n4. Testowanie POST /agent/stop")
            async with session.post(f"{base_url}/agent/stop") as response:
                data = await response.json()
                print(f"Stop agenta: {json.dumps(data, indent=2)}")
            
            # Sprawdzenie statusu po zatrzymaniu
            print("\nSprawdzenie statusu po zatrzymaniu:")
            async with session.get(f"{base_url}/agent/status") as response:
                data = await response.json()
                print(f"Status agenta: {json.dumps(data, indent=2)}")
            
            # 5. Test restartu agenta
            print("\n5. Testowanie POST /agent/restart")
            restart_params = {"mode": "automatic"}
            async with session.post(f"{base_url}/agent/restart", json=restart_params) as response:
                data = await response.json()
                print(f"Restart agenta: {json.dumps(data, indent=2)}")
            
            # Sprawdzenie statusu po restarcie
            print("\nSprawdzenie statusu po restarcie:")
            async with session.get(f"{base_url}/agent/status") as response:
                data = await response.json()
                print(f"Status agenta: {json.dumps(data, indent=2)}")
        
        # Zatrzymanie serwera
        print("\nZatrzymanie serwera...")
        await server.shutdown()
        print("Serwer zatrzymany pomyślnie")
        
    except Exception as e:
        print(f"Wystąpił błąd: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_endpoints()) 