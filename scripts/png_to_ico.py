#!/usr/bin/env python3
"""
PNG ➜ ICO converter with optional background-to-transparent processing.

Usage examples:
  # Basic multi-size ICO
  python scripts/png_to_ico.py static/favicon.png static/favicon.ico --sizes 16,32,48,64,128

  # Make the top-left pixel color transparent (recommended)
  python scripts/png_to_ico.py static/favicon.png static/favicon.ico --transparent-from-topleft --tolerance 8

  # Legacy: make near-white pixels transparent
  python scripts/png_to_ico.py static/favicon.png static/favicon.ico --white-to-transparent --threshold 250

Requires: Pillow (PIL)
  pip install Pillow
"""

import argparse
import sys
from typing import List, Tuple

try:
    from PIL import Image
except ImportError:
    print("Error: Pillow is required. Install with `pip install Pillow`.", file=sys.stderr)
    sys.exit(1)


def parse_sizes(s: str) -> List[Tuple[int, int]]:
    try:
        vals = [int(x) for x in s.split(',') if x.strip()]
        return [(v, v) for v in vals]
    except Exception:
        raise argparse.ArgumentTypeError("--sizes must be a comma-separated list of integers, e.g. 16,32,48")


def make_white_transparent(img: Image.Image, threshold: int = 250) -> Image.Image:
    """Convert near-white pixels to fully transparent.
    threshold: 0..255 – higher converts more off-white pixels.
    """
    if img.mode != 'RGBA':
        img = img.convert('RGBA')
    datas = img.getdata()
    new_data = []
    for r, g, b, a in datas:
        if r >= threshold and g >= threshold and b >= threshold:
            new_data.append((r, g, b, 0))
        else:
            new_data.append((r, g, b, a))
    img.putdata(new_data)
    return img


def make_color_transparent(img: Image.Image, color: tuple, tolerance: int = 0) -> Image.Image:
    """Convert pixels matching the given color to transparent.
    - color: (R, G, B[, A]) tuple. Alpha in color is ignored for matching.
    - tolerance: max absolute per-channel diff to still consider a match.
    """
    if img.mode != 'RGBA':
        img = img.convert('RGBA')
    # Normalize color to RGB
    if len(color) == 4:
        cr, cg, cb, _ = color
    else:
        cr, cg, cb = color[:3]
    datas = img.getdata()
    new_data = []
    for r, g, b, a in datas:
        if (
            abs(r - cr) <= tolerance and
            abs(g - cg) <= tolerance and
            abs(b - cb) <= tolerance
        ):
            new_data.append((r, g, b, 0))
        else:
            new_data.append((r, g, b, a))
    img.putdata(new_data)
    return img


def fit_to_square(img: Image.Image, bg=(0, 0, 0, 0)) -> Image.Image:
    """Pad the image with transparent pixels to make it square, preserving content."""
    w, h = img.size
    if w == h:
        return img
    size = max(w, h)
    square = Image.new('RGBA', (size, size), bg)
    offset = ((size - w) // 2, (size - h) // 2)
    square.paste(img, offset)
    return square


def main():
    parser = argparse.ArgumentParser(description="Convert PNG to multi-size ICO with optional white-to-transparent.")
    parser.add_argument('input', help='Path to source PNG')
    parser.add_argument('output', help='Path to destination ICO')
    parser.add_argument('--sizes', type=parse_sizes, default=parse_sizes('16,32,48,64,128'),
                        help='Comma-separated icon sizes (pixels). Default: 16,32,48,64,128')
    parser.add_argument('--white-to-transparent', action='store_true',
                        help='Convert near-white background to transparent (threshold 250)')
    parser.add_argument('--transparent-from-topleft', action='store_true',
                        help='Use top-left pixel color as background and make it transparent')
    parser.add_argument('--threshold', type=int, default=250,
                        help='Threshold for white-to-transparent (0-255). Default: 250')
    parser.add_argument('--tolerance', type=int, default=0,
                        help='Color tolerance for transparent-from-topleft (0-255). Default: 0')

    args = parser.parse_args()

    img = Image.open(args.input)
    img = img.convert('RGBA')
    img = fit_to_square(img)
    if args.transparent_from_topleft:
        # Determine background color from top-left pixel
        bg_color = img.getpixel((0, 0))
        img = make_color_transparent(img, bg_color, tolerance=args.tolerance)
    elif args.white_to_transparent:
        img = make_white_transparent(img, threshold=args.threshold)

    # Generate resized versions
    sizes = sorted({s[0] for s in args.sizes})
    resized = [img.resize((s, s), Image.LANCZOS) for s in sizes]

    # Save as ICO with multiple sizes
    # Pillow accepts saving the largest image with sizes= to embed multi-res
    largest = max(sizes)
    base = img.resize((largest, largest), Image.LANCZOS)
    base.save(args.output, format='ICO', sizes=[(s, s) for s in sizes])
    print(f"Wrote ICO: {args.output} with sizes: {sizes}")


if __name__ == '__main__':
    main()
