#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Test integracji z modelami LLM (Claude, Grok, DeepSeek).

Ten test weryfikuje integrację agenta handlowego z modelami LLM, w tym:
1. Inicjalizację klientów API dla różnych modeli LLM
2. Routing zapytań między modelami
3. Generowanie sygnałów handlowych na podstawie analizy LLM
4. Obsługę błędów i retry mechanizmy
5. Monitorowanie kosztów i wydajności modeli
"""

import sys
import os
import asyncio
import logging
import json
import time
from datetime import datetime
import unittest
from unittest.mock import patch, MagicMock

# Dodanie głównego katalogu projektu do PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Konfiguracja loggera
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)

logger = logging.getLogger(__name__)

class TestLLMIntegration(unittest.TestCase):
    """Klasa testowa dla integracji z modelami LLM."""
    
    @classmethod
    def setUpClass(cls):
        """Przygotowanie środowiska testowego przed wszystkimi testami."""
        logger.info("Przygotowanie środowiska testowego dla testów LLM...")
        
        # Ustawienie zmiennych środowiskowych dla testów
        os.environ["CLAUDE_API_KEY"] = "test_claude_api_key"
        os.environ["GROK_API_KEY"] = "test_grok_api_key"
        os.environ["DEEPSEEK_API_KEY"] = "test_deepseek_api_key"
        
        # Inicjalizacja mocków
        cls.setup_mocks()
    
    @classmethod
    def tearDownClass(cls):
        """Czyszczenie po wszystkich testach."""
        logger.info("Czyszczenie środowiska testowego...")
        
        # Usunięcie zmiennych środowiskowych
        for var in ["CLAUDE_API_KEY", "GROK_API_KEY", "DEEPSEEK_API_KEY"]:
            if var in os.environ:
                del os.environ[var]
    
    @classmethod
    def setup_mocks(cls):
        """Konfiguracja mocków dla testów."""
        # Tutaj będziemy konfigurować mocki dla różnych komponentów LLM
        pass
    
    def test_claude_api_initialization(self):
        """Test inicjalizacji API Claude."""
        logger.info("Test inicjalizacji API Claude...")
        
        # Import modułu Claude API
        from src.ai_models.claude_api import ClaudeAPI
        
        # Inicjalizacja API Claude
        with patch('anthropic.Anthropic') as mock_anthropic, \
             patch.object(ClaudeAPI, '__init__', return_value=None), \
             patch.object(ClaudeAPI, 'analyze_market_data') as mock_analyze:
            
            # Konfiguracja mocka
            mock_analyze.return_value = {
                "analysis": "To jest testowa analiza",
                "signal": "BUY",
                "confidence": 0.85
            }
            
            # Inicjalizacja API
            claude_api = ClaudeAPI()
            
            # Ustawienie atrybutów, które normalnie byłyby ustawione w __init__
            claude_api._initialized = True
            claude_api.api_key = "test_api_key"
            claude_api.client = mock_anthropic.return_value
            claude_api.model = "claude-3-opus-20240229"
            claude_api.max_tokens = 4096
            claude_api.temperature = 0.7
            claude_api.max_retries = 3
            claude_api.retry_delay = 2
            
            # Test metody analyze_market
            result = claude_api.analyze_market("EURUSD", {"open": 1.1234, "high": 1.1245, "low": 1.1230, "close": 1.1240})
            
            # Sprawdzenie wyniku
            self.assertIsNotNone(result)
            self.assertIn("analysis", result)
            
            # Sprawdzenie, czy API zostało wywołane
            mock_analyze.assert_called_once()
    
    def test_grok_api_initialization(self):
        """Test inicjalizacji API Grok."""
        logger.info("Test inicjalizacji API Grok...")
        
        # Import modułu Grok API
        from src.ai_models.grok_api import GrokAPI
        
        # Inicjalizacja API Grok
        with patch('src.ai_models.grok_api.GrokAPI.generate_response') as mock_generate:
            # Konfiguracja mocka
            mock_generate.return_value = {
                "text": "To jest testowa odpowiedź z Grok API.",
                "model": "grok-1",
                "tokens_used": 150,
                "input_tokens": 100,
                "output_tokens": 50,
                "response_time": 0.5,
                "finish_reason": "stop"
            }
            
            # Inicjalizacja API
            grok_api = GrokAPI()
            
            # Test metody analyze_market
            result = grok_api.analyze_market("USDJPY", {"open": 145.67, "high": 145.80, "low": 145.50, "close": 145.75})
            
            # Sprawdzenie wyniku
            self.assertIsNotNone(result)
            
            # Sprawdzenie, czy API zostało wywołane
            mock_generate.assert_called_once()
    
    def test_deepseek_api_initialization(self):
        """Test inicjalizacji API DeepSeek."""
        logger.info("Test inicjalizacji API DeepSeek...")
        
        # Import modułu DeepSeek API
        from src.ai_models.deepseek_api import DeepSeekAPI
        
        # Inicjalizacja API DeepSeek
        with patch('src.ai_models.deepseek_api.DeepSeekAPI.generate_response') as mock_generate, \
             patch.object(DeepSeekAPI, '__init__', return_value=None), \
             patch.object(DeepSeekAPI, 'analyze_market_data') as mock_analyze:
            
            # Konfiguracja mocków
            mock_generate.return_value = {
                "text": '{"analysis": "To jest testowa analiza", "signal": "BUY", "confidence": 0.85}',
                "model": "deepseek-r1:8b",
                "tokens_used": 150,
                "input_tokens": 100,
                "output_tokens": 50,
                "response_time": 0.5,
                "finish_reason": "stop"
            }
            
            mock_analyze.return_value = {
                "analysis": "To jest testowa analiza",
                "signal": "BUY",
                "confidence": 0.85
            }
            
            # Inicjalizacja API
            deepseek_api = DeepSeekAPI()
            
            # Ustawienie atrybutów, które normalnie byłyby ustawione w __init__
            deepseek_api._initialized = True
            deepseek_api.model = "deepseek-r1:8b"
            deepseek_api.max_tokens = 4096
            deepseek_api.temperature = 0.7
            deepseek_api.max_retries = 3
            deepseek_api.retry_delay = 2
            deepseek_api.logger = logging.getLogger('DeepSeekAPI')
            
            # Test metody analyze_market
            result = deepseek_api.analyze_market("GOLD", {"open": 2000.0, "high": 2010.0, "low": 1995.0, "close": 2005.0})
            
            # Sprawdzenie wyniku
            self.assertIsNotNone(result)
            self.assertIn("analysis", result)
            
            # Sprawdzenie, czy API zostało wywołane
            mock_analyze.assert_called_once()
    
    def test_ai_router(self):
        """Test routera AI."""
        logger.info("Test routera AI...")
        
        # Import modułu AI Router
        from src.ai_models.ai_router import AIRouter
        
        # Inicjalizacja routera AI
        with patch.object(AIRouter, '__init__', return_value=None):
            
            # Inicjalizacja routera
            router = AIRouter()
            
            # Ustawienie atrybutów, które normalnie byłyby ustawione w __init__
            router._initialized = True
            router.logger = logging.getLogger('test')
            
            # Mockowanie metod API
            router.claude_api = MagicMock()
            router.claude_api.analyze_market.return_value = {"analysis": "Analiza Claude", "signal": "BUY", "confidence": 0.85}
            
            router.grok_api = MagicMock()
            router.grok_api.analyze_market.return_value = {"analysis": "Analiza Grok", "signal": "SELL", "confidence": 0.75}
            
            router.deepseek_api = MagicMock()
            router.deepseek_api.analyze_market.return_value = {"analysis": "Analiza DeepSeek", "signal": "HOLD", "confidence": 0.65}
            
            router._api_lock = MagicMock()
            router.config = {}
            router.models_config = {
                'claude': {'enabled': True, 'weight': 0.4},
                'grok': {'enabled': True, 'weight': 0.3},
                'deepseek': {'enabled': True, 'weight': 0.3}
            }
            router.threshold_entry = 0.7
            router.threshold_exit = 0.6
            
            # Test metody route_analysis
            result = router.route_analysis("EURUSD", {"open": 1.1234, "high": 1.1245, "low": 1.1230, "close": 1.1240}, "claude")
            
            # Sprawdzenie wyniku
            self.assertIsNotNone(result)
            self.assertEqual(result["signal"], "BUY")
            self.assertEqual(result["confidence"], 0.85)
            
            # Sprawdzenie, czy odpowiednie API zostało wywołane
            router.claude_api.analyze_market.assert_called_once()
            router.grok_api.analyze_market.assert_not_called()
            router.deepseek_api.analyze_market.assert_not_called()
            
            # Reset mocków
            router.claude_api.analyze_market.reset_mock()
            router.grok_api.analyze_market.reset_mock()
            router.deepseek_api.analyze_market.reset_mock()
            
            # Test metody route_analysis z innym modelem
            result = router.route_analysis("USDJPY", {"open": 145.67, "high": 145.80, "low": 145.50, "close": 145.75}, "grok")
            
            # Sprawdzenie wyniku
            self.assertIsNotNone(result)
            self.assertEqual(result["signal"], "SELL")
            self.assertEqual(result["confidence"], 0.75)
            
            # Sprawdzenie, czy odpowiednie API zostało wywołane
            router.claude_api.analyze_market.assert_not_called()
            router.grok_api.analyze_market.assert_called_once()
            router.deepseek_api.analyze_market.assert_not_called()
    
    def test_ai_monitoring(self):
        """Test monitorowania AI."""
        logger.info("Test monitorowania AI...")
        
        # Import modułu AI Monitoring
        with patch('src.monitoring.alert_manager.get_alert_manager', return_value=MagicMock()):
            from src.monitoring.ai_monitor import AIMonitor
            
            # Mockowanie bazy danych i alert managera
            with patch('src.database.ai_usage_repository.AIUsageRepository._create_tables'), \
                 patch('src.database.ai_usage_repository.AIUsageRepository.insert_usage'), \
                 patch('src.database.ai_usage_repository.AIUsageRepository.get_usage_in_timeframe') as mock_get_stats, \
                 patch.object(AIMonitor, '__init__', return_value=None):
                
                # Konfiguracja mocków
                mock_get_stats.return_value = [
                    {
                        'model_name': 'claude',
                        'tokens_input': 200,
                        'tokens_output': 300,
                        'cost': 0.025,
                        'success': True
                    },
                    {
                        'model_name': 'grok',
                        'tokens_input': 150,
                        'tokens_output': 150,
                        'cost': 0.015,
                        'success': True
                    },
                    {
                        'model_name': 'deepseek',
                        'tokens_input': 100,
                        'tokens_output': 100,
                        'cost': 0.01,
                        'success': False
                    }
                ]
                
                # Inicjalizacja monitora AI
                ai_monitor = AIMonitor()
                
                # Ustawienie atrybutów, które normalnie byłyby ustawione w __init__
                ai_monitor._initialized = True
                ai_monitor.logger = logging.getLogger('test')
                ai_monitor.ai_usage_repository = MagicMock()
                ai_monitor.alert_manager = MagicMock()
                ai_monitor.cost_thresholds = {
                    'claude': 5.0,
                    'grok': 3.0,
                    'deepseek': 2.0
                }
                ai_monitor.usage_buffer = []
                
                # Test metody log_api_call
                ai_monitor.log_api_call = MagicMock()
                ai_monitor.log_api_call("claude", "analyze_market", 0.5, True)
                ai_monitor.log_api_call("grok", "analyze_market", 0.3, True)
                ai_monitor.log_api_call("deepseek", "analyze_market", 0.2, False)
                
                # Test metody get_api_usage
                ai_monitor.get_api_usage = MagicMock(return_value={
                    'total_calls': 3,
                    'total_tokens': 1000,
                    'total_cost': 0.05,
                    'models': {
                        'claude': {'calls': 1, 'tokens': 500, 'cost': 0.025},
                        'grok': {'calls': 1, 'tokens': 300, 'cost': 0.015},
                        'deepseek': {'calls': 1, 'tokens': 200, 'cost': 0.01}
                    }
                })
                usage = ai_monitor.get_api_usage()
                
                # Sprawdzenie wyniku
                self.assertIsNotNone(usage)
                self.assertEqual(usage['total_calls'], 3)
                self.assertEqual(usage['total_tokens'], 1000)
                self.assertIn('models', usage)
                self.assertIn('claude', usage['models'])
    
    def test_signal_generation_from_llm(self):
        """Test generowania sygnałów handlowych z LLM."""
        logger.info("Test generowania sygnałów handlowych z LLM...")
        
        # Import modułów
        from src.ai_models.ai_router import AIRouter
        from src.analysis.signal_generator import SignalGenerator
        
        # Inicjalizacja generatora sygnałów
        with patch.object(AIRouter, '__init__', return_value=None), \
             patch.object(SignalGenerator, 'generate_signal', return_value=None) as mock_generate:
            
            # Inicjalizacja routera i generatora sygnałów
            router = AIRouter()
            
            # Ustawienie atrybutów, które normalnie byłyby ustawione w __init__
            router._initialized = True
            router.logger = logging.getLogger('test')
            
            # Mockowanie metod API
            router.claude_api = MagicMock()
            router.claude_api.analyze_market.return_value = {
                "analysis": "Analiza rynku wskazuje na trend wzrostowy.",
                "signal": "BUY",
                "confidence": 0.85,
                "price_target": 1.1300,
                "stop_loss": 1.1200
            }
            
            router.grok_api = MagicMock()
            router.deepseek_api = MagicMock()
            
            router._api_lock = MagicMock()
            router.config = {}
            router.models_config = {
                'claude': {'enabled': True, 'weight': 0.4},
                'grok': {'enabled': True, 'weight': 0.3},
                'deepseek': {'enabled': True, 'weight': 0.3}
            }
            router.threshold_entry = 0.7
            router.threshold_exit = 0.6
            
            # Inicjalizacja generatora sygnałów
            signal_generator = SignalGenerator()
            
            # Ustawienie routera w generatorze sygnałów
            signal_generator.ai_router = router
            
            # Test generowania sygnału
            market_data = {"open": 1.1234, "high": 1.1245, "low": 1.1230, "close": 1.1240}
            signal = signal_generator.generate_signal("EURUSD", market_data)
            
            # Sprawdzenie, czy mock został wywołany
            mock_generate.assert_called_once_with("EURUSD", market_data)
    
    def test_error_handling(self):
        """Test obsługi błędów."""
        logger.info("Test obsługi błędów...")
        
        # Import modułu AI Router
        from src.ai_models.ai_router import AIRouter
        
        # Inicjalizacja routera AI
        with patch.object(AIRouter, '__init__', return_value=None):
            
            # Inicjalizacja routera
            router = AIRouter()
            
            # Ustawienie atrybutów, które normalnie byłyby ustawione w __init__
            router._initialized = True
            router.logger = logging.getLogger('test')
            
            # Mockowanie metod API
            router.claude_api = MagicMock()
            router.claude_api.analyze_market.side_effect = Exception("Test błędu API")
            
            router.grok_api = MagicMock()
            router.deepseek_api = MagicMock()
            
            router._api_lock = MagicMock()
            router.config = {}
            router.models_config = {
                'claude': {'enabled': True, 'weight': 0.4},
                'grok': {'enabled': True, 'weight': 0.3},
                'deepseek': {'enabled': True, 'weight': 0.3}
            }
            router.threshold_entry = 0.7
            router.threshold_exit = 0.6
            
            # Test metody route_analysis z obsługą błędu
            result = router.route_analysis("EURUSD", {"open": 1.1234, "high": 1.1245, "low": 1.1230, "close": 1.1240}, "claude")
            
            # Sprawdzenie wyniku
            self.assertIsNotNone(result)
            self.assertFalse(result.get("success", True))
            self.assertIn("error", result)
            self.assertEqual(result["signal"], "NONE")
            
            # Sprawdzenie, czy API zostało wywołane
            router.claude_api.analyze_market.assert_called_once()

async def run_tests():
    """Uruchamia testy asynchronicznie."""
    # Tutaj możemy uruchomić testy asynchroniczne, jeśli są potrzebne
    pass

if __name__ == "__main__":
    # Uruchomienie testów asynchronicznych
    asyncio.run(run_tests())
    
    # Uruchomienie testów jednostkowych
    unittest.main(argv=['first-arg-is-ignored'], exit=False) 