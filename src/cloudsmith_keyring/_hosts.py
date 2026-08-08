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
"""Host parsing for keyring service strings.

Everything here is pure and side-effect free: no subprocess calls, no
environment reads. Cloudsmith host gating itself is decided elsewhere,
against the authoritative host list returned by the ``cloudsmith`` CLI
(see ``_cli.fetch_cloudsmith_domains`` and ``backend.py``); this module
only extracts a hostname to check against that list.
"""

from __future__ import annotations

from urllib.parse import urlsplit


def parse_host(service_url):
    """Extract and lowercase the hostname from a keyring service string.

    Accepts full URLs (with scheme, port, userinfo, and path) as well as a
    bare hostname. Returns None if no hostname can be determined.
    """
    if not service_url:
        return None

    candidate = service_url
    if "://" not in candidate:
        candidate = "//" + candidate

    try:
        parsed = urlsplit(candidate)
        host = parsed.hostname
    except ValueError:
        return None

    if not host:
        return None

    return host.lower()
