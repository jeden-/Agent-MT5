#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
AgentMT5 - Trading Agent Monitor
Interfejs użytkownika do monitorowania i zarządzania systemem handlowym AgentMT5.
"""

import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import numpy as np
import time
import json
import requests
from datetime import datetime, timedelta
import sys
import os

# Dodanie ścieżki nadrzędnej, aby zaimportować moduły
sys.path.append(os.path.abspath(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))

# Import komponentów monitorowania
from src.monitoring.monitoring_logger import LogLevel, OperationType, OperationStatus
from src.monitoring.alert_manager import AlertLevel, AlertCategory, AlertStatus

# Konfiguracja strony
st.set_page_config(
    page_title="AgentMT5 Monitor",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Stałe
SERVER_URL = "http://127.0.0.1:5555"
REFRESH_INTERVAL = 5  # sekundy

# Custom CSS
st.markdown("""
<style>
    .stMetric {
        background-color: #f0f2f6;
        padding: 10px;
        border-radius: 5px;
    }
    .tradingChart {
        height: 400px;
        margin: 20px 0;
    }
    .statusIndicator {
        display: inline-block;
        width: 10px;
        height: 10px;
        border-radius: 50%;
        margin-right: 5px;
    }
    .status-ok { background-color: #00ff00; }
    .status-warning { background-color: #ffff00; }
    .status-error { background-color: #ff0000; }
    .status-critical { background-color: #990000; }
    
    .stTabs [data-baseweb="tab-list"] {
        gap: 2px;
    }
    
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        white-space: pre-wrap;
        background-color: #f0f2f6;
        border-radius: 4px 4px 0px 0px;
        gap: 1px;
        padding-top: 10px;
        padding-bottom: 10px;
    }
    
    .stTabs [aria-selected="true"] {
        background-color: #4CAF50;
        color: white;
    }
</style>
""", unsafe_allow_html=True)

def api_request(endpoint, method="GET", params=None, data=None):
    """Wykonuje zapytanie do API serwera MT5."""
    url = f"{SERVER_URL}/{endpoint}"
    try:
        if method == "GET":
            response = requests.get(url, params=params, timeout=5)
        else:
            response = requests.post(url, json=data, timeout=5)
        
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"Błąd API: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        st.error(f"Błąd połączenia z serwerem: {e}")
        return None

def render_status_indicator(status):
    """Renderuje kolorowy wskaźnik statusu."""
    if status == "ok":
        color_class = "status-ok"
    elif status == "warning":
        color_class = "status-warning"
    elif status == "error":
        color_class = "status-error"
    elif status == "critical":
        color_class = "status-critical"
    else:
        color_class = ""
    
    return f'<span class="statusIndicator {color_class}"></span>{status.upper()}'

def render_live_monitor():
    """Renderuje zakładkę Live Monitor."""
    st.header("Live Trading Monitor")
    
    # Podział na dwie kolumny
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # Wykres equity
        st.subheader("Equity Chart")
        
        # Przykładowe dane do wykresu
        # W rzeczywistości będziemy pobierać te dane z API
        dates = pd.date_range(start=datetime.now() - timedelta(days=7), end=datetime.now(), freq='D')
        equity = [10000 + i*100 + np.random.randint(-50, 50) for i in range(len(dates))]
        balance = [10000 + i*80 for i in range(len(dates))]
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=dates, y=equity, name='Equity', line=dict(color='blue')
        ))
        fig.add_trace(go.Scatter(
            x=dates, y=balance, name='Balance', line=dict(color='green')
        ))
        
        fig.update_layout(
            height=400,
            margin=dict(l=0, r=0, t=0, b=0),
            legend=dict(orientation="h", y=1.02),
            xaxis_title="Data",
            yaxis_title="Wartość ($)"
        )
        
        st.plotly_chart(fig, use_container_width=True, className="tradingChart")
        
        # Aktywne pozycje
        st.subheader("Aktywne Pozycje")
        
        # Przykładowe dane dla aktywnych pozycji
        positions_data = {
            "Instrument": ["EURUSD", "GOLD", "NASDAQ"],
            "Kierunek": ["BUY", "SELL", "BUY"],
            "Wolumen": [0.1, 0.05, 0.2],
            "Cena Wejścia": [1.0892, 2156.45, 17845.30],
            "Cena Aktualna": [1.0901, 2152.80, 17880.25],
            "P/L": [9.00, 18.25, 70.00],
            "Czas Trwania": ["2h 15m", "1d 4h", "45m"]
        }
        
        positions_df = pd.DataFrame(positions_data)
        st.dataframe(positions_df, use_container_width=True)
        
    with col2:
        # Metryki konta
        st.subheader("Statystyki Konta")
        
        metric_col1, metric_col2 = st.columns(2)
        
        with metric_col1:
            st.metric(label="Balance", value="$10,580.00")
            st.metric(label="Open P/L", value="$97.25", delta="+0.92%")
            st.metric(label="Otwarte Pozycje", value="3")
        
        with metric_col2:
            st.metric(label="Equity", value="$10,677.25")
            st.metric(label="Dzisiejszy Wynik", value="$52.75", delta="+0.5%")
            st.metric(label="Zlecenia Oczekujące", value="1")
        
        # Ostatnie operacje
        st.subheader("Ostatnie Operacje")
        
        operations_data = {
            "Czas": ["12:30:15", "11:45:22", "10:15:08", "09:30:45"],
            "Typ": ["Otwarcie", "Zamknięcie", "Modyfikacja", "Otwarcie"],
            "Instrument": ["EURUSD", "GOLD", "NASDAQ", "GBPUSD"],
            "Status": ["Sukces", "Sukces", "Sukces", "Odrzucone"]
        }
        
        operations_df = pd.DataFrame(operations_data)
        st.dataframe(operations_df, use_container_width=True)
        
        # Szybkie akcje
        st.subheader("Szybkie Akcje")
        
        button_col1, button_col2 = st.columns(2)
        
        with button_col1:
            st.button("Zamknij Wszystkie", use_container_width=True)
            st.button("Reset AI", use_container_width=True)
        
        with button_col2:
            st.button("Anuluj Oczekujące", use_container_width=True)
            st.button("STOP Emergency", type="primary", use_container_width=True)

def render_performance_dashboard():
    """Renderuje zakładkę Performance Dashboard."""
    st.header("Performance Dashboard")
    
    # Główne metryki
    st.subheader("Kluczowe Wskaźniki")
    
    metrics_cols = st.columns(6)
    
    metrics_cols[0].metric(label="Win Rate", value="62.5%")
    metrics_cols[1].metric(label="Profit Factor", value="2.15")
    metrics_cols[2].metric(label="Avg Win", value="$45.80")
    metrics_cols[3].metric(label="Avg Loss", value="$21.35")
    metrics_cols[4].metric(label="Sharpe Ratio", value="1.65")
    metrics_cols[5].metric(label="Max DD", value="5.2%")
    
    # Podział na dwie kolumny
    col1, col2 = st.columns(2)
    
    with col1:
        # Wykres wyników
        st.subheader("Wyniki Handlowe")
        
        # Przykładowe dane
        dates = pd.date_range(start=datetime.now() - timedelta(days=30), end=datetime.now(), freq='D')
        daily_pnl = [np.random.randint(-50, 100) for _ in range(len(dates))]
        cumulative_pnl = np.cumsum(daily_pnl)
        
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=dates, y=daily_pnl, name='Dzienny P/L', marker_color='lightblue'
        ))
        fig.add_trace(go.Scatter(
            x=dates, y=cumulative_pnl, name='Skumulowany P/L', line=dict(color='green')
        ))
        
        fig.update_layout(
            height=400,
            margin=dict(l=0, r=0, t=0, b=0),
            legend=dict(orientation="h", y=1.02),
            xaxis_title="Data",
            yaxis_title="P/L ($)"
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        # Analiza instrumentów
        st.subheader("Wydajność Instrumentów")
        
        instruments_data = {
            "Instrument": ["EURUSD", "GBPUSD", "GOLD", "SILVER", "NASDAQ"],
            "Liczba Transakcji": [25, 18, 30, 12, 8],
            "Win Rate": ["68%", "55%", "73%", "50%", "62%"],
            "Zysk Netto": ["$245.50", "$120.80", "$380.25", "-$50.60", "$195.40"],
            "Avg RRR": ["1.8", "1.5", "2.1", "1.2", "1.6"]
        }
        
        instruments_df = pd.DataFrame(instruments_data)
        st.dataframe(instruments_df, use_container_width=True)
        
        # Analiza strategii
        st.subheader("Wydajność Strategii")
        
        # Przykładowe dane
        strategies = ['Scalping', 'Intraday', 'Swing']
        profit = [320, 480, 200]
        trades = [45, 30, 15]
        
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=strategies, y=profit, name='Zysk', marker_color='lightgreen'
        ))
        fig.add_trace(go.Bar(
            x=strategies, y=trades, name='Liczba Transakcji', marker_color='lightblue'
        ))
        
        fig.update_layout(
            height=300,
            margin=dict(l=0, r=0, t=0, b=0),
            legend=dict(orientation="h", y=1.02),
            xaxis_title="Strategia",
            yaxis_title="Wartość"
        )
        
        st.plotly_chart(fig, use_container_width=True)

def render_ai_analytics():
    """Renderuje zakładkę AI Analytics."""
    st.header("AI Analytics")
    
    # Status modeli AI
    st.subheader("Status Modeli AI")
    
    models_cols = st.columns(3)
    
    with models_cols[0]:
        st.markdown(f"### Claude")
        st.markdown(f"**Status:** {render_status_indicator('ok')}", unsafe_allow_html=True)
        st.metric(label="Średni czas odpowiedzi", value="1.25s")
        st.metric(label="Użycie dziś", value="45 zapytań")
        st.metric(label="Koszt dziś", value="$0.85")
    
    with models_cols[1]:
        st.markdown(f"### Grok")
        st.markdown(f"**Status:** {render_status_indicator('warning')}", unsafe_allow_html=True)
        st.metric(label="Średni czas odpowiedzi", value="2.45s")
        st.metric(label="Użycie dziś", value="32 zapytań")
        st.metric(label="Koszt dziś", value="$0.64")
    
    with models_cols[2]:
        st.markdown(f"### DeepSeek")
        st.markdown(f"**Status:** {render_status_indicator('ok')}", unsafe_allow_html=True)
        st.metric(label="Średni czas odpowiedzi", value="1.85s")
        st.metric(label="Użycie dziś", value="28 zapytań")
        st.metric(label="Koszt dziś", value="$0.56")
    
    # Podział na dwie kolumny
    col1, col2 = st.columns(2)
    
    with col1:
        # Logi decyzji
        st.subheader("Logi Decyzji AI")
        
        decisions_data = {
            "Czas": ["12:45:10", "12:30:22", "12:15:08", "12:00:45", "11:45:30"],
            "Model": ["Claude", "Grok", "DeepSeek", "Claude", "Grok"],
            "Decyzja": ["BUY EURUSD", "SELL GOLD", "HOLD", "CLOSE NASDAQ", "BUY GBPUSD"],
            "Pewność": ["85%", "78%", "92%", "65%", "81%"],
            "Wynik": ["Sukces", "Sukces", "Sukces", "Porażka", "Trwa"]
        }
        
        decisions_df = pd.DataFrame(decisions_data)
        st.dataframe(decisions_df, use_container_width=True)
    
    with col2:
        # Jakość sygnałów
        st.subheader("Jakość Sygnałów AI")
        
        # Przykładowe dane
        models = ['Claude', 'Grok', 'DeepSeek']
        accuracy = [0.85, 0.78, 0.82]
        signals = [45, 32, 28]
        
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=models, y=accuracy, name='Dokładność', marker_color='lightgreen'
        ))
        fig.add_trace(go.Bar(
            x=models, y=[s/100 for s in signals], name='Liczba Sygnałów (x100)', marker_color='lightblue'
        ))
        
        fig.update_layout(
            height=300,
            margin=dict(l=0, r=0, t=0, b=0),
            legend=dict(orientation="h", y=1.02),
            xaxis_title="Model",
            yaxis_title="Wartość"
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Koszt operacyjny
        st.subheader("Koszt Operacyjny AI")
        
        # Przykładowe dane
        dates = pd.date_range(start=datetime.now() - timedelta(days=7), end=datetime.now(), freq='D')
        costs = [0.75, 0.95, 1.25, 1.05, 0.85, 1.15, 1.45, 1.30]
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=dates, y=costs, name='Dzienny koszt', line=dict(color='purple')
        ))
        
        fig.update_layout(
            height=250,
            margin=dict(l=0, r=0, t=0, b=0),
            xaxis_title="Data",
            yaxis_title="Koszt ($)"
        )
        
        st.plotly_chart(fig, use_container_width=True)

def render_system_status():
    """Renderuje zakładkę System Status."""
    st.header("System Status Monitor")
    
    # Pobierz status systemu
    status_data = api_request("monitoring/status", params={"detail_level": "detailed"})
    
    if not status_data:
        status_data = {
            "status": "error",
            "timestamp": datetime.now().isoformat(),
            "active_connections": 0,
            "inactive_connections": 0,
            "alerts": {"critical": 1, "error": 2, "warning": 3, "info": 5},
            "system_resources": {"cpu_usage": 25.5, "memory_usage": 512.0},
            "requests": {"total": 150, "success_rate": 98.5},
            "components": {
                "server": "ok",
                "database": "warning",
                "mt5_connection": "ok"
            }
        }
    
    # Status ogólny
    st.subheader("Status Ogólny")
    
    status_cols = st.columns(4)
    
    status_cols[0].markdown(
        f"### System\n{render_status_indicator(status_data.get('status', 'unknown'))}",
        unsafe_allow_html=True
    )
    
    status_cols[1].metric(
        label="Aktywne Połączenia",
        value=status_data.get("active_connections", 0)
    )
    
    status_cols[2].metric(
        label="Nieaktywne Połączenia",
        value=status_data.get("inactive_connections", 0)
    )
    
    alerts_count = sum(status_data.get("alerts", {}).values())
    status_cols[3].metric(
        label="Aktywne Alerty",
        value=alerts_count
    )
    
    # Podział na dwie kolumny
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # Status komponentów
        st.subheader("Status Komponentów")
        
        components = status_data.get("components", {})
        
        components_data = {
            "Komponent": list(components.keys()),
            "Status": [render_status_indicator(status) for status in components.values()]
        }
        
        # Tworzymy DataFrame
        components_df = pd.DataFrame(components_data)
        
        # Wyświetlamy tabelę z HTML dla wskaźników statusu
        st.write(
            components_df.to_html(escape=False, index=False),
            unsafe_allow_html=True
        )
        
        # Zasoby systemowe
        st.subheader("Zasoby Systemowe")
        
        resources = status_data.get("system_resources", {})
        
        cpu_usage = resources.get("cpu_usage", 0)
        memory_usage = resources.get("memory_usage", 0)
        
        resources_cols = st.columns(2)
        
        resources_cols[0].metric(
            label="Użycie CPU",
            value=f"{cpu_usage:.1f}%"
        )
        
        resources_cols[1].metric(
            label="Użycie Pamięci",
            value=f"{memory_usage:.1f} MB"
        )
        
        # Przykładowe dane dla wykresu
        times = pd.date_range(start=datetime.now() - timedelta(hours=1), end=datetime.now(), freq='5min')
        cpu_values = [max(min(cpu_usage + np.random.randint(-10, 10), 100), 0) for _ in range(len(times))]
        memory_values = [max(min(memory_usage + np.random.randint(-50, 50), 2048), 0) for _ in range(len(times))]
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=times, y=cpu_values, name='CPU (%)', line=dict(color='red')
        ))
        fig.add_trace(go.Scatter(
            x=times, y=[m/20 for m in memory_values], name='Pamięć (MB/20)', line=dict(color='blue')
        ))
        
        fig.update_layout(
            height=300,
            margin=dict(l=0, r=0, t=0, b=0),
            legend=dict(orientation="h", y=1.02),
            xaxis_title="Czas",
            yaxis_title="Użycie"
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        # Aktywne alerty
        st.subheader("Aktywne Alerty")
        
        # Pobierz alerty
        alerts_data = api_request("monitoring/alerts", params={"status": "open,acknowledged", "limit": 10})
        
        if not alerts_data:
            alerts_data = [
                {
                    "alert_id": 1,
                    "timestamp": "2025-03-09T12:30:00",
                    "level": "ERROR",
                    "category": "CONNECTION",
                    "message": "Połączenie z EA_1234 nieaktywne od 5 minut",
                    "status": "OPEN"
                },
                {
                    "alert_id": 2,
                    "timestamp": "2025-03-09T12:15:00",
                    "level": "WARNING",
                    "category": "TRADING",
                    "message": "Zlecenie odrzucone: niewystarczający depozyt",
                    "status": "ACKNOWLEDGED"
                }
            ]
        
        for alert in alerts_data:
            level = alert.get("level", "WARNING")
            if level == "CRITICAL":
                status_color = "status-critical"
            elif level == "ERROR":
                status_color = "status-error"
            elif level == "WARNING":
                status_color = "status-warning"
            else:
                status_color = "status-ok"
            
            with st.container():
                st.markdown(
                    f"<div style='padding: 10px; border-left: 5px solid #{status_color[7:]}; margin-bottom: 10px;'>"
                    f"<strong>{alert.get('timestamp', '').split('T')[1].split('.')[0]} - {level}</strong><br>"
                    f"{alert.get('message', '')}<br>"
                    f"<small>Status: {alert.get('status', '')}, Kategoria: {alert.get('category', '')}</small>"
                    f"</div>",
                    unsafe_allow_html=True
                )
        
        # Statystyki zapytań
        st.subheader("Statystyki Zapytań")
        
        requests_data = status_data.get("requests", {})
        
        requests_cols = st.columns(2)
        
        requests_cols[0].metric(
            label="Liczba Zapytań",
            value=requests_data.get("total", 0)
        )
        
        requests_cols[1].metric(
            label="Sukces",
            value=f"{requests_data.get('success_rate', 0):.1f}%"
        )

def main():
    """Główna funkcja aplikacji."""
    # Tytuł aplikacji
    st.title("AgentMT5 - Trading Agent Monitor")
    
    # Zakładki główne
    tab1, tab2, tab3, tab4 = st.tabs([
        "📊 Live Monitor", 
        "📈 Performance Dashboard", 
        "🧠 AI Analytics", 
        "⚙️ System Status"
    ])
    
    with tab1:
        render_live_monitor()
    
    with tab2:
        render_performance_dashboard()
    
    with tab3:
        render_ai_analytics()
    
    with tab4:
        render_system_status()
    
    # Auto-refresh
    if st.sidebar.checkbox("Automatyczne odświeżanie", value=True):
        refresh_interval = st.sidebar.slider(
            "Interwał odświeżania (s)", 
            min_value=5, 
            max_value=60, 
            value=REFRESH_INTERVAL
        )
        
        st.sidebar.write(f"Następne odświeżenie za {refresh_interval} s")
        time.sleep(refresh_interval)
        st.experimental_rerun()
    
    # Sidebar
    st.sidebar.header("Ustawienia")
    
    st.sidebar.subheader("Serwer")
    server_url = st.sidebar.text_input("URL Serwera", value=SERVER_URL)
    
    st.sidebar.subheader("Akcje")
    if st.sidebar.button("Testuj Połączenie"):
        try:
            response = requests.get(f"{server_url}/status", timeout=5)
            if response.status_code == 200:
                st.sidebar.success("Połączenie z serwerem OK!")
            else:
                st.sidebar.error(f"Błąd połączenia: {response.status_code}")
        except Exception as e:
            st.sidebar.error(f"Błąd połączenia: {e}")
    
    if st.sidebar.button("Wyczyść Alerty"):
        st.sidebar.info("Funkcja czyszczenia alertów w trakcie implementacji.")
    
    st.sidebar.subheader("System")
    st.sidebar.info(f"Ostatnia aktualizacja: {datetime.now().strftime('%H:%M:%S')}")
    st.sidebar.info(f"Wersja systemu: 0.1.0")

if __name__ == "__main__":
    main() 