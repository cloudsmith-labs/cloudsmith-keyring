# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- An `examples/` directory demonstrating `pip`, `twine`, `uv`, and
  `pip-tools` authenticating to a Cloudsmith repository through
  `cloudsmith-keyring`, exercised on every push and pull request by the
  `Examples` GitHub Actions workflow. Each example targets a demo repository
  by default but reads `CLOUDSMITH_ORG`/`CLOUDSMITH_REPO` to target a
  different one, substituted into its config at run time so nothing needs
  editing by hand.

### Changed

- Host gating now uses `cloudsmith domains list --format python
  --domain-type native_api` (the upload host) and `cloudsmith domains list
  --domain-type download` (the download CDN) instead of the removed
  `cloudsmith credential-helper domains`. The CLI itself now applies the
  enabled/validated/format filtering that this package used to apply
  client-side.

## [0.1.0] - 2026-07-31

Initial release.

### Added

- `cloudsmith-keyring`, a [keyring](https://github.com/jaraco/keyring)
  backend that authenticates `pip install` and `twine upload` to Cloudsmith
  by shelling out to the `cloudsmith` CLI's credential helper.
- Host gating driven entirely by `cloudsmith credential-helper domains`, the
  single authoritative source for which hosts Cloudsmith can authenticate.
  Nothing is hardcoded: the built-in Cloudsmith service hosts and an
  organisation's validated custom domains both come from that one command,
  so this package cannot drift out of sync with the platform. The lookup is
  performed at most once per process.
- Gating narrowed to the hosts `pip` and `twine` actually use: a host whose
  `format` is `python`, or whose `domain_type` is `download`. Other genuine
  Cloudsmith hosts — `npm.cloudsmith.io`, `docker.cloudsmith.io`,
  `maven.cloudsmith.io`, the generic `upload.cloudsmith.io` endpoint — are
  left to the next keyring backend. This matters because the backend sits
  ahead of the OS keychain at `priority = 9.9`, where claiming another
  ecosystem's host would shadow a credential the user stored deliberately.
- A version gate on both credential-helper contracts, so an unrecognised
  response shape confirms no hosts and yields no credential rather than
  being guessed at.
- Silent, fail-safe degradation when the `cloudsmith` CLI is missing, not
  authenticated, or produces unusable output. A user without the CLI
  installed sees no behaviour change at all.
- In-process, per-host token caching with a configurable TTL.
- Configuration via `CLOUDSMITH_CLI_PATH`, `CLOUDSMITH_KEYRING_TIMEOUT`, and
  `CLOUDSMITH_KEYRING_TTL`.
- Contract tests against recorded real output of `credential-helper domains`,
  so a change to the CLI's response shape fails the suite.

### Notes on the supported Python range

`requires-python` is `>=3.10`, matching the floor of current `pip` and
`twine` — the tools this backend exists to serve. Development uses the
newest release (see `mise.toml`); CI covers 3.10 through 3.14.

[0.1.0]: https://github.com/cloudsmith-labs/cloudsmith-keyring/releases/tag/v0.1.0
