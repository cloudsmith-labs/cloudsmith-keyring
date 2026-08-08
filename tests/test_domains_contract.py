"""Contract tests against real, recorded ``domains list`` output.

Every other test in the suite hand-writes its payloads, which keeps them
readable but means none of them would notice the CLI changing the shape or
the spelling of a field. The fixtures here are the verbatim stdout of real
``cloudsmith domains list`` runs, so these tests fail if the contract this
package parses ever drifts.

Refresh them with:

    cloudsmith domains list --format python --domain-type native_api \\
        | python -m json.tool > tests/fixtures/domains_list_upload_v1.json
    cloudsmith domains list --domain-type download \\
        | python -m json.tool > tests/fixtures/domains_list_download_v1.json
"""

import json
from pathlib import Path

import pytest

from cloudsmith_keyring import _cli

FIXTURES_DIR = Path(__file__).parent / "fixtures"
UPLOAD_FIXTURE_PATH = FIXTURES_DIR / "domains_list_upload_v1.json"
DOWNLOAD_FIXTURE_PATH = FIXTURES_DIR / "domains_list_download_v1.json"


@pytest.fixture(name="upload_payload")
def upload_payload_fixture():
    return json.loads(UPLOAD_FIXTURE_PATH.read_text(encoding="utf-8"))


@pytest.fixture(name="download_payload")
def download_payload_fixture():
    return json.loads(DOWNLOAD_FIXTURE_PATH.read_text(encoding="utf-8"))


def test_recorded_payloads_declare_the_version_this_package_supports(
    upload_payload, download_payload
):
    assert upload_payload["version"] == _cli._DOMAINS_CONTRACT_VERSION
    assert download_payload["version"] == _cli._DOMAINS_CONTRACT_VERSION


def test_recorded_payload_entries_carry_the_field_this_package_reads(
    upload_payload, download_payload
):
    for entry in upload_payload["domains"] + download_payload["domains"]:
        assert "host" in entry


def test_real_upload_filter_narrows_to_the_python_native_api_host(
    monkeypatch, upload_payload, download_payload
):
    """The whole point of the filters: --format python --domain-type native_api
    narrows the built-in table down to the one twine-upload host."""
    monkeypatch.setattr(
        _cli,
        "run_cloudsmith_json_command",
        lambda binary, args: upload_payload if "--format" in args else download_payload,
    )
    assert _cli.fetch_cloudsmith_domains("/usr/bin/cloudsmith") == {
        "python.cloudsmith.io",
        "dl.cloudsmith.io",
    }


def test_real_download_filter_includes_the_cdn_host(download_payload):
    hosts = {entry["host"] for entry in download_payload["domains"]}
    assert "dl.cloudsmith.io" in hosts
