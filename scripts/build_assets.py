#!/usr/bin/env python3
"""Regenerate the SVG artwork used by profile/README.md.

GitHub serves README images as static files, so they cannot load web fonts.
This script outlines the brand typefaces into paths so the banner and badges
look the same everywhere, in light and dark themes.

Usage:
    python3 scripts/build_assets.py --fonts /path/to/fonts

The fonts directory needs SchibstedGrotesk-Bold.ttf and GeistMono-Medium.ttf
(both SIL Open Font License). They ship in simyl-corporate under
apps/web/assets/fonts. Requires fontTools: pip install fonttools

To change a badge, edit BADGES below and run the script again.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"

# Brand colours. Orange is Pantone 144; navy lightens on dark backgrounds.
ORANGE = "#ED8B00"
NAVY = "#324667"
NAVY_ON_DARK = "#4A6A94"
INK = "#1F1711"  # text on light backgrounds
INK_ON_DARK = "#ECE8E3"  # text on dark backgrounds
INK_ON_ORANGE = "#2A1608"  # dark ink, never white, on orange
WHITE = "#FFFFFF"

# The S-mark: two congruent curves, one rotated 180 degrees.
S_CURVE = (
    "M 280 88 H 793 C 873 88 936 162 936 251 V 708 C 889 561 810 486 661 453 "
    "C 576 433 491 431 415 420 C 302 405 214 367 168 307 C 144 276 132 244 "
    "132 214 C 132 152 222 88 280 88 Z"
)
MARK_ORIGIN = 35.5  # the mark's artwork starts here on both axes
MARK_EXTENT = 953  # and spans this many units

# (file name, label, value, value style). A badge with no label is a single
# pill. Value styles: "orange" (dark ink on orange) or "navy" (white on navy).
BADGES = [
    ("website", "website", "simyl.ai", "orange"),
    ("products", "products", "4", "orange"),
    ("courses", "free courses", "6", "orange"),
    ("location", "based in", "Toronto", "orange"),
    ("status-private-preview", None, "Private preview", "orange"),
    ("status-coming-soon", None, "Coming soon", "navy"),
]


class Face:
    """A font that can turn a string into one SVG path."""

    def __init__(self, path: Path):
        self.font = TTFont(str(path))
        self.glyphs = self.font.getGlyphSet()
        self.cmap = self.font.getBestCmap()
        self.advances = self.font["hmtx"]
        self.units = self.font["head"].unitsPerEm

    def width(self, text: str, size: float, tracking: float = 0.0) -> float:
        scale = size / self.units
        total = sum(self.advances[self.cmap[ord(c)]][0] * scale for c in text)
        return total + tracking * size * max(len(text) - 1, 0)

    def path(
        self, text: str, x: float, baseline: float, size: float, tracking: float = 0.0
    ) -> str:
        scale = size / self.units
        pen = SVGPathPen(self.glyphs, ntos=lambda v: f"{v:.1f}".rstrip("0").rstrip("."))
        cursor = x
        for char in text:
            name = self.cmap[ord(char)]
            placed = TransformPen(pen, (scale, 0, 0, -scale, cursor, baseline))
            self.glyphs[name].draw(placed)
            cursor += self.advances[name][0] * scale + tracking * size
        return pen.getCommands()


def mark(x: float, y: float, size: float, navy: str) -> str:
    scale = size / MARK_EXTENT
    return (
        f'<g transform="translate({x} {y}) scale({scale:.5f}) '
        f'translate({-MARK_ORIGIN} {-MARK_ORIGIN})">'
        f'<path fill="{ORANGE}" d="{S_CURVE}"/>'
        f'<path fill="{navy}" transform="rotate(180 512 512)" d="{S_CURVE}"/>'
        "</g>"
    )


def logo(navy: str) -> str:
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" width="1024" height="1024" '
        f'viewBox="{MARK_ORIGIN} {MARK_ORIGIN} {MARK_EXTENT} {MARK_EXTENT}" '
        'role="img" aria-label="Simyl">'
        f'<path fill="{ORANGE}" d="{S_CURVE}"/>'
        f'<path fill="{navy}" transform="rotate(180 512 512)" d="{S_CURVE}"/>'
        "</svg>\n"
    )


def banner(display: Face, mono: Face, ink: str, navy: str) -> str:
    width, height = 1280, 400
    left = 8
    headline = 132
    tracking = -0.045
    line_one = display.path("Simplify", left, 204, headline, tracking)
    line_two_text = "your life"
    line_two = display.path(line_two_text, left, 330, headline, tracking)
    dot_x = left + display.width(line_two_text, headline, tracking) + tracking * headline
    dot = display.path(".", dot_x, 330, headline, tracking)
    note = mono.path("products for software teams", left + 4, 62, 22, 0.02)
    mark_size = 336
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" role="img" '
        'aria-label="Simyl. Simplify your life. Products for software teams.">'
        f'<path fill="{ORANGE}" d="{note}"/>'
        f'<path fill="{ink}" d="{line_one}"/>'
        f'<path fill="{ink}" d="{line_two}"/>'
        f'<path fill="{ORANGE}" d="{dot}"/>'
        f"{mark(width - mark_size - 8, (height - mark_size) / 2, mark_size, navy)}"
        "</svg>\n"
    )


def badge(mono: Face, label: str | None, value: str, style: str) -> str:
    height, size, pad, radius = 28, 13, 11, 5
    baseline = 18.6
    fill, text = (ORANGE, INK_ON_ORANGE) if style == "orange" else (NAVY, WHITE)
    value_width = mono.width(value, size) + pad * 2
    if label is None:
        total = value_width
        body = (
            f'<rect width="{total:.1f}" height="{height}" rx="{radius}" fill="{fill}"/>'
            f'<path fill="{text}" d="{mono.path(value, pad, baseline, size)}"/>'
        )
        title = value
    else:
        label_width = mono.width(label, size) + pad * 2
        total = label_width + value_width
        body = (
            f'<clipPath id="r"><rect width="{total:.1f}" height="{height}" rx="{radius}"/></clipPath>'
            '<g clip-path="url(#r)">'
            f'<rect width="{label_width:.1f}" height="{height}" fill="{NAVY}"/>'
            f'<rect x="{label_width:.1f}" width="{value_width:.1f}" height="{height}" fill="{fill}"/>'
            "</g>"
            f'<path fill="{WHITE}" d="{mono.path(label, pad, baseline, size)}"/>'
            f'<path fill="{text}" d="{mono.path(value, label_width + pad, baseline, size)}"/>'
        )
        title = f"{label}: {value}"
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{total:.1f}" height="{height}" '
        f'viewBox="0 0 {total:.1f} {height}" role="img" aria-label="{title}">'
        f"{body}</svg>\n"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--fonts", required=True, type=Path, help="directory with the brand fonts")
    args = parser.parse_args()

    display = Face(args.fonts / "SchibstedGrotesk-Bold.ttf")
    mono = Face(args.fonts / "GeistMono-Medium.ttf")

    outputs = {
        ASSETS / "logo.svg": logo(NAVY),
        ASSETS / "logo-dark.svg": logo(NAVY_ON_DARK),
        ASSETS / "banner-light.svg": banner(display, mono, INK, NAVY),
        ASSETS / "banner-dark.svg": banner(display, mono, INK_ON_DARK, NAVY_ON_DARK),
    }
    for name, label, value, style in BADGES:
        outputs[ASSETS / "badges" / f"{name}.svg"] = badge(mono, label, value, style)

    for path, svg in outputs.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(svg)
        print(f"wrote {path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
