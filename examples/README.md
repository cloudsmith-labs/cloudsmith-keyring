# Examples

Runnable, end-to-end demonstrations of `cloudsmith-keyring` authenticating
[`pip`](./pip/), [`twine`](./twine/), [`uv`](./uv/), and
[`pip-tools`](./pip-tools/) against a real Cloudsmith repository — no
credentials in a URL, a config file, or an environment variable that any of
those tools see directly.

They all target the same demo repository:

- Org: `iduffy-demo`
- Repository: `cloudsmith-keyring`

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

## Prerequisites

Every example assumes:

1. The [`cloudsmith` CLI](https://pypi.org/project/cloudsmith-cli/) is
   installed and authenticated. Locally, that means `cloudsmith login` or
   `CLOUDSMITH_API_KEY` in the environment — OIDC auto-discovery only
   detects supported CI environments (GitHub Actions among them), not a
   local shell.

   **Temporary:** the `domains list` command this backend relies on to
   confirm a host is Cloudsmith-served has not shipped in a release yet.
   Until it does, install the CLI from the branch that adds it:

   ```sh
   pip install "git+https://github.com/cloudsmith-io/cloudsmith-cli.git@custom-domains"
   ```

2. `CLOUDSMITH_ORG=iduffy-demo` is set, so the CLI can resolve the org's
   domains without relying on `oidc_org` being configured.
3. `cloudsmith-keyring` itself is installed in the *same* environment as
   the tool being demonstrated (`pip install -e .` from the repo root, or
   the published package once released).

None of the examples put a token in a file, a URL, or a shell history —
that's the entire point of this package.
