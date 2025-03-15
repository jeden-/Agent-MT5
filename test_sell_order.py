import logging
import sys
from datetime import datetime
import MetaTrader5 as mt5
from src.utils.patches import apply_patch_for_mt5_connector
from src.mt5_bridge.trading_service import TradingService
import os
from dotenv import load_dotenv

# Konfiguracja loggera
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# Ładowanie zmiennych środowiskowych
load_dotenv()

def test_sell_order():
    """Test dla poprawionej obsługi zleceń SELL."""
    
    # Upewnij się, że MT5 jest zainicjalizowane
    logger.info("Inicjalizacja połączenia z MT5...")
    if not mt5.initialize():
        logger.error("Nie można zainicjalizować MT5")
        sys.exit(1)
    
    logger.info(f"Połączono z MT5: {mt5.version()}")
    
    # Logowanie do konta demo
    account = int(os.getenv("MT5_LOGIN", "62499981"))  # ID konta demo
    password = os.getenv("MT5_PASSWORD", "mVBu5x!3")  # Hasło
    server = os.getenv("MT5_SERVER", "OANDATMS-MT5")  # Serwer

    logger.info(f"Próba logowania do MT5 na konto {account} na serwerze {server}")

    if not mt5.login(account, password, server):
        logger.error(f"Nie można zalogować się do MT5: {mt5.last_error()}")
        mt5.shutdown()
        sys.exit(1)
    
    logger.info("Zalogowano do MT5")
    
    # Inicjalizacja trading service
    trading_service = TradingService()
    
    # Zastosuj łatkę
    logger.info("Aplikowanie łatki dla MT5Connector...")
    patched = apply_patch_for_mt5_connector()
    
    if not patched:
        logger.error("Nie można zaaplikować łatki")
        return False
    
    logger.info("Łatka zaaplikowana")
    
    # Testowanie zlecenia SELL
    logger.info("Testowanie zlecenia SELL dla SILVER...")
    
    # Pobranie aktualnych danych rynkowych
    symbol_info = mt5.symbol_info("SILVER")
    if not symbol_info:
        logger.error("Nie można pobrać informacji o SILVER")
        return False
    
    current_price = mt5.symbol_info_tick("SILVER").bid
    sl = current_price + 1.0  # 1 USD powyżej ceny rynkowej
    tp = current_price - 1.0  # 1 USD poniżej ceny rynkowej
    
    logger.info(f"Aktualna cena SILVER: {current_price}, SL: {sl}, TP: {tp}")
    
    order_ticket = trading_service.open_position(
        symbol="SILVER",
        direction="SELL",  # Wielkie litery
        lot_size=0.1,
        entry_price=current_price,
        stop_loss=sl,
        take_profit=tp,
        comment="Test SELL z wielkimi literami",
        magic=12345
    )
    
    if not order_ticket:
        logger.error("Nie można otworzyć pozycji SELL dla SILVER")
        return False
    
    logger.info(f"Pomyślnie otwarto pozycję SELL dla SILVER, ticket: {order_ticket}")
    return True

if __name__ == "__main__":
    logger.info("Rozpoczęcie testu zlecenia SELL...")
    result = test_sell_order()
    if result:
        logger.info("Test zakończony sukcesem!")
    else:
        logger.error("Test zakończony niepowodzeniem!")
    
    # Zamknięcie połączenia
    mt5.shutdown() 