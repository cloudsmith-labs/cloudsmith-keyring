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
"""Binary discovery and subprocess invocation of the ``cloudsmith`` CLI.

Every failure mode here (missing binary, non-zero exit, timeout, malformed
output) degrades to ``None`` rather than raising, so callers never need to
wrap these functions in their own try/except to stay silent.
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor

from ._env import positive_float_from_env

logger = logging.getLogger(__name__)

_DEFAULT_TIMEOUT_SECONDS = 30.0
_CONTRACT_VERSION = 1
_DOMAINS_CONTRACT_VERSION = 1

_UPLOAD_DOMAINS_ARGS = ["domains", "list", "--format", "python", "--domain-type", "native_api"]
_DOWNLOAD_DOMAINS_ARGS = ["domains", "list", "--domain-type", "download"]


def _which_excluding_cwd(name):
    """``shutil.which``, but never resolving to the current directory.

    On Windows, ``shutil.which`` prepends ``os.curdir`` to the search path
    (unless ``NoDefaultCurrentDirectoryInExePath`` is set, which it is not
    by default), and ``.bat``/``.cmd`` are executable extensions. Without
    this guard, running ``pip install`` inside an untrusted checkout that
    happens to contain ``cloudsmith.bat`` would execute that file — and,
    since the same binary answers ``domains list``, let it declare any host
    trusted and then collect a credential for it.

    ``PATH`` entries that resolve to the current directory (``.``, ``""``)
    are dropped for the same reason on every platform.
    """
    search_path = os.environ.get("PATH", os.defpath)
    current_directory = os.path.abspath(os.curdir)
    safe_entries = [
        entry
        for entry in search_path.split(os.pathsep)
        if entry and os.path.abspath(entry) != current_directory
    ]
    if not safe_entries:
        return None
    return shutil.which(name, path=os.pathsep.join(safe_entries))


def find_cloudsmith_binary():
    """Locate the cloudsmith CLI executable, or return None if unavailable.

    An explicit ``CLOUDSMITH_CLI_PATH`` is honoured as given — the user
    naming a binary is a deliberate act — but PATH lookup deliberately
    excludes the current directory (see :func:`_which_excluding_cwd`).
    """
    override = os.environ.get("CLOUDSMITH_CLI_PATH")
    if override:
        return shutil.which(override)

    candidate_names = ["cloudsmith"]
    if sys.platform == "win32":
        candidate_names.append("cloudsmith.exe")

    for name in candidate_names:
        found = _which_excluding_cwd(name)
        if found:
            return found
    return None


def _resolve_timeout_seconds():
    return positive_float_from_env("CLOUDSMITH_KEYRING_TIMEOUT", _DEFAULT_TIMEOUT_SECONDS)


def run_cloudsmith_json_command(binary_path, args, input_text=None):
    """Run the cloudsmith CLI with args, returning parsed JSON stdout or None.

    ``input_text`` is used only by stdin-based credential helpers. Keeping it
    optional preserves the no-stdin behaviour of the JSON commands and makes
    it explicit that every subprocess is still invoked without a shell.
    """
    command = [binary_path] + list(args)
    timeout_seconds = _resolve_timeout_seconds()
    run_kwargs = {
        "capture_output": True,
        "text": True,
        "timeout": timeout_seconds,
        "shell": False,
    }
    if input_text is not None:
        run_kwargs["input"] = input_text

    try:
        result = subprocess.run(command, **run_kwargs)
    except subprocess.TimeoutExpired:
        logger.debug("cloudsmith CLI timed out after %s seconds", timeout_seconds)
        return None
    except OSError:
        logger.debug("cloudsmith CLI could not be executed")
        return None

    if result.returncode != 0:
        logger.debug("cloudsmith CLI exited with status %s", result.returncode)
        return None

    stdout = result.stdout
    if not stdout or not stdout.strip():
        logger.debug("cloudsmith CLI produced no output")
        return None

    try:
        return json.loads(stdout)
    except json.JSONDecodeError:
        logger.debug("cloudsmith CLI produced output that could not be parsed as JSON")
        return None


def fetch_generic_credential(binary_path):
    """Run ``credential-helper generic`` and return a (username, password) pair or None."""
    payload = run_cloudsmith_json_command(binary_path, ["credential-helper", "generic"])
    if not isinstance(payload, dict):
        return None
    if payload.get("version") != _CONTRACT_VERSION:
        return None

    username = payload.get("username")
    password = payload.get("password")
    if not isinstance(username, str) or not username:
        return None
    if not isinstance(password, str) or not password:
        return None
    return username, password


def fetch_docker_credential(binary_path, host):
    """Return a credential from the released Docker helper, or ``None``.

    Current public Cloudsmith CLI releases expose ``credential-helper docker``
    but not the generic helper used by newer releases. The Docker credential
    helper follows Docker's documented JSON protocol, accepting a registry
    name on stdin and returning ``Username`` and ``Secret``. It is therefore
    a compatible, dependency-free fallback for any confirmed Cloudsmith host.
    The caller is responsible for restricting ``host`` to hosts it has already
    confirmed; this function must not become a general host-trust mechanism.
    """
    payload = run_cloudsmith_json_command(
        binary_path,
        ["credential-helper", "docker"],
        input_text=f"{host}\n",
    )
    if not isinstance(payload, dict):
        return None

    username = payload.get("Username")
    password = payload.get("Secret")
    if not isinstance(username, str) or not username:
        return None
    if not isinstance(password, str) or not password:
        return None
    return username, password


def _normalised_field(entry, key):
    """Return ``entry[key]`` lowercased, or None if it is absent or not a string."""
    value = entry.get(key)
    if not isinstance(value, str) or not value:
        return None
    return value.lower()


def _hosts_from_domains_list(binary_path, args):
    """Run one ``domains list`` invocation and return its hosts, or None on failure.

    The CLI itself applies the ``--format``/``--domain-type`` filtering and
    only lists enabled, validated domains, so every host in a successful
    response is already usable. Entries are parsed tolerantly by key so
    future additional fields do not break this parsing. Returns None if the
    command itself failed. Returns an empty set if the payload's top-level
    ``version`` is missing or unsupported, so an unrecognised (e.g. older,
    pre-contract) response shape is never misread.
    """
    payload = run_cloudsmith_json_command(binary_path, args)
    if not isinstance(payload, dict):
        return None
    if payload.get("version") != _DOMAINS_CONTRACT_VERSION:
        return set()

    entries = payload.get("domains")
    if not isinstance(entries, list):
        return None

    hosts = set()
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        host = _normalised_field(entry, "host")
        if host:
            hosts.add(host)
    return hosts


def fetch_cloudsmith_domains(binary_path):
    """Run ``domains list`` and return the set of usable hosts.

    This is the single authoritative source for which hosts Cloudsmith can
    authenticate. No organisation argument is passed: ``domains list`` has
    no ``--org`` option, and resolves the organisation itself from
    ``CLOUDSMITH_ORG`` (which the subprocess inherits) or from ``oidc_org``
    in the CLI's own ``config.ini``. Without one it still returns the
    built-in hosts, so an unset organisation must not skip this call.

    Two invocations cover the hosts pip and twine actually use: one filtered
    to ``--format python --domain-type native_api`` (the PyPI upload API
    twine targets), and one filtered to ``--domain-type download`` (the CDN
    serving the ``/python/simple/`` index pip resolves against). They are run
    concurrently, since each is an independent subprocess round-trip and a
    slow or hung CLI would otherwise double the latency of every credential
    lookup. Returns None if either invocation itself failed, so a partial
    answer is never mistaken for a complete one.
    """
    with ThreadPoolExecutor(max_workers=2) as executor:
        upload_future = executor.submit(_hosts_from_domains_list, binary_path, _UPLOAD_DOMAINS_ARGS)
        download_future = executor.submit(
            _hosts_from_domains_list, binary_path, _DOWNLOAD_DOMAINS_ARGS
        )
        upload_hosts = upload_future.result()
        download_hosts = download_future.result()

    if upload_hosts is None or download_hosts is None:
        return None

    return upload_hosts | download_hosts
