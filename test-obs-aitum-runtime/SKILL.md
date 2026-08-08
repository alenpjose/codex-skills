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
3. Start localhost RTMP listeners, then run `scripts/Test-LoopbackListeners.ps1 -WebSocketPort <port> -MainRtmpPort <port> -VerticalRtmpPort <port> -WebSocketConfig <path>` against three distinct designated ports. Launch the isolated host only after it verifies that WebSocket is enabled on its designated port with authentication and that all three listeners bind only to loopback. Use the generated `obs64.exe --portable --disable-shutdown-check` command and confirm the OBS log names the plugin, Aitum Multistream, and Aitum Vertical as loaded.
4. Create two new sources. Do not reuse an existing source when isolation is under test.
5. Execute the matrix through OBS WebSocket or visible application control while observing real OBS/Aitum output objects.
6. Capture source settings, output status, logs, and screenshots with `scripts/Collect-ObsAitumEvidence.ps1`.
7. Restart OBS, repeat persistence checks, then test uninstall with OBS closed.

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
