#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Moduł integracji z API Claude (Anthropic).

Ten moduł zawiera funkcje i klasy potrzebne do komunikacji z modelem Claude
poprzez Anthropic API. Obsługuje wysyłanie zapytań, przetwarzanie odpowiedzi
oraz zarządzanie limitami API.
"""

import os
import json
import time
import logging
from typing import Dict, List, Optional, Union, Any
import anthropic
from anthropic import Anthropic, HUMAN_PROMPT, AI_PROMPT

# Konfiguracja loggera
logger = logging.getLogger('trading_agent.ai_models.claude')


class ClaudeAPI:
    """Klasa obsługująca komunikację z API Claude."""
    
    _instance = None
    
    def __new__(cls):
        """Implementacja wzorca Singleton."""
        if cls._instance is None:
            cls._instance = super(ClaudeAPI, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """Inicjalizacja klienta API Claude."""
        if self._initialized:
            return
            
        self._initialized = True
        self.api_key = os.getenv('ANTHROPIC_API_KEY')
        
        if not self.api_key:
            logger.error("Nie znaleziono klucza API Claude (ANTHROPIC_API_KEY)")
            raise ValueError("Brak klucza API Claude w zmiennych środowiskowych")
            
        self.client = Anthropic(api_key=self.api_key)
        self.model = "claude-3-opus-20240229"  # Domyślny model
        self.max_tokens = 4096
        self.temperature = 0.7
        self.max_retries = 3
        self.retry_delay = 2
        
        logger.info("Inicjalizacja klienta Claude API")
        
    def set_model(self, model_name: str) -> None:
        """
        Ustawia model Claude do użycia.
        
        Args:
            model_name: Nazwa modelu Claude (np. 'claude-3-opus-20240229', 'claude-3-sonnet-20240229')
        """
        self.model = model_name
        logger.info(f"Ustawiono model Claude: {model_name}")
        
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
        
        logger.info(f"Ustawiono parametry Claude: max_tokens={self.max_tokens}, temperature={self.temperature}")
        
    def generate_response(self, prompt: str, system_prompt: str = None, max_tokens: int = None, 
                         temperature: float = None) -> Dict[str, Any]:
        """
        Generuje odpowiedź modelu Claude na podstawie podanego promptu.
        
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
            
        attempts = 0
        while attempts < self.max_retries:
            try:
                messages = [{"role": "user", "content": prompt}]
                
                params = {
                    "model": self.model,
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                    "messages": messages
                }
                
                if system_prompt:
                    params["system"] = system_prompt
                
                start_time = time.time()
                response = self.client.messages.create(**params)
                elapsed_time = time.time() - start_time
                
                logger.info(f"Odpowiedź Claude otrzymana w {elapsed_time:.2f}s")
                
                result = {
                    "text": response.content[0].text,
                    "model": self.model,
                    "tokens_used": response.usage.input_tokens + response.usage.output_tokens,
                    "input_tokens": response.usage.input_tokens,
                    "output_tokens": response.usage.output_tokens,
                    "response_time": elapsed_time,
                    "finish_reason": response.stop_reason,
                    "raw_response": response
                }
                
                return result
                
            except anthropic.APIError as e:
                attempts += 1
                logger.warning(f"Błąd API Claude ({attempts}/{self.max_retries}): {str(e)}")
                
                if "rate_limit" in str(e).lower():
                    # Jeśli przekroczono limit zapytań, czekamy dłużej
                    time.sleep(self.retry_delay * 2)
                else:
                    time.sleep(self.retry_delay)
                    
                if attempts >= self.max_retries:
                    logger.error(f"Przekroczono liczbę prób dla Claude API: {str(e)}")
                    raise e
            
            except Exception as e:
                logger.error(f"Nieoczekiwany błąd Claude API: {str(e)}")
                raise e
                
    def analyze_market_data(self, market_data: Dict[str, Any], analysis_type: str) -> Dict[str, Any]:
        """
        Analizuje dane rynkowe za pomocą Claude.
        
        Args:
            market_data: Słownik zawierający dane rynkowe do analizy
            analysis_type: Rodzaj analizy (np. 'sentiment', 'trend', 'signal')
            
        Returns:
            Dict zawierający wyniki analizy
        """
        prompt = self._create_market_analysis_prompt(market_data, analysis_type)
        system_prompt = "Jesteś asystentem tradingowym specjalizującym się w analizie rynków finansowych. Twoja rola to precyzyjna analiza danych i przedstawienie konkretnej oceny."
        
        response = self.generate_response(prompt, system_prompt=system_prompt)
        
        # Próbujemy sparsować odpowiedź jako JSON
        try:
            analysis_result = json.loads(response["text"])
            analysis_result["model"] = "claude"
            analysis_result["response_time"] = response["response_time"]
            return analysis_result
        except json.JSONDecodeError:
            # Jeśli nie udało się sparsować jako JSON, zwracamy tekst
            return {
                "model": "claude",
                "analysis": response["text"],
                "analysis_type": analysis_type,
                "response_time": response["response_time"],
                "format_error": "Odpowiedź nie jest w formacie JSON"
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
        system_prompt = """Jesteś zaawansowanym systemem wspomagania decyzji tradingowych. 
        Twoja rola to analiza danych rynkowych i generowanie precyzyjnych decyzji handlowych 
        z uwzględnieniem zarządzania ryzykiem. Zwracaj decyzje w formacie JSON."""
        
        response = self.generate_response(prompt, system_prompt=system_prompt)
        
        # Próbujemy sparsować odpowiedź jako JSON
        try:
            decision = json.loads(response["text"])
            decision["model"] = "claude"
            decision["response_time"] = response["response_time"]
            return decision
        except json.JSONDecodeError:
            # Jeśli nie udało się sparsować jako JSON, logujemy błąd i tworzymy domyślną odpowiedź
            logger.error("Nie udało się sparsować odpowiedzi Claude jako JSON")
            return {
                "model": "claude",
                "action": "no_action",
                "confidence": 0.0,
                "reasoning": "Błąd parsowania odpowiedzi",
                "raw_response": response["text"],
                "response_time": response["response_time"],
                "error": True
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
    
    def analyze_market(self, symbol: str, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analizuje dane rynkowe dla danego symbolu.
        
        Args:
            symbol: Symbol instrumentu (np. 'EURUSD', 'GOLD')
            market_data: Słownik zawierający dane rynkowe (open, high, low, close, itp.)
            
        Returns:
            Dict zawierający wyniki analizy
        """
        logger.info(f"Analiza rynku {symbol} z użyciem Claude")
        
        # Dodajemy symbol do danych rynkowych
        market_data_with_symbol = market_data.copy()
        market_data_with_symbol['symbol'] = symbol
        
        # Delegujemy do analyze_market_data
        return self.analyze_market_data(market_data_with_symbol, "complete")


def get_claude_api() -> ClaudeAPI:
    """
    Zwraca instancję ClaudeAPI.
    
    Returns:
        Instancja ClaudeAPI
    """
    return ClaudeAPI() 