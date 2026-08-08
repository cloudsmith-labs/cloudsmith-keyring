# cloudsmith-keyring-example

A trivial, throwaway package with no purpose beyond existing: the
`examples/` walkthroughs build it, upload it to a Cloudsmith repository
with `twine`, and then install it back down with `pip`, `uv`, and
`pip-compile` to prove `cloudsmith-keyring` supplies credentials for all
four tools without any of them touching a secret directly.

It is not published anywhere permanent and has no relation to
`cloudsmith-keyring` itself beyond being used to demonstrate it.
