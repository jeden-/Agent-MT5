"""
Skrypt startowy systemu AgentMT5.
"""

import os
import sys
import asyncio
import logging
import socket
import subprocess
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

async def main():
    """Główna funkcja startowa systemu."""
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