# Codex Skills

Private source repository for reusable Codex skills developed and forward-tested for native OBS plugin engineering and release validation.

Each skill is self-contained. Its `SKILL.md` defines when it should trigger and how to use its bundled scripts and references. Project-specific branding remains in the source project and is referenced by path and hash rather than copied here.

## Skill catalog

| Skill | Use case |
| --- | --- |
| [`validate-release-evidence`](validate-release-evidence/SKILL.md) | Convert release requirements into a canonical evidence matrix and reject completion claims that exceed the available build, runtime, or user-acceptance evidence. |
| [`audit-obs-native-plugin`](audit-obs-native-plugin/SKILL.md) | Audit OBS source callbacks, instance isolation, ownership, teardown, rendering, build configuration, and pinned API compatibility. |
| [`test-obs-aitum-runtime`](test-obs-aitum-runtime/SKILL.md) | Run disposable Windows smoke tests for OBS, Aitum Multistream, Aitum Vertical, independent sources, timer routing, controls, hotkeys, persistence, and teardown. |
| [`package-windows-obs-plugin`](package-windows-obs-plugin/SKILL.md) | Validate Windows x64 DLLs, portable layouts, checksums, Inno Setup packages, installed hashes, uninstallers, and clean removal. |
| [`verify-overlay-visuals`](verify-overlay-visuals/SKILL.md) | Check transparent bounds, detached logo elements, clipping, rounded panels, dynamic width, text hierarchy, and legibility across broadcast canvases. |
| [`release-curious-bipedal-overlay`](release-curious-bipedal-overlay/SKILL.md) | Coordinate the complete Curious Bipedal OBS Overlay release gate for OBS 32.1.2 and the supported Aitum versions. |
| [`gh-release-package-review`](gh-release-package-review/SKILL.md) | Review release package contents and verify GitHub artifact existence, identity, checksums, nested ZIP delivery, and connector-upload integrity. |

## Validation policy

- Keep source review, successful compilation, simulated runtime, real runtime, and user acceptance as distinct evidence levels.
- Do not claim a plugin or installer is validated until the final binary passes the required real-host tests.
- Keep mutation-capable scripts dry-run or read-only by default.
- Validate every skill with the official `quick_validate.py` before publishing changes.
- Forward-test complex gates against representative passing, failing, and malformed fixtures.

## Repository layout

Every top-level skill directory contains:

- `SKILL.md` for trigger metadata and workflow instructions.
- `agents/openai.yaml` for the Codex UI description and default prompt.
- `scripts/` for deterministic validators or test orchestration, when required.
- `references/` for schemas and detailed domain guidance, when required.

The repository intentionally contains no plugin binaries, OBS profiles, production credentials, captured user data, or Curious Bipedal artwork.
