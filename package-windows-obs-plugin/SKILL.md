---
name: package-windows-obs-plugin
description: Build and verify Windows x64 distributions for native OBS Studio plugins, including PE architecture, portable ZIP contents, runtime assets, checksums, Inno Setup installers, disposable installation, installed-file hashes, generated uninstallers, and cleanup. Use for release packaging or Windows CI hardening.
---

# Package Windows OBS Plugin

## Workflow

1. Pin the OBS source/SDK version and dependency bundle before configuring CMake.
   In pull-request CI, check out the pull-request head SHA explicitly or record the checked-out merge SHA as a distinct build identity. Never label merge-ref bytes with the branch-head SHA.
2. Build Release x64 and install into a clean staging prefix.
3. Run `scripts/Test-PeMachine.ps1` on every plugin DLL.
4. Create the portable archive from the installed runtime tree, then run `scripts/Test-ObsPackage.ps1`.
5. Compile the Inno Setup installer from the same runtime tree.
6. Preview `scripts/Test-InnoLifecycle.ps1`; execute it with `-Apply` on a disposable Windows host or CI runner.
7. Generate checksums with `scripts/Write-Checksums.ps1` and upload only after every gate passes.

Read `references/windows-packaging-gates.md` before changing package layout or installer privilege behavior.

## Required Gates

- Verify PE machine `0x8664` for the plugin DLL. Do not infer x64 from a directory name.
- Include only runtime DLLs, assets, locales, license/notices, and minimal setup documentation.
- Exclude PDBs unless explicitly requested, source, tests, caches, credentials, local configuration, and build tooling.
- Compare every installed runtime file with the source package by SHA-256.
- Require a generated uninstaller and verify runtime removal with OBS closed.
- Preserve install/uninstall logs and the installed-file hash manifest as CI artifacts. Require both the disposable directory-override lifecycle and a documented check of the standard shared ProgramData destination.
- Record `git rev-parse HEAD` from the checked-out worktree in lifecycle evidence and require it to match the release identity used by downstream gates.
- Keep standard shared OBS installation behavior separate from portable OBS instructions.
- Document unsigned binaries and SmartScreen behavior when code signing is absent.

Treat registry/UAC access denied in a managed sandbox as an environment restriction only when logs prove the installer selected the correct registry hive and copied files successfully before rollback. Move the exact installer lifecycle test to a Windows runner with appropriate registry access rather than weakening production uninstall registration.
