from cloudsmith_keyring._hosts import parse_host


def test_parse_host_from_full_url_with_scheme_and_path():
    assert (
        parse_host("https://dl.cloudsmith.io/basic/org/repo/python/simple/") == "dl.cloudsmith.io"
    )


def test_parse_host_lowercases():
    assert parse_host("https://DL.CloudSmith.IO/foo") == "dl.cloudsmith.io"


def test_parse_host_with_port():
    assert parse_host("https://dl.cloudsmith.io:8443/foo") == "dl.cloudsmith.io"


def test_parse_host_with_userinfo():
    assert parse_host("https://user:pass@dl.cloudsmith.io/foo") == "dl.cloudsmith.io"


def test_parse_host_bare_host_no_scheme():
    assert parse_host("dl.cloudsmith.io") == "dl.cloudsmith.io"


def test_parse_host_returns_none_for_empty_or_missing():
    assert parse_host("") is None
    assert parse_host(None) is None


def test_parse_host_returns_none_when_unparsable():
    assert parse_host("http://[::1:bad") is None
