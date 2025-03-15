#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
SignalPerformanceReporter - klasa odpowiedzialna za raportowanie 
wydajności sygnałów handlowych w systemie AgentMT5.
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta

from src.reporting.signal_statistics import SignalStatistics, TimeFrame
from src.reporting.report_generator import ReportGenerator, ReportType, ReportFormat

logger = logging.getLogger(__name__)

class PerformanceReportSchedule:
    """Harmonogram generowania raportów wydajności."""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    ON_DEMAND = "on_demand"

class SignalPerformanceReporter:
    """
    Klasa do automatycznego raportowania wydajności sygnałów handlowych.
    Umożliwia zaplanowanie regularnych raportów oraz generowanie raportów na żądanie.
    """
    
    def __init__(self):
        """Inicjalizacja reportera wydajności sygnałów."""
        self.signal_statistics = SignalStatistics.get_instance()
        self.report_generator = ReportGenerator.get_instance()
        self.schedule = {}
        self.last_report_time = {}
    
    def schedule_report(self, 
                      report_type: str = ReportType.SUMMARY,
                      report_format: str = ReportFormat.HTML,
                      schedule: str = PerformanceReportSchedule.WEEKLY,
                      symbol: Optional[str] = None,
                      timeframe: Optional[str] = None) -> bool:
        """
        Planuje automatyczne generowanie raportów wydajności.
        
        Args:
            report_type: Typ raportu
            report_format: Format raportu
            schedule: Harmonogram (dzienny, tygodniowy, miesięczny, na żądanie)
            symbol: Symbol instrumentu (opcjonalny)
            timeframe: Interwał czasowy (opcjonalny)
            
        Returns:
            bool: True, jeśli zaplanowano pomyślnie, False w przeciwnym razie
        """
        key = f"{report_type}_{symbol}_{timeframe}"
        self.schedule[key] = {
            "report_type": report_type,
            "report_format": report_format,
            "schedule": schedule,
            "symbol": symbol,
            "timeframe": timeframe
        }
        self.last_report_time[key] = None
        logger.info(f"Zaplanowano raport {report_type} dla {symbol if symbol else 'wszystkich instrumentów'} "
                    f"z harmonogramem {schedule}")
        return True
    
    def unschedule_report(self, 
                        report_type: str,
                        symbol: Optional[str] = None,
                        timeframe: Optional[str] = None) -> bool:
        """
        Anuluje zaplanowane automatyczne generowanie raportów.
        
        Args:
            report_type: Typ raportu
            symbol: Symbol instrumentu (opcjonalny)
            timeframe: Interwał czasowy (opcjonalny)
            
        Returns:
            bool: True, jeśli anulowano pomyślnie, False w przeciwnym razie
        """
        key = f"{report_type}_{symbol}_{timeframe}"
        if key in self.schedule:
            del self.schedule[key]
            if key in self.last_report_time:
                del self.last_report_time[key]
            logger.info(f"Anulowano zaplanowany raport {report_type} dla {symbol if symbol else 'wszystkich instrumentów'}")
            return True
        return False
    
    def generate_scheduled_reports(self) -> List[str]:
        """
        Generuje wszystkie zaplanowane raporty, które powinny być wykonane.
        
        Returns:
            List[str]: Lista ścieżek do wygenerowanych raportów
        """
        now = datetime.now()
        reports_generated = []
        
        for key, config in self.schedule.items():
            last_time = self.last_report_time.get(key)
            
            if self._should_generate_report(config["schedule"], last_time):
                # Ustalenie zakresu dat dla raportu
                if config["schedule"] == PerformanceReportSchedule.DAILY:
                    start_date = now - timedelta(days=1)
                elif config["schedule"] == PerformanceReportSchedule.WEEKLY:
                    start_date = now - timedelta(days=7)
                elif config["schedule"] == PerformanceReportSchedule.MONTHLY:
                    start_date = now - timedelta(days=30)
                else:
                    # Dla raportów na żądanie, użyj ostatnich 30 dni
                    start_date = now - timedelta(days=30)
                
                # Generowanie raportu
                report_path = self.report_generator.generate_report(
                    report_type=config["report_type"],
                    report_format=config["report_format"],
                    symbol=config["symbol"],
                    timeframe=config["timeframe"],
                    start_date=start_date,
                    end_date=now
                )
                
                # Aktualizacja czasu ostatniego raportu
                self.last_report_time[key] = now
                reports_generated.append(report_path)
                
                logger.info(f"Wygenerowano zaplanowany raport: {report_path}")
        
        return reports_generated
    
    def generate_report_on_demand(self,
                                report_type: str = ReportType.SUMMARY,
                                report_format: str = ReportFormat.HTML,
                                symbol: Optional[str] = None,
                                timeframe: Optional[str] = None,
                                start_date: Optional[datetime] = None,
                                end_date: Optional[datetime] = None) -> str:
        """
        Generuje raport na żądanie.
        
        Args:
            report_type: Typ raportu
            report_format: Format raportu
            symbol: Symbol instrumentu (opcjonalny)
            timeframe: Interwał czasowy (opcjonalny)
            start_date: Data początkowa (opcjonalna)
            end_date: Data końcowa (opcjonalna)
            
        Returns:
            str: Ścieżka do wygenerowanego raportu
        """
        return self.report_generator.generate_report(
            report_type=report_type,
            report_format=report_format,
            symbol=symbol,
            timeframe=timeframe,
            start_date=start_date,
            end_date=end_date
        )
    
    def generate_performance_chart_on_demand(self,
                                          symbol: Optional[str] = None,
                                          timeframe: Optional[str] = None,
                                          start_date: Optional[datetime] = None,
                                          end_date: Optional[datetime] = None) -> str:
        """
        Generuje wykres wydajności na żądanie.
        
        Args:
            symbol: Symbol instrumentu (opcjonalny)
            timeframe: Interwał czasowy (opcjonalny)
            start_date: Data początkowa (opcjonalna)
            end_date: Data końcowa (opcjonalna)
            
        Returns:
            str: Ścieżka do wygenerowanego wykresu
        """
        return self.report_generator.generate_performance_chart(
            symbol=symbol,
            timeframe=timeframe,
            start_date=start_date,
            end_date=end_date
        )
    
    def _should_generate_report(self, schedule: str, last_time: Optional[datetime]) -> bool:
        """
        Sprawdza, czy należy wygenerować raport na podstawie harmonogramu i ostatniego czasu generowania.
        
        Args:
            schedule: Harmonogram raportu
            last_time: Ostatni czas wygenerowania raportu
            
        Returns:
            bool: True, jeśli raport powinien być wygenerowany, False w przeciwnym razie
        """
        if last_time is None:
            return True
        
        now = datetime.now()
        
        if schedule == PerformanceReportSchedule.DAILY:
            # Sprawdzenie, czy od ostatniego raportu minął cały dzień
            return (now.date() - last_time.date()).days >= 1
        
        elif schedule == PerformanceReportSchedule.WEEKLY:
            # Sprawdzenie, czy od ostatniego raportu minął tydzień
            return (now - last_time).days >= 7
        
        elif schedule == PerformanceReportSchedule.MONTHLY:
            # Sprawdzenie, czy od ostatniego raportu minął miesiąc
            if now.month != last_time.month or now.year != last_time.year:
                return True
            return False
        
        elif schedule == PerformanceReportSchedule.ON_DEMAND:
            # Raporty na żądanie nie są generowane automatycznie
            return False
        
        # Domyślnie nie generuj raportu
        return False

def get_signal_performance_reporter() -> SignalPerformanceReporter:
    """
    Tworzy nową instancję SignalPerformanceReporter.
    
    Returns:
        SignalPerformanceReporter: Nowa instancja klasy
    """
    return SignalPerformanceReporter() 