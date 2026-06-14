#!/usr/bin/env python3
"""
24dots_banner.py -- Print a string as a banner on continuous-feed paper.
Copyright (C) 2026  Dillon Feeney.

  This program is free software: you can redistribute it and/or modify
  it under the terms of the GNU General Public License as published by
  the Free Software Foundation, either version 3 of the License, or
  (at your option) any later version.

  This program is distributed in the hope that it will be useful,
  but WITHOUT ANY WARRANTY; without even the implied warranty of
  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
  GNU General Public License for more details.

  You should have received a copy of the GNU General Public License
  along with this program.  If not, see <https://www.gnu.org/licenses/>.
  See the COPYING file for licence details.

Created: 2026-06-14
Updated: 2026-06-14

Remember the printed office banners of the '90s?  This script does that on a
dot-matrix printer.  Pass a string to the script, the string is rendered with a
scalable font, rotated 90 degrees, and emitted as ESC/P 2 24-pin bit-image
graphics.  Character height equals the printable paper width; the banner runs
along the length of the feed.

Built-in ESC/P 2 fonts cannot do this.  Their largest scaling (double/quad
height, or multipoint mode) tops out near 0.5 inch.  Reaching a character
height of the full paper width (8 inch) requires graphics output.

Enjoy the miniature time machine.

Usage:
    24dots_banner.py STRING                   # emit ESC/P 2 to stdout
    24dots_banner.py STRING --preview F.png   # write the 1-bit bitmap to
                                              # F.png, no ESC/P
    24dots_banner.py STRING | lp -d PRINTER -o raw

Environment overrides:
    BANNER_WIDTH_IN     printable width in inches             (default 8.0)
    BANNER_MARGIN_IN    blank margin each side in inches      (default 0.25)
    BANNER_FONT         path to a TrueType/OpenType font
                        (default DejaVuSans-Bold)
    BANNER_DENSITY      how dark the printed text should be,  (default 0.2)
                        accepts `light` (0.2, default),
                        `lighter` (0.1), `half` (0.5), or
                        `full` (1.0), or any fractional value

TODOs:
[ ] Print ASCII characters for the shapes of the letters (instead of a font).
      See: https://github.com/owise1/dotmatrixbanners/
[ ] Provide a few font variants, including a "font outline" if you don't want
      to print the full centre of the character.
[ ] Advise how many sheets of paper might get used.
"""

import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ESC = b"\x1b"
DPI = 180        # ESC * mode 39: 180 dpi horizontal, 180 dpi vertical (square)
BAND = 24        # 24 pins per pass
MODE = 39


def build_bitmap(text):
    """
    Render the banner string to a 1-bit image sized for the paper.

    The text is drawn horizontally, rotated ninety degrees, then scaled so
    the character height equals the printable paper width (BANNER_WIDTH_IN
    less the side margins).  Width, margin, and font are read from the
    environment.

    Args:
        text: the string to render.

    Returns:
        An L-mode :class:`PIL.Image.Image` the full paper width wide, in which
        a value of 255 marks ink and 0 marks blank paper.

    Raises:
        ValueError: if the string renders to an empty box.
    """
    width_in = float(os.environ.get("BANNER_WIDTH_IN", "8.0"))
    margin_in = float(os.environ.get("BANNER_MARGIN_IN", "0.25"))
    font_path = os.environ.get(
        "BANNER_FONT", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    )

    paper_dots = round(width_in * DPI)
    text_dots = paper_dots - 2 * round(margin_in * DPI)
    if text_dots < 1:
        text_dots = paper_dots

    font = ImageFont.truetype(font_path, 400)

    probe = ImageDraw.Draw(Image.new("L", (1, 1)))
    bbox = probe.textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    if tw <= 0 or th <= 0:
        raise ValueError("nothing to render")

    glyphs = Image.new("L", (tw, th), 0)
    ImageDraw.Draw(glyphs).text(
        (-bbox[0], -bbox[1]), text, fill=255, font=font
    )

    glyphs = glyphs.rotate(-90, expand=True)          # height -> across paper
    scale = text_dots / glyphs.width                  # fit character height
    glyphs = glyphs.resize(
        (text_dots, max(1, round(glyphs.height * scale))), Image.LANCZOS
    )

    canvas = Image.new("L", (paper_dots, glyphs.height), 0)
    canvas.paste(glyphs, ((paper_dots - text_dots) // 2, 0))
    return canvas.point(lambda v: 255 if v >= 128 else 0, "L")


def _density():
    """
    Resolve the dot-coverage fraction from the environment.

    Reads ``BANNER_DENSITY`` and maps it to the fraction of glyph dots to
    fire: 1.0 is solid, lower values thin the ink through the ordered-dither
    mask.  The value is either a named level -- ``lighter`` (0.1), ``light``
    (0.2), ``half`` (0.5), or ``full`` (1.0) -- or any literal float such as
    ``0.35``.  When unset it defaults to ``light``.

    Returns:
        The coverage fraction as a float.

    Raises:
        ValueError: if the value is neither a known name nor a number.
    """
    v = os.environ.get("BANNER_DENSITY", "light")
    named = {
        "lighter": 0.1,
        "light": 0.2,
        "half": 0.5,
        "full": 1.0,
    }
    return named[v] if v in named else float(v)


def _bayer(n):
    """
    Return an ``n`` x ``n`` Bayer ordered-dither threshold matrix.

    ``n`` must be a power of two.  Cell values run from 0 to ``n*n - 1``;
    cells with lower values are the ones kept when thinning dots, so the
    pattern stays evenly spread at any density.

    Args:
        n: side length of the matrix, a power of two.

    Returns:
        An ``(n, n)`` integer :class:`numpy.ndarray` of thresholds.
    """
    m = np.array([[0]])
    while m.shape[0] < n:
        m = np.block([[4 * m, 4 * m + 2], [4 * m + 3, 4 * m + 1]])
    return m


def emit_escp(img, out):
    """
    Write ESC/P 2 bit-image graphics for ``img`` to a binary stream.

    Each pixel at or above mid-grey fires a pin.  When ``DENSITY`` is below
    1.0 an ordered-dither mask keeps roughly that fraction of the inked dots.
    Output is a reset, a 24/180-inch line spacing, then one ``ESC * 39`` band
    per 24 dot rows (180 dpi, square), a form feed, and a final reset.

    Args:
        img: an L-mode image as returned by :func:`build_bitmap`.
        out: a writable binary stream, typically ``sys.stdout.buffer``.
    """

    arr = np.asarray(img) >= 128                      # (H, W) bool
    height, width = arr.shape
    frac = _density()
    if frac < 1.0:
        m = _bayer(8) / 64.0                          # thresholds 0..<1
        tile = np.tile(m, (height // 8 + 1, width // 8 + 1))[:height, :width]
        arr = arr & (tile < frac)                     # keep ~frac of inked dots
    nl, nh = width & 0xFF, (width >> 8) & 0xFF
    header = ESC + b"*" + bytes([MODE, nl, nh])

    out.write(ESC + b"@")                             # reset
    out.write(ESC + b"3" + bytes([BAND]))             # 24/180" line spacing
    for y in range(0, height, BAND):
        sub = arr[y : y + BAND, :]
        if sub.shape[0] < BAND:
            sub = np.vstack([sub, np.zeros((BAND - sub.shape[0], width), bool)])
        out.write(header)
        out.write(np.packbits(sub, axis=0).T.tobytes()) # column-major, 3 B/col
        out.write(b"\r\n")
    out.write(b"\x0c")                                # form feed past perf
    out.write(ESC + b"@")


def main(argv):
    """
    Command-line entry point.

    ``argv[1]`` is the banner string.  An optional ``--preview FILE.png``
    in ``argv[2:4]`` writes the bitmap to that file instead of emitting
    ESC/P, which lets the output be checked before paper is used.

    Args:
        argv: the argument vector, normally ``sys.argv``.

    Returns:
        A process exit code: 0 on success, 1 on a usage error.
    """
    if len(argv) < 2:
        sys.stderr.write(
            "usage: 24dots_banner.py STRING [--preview FILE.png]\n"
        )
        return 1
    text = argv[1]
    img = build_bitmap(text)

    if len(argv) >= 4 and argv[2] == "--preview":
        img.save(argv[3])
        sys.stderr.write(f"preview {img.width}x{img.height} -> {argv[3]}\n")
        return 0

    emit_escp(img, sys.stdout.buffer)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
