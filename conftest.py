"""Pytest configuration for Gardena Smart System Integration tests."""

import sys
from pathlib import Path

import pytest
import pytest_asyncio

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


@pytest_asyncio.fixture(autouse=True)
async def enable_event_loop_debug():
    """Override the HA plugin's async fixture with a properly decorated one."""
    pass


# Configure Home Assistant test fixtures
def pytest_configure(config):
    """Configure pytest for Home Assistant testing."""
    config.addinivalue_line(
        "markers", "asyncio: mark test as async"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as integration test"
    )
    config.addinivalue_line(
        "markers", "unit: mark test as unit test"
    ) 