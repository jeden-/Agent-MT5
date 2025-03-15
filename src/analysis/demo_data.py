#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Moduł zawierający dane demonstracyjne dla interfejsu AI Analytics.
"""

import logging
import random
from datetime import datetime, timedelta
import json
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

class AIAnalyticsDemo:
    """Klasa dostarczająca dane demonstracyjne dla panelu AI Analytics."""
    
    def __init__(self):
        """Inicjalizacja generatora danych demonstracyjnych."""
        self.models = ["Claude", "Grok", "DeepSeek"]
        self.symbols = ["EURUSD", "GBPUSD", "USDJPY", "GOLD", "US100"]
        self.timeframes = ["M5", "M15", "H1", "H4", "D1"]
        self.directions = ["BUY", "SELL"]
        self.random_seed = datetime.now().hour  # Zmieniamy seed co godzinę, żeby dane wyglądały odmiennie
        random.seed(self.random_seed)
        
    def get_ai_models_data(self) -> Dict[str, Any]:
        """
        Generuje dane demonstracyjne o wydajności modeli AI.
        
        Returns:
            Dict: Dane o wydajności modeli AI
        """
        models_data = []
        
        for model in self.models:
            accuracy = round(random.uniform(0.65, 0.92), 2)
            roi = round(random.uniform(-0.1, 0.35), 2)
            
            # Im wyższa dokładność, tym wyższe ROI (z pewną losowością)
            if accuracy > 0.85:
                roi = round(random.uniform(0.15, 0.35), 2)
            elif accuracy > 0.75:
                roi = round(random.uniform(0.05, 0.25), 2)
            
            # Obliczenie szybkości odpowiedzi (w sekundach)
            response_time = round(random.uniform(1.5, 8.5), 1)
            
            # Dodanie sztucznych danych o kosztach
            cost_per_query = round(random.uniform(0.01, 0.08), 3)
            queries_count = random.randint(50, 500)
            total_cost = round(cost_per_query * queries_count, 2)
            
            models_data.append({
                "name": model,
                "accuracy": accuracy,
                "roi": roi,
                "response_time": response_time,
                "queries_count": queries_count,
                "cost_per_query": cost_per_query,
                "total_cost": total_cost,
                "status": "active" if random.random() > 0.1 else "degraded"
            })
        
        # Sortowanie modeli według dokładności (od najlepszych)
        models_data.sort(key=lambda x: x["accuracy"], reverse=True)
        
        return {
            "status": "demo",
            "message": "Wyświetlane są dane demonstracyjne. Podłącz rzeczywiste źródła danych, aby zobaczyć aktualne wyniki.",
            "models": models_data,
            "timestamp": datetime.now().isoformat()
        }
    
    def get_ai_signals_data(self) -> Dict[str, Any]:
        """
        Generuje dane demonstracyjne o sygnałach AI.
        
        Returns:
            Dict: Dane o sygnałach AI
        """
        # Generowanie historycznych sygnałów dla analizy
        signals_count = random.randint(50, 100)
        signals = []
        
        # Data początkowa (30 dni temu)
        start_date = datetime.now() - timedelta(days=30)
        
        for i in range(signals_count):
            # Losowa data w ciągu ostatnich 30 dni
            signal_date = start_date + timedelta(
                days=random.randint(0, 30),
                hours=random.randint(0, 23),
                minutes=random.randint(0, 59)
            )
            
            # Większa szansa na nowsze sygnały
            if random.random() > 0.7:
                signal_date = datetime.now() - timedelta(
                    days=random.randint(0, 5),
                    hours=random.randint(0, 23),
                    minutes=random.randint(0, 59)
                )
            
            model = random.choice(self.models)
            symbol = random.choice(self.symbols)
            direction = random.choice(self.directions)
            timeframe = random.choice(self.timeframes)
            confidence = round(random.uniform(0.6, 0.95), 2)
            
            # Generowanie ceny wejściowej zależnej od instrumentu
            if symbol == "EURUSD":
                entry_price = round(random.uniform(1.05, 1.15), 5)
            elif symbol == "GBPUSD":
                entry_price = round(random.uniform(1.25, 1.35), 5)
            elif symbol == "USDJPY":
                entry_price = round(random.uniform(140, 150), 3)
            elif symbol == "GOLD":
                entry_price = round(random.uniform(1950, 2050), 2)
            elif symbol == "US100":
                entry_price = round(random.uniform(17000, 18500), 2)
            else:
                entry_price = round(random.uniform(1.0, 100.0), 2)
            
            # Obliczanie wyniku (profit/loss)
            if random.random() > 0.5:  # 50% szansy na zysk
                result = "profit"
                pips = round(random.uniform(10, 80), 1)
            else:
                result = "loss"
                pips = round(random.uniform(-50, -5), 1)
            
            # Obliczenie ROI dla sygnału
            roi = round(pips / 100, 3)  # Uproszczone ROI
            
            # Tworzenie sygnału
            signal = {
                "id": i + 1,
                "timestamp": signal_date.isoformat(),
                "model": model,
                "symbol": symbol,
                "direction": direction,
                "timeframe": timeframe,
                "confidence": confidence,
                "entry_price": entry_price,
                "result": result,
                "pips": pips,
                "roi": roi
            }
            
            signals.append(signal)
        
        # Sortowanie sygnałów według daty (od najnowszych)
        signals.sort(key=lambda x: x["timestamp"], reverse=True)
        
        return {
            "status": "ok",
            "signals": signals,
            "timestamp": datetime.now().isoformat(),
            "count": len(signals)
        }
    
    def get_latest_signals(self, limit: int = 10) -> Dict[str, Any]:
        """
        Generuje najnowsze sygnały handlowe AI.
        
        Args:
            limit: Maksymalna liczba sygnałów do wygenerowania
            
        Returns:
            Dict: Dane o najnowszych sygnałach
        """
        signals_count = min(limit, random.randint(0, limit))
        signals = []
        
        for i in range(signals_count):
            # Generowanie losowej daty w ciągu ostatnich 24 godzin
            signal_date = datetime.now() - timedelta(
                hours=random.randint(0, 24),
                minutes=random.randint(0, 59)
            )
            
            model = random.choice(self.models)
            symbol = random.choice(self.symbols)
            direction = random.choice(self.directions)
            timeframe = random.choice(self.timeframes)
            confidence = round(random.uniform(0.6, 0.95), 2)
            
            # Generowanie ceny wejściowej zależnej od instrumentu
            if symbol == "EURUSD":
                entry_price = round(random.uniform(1.05, 1.15), 5)
                pip_value = 0.0001
            elif symbol == "GBPUSD":
                entry_price = round(random.uniform(1.25, 1.35), 5)
                pip_value = 0.0001
            elif symbol == "USDJPY":
                entry_price = round(random.uniform(140, 150), 3)
                pip_value = 0.01
            elif symbol == "GOLD":
                entry_price = round(random.uniform(1950, 2050), 2)
                pip_value = 0.1
            elif symbol == "US100":
                entry_price = round(random.uniform(17000, 18500), 2)
                pip_value = 0.25
            else:
                entry_price = round(random.uniform(1.0, 100.0), 2)
                pip_value = 0.01
            
            # Obliczanie SL i TP
            if direction == "BUY":
                stop_loss = round(entry_price * (1 - random.uniform(0.005, 0.02)), 5)
                take_profit = round(entry_price * (1 + random.uniform(0.01, 0.035)), 5)
            else:  # SELL
                stop_loss = round(entry_price * (1 + random.uniform(0.005, 0.02)), 5)
                take_profit = round(entry_price * (1 - random.uniform(0.01, 0.035)), 5)
            
            # Obliczenie RR (Risk-Reward Ratio)
            if direction == "BUY":
                risk = entry_price - stop_loss
                reward = take_profit - entry_price
            else:
                risk = stop_loss - entry_price
                reward = entry_price - take_profit
            
            risk_reward_ratio = round(reward / risk, 2) if risk > 0 else 0
            
            # Generowanie analizy
            analysis_templates = [
                f"Analiza {symbol} na interwale {timeframe} wskazuje na silny sygnał {direction.lower()}. Kluczowe poziomy wsparcia/oporu znajdują się na {stop_loss:.5f} i {take_profit:.5f}.",
                f"Rekomendacja {direction.lower()} dla {symbol} oparta na formacji świecowej i wskaźnikach technicznych. RR wynosi {risk_reward_ratio}.",
                f"Sygnał {direction.lower()} wygenerowany przez model {model} z pewnością {confidence:.2f}. Trend wskazuje na kontynuację ruchu cenowego w kierunku {take_profit:.5f}."
            ]
            
            analysis = random.choice(analysis_templates)
            
            # Tworzenie sygnału
            expiry = signal_date + timedelta(days=1)
            
            signal = {
                "id": i + 1,
                "symbol": symbol,
                "direction": direction,
                "confidence": confidence,
                "entry_price": entry_price,
                "stop_loss": stop_loss,
                "take_profit": take_profit,
                "analysis": analysis,
                "timeframe": timeframe,
                "timestamp": signal_date.isoformat(),
                "expiry": expiry.isoformat(),
                "model_name": model,
                "risk_reward_ratio": risk_reward_ratio
            }
            
            signals.append(signal)
        
        # Sortowanie sygnałów według pewności (od najwyższej)
        signals.sort(key=lambda x: x["confidence"], reverse=True)
        
        return {
            "status": "ok",
            "count": len(signals),
            "signals": signals,
            "timestamp": datetime.now().isoformat()
        }
    
    def get_ai_costs_data(self) -> Dict[str, Any]:
        """
        Generuje dane demonstracyjne o kosztach używania modeli AI.
        
        Returns:
            Dict: Dane o kosztach AI
        """
        cost_data = []
        total_cost = 0
        
        for model in self.models:
            # Generowanie losowych danych o kosztach
            queries_count = random.randint(50, 500)
            cost_per_query = round(random.uniform(0.01, 0.08), 3)
            total_model_cost = round(cost_per_query * queries_count, 2)
            total_cost += total_model_cost
            
            # Obliczanie średniego kosztu na sygnał
            signals_generated = random.randint(10, queries_count // 2)
            cost_per_signal = round(total_model_cost / signals_generated, 3) if signals_generated > 0 else 0
            
            # Obliczanie ROI na podstawie kosztów
            signals_profit = random.uniform(-50, 200)
            cost_effectiveness = round(signals_profit / total_model_cost, 2) if total_model_cost > 0 else 0
            
            cost_data.append({
                "model": model,
                "queries_count": queries_count,
                "cost_per_query": cost_per_query,
                "total_cost": total_model_cost,
                "signals_generated": signals_generated,
                "cost_per_signal": cost_per_signal,
                "cost_effectiveness": cost_effectiveness
            })
        
        # Sortowanie modeli według efektywności kosztowej (od najlepszych)
        cost_data.sort(key=lambda x: x["cost_effectiveness"], reverse=True)
        
        return {
            "status": "demo",
            "message": "Wyświetlane są dane demonstracyjne kosztów AI.",
            "costs": cost_data,
            "total_cost": round(total_cost, 2),
            "timestamp": datetime.now().isoformat()
        }

# Singleton instance
_demo_instance = None

def get_demo_data_provider() -> AIAnalyticsDemo:
    """
    Zwraca instancję dostawcy danych demonstracyjnych w trybie singleton.
    
    Returns:
        AIAnalyticsDemo: Instancja dostawcy danych demonstracyjnych
    """
    global _demo_instance
    if _demo_instance is None:
        _demo_instance = AIAnalyticsDemo()
    return _demo_instance


if __name__ == "__main__":
    # Test danych demonstracyjnych
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    demo = get_demo_data_provider()
    print("=== Dane modeli AI ===")
    models_data = demo.get_ai_models_data()
    print(json.dumps(models_data, indent=2))
    
    print("\n=== Dane sygnałów AI ===")
    signals_data = demo.get_ai_signals_data()
    print(f"Liczba sygnałów: {signals_data['count']}")
    print("Przykładowe sygnały:")
    for signal in signals_data["signals"][:3]:
        print(json.dumps(signal, indent=2))
    
    print("\n=== Najnowsze sygnały AI ===")
    latest_signals = demo.get_latest_signals(limit=3)
    print(f"Liczba sygnałów: {latest_signals['count']}")
    for signal in latest_signals["signals"]:
        print(json.dumps(signal, indent=2))
    
    print("\n=== Dane kosztów AI ===")
    costs_data = demo.get_ai_costs_data()
    print(f"Całkowity koszt: {costs_data['total_cost']}")
    print("Koszty według modeli:")
    for cost in costs_data["costs"]:
        print(f"{cost['model']}: ${cost['total_cost']} (efektywność: {cost['cost_effectiveness']})") 