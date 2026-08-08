---
name: Bug Report
about: Report a bug or unexpected behavior
title: "[BUG] "
labels: bug
---

## Description

<!-- A clear and concise description of what the bug is -->

## Steps to Reproduce

1.
2.
3.

## Expected Behavior

<!-- What you expected to happen -->

## Actual Behavior

<!-- What actually happened -->

## Environment

- **OS**: <!-- e.g. macOS 15, Ubuntu 24.04, Windows 11 -->
- **Python version**: <!-- python --version, from the SAME env as pip/twine -->
- **cloudsmith-keyring version**: <!-- python -m pip show cloudsmith-keyring -->
- **Cloudsmith CLI version**: <!-- cloudsmith --version -->
- **Tool involved**: <!-- pip / twine / uv / other, and its version -->

## Diagnostics

<!--
Most reports come down to one of these. Please paste the output:

  1. Is the backend visible to keyring, in the same environment as pip/twine?
       python -m keyring --list-backends

  2. Which hosts does the CLI report as usable?
       cloudsmith domains list --format python --domain-type native_api
       cloudsmith domains list --domain-type download

  3. What is the backend deciding? (tokens are never logged)
       PYTHONWARNINGS=ignore python -c "
       import logging; logging.basicConfig(level=logging.DEBUG)
       import keyring; print(keyring.get_credential('<your index or upload URL>', None))"
-->

```
paste output here
```

## Additional Context

<!-- Add any other context about the problem here -->
