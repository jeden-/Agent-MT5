#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Test AgentMT5 z pojedynczym zleceniem

Ten skrypt testowy uruchamia AgentMT5 z ograniczeniem do jednej pozycji 
i śledzeniem całego procesu przetwarzania zlecenia według schematu blokowego agenta.
"""

import os
import sys
import logging
import time
import asyncio
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# Dodanie głównego katalogu projektu do PYTHONPATH
project_root = Path(__file__).parent
sys.path.append(str(project_root))
sys.path.append(str(project_root / 'src'))

# Konfiguracja logowania
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/test_single_trade.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("test_agent")

# Ładowanie zmiennych środowiskowych
load_dotenv()

class SchemaTracer:
    """
    Klasa do śledzenia wykonania schematu blokowego agenta.
    """
    def __init__(self):
        self.steps = []
        self.current_step = None
        
    def start_step(self, step_name):
        """Rozpocznij nowy krok w schemacie blokowym."""
        self.current_step = {
            'name': step_name,
            'start_time': datetime.now(),
            'end_time': None,
            'status': 'in_progress',
            'details': []
        }
        logger.info(f"=== ROZPOCZĘCIE KROKU: {step_name} ===")
        
    def add_detail(self, detail):
        """Dodaj szczegół do bieżącego kroku."""
        if self.current_step:
            self.current_step['details'].append({
                'time': datetime.now(),
                'message': detail
            })
            logger.info(f"    SZCZEGÓŁ: {detail}")
    
    def end_step(self, status='completed'):
        """Zakończ bieżący krok i dodaj go do listy kroków."""
        if self.current_step:
            self.current_step['end_time'] = datetime.now()
            self.current_step['status'] = status
            self.steps.append(self.current_step)
            duration = (self.current_step['end_time'] - self.current_step['start_time']).total_seconds()
            logger.info(f"=== ZAKOŃCZENIE KROKU: {self.current_step['name']} (status: {status}, czas: {duration:.2f}s) ===")
            self.current_step = None
    
    def generate_report(self):
        """Generuj raport z wykonanych kroków."""
        report = ["RAPORT Z TESTOWEGO WYKONANIA AGENTA MT5:"]
        report.append("-" * 80)
        
        for i, step in enumerate(self.steps, 1):
            duration = (step['end_time'] - step['start_time']).total_seconds()
            report.append(f"{i}. {step['name']} - {step['status']} ({duration:.2f}s)")
            
            for detail in step['details']:
                time_str = detail['time'].strftime('%H:%M:%S.%f')[:-3]
                report.append(f"   {time_str} - {detail['message']}")
            
            report.append("-" * 80)
        
        return "\n".join(report)

async def test_agent():
    """Funkcja testowa uruchamiająca agenta z monitorowaniem schematu blokowego."""
    tracer = SchemaTracer()
    
    try:
        tracer.start_step("Inicjalizacja Agenta MT5 i połączenie z MetaTrader")
        
        # Import komponentów systemu
        from src.mt5_bridge.server import create_server
        from src.agent_controller import get_agent_controller
        
        # Znajdź wolny port
        from socket import socket
        def find_free_port(start_port=5555, max_port=6000):
            for port in range(start_port, max_port):
                try:
                    with socket() as s:
                        s.bind(('127.0.0.1', port))
                        return port
                except OSError:
                    continue
            raise IOError(f"Nie można znaleźć wolnego portu w zakresie od {start_port} do {max_port}")
        
        port = find_free_port()
        host = '127.0.0.1'
        
        tracer.add_detail(f"Znaleziono wolny port {port} dla serwera HTTP")
        
        # Zapisz port do zmiennej środowiskowej
        os.environ["SERVER_URL"] = f"http://{host}:{port}"
        
        # Uruchomienie serwera HTTP
        async with create_server(host, port) as server:
            tracer.add_detail("Serwer HTTP uruchomiony pomyślnie")
            
            # Inicjalizacja kontrolera agenta
            tracer.add_detail("Inicjalizacja kontrolera agenta")
            agent_controller = get_agent_controller()
            
            # Ustawienie kontrolera agenta w serwerze
            server.set_agent_controller(agent_controller)
            tracer.add_detail("Kontroler agenta skonfigurowany w serwerze")
            
            # Sprawdź połączenie z MT5
            mt5_connected = agent_controller.check_mt5_connection()
            if mt5_connected:
                tracer.add_detail("Połączenie z MetaTrader 5 ustanowione pomyślnie")
            else:
                tracer.add_detail("BŁĄD: Nie można połączyć się z MetaTrader 5")
                tracer.end_step("failed")
                return
            
            tracer.end_step()
            
            # Ocena globalnego stanu rynku
            tracer.start_step("Ocena globalnego stanu rynku")
            
            # Pobierz dane o rynku
            market_state = await agent_controller.evaluate_market_state()
            tracer.add_detail(f"Pobrano stan rynku: {market_state}")
            
            # Sprawdź zmienność rynku
            volatility = await agent_controller.evaluate_market_volatility()
            tracer.add_detail(f"Zmienność rynku: {volatility}")
            
            tracer.end_step()
            
            # Aktualizacja systemu wag
            tracer.start_step("Aktualizacja systemu wag dla różnych typów strategii")
            
            weights = await agent_controller.update_strategy_weights(market_state, volatility)
            tracer.add_detail(f"Zaktualizowano wagi strategii: {weights}")
            
            tracer.end_step()
            
            # Równoległa analiza instrumentów
            tracer.start_step("Równoległa analiza wszystkich instrumentów i timeframe'ów")
            
            instruments = agent_controller.config.get("instruments", {})
            tracer.add_detail(f"Analizowane instrumenty: {list(instruments.keys())}")
            
            analysis_results = {}
            for instrument in instruments:
                tracer.add_detail(f"Analiza instrumentu: {instrument}")
                # Uruchomienie analizy instrumentu
                instrument_analysis = await agent_controller.analyze_instrument(instrument)
                analysis_results[instrument] = instrument_analysis
            
            tracer.add_detail(f"Zakończono analizę wszystkich instrumentów")
            tracer.end_step()
            
            # Identyfikacja potencjalnych setupów
            tracer.start_step("Identyfikacja potencjalnych setupów")
            
            setups = await agent_controller.identify_setups(analysis_results)
            tracer.add_detail(f"Zidentyfikowano {len(setups)} potencjalnych setupów")
            
            for i, setup in enumerate(setups, 1):
                tracer.add_detail(f"Setup {i}: {setup}")
            
            tracer.end_step()
            
            # Ocena jakości setupów i filtracja
            tracer.start_step("Ocena jakości setupów i filtracja")
            
            filtered_setups = await agent_controller.filter_setups(setups)
            tracer.add_detail(f"Po filtracji pozostało {len(filtered_setups)} setupów")
            
            for i, setup in enumerate(filtered_setups, 1):
                quality = setup.get('quality', 'nieznana')
                tracer.add_detail(f"Setup {i} - jakość: {quality}, symbol: {setup.get('symbol')}")
            
            tracer.end_step()
            
            # Sprawdzenie, czy setupy przekraczają próg jakości
            tracer.start_step("Weryfikacja przekroczenia progu jakości setupów")
            
            quality_threshold = agent_controller.config.get("setup_quality_threshold", 7.0)
            valid_setups = [s for s in filtered_setups if s.get('quality', 0) >= quality_threshold]
            
            tracer.add_detail(f"Próg jakości: {quality_threshold}")
            tracer.add_detail(f"Liczba setupów przekraczających próg: {len(valid_setups)}")
            
            if not valid_setups:
                tracer.add_detail("Brak setupów o wystarczającej jakości")
                tracer.end_step("no_valid_setups")
                
                # Przejdź do zarządzania otwartymi pozycjami
                await handle_open_positions(agent_controller, tracer)
                
                return
            
            tracer.end_step()
            
            # Wybór najlepszego setupu
            tracer.start_step("Wybór najlepszego setupu")
            
            best_setup = max(valid_setups, key=lambda x: x.get('quality', 0))
            tracer.add_detail(f"Najlepszy setup: {best_setup}")
            
            tracer.end_step()
            
            # Weryfikacja zgodności z limitami
            tracer.start_step("Weryfikacja zgodności z limitami alokacji i zarządzaniem ryzykiem")
            
            risk_validation = await agent_controller.validate_risk(best_setup)
            tracer.add_detail(f"Wynik walidacji ryzyka: {risk_validation}")
            
            if not risk_validation.get('valid', False):
                tracer.add_detail(f"Setup odrzucony przez zarządzanie ryzykiem: {risk_validation.get('reason')}")
                tracer.end_step("risk_validation_failed")
                
                # Przejdź do zarządzania otwartymi pozycjami
                await handle_open_positions(agent_controller, tracer)
                
                return
            
            tracer.end_step()
            
            # Weryfikacja całego portfela
            tracer.start_step("Weryfikacja akceptowalności setupu w kontekście całego portfela")
            
            portfolio_validation = await agent_controller.validate_portfolio_fit(best_setup)
            tracer.add_detail(f"Wynik walidacji portfela: {portfolio_validation}")
            
            if not portfolio_validation.get('valid', False):
                tracer.add_detail(f"Setup niezgodny z portfelem: {portfolio_validation.get('reason')}")
                tracer.end_step("portfolio_validation_failed")
                
                # Przejdź do zarządzania otwartymi pozycjami
                await handle_open_positions(agent_controller, tracer)
                
                return
            
            tracer.end_step()
            
            # Obliczenie optymalnej wielkości pozycji
            tracer.start_step("Obliczenie optymalnej wielkości pozycji i parametrów zarządzania")
            
            position_params = await agent_controller.calculate_position_parameters(best_setup)
            tracer.add_detail(f"Parametry pozycji: {position_params}")
            
            tracer.end_step()
            
            # Sprawdzenie poziomu autonomii
            tracer.start_step("Sprawdzenie poziomu autonomii")
            
            autonomy_level = agent_controller.get_autonomy_level()
            tracer.add_detail(f"Poziom autonomii: {autonomy_level}")
            
            proceed_with_execution = autonomy_level >= agent_controller.config.get("min_execution_autonomy", 0.8)
            tracer.add_detail(f"Czy można wykonać zlecenie automatycznie: {proceed_with_execution}")
            
            if not proceed_with_execution:
                tracer.add_detail("Poziom autonomii zbyt niski, wymagane potwierdzenie")
                tracer.end_step("autonomy_too_low")
                
                # Przejdź do zarządzania otwartymi pozycjami
                await handle_open_positions(agent_controller, tracer)
                
                return
            
            tracer.end_step()
            
            # Wykonanie zlecenia
            tracer.start_step("Wykonanie zlecenia przez MT5")
            
            order_result = await agent_controller.execute_order(best_setup, position_params)
            tracer.add_detail(f"Wynik wykonania zlecenia: {order_result}")
            
            if not order_result.get('success', False):
                tracer.add_detail(f"Błąd wykonania zlecenia: {order_result.get('error')}")
                tracer.end_step("order_execution_failed")
                
                # Przejdź do zarządzania otwartymi pozycjami
                await handle_open_positions(agent_controller, tracer)
                
                return
            
            tracer.add_detail(f"Zlecenie wykonane pomyślnie. Ticket: {order_result.get('ticket')}")
            tracer.end_step()
            
            # Inicjalizacja zarządzania cyklem życia pozycji
            tracer.start_step("Inicjalizacja systemu zarządzania cyklem życia nowej pozycji")
            
            position_lifecycle = await agent_controller.initialize_position_lifecycle(order_result.get('ticket'))
            tracer.add_detail(f"Cykl życia pozycji zainicjalizowany: {position_lifecycle}")
            
            tracer.end_step()
            
            # Zarządzanie otwartymi pozycjami
            await handle_open_positions(agent_controller, tracer)
            
    except Exception as e:
        logger.error(f"Błąd podczas testu agenta: {e}")
        if tracer.current_step:
            tracer.add_detail(f"BŁĄD: {str(e)}")
            tracer.end_step("error")
    finally:
        # Zapisz raport z testu
        report = tracer.generate_report()
        report_path = 'logs/single_trade_report.txt'
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(report)
        logger.info(f"Raport z testu zapisany w {report_path}")

async def handle_open_positions(agent_controller, tracer):
    """Zarządzanie otwartymi pozycjami zgodnie ze schematem."""
    tracer.start_step("Zarządzanie otwartymi pozycjami")
    
    positions = await agent_controller.get_open_positions()
    tracer.add_detail(f"Liczba otwartych pozycji: {len(positions)}")
    
    for position in positions:
        tracer.add_detail(f"Zarządzanie pozycją {position.get('ticket')}")
        
        # Aktualizacja cyklu życia
        lifecycle_update = await agent_controller.update_position_lifecycle(position)
        tracer.add_detail(f"Aktualizacja cyklu życia: {lifecycle_update}")
        
        # Analiza warunków zamknięcia/modyfikacji
        conditions = await agent_controller.analyze_position_conditions(position)
        tracer.add_detail(f"Warunki pozycji: {conditions}")
        
        # Wykonanie akcji
        if conditions.get('should_close', False):
            close_result = await agent_controller.close_position(position)
            tracer.add_detail(f"Zamknięcie pozycji: {close_result}")
        elif conditions.get('should_modify', False):
            modify_result = await agent_controller.modify_position(position, conditions.get('modifications', {}))
            tracer.add_detail(f"Modyfikacja pozycji: {modify_result}")
        else:
            tracer.add_detail("Brak akcji dla pozycji")
    
    tracer.end_step()
    
    # Aktualizacja metryk wydajności
    tracer.start_step("Aktualizacja metryk wydajności")
    
    metrics = await agent_controller.update_performance_metrics()
    tracer.add_detail(f"Aktualizacja metryk: {metrics}")
    
    autonomy_update = await agent_controller.update_autonomy_levels()
    tracer.add_detail(f"Aktualizacja poziomów autonomii: {autonomy_update}")
    
    weights_update = await agent_controller.update_strategy_weights(None, None)
    tracer.add_detail(f"Aktualizacja wag strategii: {weights_update}")
    
    tracer.end_step()

if __name__ == "__main__":
    # Utwórz katalog logów jeśli nie istnieje
    os.makedirs("logs", exist_ok=True)
    
    logger.info("Rozpoczęcie testu pojedynczego zlecenia")
    
    try:
        asyncio.run(test_agent())
    except KeyboardInterrupt:
        logger.info("Test przerwany przez użytkownika")
    except Exception as e:
        logger.error(f"Nieoczekiwany błąd: {e}")
        import traceback
        traceback.print_exc()
    
    logger.info("Zakończenie testu pojedynczego zlecenia") 