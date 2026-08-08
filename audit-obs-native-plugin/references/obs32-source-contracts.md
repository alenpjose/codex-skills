# OBS 32 Source Contracts

Check these invariants against the exact OBS headers used by the build:

- Initialize `obs_source_info` deterministically and set a stable unique `id`.
- Match `type`, `output_flags`, and callback table. In OBS 32, a source advertising `OBS_SOURCE_COMPOSITE` must provide the callbacks required by composite registration; a silent composite source still needs a valid no-audio `audio_render` implementation when the registration contract requires it.
- Return an instance pointer from `create` only after all mandatory child sources and resources are valid, or handle partial construction safely in `destroy`.
- Release private child sources, filters, signals, hotkeys, output references, procedure handlers, and queued-task state exactly once.
- Use `obs_source_add_active_child`/`obs_source_remove_active_child` symmetrically for composite children.
- Perform graphics-resource creation/destruction inside the OBS graphics context and render children from the video-render callback.
- Treat callbacks as potentially concurrent unless the pinned API guarantees otherwise. Copy settings needed by render/tick under a short lock, then release the lock before OBS calls.
- Validate module load using the OBS log. `obs_register_source failed` is a runtime compatibility failure even when the DLL compiled and linked.

Audit the pinned header rather than relying on remembered behavior when the OBS version changes.

