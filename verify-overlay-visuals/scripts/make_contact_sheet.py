#!/usr/bin/env python3
"""Create a labeled PNG contact sheet from supplied images."""

from __future__ import annotations

import argparse, math, sys
from pathlib import Path
from PIL import Image, ImageDraw


def main() -> int:
    parser=argparse.ArgumentParser(); parser.add_argument("--image",action="append",required=True,type=Path); parser.add_argument("--output",required=True,type=Path); parser.add_argument("--columns",type=int,default=2); parser.add_argument("--thumb-width",type=int,default=640); args=parser.parse_args()
    if args.columns < 1 or args.thumb_width < 64: print("invalid columns or thumb width",file=sys.stderr); return 2
    opened=[]
    try:
        for path in args.image: opened.append((path,Image.open(path).convert("RGB")))
    except OSError as exc: print(f"cannot read image: {exc}",file=sys.stderr); return 2
    label_h=32; cells=[]
    for path,img in opened:
        height=max(1,round(img.height*args.thumb_width/img.width)); thumb=img.resize((args.thumb_width,height)); cells.append((path,thumb))
    cell_h=max(img.height for _,img in cells)+label_h; rows=math.ceil(len(cells)/args.columns)
    sheet=Image.new("RGB",(args.columns*args.thumb_width,rows*cell_h),(32,32,32)); draw=ImageDraw.Draw(sheet)
    for index,(path,img) in enumerate(cells):
        x=(index%args.columns)*args.thumb_width; y=(index//args.columns)*cell_h; sheet.paste(img,(x,y)); draw.text((x+8,y+cell_h-label_h+8),path.name,fill=(240,240,240))
    args.output.parent.mkdir(parents=True,exist_ok=True); sheet.save(args.output); print(str(args.output)); return 0


if __name__ == "__main__": raise SystemExit(main())
