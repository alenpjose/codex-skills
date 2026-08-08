# Curious Bipedal Release Requirements

## Environment

- Windows x64
- OBS Studio 32.1.2
- Aitum Multistream 1.0.8 test baseline
- Aitum Vertical Canvas 1.6.4 test baseline
- Repository: `alenpjose/curious-bipedal-obs-overlay`
- Feature branch and draft pull request by default

## Runtime

- Create separate landscape and vertical sources; never reuse one source when testing isolation.
- Landscape: 2560Ã—1440, timer bound to the main OBS stream.
- Vertical: 1440Ã—2560, timer bound to the selected named Aitum Vertical output.
- Verify distinct titles, LOG values, dimensions, timer state, output binding, and hotkeys.
- Test F9/F10 for landscape start/reset and F11/F12 for vertical start/reset when those assignments are used by the test scene.
- Preserve settings and documented elapsed state across restart.

## Visuals

- Default overlay scale: 80%.
- Preserve the complete approved glyph, including planet curve and detached floating dot.
- Keep rounded, compact bubbles and content-driven session width.
- Keep elapsed time prominent.
- Render LOG at native 24 bold, time at 26 bold, and date at 24 so each remains at least 18 displayed pixels at 80%.
- Do not enlarge the approved session or telemetry bubbles to satisfy secondary-text legibility.

## Approved asset hashes

- `data/assets/curious-bipedal-primary-glyph.svg`: `B2A4F6D33460C5147302945B1E65B9CCDE35B60FC0A7D7E3D484F7FEFFF507CC`
- `data/assets/curious-bipedal-primary-glyph.png`: `442B1CA898E79D6CD8161E4B711E9D9208178ECEE3A9BA560AAAD51C79676571`
- `data/assets/curious-bipedal-primary-glyph-safe.png`: `52E4007108B5920F3C367671151B30B9914AE0F635067766E6A89235072A875E`

## Known limitations

- Alpha binaries are unsigned and may trigger SmartScreen.
- The standard installer targets the shared ProgramData OBS plugin directory and does not auto-detect portable OBS.
- Aitum binding requires matching output name and canvas dimensions.
- Independently started Aitum Multistream destinations are not distinct timer bindings; destinations sharing the main OBS stream share the landscape timer.
- GitHub Actions downloads an outer artifact ZIP containing the installer, portable ZIP, raw DLL, and checksums.

