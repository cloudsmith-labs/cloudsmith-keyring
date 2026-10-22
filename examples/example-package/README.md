# cloudsmith-keyring-example

A trivial, throwaway package that exists only for the `examples/`
walkthroughs. The `twine` example builds it and uploads a new version to a
Cloudsmith repository. The `pip`, `uv`, and `pip-tools` examples install its
version 0.1.0 from the same repository. Together they show that
`cloudsmith-keyring` supplies credentials for all four tools without any of
them touching a secret directly.

The package has no relation to `cloudsmith-keyring` itself beyond being used
to demonstrate it.
