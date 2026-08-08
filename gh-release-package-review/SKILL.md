---
name: gh-release-package-review
description: Review GitHub release package contents before creating, uploading, zipping, or attaching release artifacts. Use when deciding which files belong in a GitHub Release, building release archives, drafting release asset checklists, excluding developer-only files, validating dist/build outputs, or pushing back before packaging unnecessary source, config, credentials, tests, local tooling, dependency caches, or other non-user-facing files.
---

# Gh Release Package Review

## Overview

Use this skill as a release contents gate. Classify files by release value, identify risky or unnecessary developer files, and confirm ambiguous inclusions with the user before packaging.

Prefer a small, intentional release artifact over a broad repository dump.

## Core Workflow

1. Identify the release target: app, library, plugin, binary, package, docs bundle, installer, source archive, or generated asset.
2. Inspect repository conventions before deciding: release scripts, package manifests, CI workflows, build directories, changelogs, existing release notes, `.gitignore`, `.npmignore`, packaging config, installer config, or prior release artifacts.
3. Build a candidate inclusion list and an explicit exclusion list.
4. Push back on anything that looks unnecessary, local-only, credential-bearing, oversized, reproducible from source, or useful only to developers.
5. Ask the user to confirm ambiguous or policy-sensitive files before packaging.
6. Package only confirmed files, then report what was included, excluded, and still uncertain.
7. Verify artifact delivery and connector-upload integrity before presenting the release as downloadable.

Read `references/artifact-delivery.md` when GitHub Actions artifacts, connector uploads, nested archives, 404 responses, or GitHub Release assets are involved. Run `scripts/verify_artifact_delivery.py --manifest <path>` when structured artifact metadata is available.

## Default Release Contents

Usually include:

- Compiled binaries, installers, signed packages, generated archives, or published package outputs.
- Runtime assets needed by the user-facing artifact.
- License, notices, third-party acknowledgments, release notes, changelog excerpts, and checksums when expected.
- Minimal setup or usage docs for the released artifact.
- Source files only when the release type explicitly requires a source distribution.

Usually exclude unless the user confirms:

- `.git/`, `.github/`, editor settings, local workspace files, debug logs, temp files, caches, screenshots, scratch artifacts, and generated test output.
- Secrets, tokens, private keys, `.env*`, local certificates, credentials, signing material, database dumps, and production config.
- Dependency directories such as `node_modules/`, virtualenvs, package caches, build caches, and tool caches.
- Tests, fixtures, mocks, coverage reports, development docs, benchmark output, and CI-only scripts.
- Raw source, build scripts, config files, lockfiles, and manifests when the release artifact is a binary/installer and those files are not needed at runtime.
- OS noise such as `.DS_Store`, `Thumbs.db`, desktop metadata, and archive leftovers.

## Confirmation Rules

Do not silently include ambiguous files. Ask a concise confirmation question when a file is:

- Developer-facing but possibly useful to advanced users, such as examples, templates, migration scripts, SDK headers, debug symbols, or source maps.
- Large enough to materially affect release size.
- Reproducible from source but expensive or inconvenient for users to build.
- A config file that may contain environment-specific values.
- A generated file whose provenance is unclear.
- Required only for one platform, package manager, deployment target, or customer.

When pushing back, give the reason and a recommended default:

```text
I recommend excluding `coverage/` from the release asset because it is developer test output and can be regenerated. Include it only if this release is meant to publish QA evidence. Should I exclude it?
```

## Output Format

Before packaging or uploading, provide a compact review:

- Include: files or globs, with short reasons.
- Exclude: files or globs, with short reasons.
- Confirm: ambiguous files that need user approval.
- Risk checks: secrets, credentials, size, platform coverage, reproducibility, and license/notice requirements.

After packaging, report:

- Artifact path and size.
- Final included top-level files.
- Important exclusions.
- Any unresolved assumptions.

## Artifact Delivery Gate

- Confirm the artifact exists, is not expired, belongs to the expected run and head commit, and has a recorded digest.
- Test the user-facing download route from the intended authentication context. An API success does not prove the UI link works for the user.
- Explain that GitHub Actions downloads an outer artifact ZIP. Identify the installer, portable ZIP, raw binary, and checksums inside it.
- Treat a 404, authentication mismatch, expired link, or untested route as unresolved delivery.
- Prefer a GitHub prerelease or release asset when a stable, direct file download is required; obtain authorization before publishing a release.
- For connected-app Git writes, compare the returned remote Git blob SHA with `git hash-object <file>` before creating a tree or moving a ref. Re-upload in bounded chunks if transport output truncation is possible.

## Practical Checks

Use local tooling where available:

- Inspect `git status --short` to avoid packaging unrelated local changes by accident. In a detached artifact directory, proceed with filesystem/archive inspection and explicitly mark Git context unavailable.
- Use `git ls-files` for tracked files and filesystem listing for generated release outputs.
- Prefer project release scripts over inventing package contents, then audit their output before upload.
- Open existing archives with listing commands before publishing.
- Search for likely secrets before packaging: `.env`, `secret`, `token`, `key`, `pem`, `p12`, `credentials`, `password`.

Never upload or attach a release artifact until the requested release contents are either clearly conventional or explicitly confirmed by the user.
