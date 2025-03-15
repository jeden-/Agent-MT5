#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import os
import asyncio

# Dodanie ścieżki do modułów
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

async def main():
    try:
        from mt5_bridge.server import MT5Server
        
        print("Próba inicjalizacji serwera...")
        server = MT5Server(host="localhost", port=8080)
        print("Inicjalizacja serwera zakończona sukcesem")
        
        print("\nTestowanie uruchomienia serwera...")
        await server.start()
        print("Serwer uruchomiony poprawnie")
        
        # Krótkie oczekiwanie, aby serwer zdążył się uruchomić
        await asyncio.sleep(2)
        
        print("\nTestowanie zatrzymania serwera...")
        await server.shutdown()
        print("Serwer zatrzymany poprawnie")
        
        print("\nWszystkie testy zakończone pomyślnie!")
    except Exception as e:
        print(f"Wystąpił błąd: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main()) 