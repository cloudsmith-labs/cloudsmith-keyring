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
"""The keyring backend itself.

Importing this module is what registers ``CloudsmithKeyringBackend`` with
keyring (via the ``keyring.backends`` entry point declared in
pyproject.toml): keyring's ``KeyringBackendMeta`` metaclass registers every
concrete subclass as a side effect of class creation, so no explicit
``initialize()`` call is required.
"""

from __future__ import annotations

import logging
import time

import keyring.backend
import keyring.credentials

from ._cache import TTLCache
from ._cli import (
    fetch_cloudsmith_domains,
    fetch_generic_credential,
    find_cloudsmith_binary,
)
from ._env import positive_float_from_env
from ._hosts import parse_host

logger = logging.getLogger(__name__)

_DEFAULT_TOKEN_TTL_SECONDS = 300.0


def _resolve_token_ttl_seconds():
    return positive_float_from_env("CLOUDSMITH_KEYRING_TTL", _DEFAULT_TOKEN_TTL_SECONDS)


class CloudsmithKeyringBackend(keyring.backend.KeyringBackend):
    """Resolves Cloudsmith credentials by shelling out to the ``cloudsmith`` CLI.

    ``priority`` is set to 9.9, which places this backend ahead of the OS
    keychain in keyring's chainer. A high priority is safe here specifically
    because every code path below returns None for any host that is not a
    confirmed Cloudsmith host: this backend can never hand a token to the
    wrong service, so letting it go first never risks masking or leaking
    another backend's credential.
    """

    priority = 9.9

    def __init__(self, clock=time.monotonic):
        super().__init__()
        self._token_cache = TTLCache(_resolve_token_ttl_seconds(), clock=clock)
        self._cloudsmith_hosts = None

    def get_credential(self, service, username):
        del username  # a Cloudsmith token is organisation-wide
        return self._resolve_credential(service)

    def get_password(self, service, username):
        del username
        credential = self._resolve_credential(service)
        if credential is None:
            return None
        return credential.password

    # NotImplementedError specifically, not PasswordSetError/PasswordDeleteError:
    # keyring's ChainerBackend wraps write calls in `except NotImplementedError`
    # and nothing else, so any other exception aborts the whole chain. Since this
    # backend runs ahead of the OS keychain, raising anything else would stop a
    # user storing a credential for *any* service, Cloudsmith or not.
    def set_password(self, service, username, password):
        del service, username, password
        raise NotImplementedError("cloudsmith-keyring is read-only")

    def delete_password(self, service, username):
        del service, username
        raise NotImplementedError("cloudsmith-keyring is read-only")

    def _resolve_credential(self, service):
        host = parse_host(service)
        if host is None:
            return None
        if not self._is_cloudsmith_host(host):
            return None

        cached_credential = self._token_cache.get(host)
        if cached_credential is not None:
            username, password = cached_credential
            return keyring.credentials.SimpleCredential(username, password)

        binary_path = find_cloudsmith_binary()
        if binary_path is None:
            return None

        credential_pair = fetch_generic_credential(binary_path)
        if credential_pair is None:
            return None

        self._token_cache.set(host, credential_pair)
        username, password = credential_pair
        return keyring.credentials.SimpleCredential(username, password)

    def _is_cloudsmith_host(self, host):
        return host in self._get_cloudsmith_hosts()

    def _get_cloudsmith_hosts(self):
        """The hosts the CLI confirms, cached for the process lifetime.

        Only an *answered* lookup is cached. A missing binary or a failed
        lookup returns an empty set without caching it, so the next call
        tries again: keyring keeps one backend instance per process, and
        memoising a transient failure would disable authentication for the
        rest of a pip run — and permanently in a long-lived build worker.
        An empty set from a lookup that did answer (an unsupported contract
        version) is a real answer and is cached like any other.
        """
        if self._cloudsmith_hosts is not None:
            return self._cloudsmith_hosts

        binary_path = find_cloudsmith_binary()
        if binary_path is None:
            return frozenset()

        usable_hosts = fetch_cloudsmith_domains(binary_path)
        if usable_hosts is None:
            return frozenset()

        self._cloudsmith_hosts = frozenset(usable_hosts)
        return self._cloudsmith_hosts
