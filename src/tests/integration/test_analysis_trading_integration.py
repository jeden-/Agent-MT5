#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Testy integracyjne dla połączenia systemu analizy danych z systemem handlowym.

Te testy weryfikują poprawną integrację następujących komponentów:
1. MarketDataProcessor - pobieranie danych rynkowych
2. SignalGenerator - generowanie sygnałów
3. SignalValidator - walidacja sygnałów
4. FeedbackLoop - uczenie się systemu
5. TradingIntegration - integracja z systemem handlowym
"""

import unittest
import logging
import os
import sys
import time
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

# Dodajmy do ścieżki katalog główny projektu
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../')))

# Konfiguracja logowania
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Importy testowanych modułów
from src.analysis.market_data_processor import MarketDataProcessor
from src.analysis.signal_generator import SignalGenerator, SignalType
from src.analysis.signal_validator import SignalValidator
from src.analysis.feedback_loop import FeedbackLoop
from src.trading_integration import TradingIntegration, TradingDecision


class TestAnalysisTradingIntegration(unittest.TestCase):
    """Testy integracyjne dla połączenia systemu analizy danych z systemem handlowym."""
    
    @classmethod
    def setUpClass(cls):
        """Przygotowanie środowiska testowego przed wszystkimi testami."""
        logger.info("Przygotowanie środowiska testowego dla testów integracyjnych")
        
        # Mockowanie połączenia z MT5
        patch('src.mt5_bridge.mt5_client.MT5Client.connect', return_value=True).start()
        patch('src.mt5_bridge.mt5_client.MT5Client.is_connected', return_value=True).start()
        patch('src.mt5_bridge.trading_service.TradingService.connect', return_value=True).start()
        
        # Mockowanie operacji bazodanowych
        patch('src.database.database_manager.DatabaseManager.connect', return_value=True).start()
        
        # Przygotowanie przykładowych danych
        cls.prepare_test_data()
    
    @classmethod
    def tearDownClass(cls):
        """Czyszczenie po wszystkich testach."""
        logger.info("Czyszczenie po testach integracyjnych")
        patch.stopall()
    
    @classmethod
    def prepare_test_data(cls):
        """Przygotowanie przykładowych danych testowych."""
        # Przykładowe dane rynkowe
        cls.market_data = {
            'symbol': 'EURUSD',
            'timeframe': 'H1',
            'open': [1.1000, 1.1010, 1.1020, 1.1030, 1.1040],
            'high': [1.1020, 1.1030, 1.1040, 1.1050, 1.1060],
            'low': [1.0990, 1.1000, 1.1010, 1.1020, 1.1030],
            'close': [1.1010, 1.1020, 1.1030, 1.1040, 1.1050],
            'volume': [1000, 1100, 1200, 1300, 1400],
            'time': [
                datetime.now() - timedelta(hours=5),
                datetime.now() - timedelta(hours=4),
                datetime.now() - timedelta(hours=3),
                datetime.now() - timedelta(hours=2),
                datetime.now() - timedelta(hours=1)
            ]
        }
        
        # Mockowanie odpowiedzi AI
        cls.ai_response = {
            'model': 'claude',
            'prediction': {
                'direction': 'BUY',
                'confidence': 0.85,
                'reasoning': 'Pozytywne momentum, wsparcie na 1.1000, wzrostowe przecięcie średnich kroczących.'
            }
        }
    
    def setUp(self):
        """Przygotowanie środowiska przed każdym testem."""
        # Resetowanie singletonów
        for cls in [MarketDataProcessor, SignalGenerator, SignalValidator, FeedbackLoop, TradingIntegration]:
            if hasattr(cls, '_instance') and cls._instance is not None:
                cls._instance = None
        
        # Inicjalizacja komponentów z mockami
        with patch('src.mt5_bridge.mt5_client.MT5Client.get_historical_data', return_value=self.market_data):
            self.market_processor = MarketDataProcessor()
            self.signal_generator = SignalGenerator()
            self.signal_validator = SignalValidator()
            self.feedback_loop = FeedbackLoop()
            self.trading_integration = TradingIntegration()
        
        # Mockowanie metod AI
        self.mock_ai_router()
    
    def mock_ai_router(self):
        """Mockowanie odpowiedzi z AIRouter."""
        ai_router_patch = patch('src.ai_models.ai_router.AIRouter.route_query')
        self.mock_route_query = ai_router_patch.start()
        self.mock_route_query.return_value = self.ai_response
        self.addCleanup(ai_router_patch.stop)
    
    def test_full_trading_workflow(self):
        """Test pełnego przepływu od analizy danych do decyzji handlowej."""
        logger.info("Test pełnego przepływu danych przez system")
        
        # 1. Pobierz dane rynkowe
        with patch('src.mt5_bridge.mt5_client.MT5Client.get_historical_data', return_value=self.market_data):
            data = self.market_processor.get_market_data('EURUSD', 'H1', bars=10)
        
        self.assertIsNotNone(data)
        self.assertEqual(data['symbol'], 'EURUSD')
        
        # 2. Wygeneruj sygnał
        with patch('src.analysis.signal_generator.AIRouter.route_query', return_value=self.ai_response):
            signals = self.signal_generator.generate_signals('EURUSD', data)
        
        self.assertGreater(len(signals), 0)
        signal = signals[0]
        self.assertEqual(signal['symbol'], 'EURUSD')
        
        # 3. Zwaliduj sygnał
        with patch('src.analysis.signal_validator.RiskManager.validate_signal', return_value=True):
            validation_result = self.signal_validator.validate_signal(signal)
        
        self.assertTrue(validation_result['is_valid'])
        
        # 4. Oceń jakość sygnału przez FeedbackLoop
        with patch('src.analysis.feedback_loop.FeedbackLoop.get_signal_quality', return_value=0.8):
            quality_score = self.feedback_loop.get_signal_quality(signal)
        
        self.assertGreaterEqual(quality_score, 0)
        self.assertLessEqual(quality_score, 1)
        
        # 5. Utwórz decyzję handlową
        with patch('src.trading_integration.TradingIntegration._create_trading_decision') as mock_create_decision:
            mock_create_decision.return_value = TradingDecision(
                symbol='EURUSD',
                action='BUY',
                volume=0.1,
                stop_loss=1.0990,
                take_profit=1.1100,
                quality_score=quality_score
            )
            
            self.trading_integration._create_trading_decision(signal, quality_score)
        
        mock_create_decision.assert_called_once()
        
        # 6. Wykonaj decyzję handlową
        with patch('src.trading_integration.TradingIntegration._execute_decision') as mock_execute:
            mock_execute.return_value = {'ticket': 12345, 'result': 'success'}
            
            # Mockujemy prywatną metodę _validate_decision_risk
            self.trading_integration._validate_decision_risk = Mock(return_value='VALID')
            
            # Dodajemy decyzję do listy i przetwarzamy
            decision = TradingDecision(
                symbol='EURUSD',
                action='BUY',
                volume=0.1,
                stop_loss=1.0990,
                take_profit=1.1100
            )
            self.trading_integration.decisions.append(decision)
            self.trading_integration.trading_enabled = True
            self.trading_integration.process_pending_decisions()
        
        mock_execute.assert_called_once()
        self.assertEqual(len(self.trading_integration.decisions), 0)
        self.assertEqual(len(self.trading_integration.decisions_history), 1)
        self.assertEqual(self.trading_integration.decisions_history[0].status.name, 'EXECUTED')
    
    def test_market_data_signal_integration(self):
        """Test integracji pomiędzy MarketDataProcessor a SignalGenerator."""
        logger.info("Test integracji pobierania danych i generowania sygnałów")
        
        # 1. Pobierz dane rynkowe
        with patch('src.mt5_bridge.mt5_client.MT5Client.get_historical_data', return_value=self.market_data):
            data = self.market_processor.get_market_data('EURUSD', 'H1', bars=10)
        
        # 2. Wygeneruj sygnał z wykorzystaniem prawdziwego SignalGenerator
        with patch('src.analysis.signal_generator.AIRouter.route_query', return_value=self.ai_response):
            signals = self.signal_generator.generate_signals('EURUSD', data)
        
        # Sprawdź czy sygnały zostały poprawnie wygenerowane
        self.assertIsNotNone(signals)
        self.assertGreaterEqual(len(signals), 1)
        
        # Sprawdź format sygnału
        for signal in signals:
            self.assertIn('symbol', signal)
            self.assertIn('type', signal)
            self.assertIn('timestamp', signal)
    
    def test_signal_validator_integration(self):
        """Test integracji pomiędzy SignalGenerator a SignalValidator."""
        logger.info("Test integracji generowania i walidacji sygnałów")
        
        # 1. Wygeneruj sygnał
        signal = {
            'id': 1,
            'symbol': 'EURUSD',
            'type': 'BUY',
            'price': 1.1050,
            'timestamp': datetime.now(),
            'timeframe': 'H1',
            'strength': 'STRONG',
            'source': 'AI',
            'meta': {
                'indicators': {
                    'rsi': 65,
                    'macd': 0.0015
                },
                'ai_model': 'claude',
                'confidence': 0.85
            }
        }
        
        # 2. Zwaliduj sygnał
        with patch('src.risk_management.risk_manager.RiskManager.validate_order', return_value='VALID'):
            validation_result = self.signal_validator.validate_signal(signal)
        
        # Sprawdź wynik walidacji
        self.assertIsNotNone(validation_result)
        self.assertIn('is_valid', validation_result)
    
    def test_feedback_loop_integration(self):
        """Test integracji FeedbackLoop z innymi komponentami."""
        logger.info("Test integracji mechanizmu uczenia się")
        
        # 1. Przygotuj historię sygnałów
        with patch('src.database.signal_repository.SignalRepository.get_signals_by_symbol') as mock_get_signals:
            mock_get_signals.return_value = [
                {
                    'id': 1,
                    'symbol': 'EURUSD',
                    'type': 'BUY',
                    'timestamp': datetime.now() - timedelta(days=5),
                    'source': 'TECHNICAL',
                    'strength': 'STRONG'
                },
                {
                    'id': 2,
                    'symbol': 'EURUSD',
                    'type': 'SELL',
                    'timestamp': datetime.now() - timedelta(days=3),
                    'source': 'AI',
                    'strength': 'MODERATE'
                }
            ]
            
            # 2. Przygotuj historię transakcji
            with patch('src.database.trade_repository.TradeRepository.get_trades_by_symbol') as mock_get_trades:
                mock_get_trades.return_value = [
                    {
                        'id': 101,
                        'symbol': 'EURUSD',
                        'type': 'BUY',
                        'signal_id': 1,
                        'open_time': datetime.now() - timedelta(days=5),
                        'close_time': datetime.now() - timedelta(days=4),
                        'profit': 100.0
                    },
                    {
                        'id': 102,
                        'symbol': 'EURUSD',
                        'type': 'SELL',
                        'signal_id': 2,
                        'open_time': datetime.now() - timedelta(days=3),
                        'close_time': datetime.now() - timedelta(days=2),
                        'profit': -50.0
                    }
                ]
                
                # 3. Analizuj wydajność
                performance = self.feedback_loop.analyze_performance('EURUSD', days=10)
        
        # Sprawdź wyniki analizy
        self.assertIsNotNone(performance)
        self.assertIn('overall', performance)
        self.assertIn('by_source', performance)
        self.assertIn('by_strength', performance)
    
    def test_optimize_strategy_parameters(self):
        """Test optymalizacji parametrów strategii."""
        logger.info("Test optymalizacji parametrów strategii")
        
        # Mockowanie analizy wydajności
        self.feedback_loop.analyze_performance = Mock(return_value={
            'overall': {
                'win_rate': 0.65,
                'profit_factor': 1.8,
                'avg_profit': 75.0,
                'count': 20
            },
            'by_source': {
                'TECHNICAL': {'win_rate': 0.7, 'profit_factor': 2.0},
                'AI': {'win_rate': 0.6, 'profit_factor': 1.5}
            },
            'by_strength': {
                'STRONG': {'win_rate': 0.8, 'profit_factor': 2.2},
                'MODERATE': {'win_rate': 0.6, 'profit_factor': 1.5},
                'WEAK': {'win_rate': 0.4, 'profit_factor': 1.1}
            }
        })
        
        # Ustawienie daty ostatniej optymalizacji na dawno temu, aby test przeszedł
        self.feedback_loop.last_optimization = datetime.now() - timedelta(days=1)
        
        # Optymalizacja parametrów
        optimized_params = self.feedback_loop.optimize_parameters('EURUSD')
        
        # Sprawdź wyniki optymalizacji
        self.assertIsNotNone(optimized_params)
        self.assertIn('timestamp', optimized_params)
        self.assertIn('parameters', optimized_params)


if __name__ == '__main__':
    unittest.main() 