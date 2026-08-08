# twine example

Builds [`cloudsmith-keyring-example`](../example-package/) and uploads it to
the `iduffy-demo`/`cloudsmith-keyring` Cloudsmith repository with
`twine upload` — no `TWINE_USERNAME`/`TWINE_PASSWORD`, no token on the
command line.

`.pypirc` names the repository and the fixed `token` username (safe to
commit); `twine` asks `keyring` for the password the same way it would for
any other configured repository.

```sh
pip install cloudsmith-keyring keyring twine build
pip install "git+https://github.com/cloudsmith-io/cloudsmith-cli.git@custom-domains"  # see ../README.md
export CLOUDSMITH_ORG=iduffy-demo

python -m build --outdir dist ../example-package
twine upload --config-file .pypirc -r cloudsmith dist/*
```

Uploading the same version twice fails — Cloudsmith does not support
`--skip-existing` on this repository — so re-running this locally against
a version that already exists requires bumping
`../example-package/pyproject.toml`'s `version` first. The CI workflow
does this automatically per run.

See [`../README.md`](../README.md) for the full prerequisites.
