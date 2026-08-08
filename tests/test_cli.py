import json
import os
import subprocess

import pytest

from cloudsmith_keyring import _cli


def _fake_completed_process(stdout="", stderr="", returncode=0):
    return subprocess.CompletedProcess(
        args=["cloudsmith"], returncode=returncode, stdout=stdout, stderr=stderr
    )


def test_find_cloudsmith_binary_uses_path(monkeypatch):
    monkeypatch.delenv("CLOUDSMITH_CLI_PATH", raising=False)
    monkeypatch.setattr(
        _cli.shutil,
        "which",
        lambda name, path=None: "/usr/bin/cloudsmith" if name == "cloudsmith" else None,
    )
    assert _cli.find_cloudsmith_binary() == "/usr/bin/cloudsmith"


def test_find_cloudsmith_binary_respects_override(monkeypatch):
    monkeypatch.setenv("CLOUDSMITH_CLI_PATH", "/opt/custom/cloudsmith")
    monkeypatch.setattr(
        _cli.shutil,
        "which",
        lambda name: "/opt/custom/cloudsmith" if name == "/opt/custom/cloudsmith" else None,
    )
    assert _cli.find_cloudsmith_binary() == "/opt/custom/cloudsmith"


def test_find_cloudsmith_binary_override_missing_returns_none(monkeypatch):
    monkeypatch.setenv("CLOUDSMITH_CLI_PATH", "/opt/custom/cloudsmith")
    monkeypatch.setattr(_cli.shutil, "which", lambda name: None)
    assert _cli.find_cloudsmith_binary() is None


def test_find_cloudsmith_binary_returns_none_when_missing(monkeypatch):
    monkeypatch.delenv("CLOUDSMITH_CLI_PATH", raising=False)
    monkeypatch.setattr(_cli.shutil, "which", lambda name, path=None: None)
    assert _cli.find_cloudsmith_binary() is None


def test_find_cloudsmith_binary_ignores_the_current_directory(monkeypatch, tmp_path):
    """A `cloudsmith` executable in the working directory must never be run.

    Regression test: on Windows `shutil.which` searches the current
    directory first, so `pip install` inside an untrusted checkout would
    execute a `cloudsmith.bat` shipped by that repository.
    """
    monkeypatch.delenv("CLOUDSMITH_CLI_PATH", raising=False)
    hostile = tmp_path / "cloudsmith"
    hostile.write_text("#!/bin/sh\necho pwned\n", encoding="utf-8")
    hostile.chmod(0o755)

    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("PATH", os.pathsep.join([str(tmp_path), ".", ""]))

    assert _cli.find_cloudsmith_binary() is None


def test_find_cloudsmith_binary_still_finds_it_elsewhere_on_path(monkeypatch, tmp_path):
    """Excluding the working directory must not break ordinary lookups."""
    monkeypatch.delenv("CLOUDSMITH_CLI_PATH", raising=False)
    tools = tmp_path / "tools"
    tools.mkdir()
    binary = tools / "cloudsmith"
    binary.write_text("#!/bin/sh\n", encoding="utf-8")
    binary.chmod(0o755)

    workdir = tmp_path / "work"
    workdir.mkdir()
    monkeypatch.chdir(workdir)
    monkeypatch.setenv("PATH", str(tools))

    assert _cli.find_cloudsmith_binary() == str(binary)


def test_run_command_never_uses_shell(monkeypatch):
    captured = {}

    def fake_run(command, capture_output, text, timeout, shell):
        captured["shell"] = shell
        captured["command"] = command
        return _fake_completed_process(stdout="{}")

    monkeypatch.setattr(_cli.subprocess, "run", fake_run)
    _cli.run_cloudsmith_json_command("/usr/bin/cloudsmith", ["credential-helper", "generic"])
    assert captured["shell"] is False
    assert captured["command"] == ["/usr/bin/cloudsmith", "credential-helper", "generic"]


def test_run_command_parses_json_on_success(monkeypatch):
    payload = {"version": 1, "username": "token", "password": "secret"}
    monkeypatch.setattr(
        _cli.subprocess, "run", lambda *a, **k: _fake_completed_process(stdout=json.dumps(payload))
    )
    result = _cli.run_cloudsmith_json_command(
        "/usr/bin/cloudsmith", ["credential-helper", "generic"]
    )
    assert result == payload


def test_run_command_returns_none_on_nonzero_exit(monkeypatch):
    monkeypatch.setattr(
        _cli.subprocess, "run", lambda *a, **k: _fake_completed_process(stdout="", returncode=1)
    )
    assert _cli.run_cloudsmith_json_command("/usr/bin/cloudsmith", ["x"]) is None


def test_run_command_returns_none_on_timeout(monkeypatch):
    def fake_run(*args, **kwargs):
        raise subprocess.TimeoutExpired(cmd="cloudsmith", timeout=30)

    monkeypatch.setattr(_cli.subprocess, "run", fake_run)
    assert _cli.run_cloudsmith_json_command("/usr/bin/cloudsmith", ["x"]) is None


def test_run_command_returns_none_on_oserror(monkeypatch):
    def fake_run(*args, **kwargs):
        raise OSError("boom")

    monkeypatch.setattr(_cli.subprocess, "run", fake_run)
    assert _cli.run_cloudsmith_json_command("/usr/bin/cloudsmith", ["x"]) is None


def test_run_command_returns_none_on_malformed_json(monkeypatch):
    monkeypatch.setattr(
        _cli.subprocess, "run", lambda *a, **k: _fake_completed_process(stdout="not json")
    )
    assert _cli.run_cloudsmith_json_command("/usr/bin/cloudsmith", ["x"]) is None


def test_run_command_returns_none_on_empty_stdout(monkeypatch):
    monkeypatch.setattr(_cli.subprocess, "run", lambda *a, **k: _fake_completed_process(stdout=""))
    assert _cli.run_cloudsmith_json_command("/usr/bin/cloudsmith", ["x"]) is None


def test_run_command_honours_timeout_env_var(monkeypatch):
    captured = {}

    def fake_run(command, capture_output, text, timeout, shell):
        captured["timeout"] = timeout
        return _fake_completed_process(stdout="{}")

    monkeypatch.setenv("CLOUDSMITH_KEYRING_TIMEOUT", "5")
    monkeypatch.setattr(_cli.subprocess, "run", fake_run)
    _cli.run_cloudsmith_json_command("/usr/bin/cloudsmith", ["x"])
    assert captured["timeout"] == 5.0


@pytest.mark.parametrize("raw_timeout", ["nan", "inf", "-inf", "0", "-1", "abc", ""])
def test_run_command_falls_back_for_unusable_timeouts(monkeypatch, raw_timeout):
    """Only a positive, finite timeout is usable; anything else uses the default.

    Regression test: `float("nan")`/`float("inf")` parse fine but make
    `subprocess.run` raise ValueError/OverflowError from deep inside
    selectors — neither TimeoutExpired nor OSError, so it escaped this
    module's handlers and took pip down with a traceback. A non-positive
    timeout is just as bad in a quieter way: it makes every single call
    time out, so the backend silently never authenticates.
    """
    captured = {}

    def fake_run(command, capture_output, text, timeout, shell):
        captured["timeout"] = timeout
        return _fake_completed_process(stdout="{}")

    monkeypatch.setenv("CLOUDSMITH_KEYRING_TIMEOUT", raw_timeout)
    monkeypatch.setattr(_cli.subprocess, "run", fake_run)
    _cli.run_cloudsmith_json_command("/usr/bin/cloudsmith", ["x"])
    assert captured["timeout"] == 30.0


def test_run_command_default_timeout(monkeypatch):
    captured = {}

    def fake_run(command, capture_output, text, timeout, shell):
        captured["timeout"] = timeout
        return _fake_completed_process(stdout="{}")

    monkeypatch.delenv("CLOUDSMITH_KEYRING_TIMEOUT", raising=False)
    monkeypatch.setattr(_cli.subprocess, "run", fake_run)
    _cli.run_cloudsmith_json_command("/usr/bin/cloudsmith", ["x"])
    assert captured["timeout"] == 30.0


def test_fetch_generic_credential_success(monkeypatch):
    payload = {"version": 1, "username": "token", "password": "s3cr3t"}
    monkeypatch.setattr(_cli, "run_cloudsmith_json_command", lambda binary, args: payload)
    assert _cli.fetch_generic_credential("/usr/bin/cloudsmith") == ("token", "s3cr3t")


def test_fetch_generic_credential_rejects_unexpected_version(monkeypatch):
    payload = {"version": 2, "username": "token", "password": "s3cr3t"}
    monkeypatch.setattr(_cli, "run_cloudsmith_json_command", lambda binary, args: payload)
    assert _cli.fetch_generic_credential("/usr/bin/cloudsmith") is None


def test_fetch_generic_credential_none_when_command_fails(monkeypatch):
    monkeypatch.setattr(_cli, "run_cloudsmith_json_command", lambda binary, args: None)
    assert _cli.fetch_generic_credential("/usr/bin/cloudsmith") is None


def test_fetch_generic_credential_missing_fields(monkeypatch):
    payload = {"version": 1, "username": "token"}
    monkeypatch.setattr(_cli, "run_cloudsmith_json_command", lambda binary, args: payload)
    assert _cli.fetch_generic_credential("/usr/bin/cloudsmith") is None


def test_fetch_generic_credential_rejects_non_string_fields(monkeypatch):
    payload = {"version": 1, "username": ["token"], "password": {"secret": "x"}}
    monkeypatch.setattr(_cli, "run_cloudsmith_json_command", lambda binary, args: payload)
    assert _cli.fetch_generic_credential("/usr/bin/cloudsmith") is None


_UPLOAD_ARGS = _cli._UPLOAD_DOMAINS_ARGS
_DOWNLOAD_ARGS = _cli._DOWNLOAD_DOMAINS_ARGS


def _domains_entry(host, **overrides):
    """A ``domains list`` entry, in the shape the CLI actually emits.

    The CLI applies ``--format``/``--domain-type`` filtering and only lists
    enabled, validated domains itself, so unlike the old credential-helper
    contract there is no ``enabled``/``validated`` field to read here.
    """
    entry = {
        "host": host,
        "format": "python",
        "type": "custom",
        "domain_type": "native_api",
        "org": "acme",
        "repository": None,
        "primary": True,
        "created_at": None,
    }
    entry.update(overrides)
    return entry


def _fake_domains_list(upload_payload, download_payload):
    """A ``run_cloudsmith_json_command`` fake that answers by which args it got."""

    def fake_run(binary, args):
        if args == _UPLOAD_ARGS:
            return upload_payload
        if args == _DOWNLOAD_ARGS:
            return download_payload
        raise AssertionError(f"unexpected args: {args}")

    return fake_run


def test_fetch_cloudsmith_domains_unions_upload_and_download_hosts(monkeypatch):
    upload_payload = {"version": 1, "domains": [_domains_entry("python.cloudsmith.io")]}
    download_payload = {
        "version": 1,
        "domains": [_domains_entry("dl.cloudsmith.io", format=None, domain_type="download")],
    }
    monkeypatch.setattr(
        _cli, "run_cloudsmith_json_command", _fake_domains_list(upload_payload, download_payload)
    )
    hosts = _cli.fetch_cloudsmith_domains("/usr/bin/cloudsmith")
    assert hosts == {"python.cloudsmith.io", "dl.cloudsmith.io"}


def test_fetch_cloudsmith_domains_lowercases_hosts(monkeypatch):
    upload_payload = {"version": 1, "domains": [_domains_entry("Packages.Example.COM")]}
    download_payload = {"version": 1, "domains": [_domains_entry("DL.Example.COM")]}
    monkeypatch.setattr(
        _cli, "run_cloudsmith_json_command", _fake_domains_list(upload_payload, download_payload)
    )
    hosts = _cli.fetch_cloudsmith_domains("/usr/bin/cloudsmith")
    assert hosts == {"packages.example.com", "dl.example.com"}


def test_fetch_cloudsmith_domains_ignores_unknown_fields(monkeypatch):
    upload_payload = {
        "version": 1,
        "domains": [_domains_entry("packages.example.com", future_field="anything")],
    }
    download_payload = {"version": 1, "domains": []}
    monkeypatch.setattr(
        _cli, "run_cloudsmith_json_command", _fake_domains_list(upload_payload, download_payload)
    )
    hosts = _cli.fetch_cloudsmith_domains("/usr/bin/cloudsmith")
    assert hosts == {"packages.example.com"}


def test_fetch_cloudsmith_domains_skips_entries_missing_host(monkeypatch):
    upload_payload = {
        "version": 1,
        "domains": [
            {"format": "python", "type": "custom", "domain_type": "native_api"},
            _domains_entry("packages.example.com"),
        ],
    }
    download_payload = {"version": 1, "domains": []}
    monkeypatch.setattr(
        _cli, "run_cloudsmith_json_command", _fake_domains_list(upload_payload, download_payload)
    )
    hosts = _cli.fetch_cloudsmith_domains("/usr/bin/cloudsmith")
    assert hosts == {"packages.example.com"}


def test_fetch_cloudsmith_domains_none_when_command_fails(monkeypatch):
    monkeypatch.setattr(_cli, "run_cloudsmith_json_command", lambda binary, args: None)
    assert _cli.fetch_cloudsmith_domains("/usr/bin/cloudsmith") is None


def test_fetch_cloudsmith_domains_none_when_upload_command_fails(monkeypatch):
    monkeypatch.setattr(
        _cli,
        "run_cloudsmith_json_command",
        _fake_domains_list(None, {"version": 1, "domains": []}),
    )
    assert _cli.fetch_cloudsmith_domains("/usr/bin/cloudsmith") is None


def test_fetch_cloudsmith_domains_none_when_download_command_fails(monkeypatch):
    monkeypatch.setattr(
        _cli,
        "run_cloudsmith_json_command",
        _fake_domains_list({"version": 1, "domains": []}, None),
    )
    assert _cli.fetch_cloudsmith_domains("/usr/bin/cloudsmith") is None


def test_fetch_cloudsmith_domains_none_on_malformed_structure(monkeypatch):
    monkeypatch.setattr(
        _cli, "run_cloudsmith_json_command", lambda binary, args: {"version": 1, "domains": "oops"}
    )
    assert _cli.fetch_cloudsmith_domains("/usr/bin/cloudsmith") is None
    monkeypatch.setattr(
        _cli, "run_cloudsmith_json_command", lambda binary, args: ["not", "a", "dict"]
    )
    assert _cli.fetch_cloudsmith_domains("/usr/bin/cloudsmith") is None


def test_fetch_cloudsmith_domains_empty_set_on_unexpected_version(monkeypatch):
    payload = {"version": 2, "domains": [_domains_entry("packages.example.com")]}
    monkeypatch.setattr(_cli, "run_cloudsmith_json_command", lambda binary, args: payload)
    assert _cli.fetch_cloudsmith_domains("/usr/bin/cloudsmith") == set()


def test_fetch_cloudsmith_domains_empty_set_when_version_missing(monkeypatch):
    payload = {"domains": [_domains_entry("packages.example.com")]}
    monkeypatch.setattr(_cli, "run_cloudsmith_json_command", lambda binary, args: payload)
    assert _cli.fetch_cloudsmith_domains("/usr/bin/cloudsmith") == set()


def test_fetch_cloudsmith_domains_empty_set_on_old_data_shape(monkeypatch):
    payload = {"data": [_domains_entry("packages.example.com")]}
    monkeypatch.setattr(_cli, "run_cloudsmith_json_command", lambda binary, args: payload)
    assert _cli.fetch_cloudsmith_domains("/usr/bin/cloudsmith") == set()


def test_fetch_cloudsmith_domains_invokes_domains_list_with_expected_filters(monkeypatch):
    """The CLI resolves the organisation itself, from CLOUDSMITH_ORG or config.ini.

    Regression test: ``domains list`` has no ``--org`` option, so passing one
    would make the CLI exit non-zero and leave the backend with no trusted
    hosts at all.
    """
    captured_args = []

    def fake_run(binary, args):
        captured_args.append(args)
        return {"version": 1, "domains": []}

    monkeypatch.setattr(_cli, "run_cloudsmith_json_command", fake_run)
    _cli.fetch_cloudsmith_domains("/usr/bin/cloudsmith")
    assert sorted(map(tuple, captured_args)) == sorted(map(tuple, [_UPLOAD_ARGS, _DOWNLOAD_ARGS]))
