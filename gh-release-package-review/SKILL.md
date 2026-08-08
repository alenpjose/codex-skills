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
- For connected-app Git writes, compare the returned remote Git blob SHA with `git hash-object <file>` before creating a t…20573 tokens truncated…alueError(f"{rid}: evidence must be an array")

        best_level = None
        failed = False
        unsupported = False
        usable = []
        all_artifacts = []
        for entry_index, entry in enumerate(evidence):
            if not isinstance(entry, dict):
                raise ValueError(f"{rid}: evidence[{entry_index}] must be an object")
            level = entry.get("level")
            status = entry.get("status")
            if level not in LEVELS or status not in STATUSES:
                raise ValueError(f"{rid}: evidence[{entry_index}] has invalid level or status")
            if status == "passed" and not str(entry.get("artifact", "")).strip():
                raise ValueError(f"{rid}: passed evidence[{entry_index}] needs an artifact")
            artifact = str(entry.get("artifact", "")).strip()
            if artifact:
                all_artifacts.append({"artifact": artifact, "level": level, "status": status, "superseded": bool(entry.get("superseded", False))})
            if entry.get("superseded", False):
                continue
            if status == "passed":
                verification = validate_passed_entry(entry, rid, entry_index, data["identity"], manifest_dir)
                all_artifacts[-1]["verification"] = verification
                usable.append(entry)
                if best_level is None or LEVELS[level] > LEVELS[best_level]:
                    best_level = level
            elif status == "failed":
                failed = True
            else:
                unsupported = True

        sufficient = best_level is not None and LEVELS[best_level] >= LEVELS[required_level]
        if failed:
            status = "failed"
        elif sufficient:
            status = "passed"
        elif unsupported:
            status = "unsupported"
        else:
            status = "missing"
        results.append(
            {
                "id": rid,
                "claim": claim,
                "required": bool(requirement.get("required", True)),
                "required_level": required_level,
                "best_level": best_level,
                "status": status,
                "artifacts": all_artifacts,
            }
        )

    if canonical is not None and seen_ids != set(canonical):
        missing = sorted(set(canonical) - seen_ids)
        extra = sorted(seen_ids - set(canonical))
        raise ValueError(f"canonical requirement IDs differ; missing={missing}, extra={extra}")
    required_failures = [r for r in results if r["required"] and r["status"] != "passed"]
    return {
        "schema_version": 1,
        "validator": "validate-release-evidence/1",
        "release": data.get("release"),
        "identity": data.get("identity", {}),
        "status": "validated" if not required_failures else "not validated",
        "counts": {name: sum(r["status"] == name for r in results) for name in ("passed", "missing", "failed", "unsupported")},
        "requirements": results,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--requirements-schema", type=Path)
    parser.add_argument("--json", action="store_true", dest="as_json")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        data = json.loads(args.manifest.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return fail("root must be an object")
        if not isinstance(data.get("requirements"), list) or not data["requirements"]:
            return fail("requirements must be a non-empty array")
        validate_identity(data)
        canonical = None
        if args.requirements_schema:
            schema = json.loads(args.requirements_schema.read_text(encoding="utf-8"))
            canonical = canonical_requirements(schema)
        result = evaluate(data, args.manifest.resolve().parent, canonical)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        return fail(str(exc))

    if args.as_json or args.output:
        rendered = json.dumps(result, indent=2, sort_keys=True) + "\n"
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(rendered, encoding="utf-8")
        else:
            print(rendered, end="")
    else:
        print(f"{result['status']}: {result['counts']}")
        for item in result["requirements"]:
            print(f"[{item['status']}] {item['id']}: required={item['required_level']} best={item['best_level'] or '-'}")
    return 0 if result["status"] == "validated" else 1


if __name__ == "__main__":
    raise SystemExit(main())
