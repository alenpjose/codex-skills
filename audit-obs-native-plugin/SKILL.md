---
name: audit-obs-native-plugin
description: Audit native OBS Studio plugins for API contract compatibility, source callback registration, per-instance isolation, C++ lifetime and thread safety, rendering discipline, teardown, CMake configuration, and optional Aitum integration. Use for repository audits, OBS version upgrades, module-load failures, or suspected source/output ownership defects.
---

# Audit OBS Native Plugin

## Workflow

1. Identify the pinned OBS version, supported platforms, plugin type, and optional integrations.
2. Read source registration, create/destroy/update/save/load/tick/render callbacks, build files, and packaging entrypoints.
3. Run `scripts/check_obs_contracts.py --source <repo-or-file> --obs-version <version> --headers <versioned-OBS-source-root>` as a heuristic first pass. The header root must contain `libobs/obs-source.h`, `libobs/obs.h`, and the OBS root `CMakeLists.txt`, and its version marker must match `--obs-version`; otherwise treat compatibility context as unverified and fail the gate. Prefer a repository or complete translation unit; classify findings from isolated snippets as incomplete-context hypotheses until their surrounding source is available.
4. Validate every candidate against the pinned OBS headers or official documentation.
5. Trace source, output, signal, hotkey, graphics, task, and thread lifetimes through teardown.
6. Test separate source instances and actual module loading before claiming runtime compatibility.

Read `references/obs32-source-contracts.md` for registration and rendering checks. Read `references/aitum-output-ownership.md` only when Aitum or another procedure-based output provider is in scope.

## Finding Standard

Classify findings as:

- `confirmed`: directly demonstrated by source/API contract, compilation, or runtime evidence.
- `probable`: strong static evidence but runtime confirmation remains.
- `hypothesis`: heuristic signal requiring targeted validation.

For every finding include the affected path/symbol, violated invariant, observable impact, and minimum validation needed. Never report heuristic output as a confirmed vulnerability or defect without inspection.

The bundled checker targets OBS 32 source-registration patterns. For another OBS major version, use it only for candidate discovery and validate every result against that version's pinned headers and official documentation.

## Required Audit Areas

- Match advertised `obs_source_info` flags and type to all callbacks required by the pinned OBS version.
- Keep mutable settings, timer state, hotkeys, output connections, and child sources on the source instance rather than process globals.
- Balance OBS addref/get calls with release calls on every success, failure, reconnect, and teardown path.
- Disconnect signals before releasing the object that owns the signal handler.
- Restrict graphics API and child rendering work to valid graphics/render contexts.
- Marshal provider/UI operations to the required task thread and make queued work teardown-safe.
- Avoid holding instance mutexes while calling external callbacks that may re-enter the plugin.
- Verify save/load semantics and restart behavior, not only default settings.
- Treat a successful build as insufficient proof that the module registers or loads.
