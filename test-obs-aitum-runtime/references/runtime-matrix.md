# Runtime Matrix

Use distinct source names and values so leakage is visible.

| Case | Action | Expected observation |
|---|---|---|
| Load | Start isolated OBS | Plugin and both Aitum modules load without registration errors |
| Isolation | Edit landscape source | Vertical settings and timer remain unchanged |
| Isolation | Edit vertical source | Landscape settings and timer remain unchanged |
| Main routing | Start main stream | Only main-bound elapsed timer advances |
| Main routing | Stop main stream | Main-bound timer stops according to documented behavior |
| Vertical routing | Start selected Aitum output | Only vertical-bound timer advances |
| Wrong output | Configure nonexistent Aitum name | Overlay renders, retry remains bounded, automatic vertical timing is unavailable |
| Manual | Start, pause, reset | Intended source changes and the other source remains unchanged |
| Hotkeys | Trigger each source's assignments | Only the registered source responds |
| Persistence | Save and restart OBS | Settings, hotkeys, and documented timer state return |
| Layout | Render every supported canvas | No clipping; required branding and text remain legible |
| Uninstall | Uninstall with OBS closed | Runtime files are removed; prior scene item is unavailable after restart |

Record the OBS version, Aitum versions, plugin DLL hash, scene collection, output names, canvas dimensions, and timestamps with the evidence.

Generate the matrix with the full commit SHA, final plugin DLL path, and exact OBS/Aitum versions. Record each new source UUID after creation. For every case, replace `not_run` with `passed`, `failed`, or `unsupported`, and attach timestamped evidence paths plus measured timer observations. Record start/stop elapsed values for both sources, not just expected labels. Before starting OBS, record listener addresses for WebSocket and both RTMP endpoints. Reject a host as isolated if any listener accepts non-loopback traffic or WebSocket authentication is disabled. Reject runtime evidence if the DLL hash or last-write timestamp changes after the matrix begins.
