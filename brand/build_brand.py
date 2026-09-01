# -*- coding: utf-8 -*-
"""चिह्नरचना — generate the Vāk logo and icons.

The letterforms are not traced by hand.  They are the real outlines from a
Devanagari font, shaped by HarfBuzz (so the virama sits under the क where it
belongs) and converted to SVG paths — so the mark needs no font installed to
render, anywhere.

    pip install fonttools uharfbuzz pillow
    python brand/build_brand.py

Design notes
------------
मसी — the palette is the one the whole project uses: manuscript ink indigo,
and haritāla, the orpiment yellow Indian manuscripts used for headings.

The mark is वा, the first syllable of वाक्.  Devanagari hangs its letters from
a शिरोरेखा, a head-line, and वा gives you that head-line spanning two verticals
— which is exactly the silhouette that survives being shrunk to the 16 pixels a
file tree gives you.  The full word वाक् is the wordmark; it is too intricate
to be an icon and is never used as one.
"""
import pathlib
import sys

from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.ttLib import TTCollection
import uharfbuzz as hb

ROOT = pathlib.Path(__file__).resolve().parent
FONT = "C:/Windows/Fonts/Nirmala.ttc"
FACE_INDEX = 1                      # Nirmala UI Bold — the weight that holds at 16px

INK = "#16223f"       # मसी — manuscript ink
GOLD = "#d8a94a"      # हरिताल — orpiment
GOLD_DEEP = "#a8781f"
PAPER = "#f7f6f1"


# --------------------------------------------------------------------- glyphs
def outlines(text: str):
    """Real outlines, properly shaped: [(svg path, x, y)], plus the advance."""
    data = pathlib.Path(FONT).read_bytes()
    face = hb.Face(data, FACE_INDEX)
    font = hb.Font(face)
    buf = hb.Buffer()
    buf.add_str(text)
    buf.guess_segment_properties()
    hb.shape(font, buf)

    tt = TTCollection(FONT).fonts[FACE_INDEX]
    order = tt.getGlyphOrder()
    glyphs = tt.getGlyphSet()

    paths, x = [], 0
    for info, pos in zip(buf.glyph_infos, buf.glyph_positions):
        pen = SVGPathPen(glyphs)
        glyphs[order[info.codepoint]].draw(pen)
        d = pen.getCommands()
        if d:
            paths.append((d, x + pos.x_offset, pos.y_offset))
        x += pos.x_advance
    return paths, x, face.upem


def glyph_group(text: str, fill: str, scale: float, dx: float, dy: float) -> tuple:
    """The text as one <g>, already scaled and placed.  Returns (svg, width)."""
    paths, advance, upem = outlines(text)
    k = scale / upem
    body = "\n".join(
        f'    <path d="{d}" transform="translate({ox * k:.2f} {-oy * k:.2f})"/>'
        for d, ox, oy in paths
    )
    # the font's y grows upward, SVG's grows downward
    g = (f'  <g fill="{fill}" transform="translate({dx:.2f} {dy:.2f}) '
         f'scale({k:.6f} {-k:.6f})">\n'
         + "\n".join(f'    <path d="{d}" transform="translate({ox} {oy})"/>'
                     for d, ox, oy in paths)
         + "\n  </g>")
    return g, advance * k


def svg(width: float, height: float, body: str, title: str) -> str:
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width:g} {height:g}" '
            f'width="{width:g}" height="{height:g}" role="img" aria-label="{title}">\n'
            f'  <title>{title}</title>\n{body}\n</svg>\n')


# ------------------------------------------------------------------ the icon
def build_icon(tile: bool, fg: str, bg: str | None, name: str, size: int = 64):
    """वा — the mark.  `tile` gives it a ground, for app and marketplace use;
    without one it is a bare glyph, which is what a file tree wants."""
    pad = size * 0.19
    inner = size - 2 * pad
    g, w = glyph_group("वा", fg, inner, 0, 0)

    # centre it on the tile
    paths, advance, upem = outlines("वा")
    k = inner / upem
    # Devanagari sits below the head-line; nudge so the optical centre lands right
    dx = (size - advance * k) / 2
    dy = size - pad - inner * 0.12

    body = ""
    if tile:
        r = size * 0.18
        body += (f'  <rect width="{size}" height="{size}" rx="{r:g}" ry="{r:g}" '
                 f'fill="{bg}"/>\n')
    body += (f'  <g fill="{fg}" transform="translate({dx:.2f} {dy:.2f}) '
             f'scale({k:.6f} {-k:.6f})">\n'
             + "\n".join(f'    <path d="{d}" transform="translate({ox} {oy})"/>'
                         for d, ox, oy in paths)
             + "\n  </g>")
    out = svg(size, size, body, "वाक् · Vāk")
    (ROOT / name).write_text(out, encoding="utf-8")
    return name


# --------------------------------------------------------------- the wordmark
def build_wordmark(name: str, ink: str, accent: str, height: int = 120):
    """वाक् — the full word, with the danda in haritāla."""
    cap = height * 0.62
    paths, advance, upem = outlines("वाक्")
    k = cap / upem
    dpaths, dadv, _ = outlines("।")

    pad = height * 0.18
    gap = height * 0.10
    width = pad + advance * k + gap + dadv * k + pad
    base = height * 0.74

    body = (f'  <g fill="{ink}" transform="translate({pad:.2f} {base:.2f}) '
            f'scale({k:.6f} {-k:.6f})">\n'
            + "\n".join(f'    <path d="{d}" transform="translate({ox} {oy})"/>'
                        for d, ox, oy in paths)
            + "\n  </g>\n")
    body += (f'  <g fill="{accent}" transform="translate('
             f'{pad + advance * k + gap:.2f} {base:.2f}) scale({k:.6f} {-k:.6f})">\n'
             + "\n".join(f'    <path d="{d}" transform="translate({ox} {oy})"/>'
                         for d, ox, oy in dpaths)
             + "\n  </g>")
    out = svg(round(width), height, body, "वाक् · Vāk")
    (ROOT / name).write_text(out, encoding="utf-8")
    return name


# --------------------------------------------------------------------- raster
def rasterise(sizes=(16, 32, 48, 128, 256)):
    """PNGs for the places that will not take an SVG — the extension listing,
    and the .ico.  Pillow draws the glyph directly from the same font."""
    from PIL import Image, ImageDraw, ImageFont
    made = []
    for size in sizes:
        img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        r = size * 0.18
        d.rounded_rectangle([0, 0, size - 1, size - 1], radius=r, fill=INK)
        try:
            f = ImageFont.truetype(FONT, int(size * 0.62), index=FACE_INDEX)
            box = d.textbbox((0, 0), "वा", font=f)
            d.text(((size - (box[2] - box[0])) / 2 - box[0],
                    (size - (box[3] - box[1])) / 2 - box[1]),
                   "वा", font=f, fill=GOLD)
        except Exception as err:                       # pragma: no cover
            print(f"  (raster {size}px: {err})")
        name = f"icon-{size}.png"
        img.save(ROOT / name)
        made.append(name)
    # an .ico for the websites — Pillow derives every size from the largest,
    # so it must be handed the 256 and told which sizes to keep
    from PIL import Image as I
    I.open(ROOT / "icon-256.png").save(
        ROOT / "favicon.ico", format="ICO",
        sizes=[(s, s) for s in (16, 24, 32, 48, 64, 128, 256)])
    made.append("favicon.ico")
    return made


if __name__ == "__main__":
    if not pathlib.Path(FONT).exists():
        sys.exit(f"needs a Devanagari font at {FONT}")
    made = [
        build_icon(True, GOLD, INK, "vak-icon.svg"),          # app / marketplace
        build_icon(False, GOLD_DEEP, None, "vak-file-light.svg"),  # light editors
        build_icon(False, GOLD, None, "vak-file-dark.svg"),        # dark editors
        build_wordmark("vak-wordmark.svg", INK, GOLD_DEEP),
        build_wordmark("vak-wordmark-dark.svg", PAPER, GOLD),
    ]
    made += rasterise()
    print("wrote:")
    for m in made:
        print("   brand/" + m)
