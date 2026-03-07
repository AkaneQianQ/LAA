"""
FrameCache Module

Provides TTL-based frame caching to reduce DXCam screen capture overhead.
Thread-safe implementation with automatic invalidation and statistics tracking.
"""

import threading
import time
from typing import Optional, Dict, Any

import numpy as np


class FrameCache:
    """
    Thread-safe frame cache with TTL-based invalidation.

    Reduces screen capture calls by caching frames for a configurable
    time period. Multiple template matches within the TTL window can
    reuse the same frame, significantly improving performance.

    Attributes:
        ttl_ms: Time-to-live in milliseconds for cached frames
        _cache: The cached frame (None if expired or not set)
        _timestamp: Monotonic timestamp when frame was cached
        _lock: Threading lock for concurrent access safety
        _capture_count: Number of fresh captures (cache misses)
        _cache_hit_count: Number of cache hits
    """

    def __init__(self, ttl_ms: float = 150.0):
        """
        Initialize the frame cache.

        Args:
            ttl_ms: Time-to-live in milliseconds (default: 150ms)
        """
        self.ttl_ms = ttl_ms
        self._cache: Optional[np.ndarray] = None
        self._timestamp: float = 0.0
        self._lock = threading.Lock()
        self._capture_count: int = 0
        self._cache_hit_count: int = 0

    def get(self) -> Optional[np.ndarray]:
        """
        Get cached frame if not expired.

        Thread-safe. Returns a copy of the cached frame to prevent
        external mutation. Returns None if cache is expired or empty.

        Returns:
            Cached frame copy, or None if expired/not available
        """
        with self._lock:
            if self._cache is None:
                return None

            elapsed_ms = (time.monotonic() - self._timestamp) * 1000
            if elapsed_ms > self.ttl_ms:
                self._cache = None
                return None

            self._cache_hit_count += 1
            return self._cache.copy()

    def set(self, frame: np.ndarray) -> None:
        """
        Store a frame in the cache.

        Thread-safe. Stores a copy of the frame to prevent external
        mutation. Updates the timestamp for TTL calculation.

        Args:
            frame: The frame to cache (BGR numpy array)
        """
        with self._lock:
            self._cache = frame.copy()
            self._timestamp = time.monotonic()
            self._capture_count += 1

    def invalidate(self) -> None:
        """
        Force clear the cache.

        Thread-safe. Immediately invalidates the cache regardless of TTL.
        Useful for action-after scenarios where a fresh frame is required.
        """
        with self._lock:
            self._cache = None
            self._timestamp = 0.0

    @property
    def cache_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dictionary with:
                - captures: Number of fresh captures (cache misses)
                - hits: Number of cache hits
                - hit_rate: Percentage of hits vs total accesses
                - reduction_pct: Estimated capture reduction percentage
        """
        with self._lock:
            total_accesses = self._capture_count + self._cache_hit_count
            hit_rate = 0.0
            reduction_pct = 0.0

            if total_accesses > 0:
                hit_rate = round((self._cache_hit_count / total_accesses) * 100, 2)
                reduction_pct = round((self._cache_hit_count / total_accesses) * 100, 2)

            return {
                'captures': self._capture_count,
                'hits': self._cache_hit_count,
                'hit_rate': hit_rate,
                'reduction_pct': reduction_pct
            }
