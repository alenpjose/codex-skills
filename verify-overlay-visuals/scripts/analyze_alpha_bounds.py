#!/usr/bin/env python3
"""Report alpha bounds, padding, and connected components for a raster image."""

from __future__ import annotations

import argparse
import json
import sys
from collections import deque
from pathlib import Path

from PIL import Image


def components(mask: bytearray, width: int, height: int) -> list[dict]:
    found = []
    for y in range(height):
        for x in range(width):
            index = y * width + x
            if not mask[index]:
                continue
            queue = deque([index])
            mask[index] = 0
            count = 0
            min_x = max_x = x
            min_y = max_y = y
            while queue:
                current = queue.popleft()
                cy, cx = divmod(current, width)
                count += 1
                min_x, max_x = min(min_x, cx), max(max_x, cx)
                min_y, max_y = min(min_y, cy), max(max_y, cy)
                neighbors = []
                if cx: neighbors.append(current - 1)
                if cx + 1 < width: neighbors.append(current + 1)
                if cy: neighbors.append(current - width)
                if cy + 1 < height: neighbors.append(current + width)
                for neighbor in neighbors:
                    if mask[neighbor]:
                        mask[neighbor] = 0
                        queue.append(neighbor)
            found.append({"pixels": count, "bounds": [min_x, min_y, max_x + 1, max_y + 1]})
    return sorted(found, key=lambda item: item["pixels"], reverse=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--image", required=True, type=Path)
    parser.add_argument("--alpha-threshold", type=int, default=1)
    parser.add_argument("--minimum-components", type=int, default=1)
    parser.add_argument("--edge-padding", type=int, default=0)
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args()
    if not 0 <= args.alpha_threshold <= 255 or args.minimum_components < 1 or args.edge_padding < 0:
        print("invalid threshold, component count, or padding", file=sys.stderr); return 2
    try:
        image = Image.open(args.image).convert("RGBA")
    except (OSError, ValueError) as exc:
        print(f"cannot read image: {exc}", file=sys.stderr); return 2
    width, height = image.size
    alpha = image.getchannel("A")
    mask = bytearray(value >= args.alpha_threshold for value in alpha.tobytes())
    comps = components(mask, width, height)
    if not comps:
        result = {"image": str(args.image), "size": [width,height], "bounds": None, "components": [], "passed": False, "errors": ["image has no qualifying alpha pixels"]}
    else:
        bounds=[min(item["bounds"][0] for item in comps),min(item["bounds"][1] for item in comps),max(item["bounds"][2] for item in comps),max(item["bounds"][3] for item in comps)]
        padding={"left":bounds[0],"top":bounds[1],"right":width-bounds[2],"bottom":height-bounds[3]}
        errors=[]
        if len(comps) < args.minimum_components: errors.append(f"expected at least {args.minimum_components} components, found {len(comps)}")
        if any(value < args.edge_padding for value in padding.values()): errors.append(f"alpha padding is below {args.edge_padding}px")
        result={"image":str(args.image),"size":[width,height],"bounds":bounds,"padding":padding,"components":comps,"passed":not errors,"errors":errors}
    if args.as_json: print(json.dumps(result,indent=2,sort_keys=True))
    else: print(f"{'passed' if result['passed'] else 'failed'}: bounds={result['bounds']} components={len(result['components'])} errors={'; '.join(result['errors'])}")
    return 0 if result["passed"] else 1


if __name__ == "__main__": raise SystemExit(main())
