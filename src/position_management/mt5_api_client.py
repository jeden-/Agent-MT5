import json
import logging
import requests
from typing import Dict, List, Optional, Any, Union
from datetime import datetime

# Konfiguracja loggera
logger = logging.getLogger(__name__)

class MT5ApiClient:
    """Klient API do komunikacji z MT5 poprzez HTTP."""
    
    def __init__(self, server_url: str, timeout: int = 10):
        """
        Inicjalizacja klienta API.
        
        Args:
            server_url: Adres URL serwera HTTP MT5
            timeout: Timeout dla żądań HTTP w sekundach
        """
        self.server_url = server_url.rstrip('/')
        self.timeout = timeout
        logger.info(f"MT5ApiClient zainicjalizowany z adresem {server_url}")
    
    def _make_request(self, method: str, endpoint: str, params: Dict = None, data: Dict = None) -> Dict:
        """
        Wykonuje żądanie HTTP do serwera MT5.
        
        Args:
            method: Metoda HTTP (GET, POST, itp.)
            endpoint: Endpoint API
            params: Parametry URL (dla GET)
            data: Dane do wysłania (dla POST)
            
        Returns:
            Odpowiedź w formie słownika
            
        Raises:
            Exception: Gdy wystąpi błąd podczas komunikacji
        """
        url = f"{self.server_url}/{endpoint.lstrip('/')}"
        
        try:
            if method.upper() == 'GET':
                response = requests.get(url, params=params, timeout=self.timeout)
            elif method.upper() == 'POST':
                response = requests.post(url, json=data, timeout=self.timeout)
            else:
                raise ValueError(f"Nieobsługiwana metoda HTTP: {method}")
            
            # Sprawdzenie statusu
            response.raise_for_status()
            
            # Parsowanie odpowiedzi JSON
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Błąd podczas wykonywania żądania {method} {url}: {e}")
            raise Exception(f"Błąd komunikacji z serwerem MT5: {e}")
        except json.JSONDecodeError as e:
            logger.error(f"Błąd parsowania odpowiedzi JSON: {e}")
            raise Exception(f"Nieprawidłowa odpowiedź z serwera MT5: {e}")
    
    def get_active_positions(self, ea_id: str) -> List[Dict]:
        """
        Pobiera aktywne pozycje dla danego EA.
        
        Args:
            ea_id: Identyfikator EA
            
        Returns:
            Lista pozycji jako słowniki
        """
        endpoint = "positions"
        params = {"ea_id": ea_id, "status": "active"}
        
        try:
            response = self._make_request("GET", endpoint, params=params)
            return response.get("positions", [])
        except Exception as e:
            logger.error(f"Błąd podczas pobierania aktywnych pozycji dla EA {ea_id}: {e}")
            return []
    
    def get_position(self, ea_id: str, ticket: int) -> Optional[Dict]:
        """
        Pobiera dane pojedynczej pozycji.
        
        Args:
            ea_id: Identyfikator EA
            ticket: Numer ticketu pozycji
            
        Returns:
            Dane pozycji jako słownik lub None, jeśli pozycja nie istnieje
        """
        endpoint = f"position/{ticket}"
        params = {"ea_id": ea_id}
        
        try:
            response = self._make_request("GET", endpoint, params=params)
            return response.get("position")
        except Exception as e:
            logger.error(f"Błąd podczas pobierania pozycji {ticket} dla EA {ea_id}: {e}")
            return None
    
    def get_closed_position(self, ea_id: str, ticket: int) -> Optional[Dict]:
        """
        Pobiera dane zamkniętej pozycji.
        
        Args:
            ea_id: Identyfikator EA
            ticket: Numer ticketu pozycji
            
        Returns:
            Dane zamkniętej pozycji jako słownik lub None, jeśli pozycja nie istnieje
        """
        endpoint = f"position/history/{ticket}"
        params = {"ea_id": ea_id}
        
        try:
            response = self._make_request("GET", endpoint, params=params)
            return response.get("position")
        except Exception as e:
            logger.error(f"Błąd podczas pobierania zamkniętej pozycji {ticket} dla EA {ea_id}: {e}")
            return None
    
    def open_position(self, ea_id: str, order_data: Dict) -> Optional[Dict]:
        """
        Otwiera nową pozycję.
        
        Args:
            ea_id: Identyfikator EA
            order_data: Dane zlecenia (symbol, type, volume, price, sl, tp, itp.)
            
        Returns:
            Dane nowej pozycji jako słownik lub None, jeśli wystąpił błąd
        """
        endpoint = "position/open"
        data = {**order_data, "ea_id": ea_id}
        
        try:
            response = self._make_request("POST", endpoint, data=data)
            return response.get("position")
        except Exception as e:
            logger.error(f"Błąd podczas otwierania pozycji dla EA {ea_id}: {e}")
            return None
    
    def close_position(self, ea_id: str, ticket: int, volume: float = None) -> bool:
        """
        Zamyka pozycję.
        
        Args:
            ea_id: Identyfikator EA
            ticket: Numer ticketu pozycji
            volume: Ilość do zamknięcia (None = cała pozycja)
            
        Returns:
            True, jeśli pozycja została zamknięta, False w przeciwnym razie
        """
        endpoint = "position/close"
        data = {
            "ea_id": ea_id,
            "ticket": ticket
        }
        
        if volume is not None:
            data["volume"] = volume
        
        try:
            response = self._make_request("POST", endpoint, data=data)
            return response.get("success", False)
        except Exception as e:
            logger.error(f"Błąd podczas zamykania pozycji {ticket} dla EA {ea_id}: {e}")
            return False
    
    def modify_position(self, ea_id: str, ticket: int, sl: float = None, tp: float = None) -> bool:
        """
        Modyfikuje parametry pozycji.
        
        Args:
            ea_id: Identyfikator EA
            ticket: Numer ticketu pozycji
            sl: Nowy poziom Stop Loss (None = bez zmian)
            tp: Nowy poziom Take Profit (None = bez zmian)
            
        Returns:
            True, jeśli pozycja została zmodyfikowana, False w przeciwnym razie
        """
        endpoint = "position/modify"
        data = {
            "ea_id": ea_id,
            "ticket": ticket
        }
        
        if sl is not None:
            data["sl"] = sl
        
        if tp is not None:
            data["tp"] = tp
        
        try:
            response = self._make_request("POST", endpoint, data=data)
            return response.get("success", False)
        except Exception as e:
            logger.error(f"Błąd podczas modyfikacji pozycji {ticket} dla EA {ea_id}: {e}")
            return False
    
    def get_account_info(self, ea_id: str) -> Optional[Dict]:
        """
        Pobiera informacje o koncie.
        
        Args:
            ea_id: Identyfikator EA
            
        Returns:
            Informacje o koncie jako słownik lub None, jeśli wystąpił błąd
        """
        endpoint = "account/info"
        params = {"ea_id": ea_id}
        
        try:
            response = self._make_request("GET", endpoint, params=params)
            return response.get("account_info")
        except Exception as e:
            logger.error(f"Błąd podczas pobierania informacji o koncie dla EA {ea_id}: {e}")
            return None
    
    def get_market_data(self, ea_id: str, symbol: str) -> Optional[Dict]:
        """
        Pobiera dane rynkowe dla danego instrumentu.
        
        Args:
            ea_id: Identyfikator EA
            symbol: Symbol instrumentu
            
        Returns:
            Dane rynkowe jako słownik lub None, jeśli wystąpił błąd
        """
        endpoint = "market/data"
        params = {"ea_id": ea_id, "symbol": symbol}
        
        try:
            response = self._make_request("GET", endpoint, params=params)
            return response.get("market_data")
        except Exception as e:
            logger.error(f"Błąd podczas pobierania danych rynkowych dla symbolu {symbol}, EA {ea_id}: {e}")
            return None 