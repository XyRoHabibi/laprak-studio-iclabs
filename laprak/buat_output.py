#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Naufal Habibi
"""Buat screenshot output otomatis (gaya terminal VS Code gelap) dari kode/*.cpp.

Pakai:  python laprak/buat_output.py            -> semua kerja/kode/*.cpp, lewati kerja/output/NN.png yang sudah ada
        python laprak/buat_output.py 05 07      -> hanya kode tertentu
        python laprak/buat_output.py --force    -> timpa screenshot yang sudah ada
Tiap .cpp dikompilasi (g++) ke folder sementara, dijalankan, lalu keluarannya digambar ke output/<nama>.png
dengan tampilan sama seperti contoh output/04.png (prompt "-> ./NN.exe", font Cascadia Mono).
"""
import os, sys, shutil, subprocess, tempfile, threading, time
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "kerja")   # folder kerja
BG, FG, YEL, PINK, BLUE = (36,38,45), (204,204,204), (251,231,127), (228,99,127), (62,127,164)
FONT_PATHS = [r"C:\Windows\Fonts\CascadiaMono.ttf", r"C:\Windows\Fonts\consola.ttf",           # Windows
              "/usr/share/fonts/truetype/cascadia-code/CascadiaMono.ttf",                       # Linux / Docker
              "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
              "/System/Library/Fonts/Menlo.ttc"]                                               # macOS
SIZE, ADV, PITCH, X0, PAD_R = 31, 18.4, 41, 40, 14      # hasil pengukuran contoh 04.png

def cari_gpp():
    g = shutil.which("g++")
    for c in [g, r"C:\msys64\ucrt64\bin\g++.exe", r"C:\msys64\mingw64\bin\g++.exe"]:
        if c and os.path.exists(c): return c
    sys.exit("g++ tidak ditemukan")

def jalankan(exe, env, masukan):
    """Program ber-input: tiap baris `masukan` (kode/NN.in) diketik setelah program berhenti menunggu cin; echo-nya ikut tampil."""
    p = subprocess.Popen([exe], stdin=subprocess.PIPE, stdout=subprocess.PIPE, env=env)
    buf = bytearray()
    def baca():
        while True:
            c = os.read(p.stdout.fileno(), 4096)
            if not c: break
            buf.extend(c)
    t = threading.Thread(target=baca, daemon=True); t.start()
    tampil, pos = "", 0
    for baris in masukan:
        n = -1
        for _ in range(100):                                   # tunggu keluaran stabil
            time.sleep(0.1)
            if len(buf) == n: break
            n = len(buf)
        tampil += bytes(buf[pos:]).decode("utf-8", "replace") + baris + "\n"; pos = len(buf)
        p.stdin.write((baris + "\n").encode()); p.stdin.flush()
    p.stdin.close()
    try: p.wait(15)
    except subprocess.TimeoutExpired: p.kill()
    t.join(2)
    return tampil + bytes(buf[pos:]).decode("utf-8", "replace")

def render(nama, teks, dst):
    fp = next((p for p in FONT_PATHS if os.path.exists(p)), None)
    font = ImageFont.truetype(fp, SIZE)
    lines = teks.replace("\r", "").rstrip("\n").split("\n")
    w = int(X0 + max([len(f"-> ./{nama}.exe")] + [len(l) for l in lines]) * ADV + PAD_R)
    h = PITCH * (len(lines) + 1) - 6
    im = Image.new("RGB", (w, h), BG); d = ImageDraw.Draw(im)
    cy = 16                                                    # tengah baris prompt
    def teks_(x, y, s, col):                                   # gambar per karakter agar lebar kolom tepat
        for i, ch in enumerate(s): d.text((x + i*ADV, y), ch, font=font, fill=col, anchor="mm")
    d.ellipse((6, cy-8, 23, cy+9), fill=BLUE)
    d.line((43, cy+1, 66, cy+1), fill=PINK, width=3)           # panah
    d.line((57, cy-8, 67, cy+1), fill=PINK, width=3); d.line((57, cy+10, 67, cy+1), fill=PINK, width=3)
    teks_(76 + ADV/2, cy, f"./{nama}.exe", YEL)
    for i, l in enumerate(lines):
        teks_(X0 - 1 + ADV/2, cy + PITCH*(i+1), l, FG)
    im.save(dst)

def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]; force = "--force" in sys.argv
    gpp = cari_gpp(); tmp = tempfile.mkdtemp()
    env = dict(os.environ); env["PATH"] = os.path.dirname(gpp) + os.pathsep + env["PATH"]
    os.makedirs(os.path.join(HERE, "output"), exist_ok=True)
    for f in sorted(os.listdir(os.path.join(HERE, "kode"))):
        nama, ext = os.path.splitext(f)
        if ext != ".cpp" or (args and nama not in args): continue
        dst = os.path.join(HERE, "output", nama + ".png")
        if os.path.exists(dst) and not force: print("lewati (sudah ada):", dst); continue
        exe = os.path.join(tmp, nama + ".exe")
        r = subprocess.run([gpp, os.path.join(HERE, "kode", f), "-o", exe], capture_output=True, text=True, env=env)
        if r.returncode: print("GAGAL kompilasi", f, r.stderr); continue
        fin = os.path.join(HERE, "kode", nama + ".in")
        if os.path.exists(fin):
            out = jalankan(exe, env, open(fin, encoding="utf8").read().replace("\r", "").rstrip("\n").split("\n"))
        else:
            out = subprocess.run([exe], capture_output=True, text=True, env=env, timeout=10).stdout
        render(nama, out, dst); print("OK ->", dst)
    shutil.rmtree(tmp, ignore_errors=True)

if __name__ == "__main__": main()
