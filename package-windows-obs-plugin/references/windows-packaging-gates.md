# Windows Packaging Gates

## Portable layout

Use one plugin root containing:

- `bin/64bit/<plugin>.dll`
- `data/` with runtime assets and locale files
- license and asset notices
- minimal installation/usage documentation

Reject developer-only files, credentials, private keys, debug logs, caches, tests, source, and nested release leftovers.

## Installer

- Default standard installations to the shared OBS plugin location when that is the documented target.
- Stop or block while `obs64.exe` is running.
- Preserve Apps and Features uninstall registration in production.
- Support an explicit per-user command-line override only when needed for disposable CI tests.
- Test the exact generated installer, not a manually copied approximation.

## Evidence

Record the actual checked-out commit from `git rev-parse HEAD`, DLL SHA-256, portable ZIP SHA-256, installer SHA-256, architecture result, package manifest, installer exit code, installed-file comparison, uninstaller exit code, and removal result. A compiler success alone proves none of the installer gates. GitHub pull-request workflows commonly expose a synthetic merge SHA in `GITHUB_SHA`; either explicitly check out the pull-request head or preserve the merge SHA as a separate identity. Do not claim branch-head provenance for bytes built from an unrecorded merge ref.

Upload the installer log, uninstall log, installed-versus-package SHA-256 comparison, and remaining-file scan as CI evidence even when the lifecycle fails. Test `/DIR=` or an equivalent disposable override without weakening the production default. Separately inspect or exercise the documented `C:\ProgramData\obs-studio\plugins\<plugin>` behavior because a directory override alone does not prove the standard destination. Treat registry/UAC denial as an environment restriction only when logs identify the attempted registry action and rollback; never record it as a lifecycle pass.
