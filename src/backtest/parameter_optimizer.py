#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Moduł optymalizacji parametrów strategii.

Ten moduł implementuje klasy i funkcje do optymalizacji parametrów strategii
handlowych poprzez systematyczne przeszukiwanie przestrzeni parametrów
i ocenę wyników na podstawie metryk backtestów.
"""

import logging
import itertools
import multiprocessing
from concurrent.futures import ProcessPoolExecutor, as_completed
from typing import Dict, List, Tuple, Optional, Any, Callable
from datetime import datetime

from src.backtest.backtest_engine import BacktestEngine, BacktestConfig
from src.backtest.strategy import TradingStrategy

# Konfiguracja logowania
logger = logging.getLogger(__name__)

class ParameterOptimizer:
    """
    Klasa do optymalizacji parametrów strategii handlowych.
    Implementuje metody do systematycznego przeszukiwania przestrzeni parametrów
    i oceny wyników na podstawie różnych metryk.
    """
    
    def __init__(self, 
                 strategy_class=None, 
                 parameter_space: Dict[str, List] = None,
                 evaluation_metric: str = "sharpe_ratio",
                 workers: int = None,
                 create_strategy: Callable = None):
        """
        Inicjalizacja optymalizatora.
        
        Args:
            strategy_class: Klasa strategii do optymalizacji. Opcjonalna, jeśli create_strategy jest podane.
            parameter_space: Słownik parametrów i ich możliwych wartości do optymalizacji.
            evaluation_metric: Metryka używana do oceny strategii: "net_profit", "win_rate", "profit_factor", 
                              "sharpe_ratio", "calmar_ratio".
            workers: Liczba równoległych procesów. Jeśli None, używana jest liczba rdzeni.
            create_strategy: Opcjonalna funkcja do tworzenia strategii z danymi parametrami.
                           Używana zamiast strategy_class, jeśli podana.
        """
        self.strategy_class = strategy_class
        self.parameter_space = parameter_space or {}
        self.evaluation_metric = evaluation_metric
        self.workers = workers or multiprocessing.cpu_count()
        self.create_strategy = create_strategy
        
        self._backtest_config = None
        self._parameter_constraint = None
        
        logger.info(f"Zainicjalizowano ParameterOptimizer z metryką {evaluation_metric} i {self.workers} procesami.")
    
    def set_backtest_config(self, config: BacktestConfig) -> None:
        """
        Ustawia konfigurację backtestingu.
        
        Args:
            config: Konfiguracja backtestingu.
        """
        self._backtest_config = config
        logger.info(f"Ustawiono konfigurację backtestingu: {config.symbol}:{config.timeframe}")
    
    def set_parameter_constraint(self, constraint_function: Callable) -> None:
        """
        Ustawia funkcję ograniczenia parametrów.
        Funkcja powinna przyjmować słownik parametrów i zwracać True, jeśli parametry 
        spełniają ograniczenia, False w przeciwnym przypadku.
        
        Args:
            constraint_function: Funkcja ograniczenia parametrów.
        """
        self._parameter_constraint = constraint_function
        logger.info("Ustawiono funkcję ograniczenia parametrów.")
    
    def grid_search(self) -> List[Dict]:
        """
        Przeprowadza przeszukiwanie grid search całej przestrzeni parametrów.
        
        Returns:
            Lista słowników z parametrami i wynikami, posortowana od najlepszych do najgorszych.
        """
        if not self._backtest_config:
            raise ValueError("Konfiguracja backtestingu nie została ustawiona. Użyj set_backtest_config().")
        
        # Generowanie wszystkich kombinacji parametrów
        param_names = list(self.parameter_space.keys())
        param_values = list(self.parameter_space.values())
        
        combinations = list(itertools.product(*param_values))
        logger.info(f"Wygenerowano {len(combinations)} kombinacji parametrów do przetestowania.")
        
        # Przekształcenie kombinacji na listę słowników
        param_dicts = []
        for combo in combinations:
            param_dict = {param_names[i]: combo[i] for i in range(len(param_names))}
            
            # Sprawdzenie ograniczeń parametrów
            if self._parameter_constraint and not self._parameter_constraint(param_dict):
                continue
            
            param_dicts.append(param_dict)
        
        logger.info(f"Po zastosowaniu ograniczeń pozostało {len(param_dicts)} kombinacji.")
        
        if not param_dicts:
            logger.warning("Brak kombinacji parametrów do przetestowania po zastosowaniu ograniczeń.")
            return []
        
        # Uruchomienie optymalizacji równoległej
        results = self._run_parallel_optimization(param_dicts)
        
        if not results:
            logger.warning("Nie otrzymano żadnych wyników optymalizacji.")
            return []
        
        # Sortowanie wyników według metryki ewaluacji
        results.sort(key=lambda x: x['metrics'].get(self.evaluation_metric, 0), reverse=True)
        
        logger.info(f"Optymalizacja zakończona. Najlepsza wartość {self.evaluation_metric}: "
                   f"{results[0]['metrics'].get(self.evaluation_metric, 0) if results else 'brak wyników'}")
        
        return results
    
    def _run_parallel_optimization(self, param_dicts: List[Dict]) -> List[Dict]:
        """
        Uruchamia optymalizację równolegle na wielu procesach.
        
        Args:
            param_dicts: Lista słowników parametrów do przetestowania.
            
        Returns:
            Lista wyników z parametrami i metrykami.
        """
        results = []
        total_combinations = len(param_dicts)
        completed = 0
        
        logger.info(f"Rozpoczynam równoległą optymalizację z {self.workers} procesami.")
        
        # Ograniczamy liczbę procesów do liczby kombinacji
        workers = min(self.workers, total_combinations)
        
        # Dla przypadku jednowątkowego, wykonujemy zadania sekwencyjnie
        # To pomaga uniknąć problemów z picklowaniem funkcji lokalnych w testach
        if workers == 1:
            for params in param_dicts:
                try:
                    metrics = self._evaluate_parameters(params)
                    results.append({
                        'params': params,
                        'metrics': metrics
                    })
                    
                    completed += 1
                    if completed % 10 == 0 or completed == total_combinations:
                        logger.info(f"Postęp: {completed}/{total_combinations} kombinacji ({(completed/total_combinations)*100:.2f}%)")
                        
                        # Logowanie najlepszych wyników do tej pory
                        if results:
                            best_so_far = max(results, key=lambda x: x['metrics'].get(self.evaluation_metric, 0))
                            logger.info(f"Najlepszy dotychczasowy wynik {self.evaluation_metric}: "
                                       f"{best_so_far['metrics'].get(self.evaluation_metric, 0)}")
                
                except Exception as e:
                    logger.error(f"Błąd podczas oceny parametrów {params}: {e}")
                    import traceback
                    logger.error(traceback.format_exc())
        else:
            # Dla wielowątkowego uruchomienia używamy ProcessPoolExecutor
            with ProcessPoolExecutor(max_workers=workers) as executor:
                futures = {executor.submit(self._evaluate_parameters, params): params for params in param_dicts}
                
                for future in as_completed(futures):
                    params = futures[future]
                    try:
                        metrics = future.result()
                        results.append({
                            'params': params,
                            'metrics': metrics
                        })
                        
                        completed += 1
                        if completed % 10 == 0 or completed == total_combinations:
                            logger.info(f"Postęp: {completed}/{total_combinations} kombinacji ({(completed/total_combinations)*100:.2f}%)")
                            
                            # Logowanie najlepszych wyników do tej pory
                            if results:
                                best_so_far = max(results, key=lambda x: x['metrics'].get(self.evaluation_metric, 0))
                                logger.info(f"Najlepszy dotychczasowy wynik {self.evaluation_metric}: "
                                          f"{best_so_far['metrics'].get(self.evaluation_metric, 0)}")
                        
                    except Exception as e:
                        logger.error(f"Błąd podczas oceny parametrów {params}: {e}")
                        import traceback
                        logger.error(traceback.format_exc())
        
        return results
    
    def _evaluate_parameters(self, params: Dict) -> Dict:
        """
        Ocenia jedną kombinację parametrów poprzez uruchomienie backtestingu z podanymi parametrami.
        
        Args:
            params: Słownik parametrów do oceny.
            
        Returns:
            Metryki wyników backtestingu.
        """
        try:
            # Tworzenie strategii z danymi parametrami
            if self.create_strategy:
                strategy = self.create_strategy(params)
            else:
                strategy = self.strategy_class(**params)
            
            # Inicjalizacja silnika backtestingu
            backtest_engine = BacktestEngine(
                config=self._backtest_config,
                strategy=strategy
            )
            
            # Uruchomienie backtestingu
            result = backtest_engine.run()
            
            if result and hasattr(result, 'metrics') and result.metrics:
                return result.metrics
            else:
                logger.warning(f"Backtest dla parametrów {params} nie zwrócił ważnych metryk.")
                # Zwróć domyślne puste metryki
                return {
                    'net_profit': 0.0,
                    'win_rate': 0.0,
                    'profit_factor': 0.0,
                    'sharpe_ratio': 0.0,
                    'max_drawdown': 0.0,
                    'total_trades': 0
                }
        except Exception as e:
            logger.error(f"Wystąpił błąd podczas oceny parametrów {params}: {e}")
            import traceback
            logger.error(traceback.format_exc())
            # Zwróć domyślne puste metryki
            return {
                'net_profit': 0.0,
                'win_rate': 0.0,
                'profit_factor': 0.0,
                'sharpe_ratio': 0.0,
                'max_drawdown': 0.0,
                'total_trades': 0,
                'error': str(e)
            }
    
    def random_search(self, n_iterations: int = 100) -> List[Dict]:
        """
        Przeprowadza losowe przeszukiwanie przestrzeni parametrów.
        
        Args:
            n_iterations: Liczba losowych kombinacji do przetestowania.
            
        Returns:
            Lista słowników z parametrami i wynikami, posortowana od najlepszych do najgorszych.
        """
        # TODO: Implementacja losowego przeszukiwania przestrzeni parametrów
        # To będzie przydatne dla dużych przestrzeni parametrów, gdzie pełne grid search jest niemożliwe
        logger.warning("Metoda random_search nie jest jeszcze zaimplementowana.")
        return []
    
    def bayesian_optimization(self, n_iterations: int = 50, initial_points: int = 10) -> List[Dict]:
        """
        Przeprowadza optymalizację bayesowską przestrzeni parametrów.
        
        Args:
            n_iterations: Liczba iteracji optymalizacji bayesowskiej.
            initial_points: Liczba początkowych losowych punktów.
            
        Returns:
            Lista słowników z parametrami i wynikami, posortowana od najlepszych do najgorszych.
        """
        # TODO: Implementacja optymalizacji bayesowskiej
        # To będzie bardziej efektywne dla złożonych przestrzeni parametrów z kosztownymi obliczeniami
        logger.warning("Metoda bayesian_optimization nie jest jeszcze zaimplementowana.")
        return [] 