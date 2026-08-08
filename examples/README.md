# Examples

Runnable, end-to-end demonstrations of `cloudsmith-keyring` authenticating
[`pip`](./pip/), [`twine`](./twine/), [`uv`](./uv/), and
[`pip-tools`](./pip-tools/) against a real Cloudsmith repository — no
credentials in a URL, a config file, or an environment variable that any of
those tools see directly.

They all target the same demo repository by default:

- Org: `iduffy-demo`
- Repository: `cloudsmith-keyring`

Set `CLOUDSMITH_ORG` and `CLOUDSMITH_REPO` to point any of them at a
repository you control instead. Each `mise.toml` substitutes both into the
example's config at run time, so nothing in `pip/`, `twine/`, `uv/`, or
`pip-tools/` needs editing by hand.

[`example-package/`](./example-package/) is the throwaway package the
`twine` example uploads and the `pip`/`uv`/`pip-tools` examples install back
down.

[`.github/workflows/examples.yml`](../.github/workflows/examples.yml) runs
all four on every push and pull request, authenticating the `cloudsmith` CLI
via GitHub Actions OIDC — no stored secret. It exchanges the workflow's
OIDC token for a Cloudsmith one using `CLOUDSMITH_ORG` and
`CLOUDSMITH_SERVICE_SLUG`, which requires both the `id-token: write`
permission (granted per job) and a Cloudsmith service account already
configured to trust this repository.

## Running an example

Each of `pip/`, `twine/`, `uv/`, and `pip-tools/` has its own `mise.toml`:
running any `mise run <task>` there installs Python, `uv`, and a throwaway
venv with `cloudsmith-keyring` and the `cloudsmith` CLI — nothing needs
installing by hand, and nothing touches your own environment. [`mise`](https://mise.jdx.dev/)
itself is the only prerequisite. From any example directory:

```sh
mise tasks     # see what's runnable
mise run <task>
```

**Temporary:** every example pins `cloudsmith-cli` to the branch that adds
`domains list` (see each directory's `mise.toml`), since this backend needs
that command to confirm a host is Cloudsmith-served and it hasn't shipped
in a release yet.

1. `cloudsmith login`, or `CLOUDSMITH_API_KEY` in the environment. (CI uses
   OIDC instead — see below — which only auto-discovers in a supported CI
   environment, not a local shell.)
2. `CLOUDSMITH_ORG` set, so the CLI can resolve the org's domains without
   relying on `oidc_org` being configured. Defaults to `iduffy-demo` in the
   example config if unset; set `CLOUDSMITH_REPO` alongside it to run
   against a different org/repository entirely.

None of the examples put a token in a file, a URL, or a shell history —
that's the entire point of this package.
