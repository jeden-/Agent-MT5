#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Skrypt testujący połączenie z API DeepSeek poprzez lokalny serwer Ollama.
Sprawdza podstawowe funkcjonalności API i generuje raport z wynikami testów.
"""

import os
import sys
import time
import json
import logging
import argparse
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple

# Dodanie głównego katalogu projektu do ścieżki
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import modułu DeepSeekAPI
from src.ai_models.deepseek_api import DeepSeekAPI
from scripts.check_ollama import check_ollama_running, check_deepseek_models, pull_model, start_ollama

# Konfiguracja logowania
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/deepseek_connection_test.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("deepseek_connection_test")

def setup_environment() -> bool:
    """
    Sprawdza i konfiguruje środowisko do testów.
    
    Returns:
        bool: Czy konfiguracja się powiodła
    """
    logger.info("Sprawdzanie środowiska do testów DeepSeek API...")
    
    # Sprawdzenie, czy Ollama jest uruchomiona
    is_running, version = check_ollama_running()
    if not is_running:
        logger.error("Ollama nie jest uruchomiona. Próba uruchomienia...")
        if not start_ollama():
            logger.error("Nie udało się uruchomić Ollama. Instalacja: https://ollama.com/download")
            return False
    else:
        logger.info(f"Ollama jest uruchomiona (wersja {version})")
    
    # Sprawdzenie dostępności modeli DeepSeek
    available_models = check_deepseek_models()
    if not available_models:
        logger.error("Nie znaleziono żadnych modeli DeepSeek. Próba pobrania zalecanego modelu...")
        if not pull_model("deepseek-r1:8b"):
            logger.error("Nie udało się pobrać modelu DeepSeek.")
            return False
        else:
            logger.info("Model DeepSeek pomyślnie pobrany")
    else:
        logger.info(f"Dostępne modele DeepSeek: {', '.join(available_models)}")
    
    # Tworzenie katalogu na logi, jeśli nie istnieje
    os.makedirs("logs", exist_ok=True)
    
    return True

def test_basic_response() -> Tuple[bool, Dict[str, Any]]:
    """
    Testuje podstawową odpowiedź z modelu DeepSeek.
    
    Returns:
        Tuple[bool, Dict]: (sukces, rezultat)
    """
    logger.info("Test 1: Podstawowa odpowiedź z modelu DeepSeek")
    
    try:
        api = DeepSeekAPI()
        start_time = time.time()
        
        response = api.generate_response(
            prompt="Witaj, jestem traderem. Powiedz mi jakie są kluczowe wskaźniki ekonomiczne do analizy rynku FOREX?",
            system_prompt="Jesteś ekspertem w analizie rynków finansowych."
        )
        
        execution_time = time.time() - start_time
        
        if response.get('success', False) and response.get('response'):
            logger.info(f"Test 1 zakończony sukcesem (czas: {execution_time:.2f}s)")
            logger.info(f"Otrzymano odpowiedź o długości {len(response['response'])} znaków")
            logger.info(f"Użyto {response.get('tokens_used', {}).get('total', 0)} tokenów")
            return True, response
        else:
            logger.error(f"Test 1 nie powiódł się: {response.get('error', 'Brak odpowiedzi')}")
            return False, response
    
    except Exception as e:
        logger.error(f"Wyjątek podczas testu 1: {str(e)}")
        return False, {"error": str(e), "success": False}

def test_market_analysis() -> Tuple[bool, Dict[str, Any]]:
    """
    Testuje analizę danych rynkowych.
    
    Returns:
        Tuple[bool, Dict]: (sukces, rezultat)
    """
    logger.info("Test 2: Analiza danych rynkowych")
    
    try:
        api = DeepSeekAPI()
        
        # Przykładowe dane rynkowe
        market_data = {
            "symbol": "EURUSD",
            "current_price": 1.0875,
            "open": 1.0850,
            "high": 1.0890,
            "low": 1.0845,
            "previous_close": 1.0860,
            "volume": 23450,
            "technical_indicators": {
                "RSI": 58.5,
                "MACD": {
                    "line": 0.0012,
                    "signal": 0.0008,
                    "histogram": 0.0004
                },
                "MA_50": 1.0830,
                "MA_200": 1.0790,
                "Bollinger_bands": {
                    "upper": 1.0920,
                    "middle": 1.0850,
                    "lower": 1.0780
                }
            },
            "news": [
                {
                    "title": "ECB utrzymuje stopy procentowe",
                    "time": "2023-05-10T12:00:00Z",
                    "impact": "high"
                },
                {
                    "title": "Dane o inflacji w USA niższe od oczekiwań",
                    "time": "2023-05-11T14:30:00Z",
                    "impact": "high"
                }
            ]
        }
        
        start_time = time.time()
        result = api.analyze_market_data(market_data, analysis_type="technical")
        execution_time = time.time() - start_time
        
        if result.get('success', False) and result.get('analysis'):
            logger.info(f"Test 2 zakończony sukcesem (czas: {execution_time:.2f}s)")
            logger.info(f"Wynik analizy: {json.dumps(result['analysis'], indent=2, ensure_ascii=False)}")
            return True, result
        else:
            logger.error(f"Test 2 nie powiódł się: {result.get('error', 'Brak wyniku analizy')}")
            return False, result
    
    except Exception as e:
        logger.error(f"Wyjątek podczas testu 2: {str(e)}")
        return False, {"error": str(e), "success": False}

def test_trading_decision() -> Tuple[bool, Dict[str, Any]]:
    """
    Testuje generowanie decyzji tradingowej.
    
    Returns:
        Tuple[bool, Dict]: (sukces, rezultat)
    """
    logger.info("Test 3: Generowanie decyzji tradingowej")
    
    try:
        api = DeepSeekAPI()
        
        # Przykładowe dane rynkowe
        market_data = {
            "symbol": "GOLD.pro",
            "current_price": 2150.25,
            "open": 2145.50,
            "high": 2155.30,
            "low": 2140.20,
            "previous_close": 2147.85,
            "volume": 12500,
            "technical_indicators": {
                "RSI": 62.3,
                "MACD": {
                    "line": 2.45,
                    "signal": 1.85,
                    "histogram": 0.60
                },
                "MA_50": 2100.50,
                "MA_200": 2050.75
            },
            "sentiment": {
                "overall": "bullish",
                "strength": 7
            }
        }
        
        # Parametry ryzyka
        risk_parameters = {
            "account_balance": 10000,
            "max_risk_per_trade": 0.02,  # 2% kapitału
            "max_open_positions": 5,
            "current_open_positions": 2,
            "risk_appetite": "moderate"  # low, moderate, high
        }
        
        start_time = time.time()
        result = api.generate_trading_decision(market_data, risk_parameters)
        execution_time = time.time() - start_time
        
        if result.get('success', False) and result.get('decision'):
            logger.info(f"Test 3 zakończony sukcesem (czas: {execution_time:.2f}s)")
            logger.info(f"Decyzja tradingowa: {json.dumps(result['decision'], indent=2, ensure_ascii=False)}")
            return True, result
        else:
            logger.error(f"Test 3 nie powiódł się: {result.get('error', 'Brak decyzji tradingowej')}")
            return False, result
    
    except Exception as e:
        logger.error(f"Wyjątek podczas testu 3: {str(e)}")
        return False, {"error": str(e), "success": False}

def generate_report(test_results: Dict[str, Any]) -> str:
    """
    Generuje raport z wynikami testów.
    
    Args:
        test_results: Wyniki testów
        
    Returns:
        str: Ścieżka do pliku z raportem
    """
    now = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = f"logs/deepseek_test_report_{now}.html"
    
    # Obliczenie podsumowania
    total_tests = len(test_results)
    successful_tests = sum(1 for test in test_results.values() if test.get('success', False))
    failure_tests = total_tests - successful_tests
    success_rate = (successful_tests / total_tests) * 100 if total_tests > 0 else 0
    
    # Generowanie zawartości HTML
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Raport z testów połączenia z DeepSeek API</title>
        <style>
            body {{
                font-family: Arial, sans-serif;
                line-height: 1.6;
                margin: 0;
                padding: 20px;
                color: #333;
            }}
            h1, h2, h3 {{
                color: #0066cc;
            }}
            .container {{
                max-width: 1200px;
                margin: 0 auto;
                padding: 20px;
                background-color: #f9f9f9;
                border-radius: 5px;
                box-shadow: 0 2px 5px rgba(0, 0, 0, 0.1);
            }}
            .summary {{
                display: flex;
                justify-content: space-between;
                background-color: #e9f7fe;
                padding: 15px;
                border-radius: 5px;
                margin-bottom: 20px;
            }}
            .summary-item {{
                text-align: center;
            }}
            .summary-value {{
                font-size: 24px;
                font-weight: bold;
                margin-bottom: 5px;
            }}
            .summary-label {{
                font-size: 14px;
            }}
            .test-result {{
                background-color: white;
                padding: 15px;
                margin-bottom: 15px;
                border-radius: 5px;
                border-left: 5px solid #ddd;
            }}
            .test-result.success {{
                border-left-color: #28a745;
            }}
            .test-result.failure {{
                border-left-color: #dc3545;
            }}
            .test-header {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 10px;
            }}
            .test-name {{
                font-weight: bold;
                font-size: 18px;
            }}
            .test-status {{
                padding: 5px 10px;
                border-radius: 20px;
                font-size: 14px;
                font-weight: bold;
            }}
            .status-success {{
                background-color: #d4edda;
                color: #155724;
            }}
            .status-failure {{
                background-color: #f8d7da;
                color: #721c24;
            }}
            pre {{
                background-color: #f5f5f5;
                padding: 10px;
                border-radius: 5px;
                overflow-x: auto;
            }}
            .metrics {{
                display: grid;
                grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
                gap: 10px;
                margin-bottom: 15px;
            }}
            .metric-item {{
                background-color: #f5f5f5;
                padding: 10px;
                border-radius: 5px;
            }}
            .metric-label {{
                font-size: 14px;
                color: #666;
            }}
            .metric-value {{
                font-size: 16px;
                font-weight: bold;
            }}
            footer {{
                margin-top: 30px;
                text-align: center;
                font-size: 14px;
                color: #666;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Raport z testów połączenia z DeepSeek API</h1>
            <p>Wygenerowano: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
            
            <div class="summary">
                <div class="summary-item">
                    <div class="summary-value">{total_tests}</div>
                    <div class="summary-label">Wszystkich testów</div>
                </div>
                <div class="summary-item">
                    <div class="summary-value">{successful_tests}</div>
                    <div class="summary-label">Udanych</div>
                </div>
                <div class="summary-item">
                    <div class="summary-value">{failure_tests}</div>
                    <div class="summary-label">Nieudanych</div>
                </div>
                <div class="summary-item">
                    <div class="summary-value">{success_rate:.1f}%</div>
                    <div class="summary-label">Wskaźnik powodzenia</div>
                </div>
            </div>
            
            <h2>Szczegółowe wyniki testów</h2>
    """
    
    # Dodanie wyników poszczególnych testów
    for test_name, result in test_results.items():
        success = result.get('success', False)
        status_class = "success" if success else "failure"
        status_text = "SUKCES" if success else "NIEPOWODZENIE"
        status_style = "status-success" if success else "status-failure"
        
        html_content += f"""
            <div class="test-result {status_class}">
                <div class="test-header">
                    <div class="test-name">{test_name}</div>
                    <div class="test-status {status_style}">{status_text}</div>
                </div>
        """
        
        # Metryki wykonania
        if 'execution_time' in result or 'tokens_used' in result:
            html_content += '<div class="metrics">'
            
            if 'execution_time' in result:
                html_content += f"""
                    <div class="metric-item">
                        <div class="metric-label">Czas wykonania</div>
                        <div class="metric-value">{result['execution_time']:.2f} s</div>
                    </div>
                """
                
            if 'tokens_used' in result and isinstance(result['tokens_used'], dict):
                tokens = result['tokens_used']
                html_content += f"""
                    <div class="metric-item">
                        <div class="metric-label">Tokeny (prompt)</div>
                        <div class="metric-value">{tokens.get('prompt', 0)}</div>
                    </div>
                    <div class="metric-item">
                        <div class="metric-label">Tokeny (odpowiedź)</div>
                        <div class="metric-value">{tokens.get('completion', 0)}</div>
                    </div>
                    <div class="metric-item">
                        <div class="metric-label">Tokeny (łącznie)</div>
                        <div class="metric-value">{tokens.get('total', 0)}</div>
                    </div>
                """
                
            html_content += '</div>'
        
        # Dane wynikowe w zależności od testu
        if test_name == "Test podstawowej odpowiedzi":
            if 'response' in result:
                response_snippet = result['response'][:500] + "..." if len(result['response']) > 500 else result['response']
                html_content += f"""
                    <h3>Odpowiedź modelu (fragment):</h3>
                    <pre>{response_snippet}</pre>
                """
        elif test_name == "Test analizy rynku":
            if 'analysis' in result:
                html_content += f"""
                    <h3>Wynik analizy:</h3>
                    <pre>{json.dumps(result['analysis'], indent=2, ensure_ascii=False)}</pre>
                """
        elif test_name == "Test decyzji tradingowej":
            if 'decision' in result:
                html_content += f"""
                    <h3>Decyzja tradingowa:</h3>
                    <pre>{json.dumps(result['decision'], indent=2, ensure_ascii=False)}</pre>
                """
        
        # Błędy
        if not success and 'error' in result:
            html_content += f"""
                <h3>Błąd:</h3>
                <pre>{result['error']}</pre>
            """
            
        html_content += "</div>"
    
    # Zakończenie HTML
    html_content += """
            <footer>
                <p>AgentMT5 - Test połączenia z DeepSeek API</p>
            </footer>
        </div>
    </body>
    </html>
    """
    
    # Zapisanie do pliku
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    logger.info(f"Raport wygenerowany: {report_path}")
    return report_path

def main():
    """Główna funkcja skryptu."""
    parser = argparse.ArgumentParser(description="Test połączenia z API DeepSeek")
    parser.add_argument("--setup", action="store_true", help="Automatycznie konfiguruje środowisko (uruchamia Ollama, pobiera modele)")
    parser.add_argument("--report", action="store_true", help="Generuje raport HTML z wynikami testów")
    
    args = parser.parse_args()
    
    # Utworzenie katalogu na logi, jeśli nie istnieje
    os.makedirs("logs", exist_ok=True)
    
    logger.info("Rozpoczynam test połączenia z API DeepSeek")
    
    # Konfiguracja środowiska, jeśli wymagana
    if args.setup:
        if not setup_environment():
            logger.error("Nie udało się skonfigurować środowiska. Przerywam testy.")
            return 1
    
    # Wykonanie testów
    test_results = {}
    
    # Test 1: Podstawowa odpowiedź
    success, result = test_basic_response()
    result['success'] = success
    result['execution_time'] = result.get('response_time', 0)
    test_results["Test podstawowej odpowiedzi"] = result
    
    # Test 2: Analiza rynku
    success, result = test_market_analysis()
    result['success'] = success
    test_results["Test analizy rynku"] = result
    
    # Test 3: Decyzja tradingowa
    success, result = test_trading_decision()
    result['success'] = success
    test_results["Test decyzji tradingowej"] = result
    
    # Podsumowanie wyników
    total_tests = len(test_results)
    successful_tests = sum(1 for result in test_results.values() if result.get('success', False))
    
    logger.info(f"Zakończono testy. Wynik: {successful_tests}/{total_tests} testów zakończonych sukcesem.")
    
    # Generowanie raportu, jeśli wymagane
    if args.report:
        report_path = generate_report(test_results)
        logger.info(f"Raport dostępny pod ścieżką: {report_path}")
    
    # Zwrócenie kodu błędu, jeśli którykolwiek test nie powiódł się
    return 0 if successful_tests == total_tests else 1

if __name__ == "__main__":
    sys.exit(main()) 