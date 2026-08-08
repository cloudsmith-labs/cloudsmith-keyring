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
"""Reading numeric settings out of the environment, safely.

Both of this package's tunables are durations, and both are read from
user-controlled environment variables. ``float()`` alone is not enough of
a filter: it happily accepts ``nan`` and ``inf``, which then blow up far
away from here — ``subprocess.run(timeout=nan)`` raises ``ValueError``
from inside ``selectors``, and ``inf`` raises ``OverflowError``. Neither
is ``TimeoutExpired`` or ``OSError``, so they escape the callers' handlers
and abort pip with a traceback, breaking the package's central promise
that it degrades to None rather than raising.
"""

from __future__ import annotations

import logging
import math
import os

logger = logging.getLogger(__name__)


def positive_float_from_env(name, default):
    """Return ``os.environ[name]`` as a positive, finite float, else `default`.

    A non-positive value is rejected rather than honoured: zero or a
    negative duration is never what the user meant (it would make every
    call time out immediately, or expire every cache entry on write), and
    silently doing nothing is worse than using the documented default.
    """
    raw_value = os.environ.get(name)
    if not raw_value:
        return default

    try:
        value = float(raw_value)
    except ValueError:
        logger.debug("%s is not a number; using the default of %s", name, default)
        return default

    if not math.isfinite(value) or value <= 0:
        logger.debug("%s must be a positive, finite number; using the default of %s", name, default)
        return default

    return value
