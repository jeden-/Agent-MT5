"""
Konfiguracja testów wydajnościowych.
"""

import pytest
import asyncio
import logging
from src.utils.config import load_config
from src.utils.logger import setup_logger

@pytest.fixture(scope="session")
async def event_loop_policy():
    """Konfiguruje politykę pętli zdarzeń."""
    if asyncio.get_event_loop_policy().__class__.__name__ == 'WindowsProactorEventLoopPolicy':
        # Użyj WindowsSelectorEventLoopPolicy na Windows
        policy = asyncio.WindowsSelectorEventLoopPolicy()
        asyncio.set_event_loop_policy(policy)
    return asyncio.get_event_loop_policy()

@pytest.fixture(scope="session")
def event_loop(event_loop_policy):
    """Tworzy pętlę zdarzeń dla testów asynchronicznych."""
    loop = event_loop_policy.new_event_loop()
    yield loop
    if loop.is_running():
        loop.stop()
    if not loop.is_closed():
        loop.close()

@pytest.fixture(scope="session")
def config():
    """Ładuje konfigurację testową."""
    return load_config("config/test_config.yml")

@pytest.fixture(scope="session")
def logger():
    """Konfiguruje logger dla testów."""
    return setup_logger("performance_tests", level=logging.INFO)

def pytest_configure(config):
    """Konfiguruje środowisko testowe."""
    config.addinivalue_line("markers", "performance: mark test as a performance test")

def pytest_addoption(parser):
    """Dodaje opcje wiersza poleceń dla testów wydajnościowych."""
    parser.addoption(
        "--performance",
        action="store_true",
        default=False,
        help="run performance tests"
    )
    parser.addoption(
        "--stress",
        action="store_true",
        default=False,
        help="run stress tests"
    )

def pytest_collection_modifyitems(config, items):
    """Modyfikuje kolekcję testów na podstawie opcji wiersza poleceń."""
    if not config.getoption("--performance"):
        skip_perf = pytest.mark.skip(reason="need --performance option to run")
        for item in items:
            if "performance" in item.keywords:
                item.add_marker(skip_perf)

    if not config.getoption("--stress"):
        skip_stress = pytest.mark.skip(reason="need --stress option to run")
        for item in items:
            if "stress" in item.keywords:
                item.add_marker(skip_stress) 