#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Modele danych dla tabel bazy danych.
"""

from datetime import datetime
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any


@dataclass
class Instrument:
    """Model dla instrumentu handlowego."""
    symbol: str
    description: str = ""
    pip_value: float = 0.0001
    min_lot: float = 0.01
    max_lot: float = 100.00
    lot_step: float = 0.01
    active: bool = True
    id: Optional[int] = None
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)


@dataclass
class TradingSetup:
    """Model dla setupu handlowego."""
    name: str
    symbol: str
    timeframe: str
    setup_type: str
    direction: str
    entry_conditions: str
    description: str = ""
    exit_conditions: str = ""
    risk_reward_ratio: float = 0.0
    success_rate: float = 0.0
    active: bool = True
    id: Optional[int] = None
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)


@dataclass
class TradingSignal:
    """Model dla sygnału handlowego."""
    symbol: str
    timeframe: str
    direction: str
    entry_price: float
    stop_loss: float
    take_profit: float
    confidence: float = 0.0
    status: str = "pending"
    ai_analysis: str = ""
    setup_id: Optional[int] = None
    execution_id: Optional[int] = None
    id: Optional[int] = None
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    expired_at: Optional[datetime] = None


@dataclass
class Transaction:
    """Model dla transakcji handlowej."""
    symbol: str
    order_type: str
    volume: float
    status: str
    open_price: Optional[float] = None
    close_price: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    mt5_order_id: Optional[int] = None
    signal_id: Optional[int] = None
    open_time: Optional[datetime] = None
    close_time: Optional[datetime] = None
    profit: float = 0.0
    commission: float = 0.0
    swap: float = 0.0
    comment: str = ""
    id: Optional[int] = None
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)


@dataclass
class OrderModification:
    """Model dla modyfikacji zlecenia."""
    transaction_id: int
    modification_type: str
    old_value: float
    new_value: float
    status: str
    executed_at: Optional[datetime] = None
    comment: str = ""
    id: Optional[int] = None
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class AccountSnapshot:
    """Model dla stanu rachunku."""
    balance: float
    equity: float
    margin: float
    free_margin: float
    margin_level: Optional[float] = None
    open_positions: int = 0
    id: Optional[int] = None
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class SystemLog:
    """Model dla logu systemowego."""
    log_level: str
    message: str
    component: str = ""
    id: Optional[int] = None
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class AIStats:
    """Model dla statystyk AI."""
    model: str
    query_type: str
    response_time: Optional[float] = None
    tokens_used: Optional[int] = None
    cost: Optional[float] = None
    success: bool = True
    error_message: str = ""
    id: Optional[int] = None
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class PerformanceMetric:
    """Model dla metryki wydajności."""
    metric_name: str
    metric_value: float
    metric_unit: str = ""
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None
    id: Optional[int] = None
    created_at: datetime = field(default_factory=datetime.now) 