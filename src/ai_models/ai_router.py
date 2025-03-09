#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Moduł routingu zapytań do modeli AI.

Ten moduł zawiera klasy i funkcje odpowiedzialne za koordynację 
pracy różnych modeli AI (Claude, Grok, DeepSeek) oraz 
agregację ich wyników.
"""

import os
import json
import time
import yaml
import logging
import threading
import concurrent.futures
from typing import Dict, List, Any, Optional, Union, Tuple
from datetime import datetime
from collections import Counter

from .claude_api import get_claude_api
from .grok_api import get_grok_api
from .deepseek_api import get_deepseek_api

# Konfiguracja loggera
logger = logging.getLogger('trading_agent.ai_models.router')


class AIRouter:
    """Klasa zarządzająca routingiem zapytań do różnych modeli AI."""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        """Implementacja wzorca Singleton."""
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(AIRouter, cls).__new__(cls)
                cls._instance._initialized = False
        return cls._instance
            
    def __init__(self):
        """Inicjalizacja routera AI."""
        # Singleton pattern - inicjalizacja tylko raz
        if self._initialized:
            return
            
        # Inicjalizacja loggera
        self.logger = logging.getLogger("trading_agent.ai_models.router")
        self.logger.info("Inicjalizacja AI Router")
        
        # Inicjalizacja klientów API
        self.claude_api = get_claude_api()
        self.grok_api = get_grok_api()
        self.deepseek_api = get_deepseek_api()
        
        # Inicjalizacja blokady dla bezpiecznego dostępu do API
        self._api_lock = threading.Lock()
        
        # Ładowanie konfiguracji
        self.config = {}
        self.models_config = {
            'claude': {'enabled': True, 'weight': 0.4},
            'grok': {'enabled': True, 'weight': 0.3},
            'deepseek': {'enabled': True, 'weight': 0.3}
        }
        self.threshold_entry = 0.7  # Domyślny próg pewności dla wejścia w pozycję
        self.threshold_exit = 0.6   # Domyślny próg pewności dla wyjścia z pozycji
        
        self._load_config()
        self._initialized = True
        
    def load_config(self):
        """Ładuje konfigurację z pliku."""
        try:
            config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
                                      "config", "config.yaml")
            with open(config_path, 'r') as file:
                self.config = yaml.safe_load(file)
                
            # Aktualizacja konfiguracji modeli
            if 'ai' in self.config and 'models' in self.config['ai']:
                self.models_config = self.config['ai']['models']
                
            # Aktualizacja progów
            if 'ai' in self.config and 'thresholds' in self.config['ai']:
                self.threshold_entry = self.config['ai']['thresholds'].get('entry', 0.7)
                self.threshold_exit = self.config['ai']['thresholds'].get('exit', 0.6)
                
            self.logger.info(f"Wczytano konfigurację z {config_path}")
        except Exception as e:
            self.logger.error(f"Błąd podczas ładowania konfiguracji: {str(e)}")
            
    def _load_config(self) -> Dict[str, Any]:
        """
        Wczytuje konfigurację z pliku config.yaml.
        
        Returns:
            Dict zawierający konfigurację
        """
        config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
                                  'config', 'config.yaml')
        
        try:
            with open(config_path, 'r', encoding='utf-8') as file:
                config = yaml.safe_load(file)
                self.config = config
                
                # Aktualizacja konfiguracji modeli
                if 'ai' in config and 'models' in config['ai']:
                    self.models_config = config['ai']['models']
                    
                # Aktualizacja progów
                if 'ai' in config and 'thresholds' in config['ai']:
                    self.threshold_entry = config['ai']['thresholds'].get('entry', 0.7)
                    self.threshold_exit = config['ai']['thresholds'].get('exit', 0.6)
                
                self.logger.info(f"Wczytano konfigurację z {config_path}")
                return config
        except Exception as e:
            self.logger.error(f"Błąd wczytywania konfiguracji: {str(e)}")
            # Domyślna konfiguracja w przypadku błędu
            return {
                'ai': {
                    'models': {
                        'claude': {
                            'enabled': True,
                            'weight': 0.4,
                            'timeout_seconds': 30
                        },
                        'grok': {
                            'enabled': True,
                            'weight': 0.3,
                            'timeout_seconds': 20
                        },
                        'deepseek': {
                            'enabled': True,
                            'weight': 0.3,
                            'timeout_seconds': 15
                        }
                    },
                    'thresholds': {
                        'entry': 0.75,
                        'exit': 0.65
                    }
                }
            }
    
    def _get_api_for_model(self, model_name: str):
        """
        Zwraca odpowiedni obiekt API dla danego modelu.
        
        Args:
            model_name: Nazwa modelu (claude, grok, deepseek)
            
        Returns:
            Instancja API dla danego modelu lub None, jeśli model nie istnieje
        """
        if model_name == 'claude':
            return self.claude_api
        elif model_name == 'grok':
            return self.grok_api
        elif model_name == 'deepseek':
            return self.deepseek_api
        else:
            self.logger.warning(f"Nieznany model: {model_name}")
            return None
            
    def _get_claude_api(self):
        """Pobiera instancję Claude API z leniwą inicjalizacją."""
        with self._api_lock:
            if self.claude_api is None:
                self.claude_api = get_claude_api()
        return self.claude_api
            
    def _get_grok_api(self):
        """Pobiera instancję Grok API z leniwą inicjalizacją."""
        with self._api_lock:
            if self.grok_api is None:
                self.grok_api = get_grok_api()
        return self.grok_api
            
    def _get_deepseek_api(self):
        """Pobiera instancję DeepSeek API z leniwą inicjalizacją."""
        with self._api_lock:
            if self.deepseek_api is None:
                self.deepseek_api = get_deepseek_api()
        return self.deepseek_api
    
    def analyze_market_data(self, market_data: Dict[str, Any], 
                          analysis_type: str = "complete") -> Dict[str, Any]:
        """
        Analizuje dane rynkowe przy użyciu dostępnych modeli AI.
        
        Args:
            market_data: Słownik zawierający dane rynkowe
            analysis_type: Rodzaj analizy (technical, fundamental, sentiment, complete)
            
        Returns:
            Dict zawierający zagregowane wyniki analizy
        """
        start_time = time.time()
        self.logger.info(f"Rozpoczęcie analizy danych rynkowych typu {analysis_type}")
        
        # Odśwież konfigurację, aby mieć pewność, że używamy aktualnych ustawień
        self._load_config()
        
        # Wyniki z poszczególnych modeli
        results = []
        models_used = []
        
        # Wywołanie analizy dla każdego aktywnego modelu
        for model_name, config in self.models_config.items():
            if not config.get('enabled', True):
                self.logger.info(f"Model {model_name} jest wyłączony, pomijanie")
                continue
                
            try:
                api = self._get_api_for_model(model_name)
                if api:
                    result = api.analyze_market_data(market_data, analysis_type)
                    if result.get('success', False):
                        models_used.append(model_name)
                    results.append(result)
            except Exception as e:
                self.logger.error(f"Błąd podczas analizy przez model {model_name}: {str(e)}")
                results.append({
                    'success': False,
                    'error': f"Błąd modelu {model_name}: {str(e)}"
                })
                
        # Agregacja wyników
        aggregated_result = self._aggregate_analysis_results(results)
        
        # Dodanie informacji o użytych modelach
        aggregated_result['models_used'] = models_used
        
        elapsed_time = time.time() - start_time
        self.logger.info(f"Zakończono analizę danych rynkowych w {elapsed_time:.2f}s")
        
        return aggregated_result
    
    def generate_trading_decision(self, market_data: Dict[str, Any], 
                                risk_parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generuje decyzję handlową na podstawie danych rynkowych i parametrów ryzyka.
        
        Args:
            market_data: Słownik zawierający dane rynkowe
            risk_parameters: Parametry zarządzania ryzykiem
            
        Returns:
            Dict zawierający zagregowaną decyzję handlową
        """
        start_time = time.time()
        self.logger.info("Rozpoczęcie generowania decyzji handlowej")
        
        # Odśwież konfigurację, aby mieć pewność, że używamy aktualnych ustawień
        self._load_config()
        
        # Wyniki z poszczególnych modeli
        results = []
        models_used = []
        
        # Wywołanie generowania decyzji dla każdego aktywnego modelu
        for model_name, config in self.models_config.items():
            if not config.get('enabled', True):
                self.logger.info(f"Model {model_name} jest wyłączony, pomijanie")
                continue
                
            try:
                api = self._get_api_for_model(model_name)
                if api:
                    result = api.generate_trading_decision(market_data, risk_parameters)
                    if result.get('success', False):
                        models_used.append(model_name)
                    results.append(result)
            except Exception as e:
                self.logger.error(f"Błąd podczas generowania decyzji przez model {model_name}: {str(e)}")
                results.append({
                    'success': False,
                    'error': f"Błąd modelu {model_name}: {str(e)}"
                })
                
        # Agregacja decyzji
        aggregated_decision = self._aggregate_trading_decisions(results, self.threshold_entry)
        
        # Dodanie informacji o użytych modelach
        aggregated_decision['models_used'] = models_used
        
        elapsed_time = time.time() - start_time
        self.logger.info(f"Zakończono generowanie decyzji handlowej w {elapsed_time:.2f}s")
        
        return aggregated_decision
    
    def _analyze_with_claude(self, market_data: Dict[str, Any], 
                           analysis_type: str) -> Dict[str, Any]:
        """
        Przeprowadza analizę rynku z wykorzystaniem modelu Claude.
        
        Args:
            market_data: Dane rynkowe
            analysis_type: Rodzaj analizy
            
        Returns:
            Dict zawierający wynik analizy
        """
        api = self._get_claude_api()
        return api.analyze_market_data(market_data, analysis_type)
    
    def _analyze_with_grok(self, market_data: Dict[str, Any], 
                          analysis_type: str) -> Dict[str, Any]:
        """
        Przeprowadza analizę rynku z wykorzystaniem modelu Grok.
        
        Args:
            market_data: Dane rynkowe
            analysis_type: Rodzaj analizy
            
        Returns:
            Dict zawierający wynik analizy
        """
        api = self._get_grok_api()
        return api.analyze_market_data(market_data, analysis_type)
    
    def _analyze_with_deepseek(self, market_data: Dict[str, Any], 
                             analysis_type: str) -> Dict[str, Any]:
        """
        Przeprowadza analizę rynku z wykorzystaniem modelu DeepSeek.
        
        Args:
            market_data: Dane rynkowe
            analysis_type: Rodzaj analizy
            
        Returns:
            Dict zawierający wynik analizy
        """
        api = self._get_deepseek_api()
        return api.analyze_market_data(market_data, analysis_type)
    
    def _generate_decision_with_claude(self, market_data: Dict[str, Any], 
                                     risk_parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generuje decyzję handlową z wykorzystaniem modelu Claude.
        
        Args:
            market_data: Dane rynkowe
            risk_parameters: Parametry zarządzania ryzykiem
            
        Returns:
            Dict zawierający decyzję handlową
        """
        api = self._get_claude_api()
        return api.generate_trading_decision(market_data, risk_parameters)
    
    def _generate_decision_with_grok(self, market_data: Dict[str, Any], 
                                   risk_parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generuje decyzję handlową z wykorzystaniem modelu Grok.
        
        Args:
            market_data: Dane rynkowe
            risk_parameters: Parametry zarządzania ryzykiem
            
        Returns:
            Dict zawierający decyzję handlową
        """
        api = self._get_grok_api()
        return api.generate_trading_decision(market_data, risk_parameters)
    
    def _generate_decision_with_deepseek(self, market_data: Dict[str, Any], 
                                       risk_parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generuje decyzję handlową z wykorzystaniem modelu DeepSeek.
        
        Args:
            market_data: Dane rynkowe
            risk_parameters: Parametry zarządzania ryzykiem
            
        Returns:
            Dict zawierający decyzję handlową
        """
        api = self._get_deepseek_api()
        return api.generate_trading_decision(market_data, risk_parameters)
    
    def _aggregate_analysis_results(self, results):
        """
        Agreguje wyniki analizy rynku z różnych modeli AI.
        
        Args:
            results: Lista wyników z poszczególnych modeli
            
        Returns:
            Dict zawierający zagregowany wynik analizy
        """
        valid_results = [r for r in results if r.get('success', False)]
        
        # Jeśli nie ma żadnych poprawnych wyników, zwróć błąd
        if not valid_results:
            error_messages = [r.get('error', 'Nieznany błąd') for r in results if not r.get('success', False)]
            return {
                'success': False,
                'error': 'Wszystkie modele AI zwróciły błędy',
                'errors': error_messages,
                'analysis': {
                    'sentiment': 'neutral',
                    'trend': 'neutral',
                    'signals': [],
                    'insights': ['Brak wystarczających danych'],
                    'strength': 0,
                    'confidence_level': 0
                }
            }
        
        # Zbieranie danych z wszystkich wyników
        all_sentiments = []
        all_trends = []
        all_signals = []
        all_insights = []
        all_strengths = []
        all_support_levels = []
        all_confidence_levels = []
        
        # Zbieranie błędów z nieudanych modeli
        errors = [r.get('error', 'Nieznany błąd') for r in results if not r.get('success', False)]
        
        # Agregacja danych
        for result in valid_results:
            analysis = result.get('analysis', {})
            
            if 'sentiment' in analysis:
                all_sentiments.append(analysis['sentiment'])
                
            if 'trend' in analysis:
                all_trends.append(analysis['trend'])
                
            if 'signals' in analysis:
                all_signals.extend(analysis['signals'])
                
            if 'insights' in analysis:
                all_insights.extend(analysis['insights'])
                
            if 'strength' in analysis:
                all_strengths.append(analysis['strength'])
                
            if 'support_levels' in analysis:
                all_support_levels.extend(analysis['support_levels'])
                
            if 'confidence_level' in analysis:
                all_confidence_levels.append(analysis['confidence_level'])
        
        # Określenie dominujących wartości
        sentiment_counts = Counter(all_sentiments)
        trend_counts = Counter(all_trends)
        
        dominant_sentiment = sentiment_counts.most_common(1)[0][0] if sentiment_counts else 'neutral'
        dominant_trend = trend_counts.most_common(1)[0][0] if trend_counts else 'neutral'
        
        # Obliczenie średnich wartości
        avg_strength = sum(all_strengths) / len(all_strengths) if all_strengths else 0
        avg_confidence = sum(all_confidence_levels) / len(all_confidence_levels) if all_confidence_levels else 0
        
        # Przygotowanie wyniku
        aggregated_result = {
            'success': True,
            'errors': errors,
            'analysis': {
                'sentiment': dominant_sentiment,
                'trend': dominant_trend,
                'signals': list(set(all_signals)),
                'insights': list(set(all_insights)),
                'strength': avg_strength,
                'confidence_level': avg_confidence
            }
        }
        
        # Dodanie poziomów wsparcia, jeśli są dostępne
        if all_support_levels:
            aggregated_result['analysis']['support_levels'] = sorted(list(set(all_support_levels)))
        
        return aggregated_result
    
    def _aggregate_trading_decisions(self, results, threshold=0.6):
        """
        Agreguje decyzje handlowe z różnych modeli AI.
        
        Args:
            results: Lista wyników z poszczególnych modeli
            threshold: Próg pewności dla podjęcia decyzji
            
        Returns:
            Dict zawierający zagregowaną decyzję handlową
        """
        valid_results = [r for r in results if r.get('success', False)]
        
        # Zbieranie błędów z nieudanych modeli
        errors = [r.get('error', 'Nieznany błąd') for r in results if not r.get('success', False)]
        
        if not valid_results:
            return {
                'success': False,
                'errors': errors,
                'error': 'Wszystkie modele AI zwróciły błędy',
                'decision': {
                    'action': 'HOLD',
                    'entry_price': None,
                    'position_size': 0,
                    'stop_loss': None,
                    'take_profit': None,
                    'confidence_level': 0,
                    'reasoning': ['Brak wystarczających danych do podjęcia decyzji'],
                    'risk_percent': 0,
                    'expected_risk_reward': 0
                }
            }
        
        # Agregacja wyników
        all_actions = []
        all_confidences = []
        all_reasonings = []
        
        for result in valid_results:
            decision = result.get('decision', {})
            
            if 'action' in decision:
                all_actions.append(decision['action'])
                
            if 'confidence_level' in decision:
                all_confidences.append(decision['confidence_level'])
                
            if 'reasoning' in decision:
                if isinstance(decision['reasoning'], list):
                    all_reasonings.extend(decision['reasoning'])
                else:
                    all_reasonings.append(str(decision['reasoning']))
        
        # Wybór dominującej akcji
        action_counts = Counter(all_actions)
        dominant_action, action_count = action_counts.most_common(1)[0] if action_counts else ('HOLD', 0)
        
        # Obliczenie średniego poziomu pewności
        avg_confidence = sum(all_confidences) / len(all_confidences) if all_confidences else 0
        
        # Jeśli pewność jest poniżej progu, zmień akcję na HOLD
        confidence_too_low = avg_confidence < threshold
        if confidence_too_low:
            dominant_action = 'HOLD'
        
        # Wybierz parametry z najbardziej pewnego wyniku
        most_confident_result = max(valid_results, key=lambda r: r.get('decision', {}).get('confidence_level', 0)) if valid_results else {}
        most_confident_decision = most_confident_result.get('decision', {})
        
        # Przygotowanie wyniku
        aggregated_result = {
            'success': True,
            'errors': errors,
            'decision': {
                'action': dominant_action,
                'entry_price': most_confident_decision.get('entry_price') if dominant_action != 'HOLD' else None,
                'position_size': most_confident_decision.get('position_size', 0) if dominant_action != 'HOLD' else 0,
                'stop_loss': most_confident_decision.get('stop_loss'),
                'take_profit': most_confident_decision.get('take_profit'),
                'confidence_level': avg_confidence,
                'reasoning': list(set(all_reasonings)) if all_reasonings else ['Brak uzasadnienia'],
                'risk_percent': most_confident_decision.get('risk_percent', 0) if dominant_action != 'HOLD' else 0,
                'expected_risk_reward': most_confident_decision.get('expected_risk_reward', 0) if dominant_action != 'HOLD' else 0
            }
        }
        
        # Dodaj flagę, jeśli poziom pewności jest poniżej progu
        if confidence_too_low:
            aggregated_result['confidence_too_low'] = True
        
        return aggregated_result
    

def get_ai_router() -> AIRouter:
    """
    Zwraca instancję AIRouter.
    
    Returns:
        Instancja AIRouter
    """
    return AIRouter() 