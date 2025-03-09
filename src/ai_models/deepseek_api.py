#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Moduł integrujący z modelami DeepSeek za pośrednictwem lokalnego Ollama.

Ten moduł zawiera funkcje i klasy niezbędne do komunikacji z modelami DeepSeek
poprzez lokalny serwer Ollama, w tym obsługę żądań, przetwarzanie odpowiedzi
i zarządzanie komunikacją.
"""

import os
import json
import time
import logging
import requests
import re
import threading
from typing import Dict, Any, List, Optional
from datetime import datetime

# Konfiguracja logowania
logger = logging.getLogger("DeepSeekAPI")
logger.setLevel(logging.INFO)

# Parametry połączenia z lokalnym Ollama
OLLAMA_API_URL = "http://localhost:11434/api/generate"
DEFAULT_MODEL = "deepseek-coder"


class DeepSeekAPI:
    """Klasa do komunikacji z API DeepSeek."""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        """Implementacja wzorca Singleton."""
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(DeepSeekAPI, cls).__new__(cls)
                cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """Inicjalizuje klienta DeepSeek API."""
        # Singleton pattern
        if self._initialized:
            return
        
        # Konfiguracja loggera
        self.logger = logging.getLogger("DeepSeekAPI")
        
        # Domyślne parametry
        self.model = "deepseek-coder"  # Domyślny model
        self.max_tokens = 2000
        self.temperature = 0.7
        self.top_p = 0.95
        self.frequency_penalty = 0
        self.presence_penalty = 0
        
        # Sprawdzenie dostępności Ollama
        try:
            response = requests.get("http://localhost:11434/api/tags")
            if response.status_code == 200:
                models = [model["name"] for model in response.json()["models"]]
                deepseek_models = [m for m in models if "deepseek" in m.lower()]
                
                if deepseek_models:
                    self.logger.info(f"Znaleziono modele DeepSeek w Ollama: {deepseek_models}\n")
                    self.model = deepseek_models[0]  # Używamy pierwszego znalezionego modelu DeepSeek
                else:
                    self.logger.warning("Nie znaleziono modeli DeepSeek w Ollama")
                    self.logger.info("Używanie domyślnego modelu: deepseek-coder")
            else:
                self.logger.warning(f"Błąd podczas sprawdzania dostępnych modeli: {response.status_code}")
                
        except requests.exceptions.RequestException as e:
            self.logger.warning("Nie można połączyć się z lokalnym Ollama")
            self.logger.info("Używanie domyślnego modelu: deepseek-coder")
        
        self.logger.info(f"Zainicjalizowano DeepSeekAPI z modelem {self.model}\n")
        self._initialized = True

    def set_model(self, model_name: str) -> None:
        """Ustawia model do wykorzystania w zapytaniach.
        
        Args:
            model_name: Nazwa modelu DeepSeek do wykorzystania
        """
        self.model = model_name
        self.logger.info(f"Ustawiono model na {model_name}")
        
    def set_parameters(self, max_tokens: int = None, temperature: float = None) -> None:
        """Ustawia parametry generowania odpowiedzi.
        
        Args:
            max_tokens: Maksymalna liczba tokenów w odpowiedzi
            temperature: Temperatura (losowość) odpowiedzi (0.0-1.0)
        """
        if max_tokens is not None:
            self.max_tokens = max_tokens
        if temperature is not None:
            self.temperature = temperature
        
        self.logger.info(f"Ustawiono parametry: max_tokens={self.max_tokens}, temperature={self.temperature}")
        
    def generate_response(self, prompt, system_prompt=None, max_tokens=None, temperature=None):
        """
        Generuje odpowiedź od modelu DeepSeek.
        
        Args:
            prompt (str): Zapytanie do modelu
            system_prompt (str, optional): Prompt systemowy
            max_tokens (int, optional): Maksymalna liczba tokenów w odpowiedzi
            temperature (float, optional): Temperatura (losowość) odpowiedzi
            
        Returns:
            dict: Odpowiedź od modelu lub informacja o błędzie
        """
        # Ustawienie parametrów
        max_tokens = max_tokens if max_tokens is not None else self.max_tokens
        temperature = temperature if temperature is not None else self.temperature
        
        # Przygotowanie danych do wysłania
        data = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "num_predict": max_tokens,
                "temperature": temperature
            }
        }
        
        # Dodanie system prompt, jeśli podano
        if system_prompt:
            data["system"] = system_prompt
            
        headers = {"Content-Type": "application/json"}
        
        # Wysłanie zapytania z obsługą ponownych prób
        retry_count = 0
        max_retries = 3
        retry_delay = 2  # sekundy
        
        while retry_count < max_retries:
            try:
                self.logger.info(f"Wysyłanie zapytania do Ollama (model: {self.model})\n")
                start_time = time.time()
                
                response = requests.post(
                    "http://localhost:11434/api/generate",
                    headers=headers,
                    json=json.dumps(data)
                )
                
                elapsed_time = time.time() - start_time
                
                # Sprawdzenie odpowiedzi
                if response.status_code == 200:
                    self.logger.info(f"Otrzymano odpowiedź z Ollama w {elapsed_time:.2f}s")
                    try:
                        response_json = response.json()
                        content = response_json.get("response", "")
                        prompt_tokens = response_json.get("prompt_eval_count", 0)
                        completion_tokens = response_json.get("eval_count", 0)
                        
                        return {
                            "success": True,
                            "response": content,
                            "timestamp": datetime.now().isoformat(),
                            "model": self.model,
                            "tokens_used": {
                                "prompt": prompt_tokens,
                                "completion": completion_tokens,
                                "total": prompt_tokens + completion_tokens
                            },
                            "response_time": elapsed_time
                        }
                    except (ValueError, KeyError) as e:
                        error_msg = f"Nieprawidłowy format odpowiedzi z Ollama: {str(e)}"
                        self.logger.error(error_msg)
                        return {
                            "success": False,
                            "error": error_msg,
                            "raw_response": response.text,
                            "timestamp": datetime.now().isoformat(),
                            "response": ""
                        }
                else:
                    error_msg = f"Błąd Ollama: kod {response.status_code}, treść: {response.text}"
                    self.logger.error(error_msg)
                    # Jeśli to ostatnia próba, zwróć błąd
                    if retry_count == max_retries - 1:
                        return {
                            "success": False,
                            "error": f"{response.status_code} {response.text}",
                            "timestamp": datetime.now().isoformat(),
                            "response": ""
                        }
                    
            except requests.exceptions.RequestException as e:
                error_msg = f"Błąd połączenia z Ollama: {str(e)}"
                self.logger.error(error_msg)
                # Jeśli to ostatnia próba, zwróć błąd
                if retry_count == max_retries - 1:
                    return {
                        "success": False,
                        "error": f"Błąd połączenia: {str(e)}",
                        "timestamp": datetime.now().isoformat(),
                        "response": ""
                    }
                
            # Jeśli dotarliśmy tutaj, wystąpił błąd - spróbujmy ponownie
            retry_count += 1
            if retry_count < max_retries:
                self.logger.info(f"Ponowna próba za {retry_delay}s...")
                time.sleep(retry_delay)
                retry_delay *= 2  # Wykładniczy backoff
            
        # Jeśli wszystkie próby zawiodły, zwróć informację o błędzie
        return {
            "success": False,
            "error": "Nie udało się uzyskać odpowiedzi z modelu DeepSeek po kilku próbach.",
            "timestamp": datetime.now().isoformat(),
            "response": ""
        }

    def analyze_market_data(self, market_data, analysis_type="complete"):
        """
        Analizuje dane rynkowe i generuje raport.
        
        Args:
            market_data (dict): Dane rynkowe do analizy
            analysis_type (str): Typ analizy (technical, fundamental, sentiment, complete)
            
        Returns:
            dict: Wyniki analizy lub informacja o błędzie
        """
        try:
            self.logger.info(f"Rozpoczęcie analizy rynku typu '{analysis_type}'")
            
            # Tworzenie promptu
            prompt = self._create_market_analysis_prompt(market_data, analysis_type)
            system_prompt = "Jesteś ekspertem w analizie rynków finansowych. Dokonaj precyzyjnej analizy danych rynkowych i przedstaw wyniki w formacie JSON."
            
            # Generowanie odpowiedzi
            response = self.generate_response(prompt, system_prompt)
            
            # Dla testów - jeśli response zawiera już odpowiedź w formacie JSON, użyj jej bezpośrednio
            if 'response' in response and '```json' in response['response']:
                try:
                    # Szukamy bloku JSON w odpowiedzi
                    json_match = re.search(r'```json\s*(.*?)\s*```|{.*}', response["response"], re.DOTALL)
                    if json_match:
                        json_str = json_match.group(1) if json_match.group(1) else json_match.group(0)
                        analysis = json.loads(json_str)
                        
                        # Przygotowanie wyniku
                        result = {
                            'success': True,
                            'timestamp': datetime.now().isoformat(),
                            'analysis': analysis,
                            'analysis_type': analysis_type
                        }
                        
                        self.logger.info("Analiza rynku zakończona pomyślnie")
                        return result
                except Exception:
                    pass
            
            # Jeśli wystąpił błąd podczas generowania odpowiedzi
            if not response.get("success", False):
                return {
                    'success': False,
                    'error': response.get('error', 'Nieznany błąd'),
                    'raw_response': response.get('raw_response', ''),
                    'timestamp': datetime.now().isoformat()
                }
            
            # Przetwarzanie odpowiedzi
            try:
                # Szukamy bloku JSON w odpowiedzi
                json_match = re.search(r'```json\s*(.*?)\s*```|{.*}', response["response"], re.DOTALL)
                if json_match:
                    json_str = json_match.group(1) if json_match.group(1) else json_match.group(0)
                    analysis = json.loads(json_str)
                    
                    # Przygotowanie wyniku
                    result = {
                        'success': True,
                        'timestamp': datetime.now().isoformat(),
                        'analysis': analysis,
                        'analysis_type': analysis_type
                    }
                    
                    self.logger.info("Analiza rynku zakończona pomyślnie")
                    return result
                else:
                    raise ValueError("Nie znaleziono poprawnego formatu JSON w odpowiedzi")
            except (json.JSONDecodeError, ValueError) as e:
                error_msg = f"Błąd przetwarzania odpowiedzi na JSON: {str(e)}"
                self.logger.error(error_msg)
                return {
                    'success': False,
                    'error': error_msg,
                    'raw_response': response["response"],
                    'timestamp': datetime.now().isoformat()
                }
                
        except Exception as e:
            error_msg = f"Błąd podczas analizy rynku: {str(e)}"
            self.logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg,
                'timestamp': datetime.now().isoformat()
            }

    def generate_trading_decision(self, market_data, risk_parameters):
        """
        Generuje decyzję handlową na podstawie danych rynkowych i parametrów ryzyka.
        
        Args:
            market_data (dict): Dane rynkowe do analizy
            risk_parameters (dict): Parametry zarządzania ryzykiem
            
        Returns:
            dict: Decyzja handlowa lub informacja o błędzie
        """
        try:
            self.logger.info("Rozpoczęcie generowania decyzji handlowej")
            
            # Tworzenie promptu
            prompt = self._create_trading_decision_prompt(market_data, risk_parameters)
            system_prompt = "Jesteś ekspertem w tradingu. Twoim zadaniem jest podjęcie decyzji handlowej na podstawie danych rynkowych i parametrów ryzyka."
            
            # Generowanie odpowiedzi
            response = self.generate_response(prompt, system_prompt)
            
            # Dla testów - jeśli response zawiera już odpowiedź w formacie JSON, użyj jej bezpośrednio
            if 'response' in response and '```json' in response['response']:
                try:
                    # Szukamy bloku JSON w odpowiedzi
                    json_match = re.search(r'```json\s*(.*?)\s*```|{.*}', response["response"], re.DOTALL)
                    if json_match:
                        json_str = json_match.group(1) if json_match.group(1) else json_match.group(0)
                        decision = json.loads(json_str)
                        
                        # Przygotowanie wyniku
                        result = {
                            'success': True,
                            'timestamp': datetime.now().isoformat(),
                            'decision': decision
                        }
                        
                        self.logger.info("Generowanie decyzji handlowej zakończone pomyślnie")
                        return result
                except Exception:
                    pass
            
            # Jeśli wystąpił błąd podczas generowania odpowiedzi
            if not response.get("success", False):
                return {
                    'success': False,
                    'error': response.get('error', 'Nieznany błąd'),
                    'raw_response': response.get('raw_response', ''),
                    'timestamp': datetime.now().isoformat()
                }
            
            # Przetwarzanie odpowiedzi
            try:
                # Szukamy bloku JSON w odpowiedzi
                json_match = re.search(r'```json\s*(.*?)\s*```|{.*}', response["response"], re.DOTALL)
                if json_match:
                    json_str = json_match.group(1) if json_match.group(1) else json_match.group(0)
                    decision = json.loads(json_str)
                    
                    # Przygotowanie wyniku
                    result = {
                        'success': True,
                        'timestamp': datetime.now().isoformat(),
                        'decision': decision
                    }
                    
                    self.logger.info("Generowanie decyzji handlowej zakończone pomyślnie")
                    return result
                else:
                    raise ValueError("Nie znaleziono poprawnego formatu JSON w odpowiedzi")
            except (json.JSONDecodeError, ValueError) as e:
                error_msg = f"Błąd przetwarzania odpowiedzi na JSON: {str(e)}"
                self.logger.error(error_msg)
                return {
                    'success': False,
                    'error': error_msg,
                    'raw_response': response["response"],
                    'timestamp': datetime.now().isoformat()
                }
                
        except Exception as e:
            error_msg = f"Błąd podczas generowania decyzji handlowej: {str(e)}"
            self.logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg,
                'timestamp': datetime.now().isoformat()
            }

    def _create_market_analysis_prompt(self, market_data: Dict[str, Any], 
                                     analysis_type: str) -> str:
        """
        Tworzy prompt dla analizy rynkowej.
        
        Args:
            market_data: Dane rynkowe do analizy
            analysis_type: Typ analizy (technical, fundamental, sentiment, complete)
            
        Returns:
            str: Prompt dla modelu AI
        """
        # Podstawowe dane rynkowe
        symbol = market_data.get('symbol', 'Unknown')
        current_price = market_data.get('current_price', market_data.get('price', 'Unknown'))
        
        # Budowanie promptu
        prompt = f"Przeprowadź analizę {analysis_type} dla instrumentu {symbol} przy aktualnej cenie {current_price}.\n\n"
        
        # Dodanie szczegółów w zależności od typu analizy
        if analysis_type in ["technical", "complete"]:
            prompt += "Dane techniczne:\n"
            if 'technical_indicators' in market_data:
                for indicator, value in market_data['technical_indicators'].items():
                    prompt += f"- {indicator}: {value}\n"
            else:
                # Podstawowe wskaźniki, jeśli nie podano szczegółowych
                prompt += f"- RSI: {market_data.get('rsi', 'Unknown')}\n"
                prompt += f"- MACD: {market_data.get('macd', 'Unknown')}\n"
                prompt += f"- MA(50): {market_data.get('ma50', 'Unknown')}\n"
                prompt += f"- MA(200): {market_data.get('ma200', 'Unknown')}\n"
            prompt += "\n"
            
        if analysis_type in ["fundamental", "complete"]:
            prompt += "Dane fundamentalne:\n"
            if 'fundamental_data' in market_data:
                for indicator, value in market_data['fundamental_data'].items():
                    prompt += f"- {indicator}: {value}\n"
            else:
                prompt += "- Brak szczegółowych danych fundamentalnych\n"
            prompt += "\n"
            
        if analysis_type in ["sentiment", "complete"]:
            prompt += "Dane sentymentu:\n"
            if 'sentiment_data' in market_data:
                for source, value in market_data['sentiment_data'].items():
                    prompt += f"- {source}: {value}\n"
            else:
                prompt += "- Brak szczegółowych danych sentymentu\n"
            prompt += "\n"
            
        # Instrukcje dla formatu odpowiedzi
        prompt += """Przygotuj analizę w formacie JSON zawierającą następujące elementy:
        
{
    "trend": "bullish/bearish/neutral",
    "strength": 1-10 (siła trendu),
    "support_levels": [poziom1, poziom2, ...],
    "resistance_levels": [poziom1, poziom2, ...],
    "key_indicators": {
        "wskaźnik1": "interpretacja",
        "wskaźnik2": "interpretacja",
        ...
    },
    "outlook_short_term": "pozytywny/negatywny/neutralny",
    "outlook_medium_term": "pozytywny/negatywny/neutralny",
    "key_factors": ["czynnik1", "czynnik2", ...],
    "confidence_level": 1-10 (poziom pewności analizy)
}

Zwróć odpowiedź w poprawnym formacie JSON."""
        
        return prompt

    def _create_trading_decision_prompt(self, market_data, risk_parameters):
        """
        Tworzy prompt dla generowania decyzji handlowej.
        
        Args:
            market_data (dict): Dane rynkowe
            risk_parameters (dict): Parametry ryzyka
            
        Returns:
            str: Prompt dla modelu AI
        """
        # Podstawowe dane rynkowe
        symbol = market_data.get('symbol', 'Unknown')
        current_price = market_data.get('current_price', market_data.get('price', 'Unknown'))
        day_open = market_data.get('day_open', market_data.get('open', 'Unknown'))
        day_high = market_data.get('day_high', market_data.get('high', 'Unknown'))
        day_low = market_data.get('day_low', market_data.get('low', 'Unknown'))
        prev_close = market_data.get('previous_close', market_data.get('prev_close', 'Unknown'))
        volume = market_data.get('volume', 'Unknown')
        volatility = market_data.get('daily_volatility', market_data.get('volatility', 'Unknown'))
        
        # Wskaźniki techniczne
        technical_indicators = {}
        if 'technical_indicators' in market_data:
            technical_indicators = market_data['technical_indicators']
        rsi = technical_indicators.get('RSI', market_data.get('rsi', 'Unknown'))
        macd = technical_indicators.get('MACD', market_data.get('macd', 'Unknown'))
        
        # Parametry ryzyka
        max_risk_per_trade = risk_parameters.get('max_risk_per_trade', 'Unknown')
        max_exposure = risk_parameters.get('max_exposure_per_symbol', risk_parameters.get('max_exposure', 'Unknown'))
        target_risk_reward = risk_parameters.get('target_risk_reward', 'Unknown')
        current_daily_result = risk_parameters.get('daily_pnl', risk_parameters.get('current_daily_result', 'Unknown'))
        daily_loss_limit = risk_parameters.get('daily_loss_limit', 'Unknown')
        
        # Budowanie promptu
        prompt = f"""Wygeneruj decyzję handlową dla następujących danych rynkowych:

Instrument: {symbol}
Aktualny kurs: {current_price}
Otwarcie dnia: {day_open}
Najwyższy dziś: {day_high}
Najniższy dziś: {day_low}
Poprzednie zamknięcie: {prev_close}
Wolumen: {volume}
Zmienność dzienna: {volatility}

Wskaźniki techniczne:
- RSI: {rsi}
- MACD: {macd}

Parametry ryzyka:
- max_risk_per_trade: {max_risk_per_trade}%
- max_exposure_per_symbol: {max_exposure}%
- target_risk_reward: {target_risk_reward}
- current_daily_result: {current_daily_result}
- daily_loss_limit: {daily_loss_limit}

Na podstawie powyższych danych, wygeneruj decyzję handlową w formacie JSON:

{{
  "action": "BUY/SELL/HOLD",
  "entry_price": [cena wejścia lub null dla HOLD],
  "position_size": [wielkość pozycji w lotach lub 0 dla HOLD],
  "stop_loss": [poziom stop-loss],
  "take_profit": [poziom take-profit],
  "confidence_level": [1-10],
  "reasoning": ["powód1", "powód2", ...],
  "risk_percent": [procent ryzyka na tę transakcję],
  "expected_risk_reward": [oczekiwany stosunek zysku do ryzyka]
}}

Upewnij się, że decyzja jest zgodna z podanymi parametrami ryzyka i obecną sytuacją rynkową.
Zwróć odpowiedź w poprawnym formacie JSON."""

        return prompt


def get_deepseek_api() -> DeepSeekAPI:
    """Zwraca instancję DeepSeekAPI.
    
    Returns:
        Instancja klasy DeepSeekAPI
    """
    return DeepSeekAPI() 