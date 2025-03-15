import unittest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os
import sys
import tempfile
import shutil
from unittest.mock import Mock, patch, MagicMock

# Dodajemy ścieżkę do głównego katalogu projektu
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.backtest.backtest_engine import BacktestEngine, BacktestConfig
from src.backtest.strategy import (
    SimpleMovingAverageStrategy, 
    RSIStrategy, 
    BollingerBandsStrategy,
    MACDStrategy, 
    TradingStrategy
)
from src.backtest.backtest_metrics import calculate_metrics
from src.backtest.position_manager import PositionManager
from src.backtest.historical_data_manager import HistoricalDataManager


class TestBacktestEngine(unittest.TestCase):
    """Testy jednostkowe dla silnika backtestingu."""
    
    def setUp(self):
        """Przygotowanie danych testowych."""
        # Tworzymy testowy dataframe z danymi historycznymi
        dates = pd.date_range(start='2023-01-01', periods=100, freq='H')
        self.test_data = pd.DataFrame({
            'time': dates,
            'open': np.sin(np.linspace(0, 10, 100)) * 5 + 100,
            'high': np.sin(np.linspace(0, 10, 100)) * 5 + 102,
            'low': np.sin(np.linspace(0, 10, 100)) * 5 + 98,
            'close': np.sin(np.linspace(0, 10, 100)) * 5 + 101,
            'volume': np.random.randint(100, 1000, 100)
        })
        
        # Przygotowujemy katalog tymczasowy na dane cache
        self.temp_dir = tempfile.mkdtemp()
        
        # Konfiguracja testu
        self.config = BacktestConfig(
            symbol="TEST",
            timeframe="H1",
            start_date=datetime(2023, 1, 1),
            end_date=datetime(2023, 1, 5),
            initial_balance=10000,
            position_size_pct=0.01,
            commission=0.0
        )
        
        # Przygotowanie zamockowanego data managera
        self.mock_data_manager = Mock(spec=HistoricalDataManager)
        self.mock_data_manager.get_historical_data.return_value = self.test_data
        
        # Prosta strategia testowa
        self.strategy = SimpleMovingAverageStrategy(fast_period=5, slow_period=20)
    
    def tearDown(self):
        """Czyszczenie po testach."""
        # Usuwamy katalog tymczasowy
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_backtest_engine_initialization(self):
        """Test inicjalizacji silnika backtestingu."""
        engine = BacktestEngine(self.config, strategy=self.strategy, data_manager=self.mock_data_manager)
        self.assertEqual(engine.config.symbol, "TEST")
        self.assertEqual(engine.config.timeframe, "H1")
        self.assertEqual(engine.config.initial_balance, 10000)
        self.assertIsNotNone(engine.strategy)
        self.assertEqual(engine.data_manager, self.mock_data_manager)
    
    def test_backtest_run_with_mock_data(self):
        """Test uruchomienia backtestingu z mockowanymi danymi."""
        # Tworzymy silnik backtestingu z zamockowanym data_manager
        engine = BacktestEngine(self.config, strategy=self.strategy, data_manager=self.mock_data_manager)
        
        # Uruchamiamy backtest
        result = engine.run()
        
        # Sprawdzamy, czy wynik zawiera oczekiwane pola
        self.assertIsNotNone(result)
        self.assertIsNotNone(result.trades)
        self.assertIsNotNone(result.equity_curve)
        self.assertIsNotNone(result.drawdowns)
        
        # Weryfikujemy, czy krzywa equity ma właściwą długość
        self.assertGreaterEqual(len(result.equity_curve), 1)
        
        # Sprawdzamy, czy początkowa wartość equity to initial_balance
        self.assertEqual(result.equity_curve[0], self.config.initial_balance)
        
        # Sprawdzamy, czy metoda get_historical_data została wywołana z odpowiednimi parametrami
        self.mock_data_manager.get_historical_data.assert_called_once_with(
            symbol=self.config.symbol,
            timeframe=self.config.timeframe,
            start_date=self.config.start_date,
            end_date=self.config.end_date,
            use_cache=self.config.use_cache,
            update_cache=self.config.update_cache,
            use_synthetic=self.config.use_synthetic_data
        )
    
    def test_backtest_metrics_calculation(self):
        """Test obliczania metryk backtestingu."""
        # Używamy silnika backtestingu z zamockowanym data_manager
        engine = BacktestEngine(self.config, strategy=self.strategy, data_manager=self.mock_data_manager)
        
        # Uruchamiamy backtest
        result = engine.run()
        
        # Obliczamy metryki
        metrics = calculate_metrics(result)
        
        # Sprawdzamy, czy metryki zawierają oczekiwane pola
        self.assertIn('net_profit', metrics)
        self.assertIn('total_trades', metrics)
        self.assertIn('win_rate', metrics)
        self.assertIn('profit_factor', metrics)
        self.assertIn('sharpe_ratio', metrics)
        self.assertIn('max_drawdown', metrics)
        
        # Sprawdzamy, czy wartości są typami liczbowymi
        self.assertIsInstance(metrics['net_profit'], (int, float))
        self.assertIsInstance(metrics['win_rate'], (int, float))
        self.assertIsInstance(metrics['sharpe_ratio'], (int, float))
    
    def test_backtest_with_fees(self):
        """Test, czy opłaty są prawidłowo uwzględniane."""
        # Konfiguracja z opłatami
        config_with_fees = BacktestConfig(
            symbol="TEST",
            timeframe="H1",
            start_date=datetime(2023, 1, 1),
            end_date=datetime(2023, 1, 5),
            initial_balance=10000,
            position_size_pct=0.01,
            commission=0.001  # 0.1% prowizji
        )
        
        # Konfiguracja bez opłat
        config_no_fees = BacktestConfig(
            symbol="TEST",
            timeframe="H1",
            start_date=datetime(2023, 1, 1),
            end_date=datetime(2023, 1, 5),
            initial_balance=10000,
            position_size_pct=0.01,
            commission=0.0
        )
        
        # Tworzymy silniki backtestingu
        engine_with_fees = BacktestEngine(config_with_fees, strategy=self.strategy, data_manager=self.mock_data_manager)
        engine_no_fees = BacktestEngine(config_no_fees, strategy=self.strategy, data_manager=self.mock_data_manager)
        
        # Uruchamiamy backtesty
        result_with_fees = engine_with_fees.run()
        result_no_fees = engine_no_fees.run()
        
        # Obliczamy metryki
        metrics_with_fees = calculate_metrics(result_with_fees)
        metrics_no_fees = calculate_metrics(result_no_fees)
        
        # Weryfikujemy, czy zysk z opłatami jest mniejszy niż bez opłat
        # (zakładając, że są jakiekolwiek transakcje)
        if metrics_with_fees['total_trades'] > 0 and metrics_no_fees['total_trades'] > 0:
            self.assertLessEqual(metrics_with_fees['net_profit'], metrics_no_fees['net_profit'])
    
    def test_risk_management(self):
        """Test, czy zarządzanie ryzykiem działa prawidłowo."""
        # Konfiguracja z różnymi poziomami ryzyka
        config_high_risk = BacktestConfig(
            symbol="TEST",
            timeframe="H1",
            start_date=datetime(2023, 1, 1),
            end_date=datetime(2023, 1, 5),
            initial_balance=10000,
            position_size_pct=0.05,  # 5% ryzyka na transakcję
            commission=0.0
        )
        
        config_low_risk = BacktestConfig(
            symbol="TEST",
            timeframe="H1",
            start_date=datetime(2023, 1, 1),
            end_date=datetime(2023, 1, 5),
            initial_balance=10000,
            position_size_pct=0.01,  # 1% ryzyka na transakcję
            commission=0.0
        )
        
        # Tworzymy silniki backtestingu
        engine_high_risk = BacktestEngine(config_high_risk, strategy=self.strategy, data_manager=self.mock_data_manager)
        engine_low_risk = BacktestEngine(config_low_risk, strategy=self.strategy, data_manager=self.mock_data_manager)
        
        # Uruchamiamy backtesty
        result_high_risk = engine_high_risk.run()
        result_low_risk = engine_low_risk.run()
        
        # Jeśli są jakiekolwiek transakcje, sprawdzamy, czy wielkość pozycji jest proporcjonalna do ryzyka
        if len(result_high_risk.trades) > 0 and len(result_low_risk.trades) > 0:
            # Bierzemy pierwsze transakcje z obu wyników
            trade_high_risk = result_high_risk.trades[0]
            trade_low_risk = result_low_risk.trades[0]
            
            # Sprawdzamy, czy wielkość pozycji jest proporcjonalna do poziomu ryzyka (z marginesem błędu)
            expected_ratio = config_high_risk.position_size_pct / config_low_risk.position_size_pct
            actual_ratio = trade_high_risk.volume / trade_low_risk.volume
            
            # Sprawdzamy z 10% marginesem błędu
            self.assertAlmostEqual(actual_ratio, expected_ratio, delta=expected_ratio * 0.1)
    
    def test_different_strategies(self):
        """Test uruchamiania backtestingu z różnymi strategiami."""
        # Tworzenie różnych strategii
        sma_strategy = SimpleMovingAverageStrategy(fast_period=5, slow_period=20)
        rsi_strategy = RSIStrategy(period=14, overbought=70, oversold=30)
        bb_strategy = BollingerBandsStrategy(period=20, std_dev=2.0)
        macd_strategy = MACDStrategy(fast_period=12, slow_period=26, signal_period=9)
        
        # Tworzenie silnika backtestingu
        engine = BacktestEngine(self.config, strategy=None, data_manager=self.mock_data_manager)
        
        # Testowanie każdej strategii
        for strategy in [sma_strategy, rsi_strategy, bb_strategy, macd_strategy]:
            engine.strategy = strategy
            result = engine.run()
            
            # Sprawdzenie podstawowych wyników
            self.assertIsNotNone(result)
            self.assertIsNotNone(result.trades)
            self.assertIsNotNone(result.equity_curve)
    
    def test_empty_data_handling(self):
        """Test obsługi pustych danych."""
        # Tworzymy pusty DataFrame
        empty_data = pd.DataFrame(columns=['time', 'open', 'high', 'low', 'close', 'volume'])
        
        # Tworzymy mocka managera danych, który zwraca pustą ramkę danych
        mock_empty_data_manager = Mock(spec=HistoricalDataManager)
        mock_empty_data_manager.get_historical_data.return_value = empty_data
        
        # Tworzymy silnik backtestingu
        engine = BacktestEngine(self.config, strategy=self.strategy, data_manager=mock_empty_data_manager)
        
        # Uruchamiamy backtest
        result = engine.run()
        
        # Sprawdzamy czy wynik jest poprawny mimo pustych danych
        self.assertIsNotNone(result)
        self.assertEqual(len(result.trades), 0)
        self.assertEqual(len(result.equity_curve), 1)  # Powinna być tylko początkowa wartość
        self.assertEqual(result.equity_curve[0], self.config.initial_balance)
    
    def test_invalid_data_handling(self):
        """Test obsługi nieprawidłowych danych."""
        # Dane z brakującymi kolumnami
        invalid_data = pd.DataFrame({
            'time': pd.date_range(start='2023-01-01', periods=100, freq='H'),
            'close': np.sin(np.linspace(0, 10, 100)) * 5 + 101,
            # Brakuje 'open', 'high', 'low', 'volume'
        })
        
        # Tworzymy silnik backtestingu
        engine = BacktestEngine(self.config, strategy=self.strategy)
        engine._load_historical_data = lambda: invalid_data
        
        # Uruchamiamy backtest - powinien obsłużyć nieprawidłowe dane bez wyrzucania wyjątku
        try:
            result = engine.run()
            # Jeśli doszliśmy tutaj, to znaczy że nie było wyjątku
            self.assertTrue(True)
        except Exception as e:
            self.fail(f"BacktestEngine.run() rzucił wyjątek z nieprawidłowymi danymi: {e}")
    
    def test_custom_strategy(self):
        """Test z niestandardową strategią."""
        # Tworzymy mockową strategię
        mock_strategy = Mock(spec=TradingStrategy)
        mock_strategy.generate_signals.return_value = []  # Brak sygnałów
        
        # Tworzymy silnik backtestingu
        engine = BacktestEngine(self.config, strategy=mock_strategy)
        engine._load_historical_data = lambda: self.test_data
        
        # Uruchamiamy backtest
        result = engine.run()
        
        # Sprawdzamy czy strategia została wywołana
        # Metoda generate_signals jest wywoływana dla każdej świecy, jeśli i > 50
        # Więc sprawdzamy tylko, czy została wywołana co najmniej raz
        self.assertTrue(mock_strategy.generate_signals.called)
        
        # Sprawdzamy podstawowe wyniki
        self.assertIsNotNone(result)
        self.assertEqual(len(result.trades), 0)  # Brak sygnałów = brak transakcji
    
    def test_position_manager_integration(self):
        """Test integracji z PositionManager."""
        # Tworzymy silnik backtestingu
        engine = BacktestEngine(self.config, strategy=self.strategy)
        engine._load_historical_data = lambda: self.test_data
        
        # Tworzymy własny PositionManager z mockowanymi metodami
        mock_position_manager = Mock(spec=PositionManager)
        mock_position_manager.open_position.return_value = True
        mock_position_manager.update_positions.return_value = []
        mock_position_manager.get_active_positions.return_value = []
        mock_position_manager.get_closed_positions.return_value = []
        
        # Podmieniamy position_manager w silniku
        engine.position_manager = mock_position_manager
        
        # Uruchamiamy backtest
        result = engine.run()
        
        # Sprawdzamy, czy metody PositionManager zostały wywołane
        self.assertTrue(mock_position_manager.update_positions.called)
        self.assertTrue(mock_position_manager.get_closed_positions.called)
    
    def test_different_timeframes(self):
        """Test obsługi różnych timeframe'ów."""
        # Tworzymy dane dla różnych timeframe'ów
        timeframes = {
            'M1': pd.date_range(start='2023-01-01', periods=100, freq='T'),
            'H1': pd.date_range(start='2023-01-01', periods=100, freq='H'),
            'D1': pd.date_range(start='2023-01-01', periods=100, freq='D')
        }
        
        for tf, dates in timeframes.items():
            # Tworzymy dane
            data = pd.DataFrame({
                'time': dates,
                'open': np.sin(np.linspace(0, 10, 100)) * 5 + 100,
                'high': np.sin(np.linspace(0, 10, 100)) * 5 + 102,
                'low': np.sin(np.linspace(0, 10, 100)) * 5 + 98,
                'close': np.sin(np.linspace(0, 10, 100)) * 5 + 101,
                'volume': np.random.randint(100, 1000, 100)
            })
            
            # Tworzymy mocka managera danych dla konkretnego timeframe'u
            mock_tf_data_manager = Mock(spec=HistoricalDataManager)
            mock_tf_data_manager.get_historical_data.return_value = data
            
            # Konfiguracja z odpowiednim timeframe'em
            config = BacktestConfig(
                symbol="TEST",
                timeframe=tf,
                start_date=dates[0],
                end_date=dates[-1],
                initial_balance=10000,
                position_size_pct=0.01,
                commission=0.0
            )
            
            # Tworzymy silnik backtestingu
            engine = BacktestEngine(config, strategy=self.strategy, data_manager=mock_tf_data_manager)
            
            # Uruchamiamy backtest
            result = engine.run()
            
            # Sprawdzamy, czy wynik zawiera oczekiwane pola
            self.assertIsNotNone(result)
            self.assertIsNotNone(result.trades)
            self.assertIsNotNone(result.equity_curve)
            
            # Sprawdzamy, czy timeframe został prawidłowo uwzględniony
            mock_tf_data_manager.get_historical_data.assert_called_once_with(
                symbol=config.symbol,
                timeframe=tf,
                start_date=config.start_date,
                end_date=config.end_date,
                use_cache=config.use_cache,
                update_cache=config.update_cache,
                use_synthetic=config.use_synthetic_data
            )
    
    def test_date_range_filtering(self):
        """Test filtrowania danych według zakresu dat."""
        # Tworzymy dane z szerokim zakresem dat
        dates = pd.date_range(start='2023-01-01', periods=100, freq='D')
        data = pd.DataFrame({
            'time': dates,
            'open': np.sin(np.linspace(0, 10, 100)) * 5 + 100,
            'high': np.sin(np.linspace(0, 10, 100)) * 5 + 102,
            'low': np.sin(np.linspace(0, 10, 100)) * 5 + 98,
            'close': np.sin(np.linspace(0, 10, 100)) * 5 + 101,
            'volume': np.random.randint(100, 1000, 100)
        })
        
        # Przygotowanie mocka data_managera z pełnym zakresem danych
        mock_date_range_data_manager = Mock(spec=HistoricalDataManager)
        mock_date_range_data_manager.get_historical_data.return_value = data
        
        # Konfiguracja z węższym zakresem dat
        narrow_range_config = BacktestConfig(
            symbol="TEST",
            timeframe="D1",
            start_date=datetime(2023, 1, 10),  # 10 dni po początku danych
            end_date=datetime(2023, 1, 20),    # 20 dni po początku danych
            initial_balance=10000,
            position_size_pct=0.01,
            commission=0.0
        )
        
        # Tworzymy silnik backtestingu
        engine = BacktestEngine(narrow_range_config, strategy=self.strategy, data_manager=mock_date_range_data_manager)
        
        # Uruchamiamy backtest
        result = engine.run()
        
        # Sprawdzamy, czy dane zostały odfiltrowane zgodnie z zakresem dat
        # Możemy to zrobić sprawdzając jaki jest ostatni timestamp w wyniku
        if len(result.timestamps) > 1:  # Musi być więcej niż tylko początkowy timestamp
            last_timestamp = result.timestamps[-1]
            # Sprawdzamy, czy ostatni timestamp jest nie późniejszy niż end_date
            self.assertLessEqual(last_timestamp, narrow_range_config.end_date)
            # Sprawdzamy, czy pierwszy timestamp po początkowym (który jest zawsze start_date) 
            # jest nie wcześniejszy niż start_date
            if len(result.timestamps) > 2:
                second_timestamp = result.timestamps[1]
                self.assertGreaterEqual(second_timestamp, narrow_range_config.start_date)
        
        # Sprawdzamy, czy metoda get_historical_data została wywołana z prawidłowymi parametrami
        mock_date_range_data_manager.get_historical_data.assert_called_once_with(
            symbol=narrow_range_config.symbol,
            timeframe=narrow_range_config.timeframe,
            start_date=narrow_range_config.start_date,
            end_date=narrow_range_config.end_date,
            use_cache=narrow_range_config.use_cache,
            update_cache=narrow_range_config.update_cache,
            use_synthetic=narrow_range_config.use_synthetic_data
        )


if __name__ == '__main__':
    unittest.main() 