"""Pytest configuration for Gardena Smart System Integration tests."""

import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Import pytest-homeassistant-custom-component fixtures
pytest_plugins = ["pytest_homeassistant_custom_component"]

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