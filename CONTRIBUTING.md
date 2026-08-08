# Contributing

Thanks for considering a contribution to `cloudsmith-keyring`.

## Design constraints

Two constraints shape most review feedback here.

**It stays tiny.** `keyring>=23.0` is the only runtime dependency. This
package installs into users' project virtualenvs alongside `pip`/`twine`, so
every dependency it adds is a chance to conflict with the resolver of a
project that never asked for it. Anything heavier belongs in
[`cloudsmith-cli`](https://github.com/cloudsmith-io/cloudsmith-cli)
instead, which this package invokes as a subprocess.

**The Python floor tracks pip and twine, not us.** `requires-python` is
`>=3.10`, matching the floor of the current releases of the two tools this
backend exists to serve. Raising it cuts off users whose project virtualenv
runs an older interpreter — a choice they usually did not make freely.
Development happens on the newest Python (see `mise.toml`); that is
deliberately not the floor.

Also note that **widening which hosts this backend trusts is a
security-relevant change**. The backend sits ahead of the OS keychain at
`priority = 9.9`, which is only safe because it returns `None` for every
host it has not confirmed is a validated, enabled, Python-serving
Cloudsmith host.

Please report security issues privately to security@cloudsmith.io rather
than in a public issue.

## Setup

The toolchain is defined by [mise](https://mise.jdx.dev/), which installs
the pinned Python and [uv](https://docs.astral.sh/uv/); `uv` then installs
dependencies from the committed `uv.lock`. Install mise per the
[mise installation docs](https://mise.jdx.dev/getting-started.html), then:

```sh
git clone git@github.com:cloudsmith-labs/cloudsmith-keyring.git
cd cloudsmith-keyring
mise install
mise run install    # uv sync --locked --group dev
```

That creates a `.venv` with the package (editable) plus the `dev` group
(`pytest`, `ruff`). The hook runner and the scanners come from mise, not
pip.

If you would rather not use mise, `uv sync --locked --group dev` works on
any Python in the supported range — mise is how CI resolves interpreters,
not a hard requirement for contributors.

## Running tests

```sh
mise run test          # or: uv run pytest
```

The suite fakes the subprocess layer entirely — it does not invoke a real
`cloudsmith` binary or touch the network, so it runs identically in CI and
locally.

`tests/test_domains_contract.py` is the exception in spirit: it runs offline
too, but asserts against `tests/fixtures/domains_list_upload_v1.json` and
`tests/fixtures/domains_list_download_v1.json`, which are verbatim recorded
output from real `cloudsmith domains list` runs. Refresh them when the
CLI's contract changes:

```sh
cloudsmith domains list --format python --domain-type native_api \
    | python -m json.tool > tests/fixtures/domains_list_upload_v1.json
cloudsmith domains list --domain-type download \
    | python -m json.tool > tests/fixtures/domains_list_download_v1.json
```

## Linting and formatting

[ruff](https://docs.astral.sh/ruff/) handles linting and formatting,
[zizmor](https://docs.zizmor.sh/) audits the GitHub Actions workflows, and
[gitleaks](https://github.com/gitleaks/gitleaks) scans for secrets. All of
it runs through [prek](https://github.com/j178/prek), a drop-in replacement
for pre-commit that reads the same `.pre-commit-config.yaml`:

```sh
mise run lint          # prek run --all-files
mise run hooks         # prek install — run the checks before each commit
```

CI runs exactly `prek run --all-files` in its lint job, so a clean local
run is a good predictor of CI passing.

`pre-commit` itself still works against the same config if you prefer it,
but prek is what mise installs and what CI runs.

### Secret scanning has a sharp edge

The `gitleaks` hook scans **staged** content only, so it guards commits but
reads nothing under `prek run --all-files`. Do not read a green lint job as
"no secrets committed" — the Security workflow runs the full scans, and you
can run them locally with:

```sh
mise run secrets       # gitleaks over the working tree and the full history
```

## Pull requests

- Keep changes focused; unrelated formatting or refactors make review
  harder.
- Add or update tests for any behaviour change — the suite is the contract
  this package's silent-failure guarantees are held to.
- Update `CHANGELOG.md` under an `[Unreleased]` heading for any
  user-visible change.
