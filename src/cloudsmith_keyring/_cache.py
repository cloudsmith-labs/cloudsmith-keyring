# Copyright 2026 Cloudsmith Ltd
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""A minimal in-process TTL cache, keyed by string.

The credential-helper contract carries no ``expires_at``, so callers must
rely on a short fixed TTL rather than expiry-aware caching. A monotonic
clock is used (injectable for tests) so the cache is immune to wall-clock
adjustments.
"""

from __future__ import annotations

import threading
import time


class TTLCache:
    """Thread-safe cache mapping keys to values, each expiring after a TTL."""

    def __init__(self, ttl_seconds, clock=time.monotonic):
        self._ttl_seconds = ttl_seconds
        self._clock = clock
        self._lock = threading.Lock()
        self._entries = {}

    def get(self, key):
        with self._lock:
            entry = self._entries.get(key)
            if entry is None:
                return None
            value, expires_at = entry
            if self._clock() >= expires_at:
                del self._entries[key]
                return None
            return value

    def set(self, key, value):
        with self._lock:
            self._entries[key] = (value, self._clock() + self._ttl_seconds)
