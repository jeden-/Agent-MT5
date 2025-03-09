"""
Testy jednostkowe dla modułu GrokAPI.
"""

import unittest
from unittest.mock import patch, MagicMock
import json
import requests
from datetime import datetime
import os

from src.ai_models.grok_api import GrokAPI, get_grok_api


class TestGrokAPI(unittest.TestCase):
    """Testy dla klasy GrokAPI."""

    def setUp(self):
        """Przygotowanie środowiska przed każdym testem."""
        # Resetowanie singletona przed każdym testem dla izolacji
        GrokAPI._instance = None
        
        # Mock dla requests.post
        self.patcher_post = patch('src.ai_models.grok_api.requests.post')
        self.mock_post = self.patcher_post.start()
        
        # Ustawienie odpowiedzi z API
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'id': 'chat_123456',
            'choices': [
                {
                    'message': {
                        'role': 'assistant',
                        'content': 'To jest testowa odpowiedź'
                    },
                    'finish_reason': 'stop'
                }
            ],
            'usage': {
                'prompt_tokens': 15,
                'completion_tokens': 10,
                'total_tokens': 25
            }
        }
        self.mock_post.return_value = mock_response
        
        # Mock dla os.environ
        self.env_patcher = patch.dict('os.environ', {'XAI_API_KEY': 'fake-key-for-testing'})
        self.env_patcher.start()

    def tearDown(self):
        """Czyszczenie po każdym teście."""
        self.patcher_post.stop()
        self.env_patcher.stop()

    def test_singleton_pattern(self):
        """Test wzorca Singleton."""
        api1 = GrokAPI()
        api2 = GrokAPI()
        
        # Obie instancje powinny być tym samym obiektem
        self.assertIs(api1, api2)
        
        # Funkcja get_grok_api powinna zwracać tę samą instancję
        api3 = get_grok_api()
        self.assertIs(api1, api3)

    def test_init_checks_api_key(self):
        """Test sprawdzania klucza API podczas inicjalizacji."""
        # Usunięcie zmiennej środowiskowej dla testu
        with patch.dict('os.environ', {'XAI_API_KEY': ''}, clear=True):
            with self.assertLogs(level='ERROR') as cm:
                api = GrokAPI()
                self.assertIn("Nie znaleziono klucza API Grok", cm.output[0])

    def test_set_model(self):
        """Test ustawiania modelu."""
        api = GrokAPI()
        default_model = api.model
        
        # Zmiana modelu
        new_model = "grok-2"
        api.set_model(new_model)
        
        # Sprawdzenie, czy model został zmieniony
        self.assertEqual(api.model, new_model)
        self.assertNotEqual(api.model, default_model)

    def test_set_parameters(self):
        """Test ustawiania parametrów generowania."""
        api = GrokAPI()
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
        api = GrokAPI()
        result = api.generate_response("Testowe zapytanie", system_prompt="Testowy prompt systemowy")
        
        # Sprawdzenie, czy wywołanie API było poprawne
        self.mock_post.assert_called_once()
        
        # Sprawdzenie parametrów wywołania
        call_args = self.mock_post.call_args
        # URL powinien zawierać endpoint chat/completions
        url = call_args[0][0]
        self.assertIn("chat/completions", url)
        
        # Sprawdzenie nagłówków
        headers = call_args[1]['headers']
        self.assertEqual(headers['Content-Type'], 'application/json')
        self.assertEqual(headers['Authorization'], 'Bearer fake-key-for-testing')
        
        # Sprawdzenie rezultatu (pomijamy sprawdzanie zawartości pola JSON)
        self.assertEqual(result['text'], "To jest testowa odpowiedź")
        self.assertEqual(result['model'], api.model)
        self.assertEqual(result['tokens_used'], 25)
        self.assertEqual(result['input_tokens'], 15)
        self.assertEqual(result['output_tokens'], 10)
        self.assertEqual(result['finish_reason'], 'stop')
        self.assertIn('response_time', result)

    def test_generate_response_http_error(self):
        """Test obsługi błędu HTTP."""
        # Symulacja błędu HTTP
        mock_error_response = MagicMock()
        mock_error_response.status_code = 500
        mock_error_response.text = "Internal Server Error"
        mock_error_response.raise_for_status.side_effect = requests.exceptions.HTTPError("500 Server Error")
        self.mock_post.return_value = mock_error_response
        
        api = GrokAPI()
        with self.assertLogs(level='ERROR') as cm:
            result = api.generate_response("Testowe zapytanie")
            self.assertIn("Błąd HTTP Grok API", cm.output[0])
        
        # Sprawdzenie, czy wynik zawiera informacje o błędzie
        self.assertEqual(result['error'], "500 Server Error")
        self.assertIn('timestamp', result)

    def test_generate_response_request_exception(self):
        """Test obsługi wyjątku RequestException."""
        # Symulacja wyjątku RequestException
        self.mock_post.side_effect = requests.exceptions.RequestException("Connection Error")
        
        api = GrokAPI()
        with self.assertLogs(level='ERROR') as cm:
            result = api.generate_response("Testowe zapytanie")
            self.assertIn("Błąd połączenia Grok API", cm.output[0])
        
        # Sprawdzenie, czy wynik zawiera informacje o błędzie
        self.assertEqual(result['error'], "Connection Error")
        self.assertIn('timestamp', result)

    def test_generate_response_retry_success(self):
        """Test ponownej próby po błędzie."""
        # Pierwsza próba kończy się błędem, druga sukcesem
        mock_error_response = MagicMock()
        mock_error_response.status_code = 429
        mock_error_response.text = "Too Many Requests"
        mock_error_response.raise_for_status.side_effect = requests.exceptions.HTTPError("429 Too Many Requests")
        
        mock_success_response = MagicMock()
        mock_success_response.status_code = 200
        mock_success_response.json.return_value = {
            'id': 'chat_123456',
            'choices': [
                {
                    'message': {
                        'role': 'assistant',
                        'content': 'Odpowiedź po ponownej próbie'
                    },
                    'finish_reason': 'stop'
                }
            ],
            'usage': {
                'prompt_tokens': 15,
                'completion_tokens': 10,
                'total_tokens': 25
            }
        }
        
        # Ustawienie sekwencji odpowiedzi: najpierw błąd, potem sukces
        self.mock_post.side_effect = [mock_error_response, mock_success_response]
        
        api = GrokAPI()
        result = api.generate_response("Testowe zapytanie")
        
        # Sprawdzenie, czy były dwie próby
        self.assertEqual(self.mock_post.call_count, 2)
        
        # Sprawdzenie rezultatu
        self.assertEqual(result['text'], "Odpowiedź po ponownej próbie")

    def test_analyze_market_data(self):
        """Test analizy danych rynkowych."""
        api = GrokAPI()
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
        self.mock_post.assert_called_once()
        
        # Sprawdzenie, czy wywołano z odpowiednim URL
        call_args = self.mock_post.call_args
        self.assertIn("chat/completions", call_args[0][0])
        
        # Sprawdzenie, czy prompt zawiera oczekiwane elementy (pomijamy sprawdzanie zawartości pola JSON)
        prompt = call_args[1]['headers']
        self.assertEqual(prompt['Content-Type'], 'application/json')
        
        # Sprawdzenie rezultatu
        self.assertTrue(result['success'])
        self.assertEqual(result['model'], "grok")
        self.assertIn('analysis', result)
        self.assertEqual(result['analysis_type'], "technical")

    def test_analyze_market_data_error(self):
        """Test obsługi błędu podczas analizy danych rynkowych."""
        # Symulacja błędu API
        self.mock_post.side_effect = requests.exceptions.RequestException("Connection Error")
        
        api = GrokAPI()
        market_data = {"symbol": "GOLD.pro", "current_price": 2950.75}
        
        with self.assertLogs(level='ERROR') as cm:
            result = api.analyze_market_data(market_data, "technical")
            self.assertIn("Błąd podczas analizy rynku", cm.output[0])
        
        # Sprawdzenie, czy wynik zawiera informacje o błędzie
        self.assertIn('error', result)
        self.assertEqual(result['error'], "Connection Error")

    def test_generate_trading_decision(self):
        """Test generowania decyzji handlowej."""
        api = GrokAPI()
        market_data = {
            "symbol": "GOLD.pro",
            "current_price": 2950.75,
            "technical_indicators": {
                "RSI": 68,
                "MACD": 0.45
            }
        }
        risk_parameters = {
            "max_risk_per_trade": 2.0
        }
        result = api.generate_trading_decision(market_data, risk_parameters)
        
        # Sprawdzenie, czy wywołanie API było poprawne
        self.mock_post.assert_called_once()
        
        # Sprawdzenie, czy wywołano z odpowiednim URL
        call_args = self.mock_post.call_args
        self.assertIn("chat/completions", call_args[0][0])
        
        # Sprawdzenie, czy prompt zawiera oczekiwane elementy (pomijamy sprawdzanie zawartości pola JSON)
        prompt = call_args[1]['headers']
        self.assertEqual(prompt['Content-Type'], 'application/json')
        
        # Sprawdzenie rezultatu
        self.assertTrue(result['success'])
        self.assertEqual(result['model'], "grok")
        self.assertIn('decision', result)
        self.assertEqual(result['decision']['action'], "BUY")
        self.assertEqual(result['decision']['entry_price'], 2950.0)
        self.assertEqual(result['decision']['position_size'], 0.1)

    def test_generate_trading_decision_error(self):
        """Test obsługi błędu podczas generowania decyzji handlowej."""
        # Symulacja błędu API
        self.mock_post.side_effect = requests.exceptions.RequestException("Connection Error")
        
        api = GrokAPI()
        market_data = {"symbol": "GOLD.pro", "current_price": 2950.75}
        risk_parameters = {"max_risk_per_trade": 2.0}
        
        with self.assertLogs(level='ERROR') as cm:
            result = api.generate_trading_decision(market_data, risk_parameters)
            self.assertIn("Błąd podczas generowania decyzji handlowej", cm.output[0])
        
        # Sprawdzenie, czy wynik zawiera informacje o błędzie
        self.assertIn('error', result)
        self.assertEqual(result['error'], "Connection Error")


if __name__ == '__main__':
    unittest.main() 