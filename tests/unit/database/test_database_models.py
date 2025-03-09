#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Testy jednostkowe dla modeli danych w bazie danych.
"""

import unittest
from datetime import datetime
from src.database.models import (
    Instrument, TradingSetup, TradingSignal, Transaction,
    OrderModification, AccountSnapshot, SystemLog,
    AIStats, PerformanceMetric
)


class TestDatabaseModels(unittest.TestCase):
    """Testy dla modeli danych w bazie danych."""
    
    def test_instrument_creation(self):
        """Test tworzenia modelu Instrument."""
        # Tworzenie z minimalnymi parametrami
        instrument = Instrument(symbol="EURUSD")
        self.assertEqual(instrument.symbol, "EURUSD")
        self.assertEqual(instrument.description, "")
        self.assertEqual(instrument.pip_value, 0.0001)
        
        # Tworzenie z wszystkimi parametrami
        instrument = Instrument(
            symbol="GBPUSD",
            description="Great Britain Pound vs US Dollar",
            pip_value=0.0001,
            min_lot=0.01,
            max_lot=100.00,
            lot_step=0.01,
            active=True,
            id=1,
            created_at=datetime(2023, 1, 1),
            updated_at=datetime(2023, 1, 1)
        )
        self.assertEqual(instrument.symbol, "GBPUSD")
        self.assertEqual(instrument.description, "Great Britain Pound vs US Dollar")
        self.assertEqual(instrument.id, 1)
        self.assertEqual(instrument.created_at, datetime(2023, 1, 1))
    
    def test_trading_setup_creation(self):
        """Test tworzenia modelu TradingSetup."""
        # Tworzenie z wymaganymi parametrami
        setup = TradingSetup(
            name="EURUSD Breakout",
            symbol="EURUSD",
            timeframe="H1",
            setup_type="breakout",
            direction="buy",
            entry_conditions="Breakout above resistance"
        )
        self.assertEqual(setup.name, "EURUSD Breakout")
        self.assertEqual(setup.symbol, "EURUSD")
        self.assertEqual(setup.timeframe, "H1")
        self.assertEqual(setup.setup_type, "breakout")
        self.assertEqual(setup.direction, "buy")
        self.assertEqual(setup.entry_conditions, "Breakout above resistance")
        self.assertEqual(setup.exit_conditions, "")
        self.assertEqual(setup.risk_reward_ratio, 0.0)
        self.assertEqual(setup.success_rate, 0.0)
        self.assertEqual(setup.id, None)
    
    def test_trading_signal_creation(self):
        """Test tworzenia modelu TradingSignal."""
        # Tworzenie z wymaganymi parametrami
        signal = TradingSignal(
            symbol="EURUSD",
            timeframe="H1",
            direction="buy",
            entry_price=1.1000,
            stop_loss=1.0950,
            take_profit=1.1100
        )
        self.assertEqual(signal.symbol, "EURUSD")
        self.assertEqual(signal.timeframe, "H1")
        self.assertEqual(signal.direction, "buy")
        self.assertEqual(signal.entry_price, 1.1000)
        self.assertEqual(signal.stop_loss, 1.0950)
        self.assertEqual(signal.take_profit, 1.1100)
        self.assertEqual(signal.confidence, 0.0)
        self.assertEqual(signal.status, "pending")
        self.assertEqual(signal.setup_id, None)
        self.assertEqual(signal.id, None)
    
    def test_transaction_creation(self):
        """Test tworzenia modelu Transaction."""
        # Tworzenie z wymaganymi parametrami
        transaction = Transaction(
            symbol="EURUSD",
            order_type="buy",
            volume=0.1,
            status="pending"
        )
        self.assertEqual(transaction.symbol, "EURUSD")
        self.assertEqual(transaction.order_type, "buy")
        self.assertEqual(transaction.volume, 0.1)
        self.assertEqual(transaction.status, "pending")
        self.assertEqual(transaction.open_price, None)
        self.assertEqual(transaction.close_price, None)
        self.assertEqual(transaction.profit, 0.0)
        self.assertEqual(transaction.id, None)
        
        # Tworzenie z wszystkimi parametrami
        transaction = Transaction(
            symbol="GBPUSD",
            order_type="sell",
            volume=0.2,
            status="open",
            open_price=1.2000,
            stop_loss=1.2050,
            take_profit=1.1900,
            mt5_order_id=12345,
            signal_id=1,
            open_time=datetime(2023, 1, 1),
            profit=0.0,
            id=1
        )
        self.assertEqual(transaction.symbol, "GBPUSD")
        self.assertEqual(transaction.order_type, "sell")
        self.assertEqual(transaction.volume, 0.2)
        self.assertEqual(transaction.status, "open")
        self.assertEqual(transaction.open_price, 1.2000)
        self.assertEqual(transaction.stop_loss, 1.2050)
        self.assertEqual(transaction.take_profit, 1.1900)
        self.assertEqual(transaction.mt5_order_id, 12345)
        self.assertEqual(transaction.signal_id, 1)
        self.assertEqual(transaction.open_time, datetime(2023, 1, 1))
        self.assertEqual(transaction.id, 1)
    
    def test_order_modification_creation(self):
        """Test tworzenia modelu OrderModification."""
        # Tworzenie z wymaganymi parametrami
        modification = OrderModification(
            transaction_id=1,
            modification_type="stop_loss",
            old_value=1.0950,
            new_value=1.0970,
            status="pending"
        )
        self.assertEqual(modification.transaction_id, 1)
        self.assertEqual(modification.modification_type, "stop_loss")
        self.assertEqual(modification.old_value, 1.0950)
        self.assertEqual(modification.new_value, 1.0970)
        self.assertEqual(modification.status, "pending")
        self.assertEqual(modification.executed_at, None)
        self.assertEqual(modification.id, None)
    
    def test_account_snapshot_creation(self):
        """Test tworzenia modelu AccountSnapshot."""
        # Tworzenie z wymaganymi parametrami
        snapshot = AccountSnapshot(
            balance=10000.00,
            equity=10050.00,
            margin=100.00,
            free_margin=9950.00
        )
        self.assertEqual(snapshot.balance, 10000.00)
        self.assertEqual(snapshot.equity, 10050.00)
        self.assertEqual(snapshot.margin, 100.00)
        self.assertEqual(snapshot.free_margin, 9950.00)
        self.assertEqual(snapshot.margin_level, None)
        self.assertEqual(snapshot.open_positions, 0)
        self.assertEqual(snapshot.id, None)
    
    def test_system_log_creation(self):
        """Test tworzenia modelu SystemLog."""
        # Tworzenie z wymaganymi parametrami
        log = SystemLog(
            log_level="INFO",
            message="Test message"
        )
        self.assertEqual(log.log_level, "INFO")
        self.assertEqual(log.message, "Test message")
        self.assertEqual(log.component, "")
        self.assertEqual(log.id, None)
    
    def test_ai_stats_creation(self):
        """Test tworzenia modelu AIStats."""
        # Tworzenie z wymaganymi parametrami
        stats = AIStats(
            model="Claude",
            query_type="market_analysis"
        )
        self.assertEqual(stats.model, "Claude")
        self.assertEqual(stats.query_type, "market_analysis")
        self.assertEqual(stats.response_time, None)
        self.assertEqual(stats.tokens_used, None)
        self.assertEqual(stats.cost, None)
        self.assertEqual(stats.success, True)
        self.assertEqual(stats.id, None)
        
        # Tworzenie z wszystkimi parametrami
        stats = AIStats(
            model="Grok",
            query_type="setup_validation",
            response_time=0.5,
            tokens_used=1000,
            cost=0.01,
            success=True,
            error_message="",
            id=1
        )
        self.assertEqual(stats.model, "Grok")
        self.assertEqual(stats.query_type, "setup_validation")
        self.assertEqual(stats.response_time, 0.5)
        self.assertEqual(stats.tokens_used, 1000)
        self.assertEqual(stats.cost, 0.01)
        self.assertEqual(stats.success, True)
        self.assertEqual(stats.error_message, "")
        self.assertEqual(stats.id, 1)
    
    def test_performance_metric_creation(self):
        """Test tworzenia modelu PerformanceMetric."""
        # Tworzenie z wymaganymi parametrami
        metric = PerformanceMetric(
            metric_name="win_rate",
            metric_value=65.5
        )
        self.assertEqual(metric.metric_name, "win_rate")
        self.assertEqual(metric.metric_value, 65.5)
        self.assertEqual(metric.metric_unit, "")
        self.assertEqual(metric.period_start, None)
        self.assertEqual(metric.period_end, None)
        self.assertEqual(metric.id, None)
        
        # Tworzenie z wszystkimi parametrami
        metric = PerformanceMetric(
            metric_name="profit_factor",
            metric_value=2.5,
            metric_unit="ratio",
            period_start=datetime(2023, 1, 1),
            period_end=datetime(2023, 1, 31),
            id=1
        )
        self.assertEqual(metric.metric_name, "profit_factor")
        self.assertEqual(metric.metric_value, 2.5)
        self.assertEqual(metric.metric_unit, "ratio")
        self.assertEqual(metric.period_start, datetime(2023, 1, 1))
        self.assertEqual(metric.period_end, datetime(2023, 1, 31))
        self.assertEqual(metric.id, 1)


if __name__ == "__main__":
    unittest.main() 