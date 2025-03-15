#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Wizualizacja schematu blokowego AgentMT5

Ten skrypt tworzy wizualizację schematu blokowego agenta handlowego
bez konieczności faktycznego połączenia z MT5. Służy do weryfikacji
kolejności operacji i wizualizacji przepływu procesu.
"""

import os
import sys
import logging
import time
import json
from datetime import datetime
from pathlib import Path
import asyncio

# Dodanie głównego katalogu projektu do PYTHONPATH
project_root = Path(__file__).parent
sys.path.append(str(project_root))
sys.path.append(str(project_root / 'src'))

# Konfiguracja logowania
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/schema_visualization.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("schema_visualizer")

class SchemaVisualizer:
    """
    Klasa do wizualizacji schematu blokowego agenta.
    """
    def __init__(self):
        self.steps = []
        self.current_step = None
        self.report_path = 'logs/schema_visualization_report.txt'
        self.graph_path = 'logs/schema_visualization_graph.txt'
        
    def start_step(self, step_name, step_id):
        """Rozpocznij nowy krok w schemacie blokowym."""
        self.current_step = {
            'id': step_id,
            'name': step_name,
            'start_time': datetime.now(),
            'end_time': None,
            'status': 'in_progress',
            'details': []
        }
        logger.info(f"=== POCZĄTEK KROKU [{step_id}]: {step_name} ===")
        
    def add_detail(self, detail):
        """Dodaj szczegół do bieżącego kroku."""
        if self.current_step:
            self.current_step['details'].append({
                'time': datetime.now(),
                'message': detail
            })
            logger.info(f"    SZCZEGÓŁ: {detail}")
    
    def end_step(self, status='completed', next_step_id=None):
        """Zakończ bieżący krok i dodaj go do listy kroków."""
        if self.current_step:
            self.current_step['end_time'] = datetime.now()
            self.current_step['status'] = status
            self.current_step['next_step_id'] = next_step_id
            self.steps.append(self.current_step)
            duration = (self.current_step['end_time'] - self.current_step['start_time']).total_seconds()
            logger.info(f"=== KONIEC KROKU [{self.current_step['id']}]: {self.current_step['name']} (status: {status}, czas: {duration:.2f}s) ===")
            self.current_step = None
    
    def generate_report(self):
        """Generuj raport z wizualizacji schematu."""
        report = ["WIZUALIZACJA SCHEMATU BLOKOWEGO AGENTA MT5:"]
        report.append("=" * 80)
        
        for step in self.steps:
            duration = (step['end_time'] - step['start_time']).total_seconds()
            
            if step['status'] == 'completed':
                status_text = "✓ ZAKOŃCZONO"
            elif step['status'] == 'skipped':
                status_text = "⚪ POMINIĘTO"
            elif step['status'] == 'failed':
                status_text = "❌ BŁĄD"
            else:
                status_text = step['status']
                
            next_text = f"→ Krok {step['next_step_id']}" if step['next_step_id'] else "→ KONIEC"
            report.append(f"[{step['id']}] {step['name']} ({status_text}, {duration:.2f}s) {next_text}")
            
            for detail in step['details']:
                time_str = detail['time'].strftime('%H:%M:%S.%f')[:-3]
                report.append(f"   {time_str} - {detail['message']}")
            
            report.append("-" * 80)
        
        return "\n".join(report)
    
    def generate_graph(self):
        """Generuj graf przepływu w formie tekstowej."""
        graph = ["GRAF PRZEPŁYWU PROCESU AGENTA MT5:"]
        graph.append("=" * 80)
        
        # Słownik z krokami dla łatwego dostępu
        steps_dict = {step['id']: step for step in self.steps}
        
        # Funkcja rekurencyjna do rysowania grafu
        def draw_step(step_id, indent=0):
            if step_id not in steps_dict:
                return
            
            step = steps_dict[step_id]
            
            # Rysowanie bieżącego kroku
            prefix = "│  " * indent
            status_symbol = "✓" if step['status'] == 'completed' else "❌" if step['status'] == 'failed' else "⚪"
            graph.append(f"{prefix}├─ [{step_id}] {status_symbol} {step['name']}")
            
            # Rysowanie następnego kroku
            if step['next_step_id']:
                draw_step(step['next_step_id'], indent + 1)
        
        # Rozpocznij od pierwszego kroku
        if self.steps:
            draw_step(self.steps[0]['id'])
        
        return "\n".join(graph)
    
    def save_visualization(self):
        """Zapisz raport i graf wizualizacji do plików."""
        os.makedirs(os.path.dirname(self.report_path), exist_ok=True)
        
        # Zapisz raport
        report = self.generate_report()
        with open(self.report_path, 'w', encoding='utf-8') as f:
            f.write(report)
        logger.info(f"Raport wizualizacji zapisany w {self.report_path}")
        
        # Zapisz graf
        graph = self.generate_graph()
        with open(self.graph_path, 'w', encoding='utf-8') as f:
            f.write(graph)
        logger.info(f"Graf przepływu zapisany w {self.graph_path}")
        
        return self.report_path, self.graph_path

async def simulate_agent_flow():
    """Symulacja przepływu agenta według schematu blokowego."""
    visualizer = SchemaVisualizer()
    
    try:
        # Krok 1: Inicjalizacja systemu
        visualizer.start_step("Inicjalizacja systemu", 1)
        visualizer.add_detail("Ładowanie konfiguracji")
        visualizer.add_detail("Inicjalizacja komponentów")
        visualizer.add_detail("Tworzenie połączenia z MT5 (symulacja)")
        visualizer.end_step(status='completed', next_step_id=2)
        await asyncio.sleep(0.5)  # Symulacja czasu wykonania
        
        # Krok 2: Ocena globalnego stanu rynku
        visualizer.start_step("Ocena globalnego stanu rynku", 2)
        visualizer.add_detail("Analiza indeksów zmienności")
        visualizer.add_detail("Ocena korelacji między instrumentami")
        visualizer.add_detail("Określenie fazy rynku")
        market_state = {
            'volatility': 'medium',
            'trend': 'bullish',
            'correlation': 0.3,
            'phase': 'accumulation'
        }
        visualizer.add_detail(f"Określony stan rynku: {json.dumps(market_state, indent=2)}")
        visualizer.end_step(status='completed', next_step_id=3)
        await asyncio.sleep(0.5)
        
        # Krok 3: Aktualizacja systemu wag
        visualizer.start_step("Aktualizacja systemu wag strategii", 3)
        visualizer.add_detail("Obliczanie optymalnych wag dla różnych typów strategii")
        strategy_weights = {
            'trend_following': 0.4,
            'mean_reversion': 0.3,
            'breakout': 0.2,
            'momentum': 0.1
        }
        visualizer.add_detail(f"Zaktualizowane wagi strategii: {json.dumps(strategy_weights, indent=2)}")
        visualizer.end_step(status='completed', next_step_id=4)
        await asyncio.sleep(0.3)
        
        # Krok 4: Analiza instrumentów
        visualizer.start_step("Analiza instrumentów i timeframe'ów", 4)
        instruments = ['EURUSD', 'GBPUSD', 'USDJPY', 'GOLD', 'US100']
        visualizer.add_detail(f"Analizowane instrumenty: {instruments}")
        
        for instrument in instruments:
            visualizer.add_detail(f"Analiza instrumentu: {instrument}")
            visualizer.add_detail(f"Pobieranie danych historycznych dla {instrument}")
            visualizer.add_detail(f"Obliczanie wskaźników technicznych dla {instrument}")
        
        visualizer.add_detail("Zakończono analizę wszystkich instrumentów")
        visualizer.end_step(status='completed', next_step_id=5)
        await asyncio.sleep(0.8)
        
        # Krok 5: Identyfikacja setupów
        visualizer.start_step("Identyfikacja potencjalnych setupów", 5)
        setups = [
            {'symbol': 'EURUSD', 'type': 'buy', 'quality': 8.2, 'strategy': 'trend_following'},
            {'symbol': 'GOLD', 'type': 'sell', 'quality': 7.5, 'strategy': 'breakout'},
            {'symbol': 'USDJPY', 'type': 'buy', 'quality': 6.8, 'strategy': 'momentum'}
        ]
        
        visualizer.add_detail(f"Zidentyfikowano {len(setups)} potencjalnych setupów")
        for i, setup in enumerate(setups, 1):
            visualizer.add_detail(f"Setup {i}: {json.dumps(setup, indent=2)}")
        
        visualizer.end_step(status='completed', next_step_id=6)
        await asyncio.sleep(0.5)
        
        # Krok 6: Filtracja setupów
        visualizer.start_step("Filtracja setupów", 6)
        visualizer.add_detail("Eliminacja setupów niskiej jakości")
        visualizer.add_detail("Eliminacja setupów z konfliktem")
        
        filtered_setups = [setup for setup in setups if setup['quality'] > 7.0]
        visualizer.add_detail(f"Po filtracji pozostało {len(filtered_setups)} setupów")
        
        for i, setup in enumerate(filtered_setups, 1):
            visualizer.add_detail(f"Przefiltrowany setup {i}: {json.dumps(setup, indent=2)}")
        
        visualizer.end_step(status='completed', next_step_id=7)
        await asyncio.sleep(0.3)
        
        # Krok 7: Wybór najlepszego setupu
        visualizer.start_step("Wybór najlepszego setupu", 7)
        
        best_setup = max(filtered_setups, key=lambda x: x['quality'])
        visualizer.add_detail(f"Najlepszy setup: {json.dumps(best_setup, indent=2)}")
        
        visualizer.end_step(status='completed', next_step_id=8)
        await asyncio.sleep(0.2)
        
        # Krok 8: Weryfikacja zgodności z limitami ryzyka
        visualizer.start_step("Weryfikacja zgodności z limitami ryzyka", 8)
        
        risk_validation = {
            'valid': True,
            'risk_percent': 1.2,
            'max_risk_allowed': 2.0,
            'portfolio_fit': 'good'
        }
        
        visualizer.add_detail(f"Wynik walidacji ryzyka: {json.dumps(risk_validation, indent=2)}")
        
        if risk_validation['valid']:
            visualizer.end_step(status='completed', next_step_id=9)
        else:
            visualizer.add_detail("Setup odrzucony przez zarządzanie ryzykiem")
            visualizer.end_step(status='failed', next_step_id=13)  # Przejdź do zarządzania pozycjami
            
        await asyncio.sleep(0.3)
        
        # Krok 9: Obliczenie parametrów pozycji
        visualizer.start_step("Obliczenie parametrów pozycji", 9)
        
        position_params = {
            'symbol': best_setup['symbol'],
            'type': best_setup['type'],
            'lot_size': 0.1,
            'entry_price': 1.0762,
            'stop_loss': 1.0722,
            'take_profit': 1.0842,
            'risk_reward': 2.0
        }
        
        visualizer.add_detail(f"Obliczone parametry pozycji: {json.dumps(position_params, indent=2)}")
        
        visualizer.end_step(status='completed', next_step_id=10)
        await asyncio.sleep(0.3)
        
        # Krok 10: Sprawdzenie poziomu autonomii
        visualizer.start_step("Sprawdzenie poziomu autonomii", 10)
        
        autonomy = 0.85  # 85%
        min_required = 0.8  # 80%
        
        visualizer.add_detail(f"Bieżący poziom autonomii: {autonomy}")
        visualizer.add_detail(f"Minimalny wymagany poziom: {min_required}")
        
        if autonomy >= min_required:
            visualizer.add_detail("Poziom autonomii wystarczający do automatycznego wykonania")
            visualizer.end_step(status='completed', next_step_id=11)
        else:
            visualizer.add_detail("Poziom autonomii zbyt niski, wymagane ręczne zatwierdzenie")
            visualizer.end_step(status='skipped', next_step_id=13)  # Przejdź do zarządzania pozycjami
        
        await asyncio.sleep(0.3)
        
        # Krok 11: Wykonanie zlecenia
        visualizer.start_step("Wykonanie zlecenia", 11)
        
        order_result = {
            'success': True,
            'ticket': 12345678,
            'open_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'open_price': position_params['entry_price']
        }
        
        visualizer.add_detail(f"Wynik wykonania zlecenia: {json.dumps(order_result, indent=2)}")
        
        if order_result['success']:
            visualizer.end_step(status='completed', next_step_id=12)
        else:
            visualizer.add_detail("Błąd podczas wykonywania zlecenia")
            visualizer.end_step(status='failed', next_step_id=13)
        
        await asyncio.sleep(0.5)
        
        # Krok 12: Inicjalizacja systemu zarządzania cyklem życia
        visualizer.start_step("Inicjalizacja zarządzania cyklem życia pozycji", 12)
        
        lifecycle = {
            'ticket': order_result['ticket'],
            'initial_state': 'monitoring',
            'breakeven_level': position_params['entry_price'] + (position_params['entry_price'] - position_params['stop_loss']) * 0.3,
            'trailing_activation': position_params['entry_price'] + (position_params['entry_price'] - position_params['stop_loss']) * 0.5
        }
        
        visualizer.add_detail(f"Skonfigurowany cykl życia pozycji: {json.dumps(lifecycle, indent=2)}")
        
        visualizer.end_step(status='completed', next_step_id=13)
        await asyncio.sleep(0.3)
        
        # Krok 13: Zarządzanie otwartymi pozycjami
        visualizer.start_step("Zarządzanie otwartymi pozycjami", 13)
        
        # Sprawdzenie otwartych pozycji
        open_positions = [{
            'ticket': 12345678,
            'symbol': 'EURUSD',
            'type': 'buy',
            'open_price': 1.0762,
            'current_price': 1.0775,
            'profit': 13.0,
            'profit_pips': 13,
            'stop_loss': 1.0722,
            'take_profit': 1.0842
        }]
        
        visualizer.add_detail(f"Liczba otwartych pozycji: {len(open_positions)}")
        
        for position in open_positions:
            visualizer.add_detail(f"Zarządzanie pozycją {position['ticket']} ({position['symbol']})")
            visualizer.add_detail(f"Aktualna cena: {position['current_price']}, Zysk: {position['profit']} USD ({position['profit_pips']} pips)")
            
            # Przykładowa modyfikacja pozycji - przesunięcie stop-lossa
            if position['profit_pips'] > 10:
                visualizer.add_detail(f"Przesunięcie stop-lossa na poziom breakeven")
                position['stop_loss'] = position['open_price']
                visualizer.add_detail(f"Nowy stop-loss: {position['stop_loss']}")
        
        visualizer.end_step(status='completed', next_step_id=14)
        await asyncio.sleep(0.5)
        
        # Krok 14: Aktualizacja metryk wydajności
        visualizer.start_step("Aktualizacja metryk wydajności", 14)
        
        metrics = {
            'win_rate': 68.5,  # %
            'profit_factor': 1.92,
            'avg_win': 35.2,
            'avg_loss': -18.4,
            'expectancy': 12.5,
            'max_drawdown': -3.2
        }
        
        visualizer.add_detail(f"Zaktualizowane metryki wydajności: {json.dumps(metrics, indent=2)}")
        
        visualizer.end_step(status='completed')
        await asyncio.sleep(0.3)
        
        # Zapisz raport i graf
        report_path, graph_path = visualizer.save_visualization()
        
        logger.info(f"Wizualizacja zakończona. Raport: {report_path}, Graf: {graph_path}")
        
    except Exception as e:
        logger.error(f"Błąd podczas symulacji przepływu agenta: {e}")
        if visualizer.current_step:
            visualizer.add_detail(f"BŁĄD: {str(e)}")
            visualizer.end_step(status='error')
        
        # Upewnij się, że raport zostanie zapisany nawet w przypadku błędu
        visualizer.save_visualization()

def main():
    """Funkcja główna."""
    # Utwórz katalog logów jeśli nie istnieje
    os.makedirs("logs", exist_ok=True)
    
    logger.info("Rozpoczęcie wizualizacji schematu blokowego AgentMT5")
    
    try:
        # Uruchomienie symulacji przepływu agenta
        asyncio.run(simulate_agent_flow())
    except KeyboardInterrupt:
        logger.info("Wizualizacja przerwana przez użytkownika")
    except Exception as e:
        logger.error(f"Nieoczekiwany błąd: {e}")
        import traceback
        traceback.print_exc()
    
    logger.info("Zakończenie wizualizacji schematu blokowego AgentMT5")

if __name__ == "__main__":
    main() 