#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
ReportGenerator - klasa odpowiedzialna za generowanie raportów o skuteczności
sygnałów handlowych w systemie AgentMT5.
"""

import logging
import os
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple, Union
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from jinja2 import Environment, FileSystemLoader

from src.reporting.signal_statistics import SignalStatistics, TimeFrame
from src.utils.config_manager import get_config
from src.utils.path_utils import get_project_root

logger = logging.getLogger(__name__)

class ReportFormat:
    """Formaty dostępnych raportów."""
    HTML = "html"
    PDF = "pdf"
    MARKDOWN = "markdown"
    CSV = "csv"

class ReportType:
    """Typy dostępnych raportów."""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    CUSTOM = "custom"
    PERFORMANCE = "performance"
    SUMMARY = "summary"
    DETAILED = "detailed"

class ReportGenerator:
    """
    Klasa do generowania raportów na podstawie statystyk sygnałów handlowych.
    Wykorzystuje dane z klasy SignalStatistics do tworzenia raportów w różnych formatach.
    """
    
    _instance = None
    _lock = threading.Lock()
    
    @classmethod
    def get_instance(cls) -> 'ReportGenerator':
        """
        Singleton pattern - zwraca istniejącą instancję klasy lub tworzy nową.
        
        Returns:
            ReportGenerator: Instancja klasy ReportGenerator
        """
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
        return cls._instance
    
    def __init__(self):
        """
        Inicjalizacja generatora raportów.
        """
        self.signal_statistics = SignalStatistics.get_instance()
        self.config = get_config()
        self.template_dir = os.path.join(get_project_root(), 'templates', 'reports')
        self.output_dir = os.path.join(get_project_root(), 'reports')
        
        # Utworzenie katalogu na raporty, jeśli nie istnieje
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Inicjalizacja środowiska szablonów Jinja2
        self.jinja_env = Environment(
            loader=FileSystemLoader(self.template_dir),
            trim_blocks=True,
            lstrip_blocks=True
        )
    
    def generate_report(self, 
                      report_type: str = ReportType.SUMMARY,
                      report_format: str = ReportFormat.HTML,
                      symbol: Optional[str] = None,
                      timeframe: Optional[str] = None,
                      start_date: Optional[datetime] = None,
                      end_date: Optional[datetime] = None) -> str:
        """
        Generuje raport na podstawie podanych parametrów.
        
        Args:
            report_type: Typ raportu (dzienny, tygodniowy, miesięczny, niestandardowy)
            report_format: Format raportu (HTML, PDF, Markdown, CSV)
            symbol: Symbol instrumentu (opcjonalny)
            timeframe: Interwał czasowy (opcjonalny)
            start_date: Data początkowa dla raportu (opcjonalna)
            end_date: Data końcowa dla raportu (opcjonalna)
            
        Returns:
            str: Ścieżka do wygenerowanego pliku raportu
        """
        # Ustalenie dat na podstawie typu raportu, jeśli nie podano
        if start_date is None or end_date is None:
            start_date, end_date = self._get_date_range_for_report_type(report_type)
        
        # Pobranie danych z SignalStatistics
        report_data = self._collect_report_data(
            report_type, symbol, timeframe, start_date, end_date
        )
        
        # Generowanie raportu w odpowiednim formacie
        if report_format == ReportFormat.HTML:
            return self._generate_html_report(report_type, report_data)
        elif report_format == ReportFormat.PDF:
            return self._generate_pdf_report(report_type, report_data)
        elif report_format == ReportFormat.MARKDOWN:
            return self._generate_markdown_report(report_type, report_data)
        elif report_format == ReportFormat.CSV:
            return self._generate_csv_report(report_type, report_data)
        else:
            raise ValueError(f"Nieobsługiwany format raportu: {report_format}")
    
    def _collect_report_data(self, 
                          report_type: str,
                          symbol: Optional[str],
                          timeframe: Optional[str],
                          start_date: Optional[datetime],
                          end_date: Optional[datetime]) -> Dict[str, Any]:
        """
        Zbiera dane potrzebne do wygenerowania raportu.
        
        Args:
            report_type: Typ raportu
            symbol: Symbol instrumentu (opcjonalny)
            timeframe: Interwał czasowy (opcjonalny)
            start_date: Data początkowa
            end_date: Data końcowa
            
        Returns:
            Dict[str, Any]: Słownik z danymi do raportu
        """
        data = {
            'report_type': report_type,
            'generation_time': datetime.now(),
            'start_date': start_date,
            'end_date': end_date,
            'symbol': symbol,
            'timeframe': timeframe,
        }
        
        # Pobieranie statystyk sygnałów
        data['statistics'] = self.signal_statistics.get_signal_statistics(
            symbol=symbol, 
            timeframe=timeframe,
            start_date=start_date,
            end_date=end_date
        )
        
        # Pobieranie rozkładu wyników sygnałów
        data['outcome_distribution'] = self.signal_statistics.get_signal_outcome_distribution(
            symbol=symbol,
            timeframe=timeframe,
            start_date=start_date,
            end_date=end_date
        )
        
        # Pobieranie korelacji między pewnością a skutecznością
        data['confidence_performance'] = self.signal_statistics.get_confidence_vs_performance(
            symbol=symbol,
            timeframe=timeframe,
            start_date=start_date,
            end_date=end_date
        )
        
        # Dla raportów szczegółowych dodajemy także analizę czasową
        if report_type in [ReportType.DETAILED, ReportType.PERFORMANCE]:
            period = TimeFrame.DAY if report_type == ReportType.DETAILED else TimeFrame.WEEK
            data['time_series'] = self.signal_statistics.get_time_series_performance(
                symbol=symbol,
                timeframe=timeframe,
                period=period
            )
        
        return data
    
    def _get_date_range_for_report_type(self, report_type: str) -> Tuple[datetime, datetime]:
        """
        Zwraca zakres dat na podstawie typu raportu.
        
        Args:
            report_type: Typ raportu
            
        Returns:
            Tuple[datetime, datetime]: Krotka (data_początkowa, data_końcowa)
        """
        now = datetime.now()
        if report_type == ReportType.DAILY:
            # Raport dzienny - ostatnie 24 godziny
            return now - timedelta(days=1), now
        elif report_type == ReportType.WEEKLY:
            # Raport tygodniowy - ostatnie 7 dni
            return now - timedelta(days=7), now
        elif report_type == ReportType.MONTHLY:
            # Raport miesięczny - ostatnie 30 dni
            return now - timedelta(days=30), now
        else:
            # Domyślnie - ostatnie 30 dni
            return now - timedelta(days=30), now
    
    def _generate_html_report(self, report_type: str, report_data: Dict[str, Any]) -> str:
        """
        Generuje raport w formacie HTML.
        
        Args:
            report_type: Typ raportu
            report_data: Dane do raportu
            
        Returns:
            str: Ścieżka do wygenerowanego pliku HTML
        """
        template_name = f"{report_type}_template.html"
        try:
            template = self.jinja_env.get_template(template_name)
        except:
            # Jeśli brak szablonu, użyj domyślnego
            logger.warning(f"Nie znaleziono szablonu {template_name}. Używanie domyślnego.")
            template = self.jinja_env.get_template("default_template.html")
        
        # Generowanie zawartości HTML
        html_content = template.render(**report_data)
        
        # Zapisywanie do pliku
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        symbol_str = report_data['symbol'] if report_data['symbol'] else "all"
        filename = f"report_{report_type}_{symbol_str}_{timestamp}.html"
        output_path = os.path.join(self.output_dir, filename)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        logger.info(f"Wygenerowano raport HTML: {output_path}")
        return output_path
    
    def _generate_pdf_report(self, report_type: str, report_data: Dict[str, Any]) -> str:
        """
        Generuje raport w formacie PDF.
        
        Args:
            report_type: Typ raportu
            report_data: Dane do raportu
            
        Returns:
            str: Ścieżka do wygenerowanego pliku PDF
        """
        # Najpierw wygeneruj HTML, a następnie konwertuj do PDF
        html_path = self._generate_html_report(report_type, report_data)
        
        try:
            import weasyprint
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            symbol_str = report_data['symbol'] if report_data['symbol'] else "all"
            filename = f"report_{report_type}_{symbol_str}_{timestamp}.pdf"
            output_path = os.path.join(self.output_dir, filename)
            
            pdf = weasyprint.HTML(filename=html_path).write_pdf()
            with open(output_path, 'wb') as f:
                f.write(pdf)
            
            logger.info(f"Wygenerowano raport PDF: {output_path}")
            return output_path
        except ImportError:
            logger.error("Nie można wygenerować PDF - biblioteka weasyprint nie jest zainstalowana")
            return html_path
    
    def _generate_markdown_report(self, report_type: str, report_data: Dict[str, Any]) -> str:
        """
        Generuje raport w formacie Markdown.
        
        Args:
            report_type: Typ raportu
            report_data: Dane do raportu
            
        Returns:
            str: Ścieżka do wygenerowanego pliku Markdown
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        symbol_str = report_data['symbol'] if report_data['symbol'] else "all"
        filename = f"report_{report_type}_{symbol_str}_{timestamp}.md"
        output_path = os.path.join(self.output_dir, filename)
        
        stats = report_data['statistics']
        
        with open(output_path, 'w', encoding='utf-8') as f:
            # Nagłówek
            f.write(f"# Raport {report_type} - {symbol_str}\n\n")
            f.write(f"*Wygenerowano: {report_data['generation_time']}*\n\n")
            f.write(f"Okres: {report_data['start_date']} - {report_data['end_date']}\n\n")
            
            # Podstawowe statystyki
            f.write("## Podsumowanie statystyk\n\n")
            f.write(f"- Liczba sygnałów: {stats['total_signals']}\n")
            f.write(f"- Skuteczność: {stats['success_rate']:.2f}%\n")
            f.write(f"- Średni zysk: {stats['avg_profit']:.2f}%\n")
            f.write(f"- Średnia strata: {stats['avg_loss']:.2f}%\n")
            f.write(f"- Stosunek zysku do straty: {stats['profit_loss_ratio']:.2f}\n")
            f.write(f"- Średni czas trwania pozycji: {stats['avg_position_duration']}\n\n")
            
            # Rozkład wyników
            f.write("## Rozkład wyników sygnałów\n\n")
            f.write("| Wynik | Procent |\n")
            f.write("|-------|--------|\n")
            for outcome, percentage in report_data['outcome_distribution'].items():
                f.write(f"| {outcome} | {percentage:.2f}% |\n")
            f.write("\n")
            
            # Korelacja pewności i skuteczności
            f.write("## Korelacja pewności i skuteczności\n\n")
            f.write("| Poziom pewności | Skuteczność |\n")
            f.write("|----------------|------------|\n")
            for confidence, performance in report_data['confidence_performance'].items():
                f.write(f"| {confidence:.2f} | {performance:.2f}% |\n")
            f.write("\n")
            
            # Analiza czasowa (jeśli dostępna)
            if 'time_series' in report_data:
                f.write("## Analiza czasowa\n\n")
                f.write("| Data | Liczba sygnałów | Skuteczność | Zysk |\n")
                f.write("|------|----------------|-------------|------|\n")
                dates = report_data['time_series']['dates']
                signals = report_data['time_series']['signals']
                rates = report_data['time_series']['success_rates']
                profits = report_data['time_series']['profits']
                
                for i in range(len(dates)):
                    f.write(f"| {dates[i]} | {signals[i]} | {rates[i]:.2f}% | {profits[i]:.2f}% |\n")
        
        logger.info(f"Wygenerowano raport Markdown: {output_path}")
        return output_path
    
    def _generate_csv_report(self, report_type: str, report_data: Dict[str, Any]) -> str:
        """
        Generuje raport w formacie CSV.
        
        Args:
            report_type: Typ raportu
            report_data: Dane do raportu
            
        Returns:
            str: Ścieżka do wygenerowanego pliku CSV
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        symbol_str = report_data['symbol'] if report_data['symbol'] else "all"
        filename = f"report_{report_type}_{symbol_str}_{timestamp}.csv"
        output_path = os.path.join(self.output_dir, filename)
        
        # Tworzenie DataFrame z danymi raportu
        if 'time_series' in report_data:
            # Dla raportów z danymi czasowymi
            df = pd.DataFrame({
                'date': report_data['time_series']['dates'],
                'signals': report_data['time_series']['signals'],
                'success_rate': report_data['time_series']['success_rates'],
                'profit': report_data['time_series']['profits']
            })
        else:
            # Dla raportów podsumowujących
            stats = report_data['statistics']
            outcomes = report_data['outcome_distribution']
            
            df = pd.DataFrame({
                'metric': [
                    'total_signals', 'success_rate', 'avg_profit', 'avg_loss', 'profit_loss_ratio'
                ] + [f"outcome_{k}" for k in outcomes.keys()],
                'value': [
                    stats['total_signals'], stats['success_rate'], stats['avg_profit'], 
                    stats['avg_loss'], stats['profit_loss_ratio']
                ] + list(outcomes.values())
            })
        
        # Zapisywanie do pliku CSV
        df.to_csv(output_path, index=False)
        
        logger.info(f"Wygenerowano raport CSV: {output_path}")
        return output_path
    
    def generate_performance_chart(self, 
                                symbol: Optional[str] = None,
                                timeframe: Optional[str] = None,
                                start_date: Optional[datetime] = None,
                                end_date: Optional[datetime] = None) -> str:
        """
        Generuje wykres wydajności sygnałów.
        
        Args:
            symbol: Symbol instrumentu (opcjonalny)
            timeframe: Interwał czasowy (opcjonalny)
            start_date: Data początkowa (opcjonalna)
            end_date: Data końcowa (opcjonalna)
            
        Returns:
            str: Ścieżka do wygenerowanego pliku wykresu
        """
        # Pobranie danych czasowych
        time_series = self.signal_statistics.get_time_series_performance(
            symbol=symbol,
            timeframe=timeframe,
            period=TimeFrame.DAY
        )
        
        # Utworzenie wykresu
        plt.figure(figsize=(12, 8))
        fig, ax1 = plt.subplots()
        
        # Wykres skuteczności
        color = 'tab:blue'
        ax1.set_xlabel('Data')
        ax1.set_ylabel('Skuteczność (%)', color=color)
        ax1.plot(time_series['dates'], time_series['success_rates'], color=color)
        ax1.tick_params(axis='y', labelcolor=color)
        
        # Drugi wykres - zysk
        ax2 = ax1.twinx()
        color = 'tab:red'
        ax2.set_ylabel('Zysk (%)', color=color)
        ax2.plot(time_series['dates'], time_series['profits'], color=color)
        ax2.tick_params(axis='y', labelcolor=color)
        
        # Tytuł i siatka
        symbol_str = symbol if symbol else "wszystkie instrumenty"
        plt.title(f'Wydajność sygnałów - {symbol_str}')
        plt.grid(True)
        
        # Zapisywanie wykresu
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"performance_chart_{symbol_str}_{timestamp}.png"
        output_path = os.path.join(self.output_dir, filename)
        plt.savefig(output_path)
        
        logger.info(f"Wygenerowano wykres wydajności: {output_path}")
        return output_path

def get_report_generator() -> ReportGenerator:
    """
    Zwraca instancję ReportGenerator (singleton).
    
    Returns:
        ReportGenerator: Instancja klasy ReportGenerator
    """
    return ReportGenerator.get_instance() 