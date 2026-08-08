import keyring.backend

from cloudsmith_keyring.backend import CloudsmithKeyringBackend


def test_backend_discoverable_via_get_all_keyring():
    all_backends = keyring.backend.get_all_keyring()
    assert any(isinstance(backend, CloudsmithKeyringBackend) for backend in all_backends)
