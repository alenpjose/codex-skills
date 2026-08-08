#!/usr/bin/env python3
"""Validate a release evidence manifest without mutating external state."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

LEVELS = {
    "static_inspection": 1,
    "build": 2,
    "simulated_runtime": 3,
    "real_runtime": 4,
    "user_acceptance": 5,
}
STATUSES = {"passed", "failed", "unsupported"}
HEX_SHA256 = re.compile(r"^[0-9a-fA-F]{64}$")
HEX_COMMIT = re.compile(r"^[0-9a-fA-F]{40}$")


def validate_identity(data: dict) -> None:
    identity = data.get("identity")
    if not isinstance(identity, dict) or not identity:
        raise ValueError("identity must be a non-empty object")
    commit = str(identity.get("commit", "")).strip()
    if not HEX_COMMIT.fullmatch(commit):
        raise ValueError("identity.commit must be a full 40-character hexadecimal commit SHA")
    for key in ("artifact_sha256", "binary_sha256"):
        value = str(identity.get(key, "")).strip()
        if value and not HEX_SHA256.fullmatch(value):
            raise ValueError(f"identity.{key} must be 64 hexadecimal characters")
    if not identity.get("artifact_sha256") and not identity.get("binary_sha256"):
        raise ValueError("identity needs artifact_sha256 or binary_sha256")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_passed_entry(entry: dict, rid: str, entry_index: int, root_identity: dict, manifest_dir: Path) -> dict:
    provenance = str(entry.get("provenance", "")).strip()
    environment = str(entry.get("environment", "")).strip()
    observed_at = str(entry.get("observed_at", "")).strip()
    if not provenance or not environment or not observed_at:
        raise ValueError(f"{rid}: passed evidence[{entry_index}] needs provenance, environment, and observed_at")
    try:
        datetime.fromisoformat(observed_at.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{rid}: evidence[{entry_index}].observed_at must be ISO-8601") from exc
    artifact = str(entry.get("artifact", "")).strip()
    artifact_type = str(entry.get("artifact_type", "")).strip()
    verification = {"artifact_type": artifact_type, "verified": False}
    if artifact_type == "file":
        path = Path(artifact)
        if not path.is_absolute():
            path = manifest_dir / path
        if not path.is_file():
            raise ValueError(f"{rid}: evidence[{entry_index}] file does not exist: {path}")
        declared = str(entry.get("sha256", "")).strip()
        if not HEX_SHA256.fullmatch(declared):
            raise ValueError(f"{rid}: evidence[{entry_index}] file needs a 64-character sha256")
        computed = sha256_file(path)
        if computed.lower() != declared.lower():
            raise ValueError(f"{rid}: evidence[{entry_index}] file SHA-256 mismatch")
        verification.update({"verified": True, "computed_sha256": computed, "resolved_path": str(path.resolve())})
    elif artifact_type == "url":
        parsed = urlparse(artifact)
        if parsed.scheme != "https" or not parsed.netloc:
            raise ValueError(f"{rid}: evidence[{entry_index}] URL must be HTTPS")
        verification["verified"] = bool(entry.get("access_verified", False))
        if not verification["verified"]:
            raise ValueError(f"{rid}: evidence[{entry_index}] URL access is not verified")
    elif artifact_type == "observation":
        verification["verified"] = True
    else:
        raise ValueError(f"{rid}: passed evidence[{entry_index}] artifact_type must be file, url, or observation")
    entry_identity = entry.get("identity")
    if not isinstance(entry_identity, dict):
        raise ValueError(f"{rid}: passed evidence[{entry_index}] needs identity")
    level = entry["level"]
    identity_key = "binary_sha256" if LEVELS[level] >= LEVELS["real_runtime"] else "commit"
    expected = str(root_identity.get(identity_key, "")).lower()
    actual = str(entry_identity.get(identity_key, "")).lower()
    if not expected or actual != expected:
        raise ValueError(f"{rid}: evidence[{entry_index}] {identity_key} does not match release identity")
    return verification


def fail(message: str) -> int:
    print(f"invalid manifest: {message}", file=sys.stderr)
    return 2


def canonical_requirements(schema: dict) -> dict[str, dict]:
    items = schema.get("requirements")
    if not isinstance(items, list) or not items:
        raise ValueError("requirements schema needs a non-empty requirements array")
    result: dict[str, dict] = {}
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            raise ValueError(f"requirements schema requirements[{index}] must be an object")
        rid = str(item.get("id", "")).strip()
        claim = str(item.get("claim", "")).strip()
        level = item.get("required_level")
        if not rid or not claim or level not in LEVELS:
            raise ValueError(f"requirements schema requirements[{index}] is incomplete")
        if rid in result:
            raise ValueError(f"requirements schema has duplicate ID: {rid}")
        result[rid] = {
            "id": rid,
            "claim": claim,
            "required_level": level,
            "required": bool(item.get("required", True)),
        }
    return result


def evaluate(data: dict, manifest_dir: Path, canonical: dict[str, dict] | None = None) -> dict:
    results = []
    seen_ids = set()
    for index, requirement in enumerate(data.get("requirements", [])):
        if not isinstance(requirement, dict):
            raise ValueError(f"requirements[{index}] must be an object")
        rid = str(requirement.get("id", "")).strip()
        claim = str(requirement.get("claim", "")).strip()
        required_level = requirement.get("required_level")
        if not rid or not claim:
            raise ValueError(f"requirements[{index}] needs non-empty id and claim")
        if rid in seen_ids:
            raise ValueError(f"duplicate requirement id: {rid}")
        seen_ids.add(rid)
        if required_level not in LEVELS:
            raise ValueError(f"{rid}: unknown required_level {required_level!r}")
        if canonical is not None:
            expected = canonical.get(rid)
            if expected is None:
                raise ValueError(f"requirement is not canonical: {rid}")
            actual = {
                "id": rid,
                "claim": claim,
                "required_level": required_level,
                "required": bool(requirement.get("required", True)),
            }
            if actual != expected:
                differences = [key for key in ("claim", "required_level", "required") if actual[key] != expected[key]]
                raise ValueError(f"{rid}: canonical fields differ: {', '.join(differences)}")
        evidence = requirement.get("evidence", [])
        if not isinstance(evidence, list):
            raise ValueError(f"{rid}: evidence must be an array")

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
