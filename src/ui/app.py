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
import locale

# Ustawienie lokalizacji polskiej do formatowania wartości
try:
    locale.setlocale(locale.LC_ALL, 'pl_PL.UTF-8')
except:
    # Jeśli polska lokalizacja nie jest dostępna, spróbujmy ogólną
    try:
        locale.setlocale(locale.LC_ALL, 'pl_PL')
    except:
        # Jeśli także to nie zadziała, pozostajemy przy domyślnej
        pass

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
CURRENCY = "zł"  # Waluta używana w systemie

# Funkcje pomocnicze do formatowania
def format_currency(value):
    """Formatuje wartość jako kwotę w PLN w formacie polskim."""
    if value is None:
        return "0,00 zł"
    return f"{value:,.2f}".replace(",", " ").replace(".", ",") + f" {CURRENCY}"

def format_percentage(value):
    """Formatuje wartość jako procent w formacie polskim."""
    if value is None:
        return "0,00%"
    return f"{value:,.2f}%".replace(",", " ").replace(".", ",")

def format_date(dt):
    """Formatuje datę w polskim formacie."""
    if isinstance(dt, str):
        try:
            dt = datetime.fromisoformat(dt.replace('Z', '+00:00'))
        except:
            try:
                dt = datetime.strptime(dt, "%Y-%m-%d %H:%M:%S")
            except:
                return dt
    
    if isinstance(dt, datetime):
        return dt.strftime("%d.%m.%Y %H:%M:%S")
    return str(dt)

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
    .currency-value {
        font-weight: bold;
        color: #0e5484;
    }
    .positive-value {
        color: green;
    }
    .negative-value {
        color: red;
    }
</style>
""", unsafe_allow_html=True)

def api_request(endpoint, method="GET", params=None, data=None):
    """Wykonuje żądanie do API serwera."""
    try:
        if method == "GET":
            response = requests.get(f"{SERVER_URL}/{endpoint}", params=params, timeout=5)
        else:
            response = requests.post(f"{SERVER_URL}/{endpoint}", json=data, timeout=5)
        
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"Błąd API: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        st.error(f"Błąd komunikacji z serwerem: {e}")
        return None

def render_status_indicator(status):
    """Renderuje wskaźnik statusu jako HTML."""
    colors = {
        "ok": "green",
        "warning": "orange",
        "error": "red",
        "critical": "darkred",
        "unknown": "gray"
    }
    color = colors.get(status.lower(), "gray")
    return f'<span style="color: {color}; font-weight: bold;">{status.upper()}</span>'

def render_live_monitor():
    """Renderuje zakładkę Live Monitor."""
    st.header("Monitor Trading Live")
    
    # Pobierz aktywne połączenia
    connections_data = api_request("monitoring/connections")
    
    if not connections_data:
        # Przykładowe dane jeśli nie można pobrać z API
        connections_data = {
            "connections": [
                {
                    "ea_id": "EA_1741521231",
                    "last_ping": datetime.now().isoformat(),
                    "status": "active",
                    "symbol": "EURUSD",
                    "positions": 2,
                    "account_balance": 10500,
                    "account_equity": 10650,
                    "profit": 150
                }
            ]
        }
    
    # Aktywne połączenia
    st.subheader("Aktywne Połączenia EA")
    
    connections = connections_data.get("connections", [])
    if connections:
        for connection in connections:
            col1, col2, col3, col4 = st.columns([1, 1, 1, 1])
            
            col1.metric(
                label=f"EA ID: {connection.get('ea_id')}",
                value=connection.get('symbol', 'N/A')
            )
            
            last_ping = connection.get('last_ping')
            if last_ping:
                last_ping = format_date(last_ping)
            col2.metric(
                label="Ostatnia Aktywność",
                value=last_ping
            )
            
            profit = connection.get('profit', 0)
            profit_delta = None
            profit_text = format_currency(profit)
            
            col3.metric(
                label="Bieżący Zysk",
                value=profit_text,
                delta=profit_delta
            )
            
            positions = connection.get('positions', 0)
            col4.metric(
                label="Aktywne Pozycje",
                value=positions
            )
            
            st.markdown("---")
    else:
        st.info("Brak aktywnych połączeń EA")
    
    # Ostatnie transakcje
    st.subheader("Ostatnie Transakcje")
    
    # Przykładowe dane dla ostatnich transakcji
    transactions = [
        {"id": 1, "symbol": "EURUSD", "type": "BUY", "open_time": "2025-03-09 10:15:32", 
         "close_time": "2025-03-09 11:30:45", "profit": 45.80, "status": "CLOSED"},
        {"id": 2, "symbol": "GOLD", "type": "SELL", "open_time": "2025-03-09 09:45:18", 
         "close_time": None, "profit": -12.35, "status": "OPEN"},
        {"id": 3, "symbol": "USDJPY", "type": "BUY", "open_time": "2025-03-09 08:30:21", 
         "close_time": "2025-03-09 10:05:39", "profit": 33.25, "status": "CLOSED"},
    ]
    
    transactions_df = pd.DataFrame(transactions)
    
    # Formatowanie kolumn z datami i profitem
    transactions_df['open_time'] = transactions_df['open_time'].apply(format_date)
    transactions_df['close_time'] = transactions_df['close_time'].apply(
        lambda x: format_date(x) if x else "Aktywna"
    )
    
    # Formatowanie profitu w walucie PLN
    transactions_df['profit'] = transactions_df['profit'].apply(format_currency)
    
    st.dataframe(transactions_df, use_container_width=True)

def render_performance_dashboard():
    """Renderuje zakładkę Performance Dashboard."""
    st.header("Performance Dashboard")
    
    # Główne metryki
    st.subheader("Kluczowe Wskaźniki")
    
    metrics_cols = st.columns(6)
    
    metrics_cols[0].metric(label="Win Rate", value="62,5%")
    metrics_cols[1].metric(label="Profit Factor", value="2,15")
    metrics_cols[2].metric(label="Średni Zysk", value=format_currency(45.80))
    metrics_cols[3].metric(label="Średnia Strata", value=format_currency(21.35))
    metrics_cols[4].metric(label="Sharpe Ratio", value="1,65")
    metrics_cols[5].metric(label="Max DD", value="5,2%")
    
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
            yaxis_title=f"P/L ({CURRENCY})"
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        # Analiza instrumentów
        st.subheader("Wydajność Instrumentów")
        
        # Przykładowe dane
        symbols = ["EURUSD", "GOLD", "USDJPY", "GBPUSD", "OIL"]
        profits = [325.50, 145.80, -53.20, 89.70, -120.30]
        
        symbol_data = pd.DataFrame({
            "Symbol": symbols,
            "Zysk/Strata": profits
        })
        
        # Formatowanie zysku w walucie PLN
        symbol_data['Zysk/Strata Formatowany'] = symbol_data['Zysk/Strata'].apply(format_currency)
        
        # Kolor na podstawie wartości profit
        symbol_data['Color'] = symbol_data['Zysk/Strata'].apply(
            lambda x: 'green' if x > 0 else 'red'
        )
        
        fig = go.Figure(go.Bar(
            x=symbol_data['Symbol'],
            y=symbol_data['Zysk/Strata'],
            marker_color=symbol_data['Color'],
            text=symbol_data['Zysk/Strata Formatowany'],
            textposition='auto'
        ))
        
        fig.update_layout(
            height=400,
            margin=dict(l=0, r=0, t=0, b=0),
            xaxis_title="Instrument",
            yaxis_title=f"Zysk/Strata ({CURRENCY})"
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    # Statystyki handlowe
    st.subheader("Statystyki Handlowe")
    
    stats_cols = st.columns(3)
    
    stats_cols[0].metric(label="Łącznie Transakcji", value="48")
    stats_cols[1].metric(label="Zyskowne Transakcje", value="30")
    stats_cols[2].metric(label="Stratne Transakcje", value="18")
    
    # Metryki ryzyka
    st.subheader("Metryki Ryzyka")
    
    risk_cols = st.columns(4)
    
    risk_cols[0].metric(label="Średni RRR", value="1,85")
    risk_cols[1].metric(label="Kalmar Ratio", value="0,95")
    risk_cols[2].metric(label="Średnia Ekspozycja", value="15,3%")
    risk_cols[3].metric(label="Max. Drawdown", value=format_currency(1250.00))

def render_ai_analytics():
    """Renderuje zakładkę AI Analytics."""
    st.header("Analityka AI")
    
    # Podział na dwie kolumny
    col1, col2 = st.columns(2)
    
    with col1:
        # Wydajność modeli AI
        st.subheader("Wydajność Modeli AI")
        
        # Przykładowe dane
        models = ["Claude", "Grok", "DeepSeek", "Ensemble"]
        accuracy = [0.78, 0.72, 0.75, 0.82]
        roi = [0.15, 0.05, 0.12, 0.18]
        
        model_data = pd.DataFrame({
            "Model": models,
            "Dokładność": accuracy,
            "ROI": roi
        })
        
        # Formatowanie ROI jako procent w polskim stylu
        model_data['ROI Formatowany'] = model_data['ROI'].apply(format_percentage)
        
        # Formatowanie dokładności jako procent w polskim stylu
        model_data['Dokładność Formatowana'] = model_data['Dokładność'].apply(format_percentage)
        
        fig = go.Figure(data=[
            go.Bar(name='Dokładność', x=model_data['Model'], y=model_data['Dokładność'],
                  text=model_data['Dokładność Formatowana'], textposition='auto'),
            go.Bar(name='ROI', x=model_data['Model'], y=model_data['ROI'],
                  text=model_data['ROI Formatowany'], textposition='auto')
        ])
        
        fig.update_layout(
            barmode='group',
            height=400,
            margin=dict(l=0, r=0, t=0, b=0),
            legend=dict(orientation="h", y=1.02),
            xaxis_title="Model AI",
            yaxis_title="Wartość"
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Koszty API
        st.subheader("Koszty API")
        
        # Przykładowe dane dla kosztów API
        days = pd.date_range(start=datetime.now() - timedelta(days=14), end=datetime.now(), freq='D')
        costs = [round(np.random.uniform(5, 15), 2) for _ in range(len(days))]
        
        costs_df = pd.DataFrame({
            "Data": days,
            "Koszt": costs
        })
        
        # Formatowanie kosztów w PLN
        costs_df['Koszt Formatowany'] = costs_df['Koszt'].apply(format_currency)
        
        fig = go.Figure(go.Bar(
            x=costs_df['Data'],
            y=costs_df['Koszt'],
            text=costs_df['Koszt Formatowany'],
            textposition='auto',
            marker_color='indianred'
        ))
        
        fig.update_layout(
            height=350,
            margin=dict(l=0, r=0, t=0, b=0),
            xaxis_title="Data",
            yaxis_title=f"Koszt ({CURRENCY})"
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        # Szczegóły predykcji
        st.subheader("Szczegóły Predykcji")
        
        # Wybór modelu
        selected_model = st.selectbox(
            "Wybierz model",
            ["Claude", "Grok", "DeepSeek", "Ensemble"]
        )
        
        # Metryki modelu
        metrics_cols = st.columns(3)
        
        metrics_cols[0].metric(label="Dokładność", value="78,5%")
        metrics_cols[1].metric(label="Precyzja", value="82,3%")
        metrics_cols[2].metric(label="F1-Score", value="80,1%")
        
        # Macierz konfuzji
        st.subheader("Macierz Konfuzji")
        
        confusion_matrix = np.array([
            [35, 8],
            [5, 42]
        ])
        
        fig = go.Figure(data=go.Heatmap(
            z=confusion_matrix,
            x=['Przewidziane Negatywne', 'Przewidziane Pozytywne'],
            y=['Faktyczne Negatywne', 'Faktyczne Pozytywne'],
            hoverongaps=False,
            colorscale='Blues',
            text=confusion_matrix,
            texttemplate="%{text}",
            textfont={"size":14}
        ))
        
        fig.update_layout(
            height=300,
            margin=dict(l=0, r=0, t=0, b=0)
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Historia sygnałów AI
        st.subheader("Historia Sygnałów AI")
        
        # Przykładowe dane
        signals = [
            {"id": 1, "timestamp": "2025-03-09 10:12:54", "model": "Claude", "symbol": "EURUSD", 
             "signal": "BUY", "confidence": 0.85, "result": "SUCCESS", "profit": 55.40},
            {"id": 2, "timestamp": "2025-03-09 09:45:22", "model": "Grok", "symbol": "GOLD", 
             "signal": "SELL", "confidence": 0.72, "result": "FAILURE", "profit": -32.50},
            {"id": 3, "timestamp": "2025-03-09 09:30:08", "model": "DeepSeek", "symbol": "USDJPY", 
             "signal": "BUY", "confidence": 0.91, "result": "SUCCESS", "profit": 48.30},
        ]
        
        signals_df = pd.DataFrame(signals)
        
        # Formatowanie kolumn
        signals_df['timestamp'] = signals_df['timestamp'].apply(format_date)
        signals_df['confidence'] = signals_df['confidence'].apply(format_percentage)
        signals_df['profit'] = signals_df['profit'].apply(format_currency)
        
        st.dataframe(signals_df, use_container_width=True)

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
            value=f"{cpu_usage:.1f}%".replace(".", ",")
        )
        
        resources_cols[1].metric(
            label="Użycie Pamięci",
            value=f"{memory_usage:.1f} MB".replace(".", ",")
        )
        
        # Przykładowe dane dla wykresu
        times = pd.date_range(start=datetime.now() - timedelta(hours=1), end=datetime.now(), freq='5min')
        cpu_values = [max(min(cpu_usage + np.random.randint(-10, 10), 100), 0) for _ in range(len(times))]
        memory_values = [max(min(memory_usage + np.random.randint(-50, 50), 2048), 0) for _ in range(len(times))]
        
        # Oddzielne wykresy dla CPU i pamięci
        fig_cpu = go.Figure()
        fig_cpu.add_trace(go.Scatter(
            x=times, y=cpu_values, mode='lines+markers', name='CPU',
            line=dict(color='blue', width=2)
        ))
        
        fig_cpu.update_layout(
            height=200,
            margin=dict(l=0, r=0, t=30, b=0),
            xaxis_title="Czas",
            yaxis_title="Użycie CPU (%)",
            title="Historia użycia CPU"
        )
        
        st.plotly_chart(fig_cpu, use_container_width=True)
        
        fig_mem = go.Figure()
        fig_mem.add_trace(go.Scatter(
            x=times, y=memory_values, mode='lines+markers', name='Pamięć',
            line=dict(color='green', width=2)
        ))
        
        fig_mem.update_layout(
            height=200,
            margin=dict(l=0, r=0, t=30, b=0),
            xaxis_title="Czas",
            yaxis_title="Pamięć (MB)",
            title="Historia użycia pamięci"
        )
        
        st.plotly_chart(fig_mem, use_container_width=True)
    
    with col2:
        # Alerty systemowe
        st.subheader("Alerty Systemowe")
        
        # Pobierz alerty
        alerts_data = api_request("monitoring/alerts", params={"status": "open,acknowledged", "limit": 10})
        
        if not alerts_data:
            # Przykładowe dane
            alerts_data = {
                "alerts": [
                    {
                        "id": "alert1",
                        "level": "critical",
                        "category": "connection",
                        "message": "Utracono połączenie z EA_1741521231",
                        "timestamp": (datetime.now() - timedelta(minutes=5)).isoformat(),
                        "status": "open"
                    },
                    {
                        "id": "alert2",
                        "level": "warning",
                        "category": "performance",
                        "message": "Wysoki czas odpowiedzi serwera (>500ms)",
                        "timestamp": (datetime.now() - timedelta(minutes=15)).isoformat(),
                        "status": "acknowledged"
                    }
                ]
            }
        
        alerts = alerts_data.get("alerts", [])
        
        if alerts:
            for alert in alerts:
                alert_color = {
                    "critical": "red",
                    "error": "orange",
                    "warning": "yellow",
                    "info": "blue"
                }.get(alert.get("level", "").lower(), "gray")
                
                alert_time = format_date(alert.get("timestamp", ""))
                
                st.markdown(
                    f"""
                    <div style="padding: 10px; border-left: 5px solid {alert_color}; margin-bottom: 10px; background-color: #f0f2f6;">
                        <strong>{alert.get('level', '').upper()}</strong>: {alert.get('message', '')}
                        <br><small>{alert_time} - {alert.get('category', '').upper()} - {alert.get('status', '').upper()}</small>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
        else:
            st.info("Brak aktywnych alertów")
        
        # Statystyki żądań
        st.subheader("Statystyki Żądań")
        
        # Przykładowe dane żądań
        requests_data = status_data.get("requests", {})
        
        total_requests = requests_data.get("total", 0)
        success_rate = requests_data.get("success_rate", 0)
        
        st.metric(
            label="Łączne Żądania",
            value=f"{total_requests:,}".replace(",", " ")
        )
        
        st.metric(
            label="Wskaźnik Powodzenia",
            value=f"{success_rate:.1f}%".replace(".", ",")
        )
        
        # Podział typów żądań
        request_types = {
            "GET": 65,
            "POST": 35
        }
        
        fig = go.Figure(data=[go.Pie(
            labels=list(request_types.keys()),
            values=list(request_types.values()),
            hole=.3
        )])
        
        fig.update_layout(
            height=250,
            margin=dict(l=0, r=0, t=30, b=0),
            title="Podział typów żądań"
        )
        
        st.plotly_chart(fig, use_container_width=True)

def main():
    """Główna funkcja aplikacji."""
    # Tytuł aplikacji
    st.title("AgentMT5 Trading Monitor")
    
    # Pasek boczny
    st.sidebar.image("https://raw.githubusercontent.com/jeden-/Agent-MT5/master/docs/logo.png", width=150)
    st.sidebar.title("Nawigacja")
    
    # Opcje menu
    menu_options = [
        "Live Monitor",
        "Performance Dashboard",
        "AI Analytics",
        "System Status"
    ]
    
    selected_option = st.sidebar.radio("Wybierz widok:", menu_options)
    
    # Wyświetlanie właściwej zakładki
    if selected_option == "Live Monitor":
        render_live_monitor()
    elif selected_option == "Performance Dashboard":
        render_performance_dashboard()
    elif selected_option == "AI Analytics":
        render_ai_analytics()
    else:  # System Status
        render_system_status()
    
    # Informacja o ostatniej aktualizacji
    st.sidebar.info(f"Ostatnia aktualizacja: {format_date(datetime.now())}")
    
    # Auto-refresh
    if st.sidebar.checkbox("Auto-odświeżanie", value=True):
        st.empty()
        time.sleep(REFRESH_INTERVAL)
        st.experimental_rerun()

if __name__ == "__main__":
    main() 