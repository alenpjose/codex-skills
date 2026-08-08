---
name: release-curious-bipedal-overlay
description: Coordinate audit, runtime, visual, packaging, evidence, GitHub draft-PR, and artifact-delivery gates for the Curious Bipedal native OBS Overlay. Use only for this repository's Windows x64 releases, validation reports, user test checklists, or release-candidate decisions.
---

# Release Curious Bipedal Overlay

## Dependencies

Use these staged skills together:

- `$audit-obs-native-plugin`
- `$test-obs-aitum-runtime`
- `$package-windows-obs-plugin`
- `$verify-overlay-visuals`
- `$validate-release-evidence`
- `$gh-release-package-review`

Read `references/project-requirements.md` and `references/acceptance-matrix.json` before making changes or accepting evidence.

## Workflow

Begin in read-only assessment mode. Do not commit, push, install, uninstall, launch applications, alter OBS profiles, or publish artifacts unless the user has authorized that mutation in the current task. Keep release assessment available even when writes are not authorized.

1. Resolve the `alenpjose/curious-bipedal-obs-overlay` repository and confirm the feature branch and draft PR.
2. Audit the entire runtime and packaging diff against OBS Studio 32.1.2 and the Aitum procedure contract.
3. Verify supplied brand assets by repository path and hash; do not copy or relicense them into this skill.
4. Build Windows x64 DLL, portable ZIP, and Inno installer through the repository workflow.
5. Run the isolated OBS/Aitum matrix with two newly created sources.
6. Validate both canvases and the approved 80% default layout, including the secondary-text regression.
7. Exercise installation, restart, persistence, hotkeys, timer controls, uninstallation, and post-uninstall source behavior.
8. Review package contents and test the user-facing artifact download route.
9. Run the evidence gate with the canonical acceptance matrix, run artifact delivery verification against the downloaded outer ZIP, and generate the release summary from both verified outputs with `scripts/build_release_report.py`.
10. Update the draft PR. Do not merge or push directly to `main` without explicit authorization.

## Completion Standard

Do not describe the plugin or installer as validated until the final runtime DLL has loaded in real OBS with Aitum installed and every required claim has sufficient evidence. If only code, compilation, or CI packaging is complete, state that limitation plainly.

Produce:

- final commit and draft PR link
- Actions run and artifact identity
- artifact digest and inner checksums
- runtime environment and result matrix
- visual evidence for both canvases
- installer/uninstaller evidence
- user test checklist and known limitations

Generate the report only from `validate_evidence.py --output`, `verify_artifact_delivery.py --output`, the canonical matrix, and small project metadata using `build_release_report.py --evidence <json> --delivery <json> --metadata <json> --requirements-schema references/acceptance-matrix.json`. The reporter independently recomputes canonical coverage, evidence counts, verified-artifact coverage, delivery checksums, connector blob matches, commit identity, outer digest, and raw-DLL identity; it rejects caller-authored `status: validated` JSON.
