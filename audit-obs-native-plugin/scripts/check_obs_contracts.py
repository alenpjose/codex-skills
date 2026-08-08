#!/usr/bin/env python3
"""Heuristic OBS native-plugin contract scanner. Results require human validation."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

SOURCE_SUFFIXES = {".c", ".cc", ".cpp", ".cxx", ".h", ".hpp"}


def collect(path: Path) -> list[Path]:
    if path.is_file():
        return [path]
    return sorted(p for p in path.rglob("*") if p.is_file() and p.suffix.lower() in SOURCE_SUFFIXES)


def scan(files: list[Path]) -> dict:
    texts = []
    unreadable = []
    for path in files:
        try:
            texts.append((path, path.read_text(encoding="utf-8")))
        except (OSError, UnicodeDecodeError) as exc:
            unreadable.append({"path": str(path), "error": str(exc)})
    findings = []

    def add(rule: str, severity: str, confidence: str, message: str, path: Path, token: str, symbol: str = "obs_source_info") -> None:
        text = next(value for item_path, value in texts if item_path == path)
        offset = text.find(token)
        findings.append({"rule": rule, "severity": severity, "confidence": confidence, "path": str(path), "line": text.count("\n", 0, max(0, offset)) + 1, "symbol": symbol, "message": message})

    for path, text in texts:
        if "obs_source_info" in text:
            required_assignments = {
                "source-id": (r"\.id\s*=", "stable .id"),
                "source-type": (r"\.type\s*=", ".type"),
                "source-name": (r"\.get_name\s*=", ".get_name"),
                "source-registration": (r"obs_register_source(?:_s)?\s*\(", "obs_register_source call"),
            }
            for rule, (pattern, label) in required_assignments.items():
                if not re.search(pattern, text):
                    add(rule, "high", "probable", f"Source registration appears incomplete: no {label} was found in the same translation unit.", path, "obs_source_info")
            if "OBS_SOURCE_VIDEO" in text and not re.search(r"\.video_render\s*=", text):
                add("video-render", "high", "probable", "Video output flags are present but no video_render assignment was found.", path, "OBS_SOURCE_VIDEO")
            if "OBS_SOURCE_COMPOSITE" in text and not re.search(r"(?:\.|\b)audio_render\s*=", text):
                add("composite-audio-render", "high", "probable", "Composite source flags are present but no audio_render assignment was found.", path, "OBS_SOURCE_COMPOSITE")
            if re.search(r"\.create\s*=", text) and not re.search(r"\.destroy\s*=", text):
                add("missing-destroy", "high", "probable", "A source create callback was assigned without a destroy callback.", path, ".create")
        if "obs_source_add_active_child" in text and "obs_source_remove_active_child" not in text:
            add("active-child-symmetry", "high", "probable", "Active child sources are added but no removal call was found in the same translation unit.", path, "obs_source_add_active_child", "active-child ownership")
        if "signal_handler_connect" in text and "signal_handler_disconnect" not in text:
            add("signal-disconnect", "high", "probable", "Signal handlers are connected but no disconnect call was found in the same translation unit.", path, "signal_handler_connect", "signal ownership")
        if "obs_output_get_ref" in text and "obs_output_release" not in text:
            add("output-reference", "high", "probable", "Output references are retained but no output release call was found in the same translation unit.", path, "obs_output_get_ref", "output ownership")
        if "obs_queue_task" in text and not re.search(r"destroy|lifetime|weak|cancel", text, re.IGNORECASE):
            add("queued-task-lifetime", "medium", "hypothesis", "Queued OBS work was found without an obvious teardown or lifetime guard.", path, "obs_queue_task", "queued task")

    global_pattern = re.compile(r"^(?:static\s+)?(?!const\b|constexpr\b)(?:std::)?(?:string|vector|map|unordered_map|mutex|atomic|bool|int|uint\w*)\s+\w+\s*=", re.MULTILINE)
    for path, text in texts:
        for match in global_pattern.finditer(text):
            prefix = text[max(0, match.start() - 200):match.start()]
            if prefix.count("{") == prefix.count("}"):
                line = text.count("\n", 0, match.start()) + 1
                findings.append({"rule": "mutable-global-state", "severity": "medium", "confidence": "hypothesis", "path": str(path), "line": line, "symbol": match.group(0).strip(), "message": "Possible mutable global instance state; trace uses before treating it as source-instance state."})

    return {"files_scanned": len(texts), "unreadable": unreadable, "findings": findings}


def verify_header_context(root: Path | None, expected_version: str) -> tuple[bool, list[str]]:
    limitations: list[str] = []
    if root is None:
        return False, ["Pinned OBS header root was not supplied."]
    if not root.is_dir():
        return False, ["OBS headers must name an extracted OBS source root directory, not a file."]
    required = (root / "libobs" / "obs-source.h", root / "libobs" / "obs.h", root / "CMakeLists.txt")
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        return False, ["OBS header root is missing required sentinels: " + ", ".join(missing)]
    version_token = expected_version.strip().lower()
    root_marker = root.name.lower()
    marker_files = [root / "buildspec.json", root / "cmake" / "common" / "versionconfig.cmake"]
    marker_text = "\n".join(path.read_text(encoding="utf-8", errors="ignore").lower() for path in marker_files if path.is_file())
    if version_token not in root_marker and version_token not in marker_text:
        limitations.append(
            f"Cannot prove supplied OBS headers are version {expected_version}; use a versioned source root or marker file."
        )
    return not limitations, limitations


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--obs-version", required=True)
    parser.add_argument("--headers", type=Path)
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args()
    if not args.source.exists():
        print(f"source does not exist: {args.source}", file=sys.stderr)
        return 2
    files = collect(args.source)
    if not files:
        print("no C/C++ source files found", file=sys.stderr)
        return 2
    context_verified, limitations = verify_header_context(args.headers, args.obs_version)
    result = scan(files)
    result["obs_version"] = args.obs_version
    result["headers"] = str(args.headers) if args.headers else None
    result["context_verified"] = context_verified
    result["limitations"] = limitations
    if args.as_json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(f"scanned {result['files_scanned']} files; {len(result['findings'])} candidate findings")
        for finding in result["findings"]:
            print(f"[{finding['confidence']}/{finding['severity']}] {finding['rule']}: {finding['message']}")
    return 1 if result["findings"] or not context_verified else 0


if __name__ == "__main__":
    raise SystemExit(main())
