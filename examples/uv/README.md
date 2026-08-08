# uv example

Resolves and installs [`cloudsmith-keyring-example`](../example-package/)
from the `iduffy-demo`/`cloudsmith-keyring` Cloudsmith repository with
`uv sync` — no token on the command line, no `.netrc`.

`uv`'s keyring integration needs two things `pip`/`twine` don't, both
covered in [the main README's `uv` section](../../README.md#uv) and set
here in `pyproject.toml`: `keyring-provider = "subprocess"`, and a `token@`
username in the index URL.

```sh
pip install cloudsmith-keyring keyring
pip install "git+https://github.com/cloudsmith-io/cloudsmith-cli.git@custom-domains"  # see ../README.md
export CLOUDSMITH_ORG=iduffy-demo

uv sync
uv run python -c "import cloudsmith_keyring_example; print(cloudsmith_keyring_example.greet())"
```

`cloudsmith-keyring` and the `cloudsmith` CLI need to be resolvable by the
`keyring` invoked from `uv`'s `subprocess` provider, not by this project's
own venv — `uv run keyring --list-backends` should show
`cloudsmith_keyring.backend.CloudsmithKeyringBackend`.

See [`../README.md`](../README.md) for the full prerequisites.
