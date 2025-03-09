#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Moduł integracji systemu analizy danych z systemem handlowym.

Ten moduł jest odpowiedzialny za:
- Łączenie systemu analizy danych (SignalGenerator, SignalValidator, FeedbackLoop) z systemem handlowym
- Automatyczne podejmowanie decyzji handlowych na podstawie sygnałów
- Wykonywanie operacji handlowych poprzez MT5 Expert Advisor
- Śledzenie i aktualizację wyników handlowych
"""

import os
import json
import time
import logging
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Union, Tuple
from enum import Enum, auto
from dataclasses import dataclass

# Importy wewnętrzne
try:
    # Próbujemy importu z przedrostkiem src (dla testów z katalogu głównego)
    from src.analysis.signal_generator import SignalGenerator, SignalType, SignalStrength, SignalSource
    from src.analysis.signal_validator import SignalValidator, ValidationResult
    from src.analysis.feedback_loop import FeedbackLoop
    from src.mt5_bridge.trading_service import TradingService
    from src.position_management.position_manager import PositionManager
    from src.risk_management.risk_manager import RiskManager, OrderValidationResult
    from src.database.trade_repository import TradeRepository
except ImportError:
    # Próbujemy importu względnego (dla uruchamiania z katalogu src)
    from analysis.signal_generator import SignalGenerator, SignalType, SignalStrength, SignalSource
    from analysis.signal_validator import SignalValidator, ValidationResult
    from analysis.feedback_loop import FeedbackLoop
    from mt5_bridge.trading_service import TradingService
    from position_management.position_manager import PositionManager
    from risk_management.risk_manager import RiskManager, OrderValidationResult
    from database.trade_repository import TradeRepository

# Konfiguracja loggera
logger = logging.getLogger('trading_agent.trading_integration')


class TradingDecisionStatus(Enum):
    """Status decyzji handlowej."""
    PENDING = auto()      # Oczekująca decyzja
    EXECUTED = auto()     # Wykonana decyzja
    REJECTED = auto()     # Odrzucona decyzja
    CANCELLED = auto()    # Anulowana decyzja
    EXPIRED = auto()      # Wygasła decyzja
    ERROR = auto()        # Błąd podczas wykonywania


@dataclass
class TradingDecision:
    """Decyzja handlowa wygenerowana na podstawie sygnału."""
    symbol: str                       # Symbol instrumentu
    action: str                       # Akcja (BUY, SELL, CLOSE)
    volume: float                     # Wolumen (ilość lotów)
    price: Optional[float] = None     # Cena (None dla rynkowej)
    stop_loss: Optional[float] = None # Poziom Stop Loss
    take_profit: Optional[float] = None # Poziom Take Profit
    signal_id: Optional[int] = None   # ID sygnału, który wygenerował decyzję
    status: TradingDecisionStatus = TradingDecisionStatus.PENDING
    created_at: datetime = None       # Czas utworzenia decyzji
    executed_at: Optional[datetime] = None # Czas wykonania decyzji
    ticket: Optional[int] = None      # Numer identyfikacyjny transakcji MT5
    reason: Optional[str] = None      # Powód decyzji
    quality_score: float = 0.0        # Ocena jakości decyzji (0-1)
    risk_score: float = 0.0           # Ocena ryzyka decyzji (0-1)
    
    def __post_init__(self):
        """Inicjalizacja pól po utworzeniu."""
        if self.created_at is None:
            self.created_at = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """Konwersja do słownika."""
        return {
            'symbol': self.symbol,
            'action': self.action,
            'volume': self.volume,
            'price': self.price,
            'stop_loss': self.stop_loss,
            'take_profit': self.take_profit,
            'signal_id': self.signal_id,
            'status': self.status.name,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'executed_at': self.executed_at.isoformat() if self.executed_at else None,
            'ticket': self.ticket,
            'reason': self.reason,
            'quality_score': self.quality_score,
            'risk_score': self.risk_score
        }


class TradingIntegration:
    """
    Klasa odpowiedzialna za integrację systemu analizy danych z systemem handlowym.
    
    Ta klasa łączy komponenty systemu analizy (SignalGenerator, SignalValidator, FeedbackLoop)
    z komponentami handlowymi (TradingService, PositionManager, RiskManager) w celu
    automatycznego podejmowania i wykonywania decyzji handlowych.
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        """Implementacja wzorca Singleton."""
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(TradingIntegration, cls).__new__(cls)
                cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """Inicjalizacja integracji handlowej."""
        if self._initialized:
            return
            
        self.logger = logging.getLogger('trading_agent.trading_integration')
        self.logger.info("Inicjalizacja TradingIntegration")
        
        # Inicjalizacja komponentów analizy
        self.signal_generator = SignalGenerator()
        self.signal_validator = SignalValidator()
        self.feedback_loop = FeedbackLoop()
        
        # Inicjalizacja komponentów handlowych
        self.trading_service = TradingService()
        self.position_manager = PositionManager()
        self.risk_manager = RiskManager()
        self.trade_repository = TradeRepository()
        
        # Buforowanie decyzji handlowych
        self.decisions = []
        self.decisions_history = []
        
        # Status integracji
        self.is_running = False
        self.trading_enabled = False
        self.last_market_check = datetime.now()
        self.check_interval = 60  # sekundy
        
        # Uruchomienie wątku decyzyjnego
        self.decision_thread = None
        
        self._initialized = True
    
    def start(self) -> bool:
        """
        Uruchamia integrację handlową.
        
        Returns:
            bool: True, jeśli uruchomienie się powiodło, False w przeciwnym przypadku.
        """
        if self.is_running:
            self.logger.warning("TradingIntegration jest już uruchomione")
            return True
        
        try:
            # Nawiązanie połączenia z MT5
            self.logger.info("Nawiązywanie połączenia z MT5...")
            if not self.trading_service.connect():
                self.logger.error("Nie udało się nawiązać połączenia z MT5")
                return False
            
            # Uruchomienie wątku decyzyjnego
            self.is_running = True
            self.decision_thread = threading.Thread(target=self._decision_loop, daemon=True)
            self.decision_thread.start()
            
            self.logger.info("TradingIntegration uruchomione")
            return True
            
        except Exception as e:
            self.logger.error(f"Błąd podczas uruchamiania TradingIntegration: {str(e)}")
            return False
    
    def stop(self) -> bool:
        """
        Zatrzymuje integrację handlową.
        
        Returns:
            bool: True, jeśli zatrzymanie się powiodło, False w przeciwnym przypadku.
        """
        if not self.is_running:
            self.logger.warning("TradingIntegration nie jest uruchomione")
            return True
        
        try:
            # Zatrzymanie wątku decyzyjnego
            self.is_running = False
            
            if self.decision_thread and self.decision_thread.is_alive():
                self.decision_thread.join(timeout=5.0)
            
            # Zamknięcie połączenia z MT5
            self.trading_service.disconnect()
            
            self.logger.info("TradingIntegration zatrzymane")
            return True
            
        except Exception as e:
            self.logger.error(f"Błąd podczas zatrzymywania TradingIntegration: {str(e)}")
            return False
    
    def enable_trading(self, enabled: bool = True) -> None:
        """
        Włącza lub wyłącza automatyczne handlowanie.
        
        Args:
            enabled: True, aby włączyć handlowanie, False aby wyłączyć.
        """
        self.trading_enabled = enabled
        self.logger.info(f"Automatyczne handlowanie {'włączone' if enabled else 'wyłączone'}")
    
    def _decision_loop(self) -> None:
        """Główna pętla podejmowania decyzji handlowych."""
        self.logger.info("Uruchomienie pętli decyzyjnej")
        
        while self.is_running:
            try:
                current_time = datetime.now()
                
                # Sprawdzamy rynek co określony interwał
                if (current_time - self.last_market_check).total_seconds() >= self.check_interval:
                    self.analyze_market()
                    self.last_market_check = current_time
                
                # Przetwarzamy oczekujące decyzje
                self.process_pending_decisions()
                
                # Aktualizujemy status otwartych pozycji
                self.update_positions()
                
                # Co jakiś czas aktualizujemy parametry strategii na podstawie historii
                if current_time.minute % 15 == 0 and current_time.second < 10:
                    self.update_strategy_parameters()
                
                # Pauza, aby uniknąć nadmiernego obciążenia CPU
                time.sleep(1)
                
            except Exception as e:
                self.logger.error(f"Błąd w pętli decyzyjnej: {str(e)}")
                time.sleep(5)  # Dłuższa pauza w przypadku błędu
    
    def analyze_market(self) -> None:
        """
        Analizuje rynek i generuje nowe sygnały handlowe.
        """
        self.logger.debug("Analizowanie rynku...")
        
        try:
            # Pobieramy listę monitorowanych symboli
            symbols = self._get_monitored_symbols()
            
            for symbol in symbols:
                # Pobieramy dane rynkowe
                market_data = self.trading_service.get_market_data(symbol)
                if not market_data:
                    self.logger.warning(f"Nie udało się pobrać danych rynkowych dla {symbol}")
                    continue
                
                # Generujemy sygnały
                signals = self.signal_generator.generate_signals(symbol, market_data)
                
                for signal in signals:
                    # Walidujemy sygnał
                    validation_result = self.signal_validator.validate_signal(signal)
                    
                    if validation_result == ValidationResult.VALID:
                        # Oceniamy jakość sygnału
                        signal_quality = self.feedback_loop.get_signal_quality(signal)
                        
                        # Tworzymy decyzję handlową
                        decision = self._create_trading_decision(signal, signal_quality)
                        
                        # Walidujemy decyzję przez RiskManager
                        risk_validation = self._validate_decision_risk(decision)
                        
                        if risk_validation == OrderValidationResult.VALID:
                            self.decisions.append(decision)
                            self.logger.info(f"Nowa decyzja handlowa: {decision.action} {decision.symbol} "
                                             f"vol:{decision.volume} SL:{decision.stop_loss} TP:{decision.take_profit}")
                        else:
                            decision.status = TradingDecisionStatus.REJECTED
                            decision.reason = f"Odrzucone przez RiskManager: {risk_validation.name}"
                            self.decisions_history.append(decision)
                            self.logger.warning(f"Decyzja odrzucona: {decision.reason}")
                    else:
                        self.logger.debug(f"Sygnał odrzucony: {validation_result.name} dla {symbol}")
            
        except Exception as e:
            self.logger.error(f"Błąd podczas analizy rynku: {str(e)}")
    
    def process_pending_decisions(self) -> None:
        """
        Przetwarza oczekujące decyzje handlowe.
        """
        if not self.trading_enabled:
            return
        
        for decision in list(self.decisions):
            try:
                # Sprawdzamy, czy decyzja nie wygasła
                if (datetime.now() - decision.created_at).total_seconds() > 300:  # 5 minut
                    decision.status = TradingDecisionStatus.EXPIRED
                    decision.reason = "Decyzja wygasła"
                    self.decisions.remove(decision)
                    self.decisions_history.append(decision)
                    self.logger.warning(f"Decyzja wygasła: {decision.action} {decision.symbol}")
                    continue
                
                # Wykonujemy decyzję handlową
                result = self._execute_decision(decision)
                
                if result:
                    decision.status = TradingDecisionStatus.EXECUTED
                    decision.executed_at = datetime.now()
                    decision.ticket = result.get('ticket')
                    self.decisions.remove(decision)
                    self.decisions_history.append(decision)
                    
                    # Zapisujemy informację o wykonanej decyzji
                    self._record_executed_decision(decision)
                    
                    self.logger.info(f"Decyzja wykonana: {decision.action} {decision.symbol} "
                                     f"ticket:{decision.ticket}")
                else:
                    # Jeśli trzeci raz nie udało się wykonać decyzji, odrzucamy ją
                    retries = getattr(decision, 'retries', 0) + 1
                    setattr(decision, 'retries', retries)
                    
                    if retries >= 3:
                        decision.status = TradingDecisionStatus.ERROR
                        decision.reason = "Nie udało się wykonać decyzji po 3 próbach"
                        self.decisions.remove(decision)
                        self.decisions_history.append(decision)
                        self.logger.error(f"Decyzja odrzucona po 3 próbach: {decision.action} {decision.symbol}")
                    else:
                        self.logger.warning(f"Nie udało się wykonać decyzji (próba {retries}/3): "
                                           f"{decision.action} {decision.symbol}")
                
            except Exception as e:
                self.logger.error(f"Błąd podczas przetwarzania decyzji: {str(e)}")
    
    def update_positions(self) -> None:
        """
        Aktualizuje status otwartych pozycji.
        """
        try:
            # Pobieramy aktualne pozycje
            positions = self.position_manager.get_open_positions()
            
            if not positions:
                return
                
            for position in positions:
                # Aktualizujemy status pozycji w systemie
                self.position_manager.update_position(position)
                
                # Sprawdzamy, czy pozycja została zamknięta
                if position.status == 'CLOSED':
                    # Aktualizujemy wyniki w FeedbackLoop
                    self._update_feedback_with_position_result(position)
            
        except Exception as e:
            self.logger.error(f"Błąd podczas aktualizacji pozycji: {str(e)}")
    
    def update_strategy_parameters(self) -> None:
        """
        Aktualizuje parametry strategii na podstawie historii handlowej.
        """
        try:
            # Optymalizujemy parametry dla każdego monitorowanego symbolu
            symbols = self._get_monitored_symbols()
            
            for symbol in symbols:
                self.logger.debug(f"Optymalizacja parametrów dla {symbol}")
                optimized_params = self.feedback_loop.optimize_parameters(symbol)
                
                if optimized_params:
                    self.logger.info(f"Zaktualizowane parametry dla {symbol}: {optimized_params}")
            
            # Aktualizujemy wagi modeli AI
            model_weights = self.feedback_loop.update_model_weights()
            self.logger.debug(f"Zaktualizowane wagi modeli AI: {model_weights}")
            
        except Exception as e:
            self.logger.error(f"Błąd podczas aktualizacji parametrów strategii: {str(e)}")
    
    def _get_monitored_symbols(self) -> List[str]:
        """
        Pobiera listę monitorowanych symboli.
        
        Returns:
            List[str]: Lista monitorowanych symboli.
        """
        # TODO: Pobrać listę z konfiguracji lub zaimplementować dynamiczne wykrywanie
        return ["EURUSD", "GBPUSD", "USDJPY", "XAUUSD"]
    
    def _create_trading_decision(self, signal: Dict[str, Any], signal_quality: float) -> TradingDecision:
        """
        Tworzy decyzję handlową na podstawie sygnału.
        
        Args:
            signal: Sygnał handlowy
            signal_quality: Ocena jakości sygnału (0-1)
            
        Returns:
            TradingDecision: Decyzja handlowa
        """
        # Pobieramy dane rynkowe
        market_data = self.trading_service.get_market_data(signal['symbol'])
        
        # Określamy parametry zlecenia
        action = signal['type']
        symbol = signal['symbol']
        
        # Obliczamy wolumen na podstawie wielkości konta i oceny jakości sygnału
        account_info = self.trading_service.get_account_info()
        account_balance = account_info['balance']
        
        # Bazowy procent kapitału na podstawie jakości sygnału
        base_risk_percent = 0.01  # 1% dla przeciętnego sygnału
        
        # Skalujemy procent ryzyka w zależności od jakości sygnału (0.5% - 2%)
        risk_percent = base_risk_percent * (0.5 + 1.5 * signal_quality)
        
        # Obliczamy wolumen na podstawie ryzyka
        volume = self._calculate_position_size(symbol, risk_percent, account_balance)
        
        # Określamy poziomy SL i TP
        stop_loss, take_profit = self._calculate_sl_tp(signal, market_data)
        
        # Tworzymy decyzję
        decision = TradingDecision(
            symbol=symbol,
            action=action,
            volume=volume,
            price=None,  # Cena rynkowa
            stop_loss=stop_loss,
            take_profit=take_profit,
            signal_id=signal.get('id'),
            quality_score=signal_quality
        )
        
        return decision
    
    def _calculate_position_size(self, symbol: str, risk_percent: float, account_balance: float) -> float:
        """
        Oblicza wielkość pozycji na podstawie ryzyka.
        
        Args:
            symbol: Symbol instrumentu
            risk_percent: Procent ryzyka (0-1)
            account_balance: Saldo konta
            
        Returns:
            float: Wielkość pozycji w lotach
        """
        # Pobieramy informacje o instrumencie
        symbol_info = self.trading_service.get_symbol_info(symbol)
        
        if not symbol_info:
            return 0.01  # Minimalny lot jako wartość domyślna
        
        # Pobieramy parametry instrumentu
        lot_size = symbol_info.get('trade_contract_size', 100000)
        min_lot = symbol_info.get('volume_min', 0.01)
        lot_step = symbol_info.get('volume_step', 0.01)
        
        # Obliczamy kwotę ryzyka
        risk_amount = account_balance * risk_percent
        
        # Obliczamy wielkość pozycji w lotach
        # W rzeczywistej implementacji należałoby uwzględnić również stop-loss
        position_size = risk_amount / lot_size
        
        # Zaokrąglamy do pełnego kroku lota
        position_size = round(position_size / lot_step) * lot_step
        
        # Upewniamy się, że wielkość nie jest mniejsza niż minimalny lot
        position_size = max(position_size, min_lot)
        
        return position_size
    
    def _calculate_sl_tp(self, signal: Dict[str, Any], market_data: Dict[str, Any]) -> Tuple[float, float]:
        """
        Oblicza poziomy Stop Loss i Take Profit na podstawie sygnału i danych rynkowych.
        
        Args:
            signal: Sygnał handlowy
            market_data: Dane rynkowe
            
        Returns:
            Tuple[float, float]: Poziomy Stop Loss i Take Profit
        """
        # W rzeczywistej implementacji należałoby uwzględnić więcej czynników
        # Na potrzeby przykładu używamy prostego podejścia
        
        symbol = signal['symbol']
        action = signal['type']
        price = market_data['ask'] if action == 'BUY' else market_data['bid']
        
        # Pobieramy informacje o instrumencie
        symbol_info = self.trading_service.get_symbol_info(symbol)
        point = symbol_info.get('point', 0.0001)
        
        # Ustawiamy domyślne wartości
        sl_pips = 30
        tp_pips = 50
        
        # Jeśli sygnał zawiera sugerowane poziomy SL i TP, używamy ich
        if 'stop_loss_pips' in signal:
            sl_pips = signal['stop_loss_pips']
        
        if 'take_profit_pips' in signal:
            tp_pips = signal['take_profit_pips']
        
        # Obliczamy poziomy SL i TP
        if action == 'BUY':
            stop_loss = price - sl_pips * point
            take_profit = price + tp_pips * point
        else:  # SELL
            stop_loss = price + sl_pips * point
            take_profit = price - tp_pips * point
        
        return stop_loss, take_profit
    
    def _validate_decision_risk(self, decision: TradingDecision) -> OrderValidationResult:
        """
        Waliduje decyzję handlową pod kątem ryzyka.
        
        Args:
            decision: Decyzja handlowa
            
        Returns:
            OrderValidationResult: Wynik walidacji
        """
        # Tworzymy parametry zlecenia do walidacji
        order_params = {
            'symbol': decision.symbol,
            'type': decision.action,
            'volume': decision.volume,
            'price': decision.price or 0.0,  # 0 dla ceny rynkowej
            'stop_loss': decision.stop_loss or 0.0,
            'take_profit': decision.take_profit or 0.0
        }
        
        # Walidujemy zlecenie przez RiskManager
        validation_result = self.risk_manager.validate_order(order_params)
        
        # Ustawiamy ocenę ryzyka
        if validation_result == OrderValidationResult.VALID:
            risk_assessment = self.risk_manager.assess_order_risk(order_params)
            decision.risk_score = 1.0 - risk_assessment.get('risk_level', 0.5)
        
        return validation_result
    
    def _execute_decision(self, decision: TradingDecision) -> Optional[Dict[str, Any]]:
        """
        Wykonuje decyzję handlową.
        
        Args:
            decision: Decyzja handlowa
            
        Returns:
            Optional[Dict[str, Any]]: Wynik wykonania lub None w przypadku błędu
        """
        try:
            # Tworzymy parametry zlecenia
            order_params = {
                'symbol': decision.symbol,
                'type': decision.action,
                'volume': decision.volume,
                'price': decision.price,  # None dla ceny rynkowej
                'stop_loss': decision.stop_loss,
                'take_profit': decision.take_profit
            }
            
            # Wykonujemy zlecenie
            if decision.action in ['BUY', 'SELL']:
                result = self.trading_service.open_order(**order_params)
            elif decision.action == 'CLOSE':
                # Dla zamknięcia pozycji potrzebujemy ticket
                positions = self.position_manager.find_positions(
                    symbol=decision.symbol, 
                    type=decision.action.replace('CLOSE_', '')
                )
                
                if not positions:
                    self.logger.warning(f"Nie znaleziono pozycji do zamknięcia: {decision.symbol}")
                    return None
                
                result = self.trading_service.close_position(positions[0].ticket)
            else:
                self.logger.error(f"Nieznana akcja: {decision.action}")
                return None
            
            return result
            
        except Exception as e:
            self.logger.error(f"Błąd podczas wykonywania decyzji: {str(e)}")
            return None
    
    def _record_executed_decision(self, decision: TradingDecision) -> None:
        """
        Zapisuje informację o wykonanej decyzji.
        
        Args:
            decision: Wykonana decyzja handlowa
        """
        try:
            # Zapisujemy informację w bazie danych
            trade_data = {
                'symbol': decision.symbol,
                'type': decision.action,
                'volume': decision.volume,
                'open_price': decision.price,
                'stop_loss': decision.stop_loss,
                'take_profit': decision.take_profit,
                'open_time': decision.executed_at,
                'ticket': decision.ticket,
                'signal_id': decision.signal_id,
                'quality_score': decision.quality_score,
                'risk_score': decision.risk_score
            }
            
            self.trade_repository.add_trade(trade_data)
            
        except Exception as e:
            self.logger.error(f"Błąd podczas zapisywania informacji o decyzji: {str(e)}")
    
    def _update_feedback_with_position_result(self, position: Dict[str, Any]) -> None:
        """
        Aktualizuje system feedback loop wynikami pozycji.
        
        Args:
            position: Zamknięta pozycja
        """
        try:
            # Pobieramy dane o sygnale, który wygenerował pozycję
            trade = self.trade_repository.get_trade_by_ticket(position.ticket)
            
            if not trade or not trade.get('signal_id'):
                return
                
            signal_id = trade.get('signal_id')
            signal = self.signal_repository.get_signal_by_id(signal_id)
            
            if not signal:
                return
            
            # Aktualizujemy dane o wyniku sygnału
            signal_result = {
                'signal_id': signal_id,
                'result': 'SUCCESS' if position.profit > 0 else 'FAILURE',
                'profit': position.profit,
                'open_time': position.open_time,
                'close_time': position.close_time,
                'duration': (position.close_time - position.open_time).total_seconds() / 60,  # W minutach
                'symbol': position.symbol,
                'type': position.type
            }
            
            # Zapisujemy wynik w systemie feedback loop
            self.feedback_loop.record_signal_result(signal_result)
            
        except Exception as e:
            self.logger.error(f"Błąd podczas aktualizacji feedback loop: {str(e)}")


def get_trading_integration() -> TradingIntegration:
    """
    Zwraca instancję TradingIntegration (Singleton).
    
    Returns:
        Instancja TradingIntegration
    """
    return TradingIntegration() 