#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Moduł monitorujący wydajność modeli AI.

Ten moduł jest odpowiedzialny za:
- Śledzenie użycia modeli AI
- Analizę wydajności poszczególnych modeli
- Generowanie alertów dotyczących anomalii
- Optymalizację kosztów operacyjnych API
"""

import os
import json
import time
import threading
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from enum import Enum
from dataclasses import dataclass
import pandas as pd
import numpy as np

# Importy wewnętrzne
try:
    from src.database.ai_usage_repository import AIUsageRepository, get_ai_usage_repository
    from src.monitoring.alert_manager import AlertManager, AlertType, AlertPriority, get_alert_manager
except ImportError:
    try:
        from database.ai_usage_repository import AIUsageRepository, get_ai_usage_repository
        from monitoring.alert_manager import AlertManager, AlertType, AlertPriority, get_alert_manager
    except ImportError:
        # Dla testów jednostkowych
        class AlertType(Enum):
            AI_ERROR = "ai_error"
            AI_PERFORMANCE = "ai_performance"
            AI_USAGE = "ai_usage"
            AI_COST = "ai_cost"
        
        class AlertPriority(Enum):
            LOW = "low"
            MEDIUM = "medium"
            HIGH = "high"


@dataclass
class AIModelUsage:
    """Dane o użyciu modelu AI."""
    model_name: str
    timestamp: datetime
    request_type: str
    tokens_input: int
    tokens_output: int
    duration_ms: int
    success: bool
    error_message: Optional[str] = None
    cost: float = 0.0
    signal_generated: bool = False
    decision_quality: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Konwersja do słownika."""
        return {
            'model_name': self.model_name,
            'timestamp': self.timestamp.isoformat(),
            'request_type': self.request_type,
            'tokens_input': self.tokens_input,
            'tokens_output': self.tokens_output,
            'duration_ms': self.duration_ms,
            'success': self.success,
            'error_message': self.error_message,
            'cost': self.cost,
            'signal_generated': self.signal_generated,
            'decision_quality': self.decision_quality
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AIModelUsage':
        """Tworzenie obiektu z słownika."""
        if isinstance(data['timestamp'], str):
            data['timestamp'] = datetime.fromisoformat(data['timestamp'])
        return cls(**data)


class AIMonitor:
    """
    Klasa odpowiedzialna za monitorowanie wydajności modeli AI.
    
    Ta klasa śledzi użycie modeli AI, analizuje ich wydajność,
    generuje alerty dotyczące anomalii i optymalizuje koszty operacyjne API.
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        """Implementacja wzorca Singleton."""
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(AIMonitor, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance
    
    def __init__(self):
        """Inicjalizacja monitora AI."""
        if self._initialized:
            return
            
        self.logger = logging.getLogger('trading_agent.monitoring.ai')
        self.logger.info("Inicjalizacja AIMonitor")
        
        # Inicjalizacja komponentów
        try:
            self.ai_usage_repository = get_ai_usage_repository()
            self.alert_manager = get_alert_manager()
        except Exception as e:
            self.logger.error(f"Błąd podczas inicjalizacji komponentów: {e}")
            raise
        
        # Konfiguracja
        self.cost_thresholds = {
            'claude': 5.0,    # dzienny limit kosztów dla Claude (USD)
            'grok': 3.0,      # dzienny limit kosztów dla Grok (USD)
            'deepseek': 2.0   # dzienny limit kosztów dla DeepSeek (USD)
        }
        
        # Buforowanie danych
        self.usage_buffer = []
        self.buffer_lock = threading.Lock()
        self.max_buffer_size = 100
        
        # Analiza wydajności
        self.model_performance = {}
        self.performance_history = []
        
        # Flagi stanu
        self._running = False
        self._analysis_thread = None
        
        # Uruchom wątek analizy
        self._running = True
        self._analysis_thread = threading.Thread(target=self._analysis_loop, daemon=True)
        self._analysis_thread.start()
        
        self._initialized = True
    
    def record_usage(self, usage: AIModelUsage) -> None:
        """
        Zapisuje informacje o użyciu modelu AI.
        
        Args:
            usage: Obiekt AIModelUsage z danymi o użyciu
        """
        try:
            # Dodaj do bufora
            with self.buffer_lock:
                self.usage_buffer.append(usage)
                
                # Jeśli bufor jest pełny, zapisz do bazy danych
                if len(self.usage_buffer) >= self.max_buffer_size:
                    self._flush_buffer()
            
            # Aktualizuj statystyki wydajności w czasie rzeczywistym
            self._update_performance_stats(usage)
            
            # Sprawdź anomalie i przekroczenia kosztów
            self._check_for_anomalies(usage)
            self._check_cost_thresholds(usage.model_name)
            
        except Exception as e:
            self.logger.error(f"Błąd podczas rejestrowania użycia AI: {e}")
    
    def _flush_buffer(self) -> None:
        """Zapisuje bufor do bazy danych."""
        with self.buffer_lock:
            if not self.usage_buffer:
                return
                
            try:
                # Zapisz do bazy danych
                for usage in self.usage_buffer:
                    self.ai_usage_repository.insert_usage(usage.to_dict())
                
                self.logger.debug(f"Zapisano {len(self.usage_buffer)} rekordów użycia AI do bazy danych")
                self.usage_buffer.clear()
            except Exception as e:
                self.logger.error(f"Błąd podczas zapisywania bufora do bazy danych: {e}")
    
    def _analysis_loop(self) -> None:
        """Główna pętla analizy wydajności modeli AI."""
        self.logger.info("Uruchomiono wątek analizy wydajności AI")
        
        while self._running:
            try:
                # Zapisz bufor co jakiś czas
                self._flush_buffer()
                
                # Wykonaj analizę wydajności modeli
                self._analyze_model_performance()
                
                # Generuj raport dzienny (o północy)
                current_time = datetime.now()
                if current_time.hour == 0 and current_time.minute < 5:
                    self._generate_daily_report()
                
                # Sprawdź koszty dla wszystkich modeli
                self._check_all_costs()
                
            except Exception as e:
                self.logger.error(f"Błąd w pętli analizy AI: {e}")
            
            # Interwał snu
            time.sleep(60)  # Sprawdzaj co minutę
    
    def _update_performance_stats(self, usage: AIModelUsage) -> None:
        """
        Aktualizuje statystyki wydajności modelu AI.
        
        Args:
            usage: Dane o użyciu modelu AI
        """
        model = usage.model_name
        
        if model not in self.model_performance:
            self.model_performance[model] = {
                'requests_count': 0,
                'success_rate': 0.0,
                'avg_tokens_input': 0.0,
                'avg_tokens_output': 0.0,
                'avg_duration_ms': 0.0,
                'total_cost': 0.0,
                'signal_rate': 0.0,
                'avg_decision_quality': 0.0,
                'last_updated': datetime.now()
            }
        
        stats = self.model_performance[model]
        count = stats['requests_count']
        
        # Aktualizacja statystyk z wagami
        stats['requests_count'] += 1
        stats['success_rate'] = (stats['success_rate'] * count + usage.success) / (count + 1)
        stats['avg_tokens_input'] = (stats['avg_tokens_input'] * count + usage.tokens_input) / (count + 1)
        stats['avg_tokens_output'] = (stats['avg_tokens_output'] * count + usage.tokens_output) / (count + 1)
        stats['avg_duration_ms'] = (stats['avg_duration_ms'] * count + usage.duration_ms) / (count + 1)
        stats['total_cost'] += usage.cost
        stats['signal_rate'] = (stats['signal_rate'] * count + usage.signal_generated) / (count + 1)
        
        if usage.decision_quality is not None:
            decision_quality_count = count * stats['signal_rate']
            if decision_quality_count > 0:
                stats['avg_decision_quality'] = (stats['avg_decision_quality'] * decision_quality_count + usage.decision_quality) / (decision_quality_count + usage.signal_generated)
        
        stats['last_updated'] = datetime.now()
    
    def _analyze_model_performance(self) -> None:
        """Analizuje wydajność modeli AI na podstawie zgromadzonych danych."""
        try:
            # Pobierz dane z ostatnich 24 godzin
            end_time = datetime.now()
            start_time = end_time - timedelta(hours=24)
            
            usages = self.ai_usage_repository.get_usage_in_timeframe(start_time, end_time)
            if not usages:
                return
            
            # Przekształć na DataFrame
            df = pd.DataFrame([AIModelUsage.from_dict(u).to_dict() for u in usages])
            
            # Analizuj po modelach
            models = df['model_name'].unique()
            
            for model in models:
                model_df = df[df['model_name'] == model]
                
                # Wylicz metryki
                success_rate = model_df['success'].mean() * 100
                avg_duration = model_df['duration_ms'].mean()
                total_cost = model_df['cost'].sum()
                signal_rate = model_df['signal_generated'].mean() * 100
                
                quality_df = model_df[model_df['decision_quality'].notnull()]
                avg_quality = quality_df['decision_quality'].mean() if not quality_df.empty else 0
                
                # Zapisz do historii
                self.performance_history.append({
                    'model': model,
                    'timestamp': datetime.now(),
                    'success_rate': success_rate,
                    'avg_duration_ms': avg_duration,
                    'total_cost_24h': total_cost,
                    'signal_rate': signal_rate,
                    'avg_decision_quality': avg_quality
                })
                
                # Generuj alerty dla anomalii
                if success_rate < 80:
                    self._create_alert(
                        f"Niska skuteczność modelu {model}: {success_rate:.1f}%",
                        AlertType.AI_PERFORMANCE,
                        AlertPriority.MEDIUM
                    )
                
                if avg_duration > 5000:  # powyżej 5 sekund
                    self._create_alert(
                        f"Wysoki czas odpowiedzi modelu {model}: {avg_duration:.0f}ms",
                        AlertType.AI_PERFORMANCE,
                        AlertPriority.LOW
                    )
                
                # Przytnij historię
                if len(self.performance_history) > 1000:
                    self.performance_history = self.performance_history[-1000:]
                
        except Exception as e:
            self.logger.error(f"Błąd podczas analizy wydajności modeli AI: {e}")
    
    def _check_for_anomalies(self, usage: AIModelUsage) -> None:
        """
        Sprawdza anomalie w użyciu modelu AI.
        
        Args:
            usage: Dane o użyciu modelu AI
        """
        # Sprawdź błędy
        if not usage.success:
            self._create_alert(
                f"Błąd modelu {usage.model_name}: {usage.error_message}",
                AlertType.AI_ERROR,
                AlertPriority.HIGH
            )
        
        # Sprawdź czas odpowiedzi
        if usage.duration_ms > 10000:  # powyżej 10 sekund
            self._create_alert(
                f"Bardzo długi czas odpowiedzi modelu {usage.model_name}: {usage.duration_ms}ms",
                AlertType.AI_PERFORMANCE,
                AlertPriority.MEDIUM
            )
        
        # Sprawdź zużycie tokenów
        if usage.tokens_input > 5000:  # duże wejście
            self._create_alert(
                f"Duże zużycie tokenów wejściowych przez {usage.model_name}: {usage.tokens_input}",
                AlertType.AI_USAGE,
                AlertPriority.LOW
            )
    
    def _check_cost_thresholds(self, model_name: str) -> None:
        """
        Sprawdza, czy koszty modelu nie przekraczają progów.
        
        Args:
            model_name: Nazwa modelu do sprawdzenia
        """
        if model_name not in self.cost_thresholds:
            return
            
        threshold = self.cost_thresholds[model_name]
        
        # Pobierz koszty z dzisiaj
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        today_costs = self.ai_usage_repository.get_daily_cost(model_name, today)
        
        if today_costs > threshold:
            self._create_alert(
                f"Przekroczono dzienny limit kosztów dla modelu {model_name}: ${today_costs:.2f} / ${threshold:.2f}",
                AlertType.AI_COST,
                AlertPriority.HIGH
            )
            
        # Alert przy 80% limitu
        elif today_costs > threshold * 0.8:
            self._create_alert(
                f"Zbliżamy się do dziennego limitu kosztów dla modelu {model_name}: ${today_costs:.2f} / ${threshold:.2f}",
                AlertType.AI_COST,
                AlertPriority.MEDIUM
            )
    
    def _check_all_costs(self) -> None:
        """Sprawdza koszty dla wszystkich modeli."""
        for model in self.cost_thresholds:
            self._check_cost_thresholds(model)
    
    def _create_alert(self, message: str, alert_type: AlertType, priority: AlertPriority) -> None:
        """
        Tworzy alert w systemie monitoringu.
        
        Args:
            message: Treść alertu
            alert_type: Typ alertu
            priority: Priorytet alertu
        """
        try:
            self.alert_manager.create_alert(
                message=message,
                alert_type=alert_type,
                priority=priority,
                source="AI Monitor"
            )
        except Exception as e:
            self.logger.error(f"Błąd podczas tworzenia alertu: {e}")
    
    def _generate_daily_report(self) -> Dict[str, Any]:
        """
        Generuje dzienny raport wydajności modeli AI.
        
        Returns:
            Dict z raportem dziennym
        """
        yesterday = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=1)
        
        try:
            # Pobierz dane z wczoraj
            usages = self.ai_usage_repository.get_usage_in_timeframe(
                yesterday, 
                yesterday + timedelta(days=1)
            )
            
            if not usages:
                self.logger.warning("Brak danych do raportu dziennego AI")
                return {}
            
            # Przekształć na DataFrame
            df = pd.DataFrame([AIModelUsage.from_dict(u).to_dict() for u in usages])
            
            # Metryki zagregowane
            total_requests = len(df)
            total_cost = df['cost'].sum()
            success_rate = df['success'].mean() * 100
            
            # Metryki per model
            models_data = {}
            for model in df['model_name'].unique():
                model_df = df[df['model_name'] == model]
                
                models_data[model] = {
                    'requests': len(model_df),
                    'cost': model_df['cost'].sum(),
                    'success_rate': model_df['success'].mean() * 100,
                    'avg_tokens_input': model_df['tokens_input'].mean(),
                    'avg_tokens_output': model_df['tokens_output'].mean(),
                    'avg_duration_ms': model_df['duration_ms'].mean(),
                    'signal_rate': model_df['signal_generated'].mean() * 100,
                }
                
                # Jakość decyzji tylko dla wierszy z wartościami
                quality_df = model_df[model_df['decision_quality'].notnull()]
                if not quality_df.empty:
                    models_data[model]['avg_decision_quality'] = quality_df['decision_quality'].mean()
                else:
                    models_data[model]['avg_decision_quality'] = 0
            
            # Utwórz raport
            report = {
                'date': yesterday.date().isoformat(),
                'generated_at': datetime.now().isoformat(),
                'total_requests': total_requests,
                'total_cost': total_cost,
                'overall_success_rate': success_rate,
                'models': models_data
            }
            
            # Zapisz raport
            report_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                'logs',
                'ai_reports'
            )
            os.makedirs(report_path, exist_ok=True)
            
            report_file = os.path.join(report_path, f"ai_report_{yesterday.date().isoformat()}.json")
            with open(report_file, 'w') as f:
                json.dump(report, f, indent=2)
            
            self.logger.info(f"Wygenerowano dzienny raport AI: {report_file}")
            return report
            
        except Exception as e:
            self.logger.error(f"Błąd podczas generowania dziennego raportu AI: {e}")
            return {}
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """
        Zwraca podsumowanie wydajności modeli AI.
        
        Returns:
            Dict z podsumowaniem wydajności modeli
        """
        return {
            'current_stats': self.model_performance,
            'history': self.performance_history[-50:] if self.performance_history else []
        }
    
    def stop(self) -> None:
        """Zatrzymuje monitor AI."""
        self._running = False
        
        if self._analysis_thread and self._analysis_thread.is_alive():
            self._analysis_thread.join(timeout=5.0)
        
        # Zapisz pozostałe dane w buforze
        self._flush_buffer()
        
        self.logger.info("AIMonitor zatrzymany")


def get_ai_monitor() -> AIMonitor:
    """
    Zwraca instancję AIMonitor (Singleton).
    
    Returns:
        Instancja AIMonitor
    """
    return AIMonitor() 