# uv example

Resolves and installs [`cloudsmith-keyring-example`](../example-package/)
from the `iduffy-demo`/`cloudsmith-keyring` Cloudsmith repository with
`uv sync` — no token on the command line, no `.netrc`.

`uv`'s keyring integration needs two things `pip`/`twine` don't, both
covered in [the main README's `uv` section](../../README.md#uv) and set
here in `pyproject.toml`: `keyring-provider = "subprocess"`, and a `token@`
username in the index URL.

`mise.toml` installs Python and `uv`, then wires up a *separate* throwaway
venv (`.venv-keyring`) with `cloudsmith-keyring` and the `cloudsmith` CLI —
`cloudsmith-keyring` and the CLI need to be resolvable by the `keyring`
invoked from `uv`'s `subprocess` provider, not by this project's own venv,
so its `bin/` goes on `PATH` before `uv sync` runs.

```sh
export CLOUDSMITH_ORG=iduffy-demo

mise run sync
```

Set `CLOUDSMITH_REPO` alongside `CLOUDSMITH_ORG` to run this against a
repository you control instead of the demo one; `sync` substitutes both
into a copy of `pyproject.toml` at run time, so the file itself never needs
editing.

See [`../README.md`](../README.md) for the full prerequisites.
