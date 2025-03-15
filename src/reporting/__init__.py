#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Moduł reporting - odpowiada za generowanie raportów o skuteczności sygnałów handlowych,
statystyki dotyczące handlu oraz inne analizy związane z wydajnością systemu AgentMT5.
"""

from src.reporting.signal_performance_reporter import SignalPerformanceReporter
from src.reporting.report_generator import ReportGenerator
from src.reporting.signal_statistics import SignalStatistics

__all__ = [
    'SignalPerformanceReporter',
    'ReportGenerator',
    'SignalStatistics'
] 