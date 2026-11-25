# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Naufal Habibi
"""Gambar flowchart bergaya ekspor FlowRun.io (graphviz) dari hasil/flowchart_03.flowrun -> output/flowchart_03_full.png"""
import json, sys
from PIL import Image, ImageDraw, ImageFont

S = 3                                    # supersampling
import os
_COUR = next((p for p in [r"C:\Windows\Fonts\cour.ttf",                                   # Windows
                          "/usr/share/fonts/truetype/liberation/LiberationMono-Regular.ttf",  # Linux / Docker
                          "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
                          "/System/Library/Fonts/Courier.ttc"] if os.path.exists(p)), None)
if not _COUR: sys.exit("Font Courier/monospace tidak ditemukan")
FONT = ImageFont.truetype(_COUR, 12 * S)
FSMALL = ImageFont.truetype(_COUR, 10 * S)
CW = 7.2                                 # lebar karakter Courier 12px
G = 38.7                                 # panjang panah antar node
LINE, LW = (10, 25, 49, 255), 2
C = dict(begin=("#8de4ff", "#00799e", "#982b13"), decl=("#015692", "#002a3a", "white"),
         assign=("#002a3a", "#001117", "white"), io=("#015692", "#002a3a", "white"),
         cond=("#ffd166", "#8f6400", "black"))
OPS = []                                 # daftar operasi gambar (koordinat 1x)

def tw(s): return len(s) * CW

class Node:
    def __init__(s, kind, text):
        s.kind, s.text = kind, text
        t = tw(text)
        if kind == "begin": s.w, s.h = 72, 28.8
        elif kind in ("decl", "assign"): s.w, s.h = max(t + 21, 54), 28.8
        elif kind == "in": s.w, s.h = max(t + 21, 54), 28.8
        elif kind == "out": s.w, s.h = t + 47, 28.8
        s.wl = s.wr = s.w / 2
    def draw(s, cx, y):
        OPS.append(("node", s.kind, s.text, cx, y, s.w, s.h))

class If:
    def __init__(s, cond, body, fbody=None):
        s.cond, s.body = cond, Seq(body)
        s.fbody = Seq(fbody) if fbody else None
        s.dw, s.dh = tw(cond) * 1.45 + 20, 36
        hw = s.dw / 2
        s.dxT = max(hw, s.body.wl + 25)
        s.dxF = max(hw, s.fbody.wr + 25) if s.fbody else max(hw, 60)
        s.wl = s.dxF + (s.fbody.wl if s.fbody else 2); s.wr = max(hw, s.dxT + s.body.wr)
        bh = max(s.body.h, s.fbody.h if s.fbody else 0)
        s.h = s.dh / 2 + 53 + bh + 39 + 7.2
    def draw(s, cx, y):
        yc = y + s.dh / 2; hw = s.dw / 2
        OPS.append(("node", "cond", s.cond, cx, y, s.dw, s.dh))
        bx = cx + s.dxT; by = yc + 53
        bh = max(s.body.h, s.fbody.h if s.fbody else 0)
        OPS.append(("poly", [(cx + hw, yc), (bx, yc), (bx, by)], True))
        OPS.append(("lbl", "true", cx + hw + 14, yc - 7, "forestgreen"))
        s.body.draw(bx, by)
        jy = by + bh + 39
        OPS.append(("poly", [(bx, by + s.body.h), (bx, jy), (cx + 7.2, jy)], True))
        xf = cx - s.dxF
        if s.fbody:
            OPS.append(("poly", [(cx - hw, yc), (xf, yc), (xf, by)], True))
            s.fbody.draw(xf, by)
            OPS.append(("poly", [(xf, by + s.fbody.h), (xf, jy), (cx - 7.2, jy)], True))
        else:
            OPS.append(("poly", [(cx - hw, yc), (xf, yc), (xf, jy), (cx - 7.2, jy)], True))
        OPS.append(("lbl", "false", cx - hw - 17, yc - 7, "red"))
        OPS.append(("junc", cx, jy))

class DoWhile:
    def __init__(s, cond, body):
        s.cond, s.body = cond, Seq(body)
        s.dw, s.dh = tw(cond) * 1.45 + 20, 36
        hw = s.dw / 2
        s.xl = max(hw, s.body.wl) + 25
        s.wl, s.wr = s.xl, max(hw, s.body.wr)
        s.h = 14.4 + G + s.body.h + G + s.dh
    def draw(s, cx, y):
        jy = y + 7.2; hw = s.dw / 2
        OPS.append(("junc", cx, jy))
        by = y + 14.4 + G
        OPS.append(("poly", [(cx, y + 14.4), (cx, by)], True))
        s.body.draw(cx, by)
        dy = by + s.body.h + G
        OPS.append(("poly", [(cx, by + s.body.h), (cx, dy)], True))
        OPS.append(("node", "cond", s.cond, cx, dy, s.dw, s.dh))
        yc = dy + s.dh / 2
        OPS.append(("poly", [(cx - hw, yc), (cx - s.xl, yc), (cx - s.xl, jy), (cx - 7.2, jy)], True))
        OPS.append(("lbl", "true", cx - hw - 14, yc - 7, "forestgreen"))
        OPS.append(("lbl", "false", cx + 18, dy + s.dh + 8, "red"))

class While:
    def __init__(s, cond, body):
        s.cond, s.body = cond, Seq(body)
        s.dw, s.dh = tw(cond) * 1.45 + 20, 36
        hw = s.dw / 2
        s.xl = max(hw, s.body.wl) + 25; s.xr = max(hw, s.body.wr) + 25
        s.wl, s.wr = s.xl, s.xr
        s.h = s.dh / 2 + 53 + s.body.h + 18 + 22
    def draw(s, cx, y):
        yc = y + s.dh / 2; hw = s.dw / 2
        OPS.append(("node", "cond", s.cond, cx, y, s.dw, s.dh))
        by = yc + 53
        OPS.append(("poly", [(cx, y + s.dh), (cx, by)], True))
        OPS.append(("lbl", "true", cx + 16, y + s.dh + 8, "forestgreen"))
        s.body.draw(cx, by)
        yb = by + s.body.h
        yback = yb + 18
        OPS.append(("poly", [(cx, yb), (cx, yback), (cx - s.xl, yback), (cx - s.xl, yc), (cx - hw, yc)], True))
        ye = yback + 22
        OPS.append(("poly", [(cx + hw, yc), (cx + s.xr, yc), (cx + s.xr, ye), (cx, ye)], False))
        OPS.append(("lbl", "false", cx + hw + 17, yc - 7, "red"))

class Seq:
    def __init__(s, items):
        s.items = items
        s.wl = max(i.wl for i in items); s.wr = max(i.wr for i in items)
        s.h = sum(i.h for i in items) + G * (len(items) - 1)
    def draw(s, cx, y):
        for k, it in enumerate(s.items):
            if k: OPS.append(("poly", [(cx, y - G), (cx, y)], True))
            it.draw(cx, y); y += it.h + G

def build(stmts):
    out = []
    for st in stmts:
        t = st["@type"]
        if t == "Begin": out.append(Node("begin", "Begin"))
        elif t == "Return": out.append(Node("begin", "End"))
        elif t == "Declare": out.append(Node("decl", st["name"] + (" = " + st["initValue"] if st.get("initValue") is not None else "")))
        elif t == "Assign": out.append(Node("assign", st["name"] + " = " + st["value"]))
        elif t == "Input": out.append(Node("in", st["name"]))
        elif t == "Output": out.append(Node("out", st["value"]))
        elif t == "If": out.append(If(st["condition"], build(st["trueBlock"]["statements"]), build(st["falseBlock"]["statements"])))
        elif t == "DoWhile": out.append(DoWhile(st["condition"], build(st["body"]["statements"])))
        elif t == "While": out.append(While(st["condition"], build(st["body"]["statements"])))
    return out

def render(prog, dst, pad=6):
    OPS.clear()
    root = Seq(build(prog["main"]["statements"]))
    W = root.wl + root.wr + 2 * pad; H = root.h + 2 * pad
    cx = pad + root.wl
    root.draw(cx, pad)
    im = Image.new("RGBA", (int(W * S), int(H * S)), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    P = lambda x, y: (x * S, y * S)
    def arrow(x0, y0, x1, y1):
        import math
        a = math.atan2(y1 - y0, x1 - x0); L, B = 8, 2.8
        tip = (x1, y1); bx, by = x1 - L * math.cos(a), y1 - L * math.sin(a)
        p1 = (bx + B * math.sin(a), by - B * math.cos(a)); p2 = (bx - B * math.sin(a), by + B * math.cos(a))
        d.polygon([P(*tip), P(*p1), P(*p2)], fill=LINE)
        return bx, by
    for op in [o for o in OPS if o[0] == "poly"]:          # garis dulu, node di atasnya
        pts = list(op[1])
        if op[2]: pts[-1] = arrow(*pts[-2], *pts[-1])
        d.line([P(*p) for p in pts], fill=LINE, width=LW * S, joint="curve")
    for op in OPS:
        if op[0] == "node":
            _, kind, text, cx_, y, w, h = op
            x0, x1, y1 = cx_ - w / 2, cx_ + w / 2, y + h
            if kind == "begin":
                f, s_, tc = C["begin"]; d.ellipse([P(cx_ - 36, y), P(cx_ + 36, y1)], fill=f, outline=s_, width=1)
            elif kind in ("decl", "assign"):
                f, s_, tc = C[kind]; d.rectangle([P(x0, y), P(x1, y1)], fill=f, outline=s_, width=1)
            elif kind == "in":
                f, s_, tc = C["io"]; d.polygon([P(x0, y), P(x1, y), P(x1 - 17.8, y1), P(x0 + 17.8, y1)], fill=f, outline=s_)
            elif kind == "out":
                f, s_, tc = C["io"]; sl = min(44.2, (w - 30) / 2)
                d.polygon([P(x0 + sl, y), P(x1 - sl, y), P(x1, y1), P(x0, y1)], fill=f, outline=s_)
            elif kind == "cond":
                f, s_, tc = C["cond"]; yc = y + h / 2
                d.polygon([P(cx_, y), P(x1, yc), P(cx_, y1), P(x0, yc)], fill=f, outline=s_)
            d.text(P(cx_, y + h / 2 + 0.5), text, font=FONT, fill=tc, anchor="mm")
        elif op[0] == "junc":
            _, x, y = op; d.ellipse([P(x - 7.2, y - 7.2), P(x + 7.2, y + 7.2)], fill="#ffd166", outline="#8f6400", width=1)
        elif op[0] == "lbl":
            _, t, x, y, col = op; d.text(P(x, y), t, font=FSMALL, fill=col, anchor="mm")
    im = im.resize((int(W), int(H)), Image.LANCZOS)
    im.save(dst); print(dst, im.size)

if __name__ == "__main__":
    render(json.load(open(sys.argv[1], encoding="utf8")), sys.argv[2])
