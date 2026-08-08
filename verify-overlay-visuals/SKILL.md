---
name: verify-overlay-visuals
description: Verify rendered broadcast overlays across canvas sizes, scales, margins, text lengths, and branding constraints. Use when checking transparent bounds, detached logo elements, clipping, rounded corners, dynamic-width panels, hierarchy, padding, or text legibility from OBS screenshots or raster assets.
---

# Verify Overlay Visuals

## Workflow

1. Collect actual application renders for every supported canvas and representative scale, not design-source images alone.
2. Include short, normal, and long text values plus all visibility combinations.
3. Run `scripts/analyze_alpha_bounds.py` on transparent overlay renders and logo assets.
4. Run `scripts/check_layout_assertions.py --config <json>` for scale-dependent size and geometry gates.
5. Create a review sheet with `scripts/make_contact_sheet.py`.
6. Inspect the full-resolution images for hierarchy, alignment, stretching artifacts, clipping, and readability.

Use Python 3 with Pillow for the bundled raster scripts. On Windows, try `py -3`, `python3`, or the workspace-provided Python runtime when `python` is unavailable. `make_contact_sheet.py` writes its requested output; point it only at a disposable review directory.

Read `references/visual-acceptance.md` before defining thresholds.

## Required Checks

- Preserve every approved logo component, including detached marks outside the primary body.
- Keep transparent padding intentional and prevent nontransparent pixels from touching the output edge unless specified.
- Preserve rounded corners when content width changes; use fixed caps and a stretchable center where appropriate.
- Size content-driven panels from measured rendered text plus explicit padding.
- Evaluate displayed font size after overlay scale. Native font size alone is not a legibility result.
- Keep elapsed time prominent while ensuring LOG, time, and date fill their allotted rows without enlarging approved bubbles.
- Compare both landscape and portrait canvases at original resolution.

Record manual visual judgments separately from deterministic geometry results. Do not claim aesthetic approval without an actual render or explicit user acceptance.
