#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Moduł zarządzania ryzykiem dla systemu AgentMT5.

Ten moduł zawiera klasy i funkcje odpowiedzialne za zarządzanie ryzykiem,
w tym walidację zleceń, limity pozycji, zarządzanie stop-lossami
i śledzenie ekspozycji.
"""

from .risk_manager import (
    RiskManager, RiskParameters, RiskLevel, OrderValidationResult, get_risk_manager
)
from .order_validator import (
    Order, OrderValidator, get_order_validator
)
from .exposure_tracker import (
    ExposureTracker, get_exposure_tracker
)
from .stop_loss_manager import (
    StopLossManager, StopLossStrategy, TrailingStopStrategy,
    StopLossConfig, TrailingStopConfig, PositionState, get_stop_loss_manager
)

__all__ = [
    'RiskManager', 'RiskParameters', 'RiskLevel', 'OrderValidationResult', 'get_risk_manager',
    'Order', 'OrderValidator', 'get_order_validator',
    'ExposureTracker', 'get_exposure_tracker',
    'StopLossManager', 'StopLossStrategy', 'TrailingStopStrategy',
    'StopLossConfig', 'TrailingStopConfig', 'PositionState', 'get_stop_loss_manager'
] 