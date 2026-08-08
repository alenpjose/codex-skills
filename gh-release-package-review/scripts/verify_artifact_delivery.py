#!/usr/bin/env python3
"""Validate GitHub artifact delivery metadata and connected-app blob integrity."""

from __future__ import annotations

import argparse, hashlib, json, re, subprocess, sys, zipfile
from pathlib import Path

SHA256 = re.compile(r"^sha256:([0-9a-fA-F]{64})$")
GIT_SHA1 = re.compile(r"^[0-9a-fA-F]{40}$")


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git_blob_sha(repo_root: Path, local_path: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(repo_root), "hash-object", "--", local_path],
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def main() -> int:
    parser=argparse.ArgumentParser(); parser.add_argument("--manifest",required=True,type=Path); parser.add_argument("--json",action="store_true",dest="as_json"); parser.add_argument("--output",type=Path); args=parser.parse_args()
    try: data=json.loads(args.manifest.read_text(encoding="utf-8"))
    except (OSError,json.JSONDecodeError) as exc: print(f"invalid manifest: {exc}",file=sys.stderr); return 2
    if not isinstance(data,dict) or not isinstance(data.get("artifact"),dict): print("invalid manifest: artifact object is required",file=sys.stderr); return 2
    artifact=data["artifact"]; errors=[]
    if artifact.get("exists") is not True: errors.append("artifact does not exist")
    if artifact.get("expired") is not False: errors.append("artifact is expired or expiry is unknown")
    digest=str(artifact.get("digest",""))
    digest_match=SHA256.fullmatch(digest)
    if not digest_match: errors.append("artifact digest must be sha256:<64 hex characters>")
    artifact_path=str(artifact.get("artifact_path","")).strip()
    computed_digest=None
    derived_contents=[]; checksum_results=[]; checksum_by_member={}; binary_sha256=None
    payload_roles={"installer":[],"portable_zip":[],"raw_dll":[]}
    if not artifact_path: errors.append("artifact_path is required for byte-level delivery verification")
    else:
        local_artifact=Path(artifact_path)
        if not local_artifact.is_file(): errors.append("artifact_path does not name a readable file")
        else:
            computed_digest=file_sha256(local_artifact)
            if digest_match and computed_digest.lower() != digest_match.group(1).lower(): errors.append("artifact SHA-256 does not match local bytes")
            try:
                with zipfile.ZipFile(local_artifact) as archive:
                    derived_contents=sorted(name for name in archive.namelist() if not name.endswith("/"))
                    checksum_names=[name for name in derived_contents if Path(name).name.upper()=="SHA256SUMS.TXT"]
                    if not checksum_names: errors.append("outer artifact has no SHA256SUMS.txt")
                    else:
                        checksum_text=archive.read(checksum_names[0]).decode("utf-8-sig")
                        for line in checksum_text.splitlines():
                            match=re.fullmatch(r"([0-9a-fA-F]{64})\s+[* ](.+)",line.strip())
                            if not match: continue
                            expected,name=match.groups(); candidates=[item for item in derived_contents if item==name or item.endswith("/"+name)]
                            if len(candidates)!=1:
                                errors.append(f"checksum target is missing or ambiguous: {name}"); continue
                            computed=hashlib.sha256(archive.read(candidates[0])).hexdigest(); matched=computed.lower()==expected.lower()
                            checksum_results.append({"path":candidates[0],"expected_sha256":expected.lower(),"computed_sha256":computed,"matched":matched})
                            checksum_by_member[candidates[0]]=checksum_results[-1]
                            if not matched: errors.append(f"inner checksum mismatch: {candidates[0]}")
                        if not checksum_results: errors.append("SHA256SUMS.txt contains no verifiable entries")
                        payload_roles={
                            "installer":[item for item in derived_contents if item.lower().endswith(".exe") and ("installer/" in item.lower() or "setup" in Path(item).name.lower())],
                            "portable_zip":[item for item in derived_contents if item.lower().endswith(".zip")],
                            "raw_dll":[item for item in derived_contents if item.lower().endswith(".dll")],
                        }
                        for role,members in payload_roles.items():
                            if len(members)!=1: errors.append(f"artifact must contain exactly one {role} payload; found {len(members)}")
                        mandatory_checksums=[member for members in payload_roles.values() for member in members]
                        required_checksums=artifact.get("required_checksum_contents",[])
                        if not isinstance(required_checksums,list):
                            errors.append("required_checksum_contents must be an array")
                            required_checksums=[]
                        required_checksums=list(dict.fromkeys(mandatory_checksums+[str(item) for item in required_checksums]))
                        for required_name in required_checksums:
                            candidates=[item for item in derived_contents if item==required_name or item.endswith("/"+str(required_name))]
                            if len(candidates)!=1:
                                errors.append(f"required checksum payload is missing or ambiguous: {required_name}")
                            elif candidates[0] not in checksum_by_member:
                                errors.append(f"release payload is not covered by SHA256SUMS.txt: {candidates[0]}")
                        binary_member=str(artifact.get("binary_member","")).strip()
                        binary_candidates=payload_roles["raw_dll"]
                        if binary_member and len(binary_candidates)==1 and not (binary_candidates[0]==binary_member or binary_candidates[0].endswith("/"+binary_member)):
                            errors.append("binary_member does not identify the unique raw DLL payload")
                        if len(binary_candidates)==1:
                            if binary_candidates[0] not in checksum_by_member:
                                errors.append("raw plugin DLL is not covered by SHA256SUMS.txt")
                            else:
                                binary_sha256=checksum_by_member[binary_candidates[0]]["computed_sha256"]
            except (OSError,zipfile.BadZipFile,UnicodeDecodeError) as exc: errors.append(f"cannot inspect outer artifact ZIP: {exc}")
    if not str(artifact.get("run_url","" )).startswith("https://github.com/"): errors.append("workflow run URL is missing")
    if not GIT_SHA1.fullmatch(str(artifact.get("head_sha","" )).strip()): errors.append("artifact head SHA must be 40 hexadecimal characters")
    download=artifact.get("user_download",{})
    if not isinstance(download,dict) or download.get("status") != "passed": errors.append("user-facing download is unresolved")
    contents=set(derived_contents); required=set(artifact.get("required_contents",[])); missing=sorted(required-contents)
    if missing: errors.append("missing required contents: " + ", ".join(missing))
    blob_results=[]
    for index,item in enumerate(data.get("blob_uploads",[])):
        if not isinstance(item,dict): print(f"invalid manifest: blob_uploads[{index}] must be an object",file=sys.stderr); return 2
        declared_local=str(item.get("local_git_blob_sha","")).strip(); remote=str(item.get("remote_git_blob_sha","")).strip(); computed_local=None
        repo_root=str(item.get("repo_root","")).strip(); local_path=str(item.get("local_path",item.get("path",""))).strip()
        if repo_root and local_path:
            try: computed_local=git_blob_sha(Path(repo_root),local_path)
            except (OSError,subprocess.CalledProcessError) as exc: errors.append(f"cannot compute local Git blob SHA for {local_path}: {exc}")
        local=computed_local or declared_local
        if declared_local and computed_local and declared_local.lower() != computed_local.lower(): errors.append(f"declared local Git blob SHA mismatch: {local_path}")
        matched=bool(GIT_SHA1.fullmatch(local) and GIT_SHA1.fullmatch(remote) and local.lower()==remote.lower())
        blob_results.append({"path":item.get("path"),"matched":matched,"declared_local_git_blob_sha":declared_local,"computed_local_git_blob_sha":computed_local,"remote_git_blob_sha":remote})
        if not matched: errors.append(f"Git blob SHA mismatch: {item.get('path','<unknown>')}")
    result={"schema_version":1,"validator":"gh-release-package-review/1","passed":not errors,"errors":errors,"missing_contents":missing,"derived_contents":derived_contents,"payload_roles":payload_roles,"inner_checksums":checksum_results,"blob_uploads":blob_results,"computed_artifact_sha256":computed_digest,"binary_sha256":binary_sha256,"artifact":artifact}
    if args.as_json or args.output:
        rendered=json.dumps(result,indent=2,sort_keys=True)+"\n"
        if args.output: args.output.parent.mkdir(parents=True,exist_ok=True); args.output.write_text(rendered,encoding="utf-8")
        else: print(rendered,end="")
    else: print(f"{'passed' if result['passed'] else 'failed'}: {'; '.join(errors)}")
    return 0 if result["passed"] else 1


if __name__ == "__main__": raise SystemExit(main())
