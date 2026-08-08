# pip-tools example

Compiles [`requirements.in`](./requirements.in) against the
`iduffy-demo`/`cloudsmith-keyring` Cloudsmith repository with
`pip-compile` — the same `keyring`-mediated resolution as plain `pip`,
since `pip-tools` resolves through `pip`'s own internals.

`pip-tools` 7.6.0 does not support pip 24.1+ (`stdlib_pkgs` was removed
from `pip._internal.utils.compat`), so this example pins `pip<24.1`
alongside it.

```sh
pip install cloudsmith-keyring keyring "pip<24.1" pip-tools
pip install "git+https://github.com/cloudsmith-io/cloudsmith-cli.git@custom-domains"  # see ../README.md
export CLOUDSMITH_ORG=iduffy-demo

pip-compile -o requirements.txt requirements.in
```

`requirements.txt` is not committed here — it would immediately go stale
since `example-package`'s version changes on every CI run (see
[`../twine/README.md`](../twine/README.md)). Compile it locally to see the
pin `pip-compile` resolves.

See [`../README.md`](../README.md) for the full prerequisites.
