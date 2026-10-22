# Changelog

## 0.1.0 (2026-10-22)


### Features

* authenticate pip, twine and uv to Cloudsmith with a keyring backend that calls the cloudsmith CLI ([2d121f4](https://github.com/cloudsmith-labs/cloudsmith-keyring/commit/2d121f4b9a122ebe3c4cf8e3524666c82b2a8a4d))
* cache the token of each host in the process, for the TTL that CLOUDSMITH_KEYRING_TTL sets ([2d121f4](https://github.com/cloudsmith-labs/cloudsmith-keyring/commit/2d121f4b9a122ebe3c4cf8e3524666c82b2a8a4d))
* claim only the Python upload and download hosts that `cloudsmith domains list` reports ([2d121f4](https://github.com/cloudsmith-labs/cloudsmith-keyring/commit/2d121f4b9a122ebe3c4cf8e3524666c82b2a8a4d))
* give no credential, and no error, when the cloudsmith CLI is missing, not authenticated or gives unusable output ([2d121f4](https://github.com/cloudsmith-labs/cloudsmith-keyring/commit/2d121f4b9a122ebe3c4cf8e3524666c82b2a8a4d))
* set the CLI path and the CLI timeout with CLOUDSMITH_CLI_PATH and CLOUDSMITH_KEYRING_TIMEOUT ([2d121f4](https://github.com/cloudsmith-labs/cloudsmith-keyring/commit/2d121f4b9a122ebe3c4cf8e3524666c82b2a8a4d))


### Bug Fixes

* **examples:** install a fixed example package version ([#13](https://github.com/cloudsmith-labs/cloudsmith-keyring/issues/13)) ([3d3ed01](https://github.com/cloudsmith-labs/cloudsmith-keyring/commit/3d3ed015167c85b29cc9b5f2f19b5953b190f998))
* **examples:** install the released cloudsmith-cli ([#9](https://github.com/cloudsmith-labs/cloudsmith-keyring/issues/9)) ([dfcb43e](https://github.com/cloudsmith-labs/cloudsmith-keyring/commit/dfcb43e6183597888b3be746eabc052598540883))


### Documentation

* focus custom-domain guidance on Workspace ([#5](https://github.com/cloudsmith-labs/cloudsmith-keyring/issues/5)) ([0510d95](https://github.com/cloudsmith-labs/cloudsmith-keyring/commit/0510d9561645e35fce943bf5d82aff93d9a11995))
* prefer CLOUDSMITH_WORKSPACE ([#4](https://github.com/cloudsmith-labs/cloudsmith-keyring/issues/4)) ([289a6a8](https://github.com/cloudsmith-labs/cloudsmith-keyring/commit/289a6a8d7e36e5439ad00aa552181f9df4d98eaa))
