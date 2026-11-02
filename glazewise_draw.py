"""Schematic drawings of one window-and-shading option. Pure Python, returns SVG text.

Geometry sources
- Paper (Yi et al. 2024): office 6 m x 8 m x 2.7 m, two windows on one 8 m x 2.7 m facade,
  fixed window width 3 m, window height varied to set WWR.
- ED_HSD2.idf / ED_VSD4.idf: windows at 0.5 to 3.5 m and 4.5 to 7.5 m along the facade,
  window top fixed at 2.2 m, sill = WDH. Fins sit 0.05 m above and below the window.
  Tilt 90 degrees = device perpendicular to the window (EnergyPlus convention).
- Window height = 3.6 x WWR (two 3 m windows, 21.6 m2 wall). This reproduces the WDH table.

Assumptions (not stated explicitly in the source files)
- HSD: n overhangs per window, the first at the window top, the others placed below it at
  spacing (window height / n), so every overhang is attached to the window. The paper gives
  only the spacing, and the jEPlus values for the extra overhangs were not found, so the
  vertical placement of the extra overhangs is a drawing choice, not a confirmed input.
- VSD: n fins per window, evenly spaced across the 3 m window including both edges, which
  reproduces the paper's 3 m, 1 m and 0.6 m intervals.
- Tilt below 90 degrees leans toward the window (overhangs droop, fins lean toward the window
  centre line). Above 90 degrees fins lean away from it.
- Device depth is drawn along the device.
"""
import base64
import html
import math
from xml.sax.saxutils import escape

# ---- facade geometry (metres)
WALL_W, WALL_H = 8.0, 2.7
WIN_W, WIN_TOP = 3.0, 2.2
WIN_X0 = (0.5, 4.5)
FIN_OVERRUN = 0.05

# ---- colours (explicit, so the drawing looks the same in any app theme)
INK = "#1B2A33"
MUTED = "#5C6B75"
LINE = "#9AA7B1"
WALL = "#E3E8EC"
GLASS = "#CFE8F2"
GLASS_EDGE = "#1F6F8B"
DEVICE = "#D9822B"
PANEL = "#FFFFFF"
PANEL_EDGE = "#D5DCE1"

W, H = 520, 424


def window_height(wwr):
    """Height of each of the two windows in metres."""
    return wwr * WALL_W * WALL_H / (2 * WIN_W)


def _f(v):
    return f"{v:.1f}"


def _line(x1, y1, x2, y2, color=INK, width=1.0, cap="butt"):
    return (f'<line x1="{_f(x1)}" y1="{_f(y1)}" x2="{_f(x2)}" y2="{_f(y2)}" '
            f'stroke="{color}" stroke-width="{width}" stroke-linecap="{cap}"/>')


def _rect(x, y, w, h, fill, stroke="none", sw=1.0):
    return (f'<rect x="{_f(x)}" y="{_f(y)}" width="{_f(w)}" height="{_f(h)}" '
            f'fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>')


def _text(x, y, s, size=11, anchor="start", color=INK, weight="normal"):
    return (f'<text x="{_f(x)}" y="{_f(y)}" font-size="{size}" text-anchor="{anchor}" '
            f'fill="{color}" font-weight="{weight}">{escape(s)}</text>')


def _arc(cx, cy, r, a0, a1, sweep):
    """Arc of radius r around (cx, cy) from SVG angle a0 to a1 (degrees, clockwise from +x)."""
    x0, y0 = cx + r * math.cos(math.radians(a0)), cy + r * math.sin(math.radians(a0))
    x1, y1 = cx + r * math.cos(math.radians(a1)), cy + r * math.sin(math.radians(a1))
    return (f'<path d="M {_f(x0)} {_f(y0)} A {r} {r} 0 0 {sweep} {_f(x1)} {_f(y1)}" '
            f'fill="none" stroke="{MUTED}" stroke-width="1"/>')


# ------------------------------------------------------------------ front view
def _elevation(o, h):
    s = 48.0
    ex0 = (W - WALL_W * s) / 2
    ground = 34 + 3.7 * s
    X = lambda x: ex0 + x * s
    Y = lambda z: ground - z * s
    sill = WIN_TOP - h
    n = o["sdn"]

    p = [_text(14, 22, "Front view of the window wall", 12, weight="bold"),
         _line(ex0 - 20, ground, ex0 + WALL_W * s + 20, ground, LINE, 1),
         _rect(X(0), Y(WALL_H), WALL_W * s, WALL_H * s, WALL, LINE, 1)]
    for wx in WIN_X0:
        p.append(_rect(X(wx), Y(WIN_TOP), WIN_W * s, h * s, GLASS, GLASS_EDGE, 1.5))

    for wx in WIN_X0:
        if o["sdt"] == "HSD":
            for k in range(n):
                z = WIN_TOP - k * h / n
                p.append(_line(X(wx), Y(z), X(wx + WIN_W), Y(z), DEVICE, 4))
        else:
            for i in range(n):
                x = wx + i * WIN_W / (n - 1)
                p.append(_line(X(x), Y(sill - FIN_OVERRUN), X(x), Y(WIN_TOP + FIN_OVERRUN),
                               DEVICE, 4))

    p.append(_text(W / 2, ground + 18,
                   f"Two windows, each {WIN_W:.0f} m wide by {h:.2f} m high "
                   f"({round(o['wwr'] * 100)}% of the wall)", 11, "middle", MUTED))
    return p


# ------------------------------------------------------------------ side section (HSD)
def _section(o, h, theta):
    s, yg, xw = 34.0, 400.0, 70.0
    Y = lambda z: yg - z * s
    n, d = o["sdn"], o["sdd"]
    sill = WIN_TOP - h
    th = math.radians(theta)

    p = [_text(14, 262, "Side section", 12, weight="bold"),
         _line(30, yg, 150, yg, LINE, 1),
         _rect(xw - 8, Y(WALL_H), 8, WALL_H * s, WALL, LINE, 1),
         _rect(xw - 8, Y(WIN_TOP), 8, h * s, GLASS, GLASS_EDGE, 1.5)]

    for k in range(n):
        x0, y0 = xw, Y(WIN_TOP - k * h / n)
        tx, ty = x0 + d * math.sin(th) * s, y0 + d * math.cos(th) * s
        lx, ly = tx, ty
        if ly > yg:                      # do not draw a device below the ground line
            f = (yg - y0) / (ly - y0)
            lx, ly = x0 + (tx - x0) * f, yg
        p.append(_line(x0, y0, lx, ly, DEVICE, 3, "round"))
        if k == 0:
            p.append(_text(tx + 6, ty + 4, f"{d:g} m", 10, "start", MUTED))
            if n == 1:                   # with several overhangs the arc label would collide
                r = 20
                p.append(_arc(x0, y0, r, 90, 90 - theta, 0))
                p.append(_text(x0 + (r + 12) * math.sin(th / 2),
                               y0 + (r + 12) * math.cos(th / 2) + 4,
                               f"{theta}°", 10, "middle", MUTED))

    p.append(_text(xw - 12, (Y(sill) + Y(WIN_TOP)) / 2 + 4, f"{h:.2f} m", 10, "end", MUTED))
    p.append(_text(xw - 10, 416, "inside", 10, "end", MUTED))
    p.append(_text(xw + 6, 416, "outside", 10, "start", MUTED))

    lines = [f"{n} overhang{'s' if n > 1 else ''} per window",
             f"Depth {d:g} m",
             f"Tilt {theta}° from the window plane",
             f"Spacing {h / n:.2f} m" if n > 1 else "Placed at the window top"]
    for i, t in enumerate(lines):
        p.append(_text(190, 284 + 16 * i, t, 11))
    return p


# ------------------------------------------------------------------ plan view (VSD)
def _plan(o, theta):
    s, xc, yw = 45.0, 175.0, 395.0
    X = lambda x: xc + (x - WIN_W / 2) * s
    n, d = o["sdn"], o["sdd"]
    th = math.radians(theta)

    p = [_text(14, 262, "Plan view, one window (from above)", 12, weight="bold"),
         _rect(X(-1.5), yw, (WIN_W + 3.0) * s, 8, WALL, LINE, 1),
         _rect(X(0), yw, WIN_W * s, 8, GLASS, GLASS_EDGE, 1.5)]

    for i in range(n):
        x = i * WIN_W / (n - 1)
        sg = 1 if x < WIN_W / 2 else -1
        bx = X(x)
        tx, ty = bx + sg * d * math.cos(th) * s, yw - d * math.sin(th) * s
        p.append(_line(bx, yw, tx, ty, DEVICE, 3, "round"))
        if i == 0:
            p.append(_text(tx, ty - 6, f"{d:g} m", 10, "middle", MUTED))

    p.append(_text(xc, 419, "inside", 10, "middle", MUTED))
    p.append(_text(345, 276, "outside", 10, "end", MUTED))
    lines = [f"{n} fins per window",
             f"Depth {d:g} m",
             f"Tilt {theta}° from the window plane",
             f"Spacing {WIN_W / (n - 1):.1f} m"]
    for i, t in enumerate(lines):
        p.append(_text(14, 284 + 16 * i, t, 11))
    return p


# ------------------------------------------------------------------ compass
def _compass(wfo, label):
    cx, cy, r = 440.0, 335.0, 46.0
    bearing = math.radians((wfo + 90) % 360)       # file 0 = East, 90 = South (Table 3)
    dx, dy = math.sin(bearing), -math.cos(bearing)  # unit vector, north is up
    px, py = cx + 0.78 * r * dx, cy + 0.78 * r * dy
    qx, qy = -dy, dx                                # perpendicular, used for the facade bar
    ax, ay = cx + 0.78 * r * dx * 0.72, cy + 0.78 * r * dy * 0.72

    p = [_text(372, 262, "Orientation", 12, weight="bold"),
         f'<circle cx="{_f(cx)}" cy="{_f(cy)}" r="{_f(r)}" fill="none" stroke="{LINE}" stroke-width="1"/>',
         _text(cx, cy - r - 6, "N", 11, "middle", INK, "bold"),
         _text(cx + r + 9, cy + 4, "E", 10, "middle", MUTED),
         _text(cx, cy + r + 14, "S", 10, "middle", MUTED),
         _text(cx - r - 9, cy + 4, "W", 10, "middle", MUTED),
         _line(cx, cy, ax, ay, INK, 2, "round"),
         _line(px - 15 * qx, py - 15 * qy, px + 15 * qx, py + 15 * qy, GLASS_EDGE, 6, "round"),
         _text(cx, cy + r + 36, f"Faces {label}", 11, "middle")]
    return p


# ------------------------------------------------------------------ public functions
def build_svg(o, wfo_label, tilt_deg):
    """o: dict with wfo, wwr, sdt, sdn, sdd, sda. tilt_deg: tilt in real degrees from the window plane."""
    h = window_height(o["wwr"])
    alt = (f"Schematic of a window wall facing {wfo_label} with {round(o['wwr'] * 100)}% windows and "
           f"{o['sdn']} {'horizontal overhangs' if o['sdt'] == 'HSD' else 'vertical fins'} per window, "
           f"{o['sdd']:g} m deep, tilted {tilt_deg} degrees.")
    parts = _elevation(o, h)
    parts += _section(o, h, tilt_deg) if o["sdt"] == "HSD" else _plan(o, tilt_deg)
    parts += _compass(o["wfo"], wfo_label)
    parts += [_line(14, 240, W - 14, 240, PANEL_EDGE, 1),
              _line(360, 250, 360, H - 12, PANEL_EDGE, 1)]
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" role="img" '
            f'aria-label="{escape(alt, {chr(34): "&quot;"})}" font-family="Helvetica, Arial, sans-serif">'
            f'<rect x="0.5" y="0.5" width="{W - 1}" height="{H - 1}" rx="10" fill="{PANEL}" '
            f'stroke="{PANEL_EDGE}"/>' + "".join(parts) + "</svg>")


def svg_to_img_html(svg, alt):
    """Wrap the SVG in an <img> data URI. This renders reliably inside st.markdown."""
    b64 = base64.b64encode(svg.encode("utf-8")).decode("ascii")
    return (f'<img alt="{html.escape(alt, quote=True)}" '
            f'src="data:image/svg+xml;base64,{b64}" style="width:100%;height:auto;" />')