"""
Pytest configuration and fixtures for performance tests.

Provides shared fixtures for frame cache and vision engine testing.
"""

import pytest
import numpy as np
from typing import Generator
import sys

sys.path.insert(0, 'C:\\Users\\Akane\\FerrumProject\\LostarkGuildDonationBot')


@pytest.fixture
def sample_frame() -> np.ndarray:
    """Create a dummy 2560x1440 BGR frame for testing."""
    return np.ones((1440, 2560, 3), dtype=np.uint8) * 128


@pytest.fixture
def frame_cache() -> Generator:
    """Create a FrameCache with short TTL for testing."""
    from core.frame_cache import FrameCache
    cache = FrameCache(ttl_ms=50.0)
    yield cache


@pytest.fixture
def vision_engine_with_cache() -> Generator:
    """Create a VisionEngine with FrameCache for testing."""
    from core.vision_engine import VisionEngine
    from core.frame_cache import FrameCache

    cache = FrameCache(ttl_ms=50.0)
    engine = VisionEngine(frame_cache=cache)
    yield engine
