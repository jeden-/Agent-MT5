#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Klient API do komunikacji z MT5.
Obsługuje komunikację HTTP z serwerem MT5.
"""

import os
import sys
import json
import time
import logging
import requests
from typing import Dict, Any, Optional, Union
from urllib.parse import urljoin

# Konfiguracja loggera
logger = logging.getLogger('mt5_api_client')

class MT5ApiClient:
    """Klient API do komunikacji z MT5."""
    
    def __init__(self, host: str = '127.0.0.1', port: int = 5555, timeout: int = 10):
        """
        Inicjalizacja klienta API.
        
        Args:
            host: Adres hosta MT5.
            port: Port MT5.
            timeout: Timeout dla połączeń w sekundach.
        """
        self.host = host
        self.port = port
        self.timeout = timeout
        self.base_url = f"http://{host}:{port}"
        logger.info(f"MT5ApiClient zainicjalizowany dla {host}:{port}")
    
    def send_request(self, endpoint: str, method: str = "GET", params: Dict[str, Any] = None, data: Dict[str, Any] = None) -> Optional[Dict[str, Any]]:
        """
        Wysyła żądanie do MT5 za pomocą HTTP.
        
        Args:
            endpoint: Ścieżka endpointu.
            method: Metoda HTTP (GET, POST).
            params: Parametry zapytania.
            data: Dane do wysłania w formacie JSON.
            
        Returns:
            Odpowiedź z serwera w formacie JSON lub None w przypadku błędu.
        """
        max_retries = 3
        retry_delay = 0.5  # Początkowe opóźnienie w sekundach
        last_exception = None
        
        for retry in range(max_retries + 1):
            try:
                url = urljoin(self.base_url, endpoint)
                logger.debug(f"Wysyłanie żądania {method} do {url} (próba {retry+1}/{max_retries+1})")
                
                if method.upper() == "GET":
                    response = requests.get(url, params=params, timeout=self.timeout)
                else:  # POST, PUT, itp.
                    headers = {'Content-Type': 'application/json'}
                    response = requests.post(url, params=params, json=data, headers=headers, timeout=self.timeout)
                
                response.raise_for_status()  # Zgłosi wyjątek dla kodów błędów HTTP
                
                # Dekoduj odpowiedź JSON
                try:
                    result = response.json()
                    logger.debug(f"Otrzymano odpowiedź: {result}")
                    return result
                except json.JSONDecodeError:
                    # Jeśli odpowiedź nie jest poprawnym JSON, ale ma status 200, zwróć tekst
                    if response.status_code == 200:
                        return {"text": response.text, "status": "ok"}
                    logger.error(f"Nie można zdekodować odpowiedzi JSON: {response.text}")
                    raise
                    
            except requests.exceptions.ConnectionError as e:
                logger.warning(f"Błąd połączenia z {url}: {e}")
                last_exception = e
            except requests.exceptions.Timeout as e:
                logger.warning(f"Timeout podczas łączenia z {url}: {e}")
                last_exception = e
            except requests.exceptions.HTTPError as e:
                logger.warning(f"Błąd HTTP podczas łączenia z {url}: {e}")
                last_exception = e
            except Exception as e:
                logger.error(f"Nieznany błąd podczas łączenia z {url}: {e}")
                last_exception = e
            
            # Jeśli to nie była ostatnia próba, czekaj i spróbuj ponownie
            if retry < max_retries:
                wait_time = retry_delay * (2 ** retry)  # Wykładnicze zwiększanie opóźnienia
                logger.info(f"Ponowna próba za {wait_time:.2f}s...")
                time.sleep(wait_time)
            else:
                logger.error(f"Wszystkie próby nieudane. Ostatni błąd: {last_exception}")
                return None
                
        return None  # Nigdy nie powinno tutaj dotrzeć, ale dla pewności
    
    def ping(self) -> bool:
        """
        Sprawdza połączenie z MT5.
        
        Returns:
            True jeśli połączenie działa, False w przeciwnym razie.
        """
        result = self.send_request("ping")
        return result is not None and result.get("status") == "ok"
    
    def get_status(self) -> Dict[str, Any]:
        """
        Pobiera status serwera MT5.
        
        Returns:
            Słownik ze statusem lub pusty słownik w przypadku błędu.
        """
        result = self.send_request("status")
        return result or {}
    
    def get_account_info(self) -> Dict[str, Any]:
        """
        Pobiera informacje o koncie MT5.
        
        Returns:
            Słownik z informacjami o koncie lub pusty słownik w przypadku błędu.
        """
        result = self.send_request("mt5/account")
        return result or {}
    
    def get_positions(self) -> Dict[str, Any]:
        """
        Pobiera aktywne pozycje z MT5.
        
        Returns:
            Słownik z pozycjami lub pusty słownik w przypadku błędu.
        """
        result = self.send_request("position/list")
        return result or {}

    def get_active_positions(self, ea_id: str = None) -> Dict[str, Any]:
        """
        Pobiera aktywne pozycje dla danego EA.
        
        Args:
            ea_id: Identyfikator EA (opcjonalny).
            
        Returns:
            Słownik z pozycjami lub pusty słownik w przypadku błędu.
        """
        params = {"ea_id": ea_id} if ea_id else None
        result = self.send_request("position/active", params=params)
        return result or {}

    def get_orders(self) -> Dict[str, Any]:
        """
        Pobiera aktywne zlecenia z MT5.
        
        Returns:
            Słownik ze zleceniami lub pusty słownik w przypadku błędu.
        """
        result = self.send_request("order/list")
        return result or {}

    def get_position(self, ea_id: str, ticket: int) -> Dict[str, Any]:
        """
        Pobiera informacje o konkretnej pozycji.
        
        Args:
            ea_id: Identyfikator EA.
            ticket: Numer ticketu pozycji.
            
        Returns:
            Słownik z informacjami o pozycji lub pusty słownik w przypadku błędu.
        """
        params = {"ea_id": ea_id, "ticket": ticket}
        result = self.send_request("position/get", params=params)
        return result or {}
        
    def get_closed_position(self, ea_id: str, ticket: int) -> Dict[str, Any]:
        """
        Pobiera informacje o zamkniętej pozycji.
        
        Args:
            ea_id: Identyfikator EA.
            ticket: Numer ticketu pozycji.
            
        Returns:
            Słownik z informacjami o zamkniętej pozycji lub pusty słownik w przypadku błędu.
        """
        params = {"ea_id": ea_id, "ticket": ticket}
        result = self.send_request("position/closed", params=params)
        return result or {}
        
    def get_market_data(self, symbol: str) -> Dict[str, Any]:
        """
        Pobiera dane rynkowe dla danego symbolu.
        
        Args:
            symbol: Symbol instrumentu.
            
        Returns:
            Słownik z danymi rynkowymi lub pusty słownik w przypadku błędu.
        """
        params = {"symbol": symbol}
        result = self.send_request("market_data/get", params=params)
        return result or {}
        
    def get_monitoring_connections(self) -> Dict[str, Any]:
        """
        Pobiera informacje o aktywnych połączeniach.
        
        Returns:
            Słownik z informacjami o połączeniach lub pusty słownik w przypadku błędu.
        """
        result = self.send_request("monitoring/connections")
        return result or {}
        
    def get_monitoring_alerts(self) -> Dict[str, Any]:
        """
        Pobiera informacje o alertach.
        
        Returns:
            Słownik z informacjami o alertach lub pusty słownik w przypadku błędu.
        """
        result = self.send_request("monitoring/alerts")
        return result or {}
        
    def get_monitoring_status(self) -> Dict[str, Any]:
        """
        Pobiera ogólny status systemu monitorowania.
        
        Returns:
            Słownik ze statusem lub pusty słownik w przypadku błędu.
        """
        result = self.send_request("monitoring/status")
        return result or {}

# Singleton dla klienta API
_mt5_api_client = None

def get_mt5_api_client(host: str = '127.0.0.1', port: int = 5555, force_new: bool = False) -> MT5ApiClient:
    """
    Zwraca singleton instancji MT5ApiClient.
    
    Args:
        host: Adres hosta MT5.
        port: Port MT5.
        force_new: Czy wymusić utworzenie nowej instancji.
        
    Returns:
        Instancja MT5ApiClient.
    """
    global _mt5_api_client
    
    # Zawsze używaj portu 5555, który wiemy, że działa
    port = 5555
    host = '127.0.0.1'
    
    # Utwórz nową instancję, jeśli jest wymuszona lub jeśli singleton nie istnieje
    if _mt5_api_client is None or force_new:
        _mt5_api_client = MT5ApiClient(host, port)
    # Aktualizuj host/port w istniejącej instancji, jeśli się zmieniły
    elif _mt5_api_client.host != host or _mt5_api_client.port != port:
        logger.info(f"Aktualizacja konfiguracji MT5ApiClient: {host}:{port}")
        _mt5_api_client = MT5ApiClient(host, port)
        
    return _mt5_api_client 