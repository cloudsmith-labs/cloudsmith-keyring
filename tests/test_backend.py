import json
import logging
import subprocess

import keyring.backend
import keyring.backends.chainer
import pytest

from cloudsmith_keyring import _cli
from cloudsmith_keyring.backend import CloudsmithKeyringBackend


def test_priority_is_9_9():
    assert CloudsmithKeyringBackend.priority == 9.9


@pytest.mark.parametrize("operation", ["set_password", "delete_password"])
def test_writes_raise_not_implemented_so_the_chainer_falls_through(operation):
    """The read-only refusal must be the one exception keyring's chainer catches.

    ChainerBackend wraps `set_password`/`delete_password` in
    `try/except NotImplementedError` and nothing else. Raising anything
    else from this backend — which sits ahead of the OS keychain at
    priority 9.9 — aborts the whole chain, so a user who merely installs
    this package could no longer store a credential for *any* service.
    """
    backend = CloudsmithKeyringBackend()
    arguments = ("https://pypi.org/", "alice", "secret")
    if operation == "delete_password":
        arguments = arguments[:2]

    with pytest.raises(NotImplementedError):
        getattr(backend, operation)(*arguments)


@pytest.mark.parametrize("operation", ["set_password", "delete_password"])
def test_real_chainer_reaches_the_next_backend_for_writes(monkeypatch, operation):
    """End-to-end guard against the above, driven through keyring's own chainer."""
    chainer = keyring.backends.chainer.ChainerBackend()
    recorded = []

    class RecordingBackend(keyring.backend.KeyringBackend):
        priority = 1

        def get_password(self, service, username):
            del service, username

        def set_password(self, service, username, password):
            recorded.append(("set", service, username, password))

        def delete_password(self, service, username):
            recorded.append(("delete", service, username))

    monkeypatch.setattr(
        type(chainer),
        "backends",
        property(lambda self: [CloudsmithKeyringBackend(), RecordingBackend()]),
    )

    if operation == "set_password":
        chainer.set_password("https://pypi.org/", "alice", "secret")
        assert recorded == [("set", "https://pypi.org/", "alice", "secret")]
    else:
        chainer.delete_password("https://pypi.org/", "alice")
        assert recorded == [("delete", "https://pypi.org/", "alice")]


def test_get_credential_for_standard_cloudsmith_host_uses_domains_lookup(monkeypatch):
    """There are no built-in hosts: even the standard hosts need CLI confirmation."""
    monkeypatch.delenv("CLOUDSMITH_ORG", raising=False)
    called = []
    monkeypatch.setattr(
        "cloudsmith_keyring.backend.find_cloudsmith_binary", lambda: "/usr/bin/cloudsmith"
    )
    monkeypatch.setattr(
        "cloudsmith_keyring.backend.fetch_cloudsmith_domains",
        lambda binary: called.append(binary) or {"dl.cloudsmith.io"},
    )
    monkeypatch.setattr(
        "cloudsmith_keyring.backend.fetch_generic_credential",
        lambda binary: ("token", "s3cr3t"),
    )
    backend = CloudsmithKeyringBackend()
    credential = backend.get_credential(
        "https://dl.cloudsmith.io/basic/org/repo/python/simple/", None
    )
    assert credential is not None
    assert credential.username == "token"
    assert credential.password == "s3cr3t"
    assert called == ["/usr/bin/cloudsmith"]


def test_custom_host_absent_from_domains_output_does_not_resolve(monkeypatch):
    """A custom host is never trusted unless the CLI confirms it."""
    monkeypatch.delenv("CLOUDSMITH_ORG", raising=False)
    monkeypatch.setattr(
        "cloudsmith_keyring.backend.find_cloudsmith_binary", lambda: "/usr/bin/cloudsmith"
    )
    monkeypatch.setattr(
        "cloudsmith_keyring.backend.fetch_cloudsmith_domains",
        lambda binary: set(),
    )
    backend = CloudsmithKeyringBackend()
    assert backend.get_credential("https://packages.example.com/x", None) is None


def test_non_cloudsmith_host_never_invokes_generic_credential(monkeypatch):
    monkeypatch.delenv("CLOUDSMITH_ORG", raising=False)
    called = []
    monkeypatch.setattr(
        "cloudsmith_keyring.backend.find_cloudsmith_binary", lambda: "/usr/bin/cloudsmith"
    )
    monkeypatch.setattr(
        "cloudsmith_keyring.backend.fetch_generic_credential",
        lambda binary: called.append("generic") or ("token", "x"),
    )
    monkeypatch.setattr(
        "cloudsmith_keyring.backend.fetch_cloudsmith_domains",
        lambda binary: set(),
    )
    backend = CloudsmithKeyringBackend()

    assert backend.get_credential("https://pypi.org/simple/", None) is None
    assert backend.get_credential("https://evil.example.com/x", None) is None
    assert called == []


def _domains_payload(*entries):
    return {"version": 1, "domains": list(entries)}


def _default_entry(host, package_format, domain_type):
    return {
        "host": host,
        "format": package_format,
        "type": "default",
        "domain_type": domain_type,
    }


@pytest.mark.parametrize(
    "host,package_format,domain_type",
    [
        ("npm.cloudsmith.io", "npm", "native_api"),
        ("docker.cloudsmith.io", "docker", "native_api"),
        ("maven.cloudsmith.io", "maven", "native_api"),
        ("upload.cloudsmith.io", None, "upload"),
    ],
)
def test_cloudsmith_host_for_another_ecosystem_is_left_to_the_next_backend(
    monkeypatch, host, package_format, domain_type
):
    """A genuine Cloudsmith host still gets None unless it serves Python packages.

    At priority 9.9 this backend is consulted ahead of the OS keychain, so
    claiming e.g. docker.cloudsmith.io would shadow a docker credential the
    user had deliberately stored there. The CLI itself applies the
    --format/--domain-type filtering now, so the fake below filters the
    same way the real CLI does rather than this package rejecting entries.
    """
    generic_calls = []
    monkeypatch.setattr(
        "cloudsmith_keyring.backend.find_cloudsmith_binary", lambda: "/usr/bin/cloudsmith"
    )

    all_entries = [
        _default_entry(host, package_format, domain_type),
        _default_entry("python.cloudsmith.io", "python", "native_api"),
        _default_entry("dl.cloudsmith.io", None, "download"),
    ]

    def fake_run(binary, args):
        if "--format" in args:
            matching = [entry for entry in all_entries if entry["format"] == "python"]
        else:
            matching = [entry for entry in all_entries if entry["domain_type"] == "download"]
        return _domains_payload(*matching)

    monkeypatch.setattr(_cli, "run_cloudsmith_json_command", fake_run)
    monkeypatch.setattr(
        "cloudsmith_keyring.backend.fetch_generic_credential",
        lambda binary: generic_calls.append(binary) or ("token", "s3cr3t"),
    )
    backend = CloudsmithKeyringBackend()

    assert backend.get_credential(f"https://{host}/org/repo/", None) is None
    assert generic_calls == []


@pytest.mark.parametrize(
    "service_url",
    [
        "https://python.cloudsmith.io/my-org/my-repo/",
        "https://dl.cloudsmith.io/basic/my-org/my-repo/python/simple/",
    ],
)
def test_twine_upload_and_pip_index_hosts_both_resolve(monkeypatch, service_url):
    monkeypatch.setattr(
        "cloudsmith_keyring.backend.find_cloudsmith_binary", lambda: "/usr/bin/cloudsmith"
    )
    monkeypatch.setattr(
        _cli,
        "run_cloudsmith_json_command",
        lambda binary, args: _domains_payload(
            _default_entry("python.cloudsmith.io", "python", "native_api"),
            _default_entry("dl.cloudsmith.io", None, "download"),
        ),
    )
    monkeypatch.setattr(
        "cloudsmith_keyring.backend.fetch_generic_credential",
        lambda binary: ("token", "s3cr3t"),
    )
    backend = CloudsmithKeyringBackend()

    credential = backend.get_credential(service_url, None)
    assert credential is not None
    assert (credential.username, credential.password) == ("token", "s3cr3t")


def test_binary_absent_returns_none_silently(monkeypatch):
    monkeypatch.setattr("cloudsmith_keyring.backend.find_cloudsmith_binary", lambda: None)
    backend = CloudsmithKeyringBackend()
    assert backend.get_credential("https://dl.cloudsmith.io/x", None) is None


def test_full_stack_nonzero_exit_returns_none(monkeypatch):
    monkeypatch.setattr(
        "cloudsmith_keyring.backend.find_cloudsmith_binary", lambda: "/usr/bin/cloudsmith"
    )
    monkeypatch.setattr(
        _cli.subprocess,
        "run",
        lambda *a, **k: subprocess.CompletedProcess(
            args=["cloudsmith"], returncode=1, stdout="", stderr="denied"
        ),
    )
    backend = CloudsmithKeyringBackend()
    assert backend.get_credential("https://dl.cloudsmith.io/x", None) is None


def test_full_stack_timeout_returns_none(monkeypatch):
    monkeypatch.setattr(
        "cloudsmith_keyring.backend.find_cloudsmith_binary", lambda: "/usr/bin/cloudsmith"
    )

    def fake_run(*args, **kwargs):
        raise subprocess.TimeoutExpired(cmd="cloudsmith", timeout=30)

    monkeypatch.setattr(_cli.subprocess, "run", fake_run)
    backend = CloudsmithKeyringBackend()
    assert backend.get_credential("https://dl.cloudsmith.io/x", None) is None


def test_full_stack_malformed_json_returns_none(monkeypatch):
    monkeypatch.setattr(
        "cloudsmith_keyring.backend.find_cloudsmith_binary", lambda: "/usr/bin/cloudsmith"
    )
    monkeypatch.setattr(
        _cli.subprocess,
        "run",
        lambda *a, **k: subprocess.CompletedProcess(
            args=["cloudsmith"], returncode=0, stdout="not json at all", stderr=""
        ),
    )
    backend = CloudsmithKeyringBackend()
    assert backend.get_credential("https://dl.cloudsmith.io/x", None) is None


def test_unexpected_version_returns_none(monkeypatch):
    monkeypatch.setattr(
        "cloudsmith_keyring.backend.find_cloudsmith_binary", lambda: "/usr/bin/cloudsmith"
    )
    monkeypatch.setattr(
        "cloudsmith_keyring.backend.fetch_cloudsmith_domains",
        lambda binary: {"dl.cloudsmith.io"},
    )
    monkeypatch.setattr(
        _cli.subprocess,
        "run",
        lambda *a, **k: subprocess.CompletedProcess(
            args=["cloudsmith"],
            returncode=0,
            stdout='{"version": 2, "username": "token", "password": "x"}',
            stderr="",
        ),
    )
    backend = CloudsmithKeyringBackend()
    assert backend.get_credential("https://dl.cloudsmith.io/x", None) is None


def test_custom_domain_resolves_via_domains_lookup(monkeypatch):
    monkeypatch.setenv("CLOUDSMITH_ORG", "my-org")
    monkeypatch.setattr(
        "cloudsmith_keyring.backend.find_cloudsmith_binary", lambda: "/usr/bin/cloudsmith"
    )
    monkeypatch.setattr(
        "cloudsmith_keyring.backend.fetch_cloudsmith_domains",
        lambda binary: {"packages.example.com"},
    )
    monkeypatch.setattr(
        "cloudsmith_keyring.backend.fetch_generic_credential",
        lambda binary: ("token", "s3cr3t"),
    )
    backend = CloudsmithKeyringBackend()
    credential = backend.get_credential("https://packages.example.com/simple/", None)
    assert credential.username == "token"
    assert credential.password == "s3cr3t"


def test_disabled_or_unvalidated_custom_domain_does_not_resolve(monkeypatch):
    monkeypatch.setenv("CLOUDSMITH_ORG", "my-org")
    monkeypatch.setattr(
        "cloudsmith_keyring.backend.find_cloudsmith_binary", lambda: "/usr/bin/cloudsmith"
    )
    monkeypatch.setattr("cloudsmith_keyring.backend.fetch_cloudsmith_domains", lambda binary: set())
    backend = CloudsmithKeyringBackend()
    assert backend.get_credential("https://unvalidated.example.com/simple/", None) is None


@pytest.mark.parametrize("org", [None, "my-org"])
def test_domains_invoked_without_an_org_flag_whether_or_not_org_is_set(monkeypatch, org):
    """Regression test: ``domains list`` has no ``--org`` option.

    Passing one made the real CLI exit 2 with "No such option '--org'",
    which this package degrades to None — so every user with CLOUDSMITH_ORG
    set silently got no trusted hosts at all. The CLI reads CLOUDSMITH_ORG
    from the environment it inherits, so there is nothing to pass on.
    """
    if org is None:
        monkeypatch.delenv("CLOUDSMITH_ORG", raising=False)
    else:
        monkeypatch.setenv("CLOUDSMITH_ORG", org)
    captured_args = []

    def fake_run(binary, args):
        captured_args.append(args)
        if "--format" in args:
            return {"version": 1, "domains": []}
        return {
            "version": 1,
            "domains": [
                {
                    "host": "dl.cloudsmith.io",
                    "format": None,
                    "type": "default",
                    "domain_type": "download",
                }
            ],
        }

    monkeypatch.setattr(
        "cloudsmith_keyring.backend.find_cloudsmith_binary", lambda: "/usr/bin/cloudsmith"
    )
    monkeypatch.setattr(_cli, "run_cloudsmith_json_command", fake_run)
    monkeypatch.setattr(
        "cloudsmith_keyring.backend.fetch_generic_credential",
        lambda binary: ("token", "s3cr3t"),
    )
    backend = CloudsmithKeyringBackend()
    assert backend.get_credential("https://packages.example.com/x", None) is None
    credential = backend.get_credential("https://dl.cloudsmith.io/x", None)

    assert credential is not None
    assert credential.password == "s3cr3t"
    assert all("--org" not in args for args in captured_args)
    assert sorted(map(tuple, captured_args)) == sorted(
        map(tuple, [_cli._UPLOAD_DOMAINS_ARGS, _cli._DOWNLOAD_DOMAINS_ARGS])
    )


def test_domains_lookup_unsupported_trusts_nothing(monkeypatch):
    """There are no built-in hosts: a CLI that can't answer ``domains list`` trusts none."""
    monkeypatch.setattr(
        "cloudsmith_keyring.backend.find_cloudsmith_binary", lambda: "/usr/bin/cloudsmith"
    )
    monkeypatch.setattr("cloudsmith_keyring.backend.fetch_cloudsmith_domains", lambda binary: None)
    backend = CloudsmithKeyringBackend()

    assert backend.get_credential("https://dl.cloudsmith.io/x", None) is None
    assert backend.get_credential("https://packages.example.com/simple/", None) is None


def test_transient_domains_failure_is_retried_for_custom_hosts(monkeypatch):
    attempts = []

    def fake_fetch(binary):
        attempts.append(binary)
        return None if len(attempts) == 1 else {"packages.example.com"}

    monkeypatch.setattr(
        "cloudsmith_keyring.backend.find_cloudsmith_binary", lambda: "/usr/bin/cloudsmith"
    )
    monkeypatch.setattr("cloudsmith_keyring.backend.fetch_cloudsmith_domains", fake_fetch)
    monkeypatch.setattr(
        "cloudsmith_keyring.backend.fetch_generic_credential",
        lambda binary: ("token", "s3cr3t"),
    )
    backend = CloudsmithKeyringBackend()

    assert backend.get_credential("https://packages.example.com/simple/", None) is None
    assert backend.get_credential("https://packages.example.com/simple/", None) is not None
    assert len(attempts) == 2


def test_empty_host_set_is_cached_and_not_retried(monkeypatch):
    """An *answered* lookup that trusts nothing is authoritative, so cache it.

    This is the other half of the None/empty distinction: an unsupported
    contract version yields an empty set, which is a real answer and must
    not cause a re-fetch on every single keyring lookup.
    """
    attempts = []

    def fake_fetch(binary):
        attempts.append(binary)
        return set()

    monkeypatch.setattr(
        "cloudsmith_keyring.backend.find_cloudsmith_binary", lambda: "/usr/bin/cloudsmith"
    )
    monkeypatch.setattr("cloudsmith_keyring.backend.fetch_cloudsmith_domains", fake_fetch)
    backend = CloudsmithKeyringBackend()

    assert backend.get_credential("https://packages.example.com/x", None) is None
    assert backend.get_credential("https://packages.example.com/x", None) is None
    assert len(attempts) == 1


def test_missing_binary_is_retried_rather_than_cached(monkeypatch):
    """The CLI appearing on PATH mid-process must be picked up."""
    lookups = []

    def fake_find():
        lookups.append(True)
        return None if len(lookups) == 1 else "/usr/bin/cloudsmith"

    monkeypatch.setattr("cloudsmith_keyring.backend.find_cloudsmith_binary", fake_find)
    monkeypatch.setattr(
        "cloudsmith_keyring.backend.fetch_cloudsmith_domains",
        lambda binary: {"dl.cloudsmith.io"},
    )
    monkeypatch.setattr(
        "cloudsmith_keyring.backend.fetch_generic_credential",
        lambda binary: ("token", "s3cr3t"),
    )
    backend = CloudsmithKeyringBackend()

    assert backend.get_credential("https://dl.cloudsmith.io/x", None) is None
    assert backend.get_credential("https://dl.cloudsmith.io/x", None) is not None


def test_domains_fetched_once_per_process_across_multiple_hosts(monkeypatch):
    call_count = [0]

    def fake_fetch(binary):
        call_count[0] += 1
        return {"dl.cloudsmith.io", "packages.example.com"}

    monkeypatch.setattr(
        "cloudsmith_keyring.backend.find_cloudsmith_binary", lambda: "/usr/bin/cloudsmith"
    )
    monkeypatch.setattr("cloudsmith_keyring.backend.fetch_cloudsmith_domains", fake_fetch)
    monkeypatch.setattr(
        "cloudsmith_keyring.backend.fetch_generic_credential",
        lambda binary: ("token", "s3cr3t"),
    )
    backend = CloudsmithKeyringBackend()

    backend.get_credential("https://dl.cloudsmith.io/x", None)
    backend.get_credential("https://packages.example.com/x", None)
    assert call_count[0] == 1


def test_cache_prevents_second_call_within_ttl_then_refetches_after_expiry(monkeypatch):
    current_time = [1000.0]
    call_count = [0]
    monkeypatch.setattr(
        "cloudsmith_keyring.backend.find_cloudsmith_binary", lambda: "/usr/bin/cloudsmith"
    )
    monkeypatch.setattr(
        "cloudsmith_keyring.backend.fetch_cloudsmith_domains",
        lambda binary: {"dl.cloudsmith.io"},
    )

    def fake_fetch(binary):
        call_count[0] += 1
        return ("token", "s3cr3t")

    monkeypatch.setattr("cloudsmith_keyring.backend.fetch_generic_credential", fake_fetch)
    backend = CloudsmithKeyringBackend(clock=lambda: current_time[0])

    backend.get_credential("https://dl.cloudsmith.io/x", None)
    assert call_count[0] == 1

    current_time[0] += 100
    backend.get_credential("https://dl.cloudsmith.io/x", None)
    assert call_count[0] == 1

    current_time[0] += 300
    backend.get_credential("https://dl.cloudsmith.io/x", None)
    assert call_count[0] == 2


def test_cache_ttl_overridable_via_env_var(monkeypatch):
    monkeypatch.setenv("CLOUDSMITH_KEYRING_TTL", "10")
    current_time = [1000.0]
    call_count = [0]
    monkeypatch.setattr(
        "cloudsmith_keyring.backend.find_cloudsmith_binary", lambda: "/usr/bin/cloudsmith"
    )
    monkeypatch.setattr(
        "cloudsmith_keyring.backend.fetch_cloudsmith_domains",
        lambda binary: {"dl.cloudsmith.io"},
    )

    def fake_fetch(binary):
        call_count[0] += 1
        return ("token", "s3cr3t")

    monkeypatch.setattr("cloudsmith_keyring.backend.fetch_generic_credential", fake_fetch)
    backend = CloudsmithKeyringBackend(clock=lambda: current_time[0])

    backend.get_credential("https://dl.cloudsmith.io/x", None)
    current_time[0] += 11
    backend.get_credential("https://dl.cloudsmith.io/x", None)
    assert call_count[0] == 2


@pytest.mark.parametrize("raw_ttl", ["nan", "inf", "0", "-5", "abc"])
def test_unusable_ttl_falls_back_to_the_default(monkeypatch, raw_ttl):
    """A non-positive or non-finite TTL must not be honoured.

    Zero or negative would expire every entry the moment it is written,
    turning the cache off and re-shelling out to the CLI on every one of
    pip's many per-request lookups.
    """
    monkeypatch.setenv("CLOUDSMITH_KEYRING_TTL", raw_ttl)
    current_time = [1000.0]
    call_count = [0]
    monkeypatch.setattr(
        "cloudsmith_keyring.backend.find_cloudsmith_binary", lambda: "/usr/bin/cloudsmith"
    )
    monkeypatch.setattr(
        "cloudsmith_keyring.backend.fetch_cloudsmith_domains",
        lambda binary: {"dl.cloudsmith.io"},
    )

    def fake_fetch(binary):
        call_count[0] += 1
        return ("token", "s3cr3t")

    monkeypatch.setattr("cloudsmith_keyring.backend.fetch_generic_credential", fake_fetch)
    backend = CloudsmithKeyringBackend(clock=lambda: current_time[0])

    backend.get_credential("https://dl.cloudsmith.io/x", None)
    current_time[0] += 100  # well inside the 300s default
    backend.get_credential("https://dl.cloudsmith.io/x", None)
    assert call_count[0] == 1


def test_get_password_delegates_to_shared_resolution(monkeypatch):
    monkeypatch.setattr(
        "cloudsmith_keyring.backend.find_cloudsmith_binary", lambda: "/usr/bin/cloudsmith"
    )
    monkeypatch.setattr(
        "cloudsmith_keyring.backend.fetch_cloudsmith_domains",
        lambda binary: {"dl.cloudsmith.io"},
    )
    monkeypatch.setattr(
        "cloudsmith_keyring.backend.fetch_generic_credential",
        lambda binary: ("token", "s3cr3t"),
    )
    backend = CloudsmithKeyringBackend()
    assert backend.get_password("https://dl.cloudsmith.io/x", "token") == "s3cr3t"


def test_get_password_none_for_non_cloudsmith_host(monkeypatch):
    monkeypatch.delenv("CLOUDSMITH_ORG", raising=False)
    monkeypatch.setattr(
        "cloudsmith_keyring.backend.find_cloudsmith_binary", lambda: "/usr/bin/cloudsmith"
    )
    monkeypatch.setattr("cloudsmith_keyring.backend.fetch_cloudsmith_domains", lambda binary: set())
    backend = CloudsmithKeyringBackend()
    assert backend.get_password("https://pypi.org/simple/", "irrelevant") is None


def test_unparsable_service_url_returns_none(monkeypatch):
    backend = CloudsmithKeyringBackend()
    assert backend.get_credential("", None) is None


SECRET_TOKEN = "super-secret-token-value-123"  # noqa: S105 - a fake token for tests


def _assert_secret_absent_from_logs(caplog):
    assert SECRET_TOKEN not in caplog.text
    for record in caplog.records:
        assert SECRET_TOKEN not in record.getMessage()
        assert SECRET_TOKEN not in repr(record)
        assert SECRET_TOKEN not in str(getattr(record, "args", "") or "")


def _domains_stdout():
    return json.dumps(_domains_payload(_default_entry("dl.cloudsmith.io", None, "download")))


def _generic_stdout():
    return json.dumps({"version": 1, "username": "token", "password": SECRET_TOKEN})


def test_token_never_appears_in_log_output(monkeypatch, caplog):
    """Drives the real `_cli` layer, which is the only code holding the raw token.

    Stubbing `fetch_generic_credential` (as this test used to) skips
    `run_cloudsmith_json_command` entirely — the one function that ever
    sees the CLI's stdout — so a `logger.debug(..., result.stdout)` added
    there would leak every user's token under `pip -v` while leaving this
    test green.
    """
    caplog.set_level(logging.DEBUG)
    stdouts = [_generic_stdout()]

    monkeypatch.setattr(
        "cloudsmith_keyring.backend.find_cloudsmith_binary", lambda: "/usr/bin/cloudsmith"
    )
    monkeypatch.setattr(
        "cloudsmith_keyring.backend.fetch_cloudsmith_domains",
        lambda binary: {"dl.cloudsmith.io"},
    )
    monkeypatch.setattr(
        _cli.subprocess,
        "run",
        lambda *a, **k: subprocess.CompletedProcess(
            args=["cloudsmith"], returncode=0, stdout=stdouts.pop(0), stderr=""
        ),
    )
    backend = CloudsmithKeyringBackend()
    credential = backend.get_credential("https://dl.cloudsmith.io/x", None)

    assert credential.password == SECRET_TOKEN, "the real _cli path must have run"
    _assert_secret_absent_from_logs(caplog)


@pytest.mark.parametrize(
    "returncode,stdout,stderr",
    [
        # The CLI failing *after* emitting the credential, and a CLI that
        # echoes the token on stderr: both put the secret in front of the
        # error-logging paths, which is where a leak is most likely.
        (1, "", "auth failed for token " + SECRET_TOKEN),
        (1, _generic_stdout(), ""),
        (0, "not json " + SECRET_TOKEN, ""),
    ],
)
def test_token_never_logged_on_cli_failure_paths(monkeypatch, caplog, returncode, stdout, stderr):
    caplog.set_level(logging.DEBUG)
    monkeypatch.setattr(
        _cli.subprocess,
        "run",
        lambda *a, **k: subprocess.CompletedProcess(
            args=["cloudsmith"], returncode=returncode, stdout=stdout, stderr=stderr
        ),
    )

    assert _cli.fetch_generic_credential("/usr/bin/cloudsmith") in (
        None,
        ("token", SECRET_TOKEN),
    )
    _assert_secret_absent_from_logs(caplog)
