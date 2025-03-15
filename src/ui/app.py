#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
AgentMT5 - Trading Agent Monitor
Interfejs użytkownika do monitorowania i zarządzania systemem handlowym AgentMT5.
"""

from src.mt5_bridge.mt5_api_client import get_mt5_api_client
from src.monitoring.alert_manager import AlertLevel, AlertCategory, AlertStatus
from src.monitoring.monitoring_logger import LogLevel, OperationType, OperationStatus
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
import logging
from src.utils.logging_config import get_current_log_path, read_recent_logs

# Importy dla modułu backtestingu
from src.backtest.backtest_engine import BacktestEngine, BacktestConfig
from src.backtest.strategy import TradingStrategy, SimpleMovingAverageStrategy, RSIStrategy
from src.backtest.strategy import BollingerBandsStrategy, MACDStrategy, CombinedIndicatorsStrategy
from src.backtest.historical_data_manager import HistoricalDataManager
from src.backtest.parameter_optimizer import ParameterOptimizer
from src.backtest.walk_forward_tester import WalkForwardTester
from src.backtest.backtest_metrics import calculate_metrics

# Dodane importy dla konfiguracji optymalizacji
from dataclasses import dataclass
from typing import Dict, List, Any, Optional

@dataclass
class OptimizationConfig:
    """Konfiguracja optymalizacji parametrów."""
    param_grid: Dict[str, List[Any]]
    fitness_metric: str = "sharpe_ratio"
    n_jobs: int = -1
    
@dataclass
class WalkForwardConfig:
    """Konfiguracja testowania walk-forward."""
    train_size: int  # dni
    test_size: int   # dni
    step: int        # dni
    optimize_metric: str = "sharpe_ratio"

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
sys.path.append(
    os.path.abspath(
        os.path.dirname(
            os.path.dirname(
                os.path.dirname(__file__)))))

# Import komponentów monitorowania

# Konfiguracja strony
st.set_page_config(
    page_title="AgentMT5 Monitor",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        'About': "# AgentMT5 Trading Monitor\nSystem monitorowania i zarządzania agentem handlowym MT5"
    }
)

# Stałe
SERVER_URL = os.getenv("SERVER_URL", "http://localhost:5555")
# sekundy - zwiększone z 5 do 10 sekund dla zmniejszenia obciążenia serwera
REFRESH_INTERVAL = 10
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

def handle_backtest_error(error, clear_session_state=True):
    """
    Obsługuje typowe błędy podczas backtestingu i wyświetla przyjazne komunikaty.
    
    Args:
        error: Wyjątek, który wystąpił podczas backtestingu
        clear_session_state: Czy wyczyścić stan sesji 'run_backtest'
    """
    error_str = str(error)
    
    if "No historical data available" in error_str or "Empty DataFrame" in error_str:
        st.error("📈 Brak danych historycznych dla wybranego instrumentu i okresu. Spróbuj zmienić parametry lub wybrać inny instrument.")
        st.info("💡 Wskazówka: Spróbuj krótszy okres lub wybierz instrument o większej płynności.")
    
    elif "Symbol not found" in error_str or "Symbol not available" in error_str:
        st.error("🔍 Wybrany instrument nie jest dostępny. Spróbuj wybrać inny instrument.")
        st.info("💡 Wskazówka: Sprawdź, czy symbol jest poprawnie wpisany i dostępny w MT5.")
    
    elif "Invalid timeframe" in error_str:
        st.error("⏱️ Nieprawidłowy timeframe. Wybierz jeden z dostępnych timeframe'ów.")
        st.info("💡 Wskazówka: Dostępne timeframe'y to: M1, M5, M15, M30, H1, H4, D1.")
    
    elif "Date range" in error_str:
        st.error("📅 Problem z zakresem dat. Upewnij się, że data początkowa jest wcześniejsza niż końcowa.")
        st.info("💡 Wskazówka: Wybierz krótszy zakres dat lub przesuń daty w przeszłość.")
    
    elif "No trades generated" in error_str:
        st.warning("📊 Strategia nie wygenerowała żadnych transakcji. Spróbuj zmienić parametry strategii.")
        st.info("💡 Wskazówka: Zwiększ długość okresu testowego lub zmodyfikuj parametry strategii, aby była bardziej agresywna.")
    
    elif "Not enough data points" in error_str:
        st.error("📉 Za mało punktów danych dla wybranych parametrów. Zmień parametry lub wydłuż okres testowy.")
        st.info("💡 Wskazówka: Niektóre wskaźniki wymagają minimalnej liczby punktów danych do obliczenia.")
    
    elif "Memory error" in error_str or "MemoryError" in error_str:
        st.error("💾 Błąd pamięci. Próba przetworzenia zbyt dużej ilości danych.")
        st.info("💡 Wskazówka: Zmniejsz zakres dat, wybierz wyższy timeframe lub ogranicz liczbę kombinacji parametrów.")
    
    elif "Timeout" in error_str:
        st.error("⏲️ Przekroczenie limitu czasu. Operacja trwała zbyt długo.")
        st.info("💡 Wskazówka: Zmniejsz złożoność operacji lub podziel ją na mniejsze części.")
    
    else:
        # Nieznany błąd - wyświetl oryginalną wiadomość
        st.error(f"❌ Wystąpił błąd podczas wykonywania backtestingu: {error_str}")
        st.info("📧 Jeśli problem się powtarza, zgłoś go deweloperom wraz z informacją o krokach, które doprowadziły do błędu.")
    
    # Opcjonalne czyszczenie stanu sesji
    if clear_session_state and 'run_backtest' in st.session_state:
        st.session_state.pop('run_backtest', None)

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
    /* Ukrywamy niepotrzebne metryki w sekcji Status Systemu */
    [data-testid="stMetricLabel"]:has(div:contains("Średnia Strata")),
    [data-testid="stMetricLabel"]:has(div:contains("Sharpe Ratio")),
    [data-testid="stMetricLabel"]:has(div:contains("Max DD")) {
        display: none;
    }
    [data-testid="stMetricValue"]:has(div:contains("21,35 zł")),
    [data-testid="stMetricValue"]:has(div:contains("1,65")),
    [data-testid="stMetricValue"]:has(div:contains("5,2%")) {
        display: none;
    }
</style>
""", unsafe_allow_html=True)


def api_request(endpoint, method="GET", data=None, params=None, timeout=5, json=None):
    """Wykonuje żądanie do API serwera."""
    # Ustawienie bezpośredniego adresu URL serwera, który wiemy że działa na porcie 5555
    server_url = os.environ.get("SERVER_URL", "http://localhost:5555")
    url = f"{server_url}{endpoint}" if endpoint.startswith('/') else f"{server_url}/{endpoint}"
    
    try:
        mt5_client = get_mt5_api_client(port=5555)
        if method == "GET":
            response = mt5_client.send_request(endpoint, method, params=params, data=None)
        elif method == "POST":
            # Przekazujemy parametr json zamiast data, jeśli json jest dostępny
            if json is not None:
                response = mt5_client.send_request(endpoint, method, params=params, data=json)
            else:
                response = mt5_client.send_request(endpoint, method, params=params, data=data)
        else:
            return None
        
        if response:
            return response
        
        # Logowanie błędów tylko raz na pewien czas, aby nie zaśmiecać logów
        if hasattr(api_request, "last_error_time"):
            if time.time() - api_request.last_error_time > 60:  # Loguj błędy co minutę
                st.warning(f"Nie można połączyć z serwerem API ({url}). Sprawdź czy serwer jest uruchomiony.")
                api_request.last_error_time = time.time()
        else:
            st.warning(f"Nie można połączyć z serwerem API ({url}). Sprawdź czy serwer jest uruchomiony.")
            api_request.last_error_time = time.time()
    except Exception as e:
        # Logowanie błędów tylko raz na pewien czas, aby nie zaśmiecać logów
        if hasattr(api_request, "last_error_time"):
            if time.time() - api_request.last_error_time > 60:  # Loguj błędy co minutę
                st.warning(f"Błąd podczas połączenia z serwerem API ({url}): {str(e)}")
                api_request.last_error_time = time.time()
        else:
            st.warning(f"Błąd podczas połączenia z serwerem API ({url}): {str(e)}")
            api_request.last_error_time = time.time()
    
    return None


def render_status_indicator(status):
    """Renderuje wskaźnik statusu jako HTML."""
    colors = {
        "ok": "green",
        "warning": "orange",
        "error": "red",
        "critical": "darkred",
        "unknown": "gray"
    }.get(status.lower(), "gray")
    color = colors.get(status.lower(), "gray")
    return f'<span style="color: {color}; font-weight: bold;">{status.upper()}</span>'


def render_live_monitor():
    """Renderuje zakładkę Live Monitor."""
    st.header("Monitor Trading Live")

    # Dodajemy przycisk odświeżania i wskaźnik automatycznego odświeżania
    refresh_col, sync_col, auto_refresh_col = st.columns([1, 1, 5])
    with refresh_col:
        if st.button("Odśwież", key="refresh_live_monitor"):
            st.rerun()
    with sync_col:
        if st.button("Synchronizuj z MT5", key="sync_with_mt5"):
            try:
                response = api_request("position/sync", method="POST")
                if response and response.get("status") == "ok":
                    st.success(f"Zsynchronizowano {response.get('positions_count', 0)} pozycji z MT5")
                    time.sleep(1)  # Krótkie oczekiwanie, aby użytkownik mógł zobaczyć komunikat
                    st.rerun()
                else:
                    error_msg = "Nieznany błąd" if not response else response.get('message', 'Nieznany błąd')
                    st.error(f"Błąd synchronizacji: {error_msg}")
            except Exception as e:
                st.error(f"Błąd podczas synchronizacji: {str(e)}")
    with auto_refresh_col:
        st.write(
            f"Dane odświeżają się automatycznie co {REFRESH_INTERVAL} sekund")

    # Pobierz aktywne połączenia
    connections_data = api_request("monitoring/connections")

    if not connections_data:
        st.error("Nie można połączyć się z serwerem MT5. Sprawdź połączenie.")
        # Nie wyświetlamy przykładowych danych, tylko informację o braku
        # połączenia
        st.warning(
            "Brak danych z serwera MT5. Interfejs wyświetla tylko informacje, gdy połączenie jest aktywne.")
        st.info("Sprawdź, czy serwer MT5 jest uruchomiony i dostępny.")
        return

    # Status systemu
    st.subheader("Status Systemu")

    # Pobranie statusu agenta przed wyświetleniem przycisków, aby wiedzieć który jest aktywny
    agent_status = api_request("agent/status")
    current_mode = agent_status.get("mode", "unknown") if agent_status else "unknown"
    
    # Dodanie sekcji kontroli agenta
    agent_cols = st.columns([1, 1, 1])
    
    # Funkcja do wyświetlania przycisku w odpowiednim kolorze
    def render_mode_button(col, mode, label, key):
        is_active = current_mode == mode
        button_style = f"""
        <style>
        div[data-testid="stButton"][aria-describedby="{key}"] button {{
            background-color: {"#4CAF50" if is_active else "#f0f2f6"};
            color: {"white" if is_active else "black"};
            font-weight: {"bold" if is_active else "normal"};
        }}
        </style>
        """
        col.markdown(button_style, unsafe_allow_html=True)
        
        if col.button(label, key=key):
            if is_active:
                st.info(f"Agent już pracuje w trybie {mode}")
                return False
            response = api_request("agent/start", method="POST", data={"mode": mode})
            if response and response.get("status") == "started":
                st.success(f"Agent uruchomiony w trybie {mode}")
                time.sleep(1)  # Krótkie oczekiwanie, aby użytkownik mógł zobaczyć komunikat
                st.rerun()
                return True
            else:
                error_msg = response.get('message', 'Nieznany błąd') if response else "Brak odpowiedzi z serwera"
                st.error(f"Błąd: {error_msg}")
                return False
        return False
    
    # Renderowanie przycisków z odpowiednim stylem
    with agent_cols[0]:
        render_mode_button(agent_cols[0], "observation", "Tryb Obserwacji", "mode_observation")
    
    with agent_cols[1]:
        render_mode_button(agent_cols[1], "semi_automatic", "Tryb Półautomatyczny", "mode_semi_automatic")
    
    with agent_cols[2]:
        render_mode_button(agent_cols[2], "automatic", "Tryb Automatyczny", "mode_automatic")
    
    # Wyświetlanie informacji o aktualnym trybie
    if agent_status:
        st.info(f"Aktualny tryb agenta: {agent_status.get('mode', 'Nieznany')}")
    
    # Usuwamy niepotrzebne metryki, które mogą być wyświetlane w interfejsie
    st.markdown("""
    <style>
    /* Ukrywamy niepotrzebne metryki w sekcji Status Systemu */
    [data-testid="stMetricLabel"]:has(div:contains("Średnia Strata")),
    [data-testid="stMetricLabel"]:has(div:contains("Sharpe Ratio")),
    [data-testid="stMetricLabel"]:has(div:contains("Max DD")) {
        display: none;
    }
    [data-testid="stMetricValue"]:has(div:contains("21,35 zł")),
    [data-testid="stMetricValue"]:has(div:contains("1,65")),
    [data-testid="stMetricValue"]:has(div:contains("5,2%")) {
        display: none;
    }
    </style>
    """, unsafe_allow_html=True)

    # Pobierz informacje o pozycjach
    positions_data = api_request("monitoring/positions")

    if positions_data and positions_data.get("status") == "ok":
        positions = positions_data.get("positions", [])
        # Oblicz łączny zysk/stratę z otwartych pozycji
        total_positions_profit = sum(pos.get("profit", 0) for pos in positions)
    else:
        positions = []
        total_positions_profit = 0

    if connections_data and "connections" in connections_data:
        for connection in connections_data["connections"]:
            metric_cols = st.columns(4)

            status = connection.get("status", "unknown")
            status_color = "green" if status == "active" else "red"

            # Pobierz rzeczywiste dane o koncie bezpośrednio z MT5
            account_data = api_request("mt5/account")
            if account_data and account_data.get("status") == "ok":
                account_info = account_data.get("account_info", {})
                account_balance = account_info.get("balance", 0)
                account_equity = account_info.get("equity", 0)
                # Używamy łącznego zysku z pozycji zamiast różnicy equity i balansu
                total_profit = total_positions_profit
            else:
                # Jeśli nie udało się pobrać danych o koncie, użyj danych z
                # połączenia lub obliczonego zysku z pozycji
                account_balance = connection.get("account_balance", 0)
                account_equity = connection.get("account_equity", 0)
                total_profit = total_positions_profit

            # Wyświetl dane o koncie i EA
            metric_cols[0].metric(
                label=f"Status EA {connection.get('ea_id', 'Unknown')}",
                value=status.upper(),
                delta=f"Ostatnia aktywność: {format_date(connection.get('last_ping', datetime.now().isoformat()))}",
                delta_color="off"
            )

            metric_cols[1].metric(
                label="Saldo Konta",
                value=format_currency(account_balance),
                delta=f"Equity: {format_currency(account_equity)}",
                delta_color="off"
            )

            profit_delta = None
            if positions:
                open_positions_count = len(positions)
                profit_delta = f"Otwarte pozycje: {open_positions_count}"

            # Dla delta_color w Streamlit używamy "normal" zamiast kolorów
            # Streamlit automatycznie użyje zielony dla dodatnich i czerwony
            # dla ujemnych
            profit_color = "normal"

            metric_cols[2].metric(
                label="Bieżący Zysk/Strata",
                value=format_currency(total_profit),
                delta=profit_delta,
                delta_color=profit_color
            )

            # Pobierz informacje o ostatnich transakcjach
            transactions_data = api_request(
                "monitoring/transactions", params={"limit": 5})

            if transactions_data and transactions_data.get("status") == "ok":
                transactions = transactions_data.get("transactions", [])
                if transactions:
                    last_transaction = transactions[0]
                    last_trans_profit = last_transaction.get("profit", 0)
                    last_trans_symbol = last_transaction.get(
                        "symbol", "Unknown")
                    last_trans_type = last_transaction.get("type", "Unknown")

                    # Kolor zielony/czerwony używany jest automatycznie przez Streamlit
                    # dla dodatnich/ujemnych wartości delta przy
                    # delta_color="normal"

                    metric_cols[3].metric(
                        label="Ostatnia Transakcja",
                        value=f"{last_trans_symbol} ({last_trans_type})",
                        delta=format_currency(last_trans_profit),
                        delta_color="normal"  # Używamy "normal" zamiast trans_color
                    )
                else:
                    metric_cols[3].metric(
                        label="Ostatnia Transakcja",
                        value="Brak transakcji",
                        delta=None
                    )
            else:
                metric_cols[3].metric(
                    label="Ostatnia Transakcja",
                    value="Dane niedostępne",
                    delta=None
                )

    # Dodajemy sekcję z aktualnymi pozycjami
    st.subheader("Aktywne Pozycje")

    if positions and len(positions) > 0:
        # Konwertuj dane pozycji do DataFrame
        positions_df = pd.DataFrame(positions)

        # Dodaj formatowanie
        if 'profit' in positions_df.columns:
            positions_df['profit_formatted'] = positions_df['profit'].apply(
                lambda x: f"<span style='color:{'green' if x > 0 else 'red'};'>{format_currency(x)}</span>"
            )

        if 'open_time' in positions_df.columns:
            positions_df['open_time'] = pd.to_datetime(
    positions_df['open_time']).dt.strftime('%Y-%m-%d %H:%M:%S')

        # Dodaj kolumnę z przyciskami akcji (tylko wizualnie)
        if 'ticket' in positions_df.columns:
            positions_df['akcje'] = positions_df['ticket'].apply(
                lambda x: f"<div style='text-align:center;'><span style='background-color:#f0f2f6;padding:2px 8px;border-radius:3px;margin-right:5px;'>Modyfikuj</span><span style='background-color:#f0f2f6;padding:2px 8px;border-radius:3px;'>Zamknij</span></div>"
            )

        # Wybierz kolumny do wyświetlenia
        display_columns = [
    'symbol',
    'type',
    'volume',
    'open_price',
    'sl',
    'tp',
    'open_time',
    'profit_formatted',
     'akcje']
        display_columns = [
    col for col in display_columns if col in positions_df.columns]

        # Zmień nazwy kolumn na bardziej przyjazne
        column_names = {
            'symbol': 'Instrument',
            'type': 'Typ',
            'volume': 'Wolumen',
            'open_price': 'Cena Otwarcia',
            'sl': 'Stop Loss',
            'tp': 'Take Profit',
            'open_time': 'Czas Otwarcia',
            'profit_formatted': 'Zysk/Strata',
            'akcje': 'Akcje'
        }

        # Przygotuj DataFrame do wyświetlenia
        display_df = positions_df[display_columns].rename(columns=column_names)

        # Wyświetl tabelę z pozycjami
        st.markdown(
    display_df.to_html(
        escape=False,
        index=False),
         unsafe_allow_html=True)

        # Dodaj podsumowanie pozycji
        total_profit = positions_df['profit'].sum(
        ) if 'profit' in positions_df.columns else 0
        profit_color = "green" if total_profit > 0 else "red" if total_profit < 0 else "gray"

        st.markdown(f"""
        <div style="margin-top: 10px; text-align: right;">
            <p style="font-weight: bold;">Łączny zysk/strata z otwartych pozycji:
                <span style="color: {profit_color};">{format_currency(total_profit)}</span>
            </p>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.info("Brak aktywnych pozycji")

        # Dodaj przycisk do ręcznego odświeżenia
        if st.button("Sprawdź ponownie", key="check_positions_again"):
            st.rerun()


def render_performance_dashboard():
    """Renderuje zakładkę Performance Dashboard."""
    st.header("Performance Dashboard")

    # Dodajemy przycisk odświeżania i wskaźnik automatycznego odświeżania
    refresh_col, auto_refresh_col = st.columns([1, 6])
    with refresh_col:
        if st.button("Odśwież", key="refresh_performance"):
            st.rerun()
    with auto_refresh_col:
        st.write(
            f"Dane odświeżają się automatycznie co {REFRESH_INTERVAL} sekund")

    # Pobierz dane o transakcjach
    transactions_data = api_request("monitoring/transactions")

    # Pobierz statystyki wydajności
    performance_data = api_request("monitoring/performance")

    # Pobierz dane konta bezpośrednio z MT5
    account_data = api_request("mt5/account")

    # Główne metryki
    st.subheader("Kluczowe Wskaźniki")

    metrics_cols = st.columns(6)

    if performance_data and performance_data.get("status") == "ok":
        metrics = performance_data.get("metrics", {})

        win_rate = metrics.get("win_rate", 0)
        profit_factor = metrics.get("profit_factor", 0)
        avg_profit = metrics.get("avg_profit", 0)
        avg_loss = metrics.get("avg_loss", 0)
        sharpe_ratio = metrics.get("sharpe_ratio", 0)
        max_drawdown = metrics.get("max_drawdown", 0)

        metrics_cols[0].metric(
    label="Win Rate",
     value=format_percentage(win_rate))
        metrics_cols[1].metric(
    label="Profit Factor",
    value=f"{profit_factor:.2f}".replace(
        ".",
         ","))
        metrics_cols[2].metric(
    label="Średni Zysk",
     value=format_currency(avg_profit))
        metrics_cols[3].metric(
    label="Średnia Strata",
     value=format_currency(avg_loss))
        metrics_cols[4].metric(
    label="Sharpe Ratio",
    value=f"{sharpe_ratio:.2f}".replace(
        ".",
         ","))
        metrics_cols[5].metric(
    label="Max DD",
     value=format_percentage(max_drawdown))
    else:
        # Wyświetl ostrzeżenie zamiast przykładowych danych
        st.warning(
            "Nie można pobrać danych statystycznych z serwera. Wyświetlanie rzeczywistych metryk jest niemożliwe.")

        # Pokaż podstawowe dane z konta, jeśli są dostępne
        if account_data and account_data.get("status") == "ok":
            account_info = account_data.get("account_info", {})
            balance = account_info.get("balance", 0)
            equity = account_info.get("equity", 0)

            metrics_cols[0].metric(
    label="Saldo", value=format_currency(balance))
            metrics_cols[1].metric(
    label="Equity", value=format_currency(equity))

    # Podział na dwie kolumny
    col1, col2 = st.columns(2)

    with col1:
        # Wykres wyników
        st.subheader("Wyniki Handlowe")

        if transactions_data and transactions_data.get("status") == "ok":
            transactions = transactions_data.get("transactions", [])
            if transactions:
                # Przygotuj dane do wykresu
                trans_df = pd.DataFrame(transactions)

                # Konwertuj datę zamknięcia na format datetime
                if 'close_time' in trans_df.columns:
                    trans_df['close_time'] = pd.to_datetime(
                        trans_df['close_time'])
                    trans_df = trans_df.sort_values('close_time')

                    # Oblicz skumulowany P/L
                    if 'profit' in trans_df.columns:
                        # Oblicz dzienne P/L
                        daily_pnl = trans_df.groupby(
    trans_df['close_time'].dt.date)['profit'].sum()
                        dates = daily_pnl.index
                        pnl_values = daily_pnl.values

                        # Oblicz skumulowany P/L
                        cum_pnl = np.cumsum(pnl_values)

                        # Utwórz wykres
                        fig = go.Figure()

                        # Dodaj skumulowany P/L
                        fig.add_trace(go.Scatter(
                            x=dates,
                            y=cum_pnl,
                            mode='lines+markers',
                            name='Skumulowany P/L',
                            line=dict(width=2, color='blue'),
                            marker=dict(size=6, color='blue')
                        ))

                        # Dodaj dzienny P/L jako słupki
                        fig.add_trace(go.Bar(
                            x=dates,
                            y=pnl_values,
                            name='Dzienny P/L',
                            marker_color=[
    'green' if x >= 0 else 'red' for x in pnl_values],
                            opacity=0.5
                        ))

                        # Konfiguruj układ
                        fig.update_layout(
                            title='Skumulowany i Dzienny P/L',
                            xaxis_title='Data',
                            yaxis_title='P/L (PLN)',
                            hovermode='x unified',
                            legend=dict(
    x=0.01, y=0.99, bgcolor='rgba(255,255,255,0.8)'),
                            margin=dict(l=0, r=0, t=30, b=0)
                        )

                        st.plotly_chart(fig, use_container_width=True)
                    else:
                        st.info("Brak danych o proficie w transakcjach")
                else:
                    st.info("Brak danych o czasie zamknięcia w transakcjach")
            else:
                st.info("Brak historii transakcji")
        else:
            st.warning("Nie można pobrać historii transakcji z serwera")

    with col2:
        # Wyniki per instrument
        st.subheader("Wyniki per Instrument")

        if transactions_data and transactions_data.get("status") == "ok":
            transactions = transactions_data.get("transactions", [])
            if transactions:
                # Przygotuj dane do wykresów
                trans_df = pd.DataFrame(transactions)

                if 'symbol' in trans_df.columns and 'profit' in trans_df.columns:
                    # Oblicz zysk per instrument
                    symbol_pnl = trans_df.groupby(
                        'symbol')['profit'].sum().sort_values(ascending=False)

                    # Przygotuj kolory
                    colors = [
    'green' if x >= 0 else 'red' for x in symbol_pnl.values]

                    # Utwórz wykres
                    fig = go.Figure(data=[
                        go.Bar(
                            x=symbol_pnl.index,
                            y=symbol_pnl.values,
                            marker_color=colors,
                            text=[format_currency(x)
                                                  for x in symbol_pnl.values],
                            textposition='auto'
                        )
                    ])

                    # Konfiguruj układ
                    fig.update_layout(
                        title='Wyniki per Instrument',
                        xaxis_title='Instrument',
                        yaxis_title='P/L (PLN)',
                        margin=dict(l=0, r=0, t=30, b=0)
                    )

                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("Brak danych o symbolu lub proficie w transakcjach")
            else:
                st.info("Brak historii transakcji")
        else:
            st.warning("Nie można pobrać historii transakcji z serwera")

    # Pełna historia transakcji
    st.subheader("Historia Transakcji")

    if transactions_data and transactions_data.get("status") == "ok":
        transactions = transactions_data.get("transactions", [])
        if transactions:
            # Przygotuj dane do tabeli
            trans_df = pd.DataFrame(transactions)

            # Dodaj formatowanie i przygotuj do wyświetlenia
            if 'profit' in trans_df.columns:
                trans_df['profit_formatted'] = trans_df['profit'].apply(
                    format_currency)

            if 'open_time' in trans_df.columns:
                trans_df['open_time'] = pd.to_datetime(
    trans_df['open_time']).dt.strftime('%Y-%m-%d %H:%M:%S')

            if 'close_time' in trans_df.columns:
                trans_df['close_time'] = pd.to_datetime(
    trans_df['close_time']).dt.strftime('%Y-%m-%d %H:%M:%S')

            # Wyświetl tabelę
            st.dataframe(trans_df, use_container_width=True)
        else:
            st.info("Brak historii transakcji")
    else:
        st.warning("Nie można pobrać historii transakcji z serwera")


def render_ai_analytics():
    """Renderuje zakładkę AI Analytics."""
    st.header("Analityka AI")

    # Inicjalizacja zmiennych sesji
    if "scroll_to_signal_gen" not in st.session_state:
        st.session_state.scroll_to_signal_gen = False

    # Dodajemy przycisk odświeżania i wskaźnik automatycznego odświeżania
    refresh_col, auto_refresh_col = st.columns([1, 6])
    with refresh_col:
        if st.button("Odśwież", key="refresh_ai_analytics"):
            st.rerun()
    with auto_refresh_col:
        st.write(
            f"Dane odświeżają się automatycznie co {REFRESH_INTERVAL} sekund")

    # Pobierz dane o modelach AI
    ai_models_data = api_request("ai/models")

    # Zapewnij, że ai_models_data nie jest None przed próbą uzyskania dostępu do jego atrybutów
    if ai_models_data is None:
        ai_models_data = {"status": "error", "message": "Nie udało się połączyć z API"}

    # Pobierz dane o sygnałach AI
    ai_signals_data = api_request("ai/signals")
    
    # Pobierz dane o kosztach AI
    ai_costs_data = api_request("ai/costs")
    
    # Zapewnij, że ai_costs_data nie jest None przed próbą uzyskania dostępu do jego atrybutów
    if ai_costs_data is None:
        ai_costs_data = {"status": "error", "message": "Nie udało się połączyć z API"}

    # Sprawdź czy dane są dostępne
    if not ai_models_data or not ai_signals_data:
        st.warning("Nie można pobrać danych AI z serwera. Sprawdź połączenie.")
        st.info("Analityka AI będzie dostępna po ustanowieniu połączenia z serwerem.")
        return

    # Dodajemy nową sekcję na górze dla aktualnych sygnałów
    st.subheader("Aktualne Sygnały Handlowe")

    # Pobierz najnowsze sygnały
    latest_signals_data = api_request("ai/signals/latest")

    if latest_signals_data and latest_signals_data.get("status") == "ok":
        latest_signals = latest_signals_data.get("signals", [])

        if latest_signals:
            # Utwórz kolumny dla sygnałów
            signal_cols = st.columns(
    len(latest_signals) if len(latest_signals) <= 4 else 4)

            # Wyświetl każdy sygnał w osobnej kolumnie
            for i, signal in enumerate(
                latest_signals[:4]):  # Maksymalnie 4 sygnały
                col_idx = i % 4

                signal_model = signal.get('model_name', signal.get('model', 'Unknown'))
                signal_symbol = signal.get('symbol', 'Unknown')
                signal_type = signal.get('direction', signal.get('type', 'Unknown'))
                signal_confidence = signal.get('confidence', 0)
                signal_time = signal.get('timestamp', '')

                if isinstance(signal_time, str):
                    try:
                        signal_time = datetime.fromisoformat(
                            signal_time.replace('Z', '+00:00'))
                        signal_time = signal_time.strftime('%Y-%m-%d %H:%M:%S')
                    except:
                        pass

                # Ustal kolor dla typu sygnału
                signal_color = 'green' if signal_type.lower(
                ) == 'buy' else 'red' if signal_type.lower() == 'sell' else 'blue'

                # Wyświetl sygnał w atrakcyjnym formacie
                signal_cols[col_idx].markdown(f"""
                <div style="border: 1px solid {signal_color}; border-radius: 5px; padding: 10px; text-align: center; height: 100%;">
                    <h3 style="margin: 0; color: {signal_color};">{signal_symbol}</h3>
                    <p style="font-size: 1.5em; font-weight: bold; margin: 5px 0;">{signal_type.upper()}</p>
                    <div style="background-color: {signal_color}; width: {signal_confidence*100}%; height: 5px; margin: 5px auto;"></div>
                    <p style="margin: 5px 0;">Pewność: {signal_confidence:.1%}</p>
                    <p style="margin: 0; font-size: 0.8em; color: gray;">Model: {signal_model}</p>
                    <p style="margin: 0; font-size: 0.8em; color: gray;">{signal_time}</p>
                </div>
                """, unsafe_allow_html=True)

            # Jeśli jest więcej sygnałów, dodaj przycisk "Zobacz wszystkie"
            if len(latest_signals) > 4:
                st.markdown(
    f"<p style='text-align: right;'><em>Wyświetlono 4 z {len(latest_signals)} sygnałów</em></p>",
     unsafe_allow_html=True)
                if st.button(
    "Zobacz wszystkie sygnały",
     key="view_all_signals"):
                    st.session_state.show_all_signals = True

            # Jeśli użytkownik kliknął "Zobacz wszystkie", wyświetl tabelę ze
            # wszystkimi sygnałami
            if st.session_state.get("show_all_signals", False):
                st.subheader("Wszystkie Aktualne Sygnały")

                # Konwertuj dane do DataFrame
                signals_df = pd.DataFrame(latest_signals)

                # Formatuj dane
                if 'timestamp' in signals_df.columns:
                    signals_df['timestamp'] = pd.to_datetime(signals_df['timestamp']).dt.strftime('%Y-%m-%d %H:%M:%S')

                if 'confidence' in signals_df.columns:
                    signals_df['confidence'] = signals_df['confidence'].apply(
                        lambda x: f"{x:.1%}")

                # Wybierz kolumny do wyświetlenia
                display_columns = [
    'symbol',
    'direction',
    'confidence',
    'model_name',
     'timestamp']
                display_columns = [
    col for col in display_columns if col in signals_df.columns]

                # Zmień nazwy kolumn
                column_names = {
                    'symbol': 'Instrument',
                    'direction': 'Typ Sygnału',
                    'type': 'Typ Sygnału',  # Dla kompatybilności
                    'confidence': 'Pewność',
                    'model_name': 'Model AI',
                    'model': 'Model AI',  # Dla kompatybilności
                    'timestamp': 'Czas'
                }

                # Wyświetl tabelę
                st.dataframe(
    signals_df[display_columns].rename(
        columns=column_names),
         use_container_width=True)

                # Przycisk do zamknięcia widoku wszystkich sygnałów
                if st.button("Ukryj szczegóły", key="hide_all_signals"):
                    st.session_state.show_all_signals = False
                    st.rerun()
        else:
            st.info("Brak aktualnych sygnałów handlowych")
    else:
        st.warning("Nie można pobrać aktualnych sygnałów handlowych")

    # Podział na dwie kolumny
    col1, col2 = st.columns(2)

    with col1:
        # Wydajność modeli AI
        st.subheader("Wydajność Modeli AI")

        if ai_models_data and "status" in ai_models_data:
            status = ai_models_data.get("status", "")
            
            # Obsługa różnych statusów
            if status == "error":
                st.error("Nie udało się pobrać danych o modelach AI")
                st.info(ai_models_data.get("message", "Sprawdź połączenie z serwerem."))
            elif status == "demo":
                st.warning("Wyświetlane są dane demonstracyjne")
                st.info(ai_models_data.get("message", "Rzeczywiste dane będą dostępne po wykonaniu zapytań do modeli AI."))
                
                # Kontynuuj wyświetlanie danych demonstracyjnych z wyraźnym oznaczeniem
                models_info = ai_models_data.get("models", [])
                if models_info:
                    # Przygotuj dane do wykresu
                    model_names = []
                    accuracy_values = []
                    roi_values = []

                    for model in models_info:
                        model_names.append(model.get("name", ""))
                        accuracy_values.append(model.get("accuracy", 0))
                        roi_values.append(model.get("roi", 0))

                    model_data = pd.DataFrame({
                        "Model": model_names,
                        "Dokładność": accuracy_values,
                        "ROI": roi_values
                    })

                    # Dodaj informację, że są to dane demonstracyjne
                    st.markdown("""
                    <div style="border-left: 4px solid orange; padding-left: 10px; background-color: rgba(255, 165, 0, 0.1); padding: 10px; border-radius: 5px; margin-bottom: 15px;">
                      <h4 style="margin-top: 0;">Dane Demonstracyjne</h4>
                      <p>Poniższe wykresy i tabele pokazują <b>przykładowe</b> dane. Rzeczywiste dane będą widoczne gdy agent zacznie używać modeli AI.</p>
                    </div>
                    """, unsafe_allow_html=True)

                    # Wyświetl jako interaktywny wykres
                    fig = go.Figure()

                    # Dodaj dokładność jako słupki
                    fig.add_trace(go.Bar(
                        x=model_data['Model'],
                        y=model_data['Dokładność'],
                        name='Dokładność',
                        marker_color='royalblue',
                        text=[format_percentage(x)
                                                for x in model_data['Dokładność']],
                        textposition='auto'
                    ))

                    # Dodaj ROI jako punkty
                    fig.add_trace(go.Scatter(
                        x=model_data['Model'],
                        y=model_data['ROI'],
                        yaxis="y2",
                        name='ROI',
                        mode='markers+lines',
                        marker=dict(size=10, color='green', symbol='circle'),
                        text=[format_percentage(x) for x in model_data['ROI']]
                    ))

                    # Ustaw podwójną oś Y
                    fig.update_layout(
                        title='Wydajność Modeli AI (Dane Demonstracyjne)',
                        yaxis=dict(
                            title='Dokładność',
                            range=[0, 1],
                            tickformat='.0%'
                        ),
                        yaxis2=dict(
                            title='ROI',
                            overlaying='y',
                            side='right',
                            tickformat='.0%',
                            range=[min(model_data['ROI']) * 1.1 if min(model_data['ROI']) < 0 else 0,
                           max(model_data['ROI']) * 1.1 if max(model_data['ROI']) > 0 else 0.1]
                        ),
                        margin=dict(l=0, r=0, t=30, b=0),
                        legend=dict(
                            orientation="h",
                            yanchor="bottom",
                            y=1.02,
                            xanchor="right",
                            x=1
                        )
                    )

                    st.plotly_chart(fig, use_container_width=True)

                    # Wyświetl dane w tabeli
                    st.subheader("Szczegóły modeli AI (Dane Demonstracyjne)")
                    formatted_data = model_data.copy()
                    formatted_data['Dokładność'] = formatted_data['Dokładność'].apply(
                        format_percentage)
                    formatted_data['ROI'] = formatted_data['ROI'].apply(
                        format_percentage)
                    st.dataframe(formatted_data, use_container_width=True)
                else:
                    st.info("Brak danych o modelach AI")
            elif status == "ok":
                # Wyświetl rzeczywiste dane
                models_info = ai_models_data.get("models", [])
                if models_info:
                    # Przygotuj dane do wykresu
                    model_names = []
                    accuracy_values = []
                    roi_values = []

                    for model in models_info:
                        model_names.append(model.get("name", ""))
                        accuracy_values.append(model.get("accuracy", 0))
                        roi_values.append(model.get("roi", 0))

                    model_data = pd.DataFrame({
                        "Model": model_names,
                        "Dokładność": accuracy_values,
                        "ROI": roi_values
                    })

                    # Wyświetl jako interaktywny wykres
                    fig = go.Figure()

                    # Dodaj dokładność jako słupki
                    fig.add_trace(go.Bar(
                        x=model_data['Model'],
                        y=model_data['Dokładność'],
                        name='Dokładność',
                        marker_color='royalblue',
                        text=[format_percentage(x)
                                                for x in model_data['Dokładność']],
                        textposition='auto'
                    ))

                    # Dodaj ROI jako punkty
                    fig.add_trace(go.Scatter(
                        x=model_data['Model'],
                        y=model_data['ROI'],
                        yaxis="y2",
                        name='ROI',
                        mode='markers+lines',
                        marker=dict(size=10, color='green', symbol='circle'),
                        text=[format_percentage(x) for x in model_data['ROI']]
                    ))

                    # Ustaw podwójną oś Y
                    fig.update_layout(
                        title='Wydajność Modeli AI',
                        yaxis=dict(
                            title='Dokładność',
                            range=[0, 1],
                            tickformat='.0%'
                        ),
                        yaxis2=dict(
                            title='ROI',
                            overlaying='y',
                            side='right',
                            tickformat='.0%',
                            range=[min(model_data['ROI']) * 1.1 if min(model_data['ROI']) < 0 else 0,
                           max(model_data['ROI']) * 1.1 if max(model_data['ROI']) > 0 else 0.1]
                        ),
                        margin=dict(l=0, r=0, t=30, b=0),
                        legend=dict(
                            orientation="h",
                            yanchor="bottom",
                            y=1.02,
                            xanchor="right",
                            x=1
                        )
                    )

                    st.plotly_chart(fig, use_container_width=True)

                    # Wyświetl dane w tabeli
                    st.subheader("Szczegóły modeli AI")
                    formatted_data = model_data.copy()
                    formatted_data['Dokładność'] = formatted_data['Dokładność'].apply(
                        format_percentage)
                    formatted_data['ROI'] = formatted_data['ROI'].apply(
                        format_percentage)
                    st.dataframe(formatted_data, use_container_width=True)
                else:
                    st.info("Brak danych o modelach AI")
            else:
                st.warning("Nieznany status danych o modelach AI: " + status)
                st.info("Sprawdź połączenie z serwerem lub skontaktuj się z administratorem.")
        else:
            st.warning("Nie można pobrać danych o modelach AI")

    with col2:
        # Analiza sygnałów AI
        st.subheader("Analiza Sygnałów AI")

        if ai_signals_data and ai_signals_data.get("status") == "ok":
            signals = ai_signals_data.get("signals", [])
            if signals:
                # Przygotuj dane do analizy
                signals_df = pd.DataFrame(signals)

                if 'timestamp' in signals_df.columns:
                    signals_df['timestamp'] = pd.to_datetime(signals_df['timestamp'])

                if 'model' in signals_df.columns and 'confidence' in signals_df.columns:
                    # Grupuj dane wg modelu
                    model_confidence = signals_df.groupby(
                        'model')['confidence'].mean().sort_values(ascending=False)

                    # Przygotuj wykres
                    fig = go.Figure(data=[
                        go.Bar(
                            x=model_confidence.index,
                            y=model_confidence.values,
                            marker_color='purple',
                            text=[f"{x:.1%}".replace(".", ",") for x in model_confidence.values],
                            textposition='auto'
                        )
                    ])

                    fig.update_layout(
                        title='Średnia Pewność Sygnałów wg Modelu',
                        xaxis_title='Model AI',
                        yaxis_title='Średnia Pewność',
                        yaxis=dict(tickformat='.0%'),
                        margin=dict(l=0, r=0, t=30, b=0)
                    )

                    st.plotly_chart(fig, use_container_width=True)

                    # Najnowsze sygnały handlowe
                    st.subheader("Najnowsze Sygnały Handlowe")

                    if len(signals) > 0:
                        # Sortuj sygnały wg czasu (od najnowszych)
                        if 'timestamp' in signals_df.columns:
                            signals_df = signals_df.sort_values(
                                'timestamp', ascending=False)

                        # Przygotuj dane do wyświetlenia
                        # Pokaż 5 najnowszych sygnałów
                        latest_signals = signals_df.head(5)

                        for _, signal in latest_signals.iterrows():
                            signal_model = signal.get('model', 'Unknown')
                            signal_symbol = signal.get('symbol', 'Unknown')
                            signal_type = signal.get('type', 'Unknown')
                            signal_confidence = signal.get('confidence', 0)
                            signal_time = signal.get('timestamp', '')

                            if isinstance(signal_time, pd.Timestamp):
                                signal_time = signal_time.strftime(
                                    '%Y-%m-%d %H:%M:%S')

                            # Ustal kolor dla typu sygnału
                            signal_color = 'green' if signal_type.lower() == 'buy' else 'red' if signal_type.lower() == 'sell' else 'blue'

                            # Wyświetl sygnał w atrakcyjnym formacie
                            st.markdown(f"""
                            <div style="border-left: 5px solid {signal_color}; padding-left: 10px; margin-bottom: 10px;">
                                <p style="margin: 0; font-weight: bold;">{signal_symbol} - {signal_type.upper()}</p>
                                <p style="margin: 0; color: gray;">Model: {signal_model} | Pewność: {signal_confidence:.1%} | {signal_time}</p>
                            </div>
                            """, unsafe_allow_html=True)
                    else:
                        st.info("Brak sygnałów handlowych")
                else:
                    st.info("Brak danych o modelach i pewności sygnałów")
            else:
                st.info("Brak danych o sygnałach AI")
        else:
            st.warning("Nie można pobrać danych o sygnałach AI")

    # Analiza korelacji sygnałów AI i transakcji
    st.subheader("Analiza Korelacji AI i Wyników Handlowych")
    
    # Pobierz dane o transakcjach
    transactions_data = api_request("monitoring/transactions")
    
    # Dane powinny zawierać i sygnały, i transakcje
    if ai_signals_data and transactions_data:
        signals = ai_signals_data.get("signals", [])
        transactions = transactions_data.get("transactions", [])
        
        # Sprawdź czy są rzeczywiste dane czy demonstracyjne
        ai_signals_status = ai_signals_data.get("status", "")
        transactions_status = transactions_data.get("status", "")
        
        if ai_signals_status == "error" or transactions_status == "error":
            st.error("Nie udało się pobrać danych o sygnałach AI lub transakcjach")
            st.info("Sprawdź połączenie z serwerem.")
        elif ai_signals_status == "demo" or transactions_status == "demo" or "status" not in ai_signals_data:
            # Wyświetl informację o danych demonstracyjnych
            st.warning("Wyświetlane są dane demonstracyjne")
            st.info("Rzeczywiste dane będą dostępne po wykonaniu zapytań do modeli AI i zawarciu transakcji.")
            
            # Dodaj szczegółową informację o danych demonstracyjnych
            st.markdown("""
            <div style="border-left: 4px solid orange; padding-left: 10px; background-color: rgba(255, 165, 0, 0.1); padding: 10px; border-radius: 5px; margin-bottom: 15px;">
              <h4 style="margin-top: 0;">Dane Demonstracyjne</h4>
              <p>Poniższe analizy pokazują <b>przykładowe</b> korelacje między sygnałami AI a wynikami handlowymi. Rzeczywiste dane będą widoczne gdy agent zacznie generować sygnały i zawierać transakcje.</p>
              <p>Aby zacząć gromadzić rzeczywiste dane:</p>
              <ol>
                <li>Aktywuj modele AI w ustawieniach agenta</li>
                <li>Przełącz agenta w tryb automatyczny lub generuj sygnały ręcznie</li>
                <li>Wykonaj co najmniej kilka transakcji na podstawie wygenerowanych sygnałów</li>
              </ol>
            </div>
            """, unsafe_allow_html=True)
            
            # Kontynuuj wyświetlanie danych demonstracyjnych jeśli są dostępne
            if signals and transactions:
                # Konwersja do DataFrame
                signals_df = pd.DataFrame(signals)
                transactions_df = pd.DataFrame(transactions)
                
                # Kontynuuj z kodem analizy korelacji...
            else:
                st.info("Brak danych demonstracyjnych do wyświetlenia")
        elif not signals or not transactions:
            st.warning("Nie można pobrać kompletnych danych o sygnałach AI i transakcjach")
            st.info("""
            Brak wystarczających danych do analizy korelacji. 
            
            Aby zobaczyć analizę korelacji:
            1. Upewnij się, że agent generuje sygnały AI
            2. Zawrzyj transakcje na podstawie tych sygnałów
            3. Poczekaj, aż zostanie zgromadzona wystarczająca ilość danych
            """)
        else:
            # Normalne działanie z rzeczywistymi danymi
            # Konwersja do DataFrame
            signals_df = pd.DataFrame(signals)
            transactions_df = pd.DataFrame(transactions)
            
            # Kontynuuj z kodem analizy korelacji...
    else:
        st.warning("Nie można pobrać kompletnych danych o sygnałach AI i transakcjach")
        st.info("""
        Brak połączenia z serwerem lub serwer nie zwrócił oczekiwanych danych. 
        
        Możliwe przyczyny:
        1. Serwer MT5 Bridge nie jest uruchomiony
        2. Nie ma połączenia z platformą MT5
        3. Wystąpił błąd podczas przetwarzania żądania
        
        Sprawdź logi serwera lub spróbuj ponownie później.
        """)

def render_system_status():
    """Renderuje zakładkę System Status."""
    st.header("Status Systemu")
    
    # Dodajemy przycisk odświeżania i wskaźnik automatycznego odświeżania
    refresh_col, auto_refresh_col = st.columns([1, 6])
    with refresh_col:
        if st.button("Odśwież", key="refresh_system_status"):
            st.rerun()
    with auto_refresh_col:
        st.write(f"Dane odświeżają się automatycznie co {REFRESH_INTERVAL} sekund")
    
    # Pobierz dane o statusie agenta
    agent_status = api_request("agent/status")
    
    # Pobierz dane o koncie
    account_info = api_request("mt5/account")
    
    # Wyświetl główne informacje o statusie
    st.subheader("Status Agenta")
    
    if agent_status:
        status_value = agent_status.get("status", "unknown")
        mode_value = agent_status.get("mode", "unknown")
        uptime = agent_status.get("uptime", "N/A")
        
        status_color = "green" if status_value == "running" else "red" if status_value == "stopped" else "orange"
        
        st.markdown(f"""
        <div style="border: 1px solid #ddd; padding: 15px; border-radius: 5px; margin-bottom: 20px;">
            <p style="margin: 0;"><strong>Status: </strong><span style="color: {status_color};">{status_value.upper()}</span></p>
            <p style="margin: 0;"><strong>Tryb pracy: </strong>{mode_value}</p>
            <p style="margin: 0;"><strong>Czas działania: </strong>{uptime}</p>
        </div>
        """, unsafe_allow_html=True)
        
        if agent_status.get("error"):
            st.error(f"Błąd agenta: {agent_status.get('error')}")
    else:
        st.error("Nie można pobrać statusu agenta")
    
    # Wyświetl informacje o komponentach systemu
    st.subheader("Komponenty Systemu")
    
    components = [
        {"name": "MT5 Bridge", "status": "ok" if api_request("ping") else "error"},
        {"name": "Agent Controller", "status": "ok" if agent_status else "error"},
        {"name": "Database", "status": "ok"},  # Tutaj możesz dodać faktyczną logikę sprawdzania bazy
        {"name": "API Server", "status": "ok" if api_request("ping") else "error"}
    ]
    
    # Funkcja do ustalania koloru na podstawie statusu
    def get_component_color(status):
        return "green" if status == "ok" else "red" if status == "error" else "orange"
    
    # Wyświetl status komponentów
    components_cols = st.columns(4)
    for i, component in enumerate(components):
        col_idx = i % 4
        status_color = get_component_color(component["status"])
        
        components_cols[col_idx].markdown(f"""
        <div style="border: 1px solid {status_color}; padding: 10px; border-radius: 5px; text-align: center;">
            <h4 style="margin: 0;">{component["name"]}</h4>
            <p style="color: {status_color}; font-weight: bold; margin: 5px 0;">{component["status"].upper()}</p>
        </div>
        """, unsafe_allow_html=True)
    
    # Wyświetl informacje o zasobach
    st.subheader("Zasoby Systemu")
    
    # Tutaj możesz dodać informacje o zużyciu CPU, RAM, itp.
    # Dla uproszczenia, wyświetlamy przykładowe dane
    
    resources_cols = st.columns(3)
    resources_cols[0].metric(label="CPU", value="23%", delta="5% więcej niż zwykle", delta_color="inverse")
    resources_cols[1].metric(label="RAM", value="1.2 GB", delta="0.1 GB mniej niż zwykle", delta_color="normal")
    resources_cols[2].metric(label="Dysk", value="45 GB", delta="3% zajętości", delta_color="off")

def render_control_panel():
    """Renderuje zakładkę Control Panel."""
    st.header("Panel Kontrolny")
    
    # Dodajemy przycisk odświeżania i wskaźnik automatycznego odświeżania
    refresh_col, auto_refresh_col = st.columns([1, 6])
    with refresh_col:
        if st.button("Odśwież", key="refresh_control_panel"):
            st.rerun()
    with auto_refresh_col:
        st.write(f"Dane odświeżają się automatycznie co {REFRESH_INTERVAL} sekund")
    
    # Pobierz dane o statusie agenta
    agent_status = api_request("agent/status")
    current_mode = agent_status.get("mode", "unknown") if agent_status else "unknown"
    
    # Panel kontroli agenta
    st.subheader("Kontrola Agenta")
    
    # Przyciski do kontroli agenta
    control_cols = st.columns(4)
    
    with control_cols[0]:
        if st.button("Start", key="start_agent", type="primary"):
            response = api_request("agent/start", method="POST", json={"mode": current_mode})
            if response and response.get("status") == "ok":
                st.success(f"Agent uruchomiony w trybie {current_mode}")
                time.sleep(1)
                st.rerun()
            else:
                st.error("Nie udało się uruchomić agenta")
    
    with control_cols[1]:
        if st.button("Stop", key="stop_agent", type="primary"):
            response = api_request("agent/stop", method="POST")
            if response and response.get("status") == "ok":
                st.success("Agent zatrzymany")
                time.sleep(1)
                st.rerun()
            else:
                st.error("Nie udało się zatrzymać agenta")
    
    with control_cols[2]:
        if st.button("Restart", key="restart_agent", type="primary"):
            response = api_request("agent/restart", method="POST", json={"mode": current_mode})
            if response and response.get("status") == "ok":
                st.success(f"Agent zrestartowany w trybie {current_mode}")
                time.sleep(1)
                st.rerun()
            else:
                st.error("Nie udało się zrestartować agenta")
    
    with control_cols[3]:
        if st.button("Synchronizuj z MT5", key="sync_positions"):
            response = api_request("position/sync", method="POST")
            if response and response.get("status") == "ok":
                st.success(f"Zsynchronizowano {response.get('positions_count', 0)} pozycji")
                time.sleep(1)
                st.rerun()
            else:
                st.error("Nie udało się zsynchronizować pozycji")
    
    # Konfiguracja agenta
    st.subheader("Konfiguracja Agenta")
    
    # Pobierz aktualną konfigurację
    agent_config = api_request("agent/config")
    
    # Tryb pracy
    st.write("Tryb pracy agenta:")
    mode_options = ["observation", "semi_automatic", "automatic"]
    selected_mode = st.selectbox("Wybierz tryb:", mode_options, index=mode_options.index(current_mode) if current_mode in mode_options else 0)
    
    # Limity ryzyka
    st.write("Limity ryzyka:")
    risk_cols = st.columns(3)
    
    # Pobierz aktualne wartości z konfiguracji
    current_risk_limits = agent_config.get("risk_limits", {}) if agent_config else {}
    
    max_risk_per_trade = risk_cols[0].number_input(
        "Max ryzyko na transakcję (%)", 
        min_value=0.1, 
        max_value=10.0, 
        value=current_risk_limits.get("max_risk_per_trade_percent", 1.0) * 100 if current_risk_limits else 1.0, 
        step=0.1
    )
    
    max_daily_risk = risk_cols[1].number_input(
        "Max ryzyko dzienne (%)", 
        min_value=1.0, 
        max_value=20.0, 
        value=current_risk_limits.get("daily_loss_limit_percent", 5.0) if current_risk_limits else 5.0, 
        step=0.5
    )
    
    max_positions = risk_cols[2].number_input(
        "Max liczba pozycji", 
        min_value=1, 
        max_value=50, 
        value=current_risk_limits.get("max_positions_total", 10) if current_risk_limits else 10, 
        step=1
    )
    
    # Przyciski zatwierdzania konfiguracji
    if st.button("Zastosuj konfigurację", type="primary"):
        # Przygotuj dane konfiguracyjne
        config_data = {
            "mode": selected_mode,
            "risk_limits": {
                "max_risk_per_trade": max_risk_per_trade / 100,  # Konwersja na ułamek
                "max_daily_risk": max_daily_risk / 100,  # Konwersja na ułamek
                "max_positions": int(max_positions)
            }
        }
        
        # Wyślij konfigurację
        response = api_request("agent/config", method="POST", json=config_data)
        if response and response.get("status") == "ok":
            st.success("Konfiguracja zaktualizowana")
            time.sleep(1)
            st.rerun()
        else:
            st.error("Nie udało się zaktualizować konfiguracji")
    
    # Historia konfiguracji
    st.subheader("Historia Konfiguracji")
    
    # Pobierz historię konfiguracji
    config_history = api_request("agent/config/history")
    
    if config_history and config_history.get("status") == "ok":
        configs = config_history.get("configs", [])
        if configs:
            # Konwersja do DataFrame
            configs_df = pd.DataFrame(configs)
            
            # Formatowanie daty
            if 'timestamp' in configs_df.columns:
                configs_df['timestamp'] = pd.to_datetime(configs_df['timestamp']).dt.strftime('%Y-%m-%d %H:%M:%S')
            
            # Wyświetl tabelę
            st.dataframe(configs_df, use_container_width=True)
            
            # Przycisk do przywracania konfiguracji
            selected_config = st.selectbox("Wybierz konfigurację do przywrócenia:", configs_df['id'].tolist())
            
            if st.button("Przywróć wybraną konfigurację"):
                response = api_request("agent/config/restore", method="POST", json={"config_id": selected_config})
                if response and response.get("status") == "ok":
                    st.success("Konfiguracja przywrócona")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("Nie udało się przywrócić konfiguracji")
        else:
            st.info("Brak historii konfiguracji")
    else:
        st.warning("Nie można pobrać historii konfiguracji")

def render_logs_view():
    """Renderuje zakładkę Logs."""
    st.header("Logi Systemowe")
    
    # Dodajemy przycisk odświeżania i wskaźnik automatycznego odświeżania
    refresh_col, auto_refresh_col = st.columns([1, 6])
    with refresh_col:
        if st.button("Odśwież", key="refresh_logs"):
            st.rerun()
    with auto_refresh_col:
        st.write(f"Dane odświeżają się automatycznie co {REFRESH_INTERVAL} sekund")
    
    # Pobierz ścieżkę do aktualnego pliku logów
    log_path = get_current_log_path()
    
    # Pokaż ścieżkę do pliku logów
    st.write(f"Aktualny plik logów: {log_path}")
    
    # Opcje filtrowania
    st.subheader("Filtry")
    
    filter_cols = st.columns(3)
    
    with filter_cols[0]:
        log_level = st.selectbox("Poziom logów:", ["ALL", "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"], index=2)
    
    with filter_cols[1]:
        component = st.selectbox("Komponent:", ["ALL", "Agent", "MT5 Bridge", "Database", "API Server"])
    
    with filter_cols[2]:
        num_lines = st.number_input("Liczba linii:", min_value=10, max_value=1000, value=100, step=10)
    
    # Pobierz i wyświetl logi
    logs = read_recent_logs(log_path, num_lines)
    
    # Filtruj logi według poziomu
    if log_level != "ALL":
        logs = [log for log in logs if log_level in log]
    
    # Filtruj logi według komponentu
    if component != "ALL":
        logs = [log for log in logs if component in log]
    
    # Wyświetl logi w formie tekstowej z odpowiednim formatowaniem
    log_text = "\n".join(logs)
    
    # Używamy monospace font dla lepszej czytelności logów
    st.text_area("Logi:", log_text, height=500)
    
    # Dodaj przyciski do pobrania logów
    download_cols = st.columns(3)
    
    with download_cols[0]:
        if st.button("Pobierz pełne logi"):
            # W rzeczywistej aplikacji tutaj byłby kod do przygotowania pliku do pobrania
            st.info("Funkcja pobierania logów jest obecnie niedostępna.")
    
    with download_cols[1]:
        if st.button("Wyślij logi do wsparcia"):
            # W rzeczywistej aplikacji tutaj byłby kod do wysłania logów
            st.info("Funkcja wysyłania logów jest obecnie niedostępna.")
    
    with download_cols[2]:
        if st.button("Wyczyść logi"):
            # W rzeczywistej aplikacji tutaj byłby kod do czyszczenia logów
            st.info("Funkcja czyszczenia logów jest obecnie niedostępna.")

def check_mt5_connection():
    """Sprawdza status połączenia z serwerem MT5."""
    try:
        connections_data = api_request("monitoring/connections")
        if connections_data and "connections" in connections_data:
            connection = connections_data["connections"][0]
            return connection
        return None
    except Exception as e:
        logging.error(f"Błąd podczas sprawdzania połączenia z MT5: {e}")
        return None

def render_backtesting_tab():
    st.title("📊 Backtesting")
    
    st.markdown("System backtestingu umożliwiający testowanie strategii handlowych na danych historycznych. Skonfiguruj parametry testu, wybierz strategię i analizuj wyniki.")
    
    # Dodanie przełącznika trybów
    mode = st.radio(
        "Wybierz tryb backtestingu:",
        ["Automatyczny (dla początkujących)", "Zaawansowany (dla ekspertów)"],
        horizontal=True,
        index=0 if 'backtest_mode' not in st.session_state else 
              (0 if st.session_state.backtest_mode == 'auto' else 1)
    )
    
    # Zachowanie wybranego trybu w session state
    st.session_state.backtest_mode = 'auto' if mode == "Automatyczny (dla początkujących)" else 'advanced'
    
    # Wyświetlenie odpowiedniego interfejsu w zależności od trybu
    if st.session_state.backtest_mode == 'auto':
        render_auto_backtest_interface()
    else:
        # Istniejący kod dla trybu zaawansowanego
        backtest_tabs = st.tabs(["Konfiguracja backtestingu", "Wyniki i raporty", "Optymalizacja parametrów", "Dokumentacja"])
        
        with backtest_tabs[0]:
            # Reszta istniejącego kodu dla konfiguracji backtestingu
            st.header("Konfiguracja backtestingu")
            
            # Sprawdzamy, czy mamy parametry z trybu automatycznego
            has_auto_params = 'from_auto_params' in st.session_state and st.session_state.load_from_auto
            auto_params = st.session_state.get('from_auto_params', {}) if has_auto_params else {}
            
            # Wyświetlamy informację, jeśli przeszliśmy z trybu automatycznego
            if has_auto_params:
                st.info("Parametry zostały zaimportowane z trybu automatycznego. Możesz je teraz dostosować.")
            
            col1, col2 = st.columns(2)
            
            with col1:
                # Wybór instrumentu
                symbol = st.selectbox(
                    "Instrument",
                    ["EURUSD", "GBPUSD", "USDJPY", "GOLD", "SILVER", "OIL", "US100", "DE30"],
                    index=["EURUSD", "GBPUSD", "USDJPY", "GOLD", "SILVER", "OIL", "US100", "DE30"].index(auto_params.get('symbol', "EURUSD")) if has_auto_params else 0
                )
                
                # Wybór timeframe'u
                timeframe_list = ["M1", "M5", "M15", "M30", "H1", "H4", "D1"]
                timeframe = st.selectbox(
                    "Timeframe",
                    timeframe_list,
                    index=timeframe_list.index(auto_params.get('timeframe', "M15")) if has_auto_params and auto_params.get('timeframe') in timeframe_list else 2
                )
                
                # Wybór strategii
                strategy_list = ["SimpleMovingAverage", "RSI", "BollingerBands", "MACD", "CombinedIndicators"]
                strategy_type = st.selectbox(
                    "Strategia",
                    strategy_list,
                    index=strategy_list.index(auto_params.get('strategy_type', "CombinedIndicators")) if has_auto_params and auto_params.get('strategy_type') in strategy_list else 4
                )
            
            with col2:
                # Okres backtestingu
                col2a, col2b = st.columns(2)
                with col2a:
                    start_date = st.date_input(
                        "Data początkowa", 
                        auto_params.get('start_date', datetime.now() - timedelta(days=30))
                    )
                with col2b:
                    end_date = st.date_input(
                        "Data końcowa", 
                        auto_params.get('end_date', datetime.now())
                    )
                
                # Parametry zarządzania pozycjami
                initial_capital = st.number_input(
                    "Kapitał początkowy", 
                    min_value=100, 
                    value=auto_params.get('initial_capital', 10000), 
                    step=1000
                )
                
                risk_per_trade_pct = auto_params.get('risk_per_trade', 0.01) * 100 if has_auto_params else 1.0
                risk_per_trade = st.slider(
                    "Ryzyko na transakcję (%)", 
                    min_value=0.1, 
                    max_value=5.0, 
                    value=float(risk_per_trade_pct), 
                    step=0.1
                )
                
                # Parametry analizy
                include_fees = st.checkbox(
                    "Uwzględnij prowizje i spready", 
                    value=auto_params.get('include_fees', True)
                )
        
            # Sekcja parametrów strategii
            st.subheader("Parametry strategii")
            
            # Domyślne parametry strategii z trybu automatycznego
            auto_strategy_params = auto_params.get('strategy_params', {}) if has_auto_params else {}
            
            # Dynamiczne parametry w zależności od wybranej strategii
            strategy_params = {}
            
            if strategy_type == "SimpleMovingAverage":
                col1s, col2s = st.columns(2)
                with col1s:
                    strategy_params["fast_ma_period"] = st.slider(
                        "Okres szybkiej MA", 
                        5, 50, 
                        auto_strategy_params.get("fast_ma_period", 10)
                    )
                with col2s:
                    strategy_params["slow_ma_period"] = st.slider(
                        "Okres wolnej MA", 
                        20, 200, 
                        auto_strategy_params.get("slow_ma_period", 50)
                    )
            
            elif strategy_type == "RSI":
                col1s, col2s = st.columns(2)
                with col1s:
                    strategy_params["rsi_period"] = st.slider(
                        "Okres RSI", 
                        5, 30, 
                        auto_strategy_params.get("rsi_period", 14)
                    )
                with col2s:
                    strategy_params["oversold"] = st.slider(
                        "Poziom wykupienia", 
                        20, 40, 
                        auto_strategy_params.get("oversold", 30)
                    )
                    strategy_params["overbought"] = st.slider(
                        "Poziom wyprzedania", 
                        60, 80, 
                        auto_strategy_params.get("overbought", 70)
                    )
            
            elif strategy_type == "BollingerBands":
                col1s, col2s = st.columns(2)
                with col1s:
                    strategy_params["bb_period"] = st.slider(
                        "Okres BB", 
                        10, 50, 
                        auto_strategy_params.get("bb_period", 20)
                    )
                with col2s:
                    strategy_params["bb_std"] = st.slider(
                        "Odchylenie standardowe", 
                        1.0, 3.0, 
                        float(auto_strategy_params.get("bb_std", 2.0)), 
                        0.1
                    )
            
            elif strategy_type == "MACD":
                col1s, col2s, col3s = st.columns(3)
                with col1s:
                    strategy_params["fast_ema"] = st.slider(
                        "Szybka EMA", 
                        5, 20, 
                        auto_strategy_params.get("fast_ema", 12)
                    )
                with col2s:
                    strategy_params["slow_ema"] = st.slider(
                        "Wolna EMA", 
                        15, 40, 
                        auto_strategy_params.get("slow_ema", 26)
                    )
                with col3s:
                    strategy_params["signal_period"] = st.slider(
                        "Okres sygnału", 
                        5, 15, 
                        auto_strategy_params.get("signal_period", 9)
                    )
            
            elif strategy_type == "CombinedIndicators":
                # Pobierz domyślne wartości wag i progów
                default_weights = auto_strategy_params.get("weights", {}) if has_auto_params else {
                    'trend': 0.25, 'macd': 0.30, 'rsi': 0.20, 'bb': 0.15, 'candle': 0.10
                }
                
                default_thresholds = auto_strategy_params.get("thresholds", {}) if has_auto_params else {
                    'signal_minimum': 0.2
                }
                
                col1s, col2s = st.columns(2)
                with col1s:
                    strategy_params["trend_weight"] = st.slider(
                        "Waga trendu", 
                        0.0, 1.0, 
                        float(default_weights.get('trend', 0.25)), 
                        0.05
                    )
                    strategy_params["macd_weight"] = st.slider(
                        "Waga MACD", 
                        0.0, 1.0, 
                        float(default_weights.get('macd', 0.30)), 
                        0.05
                    )
                    strategy_params["rsi_weight"] = st.slider(
                        "Waga RSI", 
                        0.0, 1.0, 
                        float(default_weights.get('rsi', 0.20)), 
                        0.05
                    )
                with col2s:
                    strategy_params["bb_weight"] = st.slider(
                        "Waga Bollinger", 
                        0.0, 1.0, 
                        float(default_weights.get('bb', 0.15)), 
                        0.05
                    )
                    strategy_params["candle_weight"] = st.slider(
                        "Waga formacji", 
                        0.0, 1.0, 
                        float(default_weights.get('candle', 0.10)), 
                        0.05
                    )
                    strategy_params["signal_minimum"] = st.slider(
                        "Próg sygnału", 
                        0.0, 1.0, 
                        float(default_thresholds.get('signal_minimum', 0.2)), 
                        0.05
                    )

            # Przycisk uruchamiający backtest
            if st.button("Uruchom backtest", type="primary"):
                st.session_state['run_backtest'] = True
                st.session_state['backtest_config'] = {
                    'symbol': symbol,
                    'timeframe': timeframe,
                    'strategy_type': strategy_type,
                    'strategy_params': strategy_params,
                    'start_date': start_date,
                    'end_date': end_date,
                    'initial_capital': initial_capital,
                    'risk_per_trade': risk_per_trade / 100,  # Konwersja z % na wartość dziesiętną
                    'include_fees': include_fees
                }
                st.success("Konfiguracja backtestingu zapisana. Przejdź do zakładki 'Wyniki i raporty', aby zobaczyć rezultaty.")
        
        with backtest_tabs[1]:
            st.header("Wyniki i raporty")
            
            # Sprawdzenie, czy backtest był uruchomiony
            if 'backtest_results' in st.session_state:
                results = st.session_state['backtest_results']
                config = st.session_state['backtest_config']
                
                # Podsumowanie backtestingu
                st.subheader("Podsumowanie")
                metrics_col1, metrics_col2, metrics_col3, metrics_col4 = st.columns(4)
                
                with metrics_col1:
                    st.metric("Zysk całkowity", f"{results['net_profit']:.2f} USD")
                    st.metric("Liczba transakcji", f"{results['total_trades']}")
                
                with metrics_col2:
                    st.metric("Win Rate", f"{results['win_rate']:.2f}%")
                    st.metric("Profit Factor", f"{results['profit_factor']:.2f}")
                
                with metrics_col3:
                    st.metric("Średni zysk", f"{results['avg_profit']:.2f} USD")
                    st.metric("Średnia strata", f"{results['avg_loss']:.2f} USD")
                
                with metrics_col4:
                    st.metric("Max Drawdown", f"{results['max_drawdown']:.2f}%")
                    st.metric("Sharpe Ratio", f"{results['sharpe_ratio']:.2f}")
                
                # Wykresy
                st.subheader("Wykres kapitału")
                
                # Wykres equity
                if 'equity_curve' in results:
                    fig = go.Figure()
                    fig.add_trace(go.Scatter(x=results['equity_curve'].index, y=results['equity_curve'].values, 
                                            mode='lines', name='Equity'))
                    fig.update_layout(title='Krzywa kapitału',
                                    xaxis_title='Data',
                                    yaxis_title='Kapitał (USD)')
                    st.plotly_chart(fig, use_container_width=True)
                
                # Tabela transakcji
                st.subheader("Historia transakcji")
                if 'trades' in results:
                    st.dataframe(results['trades'])
                
                # Przyciski do generowania raportów
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("Generuj raport HTML"):
                        st.info("Generowanie raportu HTML...")
                        # Tutaj kod do generowania raportu HTML
                        # Możemy użyć funkcji z backtest_engine.py do generowania raportów
                        try:
                            from src.backtest.report_generator import generate_html_report
                            report_path = generate_html_report(
                                results, 
                                f"backtest_{config['symbol']}_{config['timeframe']}_{config['strategy_type']}"
                            )
                            st.success(f"Raport HTML wygenerowany pomyślnie! Ścieżka: {report_path}")
                            with open(report_path, "rb") as file:
                                st.download_button(
                                    label="Pobierz raport HTML",
                                    data=file,
                                    file_name=f"backtest_report_{config['symbol']}_{config['timeframe']}.html",
                                    mime="text/html"
                                )
                        except Exception as e:
                            st.error(f"Błąd podczas generowania raportu: {str(e)}")
                
                with col2:
                    if st.button("Eksportuj do Excel"):
                        st.info("Eksportowanie danych do Excel...")
                        try:
                            # Eksport danych do Excel
                            excel_path = f"backtest_results_{config['symbol']}_{config['timeframe']}.xlsx"
                            
                            # Tworzymy Excel writer
                            with pd.ExcelWriter(excel_path) as writer:
                                # Zapisujemy dane o transakcjach
                                if 'trades' in results:
                                    results['trades'].to_excel(writer, sheet_name='Transactions')
                                
                                # Zapisujemy krzywą equity
                                if 'equity_curve' in results:
                                    results['equity_curve'].to_excel(writer, sheet_name='EquityCurve')
                                
                                # Zapisujemy metryki
                                metrics_df = pd.DataFrame({
                                    'Metric': [
                                        'Net Profit', 'Total Trades', 'Win Rate', 'Profit Factor',
                                        'Avg Profit', 'Avg Loss', 'Max Drawdown', 'Sharpe Ratio'
                                    ],
                                    'Value': [
                                        results['net_profit'], results['total_trades'], 
                                        results['win_rate'], results['profit_factor'],
                                        results['avg_profit'], results['avg_loss'], 
                                        results['max_drawdown'], results['sharpe_ratio']
                                    ]
                                })
                                metrics_df.to_excel(writer, sheet_name='Metrics', index=False)
                            
                            # Umożliwiamy pobranie pliku
                            with open(excel_path, "rb") as file:
                                st.download_button(
                                    label="Pobierz plik Excel",
                                    data=file,
                                    file_name=excel_path,
                                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                                )
                            st.success("Dane wyeksportowane pomyślnie!")
                        except Exception as e:
                            st.error(f"Błąd podczas eksportu do Excel: {str(e)}")
            
            else:
                if 'run_backtest' in st.session_state and st.session_state['run_backtest']:
                    with st.spinner("Trwa wykonywanie backtestingu..."):
                        # Tutaj logika uruchamiania backtestingu
                        config = st.session_state['backtest_config']
                        
                        try:
                            # Tworzenie konfiguracji backtestingu
                            backtest_config = BacktestConfig(
                                symbol=config['symbol'],
                                timeframe=config['timeframe'],
                                start_date=config['start_date'],
                                end_date=config['end_date'],
                                initial_capital=config['initial_capital'],
                                risk_per_trade=config['risk_per_trade'],
                                include_fees=config['include_fees']
                            )
                            
                            # Tworzenie odpowiedniej strategii
                            strategy = None
                            if config['strategy_type'] == "SimpleMovingAverage":
                                strategy = SimpleMovingAverageStrategy(
                                    fast_ma_period=config['strategy_params']['fast_ma_period'],
                                    slow_ma_period=config['strategy_params']['slow_ma_period']
                                )
                            elif config['strategy_type'] == "RSI":
                                strategy = RSIStrategy(
                                    rsi_period=config['strategy_params']['rsi_period'],
                                    oversold=config['strategy_params']['oversold'],
                                    overbought=config['strategy_params']['overbought']
                                )
                            elif config['strategy_type'] == "BollingerBands":
                                strategy = BollingerBandsStrategy(
                                    bb_period=config['strategy_params']['bb_period'],
                                    bb_std=config['strategy_params']['bb_std']
                                )
                            elif config['strategy_type'] == "MACD":
                                strategy = MACDStrategy(
                                    fast_ema=config['strategy_params']['fast_ema'],
                                    slow_ema=config['strategy_params']['slow_ema'],
                                    signal_period=config['strategy_params']['signal_period']
                                )
                            elif config['strategy_type'] == "CombinedIndicators":
                                weights = {
                                    'trend': config['strategy_params']['trend_weight'],
                                    'macd': config['strategy_params']['macd_weight'],
                                    'rsi': config['strategy_params']['rsi_weight'],
                                    'bb': config['strategy_params']['bb_weight'],
                                    'candle': config['strategy_params']['candle_weight'],
                                }
                                thresholds = {
                                    'signal_minimum': config['strategy_params']['signal_minimum'],
                                }
                                strategy = CombinedIndicatorsStrategy(weights=weights, thresholds=thresholds)
                            
                            # Uruchomienie silnika backtestingu
                            engine = BacktestEngine(backtest_config, strategy=strategy)
                            result = engine.run()
                            
                            # Formatowanie wyników
                            trades_df = pd.DataFrame([vars(trade) for trade in result.trades])
                            if not trades_df.empty:
                                trades_df = trades_df.drop(['strategy', 'symbol'], axis=1, errors='ignore')
                            
                            # Zapis wyników do sesji
                            metrics = calculate_metrics(result)
                            st.session_state['backtest_results'] = {
                                'net_profit': metrics['net_profit'],
                                'total_trades': metrics['total_trades'],
                                'win_rate': metrics['win_rate'] * 100,  # Konwersja na procenty
                                'profit_factor': metrics['profit_factor'],
                                'avg_profit': metrics['avg_profit'],
                                'avg_loss': metrics['avg_loss'],
                                'max_drawdown': metrics['max_drawdown'] * 100,  # Konwersja na procenty
                                'sharpe_ratio': metrics['sharpe_ratio'],
                                'equity_curve': result.equity_curve,
                                'trades': trades_df,
                                'drawdown_curve': result.drawdown_curve,
                                'raw_result': result
                            }
                            
                            st.success("Backtest zakończony pomyślnie!")
                            st.experimental_rerun()
                        
                        except Exception as e:
                            handle_backtest_error(e)
                            st.error(f"Błąd podczas wykonywania backtestingu: {str(e)}")
                            st.session_state.pop('run_backtest', None)
                else:
                    st.info("Najpierw skonfiguruj i uruchom backtest w zakładce 'Konfiguracja backtestingu'.")
        
        with backtest_tabs[2]:
            st.header("Optymalizacja parametrów")
            
            col1, col2 = st.columns(2)
            
            with col1:
                # Wybór instrumentu i timeframe
                optimization_symbol = st.selectbox(
                    "Instrument",
                    ["EURUSD", "GBPUSD", "USDJPY", "GOLD", "SILVER", "OIL", "US100", "DE30"],
                    index=0,
                    key="opt_symbol"
                )
                
                optimization_timeframe = st.selectbox(
                    "Timeframe",
                    ["M1", "M5", "M15", "M30", "H1", "H4", "D1"],
                    index=2,
                    key="opt_timeframe"
                )
                
                # Wybór strategii do optymalizacji
                optimization_strategy = st.selectbox(
                    "Strategia",
                    ["SimpleMovingAverage", "RSI", "BollingerBands", "MACD", "CombinedIndicators"],
                    index=4,
                    key="opt_strategy"
                )
            
            with col2:
                # Okres optymalizacji
                col2a, col2b = st.columns(2)
                with col2a:
                    optimization_start_date = st.date_input(
                        "Data początkowa", 
                        datetime.now() - timedelta(days=60),
                        key="opt_start_date"
                    )
                with col2b:
                    optimization_end_date = st.date_input(
                        "Data końcowa", 
                        datetime.now(),
                        key="opt_end_date"
                    )
                
                # Metoda optymalizacji
                optimization_method = st.selectbox(
                    "Metoda optymalizacji",
                    ["Grid Search", "Random Search", "Walk Forward"],
                    index=0
                )
                
                # Metryka optymalizacji
                optimization_metric = st.selectbox(
                    "Metryka optymalizacji",
                    ["Net Profit", "Sharpe Ratio", "Profit Factor", "Win Rate", "Calmar Ratio"],
                    index=1
                )
            
            # Parametry do optymalizacji (dynamiczne w zależności od strategii)
            st.subheader("Parametry do optymalizacji")
            
            # Słownik przechowujący parametry do optymalizacji
            param_grid = {}
            
            if optimization_strategy == "SimpleMovingAverage":
                param_col1, param_col2 = st.columns(2)
                with param_col1:
                    fast_ma_min = st.number_input("Min szybkiej MA", 5, 20, 5)
                    fast_ma_max = st.number_input("Max szybkiej MA", fast_ma_min, 50, 20)
                    fast_ma_step = st.number_input("Krok szybkiej MA", 1, 10, 5)
                    param_grid['fast_ma_period'] = list(range(fast_ma_min, fast_ma_max + 1, fast_ma_step))
                
                with param_col2:
                    slow_ma_min = st.number_input("Min wolnej MA", 20, 50, 20)
                    slow_ma_max = st.number_input("Max wolnej MA", slow_ma_min, 200, 100)
                    slow_ma_step = st.number_input("Krok wolnej MA", 1, 20, 10)
                    param_grid['slow_ma_period'] = list(range(slow_ma_min, slow_ma_max + 1, slow_ma_step))
            
            elif optimization_strategy == "RSI":
                param_col1, param_col2 = st.columns(2)
                with param_col1:
                    rsi_min = st.number_input("Min okresu RSI", 5, 20, 7)
                    rsi_max = st.number_input("Max okresu RSI", rsi_min, 30, 21)
                    rsi_step = st.number_input("Krok okresu RSI", 1, 5, 2)
                    param_grid['rsi_period'] = list(range(rsi_min, rsi_max + 1, rsi_step))
                
                with param_col2:
                    oversold_values = st.multiselect("Poziomy wykupienia", list(range(20, 41, 5)), default=[25, 30, 35])
                    overbought_values = st.multiselect("Poziomy wyprzedania", list(range(60, 81, 5)), default=[65, 70, 75])
                    param_grid['oversold'] = oversold_values
                    param_grid['overbought'] = overbought_values
            
            # Przycisk uruchamiający optymalizację
            if st.button("Uruchom optymalizację", type="primary"):
                if param_grid:
                    st.info("Uruchamianie optymalizacji. To może potrwać dłuższy czas...")
                    
                    try:
                        # Tworzenie konfiguracji backtestingu
                        backtest_config = BacktestConfig(
                            symbol=optimization_symbol,
                            timeframe=optimization_timeframe,
                            start_date=optimization_start_date,
                            end_date=optimization_end_date,
                            initial_capital=10000,  # Domyślna wartość dla optymalizacji
                            risk_per_trade=0.01,    # Domyślna wartość dla optymalizacji
                            include_fees=True
                        )
                        
                        # Tworzenie odpowiedniej strategii (z domyślnymi parametrami, zostaną one nadpisane)
                        strategy_class = None
                        if optimization_strategy == "SimpleMovingAverage":
                            strategy_class = SimpleMovingAverageStrategy
                        elif optimization_strategy == "RSI":
                            strategy_class = RSIStrategy
                        elif optimization_strategy == "BollingerBands":
                            strategy_class = BollingerBandsStrategy
                        elif optimization_strategy == "MACD":
                            strategy_class = MACDStrategy
                        elif optimization_strategy == "CombinedIndicators":
                            strategy_class = CombinedIndicatorsStrategy
                        
                        # Konfiguracja optymalizacji
                        optimization_config = OptimizationConfig(
                            param_grid=param_grid,
                            fitness_metric=optimization_metric.lower().replace(" ", "_"),
                            n_jobs=-1  # Użyj wszystkich dostępnych rdzeni
                        )
                        
                        # Uruchomienie optymalizacji
                        optimizer = ParameterOptimizer(
                            strategy_class=strategy_class,
                            backtest_config=backtest_config,
                            optimization_config=optimization_config
                        )
                        
                        # Wykonanie optymalizacji
                        if optimization_method == "Grid Search":
                            results = optimizer.grid_search()
                        elif optimization_method == "Random Search":
                            results = optimizer.random_search(n_iter=30)  # Przykładowa liczba iteracji
                        elif optimization_method == "Walk Forward":
                            walk_forward_config = WalkForwardConfig(
                                train_size=60,  # dni
                                test_size=30,   # dni
                                step=30,        # dni
                                optimize_metric=optimization_metric.lower().replace(" ", "_")
                            )
                            
                            walk_forward = WalkForwardTester(
                                strategy_class=strategy_class,
                                param_grid=param_grid,
                                symbol=optimization_symbol,
                                timeframe=optimization_timeframe,
                                start_date=optimization_start_date,
                                end_date=optimization_end_date,
                                walk_forward_config=walk_forward_config
                            )
                            
                            results = walk_forward.run()
                        
                        # Zapisanie wyników optymalizacji do sesji
                        st.session_state['optimization_results'] = results
                        
                        # Wyświetlenie wyników
                        st.success("Optymalizacja zakończona pomyślnie!")
                        
                        if optimization_method == "Walk Forward":
                            # Specyficzne wyświetlanie dla Walk Forward
                            st.subheader("Wyniki Walk Forward Testingu")
                            
                            # Tabela z wynikami dla każdego okna
                            periods_data = []
                            for i, window in enumerate(results['windows']):
                                periods_data.append({
                                    'Okno': i+1,
                                    'Okres treningu': f"{window['train_period'][0]} - {window['train_period'][1]}",
                                    'Okres testowy': f"{window['test_period'][0]} - {window['test_period'][1]}",
                                    'Parametry': str(window['params']),
                                    'Zysk': f"{window['metrics']['net_profit']:.2f}",
                                    'Sharpe': f"{window['metrics']['sharpe_ratio']:.2f}",
                                    'Win Rate': f"{window['metrics']['win_rate']*100:.2f}%"
                                })
                            
                            periods_df = pd.DataFrame(periods_data)
                            st.dataframe(periods_df)
                            
                            # Wykres wyników
                            equity_combined = results['combined_equity']
                            
                            fig = go.Figure()
                            fig.add_trace(go.Scatter(x=equity_combined.index, y=equity_combined.values, 
                                                   mode='lines', name='Walk Forward Equity'))
                            fig.update_layout(title='Krzywa kapitału Walk Forward',
                                           xaxis_title='Data',
                                           yaxis_title='Kapitał (USD)')
                            st.plotly_chart(fig, use_container_width=True)
                            
                        else:
                            # Standardowe wyświetlanie dla Grid Search / Random Search
                            st.subheader("Wyniki optymalizacji")
                            
                            # Tabela z najlepszymi zestawami parametrów
                            results_df = pd.DataFrame(results)
                            if len(results_df) > 20:
                                results_df = results_df.head(20)  # Ograniczenie do 20 najlepszych wyników
                            
                            st.dataframe(results_df)
                            
                            # Wizualizacja przestrzeni parametrów (jeśli mamy 2 parametry)
                            if len(param_grid) == 2:
                                st.subheader("Wizualizacja przestrzeni parametrów")
                                
                                # Przygotowanie danych do wizualizacji
                                param_names = list(param_grid.keys())
                                
                                # Tworzenie siatki parametrów
                                param1_values = sorted(set([result['params'][param_names[0]] for result in results]))
                                param2_values = sorted(set([result['params'][param_names[1]] for result in results]))
                                
                                Z = np.zeros((len(param2_values), len(param1_values)))
                                for i, p2 in enumerate(param2_values):
                                    for j, p1 in enumerate(param1_values):
                                        # Szukamy wyniku dla tej kombinacji parametrów
                                        for result in results:
                                            if (result['params'][param_names[0]] == p1 and 
                                                result['params'][param_names[1]] == p2):
                                                Z[i, j] = result['metrics'][optimization_metric.lower().replace(" ", "_")]
                                                break
                                
                                # Tworzenie wykresu 3D
                                X, Y = np.meshgrid(param1_values, param2_values)
                                
                                fig = go.Figure(data=[go.Surface(z=Z, x=X, y=Y)])
                                fig.update_layout(
                                    title=f'Przestrzeń parametrów - {optimization_metric}',
                                    scene=dict(
                                        xaxis_title=param_names[0],
                                        yaxis_title=param_names[1],
                                        zaxis_title=optimization_metric
                                    ),
                                    width=800,
                                    height=600
                                )
                                st.plotly_chart(fig)
                    
                    except Exception as e:
                        handle_backtest_error(e)
                else:
                    st.warning("Brak parametrów do optymalizacji. Wybierz strategię i określ parametry.")
        
        with backtest_tabs[3]:
            st.header("Dokumentacja systemu backtestingu")
            
            st.markdown("""
            ## Przewodnik po systemie backtestingu AgentMT5
            
            System backtestingu AgentMT5 umożliwia testowanie strategii handlowych na danych historycznych, analizę wyników i optymalizację parametrów.
            
            ### Strategie handlowe
            
            System obsługuje następujące strategie:
            
            1. **Simple Moving Average (SMA)** - strategie oparte na przecięciach średnich kroczących.
            2. **Relative Strength Index (RSI)** - strategie oparte na wskaźniku RSI, wykrywające stany przewartościowania/niedowartościowania.
            3. **Bollinger Bands** - strategie wykorzystujące kanały cenowe Bollingera do wykrywania wybić i powrotów do średniej.
            4. **MACD** - strategie bazujące na wskaźniku MACD (Moving Average Convergence Divergence).
            5. **Combined Indicators** - zaawansowana strategia łącząca różne wskaźniki techniczne z wagami.
            
            ### Proces backtestingu
            
            1. **Konfiguracja** - wybór instrumentu, timeframe'u, strategii i parametrów.
            2. **Wykonanie backtestingu** - uruchomienie testu na danych historycznych.
            3. **Analiza wyników** - przegląd metryk, wykresów i historii transakcji.
            4. **Eksport/raportowanie** - generowanie raportów HTML lub eksport do Excela.
            
            ### Optymalizacja parametrów
            
            System oferuje trzy metody optymalizacji:
            
            1. **Grid Search** - systematyczne przeszukiwanie przestrzeni parametrów.
            2. **Random Search** - losowe próbkowanie przestrzeni parametrów (szybsze niż Grid Search dla dużych przestrzeni).
            3. **Walk Forward** - bardziej realistyczna metoda testowania, dzieląca dane na okresy treningowe i testowe.
            
            ### Metryki oceny strategii
            
            Do oceny strategii używane są następujące metryki:
            
            - **Net Profit** - całkowity zysk netto.
            - **Win Rate** - procent zyskownych transakcji.
            - **Profit Factor** - stosunek zysków do strat.
            - **Sharpe Ratio** - stosunek zwrotu do ryzyka, uwzględniający zmienność.
            - **Calmar Ratio** - stosunek zwrotu rocznego do maksymalnego drawdownu.
            - **Maximum Drawdown** - największa procentowa strata od najwyższego punktu.
            
            ### Dobre praktyki
            
            1. **Unikaj przeuczenia** - testuj na różnych instrumentach i okresach.
            2. **Uwzględniaj koszty transakcyjne** - włącz opcję "Uwzględnij prowizje i spready".
            3. **Testuj walk-forward** - najbardziej realistyczna metoda oceny strategii.
            4. **Weryfikuj out-of-sample** - testuj na danych, które nie były używane do optymalizacji.
            5. **Analizuj różne metryki** - nie opieraj decyzji tylko na jednej metryce.
            
            ### Znane ograniczenia
            
            1. Backtest nie uwzględnia poślizgu cenowego (slippage).
            2. Dane historyczne mogą być niekompletne dla niektórych instrumentów i okresu.
            3. Wydajność może być ograniczona dla dużych zbiorów danych na niskich timeframe'ach (M1, M5).
            """)
            
            # Dodajemy linki do dokumentacji
            st.subheader("Dodatkowe zasoby")
            st.markdown("""
            - [Pełna dokumentacja systemu backtestingu](https://github.com/username/AgentMT5/wiki/Backtesting)
            - [Przykłady strategii](https://github.com/username/AgentMT5/wiki/Example-Strategies)
            - [Tuutorial optymalizacji parametrów](https://github.com/username/AgentMT5/wiki/Optimization-Tutorial)
            - [Raport błędów i propozycje funkcji](https://github.com/username/AgentMT5/issues)
            """)
            
            # Dodajemy informacje o limitach i problemach
            st.warning("""
            **Uwaga**: Pamiętaj, że wyniki backtestingu nie gwarantują przyszłych wyników. 
            Zawsze testuj strategie na rachunku demonstracyjnym przed użyciem ich na rachunku rzeczywistym.
            """)

def render_auto_backtest_interface():
    """Renderuje interfejs automatycznego backtestingu dla początkujących użytkowników."""
    
    # Sprawdzenie, czy jesteśmy w trybie wyników i odpowiednia obsługa
    if 'auto_backtest_mode' in st.session_state and st.session_state.auto_backtest_mode == "results":
        _display_auto_backtest_results()
        return
    
    st.subheader("Automatyczny Backtest")
    
    st.markdown("""
    Ten tryb automatycznie analizuje dane historyczne, identyfikuje warunki rynkowe 
    i dobiera optymalną strategię wraz z parametrami dostosowanymi do wybranego profilu ryzyka.
    """)
    
    # Sekcja konfiguracji
    st.subheader("Podstawowa konfiguracja")
    
    cols = st.columns(2)
    
    with cols[0]:
        # Wybór instrumentu
        instruments = ["EURUSD", "GBPUSD", "USDJPY", "USDCHF", "AUDUSD", "USDCAD", "NZDUSD"]
        symbol = st.selectbox("Instrument:", instruments)
        
        # Wybór profilu ryzyka
        risk_profile = st.selectbox(
            "Profil ryzyka:", 
            ["Konserwatywny", "Zrównoważony", "Agresywny"]
        )
    
    with cols[1]:
        # Wybór timeframe'u
        timeframe = st.selectbox(
            "Timeframe:", 
            ["M5", "M15", "M30", "H1", "H4", "D1"],
            index=1
        )
        
        # Preferencja strategii
        strategy_preference = st.selectbox(
            "Preferencja strategii:", 
            ["Automatyczny wybór", "Trendowa", "Oscylacyjna", "Mieszana"]
        )
    
    # Dodajemy nową opcję - używanie parametrów z produkcyjnego systemu
    use_main_system_params = st.checkbox(
        "Użyj dokładnie tych samych parametrów co system produkcyjny", 
        value=True,
        help="Jeśli zaznaczone, backtest będzie używał dokładnie tych samych parametrów co główny system AgentMT5."
    )
    
    # Sekcja zarządzania ryzykiem
    st.subheader("Zarządzanie ryzykiem")
    
    risk_cols = st.columns(3)
    
    with risk_cols[0]:
        initial_balance = st.number_input(
            "Początkowy kapitał:", 
            min_value=1000, 
            max_value=1000000, 
            value=10000,
            step=1000
        )
    
    with risk_cols[1]:
        risk_per_trade = st.number_input(
            "Ryzyko na transakcję (%):", 
            min_value=0.1, 
            max_value=10.0, 
            value=2.0,
            step=0.1
        )
    
    with risk_cols[2]:
        use_fixed_lot = st.checkbox("Użyj stałego wolumenu", value=False)
        if use_fixed_lot:
            lot_size = st.number_input(
                "Wielkość lotu:", 
                min_value=0.01, 
                max_value=10.0, 
                value=0.1,
                step=0.01
            )
        else:
            lot_size = None
    
    # Sekcja daty
    st.subheader("Zakres dat")
    
    date_cols = st.columns(2)
    
    with date_cols[0]:
        start_date = st.date_input(
            "Data początkowa:", 
            value=datetime.now() - timedelta(days=90)
        )
    
    with date_cols[1]:
        end_date = st.date_input(
            "Data końcowa:", 
            value=datetime.now()
        )
    
    # Wizualizacja warunków rynkowych (przed uruchomieniem backtestingu)
    if st.button("Analizuj warunki rynkowe"):
        with st.spinner("Analizuję warunki rynkowe..."):
            try:
                market_condition = analyze_market_condition(
                    symbol, timeframe, start_date, end_date
                )
                if market_condition:
                    display_market_condition(market_condition)
            except Exception as e:
                st.error(f"Błąd podczas analizy warunków rynkowych: {str(e)}")
    
    # Uruchomienie backtestingu
    if st.button("Uruchom automatyczny backtest"):
        with st.spinner("Uruchamiam backtest..."):
            try:
                # Utworzenie konfiguracji backtestingu
                config = {
                    "symbol": symbol,
                    "timeframe": timeframe,
                    "start_date": start_date,
                    "end_date": end_date,
                    "initial_balance": initial_balance,
                    "risk_per_trade": risk_per_trade / 100,  # Konwersja z % na wartość dziesiętną
                    "use_fixed_lot": use_fixed_lot,
                    "lot_size": lot_size if use_fixed_lot else None,
                    "risk_profile": risk_profile,
                    "strategy_preference": strategy_preference,
                    "use_main_system_params": use_main_system_params  # Nowy parametr
                }
                
                # Zapisanie konfiguracji w sesji
                st.session_state.auto_backtest_config = config
                
                # Analiza rynku i uruchomienie backtestingu
                with st.spinner("Analizuję warunki rynkowe i dobieram optymalną strategię..."):
                    # Pobieranie danych historycznych
                    historical_data = get_historical_data(
                        symbol=config["symbol"],
                        timeframe=config["timeframe"],
                        start_date=config["start_date"],
                        end_date=config["end_date"]
                    )
                    
                    if historical_data is not None and not historical_data.empty:
                        # Analiza warunków rynkowych
                        market_analyzer = MarketAnalyzer()
                        
                        # Użyj nowego parametru w wywołaniu funkcji analyze_market
                        market_analysis = market_analyzer.analyze_market(
                            data=historical_data,
                            risk_profile=config["risk_profile"],
                            strategy_preference=config["strategy_preference"],
                            use_main_system_params=config["use_main_system_params"]  # Nowy parametr
                        )
                        
                        # Zapisanie analizy w sesji
                        st.session_state.market_analysis = market_analysis
                        
                        # Wyświetlenie informacji o warunkach rynkowych
                        st.subheader("Wyniki analizy rynku")
                        st.markdown(f"**Zidentyfikowane warunki rynkowe:** {market_analysis.condition.value}")
                        st.markdown(f"**Opis:** {market_analysis.description}")
                        
                        # Utworzenie i uruchomienie backtestingu
                        with st.spinner("Uruchamiam backtest z optymalną strategią..."):
                            strategy_name = market_analysis.recommended_strategy
                            strategy_params = market_analysis.recommended_params
                            
                            st.markdown(f"**Wybrana strategia:** {strategy_name}")
                            st.markdown("**Parametry strategii:**")
                            
                            # Pokazanie parametrów w czytelnym formacie
                            if isinstance(strategy_params, dict):
                                for key, value in strategy_params.items():
                                    if isinstance(value, dict):
                                        st.markdown(f"- **{key}:**")
                                        for subkey, subvalue in value.items():
                                            st.markdown(f"  - {subkey}: {subvalue}")
                                    else:
                                        st.markdown(f"- {key}: {value}")
                            
                            # Utworzenie strategii na podstawie analizy
                            strategy = create_strategy_from_name(strategy_name, strategy_params)
                            
                            if strategy:
                                # Konwersja dat do datetime
                                start_datetime = datetime.combine(config["start_date"], datetime.min.time())
                                end_datetime = datetime.combine(config["end_date"], datetime.min.time())
                                
                                # Konfiguracja backtestingu
                                backtest_config = BacktestConfig(
                                    symbol=config["symbol"],
                                    timeframe=config["timeframe"],
                                    start_date=start_datetime,
                                    end_date=end_datetime,
                                    initial_balance=config["initial_balance"],
                                    lot_size=config["lot_size"] if config["use_fixed_lot"] else None,
                                    risk_per_trade=config["risk_per_trade"] if not config["use_fixed_lot"] else None,
                                    use_cache=True
                                )
                                
                                # Inicjalizacja silnika backtestingu
                                engine = BacktestEngine(backtest_config)
                                
                                # Uruchomienie backtestingu
                                result = engine.run(strategy)
                                
                                # Zapisanie wyników w sesji
                                st.session_state.auto_backtest_result = result
                                
                                # Przekierowanie do wyników
                                st.session_state.auto_backtest_mode = "results"
                                st.rerun()
                            else:
                                st.error(f"Nie udało się utworzyć strategii {strategy_name}")
                    else:
                        st.error("Nie udało się pobrać danych historycznych.")
            except Exception as e:
                handle_backtest_error(e)

def analyze_market_condition(instrument, timeframe, start_date, end_date):
    """
    Analizuje warunki rynkowe dla danego instrumentu i timeframe'u.
    
    Returns:
        MarketAnalysis: Wynik analizy rynku lub None w przypadku błędu
    """
    try:
        # Pobieranie danych historycznych
        historical_data = get_historical_data(
            symbol=instrument,
            timeframe=timeframe,
            start_date=start_date,
            end_date=end_date
        )
        
        if historical_data is not None and not historical_data.empty:
            # Analiza warunków rynkowych
            market_analyzer = MarketAnalyzer()
            
            # Używamy domyślnego profilu ryzyka i preferencji strategii
            # oraz korzystamy z parametrów systemu produkcyjnego
            market_analysis = market_analyzer.analyze_market(
                data=historical_data,
                risk_profile="Zrównoważony",
                strategy_preference="Automatyczny wybór",
                use_main_system_params=True  # Zawsze używamy parametrów systemu produkcyjnego dla analizy warunków
            )
            
            return market_analysis
        
        return None
    except Exception as e:
        st.error(f"Błąd podczas analizy warunków rynkowych: {str(e)}")
        return None

def display_market_condition(condition):
    """Zwraca przyjazny dla użytkownika opis warunków rynkowych"""
    condition_descriptions = {
        "strong_trend": "Silny trend",
        "moderate_trend": "Umiarkowany trend",
        "ranging": "Rynek w konsolidacji", 
        "high_volatility": "Wysoka zmienność",
        "low_volatility": "Niska zmienność"
    }
    return condition_descriptions.get(condition, "Nieznane warunki")

def main():
    """Główna funkcja aplikacji"""
    
    # Sprawdzenie połączenia z MT5
    check_mt5_connection()
    
    # Menu nawigacyjne
    menu = ["📈 Monitor", "📊 Wyniki", "🧠 Analityka AI", "🔌 Status systemu", "🎛️ Panel kontrolny", "📝 Logi", "📊 Backtesting"]
    choice = st.sidebar.radio("Nawigacja", menu)
    
    # Renderowanie odpowiedniej sekcji w zależności od wybranej opcji w menu
    if choice == "📈 Monitor":
        render_live_monitor()
    elif choice == "📊 Wyniki":
        render_performance_dashboard()
    elif choice == "🧠 Analityka AI":
        render_ai_analytics()
    elif choice == "🔌 Status systemu":
        render_system_status()
    elif choice == "🎛️ Panel kontrolny":
        render_control_panel()
    elif choice == "📝 Logi":
        render_logs_view()
    elif choice == "📊 Backtesting":
        render_backtesting_tab()

if __name__ == "__main__":
    main() 