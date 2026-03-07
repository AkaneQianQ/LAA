"""
FrameCache tests - Performance optimization for screen capture.

Tests the TTL-based frame caching system to reduce DXCam overhead.
"""

import time
import threading
import numpy as np
import pytest
from typing import Generator

# Import the module under test
import sys
sys.path.insert(0, 'C:\\Users\\Akane\\FerrumProject\\LostarkGuildDonationBot')


class TestFrameCache:
    """Tests for FrameCache class with TTL invalidation."""

    def test_cache_stores_and_retrieves_frame_within_ttl(self):
        """Test: Cache stores and retrieves frame within TTL."""
        from core.frame_cache import FrameCache

        cache = FrameCache(ttl_ms=100.0)
        frame = np.ones((1440, 2560, 3), dtype=np.uint8) * 128

        cache.set(frame)
        retrieved = cache.get()

        assert retrieved is not None
        assert np.array_equal(retrieved, frame)

    def test_cache_returns_none_after_ttl_expires(self):
        """Test: Cache returns None after TTL expires."""
        from core.frame_cache import FrameCache

        cache = FrameCache(ttl_ms=50.0)  # Short TTL for testing
        frame = np.ones((1440, 2560, 3), dtype=np.uint8) * 128

        cache.set(frame)

        # Should be available immediately
        assert cache.get() is not None

        # Wait for TTL to expire
        time.sleep(0.06)  # 60ms > 50ms TTL

        # Should be expired now
        assert cache.get() is None

    def test_cache_returns_copy_to_prevent_mutation(self):
        """Test: Cache returns copy to prevent external mutation."""
        from core.frame_cache import FrameCache

        cache = FrameCache(ttl_ms=100.0)
        original = np.ones((1440, 2560, 3), dtype=np.uint8) * 128

        cache.set(original)
        retrieved = cache.get()

        # Modify the retrieved frame
        retrieved[0, 0, 0] = 255

        # Get again - should still be original value
        retrieved2 = cache.get()
        assert retrieved2[0, 0, 0] == 128

    def test_thread_safe_concurrent_access(self):
        """Test: Thread-safe concurrent access."""
        from core.frame_cache import FrameCache

        cache = FrameCache(ttl_ms=500.0)
        errors = []
        results = {'gets': 0, 'sets': 0}

        def setter():
            for i in range(50):
                frame = np.ones((1440, 2560, 3), dtype=np.uint8) * i
                try:
                    cache.set(frame)
                    results['sets'] += 1
                except Exception as e:
                    errors.append(f"set error: {e}")

        def getter():
            for _ in range(50):
                try:
                    result = cache.get()
                    if result is not None:
                        results['gets'] += 1
                except Exception as e:
                    errors.append(f"get error: {e}")

        threads = []
        for _ in range(3):
            threads.append(threading.Thread(target=setter))
            threads.append(threading.Thread(target=getter))

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0, f"Thread errors: {errors}"
        assert results['sets'] == 150

    def test_cache_stats_track_hits_and_misses(self):
        """Test: Cache stats track hits/misses."""
        from core.frame_cache import FrameCache

        cache = FrameCache(ttl_ms=100.0)
        frame = np.ones((1440, 2560, 3), dtype=np.uint8)

        # Initial state - no captures or hits
        stats = cache.cache_stats
        assert stats['captures'] == 0
        assert stats['hits'] == 0
        assert stats['hit_rate'] == 0.0

        # Set a frame (counts as capture)
        cache.set(frame)
        stats = cache.cache_stats
        assert stats['captures'] == 1
        assert stats['hits'] == 0

        # Get the frame (counts as hit)
        cache.get()
        stats = cache.cache_stats
        assert stats['captures'] == 1
        assert stats['hits'] == 1
        assert stats['hit_rate'] == 50.0  # 1 hit / (1 capture + 1 hit)

        # Another get (another hit)
        cache.get()
        stats = cache.cache_stats
        assert stats['hits'] == 2
        assert stats['hit_rate'] == 66.67  # 2 hits / (1 capture + 2 hits)

    def test_explicit_invalidate_clears_cache(self):
        """Test: Explicit invalidate() clears cache."""
        from core.frame_cache import FrameCache

        cache = FrameCache(ttl_ms=500.0)
        frame = np.ones((1440, 2560, 3), dtype=np.uint8)

        cache.set(frame)
        assert cache.get() is not None

        cache.invalidate()
        assert cache.get() is None


class TestVisionEngineIntegration:
    """Tests for VisionEngine FrameCache integration."""

    def test_vision_engine_accepts_optional_frame_cache(self):
        """Test: VisionEngine accepts optional frame_cache parameter."""
        from core.vision_engine import VisionEngine
        from core.frame_cache import FrameCache

        # Without cache
        engine_no_cache = VisionEngine()
        assert engine_no_cache._frame_cache is None

        # With cache
        cache = FrameCache(ttl_ms=100.0)
        engine_with_cache = VisionEngine(frame_cache=cache)
        assert engine_with_cache._frame_cache is cache

    def test_get_screenshot_uses_cache_when_available(self, monkeypatch):
        """Test: get_screenshot() uses cache when available."""
        from core.vision_engine import VisionEngine
        from core.frame_cache import FrameCache

        cache = FrameCache(ttl_ms=100.0)
        engine = VisionEngine(frame_cache=cache)

        # Mock DXCam capture
        mock_frame = np.ones((1440, 2560, 3), dtype=np.uint8) * 64
        capture_calls = []

        def mock_capture():
            capture_calls.append(1)
            return mock_frame

        monkeypatch.setattr(engine, '_capture_screen', mock_capture)

        # First call should capture
        result1 = engine.get_screenshot()
        assert len(capture_calls) == 1
        assert np.array_equal(result1, mock_frame)

        # Second call should use cache
        result2 = engine.get_screenshot()
        assert len(capture_calls) == 1  # No new capture
        assert np.array_equal(result2, mock_frame)

    def test_get_screenshot_force_fresh_bypasses_cache(self, monkeypatch):
        """Test: get_screenshot(force_fresh=True) bypasses cache."""
        from core.vision_engine import VisionEngine
        from core.frame_cache import FrameCache

        cache = FrameCache(ttl_ms=100.0)
        engine = VisionEngine(frame_cache=cache)

        mock_frame = np.ones((1440, 2560, 3), dtype=np.uint8) * 64
        capture_calls = []

        def mock_capture():
            capture_calls.append(1)
            return mock_frame

        monkeypatch.setattr(engine, '_capture_screen', mock_capture)

        # First call
        engine.get_screenshot()
        assert len(capture_calls) == 1

        # Force fresh should bypass cache
        engine.get_screenshot(force_fresh=True)
        assert len(capture_calls) == 2

    def test_invalidate_cache_delegates_to_frame_cache(self):
        """Test: invalidate_cache() delegates to frame_cache."""
        from core.vision_engine import VisionEngine
        from core.frame_cache import FrameCache

        cache = FrameCache(ttl_ms=100.0)
        engine = VisionEngine(frame_cache=cache)

        frame = np.ones((1440, 2560, 3), dtype=np.uint8)
        cache.set(frame)
        assert cache.get() is not None

        engine.invalidate_cache()
        assert cache.get() is None

    def test_invalidate_cache_no_op_without_cache(self):
        """Test: invalidate_cache() no-op if no cache configured."""
        from core.vision_engine import VisionEngine

        engine = VisionEngine()  # No cache
        # Should not raise
        engine.invalidate_cache()

    def test_cache_stats_accessible_through_vision_engine(self):
        """Test: Cache stats accessible through VisionEngine."""
        from core.vision_engine import VisionEngine
        from core.frame_cache import FrameCache

        cache = FrameCache(ttl_ms=100.0)
        engine = VisionEngine(frame_cache=cache)

        # Stats should be available
        stats = engine.cache_stats
        assert stats is not None
        assert 'captures' in stats
        assert 'hits' in stats
        assert 'hit_rate' in stats
        assert 'reduction_pct' in stats

    def test_vision_engine_without_cache_returns_none_stats(self):
        """Test: VisionEngine without cache returns None for stats."""
        from core.vision_engine import VisionEngine

        engine = VisionEngine()
        assert engine.cache_stats is None


class TestPerformanceBenchmark:
    """Performance benchmarks for frame caching."""

    def test_cache_hit_rate_above_50_percent(self, monkeypatch):
        """Test: Cache hit rate > 50% with repeated accesses."""
        from core.vision_engine import VisionEngine
        from core.frame_cache import FrameCache

        cache = FrameCache(ttl_ms=100.0)
        engine = VisionEngine(frame_cache=cache)

        mock_frame = np.ones((1440, 2560, 3), dtype=np.uint8)
        monkeypatch.setattr(engine, '_capture_screen', lambda: mock_frame)

        # 10 accesses, only first should capture
        for _ in range(10):
            engine.get_screenshot()

        stats = engine.cache_stats
        assert stats['hit_rate'] >= 50.0, f"Hit rate {stats['hit_rate']}% below 50%"
        assert stats['reduction_pct'] >= 50.0, f"Reduction {stats['reduction_pct']}% below 50%"
