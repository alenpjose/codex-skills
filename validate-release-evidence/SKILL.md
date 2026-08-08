---
name: validate-release-evidence
description: Convert release requirements into an evidence matrix and reject unsupported completion claims. Use when validating whether software, plugins, installers, runtime behavior, persistence, visuals, or downloadable artifacts are genuinely complete rather than merely implemented or compiled.
---

# Validate Release Evidence

## Workflow

1. Rewrite each requested outcome as one independently testable claim.
2. Assign the minimum evidence level required by the claim.
3. Record the evidence artifact, observed result, environment, and exact build identity.
4. Run `scripts/validate_evidence.py --manifest <path>`.
5. Report passed, missing, failed, and unsupported claims separately.
6. Describe a release as validated only when every required claim passes at its required level.

Read `references/evidence-manifest.md` before creating or reviewing a manifest.

## Evidence Levels

Use the weakest level only when it genuinely proves the claim:

1. `static_inspection`: source, configuration, or package structure review.
2. `build`: successful compilation or packaging of an identified commit.
3. `simulated_runtime`: mocked or synthetic execution.
4. `real_runtime`: execution with the real application or integration binaries.
5. `user_acceptance`: user confirmation from the intended environment.

Do not substitute a lower level for a higher requirement. Compilation cannot prove that a DLL loads. Installer creation cannot prove installation or uninstallation. Source inspection cannot prove source-instance isolation, output routing, persistence, or visual correctness.

## Integrity Rules

- Tie evidence to a commit SHA, artifact digest, or local binary hash.
- Treat evidence from an older binary as applicable only when the tested runtime bytes are proven identical.
- Mark inaccessible or expired artifacts as unresolved delivery.
- Preserve negative evidence; do not omit failed attempts.
- Distinguish environment restrictions from product defects and retain the logs supporting that classification.
- Use `unsupported` when no available test can establish the claim; never silently downgrade it.

## Output

Return a compact matrix with claim, required level, best observed level, status, and evidence location. End with one of:

- `validated`: every required claim passed.
- `not validated`: one or more claims failed or lack sufficient evidence.
- `partially validated`: only when the user explicitly requests an interim status.

