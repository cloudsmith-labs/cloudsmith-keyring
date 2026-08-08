# cloudsmith-keyring

A [keyring](https://github.com/jaraco/keyring) backend that lets `pip install`
and `twine upload` authenticate to [Cloudsmith](https://cloudsmith.io)
repositories with **no credentials in the URL, no `pip.conf` entry, and no
`~/.netrc`**.

It works by shelling out to the [`cloudsmith`](https://pypi.org/project/cloudsmith-cli/)
CLI's credential helper and parsing its JSON output.

`cloudsmith-keyring` is deliberately a small, separate package from the full
`cloudsmith-cli`. A keyring backend only works if it is importable from the
*same* environment as `pip`/`twine`, and that is usually a per-project
virtualenv. Installing the full CLI into every one of those would pull in
click, requests and the Cloudsmith SDK along with their transitive pins,
adding weight and risking resolver conflicts with the project's own
dependencies. Keeping this package to a single dependency avoids both. The
CLI does the heavy lifting; this package only needs to find it and invoke it.

## How it works

1. `keyring` (used internally by `pip` and `twine`) asks this backend for a
   credential for a given host.
2. The backend checks whether that host is a Cloudsmith host that serves
   Python packages by consulting `cloudsmith domains list`. There is no
   hardcoded list of Cloudsmith hosts: if the CLI doesn't support that
   command, or the lookup fails, no host is treated as Cloudsmith. All other
   hosts return `None` immediately, so keyring falls through to its next
   backend and `pip`/`twine` behave exactly as if this package were absent.
3. The backend uses `cloudsmith credential-helper generic` when available,
   falling back to the Docker credential-helper protocol for any confirmed
   Cloudsmith host, and returns the token as the password (with username
   `token`).
4. The resolved token is cached in-process for a short TTL so that pip's
   repeated per-request keyring lookups don't each trigger a fresh CLI
   invocation (and, for OIDC-based auth, a fresh token exchange).

If the `cloudsmith` CLI is not installed, is not on `PATH`, exits non-zero,
times out, or produces output that can't be parsed, the backend returns
`None` silently. **A user without the CLI installed observes no behaviour
change at all** — this is the single most important property of the
backend, and is covered directly by the test suite.

## Installation

```sh
pip install git+https://github.com/cloudsmith-labs/cloudsmith-keyring.git@vX.Y.Z
```

You also need the [`cloudsmith` CLI](https://pypi.org/project/cloudsmith-cli/)
installed and authenticated. It does **not** need to be installed in the same
virtualenv as `cloudsmith-keyring`. It just needs to be resolvable on
`PATH` (or via `CLOUDSMITH_CLI_PATH`) when pip/twine run.

## Usage

### `pip install` from a Cloudsmith Python index

```sh
pip install --index-url https://dl.cloudsmith.io/basic/<org>/<repo>/python/simple/ <package>
```

No username, password, or token in the URL required — `cloudsmith-keyring`
supplies them transparently via `keyring`.

### `twine upload`

```sh
twine upload --repository-url https://python.cloudsmith.io/<org>/<repo>/ dist/*
```

Again, no `TWINE_USERNAME`/`TWINE_PASSWORD` needed. `twine` calls
`keyring.get_password(repository_url, username)` internally, which this
backend serves the same way as `get_credential`.

### `uv`

`uv` works too, with two requirements that `pip` and `twine` do not have.

**1. Opt in to the keyring provider.** `uv`'s default is `disabled`:

```sh
uv sync --keyring-provider subprocess
```

or, once, in `pyproject.toml`:

```toml
[tool.uv]
keyring-provider = "subprocess"
```

**2. Put a username in the index URL.** `uv` only consults `keyring` when
the URL already carries one. Without it, `uv` never invokes `keyring` at
all and fails with a bare 401 that looks like this backend is broken or
missing:

```toml
[[tool.uv.index]]
name = "cloudsmith"
url = "https://token@dl.cloudsmith.io/basic/<org>/<repo>/python/simple/"
```

`token` here is a username, not a secret: it is the fixed username
Cloudsmith tokens use, and the same value `credential-helper generic`
returns. It is safe to commit. The password still comes from `keyring`.

`uv` invokes `keyring get <url> <username>`, which reaches this backend
through `get_password`.

## Environment variables

| Variable                    | Default | Description |
|------------------------------|---------|--------------|
| `CLOUDSMITH_CLI_PATH`        | (unset) | Explicit path to the `cloudsmith` executable, overriding `PATH` lookup via `shutil.which`. |
| `CLOUDSMITH_KEYRING_TIMEOUT` | `30`    | Timeout, in seconds, for each `cloudsmith` CLI subprocess invocation. |
| `CLOUDSMITH_KEYRING_TTL`     | `300`   | How long, in seconds, a resolved token is cached in-process per host before being re-fetched. Kept short because the credential-helper contract carries no `expires_at`. |
| `CLOUDSMITH_ORG`             | (unset) | Required by the CLI when resolving an organisation's custom domains. All Cloudsmith hosts require a CLI version that supports `domains list`. |

## Priority

The backend declares `priority = 9.9`, which places it ahead of the OS
keychain in keyring's chainer. This looks aggressive for a third-party
backend, but it is safe specifically because this backend returns `None`
for every host it hasn't confirmed is Cloudsmith, so going first can never
mask or misdirect a credential for anything else.

## Troubleshooting

- **`pip install` still prompts for a username/password.** Confirm
  `cloudsmith-keyring` is actually installed in the *same* environment as
  `pip` (`python -m pip show cloudsmith-keyring`), and that `keyring` can
  see it: `python -m keyring --list-backends` should include
  `cloudsmith_keyring.backend.CloudsmithKeyringBackend`.
- **Nothing happens / credentials are never supplied, but no error
  either.** This is the intended fail-silent behaviour. Check, in order:
  the `cloudsmith` CLI is on `PATH` (`which cloudsmith`) or
  `CLOUDSMITH_CLI_PATH` points at a valid executable; `cloudsmith login`
  or another auth method has actually been configured; your CLI version
  supports `domains list` (older CLIs without it are never trusted for any
  host); and that your host appears in `cloudsmith domains list --format
  python --domain-type native_api` (upload) or `cloudsmith domains list
  --domain-type download` (download). For a custom domain, `CLOUDSMITH_ORG`
  must be set (or `oidc_org` configured) so the CLI looks the domain up at
  all.
- **A Cloudsmith host is listed, but still gets no credential.** Check its
  `format` and `domain_type` in the domains output. This backend serves
  Python hosts only, so it deliberately ignores hosts for other ecosystems
  and the generic `upload.cloudsmith.io` endpoint.
- **`uv` returns 401 and never mentions keyring.** Two causes, both
  covered under [`uv`](#uv) above: the keyring provider defaults to
  `disabled`, and the index URL needs a `token@` username before `uv` will
  consult `keyring` at all.
- **It worked, then started failing after a while.** The in-process token
  cache (`CLOUDSMITH_KEYRING_TTL`, default 300s) may be serving a stale
  entry from a long-lived process (e.g. a persistent build worker).
  Lowering the TTL or restarting the process forces a re-fetch.
- **Slow or hanging installs.** Each cache miss shells out to the
  `cloudsmith` CLI, which may itself perform network calls (e.g. an OIDC
  token exchange). Tune `CLOUDSMITH_KEYRING_TIMEOUT` (default 30s) if your
  network is slow, rather than disabling the backend.
- **Debugging.** This package logs through the stdlib `logging` module
  under the `cloudsmith_keyring` logger name; enable it at `DEBUG` level
  to see host-gating and CLI-invocation decisions (tokens themselves are
  never logged).

## Development

The toolchain is defined by [mise](https://mise.jdx.dev/) — Python,
[uv](https://docs.astral.sh/uv/), [prek](https://github.com/j178/prek) as
the hook runner, and gitleaks — with dependencies resolved by `uv` from the
committed `uv.lock`. CI uses the same tools, so a clean local run is a good
predictor of a green build.

```sh
mise install      # fetch the pinned toolchain
mise run test     # run the test suite
mise run lint     # run every check CI runs (prek run --all-files)
mise run hooks    # install the git hooks
mise run secrets  # full gitleaks scan of the tree and history
```

The test suite fakes the subprocess layer entirely — it does not require
the real `cloudsmith` binary or network access.

See [CONTRIBUTING.md](./CONTRIBUTING.md) for more, and
[RELEASING.md](./RELEASING.md) for the release process.

## License

Apache-2.0. See [LICENSE](./LICENSE).
