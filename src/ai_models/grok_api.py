#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Moduł integracji z API Grok (xAI).

Ten moduł zawiera funkcje i klasy potrzebne do komunikacji z modelem Grok
poprzez xAI API. Obsługuje wysyłanie zapytań, przetwarzanie odpowiedzi
oraz zarządzanie limitami API.
"""

import os
import json
import time
import logging
import requests
from typing import Dict, List, Optional, Union, Any
from datetime import datetime

# Konfiguracja loggera
logger = logging.getLogger('trading_agent.ai_models.grok')


class GrokAPI:
    """Klasa obsługująca komunikację z API Grok."""
    
    _instance = None
    
    def __new__(cls):
        """Implementacja wzorca Singleton."""
        if cls._instance is None:
            cls._instance = super(GrokAPI, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """Inicjalizacja klienta API Grok."""
        if self._initialized:
            return
            
        self._initialized = True
        self.api_key = os.getenv('XAI_API_KEY')
        
        if not self.api_key:
            logger.error("Nie znaleziono klucza API Grok (XAI_API_KEY)")
            raise ValueError("Brak klucza API Grok w zmiennych środowiskowych")
            
        self.api_url = "https://api.groq.com/openai/v1/chat/completions"
        self.model = "grok-1"  # Domyślny model
        self.max_tokens = 4096
        self.temperature = 0.7
        self.max_retries = 3
        self.retry_delay = 2
        
        logger.info("Inicjalizacja klienta Grok API")
        
    def set_model(self, model_name: str) -> None:
        """
        Ustawia model Grok do użycia.
        
        Args:
            model_name: Nazwa modelu Grok (np. 'grok-1')
        """
        self.model = model_name
        logger.info(f"Ustawiono model Grok: {model_name}")
        
    def set_parameters(self, max_tokens: int = None, temperature: float = None) -> None:
        """
        Ustawia parametry generowania.
        
        Args:
            max_tokens: Maksymalna liczba tokenów w odpowiedzi
            temperature: Temperatura (losowość) odpowiedzi (0.0-1.0)
        """
        if max_tokens is not None:
            self.max_tokens = max_tokens
        if temperature is not None:
            self.temperature = temperature
        
        logger.info(f"Ustawiono parametry Grok: max_tokens={self.max_tokens}, temperature={self.temperature}")
        
    def generate_response(self, prompt: str, system_prompt: str = None, max_tokens: int = None, 
                         temperature: float = None) -> Dict[str, Any]:
        """
        Generuje odpowiedź modelu Grok na podstawie podanego promptu.
        
        Args:
            prompt: Tekst zapytania
            system_prompt: Instrukcja systemowa dla modelu (opcjonalnie)
            max_tokens: Maksymalna liczba tokenów w odpowiedzi (opcjonalnie)
            temperature: Temperatura (losowość) odpowiedzi (0.0-1.0) (opcjonalnie)
            
        Returns:
            Dict zawierający odpowiedź i metadane
        """
        if max_tokens is None:
            max_tokens = self.max_tokens
        if temperature is None:
            temperature = self.temperature
            
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        messages = [{"role": "user", "content": prompt}]
        if system_prompt:
            messages.insert(0, {"role": "system", "content": system_prompt})
            
        data = {
            "model": self.model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature
        }
            
        attempts = 0
        while attempts < self.max_retries:
            try:
                start_time = time.time()
                response = requests.post(self.api_url, headers=headers, json=data)
                elapsed_time = time.time() - start_time
                
                response.raise_for_status()  # Zgłasza wyjątek dla kodów błędów HTTP
                response_data = response.json()
                
                logger.info(f"Odpowiedź Grok otrzymana w {elapsed_time:.2f}s")
                
                # Przygotowanie wyniku w standardowym formacie
                result = {
                    "success": True,
                    "text": response_data["choices"][0]["message"]["content"],
                    "model": self.model,
                    "tokens_used": response_data.get("usage", {}).get("total_tokens", 0),
                    "input_tokens": response_data.get("usage", {}).get("prompt_tokens", 0),
                    "output_tokens": response_data.get("usage", {}).get("completion_tokens", 0),
                    "response_time": elapsed_time,
                    "finish_reason": response_data["choices"][0].get("finish_reason", "unknown"),
                    "raw_response": response_data,
                    "timestamp": datetime.now().isoformat() if hasattr(datetime, 'now') else time.strftime("%Y-%m-%dT%H:%M:%S")
                }
                
                return result
                
            except requests.exceptions.HTTPError as e:
                attempts += 1
                try:
                    status_code = e.response.status_code if hasattr(e, 'response') and e.response else "unknown"
                    error_text = e.response.text if hasattr(e, 'response') and e.response else str(e)
                except:
                    status_code = "unknown"
                    error_text = str(e)
                
                logger.warning(f"Błąd HTTP Grok API ({attempts}/{self.max_retries}): {status_code} - {error_text}")
                
                if status_code == 429:  # Too Many Requests
                    # Jeśli przekroczono limit zapytań, czekamy dłużej
                    time.sleep(self.retry_delay * 3)
                else:
                    time.sleep(self.retry_delay)
                    
                if attempts >= self.max_retries:
                    logger.error(f"Przekroczono liczbę prób dla Grok API: {error_text}")
                    return {
                        "success": False,
                        "error": f"{status_code} {error_text}",
                        "timestamp": datetime.now().isoformat() if hasattr(datetime, 'now') else time.strftime("%Y-%m-%dT%H:%M:%S")
                    }
                    
            except requests.exceptions.RequestException as e:
                attempts += 1
                logger.warning(f"Błąd połączenia Grok API ({attempts}/{self.max_retries}): {str(e)}")
                time.sleep(self.retry_delay)
                
                if attempts >= self.max_retries:
                    logger.error(f"Przekroczono liczbę prób dla Grok API: {str(e)}")
                    return {
                        "success": False,
                        "error": str(e),
                        "timestamp": datetime.now().isoformat() if hasattr(datetime, 'now') else time.strftime("%Y-%m-%dT%H:%M:%S")
                    }
            
            except Exception as e:
                logger.error(f"Nieoczekiwany błąd Grok API: {str(e)}")
                return {
                    "success": False,
                    "error": str(e),
                    "timestamp": datetime.now().isoformat() if hasattr(datetime, 'now') else time.strftime("%Y-%m-%dT%H:%M:%S")
                }
                
    def analyze_market_data(self, market_data: Dict[str, Any], analysis_type: str) -> Dict[str, Any]:
        """
        Analizuje dane rynkowe za pomocą Grok.
        
        Args:
            market_data: Słownik zawierający dane rynkowe do analizy
            analysis_type: Rodzaj analizy (np. 'sentiment', 'trend', 'signal')
            
        Returns:
            Dict zawierający wyniki analizy
        """
        # Wsparcie dla nieznanych typów analizy
        if analysis_type not in ["technical", "fundamental", "sentiment", "complete"]:
            logger.warning(f"Nieznany typ analizy: {analysis_type}, używam typu 'complete'")
            analysis_type = "complete"
            
        prompt = self._create_market_analysis_prompt(market_data, analysis_type)
        system_prompt = "Jesteś asystentem tradingowym specjalizującym się w analizie rynków finansowych. Twoja rola to precyzyjna analiza danych i przedstawienie konkretnej oceny."
        
        try:
            response = self.generate_response(prompt, system_prompt=system_prompt)
            
            if not response.get("success", False):
                return response
                
            # Próbujemy sparsować odpowiedź jako JSON
            try:
                analysis_result = json.loads(response["text"])
                result = {
                    "success": True,
                    "model": "grok",
                    "analysis": analysis_result,
                    "analysis_type": analysis_type,
                    "response_time": response["response_time"],
                    "timestamp": response.get("timestamp", datetime.now().isoformat() if hasattr(datetime, 'now') else time.strftime("%Y-%m-%dT%H:%M:%S"))
                }
                return result
            except json.JSONDecodeError as e:
                # Jeśli nie udało się sparsować jako JSON, zwracamy tekst
                logger.error(f"Błąd podczas analizy rynku: {str(e)}")
                return {
                    "success": True,
                    "model": "grok",
                    "analysis": response["text"],
                    "analysis_type": analysis_type,
                    "response_time": response["response_time"],
                    "format_error": "Odpowiedź nie jest w formacie JSON",
                    "timestamp": response.get("timestamp", datetime.now().isoformat() if hasattr(datetime, 'now') else time.strftime("%Y-%m-%dT%H:%M:%S"))
                }
        except Exception as e:
            logger.error(f"Błąd podczas analizy rynku: {str(e)}")
            return {
                "success": False,
                "error": f"Błąd podczas analizy rynku: {str(e)}",
                "timestamp": datetime.now().isoformat() if hasattr(datetime, 'now') else time.strftime("%Y-%m-%dT%H:%M:%S")
            }
    
    def generate_trading_decision(self, market_data: Dict[str, Any], 
                            risk_parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generuje decyzję handlową na podstawie danych rynkowych i parametrów ryzyka.
        
        Args:
            market_data: Słownik zawierający dane rynkowe
            risk_parameters: Słownik zawierający parametry zarządzania ryzykiem
            
        Returns:
            Dict zawierający decyzję handlową
        """
        prompt = self._create_trading_decision_prompt(market_data, risk_parameters)
        system_prompt = "Jesteś asystentem tradingowym specjalizującym się w analizie rynków finansowych i podejmowaniu decyzji. Twoja rola to precyzyjna ocena sytuacji rynkowej i przedstawienie konkretnej decyzji handlowej."
        
        try:
            response = self.generate_response(prompt, system_prompt=system_prompt)
            
            if not response.get("success", False):
                return response
                
            # Próbujemy sparsować odpowiedź jako JSON
            try:
                decision = json.loads(response["text"])
                result = {
                    "success": True,
                    "model": "grok",
                    "decision": decision,
                    "response_time": response["response_time"],
                    "timestamp": response.get("timestamp", datetime.now().isoformat() if hasattr(datetime, 'now') else time.strftime("%Y-%m-%dT%H:%M:%S"))
                }
                return result
            except json.JSONDecodeError as e:
                # Jeśli nie udało się sparsować jako JSON, zwracamy tekst
                logger.error(f"Błąd podczas generowania decyzji handlowej: {str(e)}")
                return {
                    "success": False,
                    "model": "grok",
                    "raw_response": response["text"],
                    "error": "Odpowiedź nie jest w prawidłowym formacie JSON",
                    "timestamp": response.get("timestamp", datetime.now().isoformat() if hasattr(datetime, 'now') else time.strftime("%Y-%m-%dT%H:%M:%S"))
                }
        except Exception as e:
            logger.error(f"Błąd podczas generowania decyzji handlowej: {str(e)}")
            return {
                "success": False,
                "error": f"Błąd podczas generowania decyzji handlowej: {str(e)}",
                "timestamp": datetime.now().isoformat() if hasattr(datetime, 'now') else time.strftime("%Y-%m-%dT%H:%M:%S")
            }
    
    def _create_market_analysis_prompt(self, market_data: Dict[str, Any], 
                                     analysis_type: str) -> str:
        """
        Tworzy prompt do analizy rynku.
        
        Args:
            market_data: Dane rynkowe
            analysis_type: Rodzaj analizy
            
        Returns:
            String zawierający prompt
        """
        # Konwertujemy dane rynkowe do formatu JSON
        market_data_json = json.dumps(market_data, indent=2)
        
        prompts = {
            "sentiment": f"""Przeanalizuj poniższe dane rynkowe i określ sentyment rynku (bullish, bearish, neutral) 
                        z wartością liczbową od -1.0 (skrajnie bearish) do 1.0 (skrajnie bullish).
                        Zwróć wynik w formacie JSON zawierający sentyment, wartość liczbową i krótkie uzasadnienie.
                        
                        Dane rynkowe:
                        {market_data_json}
                        
                        Odpowiedź w formacie JSON:""",
                        
            "trend": f"""Przeanalizuj poniższe dane rynkowe i określ trend (uptrend, downtrend, sideways) 
                    oraz jego siłę od 0.0 (brak trendu) do 1.0 (silny trend).
                    Zwróć wynik w formacie JSON zawierający trend, siłę i krótkie uzasadnienie.
                    
                    Dane rynkowe:
                    {market_data_json}
                    
                    Odpowiedź w formacie JSON:""",
                    
            "signal": f"""Przeanalizuj poniższe dane rynkowe i wygeneruj sygnał handlowy (buy, sell, hold) 
                     wraz z poziomem pewności od 0.0 (brak pewności) do 1.0 (pełna pewność).
                     Zwróć wynik w formacie JSON zawierający sygnał, pewność i krótkie uzasadnienie.
                     
                     Dane rynkowe:
                     {market_data_json}
                     
                     Odpowiedź w formacie JSON:""",
                     
            "complete": f"""Przeprowadź pełną analizę poniższych danych rynkowych, zawierającą:
                       1. Sentyment rynku (-1.0 do 1.0)
                       2. Trend (uptrend, downtrend, sideways) i jego siłę (0.0-1.0)
                       3. Sygnał handlowy (buy, sell, hold) z poziomem pewności (0.0-1.0)
                       4. Zalecane poziomy SL/TP
                       5. Krótkie uzasadnienie analizy
                       
                       Dane rynkowe:
                       {market_data_json}
                       
                       Odpowiedź w formacie JSON:"""
        }
        
        if analysis_type in prompts:
            return prompts[analysis_type]
        else:
            logger.warning(f"Nieznany typ analizy: {analysis_type}, używam typu 'complete'")
            return prompts["complete"]
    
    def _create_trading_decision_prompt(self, market_data: Dict[str, Any], 
                                      risk_parameters: Dict[str, Any]) -> str:
        """
        Tworzy prompt do generowania decyzji handlowej.
        
        Args:
            market_data: Dane rynkowe
            risk_parameters: Parametry zarządzania ryzykiem
            
        Returns:
            String zawierający prompt
        """
        market_data_json = json.dumps(market_data, indent=2)
        risk_parameters_json = json.dumps(risk_parameters, indent=2)
        
        prompt = f"""Na podstawie poniższych danych rynkowych i parametrów ryzyka, 
                wygeneruj decyzję handlową zawierającą:
                1. Akcję (buy, sell, hold, close)
                2. Symbol instrumentu
                3. Wielkość pozycji (w lotach)
                4. Poziom stop-loss
                5. Poziom take-profit
                6. Poziom pewności (0.0-1.0)
                7. Zwięzłe uzasadnienie
                
                Dane rynkowe:
                {market_data_json}
                
                Parametry ryzyka:
                {risk_parameters_json}
                
                Odpowiedź w formacie JSON:"""
                
        return prompt


def get_grok_api() -> GrokAPI:
    """
    Zwraca instancję GrokAPI.
    
    Returns:
        Instancja GrokAPI
    """
    return GrokAPI() 