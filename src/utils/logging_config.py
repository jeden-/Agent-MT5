import os
import logging
import logging.handlers
from datetime import datetime

# Tworzenie katalogu logs, jeśli nie istnieje
log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'logs')
os.makedirs(log_dir, exist_ok=True)

# Generowanie nazwy pliku z timestampem
log_filename = os.path.join(log_dir, f'app_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')

# Konfiguracja podstawowego loggera
def configure_logging(log_level=logging.INFO):
    # Konfiguracja handlera pliku
    file_handler = logging.FileHandler(log_filename, encoding='utf-8')
    file_handler.setLevel(log_level)
    
    # Format logów
    log_format = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    file_handler.setFormatter(log_format)
    
    # Konfiguracja handlera konsoli
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_handler.setFormatter(log_format)
    
    # Konfiguracja głównego loggera
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # Usunięcie istniejących handlerów, aby uniknąć duplikacji
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Dodanie nowych handlerów
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    
    # Utworzenie specjalnego loggera dla sesji aplikacji
    session_logger = logging.getLogger("app_session")
    session_logger.info(f"Rozpoczęto nową sesję aplikacji, logi zapisywane do: {log_filename}")

# Funkcja do uzyskania aktualnej ścieżki pliku logów
def get_current_log_path():
    return log_filename

# Funkcja do czytania ostatnich n linii z pliku logów
def read_recent_logs(lines=100):
    try:
        with open(log_filename, 'r', encoding='utf-8') as f:
            all_lines = f.readlines()
            return all_lines[-lines:] if len(all_lines) > lines else all_lines
    except Exception as e:
        return [f"Błąd odczytu logów: {str(e)}"] 