# Releasing

[release-please](https://github.com/googleapis/release-please) automates
releases. This package installs directly from GitHub:
`pip install git+https://github.com/cloudsmith-labs/cloudsmith-keyring.git@vX.Y.Z`.
A release is a tag and a GitHub release. There is no upload to a package
index.

## How a release happens

1. Pull requests merge to `main` with
   [Conventional Commits](https://www.conventionalcommits.org/) titles. See
   [CONTRIBUTING.md](./CONTRIBUTING.md#commit-messages-and-pull-requests).
2. On each push to `main`, the Release workflow opens or updates a release
   pull request named `chore(main): release X.Y.Z`. It sets the version in
   `pyproject.toml` and adds the release notes to `CHANGELOG.md`.
3. Review the release pull request, then merge it.
4. The Release workflow creates the `vX.Y.Z` tag and the GitHub release.
5. Confirm the release on the
   [Releases](https://github.com/cloudsmith-labs/cloudsmith-keyring/releases)
   page.

## Set up GitHub

1. Add the `CLOUDSMITH_BOT_PR_TOKEN` secret. release-please opens the release
   pull request with this token, so CI runs on it. Without the secret,
   release-please uses the default token, and CI does not run on the release
   pull request. The Dependabot auto-merge workflow uses the same token.
2. If you remove the secret, select **Allow GitHub Actions to create and
   approve pull requests** in **Settings > Actions > General**. The default
   token needs this setting to open the release pull request.

## Version scheme

This project follows [Semantic Versioning](https://semver.org/). A `feat`
bumps the minor version, and a `fix` bumps the patch version. Before 1.0, a
breaking change bumps the minor version instead of the major version.
