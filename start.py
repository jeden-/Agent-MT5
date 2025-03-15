"""
Skrypt startowy systemu AgentMT5.
"""

import os
import sys
import asyncio
import logging
import socket
import subprocess
import argparse
from dotenv import load_dotenv
from pathlib import Path

# Dodaj ścieżkę projektu do PYTHONPATH
project_root = Path(__file__).parent
sys.path.append(str(project_root))
sys.path.append(str(project_root / 'src'))

def find_free_port(start_port=5555, max_port=6000):
    """Znajduje wolny port TCP."""
    for port in range(start_port, max_port):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('127.0.0.1', port))
                return port
        except OSError:
            continue
    raise IOError(f"Nie można znaleźć wolnego portu w zakresie od {start_port} do {max_port}")

def load_config():
    """
    Ładuje konfigurację systemu z pliku.
    
    Returns:
        dict: Słownik z konfiguracją systemu
    """
    try:
        from src.utils.config_manager import ConfigManager
        config_manager = ConfigManager()
        return config_manager.get_config()
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Błąd podczas ładowania konfiguracji: {e}")
        # Zwracamy domyślną konfigurację
        return {
            "instruments": {
                "EURUSD.pro": 0.1,
                "GBPUSD.pro": 0.1,
                "GOLD.pro": 0.1,
                "US100.pro": 0.1,
                "SILVER.pro": 0.1
            },
            "risk_management": {
                "max_positions_per_symbol": 1,
                "max_positions_total": 3,  # Zwiększamy do 3 pozycji łącznie
                "max_risk_per_trade_percent": 2.0,
                "daily_loss_limit_percent": 5.0
            }
        }

# Konfiguracja logowania
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/agent.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Załaduj zmienne środowiskowe
load_dotenv()

# Aplikowanie łatek
try:
    from src.utils.patches import apply_all_patches
    logger.info("Aplikowanie łatek systemowych...")
    patch_results = apply_all_patches()
    if not all(patch_results.values()):
        logger.warning("Nie wszystkie łatki zostały pomyślnie zaaplikowane!")
    else:
        logger.info(f"Pomyślnie zaaplikowano {sum(patch_results.values())}/{len(patch_results)} łatek")
except Exception as e:
    logger.error(f"Błąd podczas aplikowania łatek systemowych: {e}")

async def run_backtest(args):
    """Uruchamia moduł backtestingu z podanymi argumentami."""
    try:
        from src.backtest.backtest_engine import BacktestEngine, BacktestConfig
        from src.backtest.strategy import (
            TradingStrategy, SimpleMovingAverageStrategy, 
            RSIStrategy, BollingerBandsStrategy, MACDStrategy,
            CombinedIndicatorsStrategy, StrategyConfig
        )
        from src.backtest.backtest_metrics import generate_report
        from datetime import datetime, timedelta
        import pandas as pd
        
        # Parsowanie parametrów backtestingu
        symbol = args.symbol or "EURUSD"
        timeframe = args.timeframe or "H1"
        days = args.days or 30
        strategy_name = args.strategy or "SMA"
        
        logger.info(f"Uruchamianie backtestingu dla {symbol} na timeframe {timeframe}, ostatnie {days} dni")
        logger.info(f"Wybrana strategia: {strategy_name}")
        
        # Przygotowanie dat
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        # Konfiguracja backtestingu
        config = BacktestConfig(
            symbol=symbol,
            timeframe=timeframe,
            start_date=start_date,
            end_date=end_date,
            initial_balance=10000.0,
            position_size_pct=1.0,
            commission=0.0001,
            slippage=0.0,
            use_spread=True,
            min_volume=0.01,
            max_volume=10.0,
            strategy_name=strategy_name,
            use_cache=True,
            update_cache=True,
            output_dir="backtest_results"
        )
        
        # Przygotowanie parametrów strategii
        strategy_params = {}
        if strategy_name == "SMA":
            strategy_params = {"fast_period": 10, "slow_period": 30}
        elif strategy_name == "RSI":
            strategy_params = {"rsi_period": 14, "oversold": 30, "overbought": 70}
        elif strategy_name == "BB":
            strategy_params = {"period": 20, "std_dev": 2.0}
        elif strategy_name == "MACD":
            strategy_params = {"fast_period": 12, "slow_period": 26, "signal_period": 9}
        
        # Konfiguracja strategii
        strategy_config = StrategyConfig(
            stop_loss_pips=50,
            take_profit_pips=100,
            position_size_pct=1.0,
            params=strategy_params
        )
        
        # Wybór strategii
        if strategy_name == "SMA":
            strategy = SimpleMovingAverageStrategy(config=strategy_config)
        elif strategy_name == "RSI":
            strategy = RSIStrategy(config=strategy_config)
        elif strategy_name == "BB":
            strategy = BollingerBandsStrategy(config=strategy_config)
        elif strategy_name == "MACD":
            strategy = MACDStrategy(config=strategy_config)
        elif strategy_name == "COMBINED":
            strategy = CombinedIndicatorsStrategy(config=strategy_config)
        else:
            logger.error(f"Nieznana strategia: {strategy_name}")
            return
        
        # Inicjalizacja silnika backtestingu
        engine = BacktestEngine(config=config, strategy=strategy)
        
        # Uruchomienie backtestingu
        logger.info("Rozpoczęcie backtestingu...")
        
        try:
            result = engine.run()
            
            # Generowanie raportu tylko jeśli backtest się powiódł
            if result and hasattr(result, 'metrics') and result.metrics:
                logger.info("Generowanie raportu...")
                
                try:
                    # Upewnij się, że katalog wynikowy istnieje
                    import os
                    os.makedirs("backtest_results", exist_ok=True)
                    
                    output_path = f"backtest_results/{strategy_name}_{symbol}_{timeframe}_{days}days_report.html"
                    report_path = generate_report(result, output_path)
                    
                    logger.info(f"Backtest zakończony pomyślnie. Raport wygenerowany: {report_path}")
                    
                    # Wyświetlenie podstawowych statystyk
                    logger.info("\n=== PODSTAWOWE STATYSTYKI ===")
                    logger.info(f"Zysk/strata: {result.metrics['net_profit']:.2f} ({result.metrics['profit_factor']:.2f}x)")
                    logger.info(f"Drawdown: {result.metrics['max_drawdown_pct']:.2f}%")
                    logger.info(f"Liczba transakcji: {result.metrics['total_trades']}")
                    logger.info(f"Procent wygranych: {result.metrics['win_rate']*100:.2f}%")
                except Exception as e:
                    logger.error(f"Błąd podczas generowania raportu: {e}")
                    import traceback
                    logger.error(traceback.format_exc())
            else:
                logger.warning("Backtest nie zwrócił ważnych wyników, raport nie został wygenerowany.")
                
            return result
        except Exception as e:
            logger.error(f"Błąd podczas wykonywania backtestingu: {e}")
            logger.error("Spróbuj użyć innych parametrów lub innej pary walutowej.")
            return None
        
    except Exception as e:
        logger.error(f"Błąd podczas uruchamiania backtestingu: {e}")
        import traceback
        logger.error(traceback.format_exc())

async def main():
    """Główna funkcja startowa systemu."""
    # Parsowanie argumentów wiersza poleceń
    parser = argparse.ArgumentParser(description="AgentMT5 - System autonomicznego handlu")
    parser.add_argument('--backtest', action='store_true', help='Uruchom moduł backtestingu')
    parser.add_argument('--symbol', type=str, help='Symbol instrumentu dla backtestingu (np. EURUSD)')
    parser.add_argument('--timeframe', type=str, help='Timeframe dla backtestingu (np. H1, M15)')
    parser.add_argument('--days', type=int, help='Liczba dni dla backtestingu')
    parser.add_argument('--strategy', type=str, help='Strategia dla backtestingu (SMA, RSI, BB, MACD, COMBINED)')
    
    args = parser.parse_args()
    
    # Jeśli wybrano tryb backtestingu
    if args.backtest:
        logger.info("Uruchamianie w trybie backtestingu")
        await run_backtest(args)
        return
    
    try:
        # Import komponentów systemu
        from src.mt5_bridge.server import create_server
        from src.agent_controller import get_agent_controller
        
        # Konfiguracja serwera
        host = '127.0.0.1'  # Używamy localhost dla bezpieczeństwa
        port = find_free_port(5555)  # Zaczynamy od portu 5555
        
        logger.info("Uruchamianie systemu AgentMT5...")
        logger.info(f"Konfiguracja serwera: {host}:{port}")
        
        # Zapisz port do zmiennej środowiskowej
        os.environ["SERVER_URL"] = f"http://{host}:{port}"
        
        # Uruchomienie serwera HTTP
        async with create_server(host, port) as server:
            logger.info("Serwer HTTP uruchomiony pomyślnie")
            
            # Inicjalizacja kontrolera agenta
            logger.info("Inicjalizacja kontrolera agenta")
            agent_controller = get_agent_controller()
            
            # Ustawienie kontrolera agenta w serwerze
            logger.info("Konfiguracja kontrolera agenta w serwerze")
            server.set_agent_controller(agent_controller)
            
            # Uruchomienie interfejsu użytkownika Streamlit w osobnym procesie
            ui_process = None
            agent_process = None
            try:
                ui_path = project_root / 'src' / 'ui' / 'app.py'
                logger.info(f"Uruchamianie interfejsu użytkownika: {ui_path}")
                
                # Uruchom Streamlit
                python_exe = sys.executable  # Pobierz pełną ścieżkę do interpretera Pythona
                ui_process = subprocess.Popen(
                    [python_exe, '-m', 'streamlit', 'run', str(ui_path)],
                    env=os.environ
                )
                
                logger.info("Interfejs użytkownika uruchomiony pomyślnie")
                
                # Uruchomienie agenta w trybie obserwacji
                logger.info("Uruchamianie agenta w trybie automatycznym")
                agent_controller.start_agent(mode="automatic")
                logger.info("Agent uruchomiony pomyślnie")
                
                # Czekaj na sygnał zakończenia
                try:
                    await asyncio.Event().wait()
                except KeyboardInterrupt:
                    logger.info("Otrzymano sygnał zakończenia...")
            finally:
                # Zatrzymaj agenta, jeśli został uruchomiony
                if agent_controller:
                    logger.info("Zatrzymywanie agenta...")
                    agent_controller.stop_agent()
                    logger.info("Agent zatrzymany")
                
                # Zatrzymaj proces UI, jeśli został uruchomiony
                if ui_process:
                    logger.info("Zatrzymywanie interfejsu użytkownika...")
                    ui_process.terminate()
                    ui_process.wait()
                    logger.info("Interfejs użytkownika zatrzymany")
    
    except Exception as e:
        logger.error(f"Błąd podczas uruchamiania systemu: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    # Utwórz katalog logów jeśli nie istnieje
    os.makedirs("logs", exist_ok=True)
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("System zatrzymany przez użytkownika")
    except Exception as e:
        logger.error(f"Nieoczekiwany błąd: {e}", exc_info=True)
        sys.exit(1) 