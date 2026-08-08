#!/usr/bin/env python3
"""Build a Curious Bipedal release report from verified evidence and delivery outputs."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import zipfile
from pathlib import Path

SHA256 = re.compile(r"^sha256:([0-9a-fA-F]{64})$")
STATUSES = ("passed", "missing", "failed", "unsupported")


def load(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} root must be an object")
    return value


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_archive_bytes(delivery: dict) -> tuple[str, str]:
    artifact = delivery.get("artifact", {})
    path = Path(str(artifact.get("artifact_path", "")))
    if not path.is_file():
        raise ValueError("delivery artifact_path is not a readable outer ZIP")
    outer_sha = sha256_file(path)
    with zipfile.ZipFile(path) as archive:
        contents = sorted(name for name in archive.namelist() if not name.endswith("/"))
        roles = {
            "installer": [name for name in contents if name.lower().endswith(".exe") and ("installer/" in name.lower() or "setup" in Path(name).name.lower())],
            "portable_zip": [name for name in contents if name.lower().endswith(".zip")],
            "raw_dll": [name for name in contents if name.lower().endswith(".dll")],
        }
        for role, members in roles.items():
            if len(members) != 1:
                raise ValueError(f"outer artifact must contain exactly one {role} payload")
        checksum_files = [name for name in contents if Path(name).name.upper() == "SHA256SUMS.TXT"]
        if len(checksum_files) != 1:
            raise ValueError("outer artifact must contain exactly one SHA256SUMS.txt")
        checksum_text = archive.read(checksum_files[0]).decode("utf-8-sig")
        checksums: dict[str, str] = {}
        for line in checksum_text.splitlines():
            match = re.fullmatch(r"([0-9a-fA-F]{64})\s+[* ](.+)", line.strip())
            if match:
                checksums[match.group(2)] = match.group(1).lower()
        for member in [value[0] for value in roles.values()]:
            candidates = [name for name in checksums if member == name or member.endswith("/" + name)]
            if len(candidates) != 1:
                raise ValueError(f"release payload is not uniquely checksum-covered: {member}")
            computed = hashlib.sha256(archive.read(member)).hexdigest()
            if computed != checksums[candidates[0]]:
                raise ValueError(f"release payload checksum mismatch: {member}")
        binary_member = roles["raw_dll"][0]
        return outer_sha, hashlib.sha256(archive.read(binary_member)).hexdigest()


def verify_evidence(evidence: dict, schema: dict) -> tuple[bool, dict]:
    canonical_items = schema.get("requirements")
    actual_items = evidence.get("requirements")
    if not isinstance(canonical_items, list) or not canonical_items or not isinstance(actual_items, list):
        raise ValueError("canonical and evaluated requirements must be non-empty arrays")
    canonical = {}
    for item in canonical_items:
        rid = str(item.get("id", "")).strip()
        if not rid or rid in canonical:
            raise ValueError("requirements schema has missing or duplicate IDs")
        canonical[rid] = {
            "claim": str(item.get("claim", "")).strip(),
            "required_level": item.get("required_level"),
            "required": bool(item.get("required", True)),
        }
    actual = {}
    for item in actual_items:
        rid = str(item.get("id", "")).strip()
        if not rid or rid in actual:
            raise ValueError("evaluated evidence has missing or duplicate IDs")
        actual[rid] = item
    if set(actual) != set(canonical):
        raise ValueError("evaluated evidence does not cover the canonical requirement set")
    for rid, expected in canonical.items():
        item = actual[rid]
        observed = {key: item.get(key) for key in ("claim", "required_level", "required")}
        if observed != expected:
            raise ValueError(f"evaluated evidence changed canonical fields for {rid}")
        if item.get("status") not in STATUSES:
            raise ValueError(f"evaluated evidence has invalid status for {rid}")
        if item.get("status") == "passed":
            artifacts = item.get("artifacts")
            if not isinstance(artifacts, list) or not any(
                isinstance(entry, dict) and isinstance(entry.get("verification"), dict) and entry["verification"].get("verified") is True
                for entry in artifacts
            ):
                raise ValueError(f"passed requirement has no independently verified artifact: {rid}")
    recomputed_counts = {status: sum(item.get("status") == status for item in actual_items) for status in STATUSES}
    if evidence.get("counts") != recomputed_counts:
        raise ValueError("evidence counts are inconsistent with requirement statuses")
    validated = all(actual[rid].get("status") == "passed" for rid, item in canonical.items() if item["required"])
    expected_status = "validated" if validated else "not validated"
    if evidence.get("status") != expected_status:
        raise ValueError("evidence status is inconsistent with canonical requirements")
    return validated, recomputed_counts


def verify_delivery(delivery: dict) -> bool:
    errors = delivery.get("errors")
    missing = delivery.get("missing_contents")
    checksums = delivery.get("inner_checksums")
    blobs = delivery.get("blob_uploads")
    if not all(isinstance(value, list) for value in (errors, missing, checksums, blobs)):
        raise ValueError("delivery verification arrays are missing")
    artifact = delivery.get("artifact", {})
    required = artifact.get("required_checksum_contents")
    if not isinstance(required, list) or not required:
        raise ValueError("delivery artifact has no required checksum payload list")
    paths = [str(item.get("path", "")) for item in checksums if isinstance(item, dict) and item.get("matched") is True]
    uncovered = [name for name in required if not any(path == name or path.endswith("/" + str(name)) for path in paths)]
    binary = str(delivery.get("binary_sha256", ""))
    if uncovered or not re.fullmatch(r"[0-9a-fA-F]{64}", binary):
        return False
    return not errors and not missing and all(item.get("matched") is True for item in checksums) and all(item.get("matched") is True for item in blobs)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence", required=True, type=Path)
    parser.add_argument("--delivery", required=True, type=Path)
    parser.add_argument("--metadata", required=True, type=Path)
    parser.add_argument("--requirements-schema", required=True, type=Path)
    parser.add_argument("--json", action="store_true", dest="as_json")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        evidence, delivery, metadata, schema = load(args.evidence), load(args.delivery), load(args.metadata), load(args.requirements_schema)
        if evidence.get("validator") != "validate-release-evidence/1":
            raise ValueError("evidence is not output from validate-release-evidence/1")
        if delivery.get("validator") != "gh-release-package-review/1":
            raise ValueError("delivery is not output from gh-release-package-review/1")
        evidence_ok, recomputed_counts = verify_evidence(evidence, schema)
        delivery_ok = verify_delivery(delivery)
        recomputed_outer_sha, recomputed_binary_sha = verify_archive_bytes(delivery)
        artifact = delivery.get("artifact")
        if not isinstance(artifact, dict):
            raise ValueError("delivery artifact is missing")
        for field in ("artifact_name", "draft_pr_url"):
            if not str(metadata.get(field, "")).strip():
                raise ValueError(f"metadata.{field} is required")
        identity = evidence.get("identity", {})
        if str(identity.get("commit", "")).lower() != str(artifact.get("head_sha", "")).lower():
            raise ValueError("evidence commit does not match artifact head SHA")
        digest_match = SHA256.fullmatch(str(artifact.get("digest", "")))
        computed = str(delivery.get("computed_artifact_sha256", "")).lower()
        if computed != recomputed_outer_sha:
            raise ValueError("delivery-reported artifact SHA-256 does not match local bytes")
        if not digest_match or recomputed_outer_sha != digest_match.group(1).lower():
            raise ValueError("delivery digest does not match downloaded artifact bytes")
        if identity.get("artifact_sha256") and str(identity["artifact_sha256"]).lower() != recomputed_outer_sha:
            raise ValueError("evidence artifact SHA-256 does not match delivery bytes")
        if str(delivery.get("binary_sha256", "")).lower() != recomputed_binary_sha:
            raise ValueError("delivery-reported binary SHA-256 does not match the raw DLL bytes")
        if str(identity.get("binary_sha256", "")).lower() != recomputed_binary_sha:
            raise ValueError("evidence binary SHA-256 does not match the delivered raw DLL")
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"invalid input: {exc}", file=sys.stderr)
        return 2

    validated = evidence_ok and delivery_ok
    report = {
        "schema_version": 1,
        "status": "validated" if validated else "not validated",
        "identity": evidence.get("identity", {}),
        "artifact": {
            "name": metadata["artifact_name"],
            "digest": f"sha256:{recomputed_outer_sha}",
            "head_sha": artifact["head_sha"],
            "run_url": artifact.get("run_url"),
            "draft_pr_url": metadata["draft_pr_url"],
            "contents": delivery.get("derived_contents", []),
            "inner_checksums": delivery.get("inner_checksums", []),
        },
        "counts": recomputed_counts,
        "requirements": evidence.get("requirements", []),
        "delivery_errors": delivery.get("errors", []),
        "known_limitations": metadata.get("known_limitations", []),
    }
    if args.as_json:
        output = json.dumps(report, indent=2, sort_keys=True) + "\n"
    else:
        a = report["artifact"]
        lines = [
            "# Curious Bipedal OBS Overlay Release Report", "", f"Status: **{report['status']}**", "",
            f"- Commit: `{a['head_sha']}`", f"- Draft PR: {a['draft_pr_url']}", f"- Workflow: {a['run_url']}",
            f"- Artifact: `{a['name']}`", f"- Artifact digest: `{a['digest']}`", "", "## Requirements", "",
        ]
        lines += [f"- [{'x' if item.get('status') == 'passed' else ' '}] {item.get('id')}: {item.get('claim')} ({item.get('status')})" for item in report["requirements"]]
        lines += ["", "## Known limitations", ""] + [f"- {item}" for item in report["known_limitations"]]
        output = "\n".join(lines) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(output, encoding="utf-8")
    else:
        print(output, end="")
    return 0 if validated else 1


if __name__ == "__main__":
    raise SystemExit(main())
