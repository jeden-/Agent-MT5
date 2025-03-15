#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Silnik backtestingu do testowania strategii handlowych na danych historycznych.
"""

import logging
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any, Tuple, Union, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import time
import json
import os
import matplotlib.pyplot as plt
from pathlib import Path
import uuid

from src.database.models import TradingSignal, SignalEvaluation
from src.analysis.signal_generator import SignalGenerator
from src.analysis.signal_evaluator import SignalEvaluator
from src.config.config_manager import ConfigManager
from src.mt5_bridge.mt5_connector import get_mt5_connector
from src.backtest.historical_data_manager import HistoricalDataManager
from src.backtest.strategy import TradingStrategy, StrategyConfig, StrategySignal
from src.backtest.position_manager import PositionManager, BacktestPosition
from src.models.signal import SignalType

logger = logging.getLogger(__name__)


@dataclass
class BacktestConfig:
    """
    Konfiguracja procesu backtestingu.
    """
    symbol: str
    timeframe: str
    start_date: datetime
    end_date: datetime
    initial_balance: float = 10000.0
    position_size_pct: float = 1.0  # Procent salda na pojedynczą pozycję
    commission: float = 0.0  # Prowizja w punktach
    slippage: float = 0.0  # Poślizg w punktach
    use_spread: bool = True  # Czy uwzględniać spread w obliczeniach
    min_volume: float = 0.01  # Minimalny wolumen pozycji
    max_volume: float = 10.0  # Maksymalny wolumen pozycji
    strategy_name: str = "default"  # Nazwa strategii
    test_id: str = field(default_factory=lambda: datetime.now().strftime("%Y%m%d_%H%M%S"))
    output_dir: str = "backtest_results"
    use_cache: bool = True  # Czy używać cache dla danych historycznych
    update_cache: bool = True  # Czy aktualizować cache podczas backtestingu
    use_synthetic_data: bool = False  # Czy używać danych syntetycznych, gdy rzeczywiste dane są niedostępne
    strategy_params: Dict[str, Any] = field(default_factory=dict)  # Parametry strategii
    
    # Parametry zarządzania pozycjami
    use_trailing_stop: bool = False  # Czy używać trailing stop
    trailing_stop_pips: float = 20.0  # Ilość pipsów do trailing stopu
    use_breakeven: bool = False  # Czy używać breakeven
    breakeven_trigger_pips: float = 20.0  # Liczba pipsów zysku do aktywacji breakeven
    breakeven_plus_pips: float = 5.0  # Liczba pipsów powyżej entry po breakeven
    use_partial_close: bool = False  # Czy używać częściowego zamykania
    partial_close_levels: List[Tuple[float, float]] = field(default_factory=list)  # Lista tupli (poziom_pipsów, procent_do_zamknięcia)


@dataclass
class BacktestTrade:
    """
    Reprezentacja pojedynczej transakcji w backteście.
    """
    signal_id: str
    symbol: str
    direction: str
    entry_price: float
    stop_loss: float
    take_profit: float
    entry_time: datetime
    volume: float
    exit_price: Optional[float] = None
    exit_time: Optional[datetime] = None
    profit: float = 0.0
    pips: float = 0.0
    status: str = "open"  # open, closed
    hit_target: Optional[bool] = None
    hit_stop: Optional[bool] = None
    reason: str = ""
    confidence: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BacktestResult:
    """
    Wyniki backtestingu.
    """
    config: BacktestConfig
    trades: List[BacktestTrade] = field(default_factory=list)
    equity_curve: List[float] = field(default_factory=list)
    timestamps: List[datetime] = field(default_factory=list)
    balance: float = 0.0
    metrics: Dict[str, Any] = field(default_factory=dict)
    signals: List[Dict[str, Any]] = field(default_factory=list)
    
    # Dodatkowe dane dla analizy
    market_data: Optional[pd.DataFrame] = None
    drawdowns: List[float] = field(default_factory=list)
    
    def save(self, filename: Optional[str] = None) -> str:
        """
        Zapisuje wyniki backtestingu do pliku JSON.
        
        Args:
            filename: Opcjonalna nazwa pliku. Jeśli nie podano, zostanie wygenerowana.
            
        Returns:
            str: Ścieżka do zapisanego pliku
        """
        if filename is None:
            # Utwórz katalog jeśli nie istnieje
            Path(self.config.output_dir).mkdir(parents=True, exist_ok=True)
            filename = f"{self.config.output_dir}/{self.config.symbol}_{self.config.timeframe}_{self.config.test_id}.json"
        
        # Konwersja obiektów do JSON-friendly formatu
        result_dict = {
            "config": {
                "symbol": self.config.symbol,
                "timeframe": self.config.timeframe,
                "start_date": self.config.start_date.isoformat(),
                "end_date": self.config.end_date.isoformat(),
                "initial_balance": self.config.initial_balance,
                "position_size_pct": self.config.position_size_pct,
                "commission": self.config.commission,
                "slippage": self.config.slippage,
                "use_spread": self.config.use_spread,
                "min_volume": self.config.min_volume,
                "max_volume": self.config.max_volume,
                "strategy_name": self.config.strategy_name,
                "test_id": self.config.test_id,
                "output_dir": self.config.output_dir,
                "strategy_params": self.config.strategy_params
            },
            "trades": [
                {
                    "signal_id": t.signal_id,
                    "symbol": t.symbol,
                    "direction": t.direction,
                    "entry_price": t.entry_price,
                    "stop_loss": t.stop_loss,
                    "take_profit": t.take_profit,
                    "entry_time": t.entry_time.isoformat(),
                    "volume": t.volume,
                    "exit_price": t.exit_price,
                    "exit_time": t.exit_time.isoformat() if t.exit_time else None,
                    "profit": t.profit,
                    "pips": t.pips,
                    "status": t.status,
                    "hit_target": t.hit_target,
                    "hit_stop": t.hit_stop,
                    "reason": t.reason,
                    "confidence": t.confidence
                } for t in self.trades
            ],
            "equity_curve": self.equity_curve,
            "timestamps": [ts.isoformat() for ts in self.timestamps],
            "balance": self.balance,
            "metrics": self.metrics,
            "signals": self.signals,
            "drawdowns": self.drawdowns
        }
        
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(result_dict, f, indent=2)
            
        logger.info(f"Wyniki backtestingu zapisane do: {filename}")
        return filename


class BacktestEngine:
    """
    Silnik backtestingu do przeprowadzania testów strategii handlowych na danych historycznych.
    """
    
    def __init__(self, config: BacktestConfig, strategy: TradingStrategy = None, data_manager: Optional[HistoricalDataManager] = None):
        """
        Inicjalizuje silnik backtestingu.
        
        Args:
            config: Konfiguracja backtestingu
            strategy: Strategia tradingowa do testowania
            data_manager: Opcjonalny manager danych historycznych (do testów)
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.mt5_connector = get_mt5_connector()
        
        # Inicjalizacja managera danych historycznych
        self.data_manager = data_manager if data_manager is not None else HistoricalDataManager(mt5_connector=self.mt5_connector)
        
        # Inicjalizacja managera pozycji
        self.position_manager = PositionManager()
        
        # Inicjalizacja strategii
        self.strategy = strategy
        
        # Inicjalizacja zmiennych backtestingu
        self.trades: List[BacktestTrade] = []
        self.signals: List[Dict[str, Any]] = []
        self.balance = config.initial_balance
        self.equity_curve = [config.initial_balance]
        self.timestamps = [config.start_date]
        self.drawdowns = [0.0]
        self.max_equity = config.initial_balance
        self.market_data = None
        
        # Słowniki pomocnicze do obliczania zysków/strat
        self.pip_values = {}  # symbol -> wartość pipa
        self.position_values = {}  # symbol -> wartość pozycji na 1 lot
        
        # Zmienne do śledzenia postępu backtestingu
        self.total_bars = 0
        self.processed_bars = 0
        self.progress_callback = None

    def set_progress_callback(self, callback: Callable[[float], None]):
        """
        Ustawia funkcję callback do raportowania postępu.
        
        Args:
            callback: Funkcja przyjmująca wartość postępu (0.0-1.0)
        """
        self.progress_callback = callback
        
    def get_progress(self) -> float:
        """
        Zwraca aktualny postęp backtestingu jako wartość od 0.0 do 1.0.
        
        Returns:
            float: Postęp backtestingu (0.0-1.0)
        """
        if self.total_bars == 0:
            return 0.0
        return min(1.0, self.processed_bars / self.total_bars)
        
    def run(self) -> BacktestResult:
        """
        Uruchamia proces backtestingu.
        
        Returns:
            BacktestResult: Wyniki backtestingu
        """
        try:
            self.logger.info(f"Rozpoczynam backtest dla {self.config.symbol} na timeframe {self.config.timeframe}")
            self.logger.info(f"Okres: {self.config.start_date} - {self.config.end_date}")
            self.logger.info(f"Strategia: {self.config.strategy_name}")
            
            # Sprawdź czy strategia została ustawiona
            if self.strategy is None:
                self.logger.error("Nie ustawiono strategii tradingowej.")
                return self._create_empty_result()
            
            # Pobierz dane historyczne
            self.market_data = self._load_historical_data()
            if self.market_data is None or len(self.market_data) == 0:
                self.logger.error("Nie można pobrać danych historycznych.")
                return self._create_empty_result()
            
            self.logger.info(f"Pobrano {len(self.market_data)} barek danych historycznych")
            
            # Dodaj kolumny symbol i timeframe do danych, jeśli nie istnieją
            if 'symbol' not in self.market_data.columns:
                self.market_data['symbol'] = self.config.symbol
            if 'timeframe' not in self.market_data.columns:
                self.market_data['timeframe'] = self.config.timeframe
            
            # Ustaw całkowitą liczbę barek do przetworzenia
            self.total_bars = len(self.market_data)
            self.processed_bars = 0
            
            # Główna pętla backtestingu
            for i in range(1, len(self.market_data)):
                current_bar = self.market_data.iloc[i]
                
                # Aktualizuj czas
                current_time = current_bar['time']
                
                # Aktualizuj status otwartych pozycji
                self._update_trades(current_bar, current_time)
                
                # Generuj nowe sygnały
                if i > 50:  # Potrzebujemy pewnej historii do generowania sygnałów
                    historical_data = self.market_data.iloc[max(0, i-200):i].copy()
                    signals = self._generate_signals(historical_data, current_time)
                    
                    for signal in signals:
                        self.signals.append(self._convert_strategy_signal_to_dict(signal))
                        trade = self._open_trade(signal, current_bar, current_time)
                        if trade:
                            self.trades.append(trade)
                
                # Aktualizuj krzywą equity
                current_equity = self.balance + self._calculate_floating_profit(current_bar)
                self.equity_curve.append(current_equity)
                self.timestamps.append(current_time)
                
                # Aktualizuj maksymalną wartość equity i drawdown
                if current_equity > self.max_equity:
                    self.max_equity = current_equity
                
                # Oblicz drawdown
                current_drawdown = (self.max_equity - current_equity) / self.max_equity if self.max_equity > 0 else 0
                self.drawdowns.append(current_drawdown)
                
                # Aktualizuj postęp i wywołaj callback jeśli jest ustawiony
                self.processed_bars = i
                if self.progress_callback:
                    self.progress_callback(self.get_progress())
            
            # Zamknij wszystkie otwarte pozycje na koniec testu
            last_bar = self.market_data.iloc[-1]
            current_time = last_bar['time']
            
            # Słownik bieżących cen dla każdego symbolu
            current_prices = {self.config.symbol: last_bar['close']}
            
            # Lista otwartych pozycji do zamknięcia
            positions_to_close = []
            for position in self.position_manager.get_active_positions():
                positions_to_close.append((position.position_id, current_prices.get(position.symbol, last_bar['close']), current_time, "end_of_test"))
            
            # Zamknięcie wszystkich otwartych pozycji
            for position_id, close_price, close_time, close_reason in positions_to_close:
                closed_position = self.position_manager.close_position(position_id, close_price, close_time, close_reason)
                
                if closed_position:
                    # Zaktualizuj odpowiadający BacktestTrade
                    for trade in self.trades:
                        if trade.status == "open" and trade.metadata.get("position_id") == position_id:
                            # Aktualizuj obiekt BacktestTrade
                            trade.exit_price = closed_position["close_price"]
                            trade.exit_time = closed_position["close_time"]
                            trade.status = "closed"
                            trade.reason = closed_position["close_reason"]
                            
                            # Oblicz zysk/stratę
                            profit_pips = closed_position["profit_pips"]
                            
                            # Zamień pipsy na kwotę pieniężną
                            symbol = trade.symbol
                            pip_value = self.pip_values.get(symbol, 0.1)
                            trade.profit = profit_pips * pip_value * trade.volume
                            trade.pips = profit_pips
                            
                            # Aktualizuj saldo
                            self.balance += trade.profit
                            
                            self.logger.info(f"Zamknięto pozycję na koniec testu: {trade.direction} {trade.symbol} @ {trade.exit_price}, zysk/strata: {trade.profit:.2f}")
                            
                            break
            
            # Przygotuj wyniki
            result = BacktestResult(
                config=self.config,
                trades=self.trades,
                equity_curve=self.equity_curve,
                timestamps=self.timestamps,
                balance=self.balance,
                signals=self.signals,
                drawdowns=self.drawdowns,
                market_data=self.market_data
            )
            
            # Pobierz zamknięte pozycje
            closed_positions = self.position_manager.get_closed_positions()
            
            # Oblicz metryki
            from .backtest_metrics import calculate_metrics
            result.metrics = calculate_metrics(result)
            
            self.logger.info(f"Backtest zakończony. Liczba transakcji: {len(self.trades)}")
            self.logger.info(f"Końcowe saldo: {self.balance:.2f}")
            self.logger.info(f"Zysk/strata: {self.balance - self.config.initial_balance:.2f}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Błąd podczas backtestingu: {e}")
            import traceback
            self.logger.error(traceback.format_exc())
            return self._create_empty_result()
    
    def _load_historical_data(self) -> Optional[pd.DataFrame]:
        """
        Ładuje dane historyczne dla wybranego symbolu i timeframe'u.
        
        Returns:
            Optional[pd.DataFrame]: DataFrame z danymi historycznymi lub None w przypadku błędu
        """
        try:
            # Pobieranie danych z managera danych historycznych
            df = self.data_manager.get_historical_data(
                symbol=self.config.symbol,
                timeframe=self.config.timeframe,
                start_date=self.config.start_date,
                end_date=self.config.end_date,
                use_cache=self.config.use_cache,
                update_cache=self.config.update_cache,
                use_synthetic=self.config.use_synthetic_data
            )
            
            if df is None or len(df) == 0:
                self.logger.error(f"Nie można pobrać danych historycznych dla {self.config.symbol} na timeframe {self.config.timeframe}")
                return None
            
            # Dodaj kolumnę 'spread' jeśli nie istnieje
            if 'spread' not in df.columns:
                df['spread'] = 10  # Domyślny spread w punktach
            
            # Filtruj dane według zakresu dat
            if 'time' in df.columns:
                df = df[(df['time'] >= pd.Timestamp(self.config.start_date)) & 
                        (df['time'] <= pd.Timestamp(self.config.end_date))]
            
            return df
            
        except Exception as e:
            self.logger.error(f"Błąd podczas ładowania danych historycznych: {e}")
            return None
    
    def _generate_signals(self, historical_data: pd.DataFrame, current_time: datetime) -> List[StrategySignal]:
        """
        Generuje sygnały handlowe na podstawie danych historycznych i wybranej strategii.
        
        Args:
            historical_data: Dane historyczne
            current_time: Aktualny czas
            
        Returns:
            List[StrategySignal]: Lista sygnałów handlowych
        """
        try:
            # Generowanie sygnałów za pomocą strategii
            signals = self.strategy.generate_signals(historical_data)
            
            # Filtrowanie sygnałów - bierzemy tylko te z aktualnego czasu
            current_signals = [s for s in signals if s.time == current_time]
            
            return current_signals
            
        except Exception as e:
            self.logger.error(f"Błąd podczas generowania sygnałów: {e}")
            return []
    
    def _convert_strategy_signal_to_dict(self, signal: StrategySignal) -> Dict[str, Any]:
        """
        Konwertuje obiekt StrategySignal na słownik.
        
        Args:
            signal: Sygnał strategii
            
        Returns:
            Dict[str, Any]: Słownik reprezentujący sygnał
        """
        signal_dict = {
            "id": f"backtest_{signal.time.strftime('%Y%m%d%H%M%S')}_{signal.symbol}",
            "symbol": signal.symbol,
            "timeframe": signal.timeframe,
            "direction": "BUY" if signal.signal_type.name == "BUY" else "SELL",
            "entry_price": signal.entry_price,
            "stop_loss": signal.stop_loss,
            "take_profit": signal.take_profit,
            "confidence": 0.7,  # Domyślna wartość
            "created_at": signal.time,
            "volume": signal.volume,
            "comment": signal.comment,
            "risk_reward_ratio": signal.risk_reward_ratio,
            "metadata": {}
        }
        
        return signal_dict
    
    def _open_trade(self, signal: StrategySignal, current_bar: pd.Series, current_time: datetime) -> Optional[BacktestTrade]:
        """
        Otwiera nową transakcję na podstawie sygnału.
        
        Args:
            signal: Sygnał handlowy
            current_bar: Aktualna barka
            current_time: Aktualny czas
            
        Returns:
            Optional[BacktestTrade]: Nowa transakcja lub None w przypadku błędu
        """
        try:
            # Obliczanie ceny wejścia z uwzględnieniem slippage i spreadu
            entry_price = signal.entry_price
            
            # Uwzględnij spread, jeśli jest to wymagane
            if self.config.use_spread:
                if signal.signal_type.name == "BUY":
                    entry_price += current_bar['spread'] * self.mt5_connector.get_symbol_info(signal.symbol)["point"]
            
            # Uwzględnij poślizg
            if signal.signal_type.name == "BUY":
                entry_price += self.config.slippage * self.mt5_connector.get_symbol_info(signal.symbol)["point"]
            else:
                entry_price -= self.config.slippage * self.mt5_connector.get_symbol_info(signal.symbol)["point"]
            
            # Obliczanie wielkości pozycji
            position_size = self.strategy.calculate_position_size(
                account_balance=self.balance,
                risk_pct=self.config.position_size_pct,
                entry_price=entry_price,
                stop_loss=signal.stop_loss,
                symbol=signal.symbol
            )
            
            # Ograniczenie wielkości pozycji
            position_size = max(min(position_size, self.config.max_volume), self.config.min_volume)
            
            # Otwórz pozycję za pomocą menedżera pozycji
            position = self.position_manager.open_position(
                symbol=signal.symbol,
                position_type=signal.signal_type,
                volume=position_size,
                entry_price=entry_price,
                stop_loss=signal.stop_loss,
                take_profit=signal.take_profit,
                open_time=current_time,
                comment=signal.comment,
                trailing_stop=self.config.use_trailing_stop,
                trailing_pips=self.config.trailing_stop_pips,
                breakeven=self.config.use_breakeven,
                breakeven_trigger_pips=self.config.breakeven_trigger_pips,
                breakeven_plus_pips=self.config.breakeven_plus_pips,
                partial_close=self.config.use_partial_close,
                partial_close_levels=self.config.partial_close_levels
            )
            
            # Utwórz obiekt BacktestTrade dla kompatybilności
            trade = BacktestTrade(
                signal_id=position.position_id,
                symbol=signal.symbol,
                direction="BUY" if signal.signal_type.name == "BUY" else "SELL",
                entry_price=entry_price,
                stop_loss=signal.stop_loss,
                take_profit=signal.take_profit,
                entry_time=current_time,
                volume=position_size,
                confidence=0.7,  # Domyślna wartość
                metadata={"comment": signal.comment, "position_id": position.position_id}
            )
            
            # Inicjalizacja wartości pipa i wartości pozycji dla symbolu, jeśli nie istnieją
            if signal.symbol not in self.pip_values:
                symbol_info = self.mt5_connector.get_symbol_info(signal.symbol)
                self.pip_values[signal.symbol] = symbol_info["point"] * 10  # 1 pip = 10 punktów
                self.position_values[signal.symbol] = 100000  # Domyślnie 1 lot = 100,000 jednostek
            
            self.logger.info(f"Otwarto nową pozycję: {trade.direction} {trade.symbol} @ {entry_price}, SL: {signal.stop_loss}, TP: {signal.take_profit}, wolumen: {position_size}")
            
            return trade
            
        except Exception as e:
            self.logger.error(f"Błąd podczas otwierania transakcji: {e}")
            return None
    
    def _update_trades(self, current_bar: pd.Series, current_time: datetime) -> None:
        """
        Aktualizuje status otwartych pozycji na podstawie aktualnej ceny.
        
        Args:
            current_bar: Aktualna barka
            current_time: Aktualny czas
        """
        try:
            # Słownik bieżących cen dla każdego symbolu
            current_prices = {self.config.symbol: current_bar['close']}
            
            # Aktualizuj wszystkie pozycje za pomocą menedżera pozycji
            updates = self.position_manager.update_positions(
                current_prices=current_prices,
                current_time=current_time,
                pip_values=self.pip_values,
                position_values=self.position_values
            )
            
            # Pobierz zamknięte pozycje (dodane dla testu integracji z PositionManager)
            closed_positions = self.position_manager.get_closed_positions()
            
            # Przetwarzanie wyników aktualizacji
            
            # 1. Zamknięte pozycje
            for closed_position in updates["closed_positions"]:
                # Znajdź odpowiadający BacktestTrade dla zamkniętej pozycji
                position_id = closed_position["position_id"]
                for trade in self.trades:
                    if trade.status == "open" and trade.metadata.get("position_id") == position_id:
                        # Aktualizuj obiekt BacktestTrade
                        trade.exit_price = closed_position["close_price"]
                        trade.exit_time = closed_position["close_time"]
                        trade.status = "closed"
                        trade.reason = closed_position["close_reason"]
                        
                        # Określ, czy osiągnięto cel czy stop-loss
                        trade.hit_target = (closed_position["close_reason"] == "tp")
                        trade.hit_stop = (closed_position["close_reason"] == "sl")
                        
                        # Oblicz zysk/stratę
                        profit_pips = closed_position["profit_pips"]
                        
                        # Zamień pipsy na kwotę pieniężną
                        symbol = trade.symbol
                        pip_value = self.pip_values.get(symbol, 0.1)
                        trade.profit = profit_pips * pip_value * trade.volume
                        trade.pips = profit_pips
                        
                        # Aktualizuj saldo
                        self.balance += trade.profit
                        
                        self.logger.info(f"Zamknięto pozycję: {trade.direction} {trade.symbol} @ {trade.exit_price}, powód: {trade.reason}, zysk/strata: {trade.profit:.2f}")
                        
                        break
            
            # 2. Częściowo zamknięte pozycje
            for partial_close in updates["partial_closes"]:
                # Oblicz zysk z częściowego zamknięcia
                profit_amount = partial_close["profit_amount"]
                
                # Aktualizuj saldo
                self.balance += profit_amount
                
                self.logger.info(f"Częściowo zamknięto pozycję: {partial_close['level']} pips, {partial_close['percent']}%, zysk: {profit_amount:.2f}")
            
            # 3. Aktualizacje trailing stop
            for trailing_stop in updates["trailing_stops"]:
                position_id = trailing_stop["position_id"]
                new_stop_loss = trailing_stop["new_stop_loss"]
                
                # Zaktualizuj odpowiadający BacktestTrade
                for trade in self.trades:
                    if trade.status == "open" and trade.metadata.get("position_id") == position_id:
                        trade.stop_loss = new_stop_loss
                        self.logger.info(f"Zaktualizowano trailing stop dla pozycji {position_id}: nowy SL = {new_stop_loss}")
                        break
            
            # 4. Aktualizacje breakeven
            for breakeven in updates["breakevens"]:
                position_id = breakeven["position_id"]
                new_stop_loss = breakeven["new_stop_loss"]
                
                # Zaktualizuj odpowiadający BacktestTrade
                for trade in self.trades:
                    if trade.status == "open" and trade.metadata.get("position_id") == position_id:
                        trade.stop_loss = new_stop_loss
                        self.logger.info(f"Ustawiono breakeven dla pozycji {position_id}: nowy SL = {new_stop_loss}")
                        break
        
        except Exception as e:
            self.logger.error(f"Błąd podczas aktualizacji pozycji: {e}")
            import traceback
            self.logger.error(traceback.format_exc())
    
    def _calculate_floating_profit(self, current_bar: pd.Series) -> float:
        """
        Oblicza bieżący zysk/stratę z otwartych pozycji.
        
        Args:
            current_bar: Aktualna barka
            
        Returns:
            float: Bieżący zysk/strata
        """
        try:
            # Słownik bieżących cen dla każdego symbolu
            current_prices = {self.config.symbol: current_bar['close']}
            
            # Aktualizacja statystyk pozycji (bez faktycznej aktualizacji stanu)
            for position in self.position_manager.get_active_positions():
                symbol = position.symbol
                
                if symbol not in current_prices:
                    continue
                
                current_price = current_prices[symbol]
                pip_value = self.pip_values.get(symbol, 0.1)
                position_value = self.position_values.get(symbol, 100000)
                
                # Aktualizacja statystyk
                position.update_stats(current_price, datetime.now(), pip_value, position_value)
            
            # Pobierz bieżący zysk z pozycji
            floating_profit = self.position_manager.get_current_profit()
            
            return floating_profit
            
        except Exception as e:
            self.logger.error(f"Błąd podczas obliczania bieżącego zysku: {e}")
            return 0.0
    
    def _create_empty_result(self) -> BacktestResult:
        """
        Tworzy pusty obiekt wyników backtestingu (dla przypadku błędu).
        
        Returns:
            BacktestResult: Pusty obiekt wyników
        """
        return BacktestResult(
            config=self.config,
            balance=self.config.initial_balance,
            equity_curve=[self.config.initial_balance],
            timestamps=[self.config.start_date]
        ) 