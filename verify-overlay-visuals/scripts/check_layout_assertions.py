#!/usr/bin/env python3
"""Validate scale-dependent overlay font and panel assertions."""

from __future__ import annotations

import argparse, configparser, json, sys
from pathlib import Path
from PIL import Image


def main() -> int:
    parser=argparse.ArgumentParser(); parser.add_argument("--config",required=True,type=Path); parser.add_argument("--json",action="store_true",dest="as_json"); parser.add_argument("--output",type=Path); args=parser.parse_args()
    try: data=json.loads(args.config.read_text(encoding="utf-8"))
    except (OSError,json.JSONDecodeError) as exc: print(f"invalid config: {exc}",file=sys.stderr); return 2
    try:
        scale=float(data["scale_percent"])/100.0; minimum=float(data["minimum_secondary_display_px"]); fonts=data["fonts"]
        if scale <= 0 or minimum <= 0 or not fonts: raise ValueError("scale, threshold, and fonts must be positive")
    except (KeyError,TypeError,ValueError) as exc: print(f"invalid config: {exc}",file=sys.stderr); return 2
    errors=[]; displayed={name:float(size)*scale for name,size in fonts.items()}; render_results=[]
    for name,size in displayed.items():
        if size < minimum: errors.append(f"{name} displays at {size:.1f}px below {minimum:.1f}px")
    for name,expected in data.get("expected_panels",{}).items():
        actual=data.get("panels",{}).get(name,{})
        for key,value in expected.items():
            if actual.get(key) != value: errors.append(f"{name}.{key} changed from {value!r} to {actual.get(key)!r}")
    renders=data.get("render_images",[])
    if data.get("require_render") and not renders: errors.append("actual render_images are required")
    try:
        canvas_size=[int(data["canvas"]["width"]),int(data["canvas"]["height"])]
        if min(canvas_size) <= 0: raise ValueError("canvas dimensions must be positive")
    except (KeyError,TypeError,ValueError) as exc:
        print(f"invalid config: {exc}",file=sys.stderr); return 2
    for index,item in enumerate(renders):
        try:
            path=Path(item["path"]); path=path if path.is_absolute() else args.config.resolve().parent/path
            expected=canvas_size
            with Image.open(path) as image: actual=list(image.size)
            matched=actual==expected; render_results.append({"path":str(path),"actual_size":actual,"expected_size":expected,"matched":matched})
            if not matched: errors.append(f"render_images[{index}] is {actual}, expected {expected}")
        except (KeyError,TypeError,ValueError,OSError) as exc: errors.append(f"render_images[{index}] cannot be verified: {exc}")
    profile_result=None
    if data.get("obs_profile_ini"):
        path=Path(data["obs_profile_ini"]); path=path if path.is_absolute() else args.config.resolve().parent/path
        parser_ini=configparser.ConfigParser()
        try:
            parser_ini.read(path,encoding="utf-8-sig")
            actual={key:int(parser_ini[section][key]) for section,key in (("Video","BaseCX"),("Video","BaseCY"),("Video","OutputCX"),("Video","OutputCY"))}
            expected={key:int(value) for key,value in data.get("expected_profile_video",{}).items()}
            matched=all(actual.get(key)==value for key,value in expected.items()); profile_result={"path":str(path),"actual":actual,"expected":expected,"matched":matched}
            if not matched: errors.append("OBS profile video dimensions do not match expected values")
        except (OSError,KeyError,ValueError,configparser.Error) as exc: errors.append(f"OBS profile cannot be verified: {exc}")
    result={"passed":not errors,"effective_scale":scale,"displayed_fonts":displayed,"render_images":render_results,"obs_profile":profile_result,"errors":errors}
    if args.as_json or args.output:
        rendered=json.dumps(result,indent=2,sort_keys=True)+"\n"
        if args.output: args.output.parent.mkdir(parents=True,exist_ok=True); args.output.write_text(rendered,encoding="utf-8")
        else: print(rendered,end="")
    else: print(f"{'passed' if result['passed'] else 'failed'}: displayed={displayed}; errors={'; '.join(errors)}")
    return 0 if result["passed"] else 1


if __name__ == "__main__": raise SystemExit(main())
