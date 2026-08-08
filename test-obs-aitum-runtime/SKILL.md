---
name: test-obs-aitum-runtime
description: Plan and execute isolated Windows runtime smoke tests for native OBS plugins with OBS WebSocket, localhost-only streaming, Aitum Multistream, and Aitum Vertical. Use when validating module loading, independent source instances, output-bound timers, controls, hotkeys, persistence, restart, missing-output recovery, installation, or teardown.
---

# Test OBS and Aitum Runtime

## Safety

- Use a copied or portable OBS host and a disposable OBS configuration directory.
- Bind test RTMP listeners to localhost and use non-production stream keys.
- Require OBS WebSocket authentication and verify its listener is bound only to `127.0.0.1` or `::1`; do not infer this from localhost RTMP configuration.
- Keep scripts dry-run by default; pass `-Apply` only for approved disposable paths.
- Stop OBS before replacing plugin files, installing, or uninstalling.
- Never reuse production profiles, scenes, credentials, or output URLs.

Read `references/runtime-matrix.md` before execution.

## Workflow

1. Generate the case matrix with `scripts/New-ObsAitumTestMatrix.ps1`.
2. Preview host preparation with `scripts/Initialize-ObsAitumTestHost.ps1`; rerun with `-Apply` after verifying resolved paths.
3. Start localhost RTMP listeners, then run `scripts/Test-LoopbackListeners.ps1 -WebSocketPort <port> -MainRtmpPort <port> -VerticalRtmpPort <port> -WebSocketConfig <path>` against three distinct designated ports. Launch the isolated host only after it verifies that WebSocket is enabled on its designated port with authentication and that all three listeners bind only to loopback. Use the generated `obs64.exe --portable --disable-updater` command. After an abnormal disposable-host termination, preview and run `scripts/Reset-ObsTestSentinel.ps1 -TestRoot <dir> -Apply` so OBS does not block on its unclean-shutdown dialog. Confirm the OBS log names the plugin, Aitum Multistream, and Aitum Vertical as loaded.
4. Create two new sources. Do not reuse an existing source when isolation is under test.
5. Preview the deterministic WebSocket pass with `scripts/Invoke-ObsAitumMatrix.ps1 -MatrixPath <json> -EvidenceDir <dir>`. Rerun with `-Apply` to authenticate, prove settings isolation by mutation-and-restore, and optionally capture exact-canvas source screenshots. Add `-ExerciseButtons` or `-ExerciseOutputs` only when the visible host and real localhost RTMP endpoints are ready. The runner deliberately records output-timer claims as `unsupported` until before/during/after renders are reviewed; a successful request is not timer evidence.
6. Complete hotkey, missing-output, restart, and screenshot observations through visible application control. Do not use `TriggerHotkeyByName` for per-source hotkeys because identical source hotkey names can target multiple instances; use assigned key sequences and observe both sources.
7. Capture source settings, output status, logs, and screenshots with `scripts/Collect-ObsAitumEvidence.ps1`.
8. Restart OBS, repeat persistence checks, then test uninstall with OBS closed.

## Runtime Invariants

- Landscape settings, timer state, and hotkeys must not alter the vertical source.
- The landscape timer must follow only the main OBS stream.
- The vertical timer must follow only the configured Aitum Vertical output.
- A missing or mismatched Aitum output may disable automatic vertical timing but must not break rendering or OBS stability.
- Manual controls and per-source hotkeys must target the intended source.
- Settings and elapsed state must persist according to documented semantics after restart.
- After uninstall, an existing scene item becoming red/unavailable and ceasing to render is expected evidence that the source implementation was removed.

Do not treat property-button automation as equivalent to hotkey or output-signal testing when opening properties itself changes settings.

Run PowerShell scripts with `powershell.exe -NoProfile -ExecutionPolicy Bypass -File <script>` on disposable test hosts when local policy blocks direct script invocation. A generated matrix begins with every case marked `not_run`; expected labels are requirements, not evidence.
