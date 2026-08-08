# Evidence Manifest

Use UTF-8 JSON with this shape:

```json
{
  "release": "example-1.0.0",
  "identity": {"commit": "<40 hex>", "artifact_sha256": "<64 hex>", "binary_sha256": "<64 hex>"},
  "requirements": [
    {
      "id": "dll-loads",
      "claim": "The plugin DLL loads in the target application",
      "required_level": "real_runtime",
      "required": true,
      "evidence": [
        {
          "level": "real_runtime",
          "status": "passed",
          "artifact": "logs/application.log",
          "artifact_type": "file",
          "sha256": "<64 hex>",
          "provenance": "OBS module-load log",
          "environment": "Windows x64; OBS 32.1.2",
          "observed_at": "2026-08-05T20:00:00-04:00",
          "identity": {"binary_sha256": "<64 hex>"},
          "notes": "Module-load entry observed"
        }
      ]
    }
  ]
}
```

Allowed evidence levels, in increasing strength, are `static_inspection`, `build`, `simulated_runtime`, `real_runtime`, and `user_acceptance`.

Allowed evidence statuses are `passed`, `failed`, and `unsupported`.

Require `identity.commit` to be a full 40-character SHA and require at least one release-byte digest. Real-runtime and user-acceptance evidence must name the same `binary_sha256` as the release. Passed evidence must include provenance, environment, timestamp, identity, and a verified file, verified HTTPS URL, or explicit observation. File evidence requires an existing path and matching SHA-256. Preserve artifacts for passed, failed, and unsupported observations in the result. Optional requirements do not fail the overall release gate but remain visible in results.

Pass `--requirements-schema <acceptance-matrix.json>` for a release coordinator. The validator rejects missing, extra, or duplicate canonical requirement IDs and rejects any altered canonical `claim`, `required_level`, or `required` value. Use `--output <path>` to write deterministic JSON.

Set `"superseded": true` only when a later observation against byte-identical release identity replaces an older failed attempt. This preserves the negative evidence without allowing an obsolete failure to override the current gate.

Invoke with Python 3. On Windows, try `py -3`, `python3`, or the workspace-provided Python runtime when `python` is not on PATH.
