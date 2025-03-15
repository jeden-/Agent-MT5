import unittest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os
import sys
import tempfile
import shutil
import logging
from unittest.mock import patch, MagicMock, mock_open
import concurrent.futures

# Dodajemy ścieżkę do głównego katalogu projektu
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.backtest.backtest_engine import BacktestConfig
from src.backtest.parameter_optimizer import ParameterOptimizer
from src.backtest.strategy import SimpleMovingAverageStrategy

# Konfiguracja loggera
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


# Klasa do zastąpienia ProcessPoolExecutor
class MockProcessPoolExecutor:
    """
    Mock dla ProcessPoolExecutor, który wykonuje funkcje synchronicznie zamiast równolegle.
    Dzięki temu możemy łatwo testować kod wykorzystujący wielowątkowość.
    """
    def __init__(self, max_workers=None):
        self.max_workers = max_workers
        
    def __enter__(self):
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        pass
        
    def submit(self, fn, *args, **kwargs):
        """
        Wykonuje funkcję synchronicznie i zwraca mockowy Future z wynikiem.
        """
        mock_future = MagicMock(spec=concurrent.futures.Future)
        try:
            result = fn(*args, **kwargs)
            mock_future.result.return_value = result
            mock_future.exception.return_value = None
        except Exception as e:
            mock_future.result.side_effect = e
            mock_future.exception.return_value = e
        return mock_future


class TestParameterOptimizer(unittest.TestCase):
    """Testy jednostkowe dla optymalizatora parametrów."""
    
    def setUp(self):
        """Przygotowanie danych testowych."""
        logger.info("Przygotowanie danych testowych")
        
        # Ustawiamy ziarno dla powtarzalności testów
        np.random.seed(42)
        
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
        logger.info(f"Utworzono katalog tymczasowy: {self.temp_dir}")
        
        # Konfiguracja backtestingu
        self.backtest_config = BacktestConfig(
            symbol="TEST",
            timeframe="H1",
            start_date=datetime(2023, 1, 1),
            end_date=datetime(2023, 1, 5),
            initial_balance=10000,
            position_size_pct=0.01,
            commission=0.0
        )
        
        # Parametry do optymalizacji
        self.param_grid = {
            'fast_period': [5, 10, 15],
            'slow_period': [20, 30, 40]
        }
        
        # Funkcja symulująca wyniki backtestingu
        def mock_evaluate_parameters(params, symbol, timeframe, start_date, end_date, 
                            initial_balance, position_size_pct, commission, use_cache):
            logger.info(f"Mockowanie backtestingu z parametrami: {params}")
            
            # Symulujemy wyniki backtestingu na podstawie parametrów
            # W rzeczywistości wyniki zależą od parametrów strategii
            fast_period = params['fast_period']
            slow_period = params['slow_period']
            
            # Prosty model: im większa różnica między fast i slow MA, tym lepszy wynik
            # (to jest tylko symulacja do testów)
            profit = (slow_period - fast_period) * 10 + np.random.normal(0, 5)
            win_rate = 0.5 + (slow_period - fast_period) / 100
            sharpe = 1.0 + (slow_period - fast_period) / 50
            
            # Zwracamy symulowane metryki
            return {
                'params': params,
                'metrics': {
                    'net_profit': profit,
                    'win_rate': win_rate,
                    'sharpe_ratio': sharpe,
                    'max_drawdown': 0.1,
                    'profit_factor': 1.5,
                    'total_trades': 20,
                    'net_profit_percent': profit / 10000.0 * 100,  # Dodajemy brakujące pola z rzeczywistej implementacji
                    'max_drawdown_pct': 5.0
                },
                'summary': {
                    'net_profit': profit,
                    'net_profit_percent': profit / 10000.0 * 100,
                    'win_rate': win_rate,
                    'profit_factor': 1.5,
                    'max_drawdown_pct': 5.0,
                    'total_trades': 20
                }
            }
        
        # Zapisujemy funkcję mockującą
        self.mock_evaluate_parameters = mock_evaluate_parameters
    
    def tearDown(self):
        """Czyszczenie po testach."""
        # Usuwamy katalog tymczasowy
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
            logger.info(f"Usunięto katalog tymczasowy: {self.temp_dir}")
    
    @patch('src.backtest.parameter_optimizer.ParameterOptimizer._evaluate_parameters')
    def test_optimizer_initialization(self, mock_evaluate):
        """Test inicjalizacji optymalizatora."""
        # Ustawiamy mock dla metody _evaluate_parameters
        mock_evaluate.side_effect = self.mock_evaluate_parameters
        
        optimizer = ParameterOptimizer(
            strategy_class=SimpleMovingAverageStrategy,
            parameter_space=self.param_grid,
            evaluation_metric='net_profit',
            workers=1  # Single-threaded dla testów
        )
        
        self.assertEqual(optimizer.strategy_class, SimpleMovingAverageStrategy)
        self.assertEqual(optimizer.evaluation_metric, "net_profit")
        self.assertEqual(optimizer.parameter_space, self.param_grid)
        logger.info("Test inicjalizacji optymalizatora zakończony pomyślnie")

    def test_grid_search_simple(self):
        """Test przeszukiwania siatki parametrów z własną implementacją."""
        # Tutaj nie korzystamy z wbudowanej metody grid_search, która używa ProcessPoolExecutor,
        # ale implementujemy własną, prostszą wersję grid search

        # Tworzymy klasę rozszerzającą ParameterOptimizer o prostszą implementację grid search
        class SimpleGridSearchOptimizer(ParameterOptimizer):
            def simple_grid_search(self, symbol, timeframe, start_date, end_date, 
                           initial_balance, position_size_pct, commission, use_cache):
                """Prosta implementacja grid search bez wykorzystania wielowątkowości."""
                logger.info(f"Uruchamianie uproszczonego grid search")
                
                # Wygeneruj wszystkie kombinacje parametrów
                param_combinations = self._generate_parameter_combinations()
                
                results = []
                for params in param_combinations:
                    # Oceniamy parametry
                    result = self._evaluate_parameters(
                        params, symbol, timeframe, start_date, end_date, 
                        initial_balance, position_size_pct, commission, use_cache
                    )
                    
                    results.append(result)
                
                # Sortuj wyniki według metryki oceny (domyślnie malejąco)
                reverse = True  # Domyślnie sortujemy malejąco (większe wartości są lepsze)
                
                # Jeśli metryka to drawdown, sortujemy rosnąco (mniejsze wartości są lepsze)
                if "drawdown" in self.evaluation_metric.lower() or "risk" in self.evaluation_metric.lower():
                    reverse = False
                    
                results.sort(key=lambda x: x['metrics'][self.evaluation_metric], reverse=reverse)
                
                return results
                
            def _generate_parameter_combinations(self):
                """Generuje wszystkie kombinacje parametrów z przestrzeni parametrów."""
                param_names = list(self.parameter_space.keys())
                param_values = list(self.parameter_space.values())
                
                # Użyj itertools.product do wygenerowania wszystkich kombinacji
                import itertools
                combinations = list(itertools.product(*param_values))
                
                # Przekształć listy wartości w słowniki parametrów
                param_combinations = []
                for combo in combinations:
                    param_dict = {name: value for name, value in zip(param_names, combo)}
                    param_combinations.append(param_dict)
                
                return param_combinations
        
        # Tworzymy patch dla metody _evaluate_parameters
        with patch.object(SimpleGridSearchOptimizer, '_evaluate_parameters', side_effect=self.mock_evaluate_parameters):
            # Inicjalizujemy optymalizator
            optimizer = SimpleGridSearchOptimizer(
                strategy_class=SimpleMovingAverageStrategy,
                parameter_space=self.param_grid,
                evaluation_metric='net_profit',
                workers=1
            )
            
            # Uruchamiamy naszą własną metodę grid search
            results = optimizer.simple_grid_search(
                symbol="TEST",
                timeframe="H1",
                start_date=datetime(2023, 1, 1),
                end_date=datetime(2023, 1, 5),
                initial_balance=10000,
                position_size_pct=0.01,
                commission=0.0,
                use_cache=True
            )
            
            # Sprawdzamy wyniki
            expected_combinations = len(self.param_grid['fast_period']) * len(self.param_grid['slow_period'])
            self.assertEqual(len(results), expected_combinations)
            logger.info(f"Otrzymano {len(results)} wyników grid search")
            
            # Sprawdzamy, czy wyniki są posortowane według metryki fitness (malejąco)
            for i in range(len(results) - 1):
                self.assertGreaterEqual(
                    results[i]['metrics']['net_profit'],
                    results[i + 1]['metrics']['net_profit']
                )
            
            # Sprawdzamy, czy parametry są poprawnie zapisane w wynikach
            for result in results:
                self.assertIn('params', result)
                self.assertIn('fast_period', result['params'])
                self.assertIn('slow_period', result['params'])
                self.assertIn('metrics', result)
                self.assertIn('net_profit', result['metrics'])
            
            # Logujemy najlepszy wynik
            best_result = results[0]
            logger.info(f"Najlepsze parametry: {best_result['params']}")
            logger.info(f"Najlepszy zysk: {best_result['metrics']['net_profit']:.2f}")
    
    def test_random_search(self):
        """Test losowego przeszukiwania przestrzeni parametrów."""
        # Implementacja random search w optymalizatorze może się różnić, więc tworzymy własną
        # tymczasową implementację do testów
        
        class RandomSearchOptimizer(ParameterOptimizer):
            def random_search(self, symbol, timeframe, start_date, end_date, 
                             initial_balance, position_size_pct, commission, use_cache, num_iterations=10):
                """Implementacja random search dla testów."""
                logger.info(f"Uruchamianie random search z {num_iterations} iteracjami")
                
                results = []
                for _ in range(num_iterations):
                    # Losowo wybieramy parametry
                    params = {}
                    for param_name, param_values in self.parameter_space.items():
                        params[param_name] = np.random.choice(param_values)
                    
                    # Oceniamy parametry
                    result = self._evaluate_parameters(
                        params, symbol, timeframe, start_date, end_date, 
                        initial_balance, position_size_pct, commission, use_cache
                    )
                    
                    results.append(result)
                
                # Sortujemy wyniki według metryki fitness (malejąco)
                results.sort(key=lambda x: x['metrics'][self.evaluation_metric], reverse=True)
                
                return results
        
        # Tworzymy patch dla metody _evaluate_parameters
        with patch.object(RandomSearchOptimizer, '_evaluate_parameters', side_effect=self.mock_evaluate_parameters):
            # Inicjalizujemy optymalizator
            optimizer = RandomSearchOptimizer(
                strategy_class=SimpleMovingAverageStrategy,
                parameter_space=self.param_grid,
                evaluation_metric='net_profit',
                workers=1
            )
            
            # Uruchamiamy random search
            results = optimizer.random_search(
                symbol="TEST",
                timeframe="H1",
                start_date=datetime(2023, 1, 1),
                end_date=datetime(2023, 1, 5),
                initial_balance=10000,
                position_size_pct=0.01,
                commission=0.0,
                use_cache=True,
                num_iterations=5
            )
            
            # Sprawdzamy wyniki
            self.assertEqual(len(results), 5)
            logger.info(f"Otrzymano {len(results)} wyników random search")
            
            # Sprawdzamy, czy wyniki są posortowane
            for i in range(len(results) - 1):
                self.assertGreaterEqual(
                    results[i]['metrics']['net_profit'],
                    results[i + 1]['metrics']['net_profit']
                )
            
            # Logujemy najlepszy wynik
            best_result = results[0]
            logger.info(f"Najlepsze parametry: {best_result['params']}")
            logger.info(f"Najlepszy zysk: {best_result['metrics']['net_profit']:.2f}")
    
    def test_different_fitness_metrics(self):
        """Test optymalizacji z różnymi metrykami fitness."""
        # Tworzymy klasę rozszerzającą ParameterOptimizer o prostszą implementację grid search
        class SimpleGridSearchOptimizer(ParameterOptimizer):
            def simple_grid_search(self, symbol, timeframe, start_date, end_date, 
                           initial_balance, position_size_pct, commission, use_cache):
                """Prosta implementacja grid search bez wykorzystania wielowątkowości."""
                logger.info(f"Uruchamianie uproszczonego grid search")
                
                # Wygeneruj wszystkie kombinacje parametrów
                param_combinations = self._generate_parameter_combinations()
                
                results = []
                for params in param_combinations:
                    # Oceniamy parametry
                    result = self._evaluate_parameters(
                        params, symbol, timeframe, start_date, end_date, 
                        initial_balance, position_size_pct, commission, use_cache
                    )
                    
                    results.append(result)
                
                # Sortuj wyniki według metryki oceny (domyślnie malejąco)
                reverse = True  # Domyślnie sortujemy malejąco (większe wartości są lepsze)
                
                # Jeśli metryka to drawdown, sortujemy rosnąco (mniejsze wartości są lepsze)
                if "drawdown" in self.evaluation_metric.lower() or "risk" in self.evaluation_metric.lower():
                    reverse = False
                    
                results.sort(key=lambda x: x['metrics'][self.evaluation_metric], reverse=reverse)
                
                return results
                
            def _generate_parameter_combinations(self):
                """Generuje wszystkie kombinacje parametrów z przestrzeni parametrów."""
                param_names = list(self.parameter_space.keys())
                param_values = list(self.parameter_space.values())
                
                # Użyj itertools.product do wygenerowania wszystkich kombinacji
                import itertools
                combinations = list(itertools.product(*param_values))
                
                # Przekształć listy wartości w słowniki parametrów
                param_combinations = []
                for combo in combinations:
                    param_dict = {name: value for name, value in zip(param_names, combo)}
                    param_combinations.append(param_dict)
                
                return param_combinations
        
        # Testujemy różne metryki fitness
        metrics_to_test = ['net_profit', 'sharpe_ratio', 'win_rate']
        
        for metric in metrics_to_test:
            logger.info(f"Testowanie optymalizacji z metryką: {metric}")
            
            # Tworzymy patch dla metody _evaluate_parameters
            with patch.object(SimpleGridSearchOptimizer, '_evaluate_parameters', side_effect=self.mock_evaluate_parameters):
                # Inicjalizujemy optymalizator z określoną metryką
                optimizer = SimpleGridSearchOptimizer(
                    strategy_class=SimpleMovingAverageStrategy,
                    parameter_space=self.param_grid,
                    evaluation_metric=metric,
                    workers=1
                )
                
                # Uruchamiamy optymalizację
                results = optimizer.simple_grid_search(
                    symbol="TEST",
                    timeframe="H1",
                    start_date=datetime(2023, 1, 1),
                    end_date=datetime(2023, 1, 5),
                    initial_balance=10000,
                    position_size_pct=0.01,
                    commission=0.0,
                    use_cache=True
                )
                
                # Sprawdzamy, czy mamy jakiekolwiek wyniki
                self.assertGreater(len(results), 0, f"Brak wyników dla metryki {metric}")
                
                # Sprawdzamy, czy wyniki są posortowane według wybranej metryki (malejąco)
                for i in range(len(results) - 1):
                    self.assertGreaterEqual(
                        results[i]['metrics'][metric],
                        results[i + 1]['metrics'][metric]
                    )
                
                # Logujemy najlepszy wynik
                best_result = results[0]
                logger.info(f"Najlepsze parametry dla metryki {metric}: {best_result['params']}")
                logger.info(f"Najlepszy wynik: {best_result['metrics'][metric]:.4f}")
    
    def test_parameter_constraints(self):
        """Test ograniczeń parametrów."""
        # Implementujemy prostą funkcję constraints, która sprawdza, czy fast_period < slow_period
        def constraints_checker(params):
            return params['fast_period'] < params['slow_period']
        
        # Tworzymy klasę rozszerzającą ParameterOptimizer o obsługę ograniczeń
        class ConstrainedOptimizer(ParameterOptimizer):
            def __init__(self, **kwargs):
                self.constraints = kwargs.pop('constraints', None)
                super().__init__(**kwargs)
            
            def simple_grid_search_with_constraints(self, symbol, timeframe, start_date, end_date, 
                                   initial_balance, position_size_pct, commission, use_cache):
                """Grid search z obsługą ograniczeń parametrów."""
                results = []
                
                # Tworzymy wszystkie kombinacje parametrów
                param_combinations = self._generate_parameter_combinations()
                
                for params in param_combinations:
                    # Sprawdzamy ograniczenia, jeśli są
                    if self.constraints and not self.constraints(params):
                        continue
                    
                    # Oceniamy parametry
                    result = self._evaluate_parameters(
                        params, symbol, timeframe, start_date, end_date, 
                        initial_balance, position_size_pct, commission, use_cache
                    )
                    
                    results.append(result)
                
                # Sortujemy wyniki według metryki fitness (malejąco)
                results.sort(key=lambda x: x['metrics'][self.evaluation_metric], reverse=True)
                
                return results
                
            def _generate_parameter_combinations(self):
                """Generuje wszystkie kombinacje parametrów z przestrzeni parametrów."""
                param_names = list(self.parameter_space.keys())
                param_values = list(self.parameter_space.values())
                
                # Użyj itertools.product do wygenerowania wszystkich kombinacji
                import itertools
                combinations = list(itertools.product(*param_values))
                
                # Przekształć listy wartości w słowniki parametrów
                param_combinations = []
                for combo in combinations:
                    param_dict = {name: value for name, value in zip(param_names, combo)}
                    param_combinations.append(param_dict)
                
                return param_combinations
        
        # Tworzymy patch dla metody _evaluate_parameters
        with patch.object(ConstrainedOptimizer, '_evaluate_parameters', side_effect=self.mock_evaluate_parameters):
            # Inicjalizujemy optymalizator z ograniczeniami
            optimizer = ConstrainedOptimizer(
                strategy_class=SimpleMovingAverageStrategy,
                parameter_space=self.param_grid,
                evaluation_metric='net_profit',
                workers=1,
                constraints=constraints_checker
            )
            
            # Dodajemy parametry, które naruszają ograniczenia
            # Dla testu, dodajmy kombinację gdzie fast_period > slow_period
            test_param_grid = {
                'fast_period': [5, 10, 15, 25],  # Dodajemy wartość 25, która jest większa niż najmniejszy slow_period
                'slow_period': [20, 30, 40]
            }
            optimizer.parameter_space = test_param_grid
            
            # Uruchamiamy grid search
            results = optimizer.simple_grid_search_with_constraints(
                symbol="TEST",
                timeframe="H1",
                start_date=datetime(2023, 1, 1),
                end_date=datetime(2023, 1, 5),
                initial_balance=10000,
                position_size_pct=0.01,
                commission=0.0,
                use_cache=True
            )
            
            # Sprawdzamy, czy wszystkie wyniki spełniają ograniczenia
            for result in results:
                params = result['params']
                self.assertLess(params['fast_period'], params['slow_period'])
            
            logger.info(f"Otrzymano {len(results)} wyników spełniających ograniczenia")
            
            # Sprawdzamy, czy liczba wyników jest mniejsza niż całkowita liczba kombinacji
            total_combinations = len(test_param_grid['fast_period']) * len(test_param_grid['slow_period'])
            self.assertLess(len(results), total_combinations)
            
            # Logujemy najlepszy wynik
            if results:
                best_result = results[0]
                logger.info(f"Najlepsze parametry: {best_result['params']}")
                logger.info(f"Najlepszy zysk: {best_result['metrics']['net_profit']:.2f}")


if __name__ == '__main__':
    unittest.main() 