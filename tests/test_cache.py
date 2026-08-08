from cloudsmith_keyring._cache import TTLCache


def test_returns_none_for_missing_key():
    cache = TTLCache(ttl_seconds=300)
    assert cache.get("host") is None


def test_returns_cached_value_within_ttl():
    current_time = [1000.0]
    cache = TTLCache(ttl_seconds=300, clock=lambda: current_time[0])
    cache.set("host", ("token", "value"))
    current_time[0] += 100
    assert cache.get("host") == ("token", "value")


def test_expires_after_ttl():
    current_time = [1000.0]
    cache = TTLCache(ttl_seconds=300, clock=lambda: current_time[0])
    cache.set("host", "value")
    current_time[0] += 301
    assert cache.get("host") is None


def test_different_keys_are_independent():
    cache = TTLCache(ttl_seconds=300)
    cache.set("a", "1")
    assert cache.get("b") is None
    assert cache.get("a") == "1"


def test_set_overwrites_existing_entry():
    current_time = [1000.0]
    cache = TTLCache(ttl_seconds=300, clock=lambda: current_time[0])
    cache.set("host", "first")
    cache.set("host", "second")
    assert cache.get("host") == "second"
