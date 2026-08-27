# twine example

Builds [`cloudsmith-keyring-example`](../example-package/) and uploads it to
the `iduffy-demo`/`cloudsmith-keyring` Cloudsmith repository with
`twine upload` — no `TWINE_USERNAME`/`TWINE_PASSWORD`, no token on the
command line.

`.pypirc` names the repository and the fixed `token` username (safe to
commit); `twine` asks `keyring` for the password the same way it would for
any other configured repository.

`mise.toml` installs Python and `uv`, then wires up a throwaway venv with
`cloudsmith-keyring`, the `cloudsmith` CLI, `build`, and `twine`.

```sh
export CLOUDSMITH_WORKSPACE=iduffy-demo

mise run publish
```

Set `CLOUDSMITH_REPO` alongside `CLOUDSMITH_WORKSPACE` to run this against a
repository you control instead of the demo one; `publish` substitutes both
into a copy of `.pypirc` at run time, so the file itself never needs
editing.

Uploading the same version twice fails — Cloudsmith does not support
`--skip-existing` on this repository — so re-running this locally against
a version that already exists requires bumping
`../example-package/pyproject.toml`'s `version` first, or setting
`EXAMPLE_VERSION` (the CI workflow does this automatically per run):

```sh
EXAMPLE_VERSION=0.1.$(date +%s) mise run publish
```

See [`../README.md`](../README.md) for the full prerequisites.
