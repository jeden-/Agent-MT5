#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Prosty interfejs Streamlit do monitorowania i sterowania agentem MT5.
"""

import streamlit as st
import requests
import json
import time
from datetime import datetime
import sys
import os

# Dodanie ścieżki projektu do PYTHONPATH
sys.path.append(os.path.abspath(os.path.dirname(os.path.dirname(__file__))))

# Konfiguracja strony
st.set_page_config(
    page_title="AgentMT5 - Panel sterowania",
    page_icon="📈",
    layout="wide"
)

# Stałe
SERVER_URL = os.getenv("SERVER_URL", "http://127.0.0.1:8080")
REFRESH_INTERVAL = 10  # sekundy

def format_currency(value):
    """Formatuje wartość jako kwotę w PLN."""
    if value is None:
        return "0,00 zł"
    return f"{value:,.2f} zł".replace(",", " ").replace(".", ",")

def api_request(endpoint, method="GET", params=None, data=None):
    """Wysyła żądanie do API."""
    url = f"{SERVER_URL}/{endpoint.lstrip('/')}"
    
    try:
        if method == "GET":
            response = requests.get(url, params=params, timeout=5)
        elif method == "POST":
            response = requests.post(url, json=data, timeout=5)
        else:
            st.error(f"Nieobsługiwana metoda HTTP: {method}")
            return None
        
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"Błąd HTTP {response.status_code}: {response.text}")
            return None
    except Exception as e:
        st.error(f"Błąd komunikacji z serwerem: {str(e)}")
        return None

def main():
    # Tytuł aplikacji
    st.title("Panel sterowania AgentMT5")
    
    # Sprawdź połączenie z serwerem MT5
    connection_status = st.empty()
    
    # Przycisk odświeżania
    col1, col2, col3 = st.columns([1, 8, 1])
    with col1:
        refresh = st.button("Odśwież")
    with col3:
        auto_refresh = st.checkbox("Auto-odświeżanie", value=True)
    
    # Status połączenia
    ping_response = api_request("ping")
    if ping_response:
        connection_status.success("✅ Połączono z serwerem MT5")
    else:
        connection_status.error("❌ Brak połączenia z serwerem MT5")
        st.warning("Sprawdź, czy serwer MT5 jest uruchomiony i dostępny na porcie 8080.")
        st.info("Uruchom agenta: `python run_agent.py --mode observation`")
        return
    
    # Status agenta
    st.header("Status agenta")
    agent_status = api_request("agent/status")
    
    if agent_status:
        status = agent_status.get("status", "unknown")
        status_col, mode_col = st.columns(2)
        
        with status_col:
            if status == "running":
                st.success(f"Status: {status.upper()}")
                if "start_time" in agent_status:
                    start_time = agent_status.get("start_time")
                    st.info(f"Uruchomiony: {start_time}")
            elif status == "stopped":
                st.warning(f"Status: {status.upper()}")
            else:
                st.error(f"Status: {status.upper()}")
        
        with mode_col:
            mode = agent_status.get("mode", "unknown")
            st.info(f"Tryb: {mode.upper()}")
    else:
        st.error("Nie można pobrać statusu agenta.")
    
    # Sterowanie agentem
    st.header("Sterowanie agentem")
    
    control_col1, control_col2, control_col3 = st.columns(3)
    
    with control_col1:
        if st.button("Start", use_container_width=True, type="primary", disabled=(status == "running")):
            with st.spinner("Uruchamianie agenta..."):
                response = api_request("agent/start", method="POST", data={"mode": "observation"})
                if response and response.get("status") == "ok":
                    st.success("Agent uruchomiony!")
                    time.sleep(1)
                    st.experimental_rerun()
                else:
                    st.error("Nie udało się uruchomić agenta.")
    
    with control_col2:
        if st.button("Stop", use_container_width=True, type="secondary", disabled=(status == "stopped")):
            with st.spinner("Zatrzymywanie agenta..."):
                response = api_request("agent/stop", method="POST")
                if response and response.get("status") == "ok":
                    st.success("Agent zatrzymany!")
                    time.sleep(1)
                    st.experimental_rerun()
                else:
                    st.error("Nie udało się zatrzymać agenta.")
    
    with control_col3:
        if st.button("Restart", use_container_width=True, disabled=(status == "unknown")):
            with st.spinner("Restartowanie agenta..."):
                response = api_request("agent/restart", method="POST")
                if response and response.get("status") == "ok":
                    st.success("Agent zrestartowany!")
                    time.sleep(1)
                    st.experimental_rerun()
                else:
                    st.error("Nie udało się zrestartować agenta.")
    
    # Informacje o koncie
    st.header("Informacje o koncie MT5")
    
    account_info = api_request("mt5/account")
    if account_info and account_info.get("status") == "ok":
        account_col1, account_col2, account_col3, account_col4 = st.columns(4)
        
        with account_col1:
            st.metric("Numer konta", account_info.get("login", "N/A"))
        
        with account_col2:
            st.metric("Saldo", format_currency(account_info.get("balance", 0)))
        
        with account_col3:
            st.metric("Equity", format_currency(account_info.get("equity", 0)))
        
        with account_col4:
            profit = account_info.get("equity", 0) - account_info.get("balance", 0)
            st.metric("Zysk/Strata", format_currency(profit), delta=f"{profit:.2f} zł")
    else:
        st.warning("Nie można pobrać informacji o koncie MT5.")
    
    # Aktywne pozycje
    st.header("Aktywne pozycje")
    
    positions_data = api_request("monitoring/positions")
    if positions_data and positions_data.get("status") == "ok":
        positions = positions_data.get("positions", [])
        
        if positions:
            for position in positions:
                position_col1, position_col2, position_col3, position_col4 = st.columns(4)
                
                with position_col1:
                    st.write(f"**Symbol:** {position.get('symbol', 'N/A')}")
                    st.write(f"**Typ:** {position.get('type', 'N/A')}")
                
                with position_col2:
                    st.write(f"**Wolumen:** {position.get('volume', 0)}")
                    st.write(f"**Cena otwarcia:** {position.get('open_price', 0)}")
                
                with position_col3:
                    st.write(f"**Stop Loss:** {position.get('sl', 'N/A')}")
                    st.write(f"**Take Profit:** {position.get('tp', 'N/A')}")
                
                with position_col4:
                    profit = position.get('profit', 0)
                    profit_color = "green" if profit > 0 else "red" if profit < 0 else "gray"
                    st.markdown(f"**Zysk/Strata:** <span style='color:{profit_color}'>{format_currency(profit)}</span>", unsafe_allow_html=True)
                    
                    if st.button("Zamknij pozycję", key=f"close_{position.get('ticket', '')}"):
                        st.warning("Funkcja zamykania pozycji jest niedostępna w tej wersji interfejsu.")
                
                st.markdown("---")
        else:
            st.info("Brak aktywnych pozycji.")
    else:
        st.warning("Nie można pobrać informacji o aktywnych pozycjach.")
    
    # Auto-odświeżanie
    if auto_refresh:
        time.sleep(REFRESH_INTERVAL)
        st.experimental_rerun()

if __name__ == "__main__":
    main() 