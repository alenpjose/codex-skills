# Visual Acceptance

Define one JSON assertion file per layout family:

```json
{
  "canvas": {"width": 2560, "height": 1440},
  "scale_percent": 80,
  "minimum_secondary_display_px": 18,
  "fonts": {"log": 24, "time": 26, "date": 24},
  "panels": {
    "session": {"width": 410, "height": 148},
    "telemetry": {"width": 460, "height": 124}
  },
  "expected_panels": {
    "session": {"height": 148},
    "telemetry": {"width": 460, "height": 124}
  },
  "require_render": true,
  "render_images": [{"path": "actual-landscape.png", "expected_size": [2560, 1440]}],
  "obs_profile_ini": "basic/profiles/Skill Test/basic.ini",
  "expected_profile_video": {"BaseCX": 2560, "BaseCY": 1440, "OutputCX": 2560, "OutputCY": 1440}
}
```

Displayed font pixels equal native font size multiplied by the effective render scale. Choose the minimum threshold from the intended viewing context; for the Curious Bipedal regression, use 18 pixels for secondary text at the 80% default scale.

For transparent assets, require a non-empty alpha bounding box, expected connected components where detached marks exist, and explicit safe padding. Alpha analysis cannot prove semantic identity, so retain a visual comparison or approved asset hash.

Use original-resolution screenshots for acceptance. Scaled chat previews may make text appear smaller than the encoded output.

For release gates, set `require_render` and provide actual PNG paths. The checker opens each PNG and compares its encoded dimensions; filenames are never dimension evidence. Supply the isolated OBS profile INI when canvas/output configuration is part of the claim. Caller-provided font/panel JSON remains a geometry assertion and does not replace an actual render.
