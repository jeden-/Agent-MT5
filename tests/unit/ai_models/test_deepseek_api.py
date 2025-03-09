"""
Testy jednostkowe dla modułu DeepSeekAPI (integracja z Ollama).
"""

import unittest
from unittest.mock import patch, MagicMock
import json
import requests
from datetime import datetime

from src.ai_models.deepseek_api import DeepSeekAPI, get_deepseek_api


class TestDeepSeekAPI(unittest.TestCase):
    """Testy dla klasy DeepSeekAPI."""

    def setUp(self):
        """Przygotowanie środowiska przed każdym testem."""
        # Resetowanie singletona przed każdym testem dla izolacji
        DeepSeekAPI._instance = None
        self.patcher = patch('src.ai_models.deepseek_api.requests.get')
        self.mock_requests_get = self.patcher.start()
        self.mock_requests_get.return_value.status_code = 200
        self.mock_requests_get.return_value.json.return_value = {
            "models": [
                {"name": "deepseek-coder"},
                {"name": "other-model"}
            ]
        }

    def tearDown(self):
        """Czyszczenie po każdym teście."""
        self.patcher.stop()

    def test_singleton_pattern(self):
        """Test wzorca Singleton."""
        api1 = DeepSeekAPI()
        api2 = DeepSeekAPI()
        
        # Obie instancje powinny być tym samym obiektem
        self.assertIs(api1, api2)
        
        # Funkcja get_deepseek_api powinna zwracać tę samą instancję
        api3 = get_deepseek_api()
        self.assertIs(api1, api3)

    def test_init_checks_ollama_availability(self):
        """Test sprawdzania dostępności Ollama podczas inicjalizacji."""
        DeepSeekAPI()
        
        # Powinno być wywołanie sprawdzające dostępność Ollama
        self.mock_requests_get.assert_called_once_with("http://localhost:11434/api/tags")

    def test_init_logs_warning_when_no_deepseek_models(self):
        """Test ostrzeżenia, gdy nie znaleziono modeli DeepSeek."""
        self.mock_requests_get.return_value.json.return_value = {
            "models": [
                {"name": "other-model-1"},
                {"name": "other-model-2"}
            ]
        }
        
        with self.assertLogs(level='WARNING') as cm:
            DeepSeekAPI()
            self.assertIn("Nie znaleziono modeli DeepSeek w Ollama", cm.output[0])

    def test_init_logs_warning_on_connection_error(self):
        """Test obsługi błędu połączenia z Ollama."""
        self.mock_requests_get.side_effect = requests.RequestException("Błąd połączenia")
        
        with self.assertLogs(level='WARNING') as cm:
            DeepSeekAPI()
            self.assertIn("Nie można połączyć się z lokalnym Ollama", cm.output[0])

    def test_set_model(self):
        """Test ustawiania modelu."""
        api = DeepSeekAPI()
        default_model = api.model
        
        # Zmiana modelu
        new_model = "deepseek-instruct"
        api.set_model(new_model)
        
        # Sprawdzenie, czy model został zmieniony
        self.assertEqual(api.model, new_model)
        self.assertNotEqual(api.model, default_model)

    def test_set_parameters(self):
        """Test ustawiania parametrów generowania."""
        api = DeepSeekAPI()
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

    @patch('src.ai_models.deepseek_api.requests.post')
    def test_generate_response_success(self, mock_post):
        """Test udanego generowania odpowiedzi."""
        # Przygotowanie mocka odpowiedzi
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "response": "To jest odpowiedź testowa",
            "prompt_eval_count": 10,
            "eval_count": 20
        }
        mock_post.return_value = mock_response
        
        api = DeepSeekAPI()
        result = api.generate_response("Testowe zapytanie", system_prompt="Testowy prompt systemowy")
        
        # Sprawdzenie, czy wywołanie POST było poprawne
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        self.assertEqual(args[0], "http://localhost:11434/api/generate")
        self.assertEqual(kwargs['headers'], {"Content-Type": "application/json"})
        
        # Sprawdzenie struktury payloadu
        payload = json.loads(kwargs['json'])
        self.assertEqual(payload['model'], api.model)
        self.assertEqual(payload['prompt'], "Testowe zapytanie")
        self.assertEqual(payload['system'], "Testowy prompt systemowy")
        
        # Sprawdzenie rezultatu
        self.assertEqual(result['response'], "To jest odpowiedź testowa")
        self.assertEqual(result['model'], api.model)
        self.assertEqual(result['tokens_used']['prompt'], 10)
        self.assertEqual(result['tokens_used']['completion'], 20)
        self.assertEqual(result['tokens_used']['total'], 30)
        self.assertIn('timestamp', result)
        self.assertIn('response_time', result)

    @patch('src.ai_models.deepseek_api.requests.post')
    def test_generate_response_error(self, mock_post):
        """Test obsługi błędu podczas generowania odpowiedzi."""
        # Przygotowanie mocka odpowiedzi z błędem
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_post.return_value = mock_response
        
        api = DeepSeekAPI()
        result = api.generate_response("Testowe zapytanie")
        
        # Sprawdzenie, czy wynik zawiera informacje o błędzie
        self.assertIn('error', result)
        self.assertIn('timestamp', result)
        self.assertIn('500', result['error'])

    @patch('src.ai_models.deepseek_api.requests.post')
    def test_generate_response_connection_error(self, mock_post):
        """Test obsługi błędu połączenia."""
        # Symulacja błędu połączenia
        mock_post.side_effect = requests.RequestException("Błąd połączenia")
        
        api = DeepSeekAPI()
        result = api.generate_response("Testowe zapytanie")
        
        # Sprawdzenie, czy wynik zawiera informacje o błędzie
        self.assertIn('error', result)
        self.assertIn('timestamp', result)
        self.assertIn('Błąd połączenia', result['error'])

    @patch('src.ai_models.deepseek_api.requests.post')
    def test_generate_response_retry_on_error(self, mock_post):
        """Test ponownych prób przy błędzie."""
        # Pierwsze wywołanie kończy się błędem, drugie sukcesem
        mock_error_response = MagicMock()
        mock_error_response.status_code = 500
        mock_error_response.text = "Internal Server Error"
        
        mock_success_response = MagicMock()
        mock_success_response.status_code = 200
        mock_success_response.json.return_value = {
            "response": "Sukces po ponownej próbie",
            "prompt_eval_count": 10,
            "eval_count": 20
        }
        
        mock_post.side_effect = [mock_error_response, mock_success_response]
        
        api = DeepSeekAPI()
        result = api.generate_response("Testowe zapytanie")
        
        # Sprawdzenie, czy była ponowna próba
        self.assertEqual(mock_post.call_count, 2)
        
        # Sprawdzenie, czy ostatecznie uzyskano sukces
        self.assertEqual(result['response'], "Sukces po ponownej próbie")

    @patch('src.ai_models.deepseek_api.DeepSeekAPI.generate_response')
    def test_analyze_market_data(self, mock_generate):
        """Test analizy danych rynkowych."""
        # Przygotowanie mocka odpowiedzi
        mock_generate.return_value = {
            "response": """Analiza danych rynkowych:
            
            ```json
            {
                "trend": "bullish",
                "strength": 8,
                "support_levels": [2900, 2850],
                "resistance_levels": [3000, 3050],
                "key_indicators": {
                    "RSI": "wykupiony",
                    "MACD": "pozytywny sygnał"
                },
                "outlook_short_term": "pozytywny",
                "outlook_medium_term": "neutralny",
                "key_factors": ["wsparcie banku centralnego", "niskie stopy"],
                "confidence_level": 7
            }
            ```
            
            To jest dodatkowy opis, który nie powinien trafić do wyniku."""
        }
        
        api = DeepSeekAPI()
        market_data = {
            "symbol": "GOLD.pro",
            "current_price": 2950.75,
            "technical_indicators": {
                "RSI": 68,
                "MACD": 0.45
            }
        }
        
        result = api.analyze_market_data(market_data, "technical")
        
        # Sprawdzenie, czy wywołano generate_response z odpowiednimi parametrami
        mock_generate.assert_called_once()
        args, kwargs = mock_generate.call_args
        self.assertIn("GOLD.pro", args[0])
        self.assertIn("2950.75", args[0])
        self.assertIn("technical", args[0])
        
        # Sprawdzenie rezultatu
        self.assertTrue(result['success'])
        self.assertEqual(result['analysis']['trend'], "bullish")
        self.assertEqual(result['analysis']['strength'], 8)
        self.assertEqual(result['analysis']['support_levels'], [2900, 2850])
        self.assertIn('timestamp', result)
        self.assertEqual(result['analysis_type'], "technical")

    @patch('src.ai_models.deepseek_api.DeepSeekAPI.generate_response')
    def test_analyze_market_data_invalid_json(self, mock_generate):
        """Test obsługi niepoprawnego JSON w analizie danych rynkowych."""
        # Przygotowanie mocka odpowiedzi z niepoprawnym JSON
        mock_generate.return_value = {
            "response": "To nie jest poprawny format JSON"
        }
        
        api = DeepSeekAPI()
        market_data = {"symbol": "GOLD.pro", "current_price": 2950.75}
        result = api.analyze_market_data(market_data, "technical")
        
        # Sprawdzenie, czy wynik zawiera informacje o błędzie
        self.assertFalse(result['success'])
        self.assertIn('error', result)
        self.assertIn('raw_response', result)

    @patch('src.ai_models.deepseek_api.DeepSeekAPI.generate_response')
    def test_analyze_market_data_api_error(self, mock_generate):
        """Test obsługi błędu API w analizie danych rynkowych."""
        # Przygotowanie mocka odpowiedzi z błędem API
        mock_generate.return_value = {
            "error": "Błąd API",
            "timestamp": datetime.now().isoformat()
        }
        
        api = DeepSeekAPI()
        market_data = {"symbol": "GOLD.pro", "current_price": 2950.75}
        result = api.analyze_market_data(market_data, "technical")
        
        # Sprawdzenie, czy wynik zawiera informacje o błędzie
        self.assertFalse(result['success'])
        self.assertIn('error', result)

    @patch('src.ai_models.deepseek_api.DeepSeekAPI.generate_response')
    def test_generate_trading_decision(self, mock_generate):
        """Test generowania decyzji handlowej."""
        # Przygotowanie mocka odpowiedzi
        mock_generate.return_value = {
            "response": """Decyzja handlowa:
            
            ```json
            {
                "action": "BUY",
                "entry_price": 2950.0,
                "position_size": 0.1,
                "stop_loss": 2900.0,
                "take_profit": 3050.0,
                "confidence_level": 8,
                "reasoning": ["silny trend wzrostowy", "wsparcie na poziomie 2900"],
                "risk_percent": 1.5,
                "expected_risk_reward": 2.0
            }
            ```
            
            Dodatkowe informacje, które nie powinny trafić do wyniku."""
        }
        
        api = DeepSeekAPI()
        market_data = {
            "symbol": "GOLD.pro",
            "current_price": 2950.75,
            "technical_indicators": {
                "RSI": 68,
                "MACD": 0.45
            }
        }
        risk_parameters = {
            "max_risk_per_trade": 2.0,
            "max_exposure_per_symbol": 5.0,
            "target_risk_reward": 2.0
        }
        
        result = api.generate_trading_decision(market_data, risk_parameters)
        
        # Sprawdzenie, czy wywołano generate_response z odpowiednimi parametrami
        mock_generate.assert_called_once()
        args, kwargs = mock_generate.call_args
        self.assertIn("GOLD.pro", args[0])
        self.assertIn("2950.75", args[0])
        self.assertIn("max_risk_per_trade", args[0])
        
        # Sprawdzenie rezultatu
        self.assertTrue(result['success'])
        self.assertEqual(result['decision']['action'], "BUY")
        self.assertEqual(result['decision']['entry_price'], 2950.0)
        self.assertEqual(result['decision']['position_size'], 0.1)
        self.assertEqual(result['decision']['stop_loss'], 2900.0)
        self.assertEqual(result['decision']['take_profit'], 3050.0)
        self.assertIn('timestamp', result)

    @patch('src.ai_models.deepseek_api.DeepSeekAPI.generate_response')
    def test_generate_trading_decision_invalid_json(self, mock_generate):
        """Test obsługi niepoprawnego JSON w generowaniu decyzji handlowej."""
        # Przygotowanie mocka odpowiedzi z niepoprawnym JSON
        mock_generate.return_value = {
            "response": "To nie jest poprawny format JSON"
        }
        
        api = DeepSeekAPI()
        market_data = {"symbol": "GOLD.pro", "current_price": 2950.75}
        risk_parameters = {"max_risk_per_trade": 2.0}
        result = api.generate_trading_decision(market_data, risk_parameters)
        
        # Sprawdzenie, czy wynik zawiera informacje o błędzie
        self.assertFalse(result['success'])
        self.assertIn('error', result)
        self.assertIn('raw_response', result)

    @patch('src.ai_models.deepseek_api.DeepSeekAPI.generate_response')
    def test_generate_trading_decision_api_error(self, mock_generate):
        """Test obsługi błędu API w generowaniu decyzji handlowej."""
        # Przygotowanie mocka odpowiedzi z błędem API
        mock_generate.return_value = {
            "error": "Błąd API",
            "timestamp": datetime.now().isoformat()
        }
        
        api = DeepSeekAPI()
        market_data = {"symbol": "GOLD.pro", "current_price": 2950.75}
        risk_parameters = {"max_risk_per_trade": 2.0}
        result = api.generate_trading_decision(market_data, risk_parameters)
        
        # Sprawdzenie, czy wynik zawiera informacje o błędzie
        self.assertFalse(result['success'])
        self.assertIn('error', result)


if __name__ == '__main__':
    unittest.main() 