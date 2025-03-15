"""
Moduł serwera HTTP dla komunikacji z MT5.
"""

import asyncio
from typing import Optional, Dict, List, Any
import json
import logging
import signal
import socket
import uvicorn
import threading
import time
import pandas as pd
from datetime import datetime, timedelta
from contextlib import asynccontextmanager
from fastapi import FastAPI, Response, HTTPException, Request
from pydantic import BaseModel
import os

# Import modułu MT5Server do bezpośredniej komunikacji z MT5
from src.mt5_bridge.mt5_server import MT5_AVAILABLE
if MT5_AVAILABLE:
    from src.mt5_bridge.mt5_server import MT5Server as RealMT5Server
    logger = logging.getLogger(__name__)
    logger.info("Moduł MT5Server został zaimportowany pomyślnie")
else:
    RealMT5Server = None
    logger = logging.getLogger(__name__)
    logger.warning("Moduł MT5Server nie jest dostępny. Będą używane przykładowe dane.")

# Usunięto import kontrolera agenta
# from src.agent_controller import get_agent_controller, AgentMode

logger = logging.getLogger(__name__)

# Dodajemy współdzieloną pamięć na poziomie modułu
shared_memory = {
    "positions": {},
    "last_update": None,
    "account_info": {},
    "market_data": {}
}

# Kolejka poleceń dla EA: {ea_id: [command1, command2, ...]}
command_queue = {}
commands_lock = threading.Lock()

class MarketData(BaseModel):
    """Model danych rynkowych."""
    ea_id: str
    symbol: str
    bid: float
    ask: float
    last: Optional[float] = None
    volume: Optional[float] = None
    time: Optional[str] = None
    timeframe: Optional[str] = None
    data: Optional[Dict] = None

class PositionUpdate(BaseModel):
    """Model aktualizacji pozycji."""
    ea_id: str
    positions: List[Dict] = []

class AgentStartParams(BaseModel):
    """Parametry startu agenta."""
    mode: str = "observation"

class AgentConfig(BaseModel):
    """Konfiguracja agenta."""
    mode: str
    risk_limits: Dict[str, Any]
    instruments: Dict[str, Dict[str, Any]]

class MT5Server:
    def __init__(self, host: str, port: int):
        self.host = host
        self.port = port
        self.app = FastAPI()
        self.server = None
        self.is_running = False
        self._shutdown_event = asyncio.Event()
        self._ready = asyncio.Event()
        self._agent_controller = None  # Kontroler agenta
        self.last_connection_time = datetime.now()
        self.request_count = 0
        
        # Inicjalizacja rzeczywistego MT5Server, jeśli jest dostępny
        self.real_mt5_server = None
        if MT5_AVAILABLE and RealMT5Server:
            try:
                self.real_mt5_server = RealMT5Server('127.0.0.1', 5555)  # Używamy portu 5555, gdzie działa serwer MT5
                logger.info("Rzeczywisty MT5Server został zainicjalizowany")
            except Exception as e:
                logger.error(f"Błąd podczas inicjalizacji MT5Server: {str(e)}")
        
        self.setup_routes()
    
    def set_agent_controller(self, agent_controller):
        """
        Ustawia instancję kontrolera agenta.
        
        Args:
            agent_controller: Instancja kontrolera agenta
        """
        self._agent_controller = agent_controller
        logger.info("Kontroler agenta ustawiony w MT5Server")

    def setup_routes(self):
        """Konfiguruje trasy API."""
        self.app.get("/ping")(self.ping)
        self.app.post("/ping")(self.post_ping)
        
        # Endpointy do obsługi danych z MT5
        self.app.post("/position/update")(self.update_positions)
        self.app.post("/market/data")(self.handle_market_data)
        self.app.get("/market/data")(self.get_market_data)
        self.app.get("/commands")(self.get_commands)
        
        # Nowy endpoint dla informacji o koncie MT5
        self.app.get("/mt5/account")(self.get_account_info)
        
        # Endpointy do obsługi pozycji
        self.app.post("/position/open")(self.open_position)
        self.app.post("/position/close")(self.close_position)
        self.app.post("/position/modify")(self.modify_position)
        
        # Endpointy do obsługi agenta
        self.app.get("/agent/status")(self.agent_status)
        self.app.post("/agent/start")(self.start_agent)
        self.app.post("/agent/stop")(self.stop_agent)
        self.app.post("/agent/restart")(self.restart_agent)
        self.app.post("/agent/config")(self.set_agent_config)
        self.app.get("/agent/config")(self.get_agent_config)
        self.app.get("/agent/config/history")(self.get_agent_config_history)
        self.app.post("/agent/config/restore")(self.restore_agent_config)
        
        # Endpointy do zarządzania obserwowanymi instrumentami
        self.app.get("/instruments")(self.get_instruments)
        self.app.post("/instruments")(self.update_instruments)
        
        @self.app.get("/monitoring/connections")
        async def get_connections():
            """Zwraca informacje o aktualnych połączeniach."""
            # Przygotowanie danych o poziomach zysku
            total_profit = 0
            positions_count = 0
            
            # Pobierz informacje o koncie z rzeczywistego MT5
            account_info = {}
            positions_data = []
            
            if self.real_mt5_server:
                try:
                    # Pobierz dane konta z rzeczywistego MT5Server
                    account_info = self.real_mt5_server.get_account_info()
                    logger.info("Pobrano informacje o koncie z MT5")
                    
                    # Pobierz dane o pozycjach z rzeczywistego MT5Server
                    positions_data_dict = self.real_mt5_server.get_positions_data()
                    positions_data = positions_data_dict.get("positions", [])
                    logger.info(f"Pobrano {len(positions_data)} pozycji z MT5")
                except Exception as e:
                    logger.error(f"Błąd podczas pobierania danych z MT5: {str(e)}")
            
            # Jeśli nie udało się pobrać danych lub MT5 nie jest dostępny, użyj przykładowych danych
            if not account_info:
                logger.warning("Używam przykładowych danych o koncie")
                account_info = {
                    "balance": 10000,
                    "equity": 10250,
                    "margin": 2000,
                    "free_margin": 8250,
                    "margin_level": 512.5
                }
            
            if not positions_data:
                logger.warning("Używam przykładowych danych o pozycjach")
                positions_data = [
                    {
                        "ticket": 12345,
                        "symbol": "EURUSD",
                        "type": "BUY",
                        "volume": 0.1,
                        "open_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "profit": 125.50
                    },
                    {
                        "ticket": 12346,
                        "symbol": "GOLD",
                        "type": "SELL",
                        "volume": 0.05,
                        "open_time": (datetime.now() - timedelta(hours=2)).strftime("%Y-%m-%d %H:%M:%S"),
                        "profit": -35.25
                    }
                ]
            
            total_profit = sum(pos.get("profit", 0) for pos in positions_data)
            positions_count = len(positions_data)
            
            # Przygotowanie odpowiedzi
            response = {
                "connections": [
                    {
                        "status": "active",
                        "last_ping": self.last_connection_time.isoformat(),
                        "positions": positions_count,
                        "profit": total_profit,
                        "account_balance": account_info.get("balance", 0),
                        "account_equity": account_info.get("equity", 0),
                        "margin": account_info.get("margin", 0),
                        "free_margin": account_info.get("free_margin", 0),
                        "margin_level": account_info.get("margin_level", 0),
                        "positions_data": positions_data
                    }
                ]
            }
            
            return response
        
        @self.app.get("/monitoring/positions")
        async def get_positions():
            """Endpoint do pobierania pozycji z MT5."""
            global shared_memory
            
            try:
                # Użyj danych ze współdzielonej pamięci
                positions_data = shared_memory.get("positions", {})
                
                # Konwersja słownika pozycji do listy
                positions = list(positions_data.values()) if isinstance(positions_data, dict) else []
                
                # Sprawdź, czy mamy jakieś pozycje
                if positions:
                    logger.info(f"Zwracam {len(positions)} zapisanych pozycji ze współdzielonej pamięci")
                    return {
                        "status": "ok",
                        "positions": positions,
                        "timestamp": datetime.now().isoformat()
                    }
                
                # Jeśli nie ma zapisanych pozycji, zwracamy pustą listę zamiast przykładowych danych
                logger.warning("Brak pozycji w pamięci - zwracam pustą listę")
                return {
                    "status": "ok",
                    "positions": [],
                    "timestamp": datetime.now().isoformat()
                }
            except Exception as e:
                logger.error(f"Błąd podczas pobierania pozycji: {str(e)}")
                return {
                    "status": "error",
                    "message": f"Błąd podczas pobierania pozycji: {str(e)}",
                    "positions": []
                }
        
        @self.app.post("/position/sync")
        async def sync_positions_with_mt5():
            """Endpoint do synchronizacji pozycji z MT5."""
            global shared_memory, mt5_server_instance
            
            try:
                if not mt5_server_instance or not hasattr(mt5_server_instance, 'real_mt5_server') or not mt5_server_instance.real_mt5_server:
                    logger.error("Nie można zsynchronizować pozycji - brak połączenia z MT5")
                    return {
                        "status": "error",
                        "message": "Nie można zsynchronizować pozycji - brak połączenia z MT5",
                        "timestamp": datetime.now().isoformat()
                    }
                
                # Próba pobrania pozycji z MT5
                positions = []
                try:
                    positions = mt5_server_instance.real_mt5_server.get_positions()
                    logger.info(f"Pobrano {len(positions)} pozycji z MT5")
                except Exception as e:
                    logger.error(f"Błąd podczas pobierania pozycji z MT5: {str(e)}")
                    return {
                        "status": "error",
                        "message": f"Błąd podczas pobierania pozycji z MT5: {str(e)}",
                        "timestamp": datetime.now().isoformat()
                    }
                
                # Aktualizacja współdzielonej pamięci
                positions_dict = {}
                for pos in positions:
                    if 'ticket' in pos:
                        positions_dict[pos['ticket']] = pos
                
                shared_memory["positions"] = positions_dict
                shared_memory["last_update"] = datetime.now().isoformat()
                
                logger.info(f"Pamięć pozycji zaktualizowana: {len(positions_dict)} pozycji")
                
                return {
                    "status": "ok",
                    "message": f"Zsynchronizowano {len(positions_dict)} pozycji z MT5",
                    "positions_count": len(positions_dict),
                    "timestamp": datetime.now().isoformat()
                }
            except Exception as e:
                logger.error(f"Błąd podczas synchronizacji pozycji: {str(e)}")
                return {
                    "status": "error",
                    "message": f"Błąd podczas synchronizacji pozycji: {str(e)}",
                    "timestamp": datetime.now().isoformat()
                }
        
        @self.app.get("/monitoring/transactions")
        async def get_transactions():
            """Zwraca historię transakcji."""
            # Pobierz dane o transakcjach z rzeczywistego MT5
            transactions = []
            
            if self.real_mt5_server:
                try:
                    # Pobierz dane o transakcjach z rzeczywistego MT5Server
                    transactions = self.real_mt5_server.get_recent_transactions()
                    logger.info(f"Pobrano {len(transactions)} transakcji z MT5")
                except Exception as e:
                    logger.error(f"Błąd podczas pobierania transakcji z MT5: {str(e)}")
            
            # Jeśli nie udało się pobrać danych lub MT5 nie jest dostępny, użyj przykładowych danych
            if not transactions:
                logger.warning("Używam przykładowych danych o transakcjach")
                transactions = [
                    {
                        "id": "tx001",
                        "ticket": 12340,
                        "symbol": "EURUSD",
                        "type": "BUY",
                        "volume": 0.1,
                        "open_time": (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S"),
                        "close_time": (datetime.now() - timedelta(hours=4)).strftime("%Y-%m-%d %H:%M:%S"),
                        "open_price": 1.0820,
                        "close_price": 1.0870,
                        "profit": 50.00,
                        "status": "CLOSED"
                    },
                    {
                        "id": "tx002",
                        "ticket": 12341,
                        "symbol": "GOLD",
                        "type": "SELL",
                        "volume": 0.05,
                        "open_time": (datetime.now() - timedelta(days=2)).strftime("%Y-%m-%d %H:%M:%S"),
                        "close_time": (datetime.now() - timedelta(days=1, hours=6)).strftime("%Y-%m-%d %H:%M:%S"),
                        "open_price": 2370.25,
                        "close_price": 2320.50,
                        "profit": 247.50,
                        "status": "CLOSED"
                    }
                ]
            
            response = {
                "status": "ok",
                "transactions": transactions,
                "timestamp": datetime.now().isoformat()
            }
            
            return response
        
        @self.app.get("/monitoring/performance")
        async def get_performance():
            """Zwraca metryki wydajności systemu."""
            # Przykładowe dane o wydajności
            response = {
                "status": "ok",
                "metrics": {
                    "win_rate": 0.625,
                    "profit_factor": 2.15,
                    "avg_profit": 45.80,
                    "avg_loss": 21.35,
                    "sharpe_ratio": 1.65,
                    "max_drawdown": 0.052,
                    "total_trades": 48,
                    "winning_trades": 30,
                    "losing_trades": 18
                }
            }
            
            return response
        
        @self.app.get("/ai/models")
        async def get_ai_models():
            """Zwraca informacje o dostępnych modelach AI."""
            try:
                from src.monitoring.ai_monitor import get_ai_monitor
                from datetime import datetime, timedelta
                
                # Próba pobrania danych od AI monitora
                ai_monitor = get_ai_monitor()
                if ai_monitor and hasattr(ai_monitor, 'get_model_stats'):
                    ai_stats = ai_monitor.get_model_stats()
                    
                    if ai_stats and len(ai_stats) > 0:
                        # Mamy rzeczywiste dane
                        models_data = []
                        for model_name, stats in ai_stats.items():
                            models_data.append({
                                "name": model_name.capitalize(),
                                "accuracy": stats.get("accuracy", 0.0),
                                "roi": stats.get("roi", 0.0),
                                "cost_per_request": stats.get("cost_per_request", 0.0),
                                "total_requests": stats.get("total_requests", 0),
                                "active": stats.get("active", True)
                            })
                        
                        return {
                            "status": "ok",
                            "models": models_data,
                            "timestamp": datetime.now().isoformat()
                        }
                    else:
                        # Brak danych, używamy demonstracyjnych
                        from src.analysis.demo_data import get_demo_data_provider
                        demo_provider = get_demo_data_provider()
                        return demo_provider.get_ai_models_data()
                else:
                    # Brak monitora AI, używamy demonstracyjnych
                    from src.analysis.demo_data import get_demo_data_provider
                    demo_provider = get_demo_data_provider()
                    return demo_provider.get_ai_models_data()
            except Exception as e:
                logger.error(f"Błąd podczas pobierania danych modeli AI: {str(e)}")
                # W przypadku błędu, używamy demonstracyjnych
                try:
                    from src.analysis.demo_data import get_demo_data_provider
                    demo_provider = get_demo_data_provider()
                    return demo_provider.get_ai_models_data()
                except Exception as e2:
                    logger.error(f"Błąd podczas generowania demonstracyjnych danych AI: {str(e2)}")
                    return {
                        "status": "error",
                        "message": f"Nie można pobrać danych o modelach AI: {str(e)}",
                        "models": [],
                        "timestamp": datetime.now().isoformat()
                    }
        
        @self.app.get("/ai/costs")
        async def get_ai_costs():
            """Zwraca informacje o kosztach używania modeli AI."""
            try:
                from src.monitoring.ai_monitor import get_ai_monitor
                from datetime import datetime, timedelta
                
                ai_monitor = get_ai_monitor()
                ai_usage_repository = ai_monitor.ai_usage_repository
                
                # Pobierz dane o kosztach z ostatnich 30 dni
                days = 30
                daily_stats = ai_usage_repository.get_daily_usage_stats(days=days)
                
                # Sprawdź, czy są jakiekolwiek dane
                if not daily_stats:
                    return {
                        "status": "no_data",
                        "message": "Brak danych o kosztach API. Aby rozpocząć zbieranie danych, wykonaj zapytania do modeli AI.",
                        "period_days": days,
                        "models": {
                            "claude": {"total_cost": 0, "total_requests": 0},
                            "grok": {"total_cost": 0, "total_requests": 0},
                            "deepseek": {"total_cost": 0, "total_requests": 0},
                            "ensemble": {"total_cost": 0, "total_requests": 0}
                        },
                        "cost_thresholds": ai_monitor.cost_thresholds
                    }
                
                # Pobierz zagregowane statystyki dla każdego modelu
                end_time = datetime.now()
                start_time = end_time - timedelta(days=days)
                
                model_stats = {}
                for model_name in ['claude', 'grok', 'deepseek', 'ensemble']:
                    model_stats[model_name] = ai_usage_repository.get_model_performance(model_name, days=days)
                
                # Sprawdź, czy udało się pobrać statystyki dla modeli
                if not any(model_stats.values()):
                    return {
                        "status": "partial_data",
                        "message": "Dostępne są tylko podstawowe dane o kosztach API. Pełne statystyki będą dostępne po wykonaniu większej liczby zapytań.",
                        "period_days": days,
                        "models": {
                            "claude": {"total_cost": 0, "total_requests": 0},
                            "grok": {"total_cost": 0, "total_requests": 0},
                            "deepseek": {"total_cost": 0, "total_requests": 0},
                            "ensemble": {"total_cost": 0, "total_requests": 0}
                        },
                        "cost_thresholds": ai_monitor.cost_thresholds,
                        "daily_stats": daily_stats  # Dodajemy surowe dane
                    }
                
                # Przygotuj dane o dziennych kosztach
                daily_costs = {}
                for stat in daily_stats:
                    day = stat.get('day', '').isoformat() if not isinstance(stat.get('day', ''), str) else stat.get('day', '')
                    model = stat.get('model_name', '')
                    cost = stat.get('daily_cost', 0)
                    
                    if day not in daily_costs:
                        daily_costs[day] = {}
                    
                    daily_costs[day][model] = cost
                
                # Oblicz sumy i średnie
                total_cost = sum(stat.get('daily_cost', 0) for stat in daily_stats)
                total_requests = sum(stat.get('requests', 0) for stat in daily_stats)
                avg_cost_per_request = total_cost / total_requests if total_requests > 0 else 0
                
                # Przygotuj odpowiedź
                response = {
                    "status": "ok",
                    "total_cost": total_cost,
                    "total_requests": total_requests,
                    "avg_cost_per_request": avg_cost_per_request,
                    "period_days": days,
                    "start_date": start_time.isoformat(),
                    "end_date": end_time.isoformat(),
                    "models": {
                        model: {
                            "total_cost": stats.get('total_cost', 0),
                            "total_requests": stats.get('total_requests', 0),
                            "avg_tokens_input": stats.get('avg_tokens_input', 0),
                            "avg_tokens_output": stats.get('avg_tokens_output', 0),
                            "success_rate": stats.get('success_rate', 0),
                            "avg_duration_ms": stats.get('avg_duration_ms', 0)
                        } for model, stats in model_stats.items() if stats
                    },
                    "daily_costs": daily_costs,
                    "cost_thresholds": ai_monitor.cost_thresholds
                }
                
                return response
                
            except Exception as e:
                logger.error(f"Błąd podczas pobierania danych o kosztach AI: {e}")
                import traceback
                logger.debug(traceback.format_exc())
                
                # Zamiast zwracać komunikat o błędzie, używamy danych demonstracyjnych
                try:
                    from src.analysis.demo_data import get_demo_data_provider
                    demo_provider = get_demo_data_provider()
                    return demo_provider.get_ai_costs_data()
                except Exception as e2:
                    logger.error(f"Błąd podczas generowania demonstracyjnych danych o kosztach: {e2}")
                    # Jeśli nawet dane demonstracyjne nie działają, zwracamy minimalną strukturę
                    return {
                        "status": "error",
                        "message": f"Nie można pobrać danych o kosztach AI: {str(e)}",
                        "period_days": 30,
                        "total_cost": 0,
                        "total_requests": 0,
                        "models": {},
                        "timestamp": datetime.now().isoformat()
                    }
        
        @self.app.get("/ai/performance")
        async def get_ai_performance():
            """Zwraca analizę efektywności modeli AI na podstawie zebranych sygnałów."""
            try:
                from src.database.trading_signal_repository import get_trading_signal_repository
                from collections import defaultdict
                
                # Pobieranie sygnałów z bazy danych
                signal_repo = get_trading_signal_repository()
                all_signals = signal_repo.get_latest_signals(limit=100)  # Pobierz ostatnie 100 sygnałów
                
                # Analiza sygnałów według modeli AI
                models_stats = defaultdict(lambda: {
                    "total_signals": 0,
                    "buy_signals": 0,
                    "sell_signals": 0,
                    "high_confidence_signals": 0,  # Sygnały z pewnością > 0.8
                    "avg_confidence": 0,
                    "signals_by_symbol": defaultdict(int),
                    "signals_by_timeframe": defaultdict(int)
                })
                
                # Zliczanie statystyk
                for signal in all_signals:
                    model = signal.model_name
                    models_stats[model]["total_signals"] += 1
                    models_stats[model]["buy_signals"] += 1 if signal.direction.upper() == "BUY" else 0
                    models_stats[model]["sell_signals"] += 1 if signal.direction.upper() == "SELL" else 0
                    models_stats[model]["high_confidence_signals"] += 1 if signal.confidence > 0.8 else 0
                    models_stats[model]["avg_confidence"] += signal.confidence
                    models_stats[model]["signals_by_symbol"][signal.symbol] += 1
                    models_stats[model]["signals_by_timeframe"][signal.timeframe] += 1
                
                # Obliczenie średnich wartości
                for model in models_stats:
                    if models_stats[model]["total_signals"] > 0:
                        models_stats[model]["avg_confidence"] /= models_stats[model]["total_signals"]
                
                # Przygotowanie danych do odpowiedzi
                performance_data = []
                for model, stats in models_stats.items():
                    performance_data.append({
                        "model": model,
                        "total_signals": stats["total_signals"],
                        "buy_signals": stats["buy_signals"],
                        "sell_signals": stats["sell_signals"],
                        "buy_percentage": round(stats["buy_signals"] / stats["total_signals"] * 100, 2) if stats["total_signals"] > 0 else 0,
                        "sell_percentage": round(stats["sell_signals"] / stats["total_signals"] * 100, 2) if stats["total_signals"] > 0 else 0,
                        "high_confidence_percentage": round(stats["high_confidence_signals"] / stats["total_signals"] * 100, 2) if stats["total_signals"] > 0 else 0,
                        "avg_confidence": round(stats["avg_confidence"], 2),
                        "top_symbols": sorted(stats["signals_by_symbol"].items(), key=lambda x: x[1], reverse=True)[:3],
                        "top_timeframes": sorted(stats["signals_by_timeframe"].items(), key=lambda x: x[1], reverse=True)[:3]
                    })
                
                # Obliczenie ogólnych statystyk
                total_signals = sum(stats["total_signals"] for stats in models_stats.values())
                avg_global_confidence = sum(stats["avg_confidence"] * stats["total_signals"] for stats in models_stats.values()) / total_signals if total_signals > 0 else 0
                
                return {
                    "status": "ok",
                    "total_signals_analyzed": total_signals,
                    "avg_global_confidence": round(avg_global_confidence, 2),
                    "models_performance": performance_data,
                    "timestamp": datetime.now().isoformat()
                }
                
            except Exception as e:
                logger.error(f"Błąd podczas analizy efektywności modeli AI: {e}")
                import traceback
                logger.debug(traceback.format_exc())
                return {
                    "status": "error",
                    "message": f"Błąd podczas analizy efektywności modeli AI: {str(e)}",
                    "timestamp": datetime.now().isoformat()
                }
        
        @self.app.post("/ai/generate_signal")
        async def generate_signal(request: Request):
            """
            Endpoint do generowania sygnału tradingowego na żądanie dla określonego instrumentu.
            
            Przykładowe żądanie:
            {
                "symbol": "EURUSD",
                "timeframe": "M15"  // opcjonalnie
            }
            """
            try:
                data = await request.json()
                symbol = data.get("symbol")
                timeframe = data.get("timeframe", "M15")  # Domyślny timeframe to M15
                
                if not symbol:
                    logger.error("Brak wymaganego parametru 'symbol' w żądaniu")
                    return {
                        "status": "error",
                        "message": "Brak wymaganego parametru 'symbol'",
                        "timestamp": datetime.now().isoformat()
                    }
                
                # Import i inicjalizacja generatora sygnałów
                from src.analysis.signal_generator import SignalGenerator
                signal_generator = SignalGenerator()
                
                # Generowanie sygnału
                signal = signal_generator.generate_signal(symbol, timeframe)
                
                if not signal:
                    logger.warning(f"Nie wygenerowano sygnału dla {symbol} ({timeframe})")
                    return {
                        "status": "warning",
                        "message": f"Nie wygenerowano sygnału dla {symbol} ({timeframe})",
                        "timestamp": datetime.now().isoformat()
                    }
                
                # Konwersja sygnału do formatu JSON
                signal_data = {
                    "id": signal.id if hasattr(signal, "id") else None,
                    "symbol": signal.symbol,
                    "direction": signal.direction,
                    "confidence": signal.confidence,
                    "entry_price": signal.entry_price,
                    "stop_loss": signal.stop_loss,
                    "take_profit": signal.take_profit,
                    "analysis": signal.analysis,
                    "timeframe": signal.timeframe,
                    "timestamp": signal.timestamp.isoformat() if hasattr(signal.timestamp, "isoformat") else str(signal.timestamp),
                    "expiry": signal.expiry.isoformat() if hasattr(signal.expiry, "isoformat") else str(signal.expiry),
                    "model_name": signal.model_name,
                    "risk_reward_ratio": signal.risk_reward_ratio
                }
                
                logger.info(f"Wygenerowano sygnał dla {symbol} ({timeframe}): {signal_data['direction']} z pewnością {signal_data['confidence']}")
                
                return {
                    "status": "ok",
                    "message": f"Wygenerowano sygnał dla {symbol} ({timeframe})",
                    "signal": signal_data,
                    "timestamp": datetime.now().isoformat()
                }
                
            except Exception as e:
                logger.error(f"Błąd podczas generowania sygnału AI: {e}")
                import traceback
                logger.debug(traceback.format_exc())
                return {
                    "status": "error",
                    "message": f"Błąd podczas generowania sygnału AI: {str(e)}",
                    "timestamp": datetime.now().isoformat()
                }

        @self.app.get("/ai/signals")
        async def get_ai_signals():
            """
            Zwraca dane o sygnałach AI.
            """
            try:
                # W tej chwili używamy tylko danych demonstracyjnych
                from src.analysis.demo_data import get_demo_data_provider
                demo_provider = get_demo_data_provider()
                return demo_provider.get_ai_signals_data()
            except Exception as e:
                logger.error(f"Błąd podczas pobierania danych o sygnałach AI: {e}")
                import traceback
                logger.debug(traceback.format_exc())
                
                return {
                    "status": "error",
                    "message": f"Błąd podczas pobierania danych o sygnałach AI: {str(e)}",
                    "signals": [],
                    "timestamp": datetime.now().isoformat()
                }

        @self.app.get("/ai/signals/latest")
        async def get_latest_ai_signals(limit: int = 10):
            """
            Zwraca najnowsze sygnały handlowe wygenerowane przez AI.
            
            Args:
                limit: liczba najnowszych sygnałów do pobrania (domyślnie 10)
            """
            try:
                from src.database.trading_signal_repository import get_trading_signal_repository
                
                # Pobieranie sygnałów z repozytorium
                signal_repo = get_trading_signal_repository()
                signals = signal_repo.get_latest_signals(limit=limit)
                
                if not signals:
                    logger.warning(f"Nie znaleziono żadnych sygnałów w bazie danych - używam danych demonstracyjnych")
                    # Nie znaleziono sygnałów, używamy danych demonstracyjnych
                    from src.analysis.demo_data import get_demo_data_provider
                    demo_provider = get_demo_data_provider()
                    return demo_provider.get_latest_signals(limit=limit)
                
                # Konwersja sygnałów do formatu JSON
                signals_data = []
                for signal in signals:
                    signal_data = {
                        "id": signal.id if hasattr(signal, "id") else None,
                        "symbol": signal.symbol,
                        "direction": signal.direction,
                        "confidence": signal.confidence,
                        "entry_price": signal.entry_price,
                        "stop_loss": signal.stop_loss,
                        "take_profit": signal.take_profit,
                        "analysis": signal.ai_analysis if hasattr(signal, "ai_analysis") else "",
                        "timeframe": signal.timeframe,
                        "timestamp": signal.timestamp.isoformat() if hasattr(signal.timestamp, "isoformat") else str(signal.timestamp),
                        "expiry": signal.expiry.isoformat() if hasattr(signal, "expiry") and hasattr(signal.expiry, "isoformat") else (
                            str(signal.expiry) if hasattr(signal, "expiry") else None
                        ),
                        "model_name": signal.model_name if hasattr(signal, "model_name") else "AutoTrader",
                        "risk_reward_ratio": getattr(signal, "risk_reward_ratio", None)
                    }
                    signals_data.append(signal_data)
                
                logger.info(f"Pobrano {len(signals_data)} najnowszych sygnałów z bazy danych")
                
                return {
                    "status": "ok",
                    "count": len(signals_data),
                    "signals": signals_data,
                    "timestamp": datetime.now().isoformat()
                }
                
            except Exception as e:
                logger.error(f"Błąd podczas pobierania najnowszych sygnałów AI: {e}")
                import traceback
                logger.debug(traceback.format_exc())
                
                # W przypadku błędu, używamy danych demonstracyjnych
                try:
                    from src.analysis.demo_data import get_demo_data_provider
                    demo_provider = get_demo_data_provider()
                    return demo_provider.get_latest_signals(limit=limit)
                except Exception as e2:
                    logger.error(f"Błąd podczas generowania demonstracyjnych sygnałów: {e2}")
                    return {
                        "status": "error",
                        "message": f"Błąd podczas pobierania najnowszych sygnałów AI: {str(e)}",
                        "signals": [],
                        "timestamp": datetime.now().isoformat()
                    }
    
        @self.app.get("/ai/signals/analysis")
        async def get_ai_signals_analysis():
            """
            Zwraca dane o sygnałach do analizy wydajności AI.
            """
            try:
                # Próbujemy pobrać dane z bazy
                from src.database.trading_signal_repository import get_trading_signal_repository
                from src.database.signal_evaluation_repository import get_signal_evaluation_repository
                
                # Pobierz dane o sygnałach i ich ocenach
                signal_repo = get_trading_signal_repository()
                eval_repo = get_signal_evaluation_repository()
                
                # Sprawdź czy mamy wystarczająco dużo danych
                signals = signal_repo.get_latest_signals(limit=50)
                evaluations = eval_repo.get_latest_evaluations(limit=50) if eval_repo else []
                
                # Jeśli mamy wystarczająco dużo danych, przetwarzamy je
                if len(signals) > 10 or len(evaluations) > 10:
                    logger.info(f"Pobrano {len(signals)} sygnałów i {len(evaluations)} ocen sygnałów z bazy danych")
                    
                    # Tu powinno być przetwarzanie rzeczywistych danych
                    # Dla uproszczenia na razie zawsze używamy danych demonstracyjnych
                    from src.analysis.demo_data import get_demo_data_provider
                    demo_provider = get_demo_data_provider()
                    return demo_provider.get_ai_signals_data()
                else:
                    logger.warning(f"Nie znaleziono wystarczającej liczby sygnałów do analizy - używam danych demonstracyjnych")
                    from src.analysis.demo_data import get_demo_data_provider
                    demo_provider = get_demo_data_provider()
                    return demo_provider.get_ai_signals_data()
                    
            except Exception as e:
                logger.error(f"Błąd podczas pobierania danych o sygnałach do analizy: {e}")
                import traceback
                logger.debug(traceback.format_exc())
                
                # W przypadku błędu, używamy danych demonstracyjnych
                try:
                    from src.analysis.demo_data import get_demo_data_provider
                    demo_provider = get_demo_data_provider()
                    return demo_provider.get_ai_signals_data()
                except Exception as e2:
                    logger.error(f"Błąd podczas generowania demonstracyjnych danych o sygnałach: {e2}")
                    return {
                        "status": "error",
                        "message": f"Błąd podczas pobierania danych o sygnałach AI: {str(e)}",
                        "signals": [],
                        "timestamp": datetime.now().isoformat()
                    }

    def _run_server(self):
        """Uruchomienie serwera w osobnym wątku."""
        uvicorn.run(
            self.app,
            host=self.host,
            port=self.port,
            log_level="info",
            loop="asyncio"
        )
        
    async def start(self):
        """Uruchomienie serwera HTTP."""
        logger.info(f"Uruchamianie serwera HTTP na {self.host}:{self.port}")
        
        # Uruchomienie serwera w osobnym wątku
        self._server_thread = threading.Thread(target=self._run_server)
        self._server_thread.daemon = True
        self._server_thread.start()
        
        # Czekanie na uruchomienie serwera
        await asyncio.sleep(1)
        
        # Oznaczenie serwera jako gotowy
        self._ready.set()
        
        logger.info(f"Serwer HTTP uruchomiony na {self.host}:{self.port}")
    
    async def shutdown(self):
        """Zatrzymanie serwera HTTP."""
        logger.info("Zatrzymywanie serwera HTTP")
        
        # Zatrzymanie agenta, jeśli jest uruchomiony i kontroler jest ustawiony
        if self._agent_controller:
            status = self._agent_controller.get_status()
            if status["status"] == "running":
                logger.info("Zatrzymywanie agenta przed zamknięciem serwera")
                self._agent_controller.stop_agent()
        
        # Zamknięcie zasobów
        self._shutdown_event.set()
        
        logger.info("Serwer HTTP zatrzymany")

    def ping(self):
        """
        Prosty endpoint do sprawdzania czy serwer działa (GET).
        
        Returns:
            Response: Odpowiedź "pong" jako tekst
        """
        self.last_connection_time = datetime.now()
        return Response(content="pong", media_type="text/plain")

    def post_ping(self):
        """
        Endpoint POST do sprawdzania czy serwer działa.
        
        Returns:
            Dict: Status odpowiedzi
        """
        self.last_connection_time = datetime.now()
        return {"status": "ok", "message": "pong"}

    def handle_market_data(self, data: MarketData):
        """
        Aktualizacja danych rynkowych z EA.
        
        Args:
            data: Dane rynkowe
            
        Returns:
            Dict: Status operacji
        """
        logger.info(f"Otrzymano dane rynkowe dla {data.symbol} od {data.ea_id}")
        
        # Zapisanie danych w pamięci współdzielonej
        global shared_memory
        if "market_data" not in shared_memory:
            shared_memory["market_data"] = {}
        
        # Aktualizacja danych rynkowych dla danego symbolu
        shared_memory["market_data"][data.symbol] = {
            "symbol": data.symbol,
            "bid": data.bid,
            "ask": data.ask,
            "last": data.last,
            "volume": data.volume,
            "time": data.time,
            "last_update": datetime.now().isoformat(),
            "ea_id": data.ea_id
        }
        
        return {"status": "ok", "message": f"Dane rynkowe dla {data.symbol} zaktualizowane"}

    def get_market_data(self, symbol: Optional[str] = None):
        """
        Pobieranie aktualnych danych rynkowych.
        
        Args:
            symbol: Opcjonalny symbol instrumentu
            
        Returns:
            Dict: Dane rynkowe
        """
        global shared_memory
        
        # Inicjalizacja market_data jeśli nie istnieje
        if "market_data" not in shared_memory:
            shared_memory["market_data"] = {}
        
        # Jeśli podano symbol, zwróć dane tylko dla tego symbolu
        if symbol:
            if symbol in shared_memory["market_data"]:
                return {
                    "status": "ok", 
                    "market_data": shared_memory["market_data"][symbol]
                }
            else:
                return {
                    "status": "error", 
                    "message": f"Brak danych rynkowych dla symbolu {symbol}"
                }
        
        # Jeśli nie podano symbolu, zwróć wszystkie dostępne dane rynkowe
        return {
            "status": "ok", 
            "market_data": shared_memory["market_data"]
        }

    def update_positions(self, update: PositionUpdate):
        """
        Aktualizacja pozycji z EA.
        
        Args:
            update: Dane aktualizacji pozycji
            
        Returns:
            Dict: Status operacji
        """
        global shared_memory
        
        if self.real_mt5_server:
            # Zapisz aktualizację pozycji
            try:
                # Przetwarzamy i zapisujemy pozycje w formacie MT5Server
                positions_data = {
                    "ea_id": update.ea_id,
                    "positions": update.positions
                }
                
                # Aktualizacja współdzielonej pamięci
                if update.positions:
                    positions_dict = {}
                    for position in update.positions:
                        ticket = position.get("ticket", 0)
                        if ticket > 0:
                            positions_dict[ticket] = position
                    
                    shared_memory["positions"] = positions_dict
                    shared_memory["last_update"] = datetime.now()
                    logger.info(f"Zaktualizowano współdzieloną pamięć: {len(positions_dict)} pozycji")
                
                # Przekazujemy dane w formacie expected przez _handle_positions_update
                data_str = json.dumps(positions_data)
                self.real_mt5_server._handle_positions_update(data_str)
                logger.info(f"Zapisano {len(update.positions)} pozycji od EA: {update.ea_id}")
                return {"status": "ok"}
            except Exception as e:
                logger.error(f"Błąd podczas przetwarzania aktualizacji pozycji: {str(e)}")
                return {"status": "error", "message": str(e)}
        else:
            logger.warning("Serwer MT5 nie jest dostępny - nie można zapisać aktualizacji pozycji")
            return {"status": "error", "message": "Serwer MT5 nie jest dostępny"}

    def get_commands(self, ea_id: str = None):
        """
        Pobieranie komend do wykonania przez EA.
        
        Args:
            ea_id: Identyfikator EA
            
        Returns:
            Dict: Komendy do wykonania
        """
        logger.info(f"Otrzymano żądanie pobrania komend dla EA: {ea_id}")
        
        if not ea_id:
            logger.warning("Brak identyfikatora EA w żądaniu")
            return {"commands": []}
            
        # Pobieramy komendy z kolejki dla danego EA i czyścimy kolejkę
        commands = []
        with commands_lock:
            logger.info(f"Stan kolejki przed pobraniem: {command_queue}")
            if ea_id in command_queue and command_queue[ea_id]:
                commands = command_queue[ea_id].copy()
                command_queue[ea_id] = []  # Czyszczenie kolejki po pobraniu
                logger.info(f"Pobrano {len(commands)} komend dla EA {ea_id}")
            logger.info(f"Stan kolejki po pobraniu: {command_queue}")
        
        logger.info(f"Zwracam komendy dla EA {ea_id}: {commands}")
        return {"commands": commands}

    async def open_position(self, request: Request):
        """
        Obsługuje żądanie otwarcia pozycji.
        """
        try:
            data = await request.json()
            ea_id = data.get('ea_id')
            symbol = data.get('symbol')
            order_type = data.get('order_type')
            volume = data.get('volume')
            price = data.get('price')
            sl = data.get('sl')
            tp = data.get('tp')
            comment = data.get('comment', "API_ORDER")
            
            # Logowanie dla debugowania
            logger.info(f"[DEBUG] Otrzymano żądanie otwarcia pozycji: {data}")
            logger.info(f"[DEBUG] Stan kolejki przed dodaniem: {command_queue}")
            
            # Przygotowanie komendy dla EA
            command = {
                'action': 'OPEN_POSITION',
                'symbol': symbol,
                'type': order_type,
                'volume': volume,
                'timestamp': datetime.now().isoformat()
            }
            
            if price is not None:
                command['price'] = float(price)
            if sl is not None:
                command['sl'] = float(sl)
            if tp is not None:
                command['tp'] = float(tp)
            if comment is not None:
                command['comment'] = comment
            
            # Dodanie komendy do kolejki
            with commands_lock:
                if ea_id not in command_queue:
                    command_queue[ea_id] = []
                command_queue[ea_id].append(command)
                logger.info(f"[DEBUG] Stan kolejki po dodaniu: {command_queue}")
            
            logger.info(f"Dodano komendę otwarcia pozycji dla EA {ea_id}: {command}")
            
            return {
                "status": "ok",
                "message": f"Zlecenie otwarcia pozycji {symbol} ({order_type}) zostało dodane do kolejki",
                "command_id": len(command_queue.get(ea_id, [])),
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Błąd podczas przetwarzania żądania otwarcia pozycji: {str(e)}")
            return {
                "status": "error",
                "message": f"Błąd podczas przetwarzania żądania: {str(e)}",
                "timestamp": datetime.now().isoformat()
            }
        
    async def close_position(self, data: dict):
        """
        Zamyka istniejącą pozycję.
        
        Args:
            data: Dane pozycji do zamknięcia
            
        Returns:
            Dict: Status operacji
        """
        logger.info(f"Otrzymano żądanie zamknięcia pozycji: {data}")
        
        if "ea_id" not in data or "ticket" not in data:
            raise HTTPException(status_code=400, detail="Brak wymaganych parametrów ea_id lub ticket")
            
        ea_id = data["ea_id"]
        ticket = data["ticket"]
        
        # Dodaj polecenie zamknięcia pozycji do kolejki komend dla EA
        command = {
            "command": "CLOSE_POSITION",
            "id": f"cmd_{int(time.time())}",
            "data": data
        }
        
        # Tutaj dodajemy komendę do kolejki komend dla EA
        
        logger.info(f"Dodano polecenie zamknięcia pozycji {ticket} dla EA {ea_id}")
        
        return {
            "status": "ok",
            "message": "Position close command added to queue"
        }
        
    async def modify_position(self, data: dict):
        """
        Modyfikuje parametry istniejącej pozycji.
        
        Args:
            data: Dane pozycji do modyfikacji
            
        Returns:
            Dict: Status operacji
        """
        logger.info(f"Otrzymano żądanie modyfikacji pozycji: {data}")
        
        if "ea_id" not in data or "ticket" not in data:
            raise HTTPException(status_code=400, detail="Brak wymaganych parametrów ea_id lub ticket")
            
        ea_id = data["ea_id"]
        ticket = data["ticket"]
        
        # Dodaj polecenie modyfikacji pozycji do kolejki komend dla EA
        command = {
            "command": "MODIFY_POSITION",
            "id": f"cmd_{int(time.time())}",
            "data": data
        }
        
        # Tutaj dodajemy komendę do kolejki komend dla EA
        
        logger.info(f"Dodano polecenie modyfikacji pozycji {ticket} dla EA {ea_id}")
        
        return {
            "status": "ok",
            "message": "Position modify command added to queue"
        }

    def start_agent(self, params: AgentStartParams):
        """
        Uruchamia agenta handlowego w określonym trybie.
        
        Args:
            params: Parametry startu agenta (tryb pracy)
            
        Returns:
            Dict: Status operacji
        """
        logger.info(f"Żądanie uruchomienia agenta w trybie: {params.mode}")
        
        # Dynamiczny import, aby uniknąć problemów z cyklicznymi zależnościami
        from src.agent_controller import get_agent_controller
        
        agent_controller = get_agent_controller()
        if not agent_controller:
            logger.error("Kontroler agenta nie jest dostępny")
            return {
                "status": "error",
                "message": "Kontroler agenta nie jest dostępny",
                "timestamp": datetime.now().isoformat()
            }
        
        # Wywołanie faktycznej implementacji startu agenta z kontrolera
        result = agent_controller.start_agent(mode=params.mode)
        
        # Zwrócenie odpowiedzi
        if result.get("status") == "error":
            logger.error(f"Nie udało się uruchomić agenta: {result.get('message')}")
            return result
        else:
            logger.info(f"Agent uruchomiony pomyślnie w trybie: {params.mode}")
            return result

    def stop_agent(self):
        """
        Zatrzymuje agenta handlowego.
        
        Returns:
            Dict: Status operacji
        """
        logger.info("Żądanie zatrzymania agenta")
        
        # Dynamiczny import, aby uniknąć problemów z cyklicznymi zależnościami
        from src.agent_controller import get_agent_controller, AgentController
        
        agent_controller = get_agent_controller()
        if not agent_controller:
            logger.error("Kontroler agenta nie jest dostępny")
            return {
                "status": "error",
                "message": "Kontroler agenta nie jest dostępny",
                "timestamp": datetime.now().isoformat()
            }
        
        try:
            # Wywołanie faktycznej implementacji zatrzymania agenta z kontrolera
            logger.info("Delegowanie zatrzymania do kontrolera agenta")
            result = agent_controller.stop_agent()
            
            # Zwrócenie odpowiedzi
            if result.get("status") == "error":
                logger.error(f"Nie udało się zatrzymać agenta: {result.get('message')}")
                return result
            else:
                logger.info(f"Agent zatrzymany pomyślnie: {result}")
                return result
        except Exception as e:
            error_msg = f"Nieoczekiwany błąd podczas zatrzymywania agenta: {str(e)}"
            logger.error(error_msg, exc_info=True)
            
            # W przypadku błędu spróbujmy zresetować instancję kontrolera
            try:
                logger.warning("Próba awaryjnego resetowania kontrolera agenta")
                AgentController.reset_instance()
                logger.info("Kontroler agenta zresetowany awaryjnie")
            except Exception as reset_error:
                logger.error(f"Nie udało się zresetować kontrolera: {reset_error}")
            
            return {
                "status": "error",
                "message": error_msg,
                "timestamp": datetime.now().isoformat()
            }

    def restart_agent(self, params: Optional[AgentStartParams] = None):
        """
        Restartuje agenta handlowego, opcjonalnie zmieniając tryb pracy.
        
        Args:
            params: Opcjonalne parametry restartu (nowy tryb pracy)
            
        Returns:
            Dict: Status operacji
        """
        mode = params.mode if params else None
        logger.info(f"Żądanie restartu agenta{f' w trybie: {mode}' if mode else ''}")
        
        # Dynamiczny import, aby uniknąć problemów z cyklicznymi zależnościami
        from src.agent_controller import get_agent_controller
        
        agent_controller = get_agent_controller()
        if not agent_controller:
            logger.error("Kontroler agenta nie jest dostępny")
            return {
                "status": "error",
                "message": "Kontroler agenta nie jest dostępny",
                "timestamp": datetime.now().isoformat()
            }
        
        # Wywołanie faktycznej implementacji restartu agenta z kontrolera
        result = agent_controller.restart_agent(mode=mode)
        
        # Zwrócenie odpowiedzi
        if result.get("status") == "error":
            logger.error(f"Nie udało się zrestartować agenta: {result.get('message')}")
            return result
        else:
            logger.info("Agent zrestartowany pomyślnie")
            return result

    def agent_status(self):
        """
        Pobiera aktualny status agenta handlowego.
        
        Returns:
            Dict: Status agenta
        """
        # Unikamy importu bibliotek na poziomie modułu, żeby uniknąć cyklicznych zależności
        from src.agent_controller import get_agent_controller, AgentStatus
        
        agent_controller = get_agent_controller()
        
        if not agent_controller:
            return {"status": "unknown", "timestamp": datetime.now().isoformat()}
        
        status_value = agent_controller.status.value if hasattr(agent_controller.status, 'value') else str(agent_controller.status)
        mode_value = agent_controller.mode.value if hasattr(agent_controller.mode, 'value') else str(agent_controller.mode)
        
        # Obliczenie czasu pracy jeśli agent jest uruchomiony
        uptime_str = "N/A"
        if agent_controller.status == AgentStatus.RUNNING and agent_controller.start_time:
            uptime = datetime.now() - agent_controller.start_time
            hours, remainder = divmod(uptime.total_seconds(), 3600)
            minutes, seconds = divmod(remainder, 60)
            uptime_str = f"{int(hours)}h {int(minutes)}m {int(seconds)}s"
        
        return {
            "status": status_value,
            "mode": mode_value,
            "timestamp": datetime.now().isoformat(),
            "uptime": uptime_str,
            "error": agent_controller.error_message if hasattr(agent_controller, 'error_message') else None
        }

    def set_agent_config(self, data: dict):
        """
        Aktualizuje konfigurację agenta handlowego.
        
        Args:
            data: Dane konfiguracyjne
        
        Returns:
            Dict: Status operacji
        """
        # Unikamy importu bibliotek na poziomie modułu, żeby uniknąć cyklicznych zależności
        from src.agent_controller import get_agent_controller, AgentMode
        
        logger.info(f"Żądanie aktualizacji konfiguracji agenta")
        
        try:
            # Pobierz kontroler agenta
            agent_controller = get_agent_controller()
            
            if not agent_controller:
                logger.error("Kontroler agenta nie jest dostępny")
                return {"status": "error", "message": "Kontroler agenta nie jest dostępny"}
            
            # Ustaw tryb jeśli został przekazany
            if "mode" in data:
                try:
                    agent_controller.mode = AgentMode(data["mode"])
                    logger.info(f"Zmieniono tryb pracy agenta na: {data['mode']}")
                except ValueError:
                    logger.error(f"Nieprawidłowy tryb pracy: {data['mode']}")
                    return {"status": "error", "message": f"Nieprawidłowy tryb pracy: {data['mode']}"}
            
            # Zaktualizuj konfigurację
            if "risk_limits" in data:
                risk_limits = data["risk_limits"]
                
                # Mapowanie parametru max_positions z UI na max_positions_total w konfiguracji
                if "max_positions" in risk_limits:
                    risk_limits["max_positions_total"] = risk_limits.pop("max_positions")
                
                agent_controller.config["risk_limits"] = risk_limits
            
            if "instruments" in data:
                agent_controller.config["instruments"] = data["instruments"]
            
            # Zapisz komentarz, jeśli został przekazany
            comment = data.get("comment")
            
            # Zastosuj nową konfigurację
            agent_controller.apply_config()
            
            return {"status": "ok", "message": "Konfiguracja zaktualizowana"}
        
        except Exception as e:
            logger.error(f"Błąd podczas aktualizacji konfiguracji agenta: {e}")
            return {"status": "error", "message": str(e)}

    def get_agent_config_history(self, limit: int = 20):
        """
        Pobiera historię konfiguracji agenta.
        
        Args:
            limit: Maksymalna liczba rekordów do pobrania
        
        Returns:
            Dict: Status operacji i historia konfiguracji
        """
        # Unikamy importu bibliotek na poziomie modułu, żeby uniknąć cyklicznych zależności
        from src.agent_controller import get_agent_controller
        
        try:
            # Pobierz kontroler agenta
            agent_controller = get_agent_controller()
            
            if not agent_controller:
                logger.error("Kontroler agenta nie jest dostępny")
                return {"status": "error", "message": "Kontroler agenta nie jest dostępny"}
            
            # Pobierz historię konfiguracji
            config_history = agent_controller.get_config_history(limit=limit)
            
            return {
                "status": "ok", 
                "configs": config_history,
                "timestamp": datetime.now().isoformat()
            }
        
        except Exception as e:
            logger.error(f"Błąd podczas pobierania historii konfiguracji agenta: {e}")
            return {"status": "error", "message": str(e)}

    def restore_agent_config(self, data: dict):
        """
        Przywraca poprzednią konfigurację agenta.
        
        Args:
            data: Dane zawierające ID konfiguracji do przywrócenia
        
        Returns:
            Dict: Status operacji
        """
        # Unikamy importu bibliotek na poziomie modułu, żeby uniknąć cyklicznych zależności
        from src.agent_controller import get_agent_controller
        
        try:
            if "config_id" not in data:
                logger.error("Brak wymaganego parametru config_id")
                return {"status": "error", "message": "Brak wymaganego parametru config_id"}
            
            config_id = data["config_id"]
            logger.info(f"Żądanie przywrócenia konfiguracji agenta o ID: {config_id}")
            
            # Pobierz kontroler agenta
            agent_controller = get_agent_controller()
            
            if not agent_controller:
                logger.error("Kontroler agenta nie jest dostępny")
                return {"status": "error", "message": "Kontroler agenta nie jest dostępny"}
            
            # Przywróć konfigurację
            success = agent_controller.restore_config(config_id)
            
            if success:
                logger.info(f"Pomyślnie przywrócono konfigurację o ID: {config_id}")
                return {
                    "status": "ok", 
                    "message": f"Konfiguracja ID: {config_id} przywrócona pomyślnie",
                    "timestamp": datetime.now().isoformat()
                }
            else:
                logger.error(f"Nie udało się przywrócić konfiguracji o ID: {config_id}")
                return {"status": "error", "message": f"Nie udało się przywrócić konfiguracji ID: {config_id}"}
        
        except Exception as e:
            logger.error(f"Błąd podczas przywracania konfiguracji agenta: {e}")
            return {"status": "error", "message": str(e)}

    def get_account_info(self):
        """Zwraca informacje o koncie MT5."""
        try:
            if self.real_mt5_server:
                account_info = self.real_mt5_server.get_account_info()
                if account_info:
                    return {
                        "status": "ok",
                        "account_info": account_info,
                        "timestamp": datetime.now().isoformat()
                    }
        except Exception as e:
            logger.error(f"Błąd podczas pobierania informacji o koncie z MT5: {str(e)}")
        
        # Jeśli nie udało się pobrać danych lub MT5 nie jest dostępny, użyj przykładowych danych
        logger.warning("Używam przykładowych danych o koncie")
        example_account = {
            "login": 12345678,
            "balance": 10000,
            "equity": 10250,
            "margin": 2000,
            "free_margin": 8250,
            "margin_level": 512.5,
            "leverage": 100,
            "currency": "USD"
        }
        
        return {
            "status": "ok",
            "account_info": example_account,
            "timestamp": datetime.now().isoformat()
        }
        
    def get_instruments(self):
        """Zwraca listę obserwowanych instrumentów."""
        try:
            if self.real_mt5_server:
                instruments = self.real_mt5_server.get_observed_instruments()
                return {
                    "status": "ok",
                    "instruments": instruments,
                    "count": len(instruments),
                    "timestamp": datetime.now().isoformat()
                }
            else:
                # Jeśli rzeczywisty serwer MT5 nie jest dostępny, zwraca domyślną listę
                return {
                    "status": "ok",
                    "instruments": ["EURUSD", "GBPUSD", "USDJPY", "XAUUSD", "BTCUSD"],
                    "count": 5,
                    "timestamp": datetime.now().isoformat()
                }
        except Exception as e:
            logger.error(f"Błąd podczas pobierania listy instrumentów: {str(e)}")
            return {
                "status": "error",
                "message": str(e),
                "timestamp": datetime.now().isoformat()
            }
            
    async def update_instruments(self, request: Request):
        """Aktualizuje listę obserwowanych instrumentów."""
        try:
            data = await request.json()
            logger.info(f"Otrzymano żądanie aktualizacji listy instrumentów: {data}")
            
            if 'instruments' not in data:
                logger.error("Brak wymaganego pola: instruments")
                return {
                    "status": "error",
                    "message": "Brak wymaganego pola: instruments",
                    "timestamp": datetime.now().isoformat()
                }
            
            instruments = data['instruments']
            
            if not isinstance(instruments, list):
                logger.error("Pole 'instruments' musi być listą")
                return {
                    "status": "error",
                    "message": "Pole 'instruments' musi być listą",
                    "timestamp": datetime.now().isoformat()
                }
            
            if not instruments:
                logger.error("Lista instrumentów nie może być pusta")
                return {
                    "status": "error",
                    "message": "Lista instrumentów nie może być pusta",
                    "timestamp": datetime.now().isoformat()
                }
            
            # Aktualizacja listy instrumentów w rzeczywistym serwerze MT5
            if self.real_mt5_server:
                success = self.real_mt5_server.update_observed_instruments(instruments)
                if success:
                    return {
                        "status": "ok",
                        "message": "Lista instrumentów została zaktualizowana",
                        "instruments": self.real_mt5_server.get_observed_instruments(),
                        "count": len(self.real_mt5_server.get_observed_instruments()),
                        "timestamp": datetime.now().isoformat()
                    }
                else:
                    return {
                        "status": "error",
                        "message": "Nie udało się zaktualizować listy instrumentów",
                        "timestamp": datetime.now().isoformat()
                    }
            else:
                # Jeśli rzeczywisty serwer MT5 nie jest dostępny, zwraca komunikat o błędzie
                return {
                    "status": "error",
                    "message": "Serwer MT5 nie jest dostępny",
                    "timestamp": datetime.now().isoformat()
                }
        except Exception as e:
            logger.error(f"Błąd podczas aktualizacji listy instrumentów: {str(e)}")
            return {
                "status": "error",
                "message": f"Błąd podczas aktualizacji listy instrumentów: {str(e)}",
                "timestamp": datetime.now().isoformat()
            }

    def get_agent_config(self):
        """
        Pobiera aktualną konfigurację agenta handlowego.
        
        Returns:
            Dict: Aktualna konfiguracja agenta
        """
        # Unikamy importu bibliotek na poziomie modułu, żeby uniknąć cyklicznych zależności
        from src.agent_controller import get_agent_controller
        
        logger.info(f"Żądanie pobrania konfiguracji agenta")
        
        try:
            # Pobierz kontroler agenta
            agent_controller = get_agent_controller()
            
            if not agent_controller:
                logger.error("Kontroler agenta nie jest dostępny")
                return {"status": "error", "message": "Kontroler agenta nie jest dostępny"}
            
            # Przygotuj konfigurację do zwrócenia
            config = {
                "mode": agent_controller.mode.value if hasattr(agent_controller, 'mode') else "unknown",
                "risk_limits": agent_controller.config.get("risk_limits", {}),
                "instruments": agent_controller.config.get("instruments", [])
            }
            
            # Mapowanie max_positions_total na max_positions dla UI
            if "max_positions_total" in config["risk_limits"]:
                config["risk_limits"]["max_positions"] = config["risk_limits"].pop("max_positions_total")
            
            return config
        
        except Exception as e:
            logger.error(f"Błąd podczas pobierania konfiguracji agenta: {e}")
            return {"status": "error", "message": str(e)}

@asynccontextmanager
async def create_server(host: str, port: int):
    """
    Asynchroniczny menedżer kontekstu do tworzenia i zarządzania serwerem.
    
    Args:
        host: Adres hosta
        port: Numer portu
        
    Yields:
        MT5Server: Instancja serwera
    """
    server = MT5Server(host, port)
    await server.start()
    try:
        yield server
    finally:
        await server.shutdown()

async def start_server(host: str, port: int) -> MT5Server:
    """
    Uruchomienie serwera HTTP.
    
    Args:
        host: Adres hosta
        port: Numer portu
        
    Returns:
        MT5Server: Instancja serwera
    """
    server = MT5Server(host, port)
    await server.start()
    return server 

# Tworzenie globalnego obiektu aplikacji dla uvicorn
app = FastAPI(title="MT5 API Server")

# Tworzenie instancji serwera MT5 na poziomie modułu
mt5_server_instance = None

@app.on_event("startup")
async def startup_event():
    """Inicjalizacja połączenia z MT5 podczas startu aplikacji."""
    global mt5_server_instance
    
    # Inicjalizacja rzeczywistego MT5Server, jeśli jest dostępny
    if MT5_AVAILABLE and RealMT5Server:
        try:
            mt5_server_instance = RealMT5Server('127.0.0.1', 5555)  # Używamy portu 5555, gdzie działa serwer MT5
            logger.info("Rzeczywisty MT5Server został zainicjalizowany")
        except Exception as e:
            logger.error(f"Błąd podczas inicjalizacji MT5Server: {str(e)}")
            mt5_server_instance = None
    else:
        logger.warning("MT5Server nie jest dostępny. Funkcjonalność będzie ograniczona.")
        mt5_server_instance = None
        
    logger.info(f"Inicjalizacja MT5 API zakończona")

@app.on_event("shutdown")
async def shutdown_event():
    """Zamykanie połączenia z MT5 podczas wyłączania aplikacji."""
    global mt5_server_instance
    # Nie ma potrzeby zamykania MT5Server, gdyż nie uruchamiamy go bezpośrednio
    logger.info("Zamykanie połączenia z MT5 API")

# Endpointy aplikacji FastAPI
@app.get("/")
async def root():
    """Endpoint główny."""
    return {"message": "MT5 API Server działa poprawnie", "timestamp": datetime.now().isoformat()}

@app.get("/monitoring/positions")
async def get_positions():
    """Endpoint do pobierania pozycji z MT5."""
    global shared_memory
    
    try:
        # Użyj danych ze współdzielonej pamięci
        positions_data = shared_memory.get("positions", {})
        
        # Konwersja słownika pozycji do listy
        positions = list(positions_data.values()) if isinstance(positions_data, dict) else []
        
        # Sprawdź, czy mamy jakieś pozycje
        if positions:
            logger.info(f"Zwracam {len(positions)} zapisanych pozycji ze współdzielonej pamięci")
            return {
                "status": "ok",
                "positions": positions,
                "timestamp": datetime.now().isoformat()
            }
        
        # Jeśli nie ma zapisanych pozycji, zwracamy pustą listę zamiast przykładowych danych
        logger.warning("Brak pozycji w pamięci - zwracam pustą listę")
        return {
            "status": "ok",
            "positions": [],
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Błąd podczas pobierania pozycji: {str(e)}")
        return {
            "status": "error",
            "message": f"Błąd podczas pobierania pozycji: {str(e)}",
            "positions": []
        }

# Nowy endpoint do synchronizacji pozycji z MT5
@app.post("/position/sync")
async def sync_positions_with_mt5():
    """Endpoint do synchronizacji pozycji z MT5."""
    global shared_memory, mt5_server_instance
    
    try:
        if not mt5_server_instance or not hasattr(mt5_server_instance, 'real_mt5_server') or not mt5_server_instance.real_mt5_server:
            logger.error("Nie można zsynchronizować pozycji - brak połączenia z MT5")
            return {
                "status": "error",
                "message": "Nie można zsynchronizować pozycji - brak połączenia z MT5",
                "timestamp": datetime.now().isoformat()
            }
        
        # Próba pobrania pozycji z MT5
        positions = []
        try:
            positions = mt5_server_instance.real_mt5_server.get_positions()
            logger.info(f"Pobrano {len(positions)} pozycji z MT5")
        except Exception as e:
            logger.error(f"Błąd podczas pobierania pozycji z MT5: {str(e)}")
            return {
                "status": "error",
                "message": f"Błąd podczas pobierania pozycji z MT5: {str(e)}",
                "timestamp": datetime.now().isoformat()
            }
        
        # Aktualizacja współdzielonej pamięci
        positions_dict = {}
        for pos in positions:
            if 'ticket' in pos:
                positions_dict[pos['ticket']] = pos
        
        shared_memory["positions"] = positions_dict
        shared_memory["last_update"] = datetime.now().isoformat()
        
        logger.info(f"Pamięć pozycji zaktualizowana: {len(positions_dict)} pozycji")
        
        return {
            "status": "ok",
            "message": f"Zsynchronizowano {len(positions_dict)} pozycji z MT5",
            "positions_count": len(positions_dict),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Błąd podczas synchronizacji pozycji: {str(e)}")
        return {
            "status": "error",
            "message": f"Błąd podczas synchronizacji pozycji: {str(e)}",
            "timestamp": datetime.now().isoformat()
        }

@app.get("/monitoring/transactions")
async def get_transactions():
    """Endpoint do pobierania historii transakcji z MT5."""
    global mt5_server_instance
    if not mt5_server_instance or not mt5_server_instance.real_mt5_server:
        logger.error("Serwer MT5 nie jest uruchomiony lub nie jest dostępny")
        return {
            "status": "error", 
            "message": "Serwer MT5 nie jest uruchomiony lub nie jest dostępny",
            "transactions": []
        }
    
    try:
        transactions = mt5_server_instance.real_mt5_server.get_recent_transactions()
        logger.info(f"Pobrano {len(transactions)} transakcji z MT5")
        
        return {
            "status": "ok",
            "transactions": transactions,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Błąd podczas pobierania transakcji z MT5: {str(e)}")
        return {
            "status": "error",
            "message": f"Błąd podczas pobierania transakcji: {str(e)}",
            "transactions": []
        }

@app.get("/monitoring/connections")
async def get_connections():
    """Endpoint do pobierania informacji o połączeniach z MT5."""
    global mt5_server_instance
    if not mt5_server_instance or not mt5_server_instance.real_mt5_server:
        logger.error("Serwer MT5 nie jest uruchomiony lub nie jest dostępny")
        return {
            "status": "error", 
            "message": "Serwer MT5 nie jest uruchomiony lub nie jest dostępny",
            "connections": []
        }
    
    try:
        connections = [
            {
                "id": "EA_connection",
                "type": "MT5 Expert Advisor",
                "status": "connected" if mt5_server_instance.real_mt5_server.is_connected() else "disconnected",
                "last_activity": str(mt5_server_instance.real_mt5_server.last_connection_time)
            }
        ]
        
        return {
            "status": "ok",
            "connections": connections,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Błąd podczas pobierania informacji o połączeniach: {str(e)}")
        return {
            "status": "error",
            "message": f"Błąd podczas pobierania informacji o połączeniach: {str(e)}",
            "connections": []
        }

@app.get("/debug/positions")
async def debug_positions():
    """Endpoint diagnostyczny do pokazania stanu pozycji."""
    global mt5_server_instance, shared_memory
    
    response = {
        "status": "debug",
        "timestamp": datetime.now().isoformat(),
        "mt5_server_exists": mt5_server_instance is not None,
        "real_mt5_server_exists": mt5_server_instance is not None and hasattr(mt5_server_instance, 'real_mt5_server') and mt5_server_instance.real_mt5_server is not None,
        "shared_memory_exists": True,
        "shared_memory_positions": shared_memory.get("positions", {}),
        "shared_memory_positions_count": len(shared_memory.get("positions", {})),
        "shared_memory_last_update": shared_memory.get("last_update", None),
        "positions_list": list(shared_memory.get("positions", {}).values())
    }
    
    return response

@app.get("/mt5/account")
async def get_account_info():
    """Endpoint do pobierania informacji o koncie MT5."""
    global mt5_server_instance
    
    if not mt5_server_instance or not mt5_server_instance.real_mt5_server:
        logger.warning("Serwer MT5 nie jest dostępny, zwracam przykładowe dane o koncie")
        example_account = {
            "login": 12345678,
            "balance": 10000,
            "equity": 10250,
            "margin": 2000,
            "free_margin": 8250,
            "margin_level": 512.5,
            "leverage": 100,
            "currency": "USD"
        }
        
        return {
            "status": "ok",
            "account_info": example_account,
            "timestamp": datetime.now().isoformat()
        }
    
    try:
        account_info = mt5_server_instance.real_mt5_server.get_account_info()
        logger.info("Pobrano informacje o koncie z MT5")
        
        return {
            "status": "ok",
            "account_info": account_info,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Błąd podczas pobierania informacji o koncie: {str(e)}")
        example_account = {
            "login": 12345678,
            "balance": 10000,
            "equity": 10250,
            "margin": 2000,
            "free_margin": 8250,
            "margin_level": 512.5,
            "leverage": 100,
            "currency": "USD"
        }
        
        return {
            "status": "ok",
            "account_info": example_account,
            "timestamp": datetime.now().isoformat()
        }

if __name__ == "__main__":
    import argparse
    import sys
    
    # Upewniamy się, że katalog logs istnieje
    os.makedirs('logs', exist_ok=True)
    
    # Parsowanie argumentów wiersza poleceń
    parser = argparse.ArgumentParser(description='Uruchom serwer API MT5')
    parser.add_argument('--host', type=str, default='127.0.0.1', help='Adres hosta (domyślnie: 127.0.0.1)')
    parser.add_argument('--port', type=int, default=8000, help='Numer portu (domyślnie: 8000)')
    args = parser.parse_args()
    
    # Konfiguracja logowania
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('logs/api_server.log')
        ]
    )
    
    # Uruchomienie serwera FastAPI
    logger.info(f"Uruchamianie serwera API na {args.host}:{args.port}")
    uvicorn.run(
        "src.mt5_bridge.server:app", 
        host=args.host, 
        port=args.port,
        log_level="info"
    ) 