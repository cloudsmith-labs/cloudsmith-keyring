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
   and returns the token as the password (with username `token`).
4. The resolved token is cached in-process for a short TTL so that pip's
   repeated per-request keyring lookups don't each trigger a fresh CLI
   invocation.

If the `cloudsmith` CLI is not installed, is not on `PATH`, exits non-zero,
times out, or produces output that can't be parsed, the backend returns
`None` silently. **A user without the CLI installed observes no behaviour
change at all**.

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
| `CLOUDSMITH_WORKSPACE`       | (unset) | Workspace slug used by CLI 1.26.0 or later when resolving custom domains. |

## Priority

The backend declares `priority = 9.9`, which places it ahead of the OS
keychain in keyring's chainer. This looks aggressive for a third-party
backend, but it is safe specifically because this backend returns `None`
for every host it hasn't confirmed is Cloudsmith, so going first can never
mask or misdirect a credential for anything else.

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
