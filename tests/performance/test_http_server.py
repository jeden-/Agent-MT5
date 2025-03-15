"""
Testy wydajnościowe serwera HTTP.
"""

import pytest
import asyncio
import aiohttp
import time
import logging
from mt5_bridge.server import create_server

logger = logging.getLogger(__name__)

@pytest.fixture
async def server():
    """Fixture dostarczający serwer HTTP do testów."""
    ports = range(8080, 8090)
    last_error = None
    
    for port in ports:
        try:
            async with create_server("localhost", port) as server:
                yield server
                break
        except OSError as e:
            last_error = e
            logger.warning(f"Port {port} jest zajęty, próbuję następny...")
            continue
    else:
        raise RuntimeError(f"Nie znaleziono wolnego portu w zakresie {ports}. Ostatni błąd: {last_error}")

async def test_server_response_time(server):
    """Test czasu odpowiedzi serwera."""
    url = f"http://{server.host}:{server.port}/ping"
    async with aiohttp.ClientSession() as session:
        start_time = time.time()
        for _ in range(100):
            try:
                async with session.get(url, timeout=1) as response:
                    assert response.status == 200
                    text = await response.text()
                    assert text == "pong"
            except asyncio.TimeoutError:
                pytest.fail("Serwer nie odpowiedział w czasie")
            except aiohttp.ClientError as e:
                pytest.fail(f"Błąd połączenia: {e}")
        end_time = time.time()
        
    total_time = end_time - start_time
    requests_per_second = 100 / total_time
    logger.info(f"Średnia liczba żądań na sekundę: {requests_per_second:.2f}")
    assert requests_per_second >= 50, f"Za mała przepustowość: {requests_per_second:.2f} żądań/s"

async def test_server_concurrent_requests(server):
    """Test obsługi współbieżnych żądań."""
    url = f"http://{server.host}:{server.port}/ping"
    async with aiohttp.ClientSession() as session:
        tasks = []
        for _ in range(100):
            tasks.append(session.get(url))
        
        start_time = time.time()
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        end_time = time.time()
        
        successful = sum(1 for r in responses if isinstance(r, aiohttp.ClientResponse) and r.status == 200)
        success_rate = (successful / len(responses)) * 100
        
        total_time = end_time - start_time
        requests_per_second = len(responses) / total_time
        
        logger.info(f"Współczynnik sukcesu: {success_rate:.2f}%")
        logger.info(f"Żądania na sekundę: {requests_per_second:.2f}")
        
        assert success_rate >= 95, f"Za niski współczynnik sukcesu: {success_rate:.2f}%"
        assert requests_per_second >= 50, f"Za mała przepustowość: {requests_per_second:.2f} żądań/s"

async def test_server_load_distribution(server):
    """Test rozkładu obciążenia serwera."""
    url = f"http://{server.host}:{server.port}/ping"
    response_times = []
    
    async with aiohttp.ClientSession() as session:
        for _ in range(100):
            start_time = time.time()
            try:
                async with session.get(url, timeout=1) as response:
                    await response.text()
                    response_times.append(time.time() - start_time)
            except (asyncio.TimeoutError, aiohttp.ClientError) as e:
                logger.error(f"Błąd podczas żądania: {e}")
                response_times.append(float('inf'))
            await asyncio.sleep(0.01)  # Małe opóźnienie między żądaniami
    
    # Analiza rozkładu czasów odpowiedzi
    avg_time = sum(t for t in response_times if t != float('inf')) / len(response_times)
    max_time = max(t for t in response_times if t != float('inf'))
    min_time = min(t for t in response_times if t != float('inf'))
    
    logger.info(f"Średni czas odpowiedzi: {avg_time:.3f}s")
    logger.info(f"Maksymalny czas odpowiedzi: {max_time:.3f}s")
    logger.info(f"Minimalny czas odpowiedzi: {min_time:.3f}s")
    
    # Sprawdzenie czy czasy odpowiedzi są w akceptowalnym zakresie
    assert avg_time < 0.1, f"Średni czas odpowiedzi za długi: {avg_time:.3f}s"
    assert max_time < 0.5, f"Maksymalny czas odpowiedzi za długi: {max_time:.3f}s" 