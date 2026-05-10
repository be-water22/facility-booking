"""Generates concept mockups (1200x1600 PNG) for the six game ideas.

Run:  python3 scripts/generate_concept_mockups.py
Output: images/concept_<idea>.png
"""

from __future__ import annotations

import math
import os
import random
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H = 1200, 1600
OUT = Path(__file__).resolve().parent.parent / "images"
OUT.mkdir(exist_ok=True)

# Design system
INDIGO_DEEP = (15, 18, 40)
INDIGO = (26, 27, 58)
INDIGO_SOFT = (42, 45, 92)
SAFFRON = (255, 122, 26)
SAFFRON_SOFT = (242, 166, 90)
GOLD = (232, 197, 71)
GOLD_SOFT = (212, 175, 55)
CREAM = (245, 241, 232)
WHITE = (255, 255, 255)
RED = (230, 57, 70)
GREEN = (124, 198, 159)
BLUE = (98, 153, 224)

FONT_DIR = "/usr/share/fonts/truetype/dejavu"


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    name = "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"
    return ImageFont.truetype(os.path.join(FONT_DIR, name), size)


def base_canvas() -> tuple[Image.Image, ImageDraw.ImageDraw]:
    img = Image.new("RGB", (W, H), INDIGO_DEEP)
    d = ImageDraw.Draw(img, "RGBA")
    # Vignette / gradient backdrop.
    grad = Image.new("RGB", (W, H), INDIGO_DEEP)
    gd = ImageDraw.Draw(grad)
    for y in range(H):
        t = y / H
        r = int(INDIGO_DEEP[0] * (1 - t) + INDIGO[0] * t)
        g = int(INDIGO_DEEP[1] * (1 - t) + INDIGO[1] * t)
        b = int(INDIGO_DEEP[2] * (1 - t) + INDIGO[2] * t)
        gd.line([(0, y), (W, y)], fill=(r, g, b))
    img = grad
    d = ImageDraw.Draw(img, "RGBA")
    return img, d


def draw_header(d: ImageDraw.ImageDraw, eyebrow: str, title: str, subtitle: str) -> None:
    d.text((80, 110), eyebrow, fill=GOLD, font=font(28, bold=True))
    d.text((80, 150), title, fill=WHITE, font=font(78, bold=True))
    d.text((80, 250), subtitle, fill=CREAM, font=font(30))


def draw_footer(d: ImageDraw.ImageDraw, mechanic: str) -> None:
    d.rounded_rectangle((80, H - 150, W - 80, H - 80), radius=24, fill=(255, 255, 255, 18))
    d.text((110, H - 135), "RULE", fill=GOLD, font=font(22, bold=True))
    d.text((110, H - 105), mechanic, fill=WHITE, font=font(28))


def add_glow(layer: Image.Image, radius: int = 18) -> Image.Image:
    return layer.filter(ImageFilter.GaussianBlur(radius))


# ---------------------------------------------------------------------------
# 1. Resonance — clockwork polyrhythm puzzle
# ---------------------------------------------------------------------------
def draw_resonance() -> None:
    img, d = base_canvas()
    draw_header(
        d,
        "01  RESONANCE",
        "Tune the Machine",
        "Compose a polyrhythm by arranging mechanical parts.",
    )

    # Workbench panel
    panel = (80, 320, W - 80, 1340)
    d.rounded_rectangle(panel, radius=32, fill=(255, 255, 255, 12), outline=GOLD_SOFT, width=2)

    # Three pendulums with arc traces
    pend_y = 520
    for i, period in enumerate([2, 3, 5]):
        cx = 280 + i * 320
        # ceiling
        d.line([(cx - 110, pend_y - 80), (cx + 110, pend_y - 80)], fill=GOLD_SOFT, width=4)
        # arc trace
        for a in range(-60, 61, 6):
            x = cx + math.sin(math.radians(a)) * 240
            y = pend_y - 80 + math.cos(math.radians(a)) * 240
            alpha = int(30 + 80 * (1 - abs(a) / 60))
            d.ellipse((x - 3, y - 3, x + 3, y + 3), fill=(255, 255, 255, alpha))
        # rod + bob
        angle = math.radians({2: -35, 3: 10, 5: 45}[period])
        bx = cx + math.sin(angle) * 240
        by = pend_y - 80 + math.cos(angle) * 240
        d.line([(cx, pend_y - 80), (bx, by)], fill=CREAM, width=4)
        glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        gd = ImageDraw.Draw(glow)
        gd.ellipse((bx - 38, by - 38, bx + 38, by + 38), fill=SAFFRON + (200,))
        glow = add_glow(glow, radius=20)
        img.paste(glow, (0, 0), glow)
        d.ellipse((bx - 22, by - 22, bx + 22, by + 22), fill=SAFFRON, outline=WHITE, width=3)
        d.text((cx - 22, pend_y + 200), f"T={period}", fill=GOLD, font=font(34, bold=True))

    # Beat track
    track_y = 1080
    d.text((110, track_y - 60), "BEAT TRACK", fill=GOLD, font=font(24, bold=True))
    cells = 16
    cell_w = (W - 80 * 2 - 60) / cells
    for i in range(cells):
        x = 110 + i * cell_w
        on = i in {5, 8, 11, 14}  # target beats highlighted
        col = SAFFRON if on else (255, 255, 255, 35)
        d.rounded_rectangle((x, track_y, x + cell_w - 8, track_y + 70), radius=10, fill=col)
        if on:
            d.text((x + 16, track_y + 18), "♪", fill=WHITE, font=font(34, bold=True))
    d.line([(110 + cell_w * 12, track_y - 14), (110 + cell_w * 12, track_y + 86)], fill=GOLD, width=4)
    d.text((110 + cell_w * 12 - 18, track_y + 100), "NOW", fill=GOLD, font=font(20, bold=True))

    # Gear icon top right
    gx, gy = W - 230, 420
    for r in (60, 50, 40):
        d.ellipse((gx - r, gy - r, gx + r, gy + r), outline=GOLD_SOFT, width=3)
    for k in range(8):
        a = math.radians(k * 45)
        d.line(
            [(gx + math.cos(a) * 60, gy + math.sin(a) * 60), (gx + math.cos(a) * 80, gy + math.sin(a) * 80)],
            fill=GOLD_SOFT,
            width=6,
        )
    d.text((gx - 70, gy + 100), "T=7", fill=GOLD, font=font(32, bold=True))

    draw_footer(d, "All chimes must fire on tick 12.  Fewest parts wins.")
    img.save(OUT / "concept_01_resonance.png")


# ---------------------------------------------------------------------------
# 2. Lumen — optical physics puzzle
# ---------------------------------------------------------------------------
def draw_lumen() -> None:
    img, d = base_canvas()
    draw_header(
        d,
        "02  LUMEN",
        "Beam Chains",
        "Bend, split, and filter light to feed every target its recipe.",
    )

    # Grid
    grid_origin = (140, 360)
    grid_size = 920
    cells = 8
    cell = grid_size / cells
    for i in range(cells + 1):
        x = grid_origin[0] + i * cell
        y = grid_origin[1] + i * cell
        d.line([(x, grid_origin[1]), (x, grid_origin[1] + grid_size)], fill=(255, 255, 255, 24), width=1)
        d.line([(grid_origin[0], y), (grid_origin[0] + grid_size, y)], fill=(255, 255, 255, 24), width=1)

    def cell_center(cx: int, cy: int) -> tuple[float, float]:
        return grid_origin[0] + (cx + 0.5) * cell, grid_origin[1] + (cy + 0.5) * cell

    # Emitter (white) at (0,1)
    ex, ey = cell_center(0, 1)
    d.ellipse((ex - 28, ey - 28, ex + 28, ey + 28), fill=WHITE)
    d.text((ex - 90, ey + 36), "EMITTER", fill=CREAM, font=font(20, bold=True))

    # Mirror at (3,1)
    mx, my = cell_center(3, 1)
    d.line([(mx - 36, my - 36), (mx + 36, my + 36)], fill=GOLD, width=8)

    # Prism (triangle) at (3,4)
    px, py = cell_center(3, 4)
    d.polygon([(px, py - 50), (px - 45, py + 35), (px + 45, py + 35)], outline=WHITE, width=4)

    # Three colored targets
    target_specs = [(7, 1, RED), (7, 4, GREEN), (7, 7, BLUE)]
    for cx, cy, col in target_specs:
        tx, ty = cell_center(cx, cy)
        d.ellipse((tx - 30, ty - 30, tx + 30, ty + 30), outline=col, width=5)
        d.ellipse((tx - 12, ty - 12, tx + 12, ty + 12), fill=col)

    # Beam: emitter -> mirror, then split into RGB through prism into the three targets
    beam_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    bd = ImageDraw.Draw(beam_layer)

    # White beam emitter -> mirror
    bd.line([cell_center(0, 1), cell_center(3, 1)], fill=WHITE + (220,), width=8)
    # mirror reflects downward to prism
    bd.line([cell_center(3, 1), cell_center(3, 4)], fill=WHITE + (220,), width=8)
    # prism splits to red/green/blue targets
    for cx, cy, col in target_specs:
        bd.line([cell_center(3, 4), cell_center(cx, cy)], fill=col + (220,), width=6)

    glow = beam_layer.filter(ImageFilter.GaussianBlur(10))
    img.paste(glow, (0, 0), glow)
    img.paste(beam_layer, (0, 0), beam_layer)

    # Recipe pill
    d.rounded_rectangle((W - 380, 370, W - 100, 480), radius=20, fill=(255, 255, 255, 18))
    d.text((W - 360, 384), "TARGET RECIPE", fill=GOLD, font=font(20, bold=True))
    d.text((W - 360, 416), "RED 80% ·VPOL", fill=RED, font=font(24, bold=True))
    d.text((W - 360, 448), "GRN 60% ·HPOL", fill=GREEN, font=font(24, bold=True))

    draw_footer(d, "Hit each target with the right colour, intensity, polarization.")
    img.save(OUT / "concept_02_lumen.png")


# ---------------------------------------------------------------------------
# 3. Threadwork — Living Rangoli
# ---------------------------------------------------------------------------
def draw_threadwork() -> None:
    img, d = base_canvas()
    draw_header(
        d,
        "03  THREADWORK",
        "Living Rangoli",
        "Compose rules; let one stroke draw the whole pattern.",
    )

    cx_, cy_ = W // 2, 920
    R = 440

    # Pulli grid (dot lattice)
    for ring in range(7):
        rr = ring * 60
        n = max(1, ring * 6)
        for k in range(n):
            a = 2 * math.pi * k / n
            x = cx_ + math.cos(a) * rr
            y = cy_ + math.sin(a) * rr
            d.ellipse((x - 4, y - 4, x + 4, y + 4), fill=(255, 255, 255, 90))

    # Generative kolam: parametric petal pattern with 8-fold symmetry
    petal_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    pd = ImageDraw.Draw(petal_layer)

    def petal(angle_deg: float) -> None:
        pts = []
        for t in range(0, 361, 4):
            a = math.radians(t)
            r = 220 * abs(math.sin(2 * a)) ** 0.7
            x = cx_ + math.cos(a + math.radians(angle_deg)) * r
            y = cy_ + math.sin(a + math.radians(angle_deg)) * r
            pts.append((x, y))
        pd.line(pts, fill=GOLD + (235,), width=5)

    for k in range(8):
        petal(k * 45)

    # Outer ring lattice
    for k in range(48):
        a = 2 * math.pi * k / 48
        x1, y1 = cx_ + math.cos(a) * 300, cy_ + math.sin(a) * 300
        x2, y2 = cx_ + math.cos(a) * 360, cy_ + math.sin(a) * 360
        pd.line([(x1, y1), (x2, y2)], fill=SAFFRON + (180,), width=3)

    # Center motif
    pd.ellipse((cx_ - 30, cy_ - 30, cx_ + 30, cy_ + 30), outline=GOLD + (255,), width=4)
    pd.ellipse((cx_ - 12, cy_ - 12, cx_ + 12, cy_ + 12), fill=SAFFRON + (255,))

    glow = petal_layer.filter(ImageFilter.GaussianBlur(8))
    img.paste(glow, (0, 0), glow)
    img.paste(petal_layer, (0, 0), petal_layer)

    # Rule chip strip
    rules = ["TURN→", "MIRROR↕", "BRANCH⌥", "CLOSE⊙"]
    rx0 = 110
    for i, r in enumerate(rules):
        x = rx0 + i * 240
        d.rounded_rectangle((x, 370, x + 215, 430), radius=14, fill=(255, 255, 255, 20), outline=GOLD_SOFT, width=2)
        d.text((x + 18, 384), r, fill=CREAM, font=font(26, bold=True))

    draw_footer(d, "Smallest rule-set that reproduces the target wins.")
    img.save(OUT / "concept_03_threadwork.png")


# ---------------------------------------------------------------------------
# 4. Verdict — narrative deduction
# ---------------------------------------------------------------------------
def draw_verdict() -> None:
    img, d = base_canvas()
    draw_header(
        d,
        "04  VERDICT",
        "Logic Trials",
        "Find the liar before the case closes.",
    )

    # Corkboard frame
    board = (90, 350, W - 90, 1330)
    d.rounded_rectangle(board, radius=28, fill=(70, 50, 35, 200), outline=GOLD_SOFT, width=3)

    # Suspect cards
    suspects = [
        (220, 480, "ARJUN",   "TRUTH",  GREEN),
        (600, 480, "MEERA",   "LIAR?",  RED),
        (980, 480, "DEV",     "TRUTH?", GOLD),
        (220, 950, "PRIYA",   "LIAR",   RED),
        (600, 950, "RAVI",    "TRUTH",  GREEN),
        (980, 950, "ZOYA",    "?",      CREAM),
    ]
    centers = []
    for cx, cy, name, tag, col in suspects:
        d.rounded_rectangle((cx - 130, cy - 150, cx + 130, cy + 150), radius=20, fill=CREAM, outline=GOLD, width=3)
        # portrait silhouette
        d.ellipse((cx - 60, cy - 110, cx + 60, cy + 10), fill=INDIGO)
        d.rounded_rectangle((cx - 90, cy + 5, cx + 90, cy + 90), radius=20, fill=INDIGO)
        d.text((cx - 70, cy + 100), name, fill=INDIGO_DEEP, font=font(28, bold=True))
        d.rounded_rectangle((cx - 70, cy + 130, cx + 70, cy + 160), radius=12, fill=col)
        d.text((cx - 50 if len(tag) <= 5 else cx - 60, cy + 132), tag, fill=WHITE, font=font(22, bold=True))
        centers.append((cx, cy))

    # Red string between accusations
    string_pairs = [(0, 3), (1, 2), (2, 4), (1, 5)]
    string_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    sd = ImageDraw.Draw(string_layer)
    for a, b in string_pairs:
        sd.line([centers[a], centers[b]], fill=RED + (220,), width=4)
        for p in (centers[a], centers[b]):
            sd.ellipse((p[0] - 6, p[1] - 6, p[0] + 6, p[1] + 6), fill=RED + (255,))
    img.paste(string_layer, (0, 0), string_layer)

    # Statement strip
    strip_y = 1170
    d.text((130, strip_y - 50), "STATEMENTS", fill=GOLD, font=font(24, bold=True))
    statements = [
        "MEERA: “Arjun lies about Dev.”",
        "DEV:   “Priya tells the truth.”",
        "ZOYA:  “Exactly one of us lies.”",
    ]
    for i, s in enumerate(statements):
        d.text((130, strip_y + i * 44), s, fill=CREAM, font=font(26))

    draw_footer(d, "Mark every suspect TRUTH or LIAR; no contradictions allowed.")
    img.save(OUT / "concept_04_verdict.png")


# ---------------------------------------------------------------------------
# 5. Cascade — physics + ordering
# ---------------------------------------------------------------------------
def draw_cascade() -> None:
    img, d = base_canvas()
    draw_header(
        d,
        "05  CASCADE",
        "Reactive Dominoes",
        "One trigger, many targets, in the right order.",
    )

    # Order timeline at top
    timeline_y = 360
    targets_order = [("1", RED), ("2", GOLD), ("3", GREEN), ("4", BLUE)]
    d.text((110, timeline_y - 40), "TARGET ORDER", fill=GOLD, font=font(22, bold=True))
    for i, (label, col) in enumerate(targets_order):
        x = 110 + i * 140
        d.rounded_rectangle((x, timeline_y, x + 110, timeline_y + 60), radius=14, fill=col)
        d.text((x + 30, timeline_y + 12), label, fill=WHITE, font=font(34, bold=True))
        if i < len(targets_order) - 1:
            d.line([(x + 120, timeline_y + 30), (x + 130, timeline_y + 30)], fill=GOLD, width=3)

    # Sandbox panel
    sand = (90, 470, W - 90, 1340)
    d.rounded_rectangle(sand, radius=28, fill=(255, 255, 255, 10), outline=GOLD_SOFT, width=2)

    # Trigger ball
    d.ellipse((150, 540, 210, 600), fill=SAFFRON, outline=WHITE, width=3)
    d.text((140, 610), "TRIGGER", fill=GOLD, font=font(20, bold=True))

    # Ramp 1
    d.line([(220, 590), (520, 760)], fill=CREAM, width=10)
    # Domino chain
    for i in range(6):
        d.rectangle((540 + i * 50, 770, 560 + i * 50, 870), fill=GOLD)
    # Spring
    sx = 880
    for k in range(5):
        d.arc((sx, 760 + k * 18, sx + 80, 800 + k * 18), 180, 360, fill=CREAM, width=4)
    # Target 1 (red)
    d.ellipse((1010, 770, 1080, 840), fill=RED)
    d.text((1010, 850), "1", fill=RED, font=font(34, bold=True))

    # Ramp 2 (curve)
    pts = [(220, 880 + math.sin(i / 6) * 30) for i in range(0, 60)]
    pts = [(220 + i * 12, 940 + math.sin(i / 6) * 28) for i in range(0, 70)]
    d.line(pts, fill=CREAM, width=8)
    # Fan
    fx = 380
    fy = 1090
    d.ellipse((fx - 50, fy - 50, fx + 50, fy + 50), outline=CREAM, width=4)
    for k in range(3):
        a = math.radians(k * 120)
        d.polygon(
            [
                (fx, fy),
                (fx + math.cos(a) * 40, fy + math.sin(a) * 40),
                (fx + math.cos(a + 0.4) * 40, fy + math.sin(a + 0.4) * 40),
            ],
            fill=GOLD,
        )

    # Targets 2,3,4 spread across lower area
    targets_xy = [(620, 1100, GOLD, "2"), (820, 1180, GREEN, "3"), (1010, 1260, BLUE, "4")]
    for tx, ty, col, lbl in targets_xy:
        d.ellipse((tx - 35, ty - 35, tx + 35, ty + 35), fill=col)
        d.text((tx - 12, ty - 22), lbl, fill=WHITE, font=font(34, bold=True))

    # Dotted predicted path
    px, py = 1080, 805
    for step in range(40):
        ang = math.radians(40 + step * 4)
        nx = px + math.cos(ang) * step * 6
        ny = py + math.sin(ang) * step * 6
        d.ellipse((nx - 3, ny - 3, nx + 3, ny + 3), fill=(255, 255, 255, 120))

    draw_footer(d, "Hit 1 → 2 → 3 → 4 in sequence using kinetic energy of one trigger.")
    img.save(OUT / "concept_05_cascade.png")


# ---------------------------------------------------------------------------
# 6. Conjugate — word topology
# ---------------------------------------------------------------------------
def draw_conjugate() -> None:
    img, d = base_canvas()
    draw_header(
        d,
        "06  CONJUGATE",
        "Word Topology",
        "Transform START into END within a budget of mutations.",
    )

    ladder = ["BIND", "BAND", "BANE", "BONE", "BORE", "BORN"]
    annotations = ["I→A  swap", "D→E  swap", "A→O  swap", "N→R  swap", "E→N  swap"]
    mutation_colors = [SAFFRON, GOLD, GREEN, BLUE, RED]

    # Tile geometry: ladder fits in the left ~half so annotations get clean space on the right.
    tile_w = 105
    tile_h = 95
    tile_gap = 12
    cols = 4
    ladder_left = 220
    ladder_right = ladder_left + cols * tile_w + (cols - 1) * tile_gap  # 220 + 420 + 36 = 676

    y0 = 460
    row_h = 120
    for i, w in enumerate(ladder):
        y = y0 + i * row_h
        for j, ch in enumerate(w):
            x = ladder_left + j * (tile_w + tile_gap)
            fill = WHITE if i in (0, len(ladder) - 1) else CREAM
            d.rounded_rectangle((x, y, x + tile_w, y + tile_h), radius=16, fill=fill, outline=GOLD, width=3)
            d.text((x + 30, y + 12), ch, fill=INDIGO_DEEP, font=font(58, bold=True))

        if i == 0:
            d.text((90, y + 24), "START", fill=SAFFRON, font=font(26, bold=True))
        elif i == len(ladder) - 1:
            d.text((90, y + 24), "END", fill=GOLD, font=font(26, bold=True))

        if i < len(ladder) - 1:
            arrow_x = ladder_left + cols * tile_w / 2 + (cols / 2 - 0.5) * tile_gap
            ay = y + tile_h
            by = y + row_h
            d.line([(arrow_x, ay + 6), (arrow_x, by - 6)], fill=mutation_colors[i], width=5)
            d.polygon(
                [(arrow_x - 10, by - 8), (arrow_x + 10, by - 8), (arrow_x, by + 4)],
                fill=mutation_colors[i],
            )
            ann_x = ladder_right + 60
            ann_y = ay + (row_h - tile_h) // 2 - 22
            d.rounded_rectangle((ann_x, ann_y, ann_x + 320, ann_y + 50), radius=14,
                                fill=(255, 255, 255, 22), outline=mutation_colors[i], width=2)
            d.text((ann_x + 24, ann_y + 12), annotations[i], fill=mutation_colors[i], font=font(24, bold=True))

    # Budget pill — anchored top-right, well above the ladder.
    d.rounded_rectangle((W - 360, 360, W - 110, 440), radius=20, fill=(255, 255, 255, 22), outline=GOLD_SOFT, width=2)
    d.text((W - 340, 372), "BUDGET", fill=GOLD, font=font(22, bold=True))
    d.text((W - 340, 400), "5 / 6  used", fill=WHITE, font=font(26, bold=True))

    # Mutation legend
    legend_y = H - 240
    d.text((110, legend_y), "MUTATIONS", fill=GOLD, font=font(22, bold=True))
    moves = [("SWAP", SAFFRON), ("INSERT", GOLD), ("DELETE", GREEN), ("ROTATE", BLUE)]
    for i, (m, col) in enumerate(moves):
        x = 110 + i * 230
        d.rounded_rectangle((x, legend_y + 36, x + 200, legend_y + 88), radius=12, fill=col)
        d.text((x + 30, legend_y + 46), m, fill=WHITE, font=font(28, bold=True))

    draw_footer(d, "Every step must be a real word.  Shortest budget wins.")
    img.save(OUT / "concept_06_conjugate.png")


def main() -> None:
    random.seed(42)
    draw_resonance()
    draw_lumen()
    draw_threadwork()
    draw_verdict()
    draw_cascade()
    draw_conjugate()
    print("Wrote PNGs to", OUT)
    for p in sorted(OUT.glob("concept_*.png")):
        print(" ", p.name, p.stat().st_size, "bytes")


if __name__ == "__main__":
    main()
