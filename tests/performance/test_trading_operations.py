"""
Testy wydajnościowe dla operacji handlowych.
Mierzą wydajność systemu przy dużej liczbie pozycji i operacji handlowych.
"""

import pytest
import time
import asyncio
from datetime import datetime, timedelta
from src.trading_integration import TradingIntegration
from src.position_management.position_manager import PositionManager
from src.utils.config import load_config

class TestTradingOperationsPerformance:
    @pytest.fixture(scope="class")
    def trading_integration(self):
        """Inicjalizuje integrację z systemem tradingowym."""
        config = load_config()
        return TradingIntegration(config)

    @pytest.fixture(scope="class")
    def position_manager(self):
        """Inicjalizuje menedżera pozycji."""
        config = load_config()
        return PositionManager(config)

    @pytest.mark.asyncio
    async def test_position_creation_speed(self, trading_integration):
        """Test szybkości tworzenia nowych pozycji."""
        num_positions = 100
        symbol = "EURUSD"
        
        start_time = time.time()
        tasks = []
        
        for i in range(num_positions):
            tasks.append(trading_integration.open_position(
                symbol=symbol,
                order_type="BUY",
                volume=0.01,
                price=1.2000,
                stop_loss=1.1950,
                take_profit=1.2050
            ))
        
        results = await asyncio.gather(*tasks)
        total_time = time.time() - start_time
        
        # Sprawdź wyniki
        success_count = sum(1 for r in results if r is not None)
        operations_per_second = num_positions / max(total_time, 0.001)  # Unikamy dzielenia przez zero
        
        print(f"Successful operations: {success_count}/{num_positions}")
        print(f"Operations per second: {operations_per_second:.2f}")
        
        assert success_count >= num_positions * 0.95  # 95% sukcesu
        assert operations_per_second > 10  # Minimum 10 operacji na sekundę

    @pytest.mark.asyncio
    async def test_position_update_performance(self, position_manager):
        """Test wydajności aktualizacji wielu pozycji jednocześnie."""
        num_positions = 1000
        positions = []
        
        # Przygotuj pozycje testowe
        for i in range(num_positions):
            position = {
                "ticket": i,
                "symbol": "EURUSD",
                "type": "BUY",
                "volume": 0.01,
                "open_price": 1.2000,
                "current_price": 1.2010,
                "profit": 1.0,
                "swap": 0.0,
                "open_time": datetime.now() - timedelta(hours=1)
            }
            positions.append(position)
        
        # Testuj wydajność aktualizacji
        start_time = time.time()
        await position_manager.update_positions(positions)
        total_time = time.time() - start_time
        
        updates_per_second = num_positions / max(total_time, 0.001)  # Unikamy dzielenia przez zero
        print(f"Position updates per second: {updates_per_second:.2f}")
        assert updates_per_second > 100  # Minimum 100 aktualizacji na sekundę

    @pytest.mark.asyncio
    async def test_market_data_processing(self, trading_integration):
        """Test wydajności przetwarzania danych rynkowych."""
        symbols = ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCHF"]
        timeframes = ["M1", "M5", "M15", "H1"]
        num_candles = 1000
        
        start_time = time.time()
        tasks = []
        
        for symbol in symbols:
            for timeframe in timeframes:
                tasks.append(trading_integration.get_historical_data(
                    symbol=symbol,
                    timeframe=timeframe,
                    num_candles=num_candles
                ))
        
        results = await asyncio.gather(*tasks)
        total_time = time.time() - start_time
        
        total_candles = len(symbols) * len(timeframes) * num_candles
        candles_per_second = total_candles / max(total_time, 0.001)  # Unikamy dzielenia przez zero
        
        print(f"Processed {total_candles} candles in {total_time:.2f} seconds")
        print(f"Candles per second: {candles_per_second:.2f}")
        
        assert candles_per_second > 10000  # Minimum 10,000 świec na sekundę 