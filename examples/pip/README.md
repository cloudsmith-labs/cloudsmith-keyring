# pip example

Installs [`cloudsmith-keyring-example`](../example-package/) from the
`iduffy-demo`/`cloudsmith-keyring` Cloudsmith repository using plain
`pip install` — no `--extra-index-url` credentials, no `pip.conf`, no
`~/.netrc`.

`requirements.txt` carries the index URL with the fixed `token` username
(safe to commit — see the main [README](../../README.md#uv)); the password
comes from `keyring` at install time.

```sh
pip install cloudsmith-keyring keyring
pip install "git+https://github.com/cloudsmith-io/cloudsmith-cli.git@custom-domains"  # see ../README.md
export CLOUDSMITH_ORG=iduffy-demo

pip install -r requirements.txt
python -c "import cloudsmith_keyring_example; print(cloudsmith_keyring_example.greet())"
```

See [`../README.md`](../README.md) for the full prerequisites.
