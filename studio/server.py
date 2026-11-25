#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Naufal Habibi
"""Laprak Studio — tampilan web lokal untuk agent pembuat laprak.

Jalankan:   python studio/server.py --buka     (dari folder proyek; atau klik dua kali studio.bat)
            (butuh paket di requirements.txt: reportlab, pypdf, pillow, python-docx, PyMuPDF, docx2pdf)

Cara kerja:
- Form (jenis, tanggal, catatan, PDF soal) -> studio membuka JENDELA agent (default Claude Code, bisa diganti di
  config.json) di folder ini dengan perintah laprak sudah terisi. Izin, pertanyaan, dan revisi dilakukan di jendela itu.
- Agent mengirim log tiap langkah (python studio.py log "...") -> tampil live di browser lewat SSE.
- Saat agent menulis/ubah hasil/isi_*.json, server merekam tata letak halaman
  (memakai buat_laprak.py yang sama) lalu browser "membangun" halamannya dengan kawanan kursor.
- Saat PDF di hasil/ jadi, halaman asli dirender ke PNG -> tombol "Lihat asli".
"""
import glob, json, os, queue, shutil, subprocess, sys, tempfile, threading, time, traceback
from datetime import date
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs, unquote

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # folder proyek
WORK = os.path.join(HERE, "kerja")
PORT = int(os.environ.get("LAPRAK_PORT", "8000"))
HOST = os.environ.get("LAPRAK_HOST", "127.0.0.1")       # Docker: 0.0.0.0

def kirim(path, data):
    import urllib.request
    req = urllib.request.Request(f"http://127.0.0.1:{PORT}{path}", data=json.dumps(data).encode("utf8"),
                                 headers={"Content-Type": "application/json"})
    try: urllib.request.urlopen(req, timeout=5).read(); return True
    except OSError: return False

# `log` dan `stop` ditangani sebelum impor berat -> bisa dipanggil dengan python mana pun
if __name__ == "__main__" and sys.argv[1:2] == ["log"]:
    a = sys.argv[2:]
    if not kirim("/api/log", {"text": " ".join(a[:1]), "kind": a[1] if len(a) > 1 else "tool"}): print("studio tidak jalan (log diabaikan)")
    sys.exit(0)
if __name__ == "__main__" and sys.argv[1:2] == ["stop"]:
    print("studio ditutup" if kirim("/api/shutdown", {}) else "studio memang tidak jalan"); sys.exit(0)

sys.path.insert(0, os.path.join(HERE, "laprak"))
import buat_laprak as BL  # noqa: E402
UI = os.path.join(HERE, "studio", "web", "index.html")
CACHE = os.path.join(tempfile.gettempdir(), "laprak_studio")
os.makedirs(CACHE, exist_ok=True)
BULAN = ["Januari","Februari","Maret","April","Mei","Juni","Juli","Agustus","September","Oktober","November","Desember"]

# ---------------- siaran SSE ----------------
class Hub:
    def __init__(self):
        self.clients = []; self.lock = threading.Lock()
        self.state = {"logs": [], "layout": None, "final": None, "status": "siap", "job": None}
    def send(self, kind, data):
        if kind == "log":
            self.state["logs"] = (self.state["logs"] + [data])[-400:]
        elif kind in ("layout", "final", "status", "job"):
            self.state[kind] = data
        msg = f"event: {kind}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n".encode("utf8")
        with self.lock:
            for q in list(self.clients): q.put(msg)
    def log(self, who, text, kind="info"):
        self.send("log", {"t": time.strftime("%H:%M:%S"), "who": who, "text": text, "kind": kind})
HUB = Hub()

# ---------------- rekam tata letak (meniru buat_laprak.py persis) ----------------
IMAGES = {}   # id -> path file gambar
def _img_id(path):
    i = str(abs(hash((path, os.path.getmtime(path)))))
    IMAGES[i] = path; return i

class RecCanvas(BL.HaloCanvas):
    def __init__(self, *a, **k):
        super().__init__(*a, **k); self.pages = [[]]
    def _rgb(self, c):
        v = (c.red, c.green, c.blue) if hasattr(c, "red") else tuple(c)[:3]
        return [round(float(x), 3) for x in v]
    def drawString(self, x, y, text, *a, **k):
        if text.strip():
            self.pages[-1].append({"op": "text", "x": x, "y": y, "s": text, "font": self._fontname,
                                   "size": self._fontsize, "color": self._rgb(self._fillColorObj)})
        return BL.canvas.Canvas.drawString(self, x, y, text, *a, **k)
    def rect(self, x, y, w, h, *a, **k):
        self.pages[-1].append({"op": "rect", "x": x, "y": y, "w": w, "h": h,
                               "color": self._rgb(self._strokeColorObj), "lw": self._lineWidth})
        return super().rect(x, y, w, h, *a, **k)
    def line(self, x1, y1, x2, y2):
        self.pages[-1].append({"op": "line", "x1": x1, "y1": y1, "x2": x2, "y2": y2,
                               "color": self._rgb(self._strokeColorObj), "lw": self._lineWidth})
        return super().line(x1, y1, x2, y2)
    def drawImage(self, image, x, y, width=None, height=None, *a, **k):
        wm = os.path.basename(str(image)) == "wm.png"
        self.pages[-1].append({"op": "wm" if wm else "img", "x": x, "y": y, "w": width, "h": height,
                               "src": "/img/" + _img_id(str(image))})
        return super().drawImage(image, x, y, width, height, *a, **k)
    def showPage(self):
        self.pages.append([]); return super().showPage()

# ---------------- sampul ----------------
import re
COVER = {}            # kunci (jenis, nomor, tanggal) / path pdf -> daftar op
COVER_BUSY = set()

def cover_dari_pdf(pdf_path):
    """Ubah halaman 1 PDF (sampul) jadi op: teks per span, gambar (logo) per kotak."""
    import fitz
    doc = fitz.open(pdf_path); pg = doc[0]; H = pg.rect.height; ops = []
    for b in pg.get_text("dict")["blocks"]:
        if b["type"] != 0: continue
        for ln in b["lines"]:
            for sp in ln["spans"]:
                if not sp["text"].strip(): continue
                c = sp["color"]; f = sp["font"]
                fam = "Times New Roman" if "Times" in f else "Calibri" if "Calibri" in f else "Arial" if "Arial" in f else f.split("-")[0].split(",")[0]
                lead = len(sp["text"]) - len(sp["text"].lstrip())          # spasi depan dibuang, posisinya digeser
                x = sp["origin"][0]
                if lead:
                    try: x = fitz.Font("tiro").text_length(" " * lead, sp["size"]) + x
                    except Exception: pass
                ops.append({"op": "text", "x": x, "y": H - sp["origin"][1], "s": sp["text"].strip(), "font": "Cover",
                            "family": fam, "bold": bool(sp["flags"] & 16), "italic": bool(sp["flags"] & 2),
                            "size": sp["size"], "color": [((c >> 16) & 255) / 255, ((c >> 8) & 255) / 255, (c & 255) / 255]})
    key = str(abs(hash((pdf_path, os.path.getmtime(pdf_path)))))
    for i, im in enumerate(pg.get_image_info()):
        r = fitz.Rect(im["bbox"])
        if r.width < 4 or r.height < 4: continue
        dst = os.path.join(CACHE, f"cover_{key}_{i}.png")
        if not os.path.exists(dst): pg.get_pixmap(clip=r, dpi=200).save(dst)
        ops.append({"op": "img", "x": r.x0, "y": H - r.y1, "w": r.width, "h": r.height, "src": "/img/" + _img_id(dst)})
    for d in pg.get_drawings():                                    # garis / kotak bila sampul punya
        for it in d["items"]:
            if it[0] == "l":
                a, b2 = it[1], it[2]
                ops.append({"op": "line", "x1": a.x, "y1": H - a.y, "x2": b2.x, "y2": H - b2.y, "color": list(d.get("color") or (0, 0, 0)), "lw": d.get("width") or 1})
            elif it[0] == "re" and d.get("color"):
                r = it[1]; ops.append({"op": "rect", "x": r.x0, "y": H - r.y1, "w": r.width, "h": r.height, "color": list(d["color"]), "lw": d.get("width") or 1})
    return ops

def info_sampul(data, json_path):
    """(jenis, nomor, tanggal) dari JSON / nama file / form studio. tanggal bisa None."""
    sm = data.get("sampul") or {}
    m = re.match(r"isi_([a-z]+)_(\d+)", os.path.basename(json_path), re.I)
    jenis = (sm.get("jenis") or (m.group(1) if m else "")).lower()
    nomor = sm.get("nomor") or (int(m.group(2)) if m else None)
    if not nomor:
        t = re.search(r"(\d+)", data.get("title", "")); nomor = int(t.group(1)) if t else None
    job = HUB.state.get("job") or {}
    tanggal = sm.get("tanggal") or (job.get("tanggal") if (job.get("jenis") or "").lower() == jenis else None)
    return jenis, nomor, tanggal

def pdf_laprak(json_path, jenis, nomor):
    d = os.path.dirname(json_path)
    for folder in (d, os.path.dirname(d)):
        f = os.path.join(folder, f"Laprak_{jenis.upper()}_Evaluasi_{nomor}.pdf")
        if os.path.isfile(f): return f
    return None

def buat_cover_docx(key, json_path):
    """Sampul belum ada di PDF -> buat dari docx (lewat Word), lalu kirim ulang tata letak."""
    jenis, nomor, tanggal = key
    try:
        tmp = tempfile.mkdtemp(dir=CACHE)
        src = BL.sampul_path(jenis); ed = os.path.join(tmp, f"{jenis}-sampul.docx")
        BL.edit_sampul(src, ed, nomor, tanggal, jenis)
        COVER[key] = cover_dari_pdf(BL.docx_ke_pdf(ed, tmp))
        HUB.send("layout", rekam_layout(json_path))
    except Exception as e:
        HUB.log("Studio", f"Sampul belum bisa ditampilkan ({type(e).__name__}: {e})", "warn")
    finally:
        COVER_BUSY.discard(key)

def ops_sampul(data, json_path):
    jenis, nomor, tanggal = info_sampul(data, json_path)
    if not jenis or not nomor: return []
    pdf = pdf_laprak(json_path, jenis, nomor)
    if pdf:                                                       # sampul asli dari PDF yang sudah jadi
        k = (pdf, os.path.getmtime(pdf))
        if k not in COVER: COVER[k] = cover_dari_pdf(pdf)
        return COVER[k]
    if not tanggal or not os.path.isfile(BL.sampul_path(jenis)): return []
    key = (jenis, int(nomor), tanggal)
    if key in COVER: return COVER[key]
    if key not in COVER_BUSY:
        COVER_BUSY.add(key); threading.Thread(target=buat_cover_docx, args=(key, json_path), daemon=True).start()
    return []

def rekam_layout(json_path):
    data = json.load(open(json_path, encoding="utf8"))
    tmp = tempfile.mkdtemp(dir=CACHE)
    asli = BL.HaloCanvas; holder = {}
    class R(RecCanvas):
        def __init__(s, *a, **k): super().__init__(*a, **k); holder["c"] = s
    BL.HaloCanvas = R
    try:
        base = WORK                                   # path gambar di JSON relatif terhadap kerja/
        rel = os.path.relpath(json_path, HERE).replace("\\", "/").split("/")
        if rel[:2] == ["kerja", "archive"] and len(rel) > 3: base = os.path.join(WORK, "archive", rel[2])   # arsip punya output/ sendiri
        elif rel[0] == "contoh": base = os.path.join(HERE, "contoh")
        BL.render_isi(data, base, os.path.join(tmp, "isi.pdf"), 0.85, BL.LOGO, tmp)
    finally:
        BL.HaloCanvas = asli
    pages = [p for p in holder["c"].pages if p]
    try: sampul = ops_sampul(data, json_path)
    except Exception as e: sampul = []; HUB.log("Studio", f"Sampul dilewati ({type(e).__name__}: {e})", "warn")
    return {"file": os.path.relpath(json_path, HERE).replace("\\", "/"), "w": BL.PW, "h": BL.PH, "cover": True,
            "margin": {"l": BL.ML, "t": BL.MT, "r": BL.MR, "b": BL.MB}, "pages": [sampul] + pages, "stamp": time.time()}

def render_final(pdf_path):
    import fitz
    doc = fitz.open(pdf_path); out = []
    key = str(abs(hash((pdf_path, os.path.getmtime(pdf_path)))))
    for i, pg in enumerate(doc):
        dst = os.path.join(CACHE, f"final_{key}_{i}.png")
        if not os.path.exists(dst): pg.get_pixmap(dpi=110).save(dst)
        out.append("/img/" + _img_id(dst))
    return {"file": os.path.relpath(pdf_path, HERE).replace("\\", "/"), "pages": out, "stamp": time.time()}

# ---------------- pengawas folder hasil/ ----------------
def watcher():
    daftar = lambda: glob.glob(os.path.join(WORK, "hasil", "*.json")) + glob.glob(os.path.join(WORK, "hasil", "*.pdf"))
    seen = {} if WATCH_EXISTING else {p: os.path.getmtime(p) for p in daftar()}   # file lama baru diproses bila diubah
    while True:
        try:
            for path in daftar():
                m = os.path.getmtime(path)
                if seen.get(path) == m: continue
                if time.time() - m < 0.8: continue                     # tunggu file selesai ditulis
                seen[path] = m
                if path.endswith(".json"):
                    try:
                        lay = rekam_layout(path)
                        HUB.log("Studio", f"{os.path.basename(lay['file'])} ditulis, sampul + {len(lay['pages']) - 1} halaman dibangun", "build")
                        HUB.send("layout", lay)
                    except Exception as e:
                        HUB.log("Studio", f"JSON belum bisa dirender ({type(e).__name__}: {e})", "warn")
                else:
                    try:
                        fin = render_final(path)
                        HUB.log("Studio", f"PDF jadi: {fin['file']} ({len(fin['pages'])} halaman)", "done")
                        HUB.send("final", fin); HUB.send("status", "siap")
                        lay = HUB.state.get("layout")
                        if lay and lay.get("file", "").startswith("kerja/hasil/"):
                            jp = os.path.join(HERE, lay["file"])
                            if os.path.isfile(jp): HUB.send("layout", rekam_layout(jp))
                    except Exception as e:
                        HUB.log("Studio", f"PDF gagal dirender: {e}", "warn")
            if POLL["menunggu"] and time.time() - POLL["t"] > 3:
                POLL["menunggu"] = False; HUB.send("menunggu", False)
        except Exception:
            traceback.print_exc()
        time.sleep(1)
WATCH_EXISTING = False   # file yang sudah ada saat studio dibuka tidak dianggap baru

# ---------------- membuka jendela agent ----------------
def muat_config():
    """config.json -> {"agent": {"nama": ..., "perintah": [..., "{prompt}"]}}. Default: Claude Code."""
    cfg = {"agent": {"nama": "Claude Code", "perintah": ["claude", "{prompt}"]}}
    f = os.path.join(HERE, "config.json")
    if os.path.exists(f):
        try: cfg.update(json.load(open(f, encoding="utf8")))
        except ValueError as e: print("PERINGATAN: config.json tidak valid:", e)
    return cfg
CONFIG = muat_config()
AGENT_NAMA = CONFIG["agent"].get("nama") or "Agent"
AGENT_CMD = CONFIG["agent"].get("perintah") or ["claude", "{prompt}"]
CHAT = "claude" in os.path.basename(AGENT_CMD[0]).lower()     # chat studio memakai Stop hook milik Claude Code

def cari_claude():
    """claude.exe asli (dipanggil langsung, tanpa claude.cmd, agar argumen tidak dirusak cmd.exe)."""
    cmd = shutil.which("claude.cmd") or shutil.which("claude")
    if cmd:
        exe = os.path.join(os.path.dirname(cmd), "node_modules", "@anthropic-ai", "claude-code", "bin", "claude.exe")
        if os.path.isfile(exe): return exe
    return shutil.which("claude.exe") or cmd

def bersih(t):   # buang karakter yang bisa merusak baris perintah Windows
    return " ".join(t.translate({ord(c): " " for c in '"&|<>^%`\r\n'}).split())

def daftar_matkul_info():
    out = []
    for k in BL.daftar_matkul():
        try: m = json.load(open(os.path.join(HERE, "matkul", k, "matkul.json"), encoding="utf8"))
        except (OSError, ValueError): m = {}
        out.append({"kode": k, "nama": m.get("nama", k.upper()), "singkat": m.get("singkat", k.upper()), "urutan": m.get("urutan", 99)})
    return sorted(out, key=lambda m: (m["urutan"], m["kode"]))

def buka_agent(prompt):
    if os.name != "nt":
        raise RuntimeError("Tombol Buat laprak baru didukung di Windows. Di Docker/Linux/macOS, jalankan agent sendiri "
                           "di folder proyek (Docker: docker compose exec studio bash) lalu ketik perintah laprak.")
    args = [a.replace("{prompt}", prompt) for a in AGENT_CMD]
    exe = cari_claude() if args[0] == "claude" else (shutil.which(args[0]) or args[0])
    if not exe or not (os.path.isfile(exe) or shutil.which(exe)):
        raise RuntimeError(f"Perintah agent `{args[0]}` tidak ditemukan. Periksa config.json.")
    flags = getattr(subprocess, "CREATE_NEW_CONSOLE", 0)
    env = {**os.environ, "LAPRAK_STUDIO": "1", "LAPRAK_PORT": str(PORT)}   # mengaktifkan studio_hook.py di sesi ini saja
    if exe.lower().endswith(".exe"):
        subprocess.Popen([exe, *args[1:]], cwd=HERE, creationflags=flags, env=env)
    else:
        subprocess.Popen(["cmd", "/k", exe, *args[1:]], cwd=HERE, creationflags=flags, env=env)

def buat_prompt(jenis, tanggal, catatan, soal):
    perintah = f"{jenis} {bersih(tanggal)}" + (f"  catatan: {bersih(catatan)}" if catatan.strip() else "")
    return (f"Baca dan ikuti AGENTS.md di folder ini sepenuhnya. Perintah pengguna: {perintah}. PDF soal: kerja/soal/{bersih(soal)}. "
            "Kamu dibuka dari Laprak Studio (AGENTS.md bagian 12B): studio SUDAH menyala di http://localhost:8000, "
            "jadi JANGAN jalankan studio/server.py --viewer dan JANGAN jalankan studio/server.py stop. "
            "Kirim log hanya di tahap penting (6-10 kali per laprak) dengan: python studio/server.py log teks-langkah, digabung dengan perintah Bash yang memang dijalankan (bukan langkah tersendiri) agar hemat token. "
            + ("Pesan yang datang sebagai Pesan baru dari pengguna lewat chat Laprak Studio adalah pesan pengguna biasa. " if CHAT else "")
            + "Tulis kerja/hasil/isi_jenis_N.json sebelum menjalankan laprak/buat_laprak.py.")

# ---------------- HTTP ----------------
class H(BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def _send(self, code, body, ctype="application/json; charset=utf-8"):
        if isinstance(body, (dict, list)): body = json.dumps(body, ensure_ascii=False).encode("utf8")
        elif isinstance(body, str): body = body.encode("utf8")
        self.send_response(code); self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body))); self.send_header("Cache-Control", "no-store"); self.end_headers()
        self.wfile.write(body)
    def _file(self, path, ctype):
        if not os.path.isfile(path): return self._send(404, {"error": "tidak ada"})
        self._send(200, open(path, "rb").read(), ctype)
    def _body(self):
        n = int(self.headers.get("Content-Length", 0)); return self.rfile.read(n) if n else b""
    def do_GET(self):
        u = urlparse(self.path); p = u.path
        if p == "/": return self._file(UI, "text/html; charset=utf-8")
        if p.startswith("/vendor/"):
            nm = os.path.basename(p)
            ct = {".woff2": "font/woff2", ".css": "text/css; charset=utf-8"}.get(os.path.splitext(nm)[1], "application/octet-stream")
            return self._file(os.path.join(HERE, "studio", "web", "vendor", nm), ct)
        if p == "/lisensi": return self._file(os.path.join(HERE, "LICENSE"), "text/plain; charset=utf-8")
        if p == "/favicon.ico": return self._send(204, b"", "image/x-icon")   # ikon tab dipasang oleh halaman
        if p == "/font": return self._file(BL.FONT, "font/ttf")
        if p == "/logo": return self._file(BL.LOGO, "image/png")
        if p == "/final.pdf":
            f = HUB.state.get("final")
            return self._file(os.path.join(HERE, f["file"]), "application/pdf") if f else self._send(404, {"error": "belum ada PDF"})
        if p.startswith("/img/"):
            path = IMAGES.get(p[5:])
            return self._file(path, "image/png") if path else self._send(404, {"error": "gambar tidak dikenal"})
        if p == "/api/antrean":                   # dipanggil studio_hook.py tiap detik saat agent menunggu
            POLL["t"] = time.time()
            if not POLL["menunggu"]: POLL["menunggu"] = True; HUB.send("menunggu", True)
            with ANTREAN_LOCK: pesan = ANTREAN.pop(0) if ANTREAN else None
            if pesan:
                POLL["menunggu"] = False; HUB.send("menunggu", False)
                HUB.log("Studio", "pesan diteruskan ke jendela Claude Code", "build"); HUB.send("antrean", len(ANTREAN))
                HUB.send("status", "bekerja")
            return self._send(200, {"pesan": pesan})
        if p == "/api/info":
            d = date.today()
            return self._send(200, {
                "soal": sorted(os.path.basename(x) for x in glob.glob(os.path.join(WORK, "soal", "*.pdf"))),
                "matkul": daftar_matkul_info(),
                "arsip": sorted(os.path.relpath(x, HERE).replace("\\", "/") for x in
                                glob.glob(os.path.join(HERE, "contoh", "isi_*.json")) +
                                glob.glob(os.path.join(WORK, "archive", "**", "isi_*.json"), recursive=True) +
                                glob.glob(os.path.join(WORK, "hasil", "isi_*.json"))),
                "tanggal": f"{d.day:02d} {BULAN[d.month-1]} {d.year}", "state": HUB.state, "menunggu": POLL["menunggu"], "chat": CHAT, "agent": AGENT_NAMA, "antrean": len(ANTREAN), "viewer": VIEWER})
        if p == "/api/preview":                  # bangun ulang dari JSON yang sudah ada (arsip / hasil)
            rel = unquote(parse_qs(u.query).get("json", [""])[0])
            path = os.path.normpath(os.path.join(HERE, rel))
            if not path.startswith(HERE) or not os.path.isfile(path): return self._send(404, {"error": "JSON tidak ada"})
            try:
                lay = rekam_layout(path); HUB.send("layout", lay)
                nama = lay["file"].split("/")[2] if lay["file"].startswith("kerja/archive/") else os.path.basename(lay["file"])[4:-5]
                HUB.log("Studio", f"Putar ulang {nama.replace('_', ' ')}, sampul + {len(lay['pages']) - 1} halaman", "build")
                pdfs = glob.glob(os.path.join(os.path.dirname(path), "*.pdf")) + glob.glob(os.path.join(os.path.dirname(path), "..", "*.pdf"))
                pdfs = [x for x in pdfs if os.path.basename(x).startswith("Laprak_")]
                if pdfs: HUB.send("final", render_final(max(pdfs, key=os.path.getmtime)))
                else: HUB.send("final", None)
                return self._send(200, {"ok": True})
            except Exception as e:
                traceback.print_exc(); return self._send(500, {"error": f"{type(e).__name__}: {e}"})
        if p == "/events":
            self.send_response(200); self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-store"); self.end_headers()
            q = queue.Queue()
            with HUB.lock: HUB.clients.append(q)
            try:
                self.wfile.write(b"event: hello\ndata: {}\n\n"); self.wfile.flush()
                while True:
                    try: msg = q.get(timeout=15)
                    except queue.Empty: msg = b": ping\n\n"
                    self.wfile.write(msg); self.wfile.flush()
            except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError, OSError):
                pass
            finally:
                with HUB.lock:
                    if q in HUB.clients: HUB.clients.remove(q)
            return
        self._send(404, {"error": "tidak ada"})
    def do_POST(self):
        p = urlparse(self.path).path
        try:
            if p == "/api/upload":
                name = os.path.basename(unquote(self.headers.get("X-Filename", "soal.pdf")))
                if not name.lower().endswith(".pdf"): return self._send(400, {"error": "harus PDF"})
                os.makedirs(os.path.join(WORK, "soal"), exist_ok=True)
                open(os.path.join(WORK, "soal", name), "wb").write(self._body())
                HUB.log("Studio", f"soal diunggah: kerja/soal/{name}", "info")
                return self._send(200, {"ok": True, "name": name})
            d = json.loads(self._body() or b"{}")
            if p == "/api/start":
                if not d.get("soal"): return self._send(400, {"error": "pilih PDF soal dulu"})
                jenis, tgl, cat = d.get("jenis", "pp"), d.get("tanggal", ""), d.get("catatan", "")
                buka_agent(buat_prompt(jenis, tgl, cat, d["soal"]))
                HUB.send("job", {"jenis": jenis, "tanggal": tgl, "soal": d["soal"]})
                HUB.log("Kamu", f"{jenis} {tgl}" + (f"  catatan: {cat}" if cat.strip() else "") + f"  ·  kerja/soal/{d['soal']}", "user")
                HUB.log("Studio", f"Jendela {AGENT_NAMA} dibuka. Izin disetujui di jendela itu.", "info")
                HUB.send("status", "bekerja"); return self._send(200, {"ok": True})
            if p == "/api/pesan":                # chat studio -> antrean -> diambil studio_hook.py
                text = (d.get("text") or "").strip()
                if not text: return self._send(400, {"error": "pesan kosong"})
                with ANTREAN_LOCK: ANTREAN.append(text); n = len(ANTREAN)
                HUB.log("Kamu", text, "user")
                if not POLL["menunggu"]: HUB.log("Studio", "Agent masih bekerja. Pesan mengantre sampai agent selesai.", "info")
                HUB.send("antrean", n); return self._send(200, {"ok": True, "antrean": n})
            if p == "/api/log":                  # langkah dari agent di chat Claude Code (mode penonton)
                HUB.log(d.get("who") or "Agent", d.get("text", ""), d.get("kind") or "tool")
                if HUB.state["status"] != "bekerja": HUB.send("status", "bekerja")
                return self._send(200, {"ok": True})
            if p == "/api/shutdown":
                HUB.log("Studio", "laprak selesai, studio ditutup", "done"); HUB.send("bye", {})
                self._send(200, {"ok": True})
                threading.Timer(0.8, SRV.shutdown).start(); return
        except RuntimeError as e:
            return self._send(409, {"error": str(e)})
        self._send(404, {"error": "tidak ada"})

VIEWER = False; SRV = None
ANTREAN = []; ANTREAN_LOCK = threading.Lock(); POLL = {"t": 0.0, "menunggu": False}

def main():
    """python studio.py                 -> studio lengkap (form -> membuka jendela Claude Code), untuk studio.bat
       python studio.py --viewer        -> mode penonton: agentnya Claude Code di chat; browser dibuka otomatis
       python studio.py log "teks" [jenis]   -> kirim satu baris log ke studio yang sedang jalan (jenis: tool|say|done|warn|build)
       python studio.py stop            -> tutup studio"""
    global VIEWER, SRV
    a = sys.argv[1:]
    VIEWER = "--viewer" in a
    import socket
    with socket.socket() as so:
        if so.connect_ex(("127.0.0.1", PORT)) == 0:     # sudah jalan -> cukup buka browser
            print(f"studio sudah jalan di http://localhost:{PORT}")
            if VIEWER or "--buka" in a: import webbrowser; webbrowser.open(f"http://localhost:{PORT}")
            return
    if VIEWER: HUB.state["status"] = "bekerja"
    threading.Thread(target=watcher, daemon=True).start()
    SRV = ThreadingHTTPServer((HOST, PORT), H); SRV.daemon_threads = True
    print(f"Laprak Studio jalan di http://localhost:{PORT}" + (" (mode penonton)" if VIEWER else "") + "  (Ctrl+C untuk berhenti)", flush=True)
    if (VIEWER or "--buka" in a) and not os.environ.get("LAPRAK_NO_BROWSER"):
        import webbrowser; threading.Timer(0.5, lambda: webbrowser.open(f"http://localhost:{PORT}")).start()
    try: SRV.serve_forever()
    except KeyboardInterrupt: pass

if __name__ == "__main__": main()
