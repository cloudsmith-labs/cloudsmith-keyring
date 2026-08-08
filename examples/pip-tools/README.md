# pip-tools example

Compiles [`requirements.in`](./requirements.in) against the
`iduffy-demo`/`cloudsmith-keyring` Cloudsmith repository with
`pip-compile` — the same `keyring`-mediated resolution as plain `pip`,
since `pip-tools` resolves through `pip`'s own internals.

`pip-tools` 7.6.0 does not support pip 24.1+ (`stdlib_pkgs` was removed
from `pip._internal.utils.compat`), so this example pins `pip<24.1`
alongside it.

`mise.toml` installs Python and `uv`, then wires up a throwaway venv with
`cloudsmith-keyring`, the `cloudsmith` CLI, and a `pip<24.1` + `pip-tools`
pair.

```sh
export CLOUDSMITH_ORG=iduffy-demo

mise run compile
```

Set `CLOUDSMITH_REPO` alongside `CLOUDSMITH_ORG` to run this against a
repository you control instead of the demo one; `compile` substitutes both
into a copy of `requirements.in` at run time, so the file itself never needs
editing.

`requirements.txt` is not committed here (it's gitignored) — it would
immediately go stale since `example-package`'s version changes on every CI
run (see [`../twine/README.md`](../twine/README.md)). Compile it locally to
see the pin `pip-compile` resolves.

See [`../README.md`](../README.md) for the full prerequisites.
