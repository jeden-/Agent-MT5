#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Skrypt do uruchamiania agenta handlowego w różnych trybach pracy.

Ten skrypt uruchamia agenta handlowego w jednym z trzech trybów pracy:
1. observation - tryb obserwacyjny, tylko analiza bez zawierania transakcji
2. semi_automatic - tryb półautomatyczny, propozycje wymagają zatwierdzenia
3. automatic - tryb automatyczny, pełna automatyzacja
"""

import sys
import os
import asyncio
import logging
import argparse
import json
import time
from datetime import datetime

# Dodanie głównego katalogu projektu do PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Konfiguracja loggera
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(f"agent_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
    ]
)

logger = logging.getLogger("agent_runner")

async def run_agent(mode, instruments, risk_limits, server_port=8080, run_time=None):
    """
    Uruchamia agenta handlowego w określonym trybie pracy.
    
    Args:
        mode: Tryb pracy agenta (observation, semi_automatic, automatic)
        instruments: Słownik instrumentów do handlu
        risk_limits: Słownik limitów ryzyka
        server_port: Port serwera HTTP
        run_time: Czas działania agenta w sekundach (None = nieskończony)
    """
    try:
        # Import modułów
        from src.mt5_bridge import start_server
        from src.agent_controller import get_agent_controller, AgentMode, AgentStatus
        
        # Uruchomienie serwera HTTP
        logger.info(f"Uruchamianie serwera HTTP na porcie {server_port}...")
        server = await start_server(host="localhost", port=server_port)
        logger.info(f"Serwer HTTP uruchomiony na http://localhost:{server_port}")
        
        # Inicjalizacja kontrolera agenta
        logger.info("Inicjalizacja kontrolera agenta...")
        agent_controller = get_agent_controller()
        
        # Ustawienie kontrolera agenta w serwerze
        logger.info("Konfiguracja serwera z kontrolerem agenta...")
        server.set_agent_controller(agent_controller)
        
        # Konfiguracja agenta
        logger.info(f"Konfiguracja agenta w trybie {mode}...")
        config = {
            "mode": mode,
            "risk_limits": risk_limits,
            "instruments": instruments,
            # Dodatkowe parametry dla SignalValidator
            "min_probability": 0.7,
            "min_risk_reward_ratio": 1.5
        }
        
        # Aktualizacja konfiguracji agenta
        result = agent_controller.update_config(config)
        logger.info(f"Wynik aktualizacji konfiguracji: {json.dumps(result, indent=2)}")
        
        # Uruchomienie agenta
        logger.info(f"Uruchamianie agenta w trybie {mode}...")
        start_result = agent_controller.start_agent(mode=mode)
        logger.info(f"Wynik uruchomienia agenta: {json.dumps(start_result, indent=2)}")
        
        # Sprawdzenie statusu po uruchomieniu
        await asyncio.sleep(1)
        status = agent_controller.get_status()
        logger.info(f"Status agenta po uruchomieniu: {json.dumps(status, indent=2)}")
        
        if status["status"] != "running":
            logger.error(f"Agent nie został uruchomiony poprawnie. Status: {status['status']}")
            return
        
        # Działanie agenta przez określony czas lub nieskończenie
        start_time = time.time()
        try:
            if run_time is None:
                # Nieskończone działanie
                logger.info("Agent uruchomiony w trybie ciągłym. Naciśnij Ctrl+C, aby zatrzymać.")
                while True:
                    await asyncio.sleep(10)
                    status = agent_controller.get_status()
                    logger.info(f"Status agenta: {status['status']}, czas pracy: {time.time() - start_time:.2f}s")
            else:
                # Działanie przez określony czas
                logger.info(f"Agent uruchomiony na {run_time} sekund.")
                while time.time() - start_time < run_time:
                    await asyncio.sleep(min(10, run_time - (time.time() - start_time)))
                    status = agent_controller.get_status()
                    logger.info(f"Status agenta: {status['status']}, czas pracy: {time.time() - start_time:.2f}s")
        
        except KeyboardInterrupt:
            logger.info("Otrzymano sygnał przerwania. Zatrzymywanie agenta...")
        
        finally:
            # Zatrzymanie agenta
            logger.info("Zatrzymywanie agenta...")
            stop_result = agent_controller.stop_agent()
            logger.info(f"Wynik zatrzymania agenta: {json.dumps(stop_result, indent=2)}")
            
            # Sprawdzenie statusu po zatrzymaniu
            await asyncio.sleep(1)
            status = agent_controller.get_status()
            logger.info(f"Status agenta po zatrzymaniu: {json.dumps(status, indent=2)}")
            
            # Zatrzymanie serwera HTTP
            logger.info("Zatrzymywanie serwera HTTP...")
            await server.shutdown()
            logger.info("Serwer HTTP zatrzymany")
    
    except Exception as e:
        logger.error(f"Błąd podczas uruchamiania agenta: {e}")
        raise

def main():
    """Główna funkcja skryptu."""
    parser = argparse.ArgumentParser(description="Uruchamianie agenta handlowego")
    parser.add_argument("--mode", choices=["observation", "semi_automatic", "automatic"], 
                        default="observation", help="Tryb pracy agenta")
    parser.add_argument("--port", type=int, default=8080, help="Port serwera HTTP")
    parser.add_argument("--time", type=int, help="Czas działania agenta w sekundach (domyślnie: nieskończony)")
    parser.add_argument("--instruments", type=str, default="EURUSD,USDJPY", 
                        help="Lista instrumentów do handlu (oddzielone przecinkami)")
    parser.add_argument("--max-positions", type=int, default=3, help="Maksymalna liczba pozycji")
    parser.add_argument("--max-risk-per-trade", type=float, default=0.01, 
                        help="Maksymalne ryzyko na transakcję (0.01 oznacza 1 procent)")
    parser.add_argument("--max-daily-risk", type=float, default=0.05, 
                        help="Maksymalne dzienne ryzyko (0.05 oznacza 5 procent)")
    parser.add_argument("--max-lot-size", type=float, default=0.1, 
                        help="Maksymalny rozmiar pozycji (w lotach)")
    args = parser.parse_args()
    
    # Przygotowanie listy instrumentów
    instruments = {}
    for instrument in args.instruments.split(","):
        instrument = instrument.strip()
        if instrument:
            instruments[instrument] = {
                "active": True,
                "max_lot_size": args.max_lot_size
            }
    
    # Przygotowanie limitów ryzyka
    risk_limits = {
        "max_positions": args.max_positions,
        "max_risk_per_trade": args.max_risk_per_trade,
        "max_daily_risk": args.max_daily_risk
    }
    
    # Wyświetlenie konfiguracji
    logger.info(f"Uruchamianie agenta w trybie: {args.mode}")
    logger.info(f"Instrumenty: {json.dumps(instruments, indent=2)}")
    logger.info(f"Limity ryzyka: {json.dumps(risk_limits, indent=2)}")
    
    # Uruchomienie agenta
    asyncio.run(run_agent(
        mode=args.mode,
        instruments=instruments,
        risk_limits=risk_limits,
        server_port=args.port,
        run_time=args.time
    ))
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 