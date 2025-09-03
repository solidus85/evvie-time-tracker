#!/usr/bin/env python3
"""
Create a circular ICO (transparent background) from a PNG.

This script:
  1) Loads a PNG (with or without alpha)
  2) Center-crops to a square using the smaller dimension
  3) Applies a circular mask (full-size circle) to make corners transparent
  4) Exports a multi-resolution ICO file with the given sizes

Usage examples:
  # Basic usage: circle-crop favicon.png and write multi-size favicon.ico
  python scripts/png_to_circle_ico.py static/favicon.png static/favicon.ico

  # Specify sizes and a slight inset (to avoid hard clipping at the edge)
  python scripts/png_to_circle_ico.py static/favicon.png static/favicon.ico \
         --sizes 16,32,48,64,128,256 --inset 2

Requires: Pillow
  pip install Pillow
"""

import argparse
import sys
from typing import List, Tuple

try:
    from PIL import Image, ImageDraw, ImageChops
except ImportError:
    print("Error: Pillow is required. Install with `pip install Pillow`.", file=sys.stderr)
    sys.exit(1)


def parse_sizes(s: str) -> List[Tuple[int, int]]:
    try:
        vals = [int(x) for x in s.split(',') if x.strip()]
        if not vals:
            raise ValueError
        return [(v, v) for v in vals]
    except Exception:
        raise argparse.ArgumentTypeError("--sizes must be a comma-separated list of integers, e.g. 16,32,48")


def center_crop_to_square(img: Image.Image) -> Image.Image:
    w, h = img.size
    if w == h:
        return img
    side = min(w, h)
    left = (w - side) // 2
    top = (h - side) // 2
    right = left + side
    bottom = top + side
    return img.crop((left, top, right, bottom))


def apply_circle_mask(img: Image.Image, inset: int = 0) -> Image.Image:
    """Apply a circular alpha mask to an RGBA image. inset shrinks the circle a bit (pixels)."""
    if img.mode != 'RGBA':
        img = img.convert('RGBA')
    w, h = img.size
    # Build circular mask
    mask = Image.new('L', (w, h), 0)
    draw = ImageDraw.Draw(mask)
    # Insets all sides to avoid hard clipping at the very edge if desired
    draw.ellipse((inset, inset, w - 1 - inset, h - 1 - inset), fill=255)

    # Combine existing alpha with mask (keep existing transparency inside circle)
    r, g, b, a = img.split()
    combined_alpha = ImageChops.multiply(a, mask)
    out = Image.merge('RGBA', (r, g, b, combined_alpha))
    return out


def main():
    parser = argparse.ArgumentParser(description="Create a circular ICO from a PNG, with transparent background.")
    parser.add_argument('input', help='Path to source PNG (e.g., static/favicon.png)')
    parser.add_argument('output', help='Path to destination ICO (e.g., static/favicon.ico)')
    parser.add_argument('--sizes', type=parse_sizes, default=parse_sizes('16,32,48,64,128,256'),
                        help='Comma-separated icon sizes. Default: 16,32,48,64,128,256')
    parser.add_argument('--inset', type=int, default=0,
                        help='Shrink circle by this many pixels from each edge (default 0)')

    args = parser.parse_args()

    img = Image.open(args.input).convert('RGBA')
    img = center_crop_to_square(img)
    img = apply_circle_mask(img, inset=args.inset)

    sizes = sorted({s[0] for s in args.sizes})
    # Save as multi-resolution ICO
    largest = max(sizes)
    base = img.resize((largest, largest), Image.LANCZOS)
    base.save(args.output, format='ICO', sizes=[(s, s) for s in sizes])
    print(f"Wrote circular ICO: {args.output} with sizes: {sizes}")


if __name__ == '__main__':
    main()

