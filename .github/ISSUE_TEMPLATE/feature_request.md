---
name: Feature Request
about: Suggest a new feature or improvement
title: "[FEATURE] "
labels: enhancement
---

## Problem

<!-- What are you trying to do that is difficult or impossible today? -->

## Proposed Solution

<!-- What you would like to see happen -->

## Alternatives Considered

<!-- Other approaches you have thought about, and why they fall short -->

## Scope Check

<!--
This package is deliberately tiny: `keyring` is its only runtime dependency,
because it has to install into users' project virtualenvs alongside pip and
twine without risking resolver conflicts. Anything needing HTTP clients, the
Cloudsmith SDK, or extra dependencies belongs in cloudsmith-cli, which this
package invokes as a subprocess.

If your request would add a runtime dependency, say why it cannot live in
the CLI instead.
-->

## Additional Context

<!-- Anything else that would help -->
