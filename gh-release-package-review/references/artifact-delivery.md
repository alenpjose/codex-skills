# Artifact Delivery

Use an artifact manifest such as:

```json
{
  "artifact": {
    "exists": true,
    "expired": false,
    "digest": "sha256:<64 hexadecimal characters>",
    "artifact_path": "optional/local/actions-artifact.zip",
    "run_url": "https://github.com/owner/repo/actions/runs/123",
    "head_sha": "...",
    "required_contents": ["installer/setup.exe", "portable.zip", "plugin.dll", "SHA256SUMS.txt"],
    "required_checksum_contents": ["setup.exe", "portable.zip", "plugin.dll"],
    "binary_member": "plugin.dll",
    "user_download": {"status": "passed", "notes": "Downloaded from run page"}
  },
  "blob_uploads": [
    {"path": "src/plugin.cpp", "repo_root": "C:/repo", "local_path": "src/plugin.cpp", "local_git_blob_sha": "...", "remote_git_blob_sha": "..."}
  ]
}
```

GitHub Actions always wraps an artifact in a downloadable ZIP. A portable ZIP inside that wrapper is expected, not accidental double compression. Give users the exact inner installer path.

For pull-request workflows, distinguish the event's synthetic merge commit from the feature-branch head and the commit actually checked out. Require the artifact metadata head SHA, recorded checkout SHA, and release evidence identity to describe the same bytes; otherwise keep delivery unresolved.

Artifact API access and a connected GitHub app do not guarantee that a browser session can use a direct artifact URL. Prefer the workflow run page for authenticated Actions downloads. If the intended audience needs a durable direct link, use an authorized GitHub prerelease/release asset.

Git blob SHAs are content-addressed integrity checks. Compute the canonical local SHA with `git hash-object <path>` and require the connector's created-blob SHA to match before creating a tree. A mismatch means the upload is corrupt or represents different bytes; never move the branch ref.

Supply the downloaded outer ZIP as `artifact_path`. The checker derives its file list, recomputes the outer SHA-256, parses `SHA256SUMS.txt`, and verifies every checksum target it names. List every release payload in `required_checksum_contents`; the gate fails if the installer, portable ZIP, raw DLL, or another named payload is absent from the checksum chain. Set `binary_member` to the raw plugin DLL so its computed digest can be linked to runtime evidence. It never trusts a caller-declared contents list. Existence, expiry, workflow identity, and user-download status still originate from GitHub or user evidence; label that provenance in notes.

Invoke the checker with Python 3. On Windows, try `py -3`, `python3`, or the workspace-provided Python runtime if `python` is unavailable.
