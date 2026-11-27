"""Original, generated travel-poster illustrations (SVG).

Every destination gets its own illustration, generated from its id. The same
id always produces the same picture. This way the app has rich visuals
without using photos of real places that could misrepresent a fictional
destination. In the admin window a real image can be uploaded per destination;
that image then replaces the illustration.
"""

import math
import random
from functools import lru_cache

W, H = 640, 400

# Sky palettes: (top, bottom, sun colour, mood)
SKIES = {
    "dawn":   ("#FFB88A", "#FFE9D2", "#FFF4E0"),
    "day":    ("#7CB8E8", "#DCEEFB", "#FFD27A"),
    "sunset": ("#2B4A66", "#F59A4A", "#FFD08A"),
    "golden": ("#F07913", "#FFD6A0", "#FFF1D6"),
    "dusk":   ("#153147", "#5F7FA3", "#F7E7C6"),
}

NAVY = "#153147"
ORANGE = "#F07913"


def _gradient(gid: str, top: str, bottom: str, vertical: bool = True) -> str:
    x2, y2 = ("0", "1") if vertical else ("1", "0")
    return (f'<linearGradient id="{gid}" x1="0" y1="0" x2="{x2}" y2="{y2}">'
            f'<stop offset="0" stop-color="{top}"/><stop offset="1" stop-color="{bottom}"/></linearGradient>')


def _mix(c1: str, c2: str, t: float) -> str:
    a = [int(c1[i:i + 2], 16) for i in (1, 3, 5)]
    b = [int(c2[i:i + 2], 16) for i in (1, 3, 5)]
    return "#" + "".join(f"{round(x + (y - x) * t):02X}" for x, y in zip(a, b))


def _cloud(x: float, y: float, s: float, opacity: float = 0.85) -> str:
    return (f'<g fill="#FFFFFF" opacity="{opacity}"><ellipse cx="{x}" cy="{y}" rx="{34 * s}" ry="{12 * s}"/>'
            f'<circle cx="{x - 12 * s}" cy="{y - 8 * s}" r="{13 * s}"/><circle cx="{x + 8 * s}" cy="{y - 12 * s}" r="{17 * s}"/></g>')


def _birds(rng: random.Random, n: int, color: str) -> str:
    out = []
    for _ in range(n):
        x, y, s = rng.uniform(80, 560), rng.uniform(40, 140), rng.uniform(0.6, 1.2)
        out.append(f'<path d="M{x} {y} q{6 * s} {-6 * s} {12 * s} 0 q{6 * s} {-6 * s} {12 * s} 0" '
                   f'fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round"/>')
    return "".join(out)


def _sky(rng: random.Random, uid: str, sky: str) -> tuple[str, str]:
    top, bottom, sun = SKIES[sky]
    defs = _gradient(f"sky{uid}", top, bottom)
    sx, sy = rng.uniform(120, 520), rng.uniform(70, 150)
    body = (f'<rect width="{W}" height="{H}" fill="url(#sky{uid})"/>'
            f'<circle cx="{sx}" cy="{sy}" r="{rng.uniform(30, 46):.0f}" fill="{sun}" opacity=".95"/>'
            f'<circle cx="{sx}" cy="{sy}" r="70" fill="{sun}" opacity=".18"/>')
    for _ in range(rng.randint(1, 3)):
        body += _cloud(rng.uniform(60, 580), rng.uniform(50, 150), rng.uniform(0.8, 1.5), rng.uniform(.55, .9))
    return defs, body


# --------------------------------------------------------------------- beach
def _palm(x: float, base: float, h: float, lean: float, color: str) -> str:
    top_x, top_y = x + lean, base - h
    trunk = (f'<path d="M{x} {base} Q{x + lean * 0.2} {base - h * 0.6} {top_x} {top_y}" '
             f'stroke="{color}" stroke-width="{h * 0.07:.1f}" fill="none" stroke-linecap="round"/>')
    leaves = ""
    for angle in (-160, -125, -90, -55, -20, 15):
        rad = math.radians(angle)
        lx, ly = top_x + math.cos(rad) * h * 0.55, top_y + math.sin(rad) * h * 0.35 + h * 0.18
        cx, cy = top_x + math.cos(rad) * h * 0.35, top_y - h * 0.18
        leaves += (f'<path d="M{top_x} {top_y} Q{cx} {cy} {lx} {ly} Q{(cx + top_x) / 2} {(cy + top_y) / 2 + h * 0.08} {top_x} {top_y}Z" '
                   f'fill="{color}"/>')
    return trunk + leaves


def _beach(rng: random.Random, uid: str) -> str:
    sky = rng.choice(["day", "day", "golden", "sunset", "dawn"])
    defs, body = _sky(rng, uid, sky)
    horizon = rng.uniform(215, 245)
    sea_top, sea_bottom = ("#3E86C6", "#9ED3EE") if sky in ("day", "dawn") else ("#2B5C8A", "#E9A46A")
    defs += _gradient(f"sea{uid}", sea_top, sea_bottom)
    # distant island
    ix = rng.uniform(60, 420)
    body += (f'<path d="M{ix} {horizon} q60 -38 130 0Z" fill="{_mix(NAVY, sea_top, 0.55)}" opacity=".7"/>')
    body += f'<rect y="{horizon}" width="{W}" height="{H - horizon}" fill="url(#sea{uid})"/>'
    for i in range(4):
        y = horizon + 18 + i * 18
        body += (f'<path d="M0 {y} ' + " ".join(f"q20 -6 40 0 t40 0" for _ in range(1)) +
                 "".join(" t40 0" for _ in range(15)) + f'" fill="none" stroke="#FFFFFF" stroke-width="2" opacity="{.5 - i * .1:.2f}"/>')
    if rng.random() < 0.7:  # sailboat
        bx, by = rng.uniform(380, 560), horizon + rng.uniform(10, 30)
        body += (f'<path d="M{bx - 22} {by} h44 l-8 9 h-28Z" fill="{NAVY}"/>'
                 f'<path d="M{bx} {by - 2} V{by - 46} L{bx + 22} {by - 4}Z" fill="#FFFFFF"/>'
                 f'<path d="M{bx - 2} {by - 4} V{by - 38} L{bx - 20} {by - 4}Z" fill="{ORANGE}"/>')
    sand_y = rng.uniform(318, 340)
    body += (f'<path d="M0 {sand_y} Q{W * 0.35} {sand_y - 30} {W * 0.65} {sand_y - 6} T{W} {sand_y - 14} V{H} H0Z" fill="#F3D9A8"/>'
             f'<path d="M0 {sand_y + 18} Q{W * 0.4} {sand_y - 6} {W} {sand_y + 6} V{H} H0Z" fill="#E9C68A"/>')
    palm_color = _mix(NAVY, "#1E5B3A", 0.35)
    side = rng.choice([-1, 1])
    px = 80 if side < 0 else 560
    body += _palm(px, sand_y + 10, rng.uniform(150, 190), side * -30, palm_color)
    if rng.random() < 0.6:
        body += _palm(px + side * -70, sand_y + 4, rng.uniform(100, 130), side * -18, palm_color)
    if rng.random() < 0.6:  # umbrella
        ux = rng.uniform(260, 420)
        body += (f'<line x1="{ux}" y1="{sand_y + 10}" x2="{ux - 6}" y2="{sand_y - 52}" stroke="{NAVY}" stroke-width="3"/>'
                 f'<path d="M{ux - 46} {sand_y - 40} Q{ux - 6} {sand_y - 86} {ux + 34} {sand_y - 56}Z" fill="{ORANGE}"/>'
                 f'<path d="M{ux - 20} {sand_y - 48} Q{ux - 8} {sand_y - 80} {ux + 6} {sand_y - 60}" fill="#FFFFFF" opacity=".55"/>')
    body += _birds(rng, rng.randint(1, 3), NAVY)
    return defs, body


# -------------------------------------------------------------------- nature
def _ridge(rng: random.Random, base: float, amp: float, color: str, peaks: int) -> str:
    xs = [i * W / peaks for i in range(peaks + 1)]
    pts = [f"M0 {base}"]
    for i in range(peaks):
        mx = (xs[i] + xs[i + 1]) / 2 + rng.uniform(-20, 20)
        pts.append(f"L{mx:.0f} {base - amp * rng.uniform(0.5, 1.0):.0f} L{xs[i + 1]:.0f} {base - amp * rng.uniform(0, 0.3):.0f}")
    return f'<path d="{" ".join(pts)} V{H} H0Z" fill="{color}"/>'


def _pine(x: float, base: float, h: float, color: str) -> str:
    w = h * 0.42
    return (f'<path d="M{x} {base - h} L{x + w / 2} {base - h * 0.45} H{x + w * 0.3} L{x + w * 0.62} {base - h * 0.1} '
            f'H{x - w * 0.62} L{x - w * 0.3} {base - h * 0.45} H{x - w / 2}Z" fill="{color}"/>'
            f'<rect x="{x - 3}" y="{base - h * 0.1}" width="6" height="{h * 0.12}" fill="{color}"/>')


def _nature(rng: random.Random, uid: str) -> str:
    sky = rng.choice(["dawn", "day", "golden", "dusk", "day"])
    defs, body = _sky(rng, uid, sky)
    far = "#9DB8C9" if sky != "dusk" else "#4C6A8A"
    body += _ridge(rng, 250, rng.uniform(110, 150), far, rng.randint(2, 4))
    body += _ridge(rng, 290, rng.uniform(90, 120), "#6F9A86", rng.randint(3, 5))
    if rng.random() < 0.5:  # waterfall
        wx = rng.uniform(200, 440)
        body += (f'<path d="M{wx - 30} 300 L{wx - 18} 200 H{wx + 18} L{wx + 30} 300Z" fill="#4E7A63"/>'
                 f'<rect x="{wx - 10}" y="200" width="20" height="100" fill="#E8F4FA"/>'
                 f'<rect x="{wx - 4}" y="200" width="3" height="100" fill="#B9DDF0"/>'
                 f'<ellipse cx="{wx}" cy="302" rx="34" ry="8" fill="#E8F4FA"/>')
    else:  # lake / river
        defs += _gradient(f"lake{uid}", "#7DB6DA", "#CFE7F3")
        body += f'<path d="M0 312 Q{W / 2} 292 {W} 314 V340 Q{W / 2} 330 0 344Z" fill="url(#lake{uid})"/>'
    body += _ridge(rng, 345, 40, "#4F7F62", rng.randint(5, 8))
    body += f'<rect y="340" width="{W}" height="{H - 340}" fill="#3F6A51"/>'
    tree_color = _mix("#24493A", NAVY, 0.25)
    for _ in range(rng.randint(5, 9)):
        x = rng.choice([rng.uniform(10, 200), rng.uniform(440, 630)])
        body += _pine(x, rng.uniform(360, 395), rng.uniform(55, 105), tree_color)
    if rng.random() < 0.5:  # tent / lodge
        tx = rng.uniform(250, 380)
        body += (f'<path d="M{tx - 30} 372 L{tx} 336 L{tx + 30} 372Z" fill="{ORANGE}"/>'
                 f'<path d="M{tx - 6} 372 L{tx} 352 L{tx + 6} 372Z" fill="{NAVY}"/>')
    body += _birds(rng, rng.randint(2, 4), NAVY if sky != "dusk" else "#FFFFFF")
    return defs, body


# ---------------------------------------------------------------------- city
def _skyline(rng: random.Random, base: float, color: str, window: str | None, min_h: float, max_h: float) -> str:
    x, out = -10.0, []
    while x < W:
        w = rng.uniform(34, 70)
        h = rng.uniform(min_h, max_h)
        top = base - h
        shape = rng.random()
        out.append(f'<rect x="{x:.0f}" y="{top:.0f}" width="{w:.0f}" height="{h + 2:.0f}" fill="{color}"/>')
        if shape < 0.18:  # spire
            out.append(f'<path d="M{x + w / 2 - 6:.0f} {top:.0f} L{x + w / 2:.0f} {top - 34:.0f} L{x + w / 2 + 6:.0f} {top:.0f}Z" fill="{color}"/>')
        elif shape < 0.32:  # dome
            out.append(f'<path d="M{x + 4:.0f} {top:.0f} A{w / 2 - 4:.0f} {w / 2 - 4:.0f} 0 0 1 {x + w - 4:.0f} {top:.0f}Z" fill="{color}"/>')
        elif shape < 0.45:  # stepped
            out.append(f'<rect x="{x + w * 0.2:.0f}" y="{top - 18:.0f}" width="{w * 0.6:.0f}" height="20" fill="{color}"/>')
        if window:
            for wy in range(int(top) + 10, int(base) - 8, 14):
                for wx in range(int(x) + 7, int(x + w) - 8, 12):
                    if rng.random() < 0.45:
                        out.append(f'<rect x="{wx}" y="{wy}" width="5" height="7" fill="{window}"/>')
        x += w + rng.uniform(-4, 6)
    return "".join(out)


def _city(rng: random.Random, uid: str) -> str:
    sky = rng.choice(["sunset", "dusk", "golden", "day", "sunset"])
    defs, body = _sky(rng, uid, sky)
    night = sky in ("sunset", "dusk")
    body += _skyline(rng, 300, _mix("#8E9DB0", SKIES[sky][1], 0.35), None, 60, 170)
    body += _skyline(rng, 318, NAVY if night else "#2B4A66", "#FFD27A" if night else "#BFD3E6", 50, 140)
    water_top = "#2B4A66" if night else "#6F9CC4"
    defs += _gradient(f"water{uid}", water_top, _mix(water_top, "#FFFFFF", 0.35))
    body += f'<rect y="316" width="{W}" height="{H - 316}" fill="url(#water{uid})"/>'
    for i in range(6):
        y = 330 + i * 11
        x = rng.uniform(40, 520)
        body += f'<rect x="{x:.0f}" y="{y}" width="{rng.uniform(40, 110):.0f}" height="2" fill="#FFD27A" opacity="{0.55 - i * 0.07:.2f}"/>'
    if rng.random() < 0.6:  # bridge
        by = 316
        body += f'<rect x="0" y="{by - 18}" width="{W}" height="6" fill="{ORANGE}"/>'
        for bx in range(40, W, 140):
            body += (f'<rect x="{bx}" y="{by - 70}" width="8" height="80" fill="{ORANGE}"/>'
                     f'<path d="M{bx + 4} {by - 66} Q{bx + 74} {by - 20} {bx + 144} {by - 66}" stroke="{ORANGE}" stroke-width="2" fill="none"/>')
    body += _birds(rng, rng.randint(1, 3), "#FFFFFF" if night else NAVY)
    return defs, body


_BUILDERS = {"Strand": _beach, "Natuur": _nature, "Stad": _city}


@lru_cache(maxsize=256)
def destination_svg(key: str, category: str) -> str:
    """Return a complete SVG illustration for a destination (deterministic per key)."""
    seed = sum((i + 1) * ord(ch) for i, ch in enumerate(f"{key}-{category}"))
    rng = random.Random(seed)
    uid = "".join(ch for ch in key if ch.isalnum())[:12] or "x"
    defs, body = _BUILDERS.get(category, _city)(rng, uid)
    return (f'<svg viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg" preserveAspectRatio="xMidYMid slice" '
            f'role="img" aria-hidden="true"><defs>{defs}</defs>{body}</svg>')
