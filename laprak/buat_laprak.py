#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Naufal Habibi
"""Pembuat laprak: sampul (docx -> pdf) + isi tulisan tangan (reportlab) -> 1 PDF.

Pakai (dari folder proyek):
  python laprak/buat_laprak.py --json kerja/hasil/isi_pp_1.json --jenis pp --tanggal "01 Oktober 2026" \
      --nomor 1 --out "kerja/hasil/Laprak_PP_Evaluasi_1.pdf"
Path gambar di JSON (mis. "output/04.png") relatif terhadap folder kerja/.
Opsi: --ink 0.85 (abu tipis, default) | 0.1 (hitam)   --halo 2.4 (garis putih di sekeliling huruf, 0 = mati)   --tanpa-sampul
"""
import argparse, json, os, subprocess, shutil, sys, tempfile
from PIL import Image
from pypdf import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)                       # folder proyek
WORK = os.path.join(ROOT, "kerja")                 # soal/, kode/, output/, hasil/, archive/
FONT = os.path.join(ROOT, "aset", "fonts", "PatrickHand-Regular.ttf")
LOGO = os.path.join(ROOT, "aset", "logo_iclabs.png")

def daftar_matkul():
    """Matkul = subfolder matkul/<kode>/ yang punya sampul.docx."""
    d = os.path.join(ROOT, "matkul")
    return sorted(k for k in os.listdir(d) if os.path.isfile(os.path.join(d, k, "sampul.docx"))) if os.path.isdir(d) else []

def sampul_path(jenis): return os.path.join(ROOT, "matkul", jenis, "sampul.docx")

# ---------------- angka romawi + sampul ----------------
def roman(n):
    out = ""
    for v, s in [(1000,"M"),(900,"CM"),(500,"D"),(400,"CD"),(100,"C"),(90,"XC"),(50,"L"),(40,"XL"),(10,"X"),(9,"IX"),(5,"V"),(4,"IV"),(1,"I")]:
        while n >= v: out += s; n -= v
    return out

def muat_identitas():
    """identitas.json (dibuat pengguna dari identitas.example.json). None bila belum ada."""
    f = os.path.join(ROOT, "identitas.json")
    if not os.path.exists(f):
        print("PERINGATAN: identitas.json belum ada -> sampul memakai isian contoh. "
              "Salin identitas.example.json menjadi identitas.json lalu isi data diri.")
        return None
    return json.load(open(f, encoding="utf8"))

LABEL_IDENTITAS = {"Nama": "nama", "Stambuk": "stambuk", "Frekuensi": "frekuensi",
                   "Dosen": "dosen", "Asisten 1": "asisten1", "Asisten 2": "asisten2"}

def isi_identitas(d, jenis, tanggal):
    """Ganti nilai setelah ':' pada baris identitas sampul, dan tahun di bagian bawah sampul."""
    idt = muat_identitas()
    if idt:
        nilai = {**idt, **(idt.get(jenis) or {})}
        for p in d.paragraphs:
            runs = p.runs
            if not runs or runs[0].text.strip() not in LABEL_IDENTITAS: continue
            kunci = LABEL_IDENTITAS[runs[0].text.strip()]
            if kunci not in nilai: continue
            i = next((k for k, r in enumerate(runs) if ":" in r.text), None)
            if i is None or i + 1 >= len(runs): continue
            runs[i + 1].text = str(nilai[kunci])
            for r in runs[i + 2:]: r.text = ""
    tahun = (tanggal or "").strip()[-4:]
    if tahun.isdigit():
        for p in d.paragraphs:
            if p.text.strip().isdigit() and len(p.text.strip()) == 4 and p.runs:
                p.runs[0].text = tahun
                for r in p.runs[1:]: r.text = ""

def edit_sampul(docx_in, docx_out, nomor, tanggal, jenis=None):
    import docx
    d = docx.Document(docx_in)
    if jenis is None:                                # matkul/<jenis>/sampul.docx
        jenis = os.path.basename(os.path.dirname(os.path.abspath(docx_in)))
    isi_identitas(d, jenis.lower(), tanggal)
    target = None
    for p in d.paragraphs:
        if "Makassar," in p.text and "Praktikum" in p.text: target = p; break
    if target is None: sys.exit("Paragraf 'Tugas Evaluasi Praktikum ... Makassar,' tidak ditemukan di sampul")
    runs = target.runs
    # 1) angka romawi: run non-kosong pertama setelah run yang memuat 'Praktikum'
    ip = next(i for i, r in enumerate(runs) if "Praktikum" in r.text)
    for r in runs[ip+1:]:
        if "\t" in r.text: break
        if r.text.strip():
            r.text = roman(int(nomor)); break
    # angka romawi panjang (VII, VIII, ...) melewati satu tab stop -> buang satu tab agar tanggal tetap satu baris
    if len(roman(int(nomor))) >= 3:
        next(r for r in runs[ip+1:] if r.text == "\t").text = ""
    # 2) tanggal: semua run setelah run 'Makassar, ' diganti satu teks tanggal
    im = next(i for i, r in enumerate(runs) if "Makassar," in r.text)
    after = runs[im+1:]
    after[0].text = tanggal
    for r in after[1:]: r.text = ""
    d.save(docx_out)

def mark(s): return s.count("|") == 1   # "||" (operator logika) bukan penanda kolom

def docx_ke_pdf(docx_path, outdir):
    if not shutil.which("soffice"):      # cadangan: Microsoft Word via docx2pdf
        from docx2pdf import convert
        out = os.path.join(outdir, os.path.splitext(os.path.basename(docx_path))[0] + ".pdf")
        convert(docx_path, out); return out
    subprocess.run(["soffice","--headless","--convert-to","pdf","--outdir",outdir,docx_path],
                   check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=180)
    return os.path.join(outdir, os.path.splitext(os.path.basename(docx_path))[0] + ".pdf")

# ---------------- isi tulisan tangan ----------------
ML, MT, MR, MB = 4*cm, 4*cm, 3*cm, 3*cm            # margin 4-4-3-3
PW, PH = A4
CW = PW - ML - MR
TOP, BOT = PH - MT, MB
FS, LH = 14, 18.5            # teks
CFS, CLH = 13.5, 16.5        # kode
TFS, TLH = 12.5, 15          # tabel
TRH = 19                     # tinggi baris hierarchy chart
INDENT, NUMW = 0.85*cm, 1.0*cm
IMG_SCALE = 0.4
GAP_SOAL = 13

def flatten(src, dst):
    im = Image.open(src).convert("RGBA")
    bg = Image.new("RGBA", im.size, im.getpixel((im.width-2, im.height-2))[:3] + (255,))
    bg.alpha_composite(im); bg.convert("RGB").save(dst); return im.size

def make_wm(logo, dst, alpha=0.13):
    im = Image.open(logo).convert("RGBA")
    im.putalpha(im.getchannel("A").point(lambda v: int(v*alpha))); im.save(dst); return im.size

HALO = 2.4   # tebal garis putih di sekeliling huruf (pt); 0 = mati

class HaloCanvas(canvas.Canvas):
    """Setiap tulisan diberi garis tepi putih dulu, baru diisi warna tinta.
    Watermark di sekeliling huruf jadi 'terhapus' tipis -> tulisan tetap terbaca
    saat dicetak mode Draft (tinta abu tipis tidak lebur dengan warna toska logo)."""
    def drawString(self, x, y, text, *a, **k):
        if HALO > 0 and text.strip():
            self.saveState()
            self.setStrokeColorRGB(1, 1, 1); self.setLineWidth(HALO); self.setLineJoin(1)
            t = self.beginText(x, y); t.setTextRenderMode(1); t.textOut(text); self.drawText(t)
            self.restoreState()
        return super().drawString(x, y, text, *a, **k)
    def drawCentredString(self, x, y, text, *a, **k):    # bawaan reportlab tidak lewat drawString -> arahkan ke sini
        return self.drawString(x - pdfmetrics.stringWidth(text, self._fontname, self._fontsize)/2, y, text)

class Doc:
    def __init__(self, path, ink, wm, wmsize, tmp):
        self.c = HaloCanvas(path, pagesize=A4); self.ink = ink; self.wm = wm
        self.wmw = CW; self.wmh = CW * wmsize[1] / wmsize[0]; self.tmp = tmp
        self.c.setTitle("Laprak"); self.page()
    def page(self):   # watermark: di tengah area margin 4-4-3-3, lebar = lebar area tulis
        self.c.drawImage(self.wm, ML, BOT + ((TOP-BOT)-self.wmh)/2, self.wmw, self.wmh, mask="auto")
        self.y = TOP
    def newpage(self): self.c.showPage(); self.page()

def wrap(text, width, font=FS):
    out = []
    for raw in text.split("\n"):
        cur = ""
        for w in raw.split(" "):
            t = (cur + " " + w) if cur else w
            if pdfmetrics.stringWidth(t, "Hand", font) <= width: cur = t
            else: out.append(cur); cur = w
        out.append(cur)
    return out

def build_blocks(data, base, tmp):
    blocks = []
    for p in data.get("intro", []):                  # deskripsi/kasus di bawah judul evaluasi, rata kiri sejajar judul
        if p["t"] == "para":
            ind = 0.6*cm if p.get("bullet") else 0
            lv = p.get("lvl", 0)*0.6*cm                   # "lvl": sub-butir (a., b.) menjorok di bawah butir 1., 2.
            ls = wrap(p["text"], CW-ind-lv)
            blocks.append({**p,"lines":ls,"ind":ind,"h":len(ls)*LH+1,"keep":False,"x":ML+lv})
        elif p["t"] == "label":
            blocks.append({**p,"h":LH,"keep":True,"x":ML})
        elif p["t"] == "code":
            lines = [tuple(x) for x in p["lines"]]
            fn = "Courier" if p.get("printed") else "Hand"
            maxpre = 0
            for l, s in lines:
                if mark(s): maxpre = max(maxpre, pdfmetrics.stringWidth(s.split("|")[0],fn,CFS) + l*INDENT)
            col = maxpre + pdfmetrics.stringWidth(" ",fn,CFS)*1.2
            for l, s in lines:
                w = (col + pdfmetrics.stringWidth(s.split("|")[1],fn,CFS)) if mark(s) else l*INDENT + pdfmetrics.stringWidth(s,fn,CFS)
                assert w <= CW, f"baris kode terlalu lebar: {s}"
            blocks.append({"t":"code","lines":lines,"col":col,"h":len(lines)*CLH+4,"keep":False,"split":True,"x":ML,"printed":p.get("printed",False)})
        elif p["t"] == "img":
            if not os.path.exists(os.path.join(base, p["file"])):
                print("PERINGATAN: gambar intro tidak ada ->", p["file"]); continue
            dst = os.path.join(tmp, os.path.basename(p["file"]) + ".flat.png")
            w, h = flatten(os.path.join(base, p["file"]), dst)
            dw, dh = w * IMG_SCALE, h * IMG_SCALE
            if dw > CW: r = CW / dw; dw, dh = CW, dh * r
            blocks.append({"t":"img","path":dst,"dw":dw,"dh":dh,"h":dh+10,"keep":False,"x":ML})
    for q in data["questions"]:
        ls = wrap(q["text"], CW-NUMW)
        blocks.append({"t":"q","num":q["num"],"lines":ls,"h":len(ls)*LH+2,"keep":True})
        for p in q["parts"]:
            t = p["t"]
            if t == "para":
                ind = 0.6*cm if p.get("bullet") else 0
                lv = p.get("lvl", 0)*0.6*cm
                ls = wrap(p["text"], CW-NUMW-ind-lv)
                blocks.append({**p,"lines":ls,"ind":ind,"h":len(ls)*LH+1,"keep":False,"x":ML+NUMW+lv})
            elif t == "label":
                blocks.append({**p,"h":LH,"keep":True})
            elif t == "code":
                lines = [tuple(x) for x in p["lines"]]
                fn = "Courier" if p.get("printed") else "Hand"
                maxpre = 0
                for l, s in lines:
                    if mark(s): maxpre = max(maxpre, pdfmetrics.stringWidth(s.split("|")[0],fn,CFS) + l*INDENT)
                col = maxpre + pdfmetrics.stringWidth(" ",fn,CFS)*1.2
                for l, s in lines:
                    w = (col + pdfmetrics.stringWidth(s.split("|")[1],fn,CFS)) if mark(s) else l*INDENT + pdfmetrics.stringWidth(s,fn,CFS)
                    assert w + NUMW <= CW, f"baris kode terlalu lebar: {s}"
                blocks.append({"t":"code","lines":lines,"col":col,"h":len(lines)*CLH+4,"keep":False,"split":True,"printed":p.get("printed",False)})
            elif t == "table":                       # tabel bergaris tipis; baris tidak dipotong antar halaman
                ws = [f*CW for f in p["widths"]]
                def cell_rows(r):
                    cl = [wrap(str(x), w-8, TFS) for x, w in zip(r, ws)]
                    return {"cells": cl, "h": max(len(x) for x in cl)*TLH + 6}
                rows = [cell_rows(p["header"])] + [cell_rows(r) for r in p["rows"]]
                blocks.append({"t":"table","ws":ws,"rows":rows,"h":sum(r["h"] for r in rows)+6,"keep":False,"tbl":True})
            elif t == "imgtable":                    # tabel kolom berjudul berisi gambar/teks (contoh output di soal); satu baris, tidak dipotong
                ws = [f*(CW-NUMW) for f in p["widths"]]
                cols = []
                for cell, w in zip(p["cells"], ws):
                    items = []
                    for it in cell:
                        if "img" in it:
                            if not os.path.exists(os.path.join(base, it["img"])):
                                print("PERINGATAN: gambar tabel tidak ada ->", it["img"]); continue
                            dst = os.path.join(tmp, os.path.basename(it["img"]) + ".flat.png")
                            iw, ih = flatten(os.path.join(base, it["img"]), dst)
                            dw, dh = iw * IMG_SCALE, ih * IMG_SCALE
                            if dw > w - 8: r = (w - 8) / dw; dw, dh = w - 8, dh * r
                            items.append({"img":dst,"dw":dw,"dh":dh})
                        else:
                            ls = wrap(it["text"], w-8, TFS)
                            items.append({"lines":ls,"dh":len(ls)*TLH})
                    cols.append(items)
                rh = max(sum(i["dh"] for i in col) + (len(col)+1)*4 for col in cols)
                hh = TLH + 6
                blocks.append({"t":"imgtable","ws":ws,"header":p["header"],"cols":cols,"rh":rh,"hh":hh,"h":rh+hh+6,"keep":False})
            elif t == "tree":                        # hierarchy chart: [[kedalaman, teks], ...] urut DFS, kedalaman 0 = akar
                nodes = [tuple(x) for x in p["nodes"]]
                blocks.append({"t":"tree","nodes":nodes,"h":len(nodes)*TRH+6,"keep":False})
            elif t == "img":
                if not os.path.exists(os.path.join(base, p["file"])):
                    print("PERINGATAN: screenshot tidak ada ->", p["file"]); continue
                if p.get("transparent"):                 # "transparent": true -> latar transparan dipertahankan, tanpa bingkai (flowchart)
                    dst = os.path.join(base, p["file"]); w, h = Image.open(dst).size
                else:
                    dst = os.path.join(tmp, os.path.basename(p["file"]) + ".flat.png")
                    w, h = flatten(os.path.join(base, p["file"]), dst)      # opak, tanpa transparan
                dw, dh = w * IMG_SCALE, h * IMG_SCALE
                mw = CW - NUMW
                if dw > mw: r = mw / dw; dw, dh = mw, dh * r
                blocks.append({"t":"img","path":dst,"dw":dw,"dh":dh,"h":dh+10,"keep":False,
                               "noframe":p.get("noframe",False) or p.get("transparent",False),"transparent":p.get("transparent",False)})
    return blocks

def render_isi(data, base, out, ink, logo, tmp):
    pdfmetrics.registerFont(TTFont("Hand", FONT))
    # peringatan jika ada karakter yang tidak ada di font tulisan tangan
    teks = data["title"] + "".join(p.get("text","") for p in data.get("intro",[])) + "".join(q["text"] + "".join(p.get("text","") + "".join(x[1] for x in p.get("lines",[]) if p["t"]=="code" and not p.get("printed")) + "".join(str(x) for r in [p.get("header",[])] + p.get("rows",[]) for x in r) for p in q["parts"]) for q in data["questions"])
    face = pdfmetrics.getFont("Hand").face
    hilang = sorted({ch for ch in teks if ord(ch) > 32 and ch != "|" and ord(ch) not in face.charToGlyph})
    if hilang: print("PERINGATAN: karakter tidak ada di font ->", hilang, "(ganti dengan karakter ASCII biasa)")
    wmp = os.path.join(tmp, "wm.png"); wms = make_wm(logo, wmp)
    D = Doc(out, (ink,ink,ink), wmp, wms, tmp); c = D.c
    X0 = ML + NUMW
    c.setFont("Hand", 22); c.setFillColorRGB(*D.ink)
    if data["title"]: c.drawString(ML, D.y-20, data["title"]); D.y -= 42   # judul kosong -> tidak digambar
    blocks = build_blocks(data, base, tmp)
    def need(h):                                         # tidak ada ruang kosong: pindah halaman HANYA bila baris berikutnya tidak muat
        if D.y - h < BOT: D.newpage()
    def table(b):
        rows = b["rows"]
        def setup(): c.setStrokeColorRGB(*D.ink); c.setLineWidth(.6); c.setFont("Hand", TFS); c.setFillColorRGB(*D.ink)
        def draw_row(r):
            x = ML; top = D.y
            for cl, w in zip(r["cells"], b["ws"]):
                c.rect(x, top - r["h"], w, r["h"])
                for k, ln in enumerate(cl): c.drawString(x + 4, top - 3 - (k+1)*TLH + 4, ln)
                x += w
            D.y -= r["h"]
        need(rows[0]["h"] + rows[1]["h"] + 3); D.y -= 3; setup(); draw_row(rows[0])
        for r in rows[1:]:
            if D.y - r["h"] < BOT:
                D.newpage(); D.y -= 3; setup(); draw_row(rows[0])
            draw_row(r)
        D.y -= 3
    def imgtable(b):
        need(b["h"]); D.y -= 3
        c.setStrokeColorRGB(*D.ink); c.setLineWidth(.6); c.setFont("Hand", TFS); c.setFillColorRGB(*D.ink)
        x = X0; top = D.y; hh = b["hh"]; rh = b["rh"]
        for w, hd, col in zip(b["ws"], b["header"], b["cols"]):
            c.rect(x, top-hh, w, hh); c.drawCentredString(x+w/2, top-hh+6, hd)
            c.rect(x, top-hh-rh, w, rh)
            y = top - hh - 4
            for it in col:
                if "img" in it: c.drawImage(it["img"], x+(w-it["dw"])/2, y-it["dh"], it["dw"], it["dh"])
                else:
                    for k, ln in enumerate(it["lines"]): c.drawString(x+4, y-(k+1)*TLH+4, ln)
                y -= it["dh"] + 4
            x += w
        D.y = top - hh - rh - 3
    def code(lines, col, base_x=None, printed=False):
        if base_x is None: base_x = X0
        D.y -= 2
        for l, s in lines:
            need(CLH)
            if printed:
                c.setFont("Courier", CFS); c.setFillColorRGB(0.1, 0.1, 0.1)
            else:
                c.setFont("Hand", CFS); c.setFillColorRGB(*D.ink)
            D.y -= CLH; x = base_x + l*INDENT
            if mark(s):
                a, r = s.split("|"); c.drawString(x, D.y+5, a); c.drawString(base_x+col, D.y+5, r)
            else: c.drawString(x, D.y+5, s)
        D.y -= 2
    def tree(b):                                         # garis cabang digambar vektor (font tidak punya karakter kotak)
        nodes = b["nodes"]; S = 26
        vx = lambda d: X0 + 6 + (d-1)*S
        def has_next(i, a):
            for dj, _ in nodes[i+1:]:
                if dj < a: return False
                if dj == a: return True
            return False
        D.y -= 3
        for i, (d, s) in enumerate(nodes):
            need(TRH)
            c.setFont("Hand", FS); c.setFillColorRGB(*D.ink); c.setStrokeColorRGB(*D.ink); c.setLineWidth(.7)
            top = D.y; mid = top - TRH/2; bot = top - TRH
            if d == 0: c.drawString(X0, mid-4, s)
            else:
                for a in range(1, d):
                    if has_next(i, a): c.line(vx(a), top, vx(a), bot)
                c.line(vx(d), top, vx(d), bot if has_next(i, d) else mid)
                c.line(vx(d), mid, vx(d)+S-4, mid)
                c.drawString(vx(d)+S, mid-4, s)
            D.y -= TRH
        D.y -= 3
    def textline(x, s, dy=6):
        need(LH); c.setFont("Hand", FS); c.setFillColorRGB(*D.ink)
        D.y -= LH; c.drawString(x, D.y+dy, s)
    for i, b in enumerate(blocks):
        t = b["t"]
        if t == "q":
            if D.y != TOP: D.y -= GAP_SOAL
            need(LH)
            c.setFont("Hand", FS); c.setFillColorRGB(*D.ink); c.drawString(ML, D.y-LH+6, b["num"])
            for ln in b["lines"]: textline(X0, ln)
            D.y -= 2
        elif t == "label":                               # TANPA garis bawah
            if b.get("gap") and D.y != TOP: D.y -= GAP_SOAL
            textline(b.get("x", X0), b["text"], 5)
        elif t == "para":
            xx = b.get("x", X0)
            nx = blocks[i+1] if i+1 < len(blocks) else None
            if nx and nx["t"] == "img" and len(b["lines"]) == 1: need(LH + nx["dh"] + 9)   # judul gambar ikut pindah bersama gambarnya
            elif nx and nx["t"] == "imgtable" and len(b["lines"]) == 1: need(LH + nx["h"] + 1)   # judul tabel ikut pindah bersama tabelnya
            else: need(LH)
            if b.get("bullet"): c.setFont("Hand", FS); c.setFillColorRGB(*D.ink); c.drawString(xx, D.y-LH+6, b["bullet"])
            for ln in b["lines"]: textline(xx+b["ind"], ln)
            D.y -= 1
        elif t == "code":
            code(b["lines"], b["col"], b.get("x"), b.get("printed", False))
        elif t == "table":
            table(b)
        elif t == "imgtable":
            imgtable(b)
        elif t == "tree":
            tree(b)
        elif t == "img":                                 # gambar tidak bisa dipotong; digambar SETELAH watermark -> opak
            bx = b.get("x", X0)
            need(b["dh"] + 8); D.y -= 3
            c.drawImage(b["path"], bx, D.y-b["dh"], b["dw"], b["dh"], mask="auto" if b.get("transparent") else None)
            if not b.get("noframe"):                     # "noframe": true -> tanpa bingkai (mis. potongan flowchart)
                c.setStrokeColorRGB(.35,.35,.35); c.setLineWidth(.6); c.rect(bx, D.y-b["dh"], b["dw"], b["dh"])
            D.y -= b["dh"] + 5
    c.save()

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", required=True); ap.add_argument("--out", required=True)
    ap.add_argument("--jenis", choices=daftar_matkul(), default="pp")
    ap.add_argument("--tanggal"); ap.add_argument("--nomor", type=int, default=1)
    ap.add_argument("--ink", type=float, default=0.85)
    ap.add_argument("--halo", type=float, default=2.4)
    ap.add_argument("--logo", default=LOGO)
    ap.add_argument("--tanpa-sampul", action="store_true")
    a = ap.parse_args()
    globals()["HALO"] = a.halo
    data = json.load(open(a.json, encoding="utf8")); base = WORK   # path gambar di JSON relatif terhadap kerja/
    tmp = tempfile.mkdtemp()
    isi = os.path.join(tmp, "isi.pdf"); render_isi(data, base, isi, a.ink, a.logo, tmp)
    w = PdfWriter()
    if not a.tanpa_sampul:
        src = sampul_path(a.jenis); ed = os.path.join(tmp, f"{a.jenis}-sampul.docx")
        edit_sampul(src, ed, a.nomor, a.tanggal, a.jenis); cov = docx_ke_pdf(ed, tmp)
        for p in PdfReader(cov).pages: w.add_page(p)
    for p in PdfReader(isi).pages: w.add_page(p)
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    w.write(a.out); shutil.rmtree(tmp, ignore_errors=True); print("OK ->", a.out, "| halaman:", len(w.pages))

if __name__ == "__main__": main()
