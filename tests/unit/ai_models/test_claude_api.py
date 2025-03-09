"""
Testy jednostkowe dla modułu ClaudeAPI.
"""

import unittest
from unittest.mock import patch, MagicMock, ANY
import json
from datetime import datetime
import os

from src.ai_models.claude_api import ClaudeAPI, get_claude_api


class TestClaudeAPI(unittest.TestCase):
    """Testy dla klasy ClaudeAPI."""

    def setUp(self):
        """Przygotowanie środowiska przed każdym testem."""
        # Resetowanie singletona przed każdym testem dla izolacji
        ClaudeAPI._instance = None
        # Patchowanie anthropic.Anthropic dla testów
        self.patcher_anthropic = patch('src.ai_models.claude_api.anthropic.Anthropic')
        self.mock_anthropic_class = self.patcher_anthropic.start()
        self.mock_anthropic = MagicMock()
        self.mock_anthropic_class.return_value = self.mock_anthropic
        
        # Patchowanie messageów
        self.mock_messages = MagicMock()
        self.mock_anthropic.messages.create = self.mock_messages
        
        # Ustawienie wartości zwracanej przez messages.create
        self.mock_messages.return_value = {
            'id': 'msg_123456',
            'content': [{'type': 'text', 'text': 'To jest testowa odpowiedź'}],
            'usage': {
                'input_tokens': 10,
                'output_tokens': 5
            }
        }
        
        # Mock dla os.environ
        self.env_patcher = patch.dict('os.environ', {'ANTHROPIC_API_KEY': 'fake-key-for-testing'})
        self.env_patcher.start()

    def tearDown(self):
        """Czyszczenie po każdym teście."""
        self.patcher_anthropic.stop()
        self.env_patcher.stop()

    def test_singleton_pattern(self):
        """Test wzorca Singleton."""
        api1 = ClaudeAPI()
        api2 = ClaudeAPI()
        
        # Obie instancje powinny być tym samym obiektem
        self.assertIs(api1, api2)
        
        # Funkcja get_claude_api powinna zwracać tę samą instancję
        api3 = get_claude_api()
        self.assertIs(api1, api3)

    def test_init_checks_api_key(self):
        """Test sprawdzania klucza API podczas inicjalizacji."""
        # Usunięcie zmiennej środowiskowej dla testu
        with patch.dict('os.environ', {'ANTHROPIC_API_KEY': ''}, clear=True):
            with self.assertLogs(level='ERROR') as cm:
                api = ClaudeAPI()
                self.assertIn("Nie znaleziono klucza API Claude", cm.output[0])

    def test_set_model(self):
        """Test ustawiania modelu."""
        api = ClaudeAPI()
        default_model = api.model
        
        # Zmiana modelu
        new_model = "claude-3-opus-20240229"
        api.set_model(new_model)
        
        # Sprawdzenie, czy model został zmieniony
        self.assertEqual(api.model, new_model)
        self.assertNotEqual(api.model, default_model)

    def test_set_parameters(self):
        """Test ustawiania parametrów generowania."""
        api = ClaudeAPI()
        default_max_tokens = api.max_tokens
        default_temperature = api.temperature
        
        # Zmiana parametrów
        new_max_tokens = 1500
        new_temperature = 0.5
        api.set_parameters(max_tokens=new_max_tokens, temperature=new_temperature)
        
        # Sprawdzenie, czy parametry zostały zmienione
        self.assertEqual(api.max_tokens, new_max_tokens)
        self.assertEqual(api.temperature, new_temperature)
        self.assertNotEqual(api.max_tokens, default_max_tokens)
        self.assertNotEqual(api.temperature, default_temperature)

    def test_generate_response_success(self):
        """Test udanego generowania odpowiedzi."""
        api = ClaudeAPI()
        result = api.generate_response("Testowe zapytanie", system_prompt="Testowy prompt systemowy")
        
        # Sprawdzenie, czy wywołanie API było poprawne
        self.mock_anthropic.messages.create.assert_called_once()
        
        # Sprawdzenie parametrów wywołania
        call_args = self.mock_anthropic.messages.create.call_args[1]
        self.assertEqual(call_args['model'], api.model)
        self.assertEqual(call_args['max_tokens'], api.max_tokens)
        self.assertEqual(call_args['temperature'], api.temperature)
        self.assertEqual(call_args['system'], "Testowy prompt systemowy")
        self.assertEqual(len(call_args['messages']), 1)
        self.assertEqual(call_args['messages'][0]['role'], 'user')
        self.assertEqual(call_args['messages'][0]['content'], "Testowe zapytanie")
        
        # Sprawdzenie rezultatu
        self.assertEqual(result['text'], "To jest testowa odpowiedź")
        self.assertEqual(result['model'], api.model)
        self.assertEqual(result['input_tokens'], 10)
        self.assertEqual(result['output_tokens'], 5)
        self.assertEqual(result['tokens_used'], 15)
        self.assertIn('response_time', result)

    def test_generate_response_api_error(self):
        """Test obsługi błędu API."""
        # Symulacja błędu API
        self.mock_messages.side_effect = Exception("API Error")
        
        api = ClaudeAPI()
        with self.assertLogs(level='ERROR') as cm:
            result = api.generate_response("Testowe zapytanie")
            self.assertIn("Błąd podczas generowania odpowiedzi Claude API", cm.output[0])
        
        # Sprawdzenie, czy wynik zawiera informacje o błędzie
        self.assertEqual(result['error'], "API Error")
        self.assertIn('timestamp', result)

    def test_analyze_market_data(self):
        """Test analizy danych rynkowych."""
        # Ustawienie odpowiedzi API dla analizy rynku
        self.mock_messages.return_value = {
            'id': 'msg_123456',
            'content': [{
                'type': 'text', 
                'text': json.dumps({
                    "trend": "bullish",
                    "strength": 8,
                    "support_levels": [2900, 2850],
                    "confidence_level": 7
                })
            }],
            'usage': {
                'input_tokens': 100,
                'output_tokens': 50
            }
        }
        
        api = ClaudeAPI()
        market_data = {
            "symbol": "GOLD.pro",
            "current_price": 2950.75,
            "technical_indicators": {
                "RSI": 68,
                "MACD": 0.45
            }
        }
        
        result = api.analyze_market_data(market_data, "technical")
        
        # Sprawdzenie, czy wywołanie API było poprawne
        self.mock_anthropic.messages.create.assert_called_once()
        
        # Sprawdzenie zawartości promptu
        call_args = self.mock_anthropic.messages.create.call_args[1]
        prompt_content = call_args['messages'][0]['content']
        self.assertIn("GOLD.pro", prompt_content)
        self.assertIn("2950.75", prompt_content)
        self.assertIn("technical", prompt_content)
        
        # Sprawdzenie rezultatu
        self.assertEqual(result["trend"], "bullish")
        self.assertEqual(result["strength"], 8)
        self.assertEqual(result["support_levels"], [2900, 2850])
        self.assertEqual(result["confidence_level"], 7)

    def test_analyze_market_data_error(self):
        """Test obsługi błędu podczas analizy danych rynkowych."""
        # Symulacja błędu API
        self.mock_messages.side_effect = Exception("API Error")
        
        api = ClaudeAPI()
        market_data = {"symbol": "GOLD.pro", "current_price": 2950.75}
        
        with self.assertLogs(level='ERROR') as cm:
            result = api.analyze_market_data(market_data, "technical")
            self.assertIn("Błąd podczas analizy rynku", cm.output[0])
        
        # Sprawdzenie, czy wynik zawiera informacje o błędzie
        self.assertIn('error', result)
        self.assertEqual(result['error'], "API Error")

    def test_generate_trading_decision(self):
        """Test generowania decyzji handlowej."""
        # Ustawienie odpowiedzi API dla decyzji handlowej
        self.mock_messages.return_value = {
            'id': 'msg_123456',
            'content': [{
                'type': 'text', 
                'text': json.dumps({
                    "action": "BUY",
                    "entry_price": 2950.0,
                    "position_size": 0.1,
                    "stop_loss": 2900.0,
                    "take_profit": 3050.0,
                    "confidence_level": 8
                })
            }],
            'usage': {
                'input_tokens': 120,
                'output_tokens': 60
            }
        }
        
        api = ClaudeAPI()
        market_data = {
            "symbol": "GOLD.pro",
            "current_price": 2950.75
        }
        risk_parameters = {
            "max_risk_per_trade": 2.0,
            "max_exposure_per_symbol": 5.0
        }
        
        result = api.generate_trading_decision(market_data, risk_parameters)
        
        # Sprawdzenie, czy wywołanie API było poprawne
        self.mock_anthropic.messages.create.assert_called_once()
        
        # Sprawdzenie zawartości promptu
        call_args = self.mock_anthropic.messages.create.call_args[1]
        prompt_content = call_args['messages'][0]['content']
        self.assertIn("GOLD.pro", prompt_content)
        self.assertIn("2950.75", prompt_content)
        self.assertIn("max_risk_per_trade", prompt_content)
        
        # Sprawdzenie rezultatu
        self.assertEqual(result["action"], "BUY")
        self.assertEqual(result["entry_price"], 2950.0)
        self.assertEqual(result["position_size"], 0.1)
        self.assertEqual(result["stop_loss"], 2900.0)
        self.assertEqual(result["take_profit"], 3050.0)
        self.assertEqual(result["confidence_level"], 8)

    def test_generate_trading_decision_error(self):
        """Test obsługi błędu podczas generowania decyzji handlowej."""
        # Symulacja błędu API
        self.mock_messages.side_effect = Exception("API Error")
        
        api = ClaudeAPI()
        market_data = {"symbol": "GOLD.pro", "current_price": 2950.75}
        risk_parameters = {"max_risk_per_trade": 2.0}
        
        with self.assertLogs(level='ERROR') as cm:
            result = api.generate_trading_decision(market_data, risk_parameters)
            self.assertIn("Błąd podczas generowania decyzji handlowej", cm.output[0])
        
        # Sprawdzenie, czy wynik zawiera informacje o błędzie
        self.assertIn('error', result)
        self.assertEqual(result['error'], "API Error")


if __name__ == '__main__':
    unittest.main() 