# Releasing

This package installs directly from GitHub:
`pip install git+https://github.com/cloudsmith-labs/cloudsmith-keyring.git@vX.Y.Z`.
A release is a tagged commit and a GitHub Release for changelog visibility;
there is no package-index upload.

## Release steps

1. Update `CHANGELOG.md`: move `[Unreleased]` entries under a new
   `## [X.Y.Z] - YYYY-MM-DD` heading, and add the corresponding link
   reference at the bottom of the file.
2. Bump the `version` in `pyproject.toml` to match.
3. Commit those changes (e.g. `chore: release vX.Y.Z`) and merge to `main`.
4. Tag the resulting commit and push the tag:

   ```sh
   git tag -a vX.Y.Z -m "vX.Y.Z"
   git push origin vX.Y.Z
   ```

5. Pushing the tag triggers `.github/workflows/release.yml`, which verifies
   the tag matches `pyproject.toml`'s version and creates a GitHub Release.
6. Confirm the release on the repository's
   [Releases](https://github.com/cloudsmith-labs/cloudsmith-keyring/releases)
   page.

## Version scheme

This project follows [Semantic Versioning](https://semver.org/): breaking
changes to the public backend behaviour or environment-variable contract
bump the major version; new, backward-compatible behaviour bumps the
minor version; fixes bump the patch version.
