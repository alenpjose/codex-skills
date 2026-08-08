# Aitum Output Ownership

Treat procedure-based integrations as optional runtime dependencies:

- Discover the public procedure at runtime and tolerate absence without preventing overlay rendering.
- Pass the exact canvas dimensions and configured output name expected by the provider.
- Determine whether the returned `obs_output_t *` is borrowed or referenced from the provider's published contract. Add a reference before retaining a borrowed pointer and release retained references during reconnect and teardown.
- Connect start/stop signals only while the retained output remains valid. Disconnect before releasing or replacing it.
- Marshal procedure calls to the provider's required UI/task thread.
- Protect queued reconnect work with a lifetime token or equivalent teardown guard.
- Retry boundedly when the provider, canvas, or named output is unavailable. Do not busy-loop.
- Test main OBS output and Aitum Vertical output independently with real output objects; manual timer buttons do not prove routing.

