# pip example

Installs [`cloudsmith-keyring-example`](../example-package/) from the
`iduffy-demo`/`cloudsmith-keyring` Cloudsmith repository using plain
`pip install` — no `--extra-index-url` credentials, no `pip.conf`, no
`~/.netrc`.

`requirements.txt` carries the index URL with the fixed `token` username
(safe to commit — see the main [README](../../README.md#uv)); the password
comes from `keyring` at install time.

`mise.toml` installs Python and `uv`, then wires up a throwaway venv with
`cloudsmith-keyring`, the `cloudsmith` CLI, and real `pip` — nothing here
touches your own environment.

```sh
export CLOUDSMITH_ORG=iduffy-demo

mise run install-example
```

Set `CLOUDSMITH_REPO` alongside `CLOUDSMITH_ORG` to run this against a
repository you control instead of the demo one; `install-example`
substitutes both into `requirements.txt` at run time, so the file itself
never needs editing.

See [`../README.md`](../README.md) for the full prerequisites.
